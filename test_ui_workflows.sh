#!/usr/bin/env bash

BASE="http://127.0.0.1:5000"

echo "Checking dashboard..."
curl -fsS "$BASE/tests/dashboard" >/dev/null && echo "OK dashboard" || echo "FAIL dashboard"

echo "Checking new test page..."
curl -fsS "$BASE/tests/new" >/dev/null && echo "OK new test page" || echo "FAIL new test page"

echo "Checking TA subtype endpoint..."
curl -fsS "$BASE/tests/subtypes/TA4" && echo

echo "Checking TA spec endpoint..."
curl -fsS "$BASE/tests/spec/TA4/CURL_BURST_PIDSTAT" && echo

echo "Checking validation..."
curl -fsS -X POST "$BASE/tests/validate" \
  -H "Content-Type: application/json" \
  -d '{
    "test_area": "TA4",
    "test_type": "CURL_BURST_PIDSTAT",
    "runner_mode": "curl_pidstat",
    "target_config": {
      "protocol": "http",
      "host": "192.168.42.8",
      "port": 5000,
      "endpoints": ["/"]
    },
    "parameters": {
      "level": "baseline",
      "request_timeout": 10
    }
  }'
echo
