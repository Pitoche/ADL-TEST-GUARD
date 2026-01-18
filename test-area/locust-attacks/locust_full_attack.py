from locust import HttpUser, task, between
import random

"""
FULL ATTACK / STRESS TEST SCENARIO
----------------------------------
Goal:
    Push the application close to, or beyond, its capacity limits.
    This scenario is for controlled, internal stress testing only.

Recommended command:
    locust -f locust_full_attack.py --headless \
        -u 200 -r 40 \
        --run-time 5m \
        --print-stats

Parameters explained:
    -u 200      --> 200 concurrent users (very high load)
    -r 40       --> ramp-up 40 users per second (aggressive ramp)
    --run-time  --> 5 minutes of sustained attack
    --print-stats -> show stats periodically

⚠ WARNING:
    Only run this against your own controlled lab environment.
    This can easily overwhelm small servers.
"""


class FloodUser(HttpUser):
    # Full attack: extremely short think time.
    # Almost continuous traffic per user.
    # You can go even harder with "wait_time = lambda self: 0".
    wait_time = between(0.05, 0.2)

    # Target your Flask server
    host = "http://192.168.42.8:5000"

    # Same routes list reused so your scenarios are comparable.
    # You can trim / modify this per scenario if needed.
    routes = [
        "/",
        "/docker",
        "/historical-data",
        "/ai-help",
        "/reports",
        "/iot-tools",
        "/settings",
        "/view_projects",
        "/create_project",
    ]

    @task(5)
    def hit_random_route(self):
        """
        READ-HEAVY / RPS-focused part of the attack:
        Continuously hit random endpoints to maximise overall
        request rate and concurrency.
        """
        route = random.choice(self.routes)
        self.client.get(route, name=f"GET {route}")

    @task(2)
    def create_project(self):
        """
        WRITE-HEAVY traffic:
        Generate a high volume of POST requests to stress database,
        application logic and I/O paths.
        """
        payload = {
            "project_name": f"FullAttack-{random.randint(10000, 99999)}",
            "description": "Full-attack generated project",
            "owner": "locust_full_attack",
        }

        self.client.post(
            "/create_project",
            json=payload,
            name="POST /create_project",
        )
