#!/usr/bin/env bash
# BASELINE — Single-request control (no burst)
# Test 5: Application-Layer Service-Abuse DoS (L7)

BASE="http://192.168.42.8:5000"
OUT="$HOME/ADL-TEST-GUARD/reports-area"
mkdir -p "$OUT"

LOG="$OUT/service_abuse_baseline.csv"
echo "timestamp,endpoint,http_code,time_total" > "$LOG"

ENDPOINTS=(
  "/view_projects"
  "/historical-data"
  "/reports"
)

for ep in "${ENDPOINTS[@]}"; do
  echo "Baseline testing $ep"
  for i in {1..10}; do
    curl -s -o /dev/null \
      -w "$(date +%s),$ep,%{http_code},%{time_total}\n" \
      "$BASE$ep" >> "$LOG"
    sleep 2
  done
done

echo "✅ Baseline complete: $LOG"

