#!/usr/bin/env bash
# Test 5 — Application-Layer Service-Abuse DoS (L7)
# Endpoint: /view_projects
# Client: Kali (cURL bursts)
# Server monitoring: Ubuntu (pidstat via SSH)
# Final reports consolidated in Kali reports-area

set -euo pipefail

############################
# Configuration
############################

# Target application
BASE_URL="http://192.168.42.8:5000"
TARGET_SSH="angel@192.168.42.8"

# Kali reports directory (FINAL destination)
KALI_REPORTS="$HOME/ADL-TEST-GUARD/reports-area"
mkdir -p "$KALI_REPORTS"

# Burst tuning (safe but effective)
BURSTS=20
BURST_SIZE=40
PARALLEL=10
SLEEP_BETWEEN=1

############################
# Timestamped filenames
############################

TS="$(date +%Y%m%d_%H%M%S)"

CLIENT_LOG="$KALI_REPORTS/service_abuse_view_projects_${TS}.csv"
SERVER_LOG_REMOTE="/tmp/service_abuse_view_projects_pidstat_${TS}.log"
SERVER_PIDFILE="/tmp/pidstat_service_abuse_${TS}.pid"
SERVER_LOG_LOCAL="$KALI_REPORTS/service_abuse_view_projects_pidstat_${TS}.log"

############################
# Client-side CSV header
############################

echo "timestamp,endpoint,http_code,time_total" > "$CLIENT_LOG"

############################
# Start pidstat on server
############################

echo "▶ Starting pidstat on Ubuntu server (user: angel)"

ssh "$TARGET_SSH" "
  nohup pidstat -u -r -d -h 1 > '$SERVER_LOG_REMOTE' 2>&1 &
  echo \$! > '$SERVER_PIDFILE'
"

sleep 2

############################
# Launch service-abuse bursts
############################

echo "▶ Launching service-abuse bursts against /view_projects"
echo "   BURSTS=$BURSTS  BURST_SIZE=$BURST_SIZE  PARALLEL=$PARALLEL"

for b in $(seq 1 "$BURSTS"); do
  for i in $(seq 1 "$BURST_SIZE"); do
    {
      curl -s -o /dev/null \
        -w "$(date +%s),/view_projects,%{http_code},%{time_total}\n" \
        "$BASE_URL/view_projects"
    } &
    (( i % PARALLEL == 0 )) && wait
  done
  wait
  sleep "$SLEEP_BETWEEN"
done

############################
# Stop pidstat on server
############################

echo "▶ Stopping pidstat on Ubuntu server"

ssh "$TARGET_SSH" "
  kill \$(cat '$SERVER_PIDFILE') 2>/dev/null || true
"

############################
# Copy server log to Kali
############################

echo "▶ Copying server pidstat log to Kali reports-area"

scp "$TARGET_SSH:$SERVER_LOG_REMOTE" "$SERVER_LOG_LOCAL"

############################
# Final summary
############################

echo "✅ Service-Abuse test completed"
echo "• Client log : $CLIENT_LOG"
echo "• Server log : $SERVER_LOG_LOCAL"
