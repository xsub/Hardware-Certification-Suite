#!/bin/bash

set -o pipefail

DURATION=${HCS_GPU_BURN_DURATION:-60}
MEMORY=${HCS_GPU_BURN_MEMORY:-90%}
DEVICES=${HCS_GPU_BURN_DEVICES:-}
USE_DOUBLES=${HCS_GPU_BURN_USE_DOUBLES:-false}
USE_TENSOR_CORES=${HCS_GPU_BURN_USE_TENSOR_CORES:-false}
TELEMETRY_INTERVAL=${HCS_GPU_BURN_TELEMETRY_INTERVAL:-5}
SNAP_PACKAGE=${HCS_GPU_BURN_SNAP_PACKAGE:-gpu-burn}
INSTALL_SNAP=${HCS_GPU_BURN_INSTALL_SNAP:-false}
REMOVE_SNAP_AFTER=${HCS_GPU_BURN_REMOVE_SNAP_AFTER:-false}
SOURCE_URL=${HCS_GPU_BURN_SOURCE_URL:-https://github.com/wilicc/gpu-burn.git}
# Pinned for reproducible certification evidence (upstream has no tags; this
# is master as of 2026-05-31). Override with gpu_burn_source_ref.
SOURCE_REF=${HCS_GPU_BURN_SOURCE_REF:-3ead140434da9473582b68452f7115967a7a0581}
SOURCE_DIR=${HCS_GPU_BURN_SOURCE_DIR:-/tmp/gpu-burn}
BINARY=${HCS_GPU_BURN_BINARY:-${SOURCE_DIR}/gpu_burn}
BUILD_FROM_SOURCE=${HCS_GPU_BURN_BUILD_FROM_SOURCE:-true}
LOG_FILE=${HCS_GPU_BURN_LOG_FILE:-/tmp/gpu-burn.log}
TELEMETRY_FILE=${HCS_GPU_BURN_TELEMETRY_FILE:-/tmp/gpu-burn.nvidia-smi.csv}
RESULT_FILE=${HCS_GPU_BURN_RESULT_FILE:-/tmp/gpu-burn.result.json}
TELEMETRY_PID=""
GPU_BURN_MODE=""
SNAP_INSTALLED_BY_HCS="false"

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
  "mode": $(json_string "$GPU_BURN_MODE"),
  "binary": $(json_string "$BINARY"),
  "source_ref": $(json_string "$SOURCE_REF"),
  "source_commit": $(json_string "$(git -C "$SOURCE_DIR" rev-parse HEAD 2>/dev/null || true)"),
  "snap_package": $(json_string "$SNAP_PACKAGE"),
  "snap_installed_by_hcs": $(json_string "$SNAP_INSTALLED_BY_HCS"),
  "snap_remove_after": $(json_string "$REMOVE_SNAP_AFTER"),
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

function almalinux_nvidia_hint() {
  local os_id=""
  local version_id=""
  local major=""

  if [ -r /etc/os-release ]; then
    # shellcheck disable=SC1091
    . /etc/os-release
    os_id=${ID:-}
    version_id=${VERSION_ID:-}
    major=${version_id%%.*}
  fi

  if [ "$os_id" = "almalinux" ] && { [ "$major" = "9" ] || [ "$major" = "10" ]; }; then
    printf '%s' "AlmaLinux ${version_id} has native NVIDIA packages: dnf install almalinux-release-nvidia-driver; dnf install nvidia-open-kmod nvidia-driver nvidia-driver-cuda; reboot or modprobe nvidia_drm; rerun gpu_burn"
    return
  fi

  printf '%s' "install NVIDIA drivers/runtime and confirm nvidia-smi before rerunning gpu_burn"
}

function fail() {
  local reason=$1
  local rc=${2:-1}
  log "HCS_FAILED: $reason"
  write_result "failed" "$reason" "$rc"
  exit "$rc"
}

function run_privileged() {
  if [ "$(id -u)" -eq 0 ]; then
    "$@"
    return
  fi

  if command -v sudo >/dev/null 2>&1; then
    sudo -n "$@"
    return
  fi

  return 127
}

function stop_telemetry() {
  if [ -n "$TELEMETRY_PID" ] && kill -0 "$TELEMETRY_PID" >/dev/null 2>&1; then
    kill "$TELEMETRY_PID" >/dev/null 2>&1 || true
    wait "$TELEMETRY_PID" >/dev/null 2>&1 || true
  fi
}

function remove_snap_if_requested() {
  if [ "$SNAP_INSTALLED_BY_HCS" != "true" ] || ! is_true "$REMOVE_SNAP_AFTER"; then
    return
  fi
  if ! command -v snap >/dev/null 2>&1; then
    return
  fi

  log "Removing snap package installed by HCS: $SNAP_PACKAGE"
  run_privileged snap remove "$SNAP_PACKAGE" >>"$LOG_FILE" 2>&1 || \
    log "WARNING: failed to remove snap package $SNAP_PACKAGE"
}

function cleanup() {
  stop_telemetry
  remove_snap_if_requested
}

trap cleanup EXIT

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
    unsupported "nvidia-smi not found; NVIDIA driver/runtime is not installed; $(almalinux_nvidia_hint)"
  fi

  if ! nvidia-smi -L >>"$LOG_FILE" 2>&1; then
    unsupported "nvidia-smi cannot list GPUs; NVIDIA driver/runtime is not ready; $(almalinux_nvidia_hint)"
  fi

  if ! nvidia-smi --query-gpu=index,name,uuid,driver_version --format=csv,noheader >>"$LOG_FILE" 2>&1; then
    unsupported "nvidia-smi query failed; NVIDIA GPU is not ready"
  fi
}

function ensure_gpu_burn() {
  if [ -x "$BINARY" ]; then
    GPU_BURN_MODE="binary"
    log "Using GPU Burn binary: $BINARY"
    return
  fi

  if command -v gpu-burn >/dev/null 2>&1; then
    BINARY=$(command -v gpu-burn)
    GPU_BURN_MODE="binary"
    log "Using GPU Burn command on PATH: $BINARY"
    return
  fi

  if command -v snap >/dev/null 2>&1; then
    if snap list "$SNAP_PACKAGE" >/dev/null 2>&1; then
      GPU_BURN_MODE="snap"
      log "Using installed snap package: $SNAP_PACKAGE"
      return
    fi

    if is_true "$INSTALL_SNAP"; then
      log "Installing snap package requested by HCS config: $SNAP_PACKAGE"
      if run_privileged snap install "$SNAP_PACKAGE" >>"$LOG_FILE" 2>&1; then
        SNAP_INSTALLED_BY_HCS="true"
        GPU_BURN_MODE="snap"
        log "Installed snap package: $SNAP_PACKAGE"
        return
      fi
      fail "failed to install snap package $SNAP_PACKAGE" 2
    fi

    log "Snap is available but $SNAP_PACKAGE is not installed and snap install was not enabled"
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
      # Tags and branches shallow-clone directly; a commit SHA needs an
      # explicit fetch. Never fall back to an unpinned default branch.
      log "Ref clone failed; fetching $SOURCE_REF explicitly"
      git clone --no-checkout "$SOURCE_URL" "$SOURCE_DIR" >>"$LOG_FILE" 2>&1 || fail "failed to clone GPU Burn" 2
      git -C "$SOURCE_DIR" fetch --depth 1 origin "$SOURCE_REF" >>"$LOG_FILE" 2>&1 || true
      git -C "$SOURCE_DIR" checkout "$SOURCE_REF" >>"$LOG_FILE" 2>&1 || fail "failed to checkout GPU Burn ref $SOURCE_REF" 2
    fi
  fi

  log "Building GPU Burn in $SOURCE_DIR"
  make -C "$SOURCE_DIR" >>"$LOG_FILE" 2>&1 || fail "failed to build GPU Burn" 2

  if [ ! -x "$BINARY" ] && [ -x "$SOURCE_DIR/gpu_burn" ]; then
    BINARY="$SOURCE_DIR/gpu_burn"
  fi
  [ -x "$BINARY" ] || fail "GPU Burn binary was not produced at $BINARY" 2
  GPU_BURN_MODE="source"
}

ensure_nvidia_driver
ensure_gpu_burn

if [ "$GPU_BURN_MODE" = "snap" ]; then
  COMMAND=("snap" "run" "$SNAP_PACKAGE" "-m" "$MEMORY")
else
  COMMAND=("$BINARY" "-m" "$MEMORY")
fi
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
