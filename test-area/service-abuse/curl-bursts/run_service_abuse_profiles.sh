#!/usr/bin/env bash
# ------------------------------------------------------------
# ADL-TEST-GUARD — Service Abuse (cURL Bursts) Profile Runner
# ------------------------------------------------------------
# Profiles:
#   baseline | light | medium | full
#
# What it does:
#   - Baseline: slow single requests across a small endpoint set
#   - Light/Medium/Full: burst load against /view_projects
#   - Optional: remote pidstat capture via SSH + copy log back to Kali
#
# Outputs (Kali):
#   ~/ADL-TEST-GUARD/reports-area/service-abuse/
#     service_abuse_<profile>_<target>_<timestamp>_client.csv
#     service_abuse_<profile>_<target>_<timestamp>_meta.txt
#     service_abuse_<profile>_<target>_<timestamp>_pidstat.log   (if enabled)
#
# Examples:
#   ./run_service_abuse_profiles.sh baseline
#   ./run_service_abuse_profiles.sh light
#   ./run_service_abuse_profiles.sh full --pidstat
#   ./run_service_abuse_profiles.sh medium --base http://192.168.42.8:5000 --ssh angel@192.168.42.8 --pidstat
# ------------------------------------------------------------

set -euo pipefail

# -------------------------
# Defaults (match your lab)
# -------------------------
BASE_URL_DEFAULT="http://192.168.42.8:5000"
TARGET_SSH_DEFAULT="angel@192.168.42.8"

REPORTS_DIR="$HOME/ADL-TEST-GUARD/reports-area/service-abuse"

# Baseline endpoints (from your baseline script) :contentReference[oaicite:3]{index=3}
BASELINE_ENDPOINTS=(
  "/view_projects"
  "/historical-data"
  "/reports"
)

# -------------------------
# Profiles
# -------------------------
# Burst tuning derived from your burst scripts :contentReference[oaicite:4]{index=4} :contentReference[oaicite:5]{index=5}
# You can tune these later after one dry run.
profile_params() {
  local profile="$1"
  case "$profile" in
    baseline)
      # Baseline "control": 10 requests per endpoint, 2s pause
      BASELINE_REPS=10
      BASELINE_SLEEP=2
      # No burst values used
      BURSTS=0; BURST_SIZE=0; PARALLEL=0; SLEEP_BETWEEN=0
      ;;
    light)
      BURSTS=10
      BURST_SIZE=20
      PARALLEL=5
      SLEEP_BETWEEN=1
      ;;
    medium)
      BURSTS=20
      BURST_SIZE=40
      PARALLEL=10
      SLEEP_BETWEEN=1
      ;;
    full)
      BURSTS=30
      BURST_SIZE=60
      PARALLEL=15
      SLEEP_BETWEEN=1
      ;;
    *)
      echo "Unknown profile: $profile" >&2
      exit 1
      ;;
  esac
}

usage() {
  cat <<EOF
Usage:
  $0 {baseline|light|medium|full} [--base URL] [--ssh user@host] [--pidstat]

Options:
  --base     Target base URL (default: $BASE_URL_DEFAULT)
  --ssh      SSH target for pidstat (default: $TARGET_SSH_DEFAULT)
  --pidstat  Enable server-side pidstat capture + scp back to Kali

Examples:
  $0 baseline
  $0 light
  $0 medium --pidstat
  $0 full --base http://192.168.42.8:5000 --ssh angel@192.168.42.8 --pidstat
EOF
}

need_cmd() {
  command -v "$1" >/dev/null 2>&1 || { echo "Missing required command: $1" >&2; exit 1; }
}

safe_target_tag() {
  # Turn http://192.168.42.8:5000 -> 192_168_42_8_5000
  echo "$1" | sed -e 's|https\?://||' -e 's|/||g' -e 's|:|_|g' -e 's|\.|_|g'
}

# -------------------------
# Parse args
# -------------------------
if [[ $# -lt 1 ]]; then usage; exit 1; fi

PROFILE="$1"; shift

BASE_URL="$BASE_URL_DEFAULT"
TARGET_SSH="$TARGET_SSH_DEFAULT"
ENABLE_PIDSTAT="no"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --base) BASE_URL="$2"; shift 2;;
    --ssh) TARGET_SSH="$2"; shift 2;;
    --pidstat) ENABLE_PIDSTAT="yes"; shift;;
    -h|--help) usage; exit 0;;
    *) echo "Unknown option: $1" >&2; usage; exit 1;;
  esac
done

# -------------------------
# Checks
# -------------------------
need_cmd curl
need_cmd date

mkdir -p "$REPORTS_DIR"

# pidstat mode needs ssh + scp
if [[ "$ENABLE_PIDSTAT" == "yes" ]]; then
  need_cmd ssh
  need_cmd scp
fi

# Load profile params
profile_params "$PROFILE"

TS="$(date +%Y%m%d_%H%M%S)"
TARGET_TAG="$(safe_target_tag "$BASE_URL")"
RUN_TAG="service_abuse_${PROFILE}_${TARGET_TAG}_${TS}"

CLIENT_CSV="$REPORTS_DIR/${RUN_TAG}_client.csv"
META_TXT="$REPORTS_DIR/${RUN_TAG}_meta.txt"
PIDSTAT_LOCAL="$REPORTS_DIR/${RUN_TAG}_pidstat.log"

# Remote pidstat files (only used when enabled) :contentReference[oaicite:6]{index=6}
PIDSTAT_REMOTE_LOG="/tmp/${RUN_TAG}_pidstat.log"
PIDSTAT_REMOTE_PID="/tmp/${RUN_TAG}_pidstat.pid"

# -------------------------
# Write metadata
# -------------------------
{
  echo "run_tag=$RUN_TAG"
  echo "profile=$PROFILE"
  echo "base_url=$BASE_URL"
  echo "timestamp=$TS"
  echo "pidstat_enabled=$ENABLE_PIDSTAT"
  if [[ "$PROFILE" == "baseline" ]]; then
    echo "baseline_reps=$BASELINE_REPS"
    echo "baseline_sleep=$BASELINE_SLEEP"
    echo "baseline_endpoints=${BASELINE_ENDPOINTS[*]}"
  else
    echo "bursts=$BURSTS"
    echo "burst_size=$BURST_SIZE"
    echo "parallel=$PARALLEL"
    echo "sleep_between=$SLEEP_BETWEEN"
    echo "burst_endpoint=/view_projects"
  fi
  if [[ "$ENABLE_PIDSTAT" == "yes" ]]; then
    echo "target_ssh=$TARGET_SSH"
    echo "pidstat_remote_log=$PIDSTAT_REMOTE_LOG"
  fi
} > "$META_TXT"

# -------------------------
# CSV header
# -------------------------
echo "timestamp,endpoint,http_code,time_total" > "$CLIENT_CSV"

# -------------------------
# pidstat start (optional)
# -------------------------
start_pidstat() {
  echo "▶ Starting pidstat on server: $TARGET_SSH"
  ssh "$TARGET_SSH" "
    nohup pidstat -u -r -d -h 1 > '$PIDSTAT_REMOTE_LOG' 2>&1 &
    echo \$! > '$PIDSTAT_REMOTE_PID'
  "
  sleep 2
}

stop_pidstat() {
  echo "▶ Stopping pidstat on server"
  ssh "$TARGET_SSH" "
    kill \$(cat '$PIDSTAT_REMOTE_PID') 2>/dev/null || true
  "
}

fetch_pidstat() {
  echo "▶ Copying pidstat log back to Kali"
  scp "$TARGET_SSH:$PIDSTAT_REMOTE_LOG" "$PIDSTAT_LOCAL" >/dev/null
}

# -------------------------
# Baseline run
# -------------------------
run_baseline() {
  echo "▶ Running BASELINE (single requests, controlled pacing)"
  for ep in "${BASELINE_ENDPOINTS[@]}"; do
    echo "  • Baseline endpoint: $ep"
    for _ in $(seq 1 "$BASELINE_REPS"); do
      curl -s -o /dev/null \
        -w "$(date +%s),$ep,%{http_code},%{time_total}\n" \
        "$BASE_URL$ep" >> "$CLIENT_CSV"
      sleep "$BASELINE_SLEEP"
    done
  done
}

# -------------------------
# Burst run (light/medium/full)
# -------------------------
run_bursts() {
  echo "▶ Running BURSTS against /view_projects"
  echo "   BURSTS=$BURSTS  BURST_SIZE=$BURST_SIZE  PARALLEL=$PARALLEL  SLEEP_BETWEEN=$SLEEP_BETWEEN"

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

  # Append burst summary to meta
  {
    echo ""
    echo "summary_total_requests=$((BURSTS * BURST_SIZE))"
  } >> "$META_TXT"
}

# -------------------------
# Main
# -------------------------
echo "==================================================="
echo "ADL-TEST-GUARD — Service Abuse (cURL) Runner"
echo "Profile : $PROFILE"
echo "Target  : $BASE_URL"
echo "Reports : $REPORTS_DIR"
echo "Run tag : $RUN_TAG"
echo "Client  : $CLIENT_CSV"
echo "Meta    : $META_TXT"
if [[ "$ENABLE_PIDSTAT" == "yes" ]]; then
  echo "Pidstat : $PIDSTAT_LOCAL (copied from server)"
fi
echo "==================================================="

if [[ "$ENABLE_PIDSTAT" == "yes" ]]; then
  start_pidstat
fi

if [[ "$PROFILE" == "baseline" ]]; then
  run_baseline
else
  run_bursts
fi

if [[ "$ENABLE_PIDSTAT" == "yes" ]]; then
  stop_pidstat
  fetch_pidstat
fi

echo "✅ Completed"
echo "• Client CSV : $CLIENT_CSV"
echo "• Meta file  : $META_TXT"
if [[ "$ENABLE_PIDSTAT" == "yes" ]]; then
  echo "• Pidstat log : $PIDSTAT_LOCAL"
fi
