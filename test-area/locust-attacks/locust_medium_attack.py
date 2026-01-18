from locust import HttpUser, task, between
import random

"""
MEDIUM ATTACK SCENARIO
----------------------
Goal:
    Generate sustained, noticeable pressure on the application
    with both read (GET) and write (POST) traffic, but still
    short of a full denial-of-service.

Recommended command:
    locust -f locust_medium_attack.py --headless \
        -u 75 -r 15 \
        --run-time 5m \
        --print-stats

Parameters explained:
    -u 75       --> 75 concurrent users (medium-high load)
    -r 15       --> ramp-up 15 users per second (moderately fast)
    --run-time  --> 5 minutes to observe performance degradation
    --print-stats -> show stats periodically
"""


class FloodUser(HttpUser):
    # Medium attack: more aggressive than light, still not full blast.
    # Short wait time => higher request rate.
    wait_time = between(0.1, 0.5)

    # Full attack, max RPS per user (for reference):
    # wait_time = lambda self: 0

    # Target your Flask server
    host = "http://192.168.42.8:5000"

    # All main application "gates"
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

    @task(4)
    def hit_random_route(self):
        """
        READ-HEAVY traffic:
        Users repeatedly hit random endpoints from the list
        of main application routes.
        Weight 4 --> this happens more often than the POST task.
        """
        route = random.choice(self.routes)
        self.client.get(route, name=f"GET {route}")

    @task(1)
    def create_project(self):
        """
        WRITE-HEAVY traffic:
        Simulate creating a project via POST.
        Adjust payload fields to match your real API.
        Weight 1 --> happens less often than GETs but still present.
        """
        payload = {
            "project_name": f"TestProject-{random.randint(1000, 9999)}",
            "description": "Load-test generated project",
            "owner": "locust_tester",
        }

        self.client.post(
            "/create_project",
            json=payload,
            name="POST /create_project",
        )
