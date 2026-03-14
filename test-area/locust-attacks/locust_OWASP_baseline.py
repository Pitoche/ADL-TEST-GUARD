from locust import HttpUser, task, between
import random

"""
BASELINE SCENARIO
-----------------
Goal:
    Simulate a "normal" single user browsing the application
    with realistic timmings between requests. This is the control / baseline to compare against attack scenarios.

Recommended command:
    locust -f locust_baseline.py --headless \
        -u 1 -r 1 \
        --run-time 2m \
        --print-stats

Parameters :
    -u 1        --> 1 concurrent user (single typical user)
    -r 1        --> ramp-up 1 user per second (instant here)
    --run-time  --> how long the test runs
    --print-stats -> periodically show stats in the terminal
"""


class FloodUser(HttpUser):
    # Baseline (normal human usage)
    # Higher wait time = lower request rate, more realistic.
    wait_time = between(0.8, 2.0)

    # Target app server
    host = "http://192.168.42.8:3001"

    # Main "gates" of the application a normal user might visit
    routes = [
        "/",
        "/historical-data",
        "/reports",
        "/iot-tools",
        "/settings",
        "/view_projects",
    ]

    @task
    def browse_random_route(self):
        """
        Simulate a normal user clicking around the app,
        visiting a random route each time.
        """
        route = random.choice(self.routes)
        self.client.get(route, name=f"GET {route}")
