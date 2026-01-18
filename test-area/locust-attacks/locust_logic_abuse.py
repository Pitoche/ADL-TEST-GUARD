from locust import HttpUser, task, between
import random

"""
LOGIC BOMB / L7 LOGIC DoS
------------------------
Goal:
    Abuse CPU- and DB-intensive endpoints using valid,
    low-volume but high-cost requests.
"""

class LogicAbuseUser(HttpUser):
    host = "http://192.168.42.8:5000"
    wait_time = between(0.1, 0.4)

    @task(6)
    def abuse_historical_data(self):
        """
        DB-heavy logic abuse:
        Repeated access to historical-data which likely
        performs full-table scans or aggregations.
        """
        self.client.get(
            "/historical-data",
            name="LOGIC: historical-data (DB heavy)"
        )

    @task(3)
    def abuse_reports(self):
        """
        CPU / I/O-heavy logic abuse:
        Forces report generation and file handling.
        """
        self.client.get(
            "/reports",
            name="LOGIC: reports (CPU + I/O)"
        )

    @task(1)
    def abuse_write_path(self):
        """
        Optional DB-lock pressure:
        Writes cause SQLite contention under concurrency.
        """
        payload = {
            "project_name": f"LogicDoS-{random.randint(1000,9999)}",
            "description": "Logic abuse test",
            "owner": "locust_logic"
        }

        self.client.post(
            "/create_project",
            json=payload,
            name="LOGIC: create_project (DB write)"
        )
