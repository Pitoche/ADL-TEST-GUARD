from locust import HttpUser, task
import random

"""
ABUSE FULL SCENARIO — Logic-DoS Test Set (Logic Bomb)
-----------------------------------------------------
Goal:
    Maximise application-layer cost using valid, behaviour-driven requests
    with minimal think time. This focuses on:
      - DB-heavy reads (historical-data, view_projects)
      - CPU/I/O-heavy reporting (reports)
      - SQLite write contention (create_project)

    This scenario is intended to push the application toward (or into)
    availability degradation via logic exploitation rather than raw bandwidth.

Recommended command:
    locust -f locust_abuse_full.py --headless \
        -u 150 -r 30 \
        --run-time 5m \
        --print-stats \
        --csv ~/ADL-TEST-GUARD/reports-area/abuse_full \
        --html ~/ADL-TEST-GUARD/reports-area/abuse_full.html

Parameters:
    -u 150      --> 150 concurrent users (high logic-abuse concurrency)
    -r 30       --> ramp-up 30 users per second (fast)
    --run-time  --> 5 minutes to capture peak degradation behaviour
    --print-stats -> periodically show stats in the terminal
"""

class AbuseFullUser(HttpUser):
    # Full abuse: maximum per-user request rate (very aggressive)
    wait_time = lambda self: 0

    # Target app server
    host = "http://192.168.42.8:5000"

    @task(8)
    def heavy_db_reads(self):
        """
        Hammer DB-heavy endpoints to drive read pressure.
        Weight 8 -> primary load driver.
        """
        route = random.choice(["/historical-data", "/view_projects"])
        self.client.get(route, name=f"LOGIC GET {route} (DB heavy)")

    @task(4)
    def heavy_reports(self):
        """
        Hammer reporting endpoint to drive CPU/I/O pressure.
        Weight 4 -> strong secondary load driver.
        """
        self.client.get(
            "/reports",
            name="LOGIC GET /reports (CPU / I/O)"
        )

    @task(3)
    def sqlite_write_contention(self):
        """
        High write contention path:
        Frequent project creation to exacerbate SQLite locking/contention.
        Weight 3 -> substantial write load (use with caution).
        """
        payload = {
            "project_name": f"FullAbuse-{random.randint(100000, 999999)}",
            "description": "Locust full logic abuse",
            "owner": "locust_full",
        }

        self.client.post(
            "/create_project",
            json=payload,
            name="LOGIC POST /create_project (SQLite write)"
        )
