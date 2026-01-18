from locust import HttpUser, task, between
import random

"""
ABUSE MEDIUM SCENARIO — Logic-DoS Test Set
-----------------------------------------
Goal:
    Generate sustained, noticeable application-layer pressure by repeatedly
    abusing resource-intensive endpoints (DB-heavy reads + report generation),
    while also introducing controlled write contention (SQLite lock pressure)
    via POST traffic.

Recommended command:
    locust -f locust_abuse_medium.py --headless \
        -u 75 -r 15 \
        --run-time 5m \
        --print-stats \
        --csv ~/ADL-TEST-GUARD/reports-area/abuse_medium \
        --html ~/ADL-TEST-GUARD/reports-area/abuse_medium.html

Parameters:
    -u 75       --> 75 concurrent users (medium-high logic abuse)
    -r 15       --> ramp-up 15 users per second (moderately fast)
    --run-time  --> 5 minutes to observe latency amplification / contention
    --print-stats -> periodically show stats in the terminal
"""

class AbuseMediumUser(HttpUser):
    # Medium abuse: more aggressive than light, still with short waits
    wait_time = between(0.15, 0.6)

    # Target app server
    host = "http://192.168.42.8:5000"

    @task(6)
    def hammer_historical_data(self):
        """
        DB-heavy read endpoint.
        Weight 6 -> primary load driver (read-side DB pressure).
        """
        self.client.get(
            "/historical-data",
            name="LOGIC GET /historical-data (DB heavy)"
        )

    @task(3)
    def hammer_reports(self):
        """
        CPU / I/O heavy endpoint.
        Weight 3 -> sustained report-generation pressure.
        """
        self.client.get(
            "/reports",
            name="LOGIC GET /reports (CPU / I/O)"
        )

    @task(2)
    def hammer_view_projects(self):
        """
        DB-heavy listing endpoint.
        Weight 2 -> secondary DB pressure path.
        """
        self.client.get(
            "/view_projects",
            name="LOGIC GET /view_projects (DB heavy)"
        )

    @task(1)
    def create_project_write_pressure(self):
        """
        Controlled write pressure:
        Creates new projects to introduce SQLite write contention/locking
        under concurrent load.
        Weight 1 -> less frequent than reads, but impactful for SQLite.
        """
        payload = {
            "project_name": f"MediumAbuse-{random.randint(1000, 9999)}",
            "description": "Locust medium logic abuse",
            "owner": "locust_medium",
        }

        self.client.post(
            "/create_project",
            json=payload,
            name="LOGIC POST /create_project (SQLite write)"
        )
