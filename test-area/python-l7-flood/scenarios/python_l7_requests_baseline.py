#!/usr/bin/env python3
import os, subprocess, sys
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
ENGINE = os.path.join(ROOT, "flood_requests.py")

cmd = [
    sys.executable, "-u", ENGINE,
    "--url", "http://192.168.42.8:5000/",
    "--threads", "10",
    "--duration", "60",
    "--rps", "30",
    "--scenario", "l7_requests_baseline",
    "--user-agent", "adl-l7-requests-baseline",
    "--results-dir", os.path.join(ROOT, "results"),
]
print("Running:", " ".join(cmd))
raise SystemExit(subprocess.call(cmd))
