#!/usr/bin/env python3
import os, subprocess, sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
ENGINE = os.path.join(ROOT, "flood_requests.py")

cmd = [
    sys.executable, "-u", ENGINE,
    "--url", "http://192.168.42.8:5000/api/projects",
    "--threads", "80",
    "--duration", "90",
    "--rps", "200",
    "--scenario", "l7_requests_medium",
    "--user-agent", "adl-l7-requests-medium",
    "--results-dir", os.path.join(ROOT, "results"),
]

print("Running:", " ".join(cmd))
raise SystemExit(subprocess.call(cmd))
