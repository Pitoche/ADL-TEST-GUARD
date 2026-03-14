TEST_CATALOG = {
  "TA1": {
    "VOL_LOCUST": {
      "label": "Volumetric L7 Flood (Locust)",
      "profiles": {
        "baseline": {"users": 1, "spawn_rate": 1, "run_time": "60s", "locustfile": "locust_baseline.py"},
        "light":    {"users": 50, "spawn_rate": 10, "run_time": "2m",  "locustfile": "locust_light_attack.py"},
        "medium":   {"users": 150,"spawn_rate": 30, "run_time": "3m",  "locustfile": "locust_medium_attack.py"},
        "full":     {"users": 300,"spawn_rate": 60, "run_time": "5m",  "locustfile": "locust_full_attack.py"},
      }
    }
  },
  "TA5": {
    "PY_ASYNC_FLOOD": {
      "label": "Python AsyncIO Flood",
      "profiles": {
        "baseline": {"concurrency": 5, "duration": 60, "rps": 10, "script": "flood_async.py"},
        "full":     {"concurrency": 200, "duration": 300, "rps": 0, "script": "flood_async.py"},
      }
    }
  }
}