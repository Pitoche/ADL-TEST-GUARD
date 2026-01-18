#!/usr/bin/env python3
import argparse
import json
import os
import subprocess
from datetime import datetime

# -------------------------------------------------------
# SlowHTTPTest Experiment Launcher (Profiles + Reporting)
# -------------------------------------------------------
# Supports:
#   -H  Slow Headers (Slowloris-style)
#   -B  Slow Body (Slow POST)
#
# Profiles:
#   baseline | light | medium | full
#
# Outputs:
#   ~/ADL-TEST-GUARD/reports-area/slowhttptest/
#   - .html
#   - .csv
#   - .json (run metadata)
# -------------------------------------------------------

TARGET_URL_DEFAULT = "http://192.168.42.8:5000/"

REPORTS_DIR = os.path.expanduser("~/ADL-TEST-GUARD/reports-area/slowhttptest")

# Profile definitions (conservative and reproducible)
# You can adjust based on server capacity.
PROFILES = {
    "baseline": {"c": 50,  "i": 10, "r": 10, "p": 5, "l": 60},
    "light":    {"c": 100, "i": 10, "r": 20, "p": 5, "l": 90},
    "medium":   {"c": 200, "i": 10, "r": 30, "p": 5, "l": 120},
    "full":     {"c": 300, "i": 10, "r": 40, "p": 5, "l": 180},
}


def timestamp():
    return datetime.now().strftime("%Y-%m-%d_%H-%M-%S")


def ensure_reports_dir():
    os.makedirs(REPORTS_DIR, exist_ok=True)


def build_output_prefix(attack_type: str, profile: str, target_url: str):
    ts = timestamp()
    # Make URL file-safe (minimal)
    safe_target = target_url.replace("http://", "").replace("https://", "")
    safe_target = safe_target.replace("/", "_").replace(":", "_")
    base = f"slowhttptest_{attack_type}_{profile}_{safe_target}_{ts}"
    return os.path.join(REPORTS_DIR, base)


def write_metadata_json(meta: dict, output_prefix: str):
    json_path = output_prefix + ".json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)
    print(f"[+] JSON written: {json_path}")


def run_slowhttptest(mode: str, profile: str, target_url: str, overrides: dict):
    """
    mode:
      H = slow headers (-H)
      B = slow body (-B)
    """
    ensure_reports_dir()

    profile_cfg = PROFILES[profile].copy()
    profile_cfg.update({k: v for k, v in overrides.items() if v is not None})

    c = str(profile_cfg["c"])   # concurrent connections
    i = str(profile_cfg["i"])   # interval between follow-up data (sec)
    r = str(profile_cfg["r"])   # connections per second
    p = str(profile_cfg["p"])   # probe timeout
    l = str(profile_cfg["l"])   # test length

    attack_type = "headers" if mode == "H" else "body"
    output_prefix = build_output_prefix(attack_type, profile, target_url)

    cmd = [
        "slowhttptest",
        f"-{mode}",
        "-c", c,
        "-i", i,
        "-r", r,
        "-u", target_url,
        "-p", p,
        "-l", l,
        "-g",
        "-o", output_prefix,
    ]

    print("\n===================================================")
    print(f"[▶] Running SlowHTTPTest: {attack_type.upper()} | Profile: {profile.upper()}")
    print(f"[▶] Target URL: {target_url}")
    print(f"[▶] Output prefix (reports dir): {output_prefix}")
    print("[▶] Files expected:")
    print(f"    {output_prefix}.html")
    print(f"    {output_prefix}.csv")
    print(f"    {output_prefix}.json")
    print("[▶] Command:")
    print("    " + " ".join(cmd))
    print("===================================================\n")

    start_time = datetime.now().isoformat(timespec="seconds")
    rc = subprocess.call(cmd)
    end_time = datetime.now().isoformat(timespec="seconds")

    meta = {
        "tool": "slowhttptest",
        "attack_type": attack_type,
        "mode_flag": f"-{mode}",
        "profile": profile,
        "target_url": target_url,
        "parameters": {
            "c_concurrent_connections": int(c),
            "i_interval_seconds": int(i),
            "r_rate_connections_per_sec": int(r),
            "p_probe_timeout": int(p),
            "l_test_length_seconds": int(l),
            "g_generate_charts": True,
        },
        "command": " ".join(cmd),
        "start_time": start_time,
        "end_time": end_time,
        "return_code": rc,
        "reports_dir": REPORTS_DIR,
        "output_prefix": output_prefix,
        "expected_outputs": [output_prefix + ".html", output_prefix + ".csv", output_prefix + ".json"],
    }

    write_metadata_json(meta, output_prefix)

    print("\n[+] Test complete.")
    print(f"    RC  : {rc}")
    print(f"    HTML: {output_prefix}.html")
    print(f"    CSV : {output_prefix}.csv")
    print(f"    JSON: {output_prefix}.json")
    print()


def parse_args():
    parser = argparse.ArgumentParser(
        description="SlowHTTPTest runner with Baseline/Light/Medium/Full profiles + central reports folder."
    )
    parser.add_argument("mode", choices=["H", "B"], help="H=Slow Headers, B=Slow Body")
    parser.add_argument("profile", choices=list(PROFILES.keys()), help="baseline|light|medium|full")
    parser.add_argument("--url", default=TARGET_URL_DEFAULT, help="Target URL (default points to your Flask app)")

    # Optional overrides (leave blank to use profile defaults)
    parser.add_argument("--c", type=int, help="Override -c (concurrent connections)")
    parser.add_argument("--i", type=int, help="Override -i (interval seconds)")
    parser.add_argument("--r", type=int, help="Override -r (connections per second)")
    parser.add_argument("--p", type=int, help="Override -p (probe timeout)")
    parser.add_argument("--l", type=int, help="Override -l (test length seconds)")

    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()

    overrides = {"c": args.c, "i": args.i, "r": args.r, "p": args.p, "l": args.l}
    run_slowhttptest(args.mode, args.profile, args.url, overrides)
