import pytest


LEVELS = ["baseline", "light", "medium", "full"]


def test_health_endpoint(client):
    response = client.get("/health")
    assert response.status_code == 200

    data = response.get_json()
    assert data["status"] == "Work In Progress. By Angel De  Luis"


def test_validate_page_loads(client):
    response = client.get("/tests/new")
    assert response.status_code == 200


def _baseline_seconds_for_level(level):
    return 60 if level == "full" else 30


def _build_payload(
    test_area,
    test_type,
    runner_mode,
    level,
    host="192.168.42.8",
    port="5000",
    endpoint="/",
):
    baseline_seconds = _baseline_seconds_for_level(level)

    return {
        "test_area": test_area,
        "test_type": test_type,
        "runner_mode": runner_mode,
        "protocol": "http",
        "host": host,
        "port": str(port),
        "endpoints": endpoint,
        "level": level,
        "notes": f"pytest validate {test_area}-{test_type}-{runner_mode}-{level}",
        "baseline_seconds": str(baseline_seconds),
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


def _assert_validation_ok(
    response,
    *,
    expected_area,
    expected_resolved_type,
    expected_resolved_runner,
    expected_level,
):
    assert response.status_code == 200, response.get_data(as_text=True)

    data = response.get_json()
    assert data is not None, response.get_data(as_text=True)

    assert data["ok"] is True
    assert data["test_area"] == expected_area
    assert data["resolved_test_type"] == expected_resolved_type
    assert data["resolved_runner"] == expected_resolved_runner

    assert "parameters" in data
    assert data["parameters"]["level"] == expected_level
    assert data["parameters"]["baseline_seconds"] == _baseline_seconds_for_level(expected_level)
    assert data["parameters"]["request_timeout"] == 10

    assert "target_config" in data
    assert data["target_config"]["protocol"] == "http"
    assert data["target_config"]["host"] == "192.168.42.8"
    assert data["target_config"]["port"] == 5000
    assert data["target_config"]["endpoints"] == ["/"]


def _expand_levels(label_prefix, test_area, test_type, runner_mode, expected_resolved_type, expected_resolved_runner):
    cases = []
    for level in LEVELS:
        cases.append(
            (
                f"{label_prefix} {level}",
                test_area,
                test_type,
                runner_mode,
                level,
                expected_resolved_type,
                expected_resolved_runner,
            )
        )
    return cases


TEST_CASES = (
    _expand_levels(
        "TA1 volumetric",
        "TA1",
        "VOLUMETRIC",
        "locust",
        "__default__",
        "locust",
    )
    + _expand_levels(
        "TA2 slowhttptest header",
        "TA2",
        "SLOWHTTPTEST_HEADER",
        "slowhttptest",
        "SLOWHTTPTEST_HEADER",
        "slowhttptest",
    )
    + _expand_levels(
        "TA2 slowhttptest body",
        "TA2",
        "SLOWHTTPTEST_BODY",
        "slowhttptest",
        "SLOWHTTPTEST_BODY",
        "slowhttptest",
    )
    + _expand_levels(
        "TA2 slowloris",
        "TA2",
        "SLOWLORIS",
        "slowloris",
        "SLOWLORIS",
        "slowloris",
    )
    + _expand_levels(
        "TA3 application-logic",
        "TA3",
        "APPLICATION_LOGIC_ABUSE",
        "locust",
        "__default__",
        "locust",
    )
    + _expand_levels(
        "TA4 curl burst",
        "TA4",
        "CURL_BURST",
        "curl",
        "CURL_BURST",
        "curl",
    )
    + _expand_levels(
        "TA4 curl burst pidstat",
        "TA4",
        "CURL_BURST_PIDSTAT",
        "curl_pidstat",
        "CURL_BURST_PIDSTAT",
        "curl_pidstat",
    )
    + _expand_levels(
        "TA5 async flood",
        "TA5",
        "PYTHON_FLOOD_ASYNC",
        "python_async",
        "ASYNC_FLOOD",
        "python_async",
    )
    + _expand_levels(
        "TA5 requests flood",
        "TA5",
        "REQUESTS_FLOOD",
        "python_requests",
        "REQUESTS_FLOOD",
        "python_requests",
    )
)


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
    payload = _build_payload(
        test_area=test_area,
        test_type=test_type,
        runner_mode=runner_mode,
        level=level,
    )

    response = client.post(
        "/tests/validate",
        data=payload,
        follow_redirects=True,
    )

    print(f"\nTEST: {label}")
    print("STATUS:", response.status_code)
    print("BODY:", response.get_data(as_text=True))

    _assert_validation_ok(
        response,
        expected_area=test_area,
        expected_resolved_type=expected_resolved_type,
        expected_resolved_runner=expected_resolved_runner,
        expected_level=level,
    )


@pytest.mark.parametrize("level", LEVELS)
def test_validate_ta1_without_endpoint_still_normalizes_to_root(client, level):
    payload = _build_payload(
        test_area="TA1",
        test_type="VOLUMETRIC",
        runner_mode="locust",
        level=level,
        endpoint="",
    )

    response = client.post(
        "/tests/validate",
        data=payload,
        follow_redirects=True,
    )

    print(f"\nTEST: TA1 empty endpoint normalization {level}")
    print("STATUS:", response.status_code)
    print("BODY:", response.get_data(as_text=True))

    _assert_validation_ok(
        response,
        expected_area="TA1",
        expected_resolved_type="__default__",
        expected_resolved_runner="locust",
        expected_level=level,
    )


@pytest.mark.parametrize("level", LEVELS)
def test_validate_ta3_without_endpoint_still_normalizes_to_root(client, level):
    payload = _build_payload(
        test_area="TA3",
        test_type="APPLICATION_LOGIC_ABUSE",
        runner_mode="locust",
        level=level,
        endpoint="",
    )

    response = client.post(
        "/tests/validate",
        data=payload,
        follow_redirects=True,
    )

    print(f"\nTEST: TA3 empty endpoint normalization {level}")
    print("STATUS:", response.status_code)
    print("BODY:", response.get_data(as_text=True))

    _assert_validation_ok(
        response,
        expected_area="TA3",
        expected_resolved_type="__default__",
        expected_resolved_runner="locust",
        expected_level=level,
    )
