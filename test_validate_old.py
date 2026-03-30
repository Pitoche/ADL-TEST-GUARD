import pytest


def test_health_endpoint(client):
    response = client.get("/health")
    assert response.status_code == 200

    data = response.get_json()
    assert data["status"] == "Work In Progress. By Angel De  Luis"


def test_validate_page_loads(client):
    response = client.get("/tests/new")
    assert response.status_code == 200


TEST_CASES = [
    # label, submitted area, submitted type, submitted runner, level, expected resolved type, expected resolved runner
    ("TA1 baseline", "TA1", "VOLUMETRIC", "locust", "baseline", "__default__", "locust"),
    ("TA1 light", "TA1", "VOLUMETRIC", "locust", "light", "__default__", "locust"),

    ("TA2 header baseline", "TA2", "SLOWHTTPTEST_HEADER", "slowhttptest", "baseline", "SLOWHTTPTEST_HEADER", "slowhttptest"),
    ("TA2 body baseline", "TA2", "SLOWHTTPTEST_BODY", "slowhttptest", "baseline", "SLOWHTTPTEST_BODY", "slowhttptest"),
    ("TA2 slowloris baseline", "TA2", "SLOWLORIS", "slowloris", "baseline", "SLOWLORIS", "slowloris"),

    ("TA3 baseline", "TA3", "APPLICATION_LOGIC_ABUSE", "locust", "baseline", "__default__", "locust"),

    ("TA4 curl baseline", "TA4", "CURL_BURST", "curl", "baseline", "CURL_BURST", "curl"),
    ("TA4 curl pidstat baseline", "TA4", "CURL_BURST_PIDSTAT", "curl_pidstat", "baseline", "CURL_BURST_PIDSTAT", "curl_pidstat"),

    ("TA5 async baseline", "TA5", "PYTHON_FLOOD_ASYNC", "python_async", "baseline", "ASYNC_FLOOD", "python_async"),
]


@pytest.mark.parametrize(
    "label,test_area,test_type,runner_mode,level,expected_resolved_type,expected_resolved_runner",
    TEST_CASES,
)
def test_validate_matrix(
    client,
    label,
    test_area,
    test_type,
    runner_mode,
    level,
    expected_resolved_type,
    expected_resolved_runner,
):
    payload = {
        "test_area": test_area,
        "test_type": test_type,
        "runner_mode": runner_mode,
        "protocol": "http",
        "host": "192.168.42.8",
        "port": "5000",
        "endpoints": "/",
        "level": level,
        "notes": f"pytest {test_area}-{test_type}-{level}",
        "baseline_seconds": "60",
        "request_timeout": "10",
        "collect_telemetry": "",
        "custom_flags": "",
        "dry_run": "",
        "escalation_schedule": "",
        "follow_redirects": "",
        "keep_alive": "",
        "randomize_endpoints": "",
        "store_artifacts": "",
    }

    response = client.post(
        "/tests/validate",
        data=payload,
        follow_redirects=True,
    )

    print(f"\nTEST: {label}")
    print("STATUS:", response.status_code)
    print("BODY:", response.get_data(as_text=True))

    assert response.status_code == 200

    data = response.get_json()
    assert data["ok"] is True
    assert data["test_area"] == test_area
    assert data["resolved_test_type"] == expected_resolved_type
    assert data["resolved_runner"] == expected_resolved_runner


@pytest.mark.xfail(reason="Known issue: TA5 requests currently resolves to ASYNC_FLOOD/python_async")
def test_validate_ta5_requests_baseline_known_bug(client):
    payload = {
        "test_area": "TA5",
        "test_type": "PYTHON_FLOOD_REQUESTS",
        "runner_mode": "python_requests",
        "protocol": "http",
        "host": "192.168.42.8",
        "port": "5000",
        "endpoints": "/",
        "level": "baseline",
        "notes": "pytest TA5 requests known bug",
        "baseline_seconds": "60",
        "request_timeout": "10",
        "collect_telemetry": "",
        "custom_flags": "",
        "dry_run": "",
        "escalation_schedule": "",
        "follow_redirects": "",
        "keep_alive": "",
        "randomize_endpoints": "",
        "store_artifacts": "",
    }

    response = client.post(
        "/tests/validate",
        data=payload,
        follow_redirects=True,
    )

    print("\nTEST: TA5 requests baseline known bug")
    print("STATUS:", response.status_code)
    print("BODY:", response.get_data(as_text=True))

    assert response.status_code == 200

    data = response.get_json()
    assert data["ok"] is True
    assert data["test_area"] == "TA5"
    assert data["resolved_test_type"] == "REQUEST_FLOOD"
    assert data["resolved_runner"] == "python_requests"
