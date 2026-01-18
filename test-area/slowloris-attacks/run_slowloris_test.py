#!/usr/bin/env python3
"""
Slowloris Experiment Launcher + Connection Sampler

Features
--------
- Runs Slowloris against a target (host:port)
- Samples open TCP connections every second using 'ss'
- Supports profiles: baseline / light / medium / full
- Writes outputs to: ~/ADL-TEST-GUARD/reports-area/slowloris/
- Produces:
    1) CSV time-series (open connections)
    2) HTML chart report
    3) JSON run metadata (profile, params, timestamps)

Usage examples
--------------
./run_slowloris_test.py baseline
./run_slowloris_test.py light --host 192.168.42.8 --port 5000
./run_slowloris_test.py medium --sockets 250 --duration 90
./run_slowloris_test.py full --duration 120
"""

import argparse
import json
import os
import shlex
import subprocess
import time
from datetime import datetime

# -----------------------------
# Default profiles (safe ramp)
# -----------------------------
PROFILES = {
    "baseline": {"sockets": 25,  "duration": 60},
    "light":    {"sockets": 100, "duration": 60},
    "medium":   {"sockets": 200, "duration": 60},
    "full":     {"sockets": 400, "duration": 60},
}

DEFAULT_HOST = "192.168.42.8"
DEFAULT_PORT = 5000
SS_CMD = "ss"

REPORTS_DIR = os.path.expanduser("~/ADL-TEST-GUARD/reports-area/slowloris")


def timestamp() -> str:
    return datetime.now().strftime("%Y-%m-%d_%H-%M-%S")


def run_command(cmd: str):
    """Run shell command; return stdout, stderr, rc."""
    result = subprocess.run(
        shlex.split(cmd),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    return result.stdout.strip(), result.stderr.strip(), result.returncode


def start_slowloris(host: str, port: int, sockets: int, verbose: bool):
    """
    Start Slowloris as a background process.
    Assumes 'slowloris' is installed and available in PATH.
    """
    cmd = [
        "slowloris",
        host,
        "-p", str(port),
        "-s", str(sockets),
    ]
    if verbose:
        cmd.append("-v")

    print("\n[+] Starting Slowloris:")
    print("    " + " ".join(cmd))

    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    return proc, cmd


def sample_open_connections(host: str, port: int):
    """
    Count TCP connections from attacker (this machine) to host:port using ss.
    Example: ss -tn dst 192.168.42.8:5000
    """
    cmd = f"{SS_CMD} -tn dst {host}:{port}"
    stdout, stderr, rc = run_command(cmd)
    if rc != 0:
        print(f"[!] Error running '{cmd}': {stderr}")
        return None

    lines = [line for line in stdout.splitlines() if line.strip()]
    if not lines:
        return 0

    # First line is header
    return max(0, len(lines) - 1)


def write_csv(rows, csv_path: str):
    with open(csv_path, "w", encoding="utf-8") as f:
        f.write("second,open_connections\n")
        for sec, conn in rows:
            f.write(f"{sec},{conn}\n")
    print(f"[+] CSV written:  {csv_path}")


def write_json(meta: dict, json_path: str):
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)
    print(f"[+] JSON written: {json_path}")


def write_html(rows, html_path: str, meta: dict):
    js_rows = ",\n".join(f"['{sec}', {conn}]" for sec, conn in rows)

    html_content = f"""<!-- Slowloris Analysis chart -->
<html>
  <head>
    <style>
      body {{
        font: 12px/18px "Lucida Grande", "Lucida Sans Unicode",
              Helvetica, Arial, Verdana, sans-serif;
        background-color: transparent;
        color: #333;
        -webkit-font-smoothing: antialiased;
      }}
      .slow_results {{ font-size: 12px; }}
      .meta {{ margin-bottom: 10px; }}
    </style>
    <script type="text/javascript" src="https://www.google.com/jsapi"></script>
    <script type="text/javascript">
      google.load("visualization", "1", {{packages:["corechart"]}});
      google.setOnLoadCallback(drawChart);
      function drawChart() {{
        var data = new google.visualization.DataTable();
        data.addColumn('string', 'Seconds');
        data.addColumn('number', 'Open connections');
        data.addRows([
{js_rows}
        ]);

        var chart = new google.visualization.AreaChart(
          document.getElementById('chart_div')
        );
        chart.draw(data, {{
          width: 900,
          height: 420,
          title: 'Slowloris test — {meta["target_host"]}:{meta["target_port"]} — profile: {meta["profile"]}',
          hAxis: {{
            title: 'Seconds'
          }},
          vAxis: {{
            title: 'Open connections',
            viewWindowMode: 'maximized'
          }}
        }});
      }}
    </script>
    <title>Slowloris Connection Results</title>
  </head>
  <body>
    <div class="meta">
      <table class='slow_results' border='0'>
        <tr><th colspan="2">Test parameters</th></tr>
        <tr><td><b>Attack type</b></td><td>Slowloris (Partial HTTP Request)</td></tr>
        <tr><td><b>Profile</b></td><td>{meta["profile"]}</td></tr>
        <tr><td><b>Target</b></td><td>{meta["target_host"]}:{meta["target_port"]}</td></tr>
        <tr><td><b>Sockets</b></td><td>{meta["sockets"]}</td></tr>
        <tr><td><b>Duration</b></td><td>{meta["duration"]} seconds</td></tr>
        <tr><td><b>Start time</b></td><td>{meta["start_time"]}</td></tr>
        <tr><td><b>End time</b></td><td>{meta["end_time"]}</td></tr>
      </table>
    </div>
    <div id="chart_div"></div>
  </body>
</html>
"""
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html_content)
    print(f"[+] HTML written: {html_path}")


def parse_args():
    parser = argparse.ArgumentParser(description="Run Slowloris profile test and sample open connections.")
    parser.add_argument(
        "profile",
        nargs="?",
        default="baseline",
        choices=sorted(PROFILES.keys()),
        help="Test intensity profile."
    )
    parser.add_argument("--host", default=DEFAULT_HOST, help="Target host (default: 192.168.42.8)")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help="Target port (default: 5000)")
    parser.add_argument("--sockets", type=int, default=None, help="Override sockets for the profile")
    parser.add_argument("--duration", type=int, default=None, help="Override duration for the profile (seconds)")
    parser.add_argument("--no-verbose", action="store_true", help="Disable Slowloris verbose output (-v)")
    return parser.parse_args()


def main():
    os.makedirs(REPORTS_DIR, exist_ok=True)

    args = parse_args()
    profile_defaults = PROFILES[args.profile]

    sockets = args.sockets if args.sockets is not None else profile_defaults["sockets"]
    duration = args.duration if args.duration is not None else profile_defaults["duration"]
    verbose = not args.no_verbose

    ts = timestamp()
    safe_host = args.host.replace(".", "_")
    base_name = f"slowloris_{args.profile}_{safe_host}_{args.port}_{ts}"

    csv_path = os.path.join(REPORTS_DIR, base_name + ".csv")
    html_path = os.path.join(REPORTS_DIR, base_name + ".html")
    json_path = os.path.join(REPORTS_DIR, base_name + ".json")

    start_time_str = datetime.now().isoformat(timespec="seconds")

    rows = []
    proc = None
    cmd_used = None

    try:
        proc, cmd_used = start_slowloris(args.host, args.port, sockets, verbose)

        print(f"\n[+] Sampling open connections (ss) every 1s for {duration} seconds...")
        print(f"[+] Target: {args.host}:{args.port}")
        print(f"[+] Profile: {args.profile} | sockets={sockets} | duration={duration}")
        print(f"[+] Output base: {base_name}\n")

        t0 = time.time()
        for _ in range(duration + 1):
            elapsed = int(time.time() - t0)
            conn = sample_open_connections(args.host, args.port)
            if conn is None:
                conn = 0

            print(f"t={elapsed:3d}s  open_connections={conn}")
            rows.append((elapsed, conn))
            time.sleep(1)

    finally:
        if proc is not None:
            print("\n[+] Stopping Slowloris process...")
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()

        end_time_str = datetime.now().isoformat(timespec="seconds")

        meta = {
            "attack_type": "slowloris",
            "profile": args.profile,
            "target_host": args.host,
            "target_port": args.port,
            "sockets": sockets,
            "duration": duration,
            "start_time": start_time_str,
            "end_time": end_time_str,
            "command": " ".join(cmd_used) if cmd_used else None,
            "reports_dir": REPORTS_DIR,
            "csv_path": csv_path,
            "html_path": html_path,
            "json_path": json_path,
        }

        write_csv(rows, csv_path)
        write_html(rows, html_path, meta)
        write_json(meta, json_path)

        print("\n[+] Test complete.")
        print(f"    CSV :  {csv_path}")
        print(f"    HTML:  {html_path}")
        print(f"    JSON:  {json_path}")


if __name__ == "__main__":
    main()
