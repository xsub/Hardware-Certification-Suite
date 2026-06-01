#!/bin/bash

set -o pipefail

DURATION=${HCS_GPU_BURN_DURATION:-60}
MEMORY=${HCS_GPU_BURN_MEMORY:-90%}
DEVICES=${HCS_GPU_BURN_DEVICES:-}
USE_DOUBLES=${HCS_GPU_BURN_USE_DOUBLES:-false}
USE_TENSOR_CORES=${HCS_GPU_BURN_USE_TENSOR_CORES:-false}
TELEMETRY_INTERVAL=${HCS_GPU_BURN_TELEMETRY_INTERVAL:-5}
SOURCE_URL=${HCS_GPU_BURN_SOURCE_URL:-https://github.com/wilicc/gpu-burn.git}
SOURCE_REF=${HCS_GPU_BURN_SOURCE_REF:-master}
SOURCE_DIR=${HCS_GPU_BURN_SOURCE_DIR:-/tmp/gpu-burn}
BINARY=${HCS_GPU_BURN_BINARY:-${SOURCE_DIR}/gpu_burn}
BUILD_FROM_SOURCE=${HCS_GPU_BURN_BUILD_FROM_SOURCE:-true}
LOG_FILE=${HCS_GPU_BURN_LOG_FILE:-/tmp/gpu-burn.log}
TELEMETRY_FILE=${HCS_GPU_BURN_TELEMETRY_FILE:-/tmp/gpu-burn.nvidia-smi.csv}
RESULT_FILE=${HCS_GPU_BURN_RESULT_FILE:-/tmp/gpu-burn.result.json}
TELEMETRY_PID=""

mkdir -p "$(dirname "$LOG_FILE")" "$(dirname "$TELEMETRY_FILE")" "$(dirname "$RESULT_FILE")"
: >"$LOG_FILE"

function log() {
  printf '[%s] %s\n' "$(date -Is)" "$*" | tee -a "$LOG_FILE"
}

function json_string() {
  local value=${1-}
  if command -v python3 >/dev/null 2>&1; then
    python3 -c 'import json, sys; print(json.dumps(sys.argv[1]))' "$value"
  else
    printf '"%s"' "$(printf '%s' "$value" | sed 's/\\/\\\\/g; s/"/\\"/g')"
  fi
}

function write_result() {
  local status=$1
  local reason=$2
  local rc=$3
  cat >"$RESULT_FILE" <<EOF
{
  "schema_version": 1,
  "test_id": "gpu_burn",
  "status": $(json_string "$status"),
  "status_reason": $(json_string "$reason"),
  "return_code": $rc,
  "duration": $(json_string "$DURATION"),
  "memory": $(json_string "$MEMORY"),
  "devices": $(json_string "$DEVICES"),
  "binary": $(json_string "$BINARY"),
  "log_file": $(json_string "$LOG_FILE"),
  "telemetry_file": $(json_string "$TELEMETRY_FILE")
}
EOF
}

function is_true() {
  local value
  value=$(printf '%s' "$1" | tr '[:upper:]' '[:lower:]')
  case "$value" in
    1|true|yes|y|on) return 0 ;;
    *) return 1 ;;
  esac
}

function unsupported() {
  local reason=$1
  printf 'HCS_UNSUPPORTED: %s\n' "$reason" | tee -a "$LOG_FILE"
  write_result "unsupported" "$reason" 0
  exit 0
}

function fail() {
  local reason=$1
  local rc=${2:-1}
  log "HCS_FAILED: $reason"
  write_result "failed" "$reason" "$rc"
  exit "$rc"
}

function stop_telemetry() {
  if [ -n "$TELEMETRY_PID" ] && kill -0 "$TELEMETRY_PID" >/dev/null 2>&1; then
    kill "$TELEMETRY_PID" >/dev/null 2>&1 || true
    wait "$TELEMETRY_PID" >/dev/null 2>&1 || true
  fi
}

trap stop_telemetry EXIT

function start_telemetry() {
  if ! command -v nvidia-smi >/dev/null 2>&1; then
    return
  fi

  printf 'sample_time,index,name,uuid,temperature.gpu,power.draw,utilization.gpu,memory.used,memory.total,clocks.sm,clocks.mem\n' >"$TELEMETRY_FILE"
  (
    while true; do
      nvidia-smi \
        --query-gpu=timestamp,index,name,uuid,temperature.gpu,power.draw,utilization.gpu,memory.used,memory.total,clocks.sm,clocks.mem \
        --format=csv,noheader,nounits >>"$TELEMETRY_FILE" 2>>"$LOG_FILE" || true
      sleep "$TELEMETRY_INTERVAL"
    done
  ) &
  TELEMETRY_PID=$!
}

function ensure_nvidia_driver() {
  if ! command -v nvidia-smi >/dev/null 2>&1; then
    unsupported "nvidia-smi not found; NVIDIA driver/runtime is not installed"
  fi

  if ! nvidia-smi -L >>"$LOG_FILE" 2>&1; then
    unsupported "nvidia-smi cannot list GPUs; NVIDIA driver/runtime is not ready"
  fi

  if ! nvidia-smi --query-gpu=index,name,uuid,driver_version --format=csv,noheader >>"$LOG_FILE" 2>&1; then
    unsupported "nvidia-smi query failed; NVIDIA GPU is not ready"
  fi
}

function ensure_gpu_burn() {
  if [ -x "$BINARY" ]; then
    log "Using GPU Burn binary: $BINARY"
    return
  fi

  if ! is_true "$BUILD_FROM_SOURCE"; then
    fail "GPU Burn binary not found at $BINARY and source build is disabled" 2
  fi

  command -v git >/dev/null 2>&1 || fail "git is required to fetch GPU Burn" 2
  command -v make >/dev/null 2>&1 || fail "make is required to build GPU Burn" 2
  command -v nvcc >/dev/null 2>&1 || fail "nvcc is required to build GPU Burn from source" 2

  if [ ! -d "$SOURCE_DIR/.git" ]; then
    rm -rf "$SOURCE_DIR"
    log "Cloning GPU Burn from $SOURCE_URL ref $SOURCE_REF"
    if ! git clone --depth 1 --branch "$SOURCE_REF" "$SOURCE_URL" "$SOURCE_DIR" >>"$LOG_FILE" 2>&1; then
      log "Branch-specific clone failed; retrying default branch"
      git clone --depth 1 "$SOURCE_URL" "$SOURCE_DIR" >>"$LOG_FILE" 2>&1 || fail "failed to clone GPU Burn" 2
    fi
  fi

  log "Building GPU Burn in $SOURCE_DIR"
  make -C "$SOURCE_DIR" >>"$LOG_FILE" 2>&1 || fail "failed to build GPU Burn" 2

  if [ ! -x "$BINARY" ] && [ -x "$SOURCE_DIR/gpu_burn" ]; then
    BINARY="$SOURCE_DIR/gpu_burn"
  fi
  [ -x "$BINARY" ] || fail "GPU Burn binary was not produced at $BINARY" 2
}

ensure_nvidia_driver
ensure_gpu_burn

COMMAND=("$BINARY" "-m" "$MEMORY")
if [ -n "$DEVICES" ]; then
  COMMAND+=("-i" "$DEVICES")
fi
if is_true "$USE_DOUBLES"; then
  COMMAND+=("-d")
fi
if is_true "$USE_TENSOR_CORES"; then
  COMMAND+=("-tc")
fi
COMMAND+=("$DURATION")

log "Running GPU Burn: ${COMMAND[*]}"
start_telemetry
"${COMMAND[@]}" 2>&1 | tee -a "$LOG_FILE"
RC=${PIPESTATUS[0]}
stop_telemetry

if [ "$RC" -ne 0 ]; then
  fail "GPU Burn returned $RC" "$RC"
fi

write_result "passed" "ok" 0
log "GPU Burn completed successfully"
exit 0
