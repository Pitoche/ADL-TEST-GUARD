"""
app/services/test_taxonomy.py

High-level taxonomy for the ADL-TEST-GUARD testing area.

Design goals:
- Keep a clean mapping of Test Area -> Subtype -> metadata
- Expose helper functions for UI dropdowns
- Provide field definitions for form rendering / parameter extraction
- Stay compatible with the current routes.py implementation, where:
    TEST_TAXONOMY[area][test_type]["fields"]
  is expected, and each field has a "type" such as "select" or "bool"

Important compatibility note:
Your current routes.py only auto-reads fields with:
- meta["type"] == "select"
- meta["type"] == "bool"

So this starter taxonomy mainly uses:
- "select" for numeric / selectable values
- "bool" for toggles

Later, if you expand routes.py, you can also add support for:
- text
- string
- float
- list
"""

from copy import deepcopy
from typing import Dict, List, Tuple


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
    """
    Merge dictionaries of field definitions into a fresh dict.
    Later groups override earlier groups if keys overlap.
    """
    merged = {}
    for group in field_groups:
        merged.update(deepcopy(group))
    return merged


# ---------------------------------------------------------------------
# Main taxonomy
# ---------------------------------------------------------------------

TEST_TAXONOMY = {
    "TA1": {
        "meta": {
            "label": "TA1 - Volumetric Application-Layer Flood",
            "description": (
                "High-volume application-layer request floods intended to "
                "degrade or exhaust web-facing application resources."
            ),
        },

        "HTTP_GET_FLOOD": {
            "label": "HTTP GET Flood",
            "runner_modes": ["framework", "custom"],
            "default_runner": "framework",
            "category": "volumetric_l7",
            "description": (
                "High-rate GET requests against one or more endpoints."
            ),
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

        "HTTP_POST_FLOOD": {
            "label": "HTTP POST Flood",
            "runner_modes": ["framework", "custom"],
            "default_runner": "framework",
            "category": "volumetric_l7",
            "description": (
                "High-rate POST requests, optionally with payload stress."
            ),
            "fields": _merge_fields(
                COMMON_HTTP_FIELDS,
                {
                    "payload_size": {
                        "label": "Payload Size (bytes)",
                        "type": "select",
                        "choices": [
                            (128, "128"),
                            (256, "256"),
                            (512, "512"),
                            (1024, "1024"),
                            (2048, "2048"),
                            (4096, "4096"),
                            (8192, "8192"),
                            (16384, "16384"),
                        ],
                        "default": 512,
                        "help": "Approximate request payload size.",
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
                        "default": 50,
                        "help": "Approximate request rate target.",
                    },
                },
            ),
        },

        "MIXED_ENDPOINT_FLOOD": {
            "label": "Mixed Endpoint Flood",
            "runner_modes": ["framework", "custom"],
            "default_runner": "framework",
            "category": "volumetric_l7",
            "description": (
                "Flood across multiple endpoints to imitate broader user traffic."
            ),
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
                        ],
                        "default": 100,
                        "help": "Approximate request rate target.",
                    },
                    "randomize_endpoints": {
                        "label": "Randomize Endpoint Selection",
                        "type": "bool",
                        "default": True,
                        "help": "Use random endpoint selection to vary request pattern.",
                    },
                },
            ),
        },
    },

    "TA2": {
        "meta": {
            "label": "TA2 - Protocol / Connection Abuse",
            "description": (
                "Tests focused on abusive connection handling, slow headers, "
                "slow body delivery, or prolonged socket occupancy."
            ),
        },

        "SLOWLORIS": {
            "label": "Slowloris / Slow Headers",
            "runner_modes": ["custom"],
            "default_runner": "custom",
            "category": "protocol_abuse",
            "description": (
                "Many long-lived connections sending partial headers slowly."
            ),
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

        "SLOW_POST": {
            "label": "Slow POST / Slow Body",
            "runner_modes": ["custom"],
            "default_runner": "custom",
            "category": "protocol_abuse",
            "description": (
                "Open POST requests and drip-feed the body slowly."
            ),
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

        "KEEPALIVE_HOLD": {
            "label": "Keep-Alive Connection Hold",
            "runner_modes": ["custom"],
            "default_runner": "custom",
            "category": "protocol_abuse",
            "description": (
                "Occupy and hold many idle or semi-idle keep-alive connections."
            ),
            "fields": _merge_fields(
                COMMON_CONNECTION_FIELDS,
                {
                    "think_time_ms": {
                        "label": "Idle Hold Interval (ms)",
                        "type": "select",
                        "choices": [
                            (500, "500"),
                            (1000, "1000"),
                            (2000, "2000"),
                            (5000, "5000"),
                            (10000, "10000"),
                        ],
                        "default": 2000,
                        "help": "Hold interval between occasional keep-alive activity.",
                    },
                    "keep_alive": {
                        "label": "Use Keep-Alive",
                        "type": "bool",
                        "default": True,
                        "help": "Keep the connection open where supported.",
                    },
                },
            ),
        },
    },

    "TA3": {
        "meta": {
            "label": "TA3 - Application Logic Abuse",
            "description": (
                "Tests focused on expensive application operations such as "
                "CPU-heavy routes, search, reporting, or database-intensive logic."
            ),
        },

        "CPU_HEAVY_ENDPOINT": {
            "label": "CPU-Heavy Endpoint Abuse",
            "runner_modes": ["framework", "custom"],
            "default_runner": "framework",
            "category": "application_logic_abuse",
            "description": (
                "Repeated requests to endpoints that trigger expensive CPU logic."
            ),
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

        "DB_HEAVY_QUERY": {
            "label": "Database-Heavy Query Abuse",
            "runner_modes": ["framework", "custom"],
            "default_runner": "framework",
            "category": "application_logic_abuse",
            "description": (
                "Repeated access to database-intensive search/reporting endpoints."
            ),
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
                        ],
                        "default": 20,
                        "help": "Approximate request rate target.",
                    },
                    "randomize_endpoints": {
                        "label": "Randomize Endpoint Selection",
                        "type": "bool",
                        "default": True,
                        "help": "Distribute requests across several DB-heavy endpoints.",
                    },
                },
            ),
        },

        "AUTH_WORKFLOW_ABUSE": {
            "label": "Authentication / Session Workflow Abuse",
            "runner_modes": ["framework", "custom"],
            "default_runner": "framework",
            "category": "application_logic_abuse",
            "description": (
                "Repeated login/session-related activity to stress auth workflows."
            ),
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
                        ],
                        "default": 25,
                        "help": "Approximate request rate target.",
                    },
                    "follow_redirects": {
                        "label": "Follow Redirects",
                        "type": "bool",
                        "default": True,
                        "help": "Useful where auth flows involve redirects.",
                    },
                },
            ),
        },
    },

    "TA4": {
        "meta": {
            "label": "TA4 - Endpoint / API Service Abuse",
            "description": (
                "Misuse of exposed but weakly protected endpoints or APIs, "
                "especially unauthenticated or low-cost-to-client services."
            ),
        },

        "UNAUTHENTICATED_API_ABUSE": {
            "label": "Unauthenticated API Abuse",
            "runner_modes": ["framework", "custom"],
            "default_runner": "framework",
            "category": "endpoint_service_abuse",
            "description": (
                "Repeated use of public or insufficiently protected API routes."
            ),
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

        "FILE_EXPORT_ABUSE": {
            "label": "File Export / Report Abuse",
            "runner_modes": ["framework", "custom"],
            "default_runner": "framework",
            "category": "endpoint_service_abuse",
            "description": (
                "Repeated use of file export or report-generation endpoints."
            ),
            "fields": _merge_fields(
                COMMON_HTTP_FIELDS,
                {
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
                        ],
                        "default": 10,
                        "help": "Number of concurrent workers / virtual users.",
                    },
                    "rate_limit": {
                        "label": "Rate Limit (requests/sec)",
                        "type": "select",
                        "choices": [
                            (1, "1"),
                            (5, "5"),
                            (10, "10"),
                            (25, "25"),
                            (50, "50"),
                        ],
                        "default": 10,
                        "help": "Approximate request rate target for expensive exports.",
                    },
                    "payload_size": {
                        "label": "Request Payload Size (bytes)",
                        "type": "select",
                        "choices": [
                            (128, "128"),
                            (256, "256"),
                            (512, "512"),
                            (1024, "1024"),
                            (2048, "2048"),
                        ],
                        "default": 256,
                        "help": "Optional body size if POST-based export APIs are used.",
                    },
                },
            ),
        },

        "SEARCH_FILTER_ABUSE": {
            "label": "Search / Filter Abuse",
            "runner_modes": ["framework", "custom"],
            "default_runner": "framework",
            "category": "endpoint_service_abuse",
            "description": (
                "Repeated heavy search/filter combinations targeting service inefficiency."
            ),
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
                        ],
                        "default": 25,
                        "help": "Approximate request rate target.",
                    },
                    "randomize_endpoints": {
                        "label": "Randomize Endpoint Selection",
                        "type": "bool",
                        "default": True,
                        "help": "Rotate search targets / filter combinations where applicable.",
                    },
                },
            ),
        },
    },

    "TA5": {
        "meta": {
            "label": "TA5 - Adaptive / Custom Flood",
            "description": (
                "Adaptive or hybrid application-layer flooding intended to vary "
                "request behavior and compare framework vs custom execution styles."
            ),
        },

        "ADAPTIVE_HTTP_FLOOD": {
            "label": "Adaptive HTTP Flood",
            "runner_modes": ["custom", "framework"],
            "default_runner": "custom",
            "category": "adaptive_flood",
            "description": (
                "Adaptive request generation that can vary rates, endpoints, or timing."
            ),
            "fields": _merge_fields(
                COMMON_HTTP_FIELDS,
                {
                    "rate_limit": {
                        "label": "Base Rate Limit (requests/sec)",
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
                        "help": "Base request rate before adaptive behavior applies.",
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
                            (1000, "1000"),
                        ],
                        "default": 100,
                        "help": "Delay used to vary timing between requests.",
                    },
                    "randomize_endpoints": {
                        "label": "Randomize Endpoint Selection",
                        "type": "bool",
                        "default": True,
                        "help": "Rotate among endpoints to reduce obvious regularity.",
                    },
                },
            ),
        },

        "THREADED_PYTHON_FLOOD": {
            "label": "Threaded Python Flood",
            "runner_modes": ["custom"],
            "default_runner": "custom",
            "category": "adaptive_flood",
            "description": (
                "Thread-based custom Python runner for comparative experimentation."
            ),
            "fields": _merge_fields(
                COMMON_HTTP_FIELDS,
                {
                    "users": {
                        "label": "Thread Count",
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
                        "help": "Number of worker threads used by the custom runner.",
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
                        ],
                        "default": 50,
                        "help": "Approximate request rate target.",
                    },
                },
            ),
        },

        "ASYNCIO_PYTHON_FLOOD": {
            "label": "AsyncIO Python Flood",
            "runner_modes": ["custom"],
            "default_runner": "custom",
            "category": "adaptive_flood",
            "description": (
                "AsyncIO-based custom Python runner for high-concurrency experiments."
            ),
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
    },
}


# ---------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------

def area_choices() -> List[Tuple[str, str]]:
    """
    Return dropdown choices for test areas.
    """
    choices = []
    for area_code, area_data in TEST_TAXONOMY.items():
        meta = area_data.get("meta", {})
        choices.append((area_code, meta.get("label", area_code)))
    return choices


def test_types_for_area(area: str) -> List[Tuple[str, str]]:
    """
    Return dropdown choices for subtypes within a given area.

    Example return:
        [("HTTP_GET_FLOOD", "HTTP GET Flood"), ...]
    """
    area_data = TEST_TAXONOMY.get(area, {})
    choices = []

    for key, value in area_data.items():
        if key == "meta":
            continue
        choices.append((key, value.get("label", key)))

    return choices


def get_area_meta(area: str) -> Dict:
    """
    Return metadata for a test area.
    """
    return deepcopy(TEST_TAXONOMY.get(area, {}).get("meta", {}))


def get_test_spec(area: str, test_type: str) -> Dict:
    """
    Return the full spec for a given area + subtype.
    """
    return deepcopy(TEST_TAXONOMY.get(area, {}).get(test_type, {}))


def get_test_fields(area: str, test_type: str) -> Dict:
    """
    Return only the field definitions for a given area + subtype.
    """
    spec = TEST_TAXONOMY.get(area, {}).get(test_type, {})
    return deepcopy(spec.get("fields", {}))


def allowed_runner_modes(area: str, test_type: str) -> List[str]:
    """
    Return allowed runner modes for a subtype.
    """
    spec = TEST_TAXONOMY.get(area, {}).get(test_type, {})
    return list(spec.get("runner_modes", []))


def default_runner_mode(area: str, test_type: str) -> str:
    """
    Return the preferred default runner for a subtype.
    """
    spec = TEST_TAXONOMY.get(area, {}).get(test_type, {})
    return spec.get("default_runner", "framework")


def all_supported_field_names() -> List[str]:
    """
    Return a sorted list of all field names referenced anywhere
    in the taxonomy. Useful to compare against forms.py.
    """
    names = set()

    for area_code, area_data in TEST_TAXONOMY.items():
        for subtype, spec in area_data.items():
            if subtype == "meta":
                continue
            fields = spec.get("fields", {})
            names.update(fields.keys())

    return sorted(names)


def validate_taxonomy() -> List[str]:
    """
    Perform lightweight internal checks and return a list of problems.
    Empty list means the taxonomy looks structurally OK.
    """
    problems = []

    for area_code, area_data in TEST_TAXONOMY.items():
        if "meta" not in area_data:
            problems.append(f"{area_code}: missing meta section")

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

    print("\nTA1 subtypes:")
    for item in test_types_for_area("TA1"):
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