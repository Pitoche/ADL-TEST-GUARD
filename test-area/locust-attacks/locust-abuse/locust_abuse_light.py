from locust import HttpUser, task, between
import random

"""
ABUSE LIGHT SCENARIO — Logic-DoS Test Set
----------------------------------------
Goal:
    Apply light, behaviour-driven pressure on resource-intensive
    application endpoints while remaining below full denial-of-service.
    This scenario represents early-stage application-layer logic abuse.

Recommended command:
    locust -f locust_abuse_light.py --headless \
        -u 25 -r 5 \
        --run-time 5m \
        --print-stats \
        --csv ~/ADL-TEST-GUARD/reports-area/abuse_light \
        --html ~/ADL-TEST-GUARD/reports-area/abuse_light.html

Parameters:
    -u 25       --> 25 concurrent users (light abuse)
    -r 5        --> ramp-up 5 users per second
    --run-time  --> 5 minutes sustained pressure
    --print-stats -> periodically show stats in the terminal
"""

class AbuseLightUser(HttpUser):
    # Light abuse: faster than baseline but still human-like
    wait_time = between(0.6, 1.5)

    # Target app server
    host = "http://192.168.42.8:5000"

    # DB-heavy endpoints (logic-relevant)
    expensive_db_routes = [
        "/historical-data",
        "/view_projects",
    ]

    @task(6)
    def db_heavy_reads(self):
        """
        Repeated access to DB-intensive read endpoints.
        Weight 6 -> primary focus of light abuse.
        """
        route = random.choice(self.expensive_db_routes)
        self.client.get(route, name=f"LOGIC GET {route} (DB heavy)")

    @task(3)
    def reports_pressure(self):
        """
        Light pressure on report generation.
        Weight 3 -> moderate CPU / I/O cost.
        """
        self.client.get(
            "/reports",
            name="LOGIC GET /reports (CPU / I/O)"
        )

    @task(1)
    def occasional_normal_navigation(self):
        """
        Occasional normal navigation to maintain
        realistic user behaviour.
        """
        route = random.choice([
            "/",
            "/settings",
            "/docker",
        ])
        self.client.get(route, name=f"GET {route}")
