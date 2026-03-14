#!/bin/bash
set -euo pipefail

ROOT_DIR=$(cd "$(dirname "$0")/../../.." && pwd)
JMETER_PLAN="$ROOT_DIR/test-area/jmeter-tests/test-plans/baseline.jmx"
REPORT_DIR="$ROOT_DIR/reports-area/jmeter/baseline"

mkdir -p "$REPORT_DIR"

jmeter -n \
  -t "$JMETER_PLAN" \
  -l "$REPORT_DIR/results.jtl" \
  -Jtarget_host=192.168.42.8 \
  -Jtarget_port=5000 \
  -Jscenario=jmeter_baseline \
  -Jusers=1 \
  -Jramp=10 \
  -Jduration=120 \
  -Jconnect_timeout=5000 \
  -Jresponse_timeout=15000
