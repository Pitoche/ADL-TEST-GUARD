"""
app/services/test_taxonomy.py

Corrected taxonomy for the ADL-TEST-GUARD testing area.

Key rules implemented:
- TA1 has NO user-visible subtype and uses LOCUST only
- TA2 has subtypes:
    - SLOWHTTPTEST_BODY
    - SLOWHTTPTEST_HEADER
    - SLOWLORIS
- TA3 has NO user-visible subtype and uses LOCUST only
- TA4 has subtypes:
    - CURL_BURST
    - CURL_BURST_PIDSTAT
- TA5 has subtypes:
    - ASYNC_FLOOD
    - REQUESTS_FLOOD

Compatibility:
- Some existing routes.py code may still expect:
      TEST_TAXONOMY[area][test_type]["fields"]
- To preserve compatibility, TA1 and TA3 include an INTERNAL subtype key:
      "__default__"
  but helper functions hide that from the UI.
"""

from copy import deepcopy
from typing import Dict, List, Tuple, Optional


# ---------------------------------------------------------------------
# Common reusable field sets
# ---------------------------------------------------------------------

COMMON_HTTP_FIELDS = {
    "users": {
        "label": "Concurrent Users / Workers",
        "type": "select",
        "choices": [
            (1, "1"),
            (5, "5"),
            (10, "10"),
            (25, "25"),
            (50, "50"),
            (100, "100"),
            (200, "200"),
            (300, "300"),
            (500, "500"),
            (1000, "1000"),
        ],
        "default": 10,
        "help": "Number of concurrent workers / virtual users.",
    },
    "spawn_rate": {
        "label": "Spawn Rate / Ramp-up per Second",
        "type": "select",
        "choices": [
            (1, "1"),
            (2, "2"),
            (5, "5"),
            (10, "10"),
            (20, "20"),
            (30, "30"),
            (50, "50"),
            (100, "100"),
        ],
        "default": 5,
        "help": "Ramp-up rate used by the runner.",
    },
    "duration_seconds": {
        "label": "Attack Duration (seconds)",
        "type": "select",
        "choices": [
            (30, "30"),
            (60, "60"),
            (120, "120"),
            (180, "180"),
            (300, "300"),
            (600, "600"),
        ],
        "default": 60,
        "help": "Planned duration for the active attack phase.",
    },
    "request_timeout": {
        "label": "Request Timeout (seconds)",
        "type": "select",
        "choices": [
            (3, "3"),
            (5, "5"),
            (10, "10"),
            (15, "15"),
            (30, "30"),
            (60, "60"),
        ],
        "default": 10,
        "help": "Per-request timeout used by the runner.",
    },
    "randomize_endpoints": {
        "label": "Randomize Endpoint Selection",
        "type": "bool",
        "default": False,
        "help": "If enabled, endpoints are selected randomly.",
    },
    "follow_redirects": {
        "label": "Follow Redirects",
        "type": "bool",
        "default": False,
        "help": "If enabled, HTTP redirects will be followed.",
    },
    "keep_alive": {
        "label": "Use Keep-Alive",
        "type": "bool",
        "default": True,
        "help": "If enabled, reuse connections where supported.",
    },
    "collect_telemetry": {
        "label": "Collect Telemetry Samples",
        "type": "bool",
        "default": True,
        "help": "If enabled, backend telemetry should be sampled.",
    },
    "store_artifacts": {
        "label": "Store Runner Artifacts",
        "type": "bool",
        "default": True,
        "help": "If enabled, stdout/stderr and runner outputs are stored.",
    },
}

COMMON_CONNECTION_FIELDS = {
    "connection_count": {
        "label": "Connection Count",
        "type": "select",
        "choices": [
            (10, "10"),
            (25, "25"),
            (50, "50"),
            (100, "100"),
            (200, "200"),
            (500, "500"),
            (1000, "1000"),
            (2000, "2000"),
        ],
        "default": 100,
        "help": "Number of simultaneous connections / sockets.",
    },
    "duration_seconds": {
        "label": "Attack Duration (seconds)",
        "type": "select",
        "choices": [
            (30, "30"),
            (60, "60"),
            (120, "120"),
            (180, "180"),
            (300, "300"),
            (600, "600"),
        ],
        "default": 120,
        "help": "Planned duration for the active attack phase.",
    },
    "request_timeout": {
        "label": "Socket / Read Timeout (seconds)",
        "type": "select",
        "choices": [
            (5, "5"),
            (10, "10"),
            (15, "15"),
            (30, "30"),
            (60, "60"),
            (120, "120"),
        ],
        "default": 15,
        "help": "Timeout applied to connection operations.",
    },
    "collect_telemetry": {
        "label": "Collect Telemetry Samples",
        "type": "bool",
        "default": True,
        "help": "If enabled, backend telemetry should be sampled.",
    },
    "store_artifacts": {
        "label": "Store Runner Artifacts",
        "type": "bool",
        "default": True,
        "help": "If enabled, stdout/stderr and runner outputs are stored.",
    },
}


def _merge_fields(*field_groups: Dict) -> Dict:
    merged = {}
    for group in field_groups:
        merged.update(deepcopy(group))
    return merged


_INTERNAL_DEFAULT_KEY = "__default__"


# ---------------------------------------------------------------------
# Main taxonomy
# ---------------------------------------------------------------------

TEST_TAXONOMY = {
    "TA1": {
        "meta": {
            "label": "TA1 - Volumetric Application-Layer Flood",
            "description": (
                "Volumetric application-layer flooding using the standard "
                "Locust-based profile. This test area has no user-visible subtype."
            ),
            "has_subtypes": False,
            "fixed_runner": "locust",
            "ui_hide_test_type": True,
        },

        _INTERNAL_DEFAULT_KEY: {
            "label": "Volumetric Application-Layer Flood",
            "runner_modes": ["locust"],
            "default_runner": "locust",
            "category": "volumetric_l7",
            "description": "Single TA1 volumetric flood definition.",
            "fields": _merge_fields(
                COMMON_HTTP_FIELDS,
                {
                    "rate_limit": {
                        "label": "Rate Limit (requests/sec)",
                        "type": "select",
                        "choices": [
                            (10, "10"),
                            (25, "25"),
                            (50, "50"),
                            (100, "100"),
                            (250, "250"),
                            (500, "500"),
                            (1000, "1000"),
                            (2000, "2000"),
                        ],
                        "default": 100,
                        "help": "Approximate request rate target.",
                    },
                },
            ),
        },
    },

    "TA2": {
        "meta": {
            "label": "TA2 - Protocol / Connection Abuse",
            "description": (
                "Tests focused on abusive connection handling, including "
                "SlowHTTPTest body/header variants and Slowloris."
            ),
            "has_subtypes": True,
            "fixed_runner": None,
            "ui_hide_test_type": False,
        },

        "SLOWHTTPTEST_BODY": {
            "label": "SlowHTTPTest - Body",
            "runner_modes": ["slowhttptest"],
            "default_runner": "slowhttptest",
            "category": "protocol_abuse",
            "description": "Open POST requests and drip-feed the body slowly.",
            "fields": _merge_fields(
                COMMON_CONNECTION_FIELDS,
                {
                    "payload_size": {
                        "label": "Declared Payload Size (bytes)",
                        "type": "select",
                        "choices": [
                            (1024, "1024"),
                            (4096, "4096"),
                            (8192, "8192"),
                            (16384, "16384"),
                            (32768, "32768"),
                            (65536, "65536"),
                        ],
                        "default": 8192,
                        "help": "Declared request body size to keep the server waiting.",
                    },
                    "think_time_ms": {
                        "label": "Chunk Delay (ms)",
                        "type": "select",
                        "choices": [
                            (250, "250"),
                            (500, "500"),
                            (1000, "1000"),
                            (2000, "2000"),
                            (5000, "5000"),
                        ],
                        "default": 1000,
                        "help": "Delay between partial body chunks.",
                    },
                },
            ),
        },

        "SLOWHTTPTEST_HEADER": {
            "label": "SlowHTTPTest - Header",
            "runner_modes": ["slowhttptest"],
            "default_runner": "slowhttptest",
            "category": "protocol_abuse",
            "description": "Send partial HTTP headers slowly to hold server resources.",
            "fields": _merge_fields(
                COMMON_CONNECTION_FIELDS,
                {
                    "header_count": {
                        "label": "Header Count",
                        "type": "select",
                        "choices": [
                            (5, "5"),
                            (10, "10"),
                            (20, "20"),
                            (30, "30"),
                            (50, "50"),
                            (100, "100"),
                        ],
                        "default": 20,
                        "help": "Number of headers / header fragments to trickle.",
                    },
                    "think_time_ms": {
                        "label": "Inter-Header Delay (ms)",
                        "type": "select",
                        "choices": [
                            (250, "250"),
                            (500, "500"),
                            (1000, "1000"),
                            (2000, "2000"),
                            (5000, "5000"),
                            (10000, "10000"),
                        ],
                        "default": 1000,
                        "help": "Delay between partial header sends.",
                    },
                    "keep_alive": {
                        "label": "Use Keep-Alive",
                        "type": "bool",
                        "default": True,
                        "help": "Attempt to keep sockets occupied for longer.",
                    },
                },
            ),
        },

        "SLOWLORIS": {
            "label": "Slowloris",
            "runner_modes": ["slowloris"],
            "default_runner": "slowloris",
            "category": "protocol_abuse",
            "description": "Many long-lived connections sending partial headers slowly.",
            "fields": _merge_fields(
                COMMON_CONNECTION_FIELDS,
                {
                    "header_count": {
                        "label": "Header Count",
                        "type": "select",
                        "choices": [
                            (5, "5"),
                            (10, "10"),
                            (20, "20"),
                            (30, "30"),
                            (50, "50"),
                            (100, "100"),
                        ],
                        "default": 20,
                        "help": "Number of headers / header fragments to trickle.",
                    },
                    "think_time_ms": {
                        "label": "Inter-Header Delay (ms)",
                        "type": "select",
                        "choices": [
                            (250, "250"),
                            (500, "500"),
                            (1000, "1000"),
                            (2000, "2000"),
                            (5000, "5000"),
                            (10000, "10000"),
                        ],
                        "default": 1000,
                        "help": "Delay between partial header sends.",
                    },
                    "keep_alive": {
                        "label": "Use Keep-Alive",
                        "type": "bool",
                        "default": True,
                        "help": "Attempt to keep sockets occupied for longer.",
                    },
                },
            ),
        },
    },

    "TA3": {
        "meta": {
            "label": "TA3 - Application Logic Abuse",
            "description": (
                "Application logic abuse focused on CPU- and database-intensive "
                "endpoints. This test area has no user-visible subtype."
            ),
            "has_subtypes": False,
            "fixed_runner": "locust",
            "ui_hide_test_type": True,
        },

        _INTERNAL_DEFAULT_KEY: {
            "label": "Application Logic Abuse",
            "runner_modes": ["locust"],
            "default_runner": "locust",
            "category": "application_logic_abuse",
            "description": "Single TA3 application logic abuse definition.",
            "fields": _merge_fields(
                COMMON_HTTP_FIELDS,
                {
                    "rate_limit": {
                        "label": "Rate Limit (requests/sec)",
                        "type": "select",
                        "choices": [
                            (5, "5"),
                            (10, "10"),
                            (25, "25"),
                            (50, "50"),
                            (100, "100"),
                            (250, "250"),
                        ],
                        "default": 25,
                        "help": "Approximate request rate target.",
                    },
                    "think_time_ms": {
                        "label": "Think Time (ms)",
                        "type": "select",
                        "choices": [
                            (0, "0"),
                            (50, "50"),
                            (100, "100"),
                            (250, "250"),
                            (500, "500"),
                        ],
                        "default": 0,
                        "help": "Delay between task iterations.",
                    },
                },
            ),
        },
    },

    "TA4": {
        "meta": {
            "label": "TA4 - Endpoint / API Service Abuse",
            "description": (
                "Endpoint or service misuse with the two supported TA4 profiles."
            ),
            "has_subtypes": True,
            "fixed_runner": None,
            "ui_hide_test_type": False,
        },

        "CURL_BURST": {
            "label": "CURL_BURST",
            "runner_modes": ["curl"],
            "default_runner": "curl",
            "category": "endpoint_service_abuse",
            "description": "Burst-style unauthenticated endpoint or API abuse using curl.",
            "fields": _merge_fields(
                COMMON_HTTP_FIELDS,
                {
                    "rate_limit": {
                        "label": "Rate Limit (requests/sec)",
                        "type": "select",
                        "choices": [
                            (10, "10"),
                            (25, "25"),
                            (50, "50"),
                            (100, "100"),
                            (250, "250"),
                            (500, "500"),
                        ],
                        "default": 50,
                        "help": "Approximate request rate target.",
                    },
                },
            ),
        },

        "CURL_BURST_PIDSTAT": {
            "label": "CURL_BURST_PIDSTAT",
            "runner_modes": ["curl_pidstat"],
            "default_runner": "curl_pidstat",
            "category": "endpoint_service_abuse",
            "description": "Burst-style abuse using curl with pidstat resource monitoring.",
            "fields": _merge_fields(
                COMMON_HTTP_FIELDS,
                {
                    "rate_limit": {
                        "label": "Rate Limit (requests/sec)",
                        "type": "select",
                        "choices": [
                            (10, "10"),
                            (25, "25"),
                            (50, "50"),
                            (100, "100"),
                            (250, "250"),
                            (500, "500"),
                        ],
                        "default": 50,
                        "help": "Approximate request rate target.",
                    },
                },
            ),
        },
    },

    "TA5": {
        "meta": {
            "label": "TA5 - Adaptive / Custom Flood",
            "description": (
                "Custom Python-based application-layer flooding using one of the "
                "two supported runner families."
            ),
            "has_subtypes": True,
            "fixed_runner": None,
            "ui_hide_test_type": False,
        },

        "ASYNC_FLOOD": {
            "label": "Async Floods",
            "runner_modes": ["python_async"],
            "default_runner": "python_async",
            "category": "adaptive_flood",
            "description": "AsyncIO-based Python flooding.",
            "fields": _merge_fields(
                COMMON_HTTP_FIELDS,
                {
                    "users": {
                        "label": "Coroutine Count",
                        "type": "select",
                        "choices": [
                            (10, "10"),
                            (25, "25"),
                            (50, "50"),
                            (100, "100"),
                            (200, "200"),
                            (500, "500"),
                            (1000, "1000"),
                        ],
                        "default": 100,
                        "help": "Number of concurrent coroutine workers.",
                    },
                    "rate_limit": {
                        "label": "Rate Limit (requests/sec)",
                        "type": "select",
                        "choices": [
                            (10, "10"),
                            (25, "25"),
                            (50, "50"),
                            (100, "100"),
                            (250, "250"),
                            (500, "500"),
                            (1000, "1000"),
                        ],
                        "default": 100,
                        "help": "Approximate request rate target.",
                    },
                },
            ),
        },

        "REQUESTS_FLOOD": {
            "label": "Requests Floods",
            "runner_modes": ["python_requests"],
            "default_runner": "python_requests",
            "category": "adaptive_flood",
            "description": "Requests-based Python flooding.",
            "fields": _merge_fields(
                COMMON_HTTP_FIELDS,
                {
                    "users": {
                        "label": "Thread / Worker Count",
                        "type": "select",
                        "choices": [
                            (1, "1"),
                            (5, "5"),
                            (10, "10"),
                            (25, "25"),
                            (50, "50"),
                            (100, "100"),
                            (200, "200"),
                            (300, "300"),
                        ],
                        "default": 25,
                        "help": "Number of worker threads used by the requests-based runner.",
                    },
                    "rate_limit": {
                        "label": "Rate Limit (requests/sec)",
                        "type": "select",
                        "choices": [
                            (10, "10"),
                            (25, "25"),
                            (50, "50"),
                            (100, "100"),
                            (250, "250"),
                            (500, "500"),
                        ],
                        "default": 50,
                        "help": "Approximate request rate target.",
                    },
                },
            ),
        },
    },
}


# ---------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------

def _visible_subtype_items(area: str) -> List[Tuple[str, Dict]]:
    area_data = TEST_TAXONOMY.get(area, {})
    items = []

    for key, value in area_data.items():
        if key == "meta":
            continue
        if key == _INTERNAL_DEFAULT_KEY:
            continue
        items.append((key, value))

    return items


def area_choices() -> List[Tuple[str, str]]:
    choices = []
    for area_code, area_data in TEST_TAXONOMY.items():
        meta = area_data.get("meta", {})
        choices.append((area_code, meta.get("label", area_code)))
    return choices


def area_has_subtypes(area: str) -> bool:
    meta = TEST_TAXONOMY.get(area, {}).get("meta", {})
    return bool(meta.get("has_subtypes", False))


def internal_test_type_for_area(area: str, test_type: Optional[str] = None) -> Optional[str]:
    """
    Resolve the subtype key to use internally.

    - For TA1 / TA3, returns '__default__'
    - For other areas, returns the provided test_type
    """
    area_data = TEST_TAXONOMY.get(area, {})
    if not area_data:
        return None

    meta = area_data.get("meta", {})
    if not meta.get("has_subtypes", False):
        return _INTERNAL_DEFAULT_KEY

    return test_type


def test_types_for_area(area: str) -> List[Tuple[str, str]]:
    """
    Return dropdown choices for subtypes within a given area.

    For TA1 / TA3 this correctly returns an empty list,
    because those areas have no visible subtype.
    """
    area_data = TEST_TAXONOMY.get(area, {})
    meta = area_data.get("meta", {})

    if not meta.get("has_subtypes", False):
        return []

    return [(key, value.get("label", key)) for key, value in _visible_subtype_items(area)]


def get_area_meta(area: str) -> Dict:
    return deepcopy(TEST_TAXONOMY.get(area, {}).get("meta", {}))


def get_test_spec(area: str, test_type: Optional[str]) -> Dict:
    resolved_type = internal_test_type_for_area(area, test_type)
    return deepcopy(TEST_TAXONOMY.get(area, {}).get(resolved_type, {}))


def get_test_fields(area: str, test_type: Optional[str]) -> Dict:
    spec = get_test_spec(area, test_type)
    return deepcopy(spec.get("fields", {}))


def allowed_runner_modes(area: str, test_type: Optional[str]) -> List[str]:
    spec = get_test_spec(area, test_type)
    return list(spec.get("runner_modes", []))


def default_runner_mode(area: str, test_type: Optional[str]) -> str:
    spec = get_test_spec(area, test_type)
    return spec.get("default_runner", "framework")


def all_supported_field_names() -> List[str]:
    names = set()

    for area_code, area_data in TEST_TAXONOMY.items():
        for subtype, spec in area_data.items():
            if subtype == "meta":
                continue
            fields = spec.get("fields", {})
            names.update(fields.keys())

    return sorted(names)


def validate_taxonomy() -> List[str]:
    problems = []

    for area_code, area_data in TEST_TAXONOMY.items():
        meta = area_data.get("meta")
        if not meta:
            problems.append(f"{area_code}: missing meta section")
            continue

        has_subtypes = bool(meta.get("has_subtypes", False))

        if has_subtypes:
            visible_items = _visible_subtype_items(area_code)
            if not visible_items:
                problems.append(f"{area_code}: marked has_subtypes=True but no visible subtypes found")
        else:
            if _INTERNAL_DEFAULT_KEY not in area_data:
                problems.append(f"{area_code}: missing internal default subtype '{_INTERNAL_DEFAULT_KEY}'")

        for subtype, spec in area_data.items():
            if subtype == "meta":
                continue

            if "label" not in spec:
                problems.append(f"{area_code}/{subtype}: missing label")

            if "fields" not in spec:
                problems.append(f"{area_code}/{subtype}: missing fields")

            for field_name, field_meta in spec.get("fields", {}).items():
                field_type = field_meta.get("type")
                if field_type not in {"select", "bool"}:
                    problems.append(
                        f"{area_code}/{subtype}/{field_name}: unsupported type '{field_type}'"
                    )

                if field_type == "select" and "choices" not in field_meta:
                    problems.append(
                        f"{area_code}/{subtype}/{field_name}: select field missing choices"
                    )

    return problems


# ---------------------------------------------------------------------
# Optional manual test
# ---------------------------------------------------------------------

if __name__ == "__main__":
    print("Area choices:")
    for item in area_choices():
        print("  ", item)

    print("\nTA1 visible subtypes:")
    for item in test_types_for_area("TA1"):
        print("  ", item)

    print("\nTA2 visible subtypes:")
    for item in test_types_for_area("TA2"):
        print("  ", item)

    print("\nAll supported field names:")
    for name in all_supported_field_names():
        print("  ", name)

    issues = validate_taxonomy()
    print("\nValidation issues:")
    if not issues:
        print("  None")
    else:
        for issue in issues:
            print("  ", issue)