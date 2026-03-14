#!/bin/bash
set -euo pipefail

ROOT_DIR=$(cd "$(dirname "$0")/../../.." && pwd)
JMETER_PLAN="$ROOT_DIR/test-area/jmeter-tests/test-plans/abuse_medium.jmx"
REPORT_DIR="$ROOT_DIR/reports-area/jmeter/abuse_medium"

mkdir -p "$REPORT_DIR"

jmeter -n \
  -t "$JMETER_PLAN" \
  -l "$REPORT_DIR/results.jtl" \
  -e -o "$REPORT_DIR/html" \
  -Jtarget_host=192.168.42.8 \
  -Jtarget_port=5000 \
  -Jscenario=jmeter_abuse_medium \
  -Jusers=150 \
  -Jramp=60 \
  -Jduration=300 \
  -Jconnect_timeout=5000 \
  -Jresponse_timeout=15000
