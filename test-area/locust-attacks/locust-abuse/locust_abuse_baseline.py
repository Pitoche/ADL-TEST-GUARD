from locust import HttpUser, task, between
import random

"""
ABUSE BASELINE (CONTROL) — Logic-DoS Test Set
--------------------------------------------
Goal:
    Simulate normal-ish user browsing with realistic timings,
    plus occasional access to resource-intensive endpoints.
    This is the control / baseline to compare against logic-abuse scenarios.

Recommended command:
    locust -f locust_abuse_baseline.py --headless \
        -u 5 -r 1 \
        --run-time 2m \
        --print-stats

Parameters:
    -u 5        --> 5 concurrent users (light baseline)
    -r 1        --> ramp-up 1 user per second
    --run-time  --> 2 minutes baseline capture
    --print-stats -> periodically show stats in the terminal
"""

class AbuseBaselineUser(HttpUser):
    # Baseline (normal human usage)
    # Higher wait time = lower request rate, more realistic.
    wait_time = between(1.5, 4.0)

    # Target app server
    host = "http://192.168.42.8:5000"

    # Normal navigation routes (low-cost)
    normal_routes = [
        "/",
        "/docker",
        "/iot-tools",
        "/settings",
        "/ai-help",
    ]

    # Expensive routes (higher-cost / logic-relevant)
    expensive_routes = [
        "/historical-data",   # DB heavy
        "/view_projects",     # DB heavy listing
        "/reports",           # CPU / I/O heavy
    ]

    @task(8)
    def browse_normal(self):
        """
        Simulate a normal user clicking around typical pages.
        Weight 8 -> happens most often.
        """
        route = random.choice(self.normal_routes)
        self.client.get(route, name=f"GET {route}")

    @task(2)
    def occasional_expensive(self):
        """
        Occasionally hit more expensive endpoints.
        Weight 2 -> happens less often than normal browsing.
        """
        route = random.choice(self.expensive_routes)
        self.client.get(route, name=f"GET {route} (expensive)")
