from locust import HttpUser, task, between
import random

"""
LIGHT ATTACK SCENARIO
---------------------
Goal:
    Create visible load on the application without causing total failure. 
    Good for early testing and tuning.

Recommended command:
    locust -f locust_light_attack.py --headless \
        -u 25 -r 5 \
        --run-time 2m \
        --print-stats

Parameters explained:
    -u 25       --> 25 concurrent users, light concurrent pressure
    -r 5        --> ramp-up 5 users per second (smooth, not a spike)
    --run-time  --> run for 2 minutes to observe early degradation
    --print-stats -> show stats in the terminal periodically
"""


class FloodUser(HttpUser):
    # Light attack (visible in metrics, not devastating)
    # Slightly faster than a human, but not crazy.
    wait_time = between(0.3, 0.8)

    # Baseline sample (for reference):
    # wait_time = between(0.5, 1.5)

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

    @task
    def hit_random_route(self):
        """
        Simulate a light browsing pattern: users repeatedly load random pages across the application.
        """
        route = random.choice(self.routes)
        self.client.get(route, name=f"GET {route}")
