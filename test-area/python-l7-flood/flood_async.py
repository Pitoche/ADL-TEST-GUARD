#!/usr/bin/env python3
"""
AsyncIO + aiohttp Layer-7 flood generator (LAB USE ONLY)

- Controlled, adjustable concurrency + (optional) RPS cap
- GET/POST support
- Jitter + delay support
- Results written to ./results (symlink recommended to central reports-area)

Ethical use:
Run ONLY against systems you own/control and have explicit permission to test.
"""

import argparse
import asyncio
import json
import os
import random
import sys
import time
from datetime import datetime, timezone
from typing import Dict, Optional, Tuple, List

import aiohttp
from pathlib import Path

REPORTS_ROOT = Path.home() / "ADL-TEST-GUARD" / "reports-area" / "python-l7-flood"
REPORTS_ROOT.mkdir(parents=True, exist_ok=True)

KNOWN_PROFILES = {"baseline", "light", "medium", "full"}
PROFILE = sys.argv[1].lower() if len(sys.argv) > 1 and sys.argv[1].lower() in KNOWN_PROFILES else "baseline"

PROFILE_DIR = REPORTS_ROOT / PROFILE
PROFILE_DIR.mkdir(parents=True, exist_ok=True)




def utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def now_iso_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def read_payload(path: Optional[str], size_bytes: int) -> str:
    """
    If payload file provided, read it.
    Else generate a JSON payload roughly size_bytes (best-effort).
    """
    if path:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()

    if size_bytes <= 0:
        return ""

    # Best-effort payload sizing: fill a string field.
    base = {"ts": now_iso_utc(), "data": ""}
    overhead = len(json.dumps(base).encode("utf-8")) + 20
    fill_len = max(0, size_bytes - overhead)
    base["data"] = "A" * fill_len
    return json.dumps(base)


class RateLimiter:
    """
    Simple token bucket limiter for approximate global RPS control.
    """
    def __init__(self, rps: float):
        self.rps = float(rps)
        self._tokens = 0.0
        self._last = time.perf_counter()
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        if self.rps <= 0:
            return

        async with self._lock:
            while True:
                now = time.perf_counter()
                elapsed = now - self._last
                self._last = now

                self._tokens += elapsed * self.rps
                if self._tokens > self.rps:
                    self._tokens = self.rps  # cap burst

                if self._tokens >= 1.0:
                    self._tokens -= 1.0
                    return

                # not enough tokens, sleep a bit
                need = (1.0 - self._tokens) / self.rps
                await asyncio.sleep(min(max(need, 0.001), 0.05))


async def one_request(
    session: aiohttp.ClientSession,
    method: str,
    url: str,
    headers: Dict[str, str],
    body: Optional[str],
    timeout_s: float,
) -> Tuple[bool, int, float, str]:
    """
    Returns: (ok, status, latency_ms, err)
    """
    t0 = time.perf_counter()
    try:
        timeout = aiohttp.ClientTimeout(total=timeout_s)
        async with session.request(
            method=method,
            url=url,
            headers=headers,
            data=body if (method.upper() in ("POST", "PUT", "PATCH") and body is not None) else None,
            timeout=timeout,
        ) as resp:
            # read body to completion so server does real work
            await resp.read()
            latency_ms = (time.perf_counter() - t0) * 1000.0
            return True, int(resp.status), latency_ms, ""
    except Exception as e:
        latency_ms = (time.perf_counter() - t0) * 1000.0
        return False, 0, latency_ms, repr(e)


async def worker(
    wid: int,
    session: aiohttp.ClientSession,
    urls: List[str],
    method: str,
    headers: Dict[str, str],
    body: Optional[str],
    timeout_s: float,
    end_time: float,
    limiter: Optional[RateLimiter],
    base_delay_ms: int,
    jitter_ms: int,
    results_q: asyncio.Queue,
) -> None:
    """
    Each worker loops until end_time, selecting a URL and issuing requests.
    """
    rng = random.Random(wid * 1337 + int(time.time()))
    while time.perf_counter() < end_time:
        if limiter:
            await limiter.acquire()

        url = rng.choice(urls)
        ok, status, latency_ms, err = await one_request(
            session=session,
            method=method,
            url=url,
            headers=headers,
            body=body,
            timeout_s=timeout_s,
        )

        await results_q.put({
            "ts": now_iso_utc(),
            "worker": wid,
            "method": method.upper(),
            "url": url,
            "ok": ok,
            "status": status,
            "latency_ms": round(latency_ms, 3),
            "error": err,
        })

        # pacing
        if base_delay_ms > 0 or jitter_ms > 0:
            j = rng.randint(0, max(0, jitter_ms))
            await asyncio.sleep((base_delay_ms + j) / 1000.0)


async def writer(results_q: asyncio.Queue, out_jsonl: str, end_time: float) -> None:
    """
    Writes JSONL until workers stop and queue drains.
    """
    with open(out_jsonl, "w", encoding="utf-8") as f:
        while True:
            try:
                item = await asyncio.wait_for(results_q.get(), timeout=0.5)
                f.write(json.dumps(item) + "\n")
                results_q.task_done()
            except asyncio.TimeoutError:
                if time.perf_counter() >= end_time and results_q.empty():
                    break


def summarize(jsonl_path: str) -> Dict:
    total = 0
    ok = 0
    status_counts = {}
    latencies = []

    with open(jsonl_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            total += 1
            rec = json.loads(line)
            if rec.get("ok"):
                ok += 1
                st = int(rec.get("status", 0))
                status_counts[st] = status_counts.get(st, 0) + 1
            latencies.append(float(rec.get("latency_ms", 0.0)))

    latencies.sort()
    def pct(p: float) -> float:
        if not latencies:
            return 0.0
        idx = int(round((p / 100.0) * (len(latencies) - 1)))
        return float(latencies[max(0, min(idx, len(latencies) - 1))])

    return {
        "total_requests": total,
        "ok_requests": ok,
        "error_requests": total - ok,
        "ok_rate": (ok / total) if total else 0.0,
        "status_counts": dict(sorted(status_counts.items(), key=lambda x: x[0])),
        "latency_ms": {
            "min": latencies[0] if latencies else 0.0,
            "p50": pct(50),
            "p90": pct(90),
            "p95": pct(95),
            "p99": pct(99),
            "max": latencies[-1] if latencies else 0.0,
        },
    }


async def main_async(args: argparse.Namespace) -> int:
    # Outputs
    results_dir = os.path.abspath(args.results_dir)
    ensure_dir(results_dir)
    run_id = args.run_id or f"async_l7_{utc_stamp()}"
    out_jsonl = os.path.join(results_dir, f"{run_id}.jsonl")
    out_summary = os.path.join(results_dir, f"{run_id}.summary.json")

    # URLs
    urls = [u.strip() for u in args.url if u.strip()]
    if not urls:
        print("❌ No URLs provided. Use --url one or more times.", file=sys.stderr)
        return 2

    # Headers (scenario attribution)
    headers = {
        "User-Agent": args.user_agent,
        "X-Test-Scenario": args.scenario,
    }
    # Optional extra headers (k:v)
    for hv in args.header or []:
        if ":" not in hv:
            continue
        k, v = hv.split(":", 1)
        headers[k.strip()] = v.strip()

    body = None
    if args.method.upper() in ("POST", "PUT", "PATCH"):
        body = read_payload(args.payload_file, args.payload_size)

    limiter = RateLimiter(args.rps) if args.rps > 0 else None

    connector = aiohttp.TCPConnector(
        limit=args.concurrency * 2,  # allow some headroom
        ssl=False,
    )

    print(f"▶ run_id:       {run_id}")
    print(f"▶ urls:         {len(urls)}")
    print(f"▶ method:       {args.method.upper()}")
    print(f"▶ concurrency:  {args.concurrency}")
    print(f"▶ duration_s:   {args.duration}")
    print(f"▶ rps_cap:      {args.rps if args.rps > 0 else 'disabled'}")
    print(f"▶ delay_ms:     {args.delay_ms} (+ jitter {args.jitter_ms})")
    print(f"▶ scenario:     {args.scenario}")
    print(f"▶ results_dir:  {results_dir}")
    print(f"▶ out_jsonl:    {out_jsonl}")

    end_time = time.perf_counter() + args.duration
    results_q: asyncio.Queue = asyncio.Queue(maxsize=args.concurrency * 1000)

    async with aiohttp.ClientSession(connector=connector) as session:
        w_task = asyncio.create_task(writer(results_q, out_jsonl, end_time))

        workers = [
            asyncio.create_task(
                worker(
                    wid=i + 1,
                    session=session,
                    urls=urls,
                    method=args.method,
                    headers=headers,
                    body=body,
                    timeout_s=args.timeout,
                    end_time=end_time,
                    limiter=limiter,
                    base_delay_ms=args.delay_ms,
                    jitter_ms=args.jitter_ms,
                    results_q=results_q,
                )
            )
            for i in range(args.concurrency)
        ]

        await asyncio.gather(*workers)
        await results_q.join()
        await w_task

    s = summarize(out_jsonl)
    with open(out_summary, "w", encoding="utf-8") as f:
        json.dump(
            {
                "run_id": run_id,
                "started_utc": None,  # kept simple
                "ended_utc": now_iso_utc(),
                "config": {
                    "urls": urls,
                    "method": args.method.upper(),
                    "concurrency": args.concurrency,
                    "duration_s": args.duration,
                    "rps_cap": args.rps,
                    "delay_ms": args.delay_ms,
                    "jitter_ms": args.jitter_ms,
                    "timeout_s": args.timeout,
                    "scenario": args.scenario,
                    "user_agent": args.user_agent,
                    "payload_size": args.payload_size if body is not None else 0,
                    "payload_file": args.payload_file if body is not None else None,
                },
                "summary": s,
            },
            f,
            indent=2,
        )

    print("✅ Done.")
    print(f"📄 Summary: {out_summary}")
    print(json.dumps(s, indent=2))
    return 0


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="AsyncIO L7 flood generator (LAB USE ONLY)",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    p.add_argument("--url", action="append", required=True,
                   help="Target URL. Use multiple times for a pool.")
    p.add_argument("--method", default="GET",
                   choices=["GET", "POST", "PUT", "PATCH"],
                   help="HTTP method.")
    p.add_argument("--concurrency", type=int, default=200,
                   help="Number of concurrent workers.")
    p.add_argument("--duration", type=int, default=60,
                   help="Duration in seconds.")
    p.add_argument("--rps", type=float, default=0.0,
                   help="Global approximate RPS cap (0 disables).")
    p.add_argument("--delay-ms", type=int, default=0,
                   help="Base delay between requests per worker.")
    p.add_argument("--jitter-ms", type=int, default=0,
                   help="Random jitter added to delay-ms (0..jitter-ms).")
    p.add_argument("--timeout", type=float, default=10.0,
                   help="Request timeout seconds.")
    p.add_argument("--scenario", default="l7_flood_async",
                   help="Value for X-Test-Scenario header.")
    p.add_argument("--user-agent", default="adl-async-l7-flood",
                   help="User-Agent header.")
    p.add_argument("--header", action="append",
                   help="Extra header in 'Key: Value' format. Can be repeated.")
    p.add_argument("--payload-size", type=int, default=0,
                   help="Payload size in bytes (best-effort) for POST/PUT/PATCH if no file.")
    p.add_argument("--payload-file", default=None,
                   help="Path to payload file (raw text/JSON) for POST/PUT/PATCH.")
    p.add_argument("--results-dir", default=str(REPORTS_ROOT),
                   help="Where to write output files (JSONL + summary).")




   # p.add_argument("--results-dir", default=str(PROFILE_DIR),
    #          help="Where to write output files (JSONL + summary).")
    p.add_argument("--run-id", default=None,
                   help="Override run id filename prefix.")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    try:
        return asyncio.run(main_async(args))
    except KeyboardInterrupt:
        print("\n⏹️ Interrupted.")
        return 130


if __name__ == "__main__":
    raise SystemExit(main())

