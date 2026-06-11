#!/bin/bash

set -o pipefail

# AI inference benchmark based on llama.cpp's llama-bench.
#
# The CPU path runs on any SUT; GPU backends (CUDA/Vulkan/HIP) are opt-in and
# build only when their toolchain is present. When no model can be obtained
# (air-gapped with no local GGUF) the test emits HCS_UNSUPPORTED and the runner
# records the step as unsupported instead of failing the machine.

REPETITIONS=${HCS_AI_LLM_REPETITIONS:-5}
PROMPT_TOKENS=${HCS_AI_LLM_PROMPT_TOKENS:-512}
GEN_TOKENS=${HCS_AI_LLM_GEN_TOKENS:-128}
THREADS=${HCS_AI_LLM_THREADS:-}
BACKEND=${HCS_AI_LLM_BACKEND:-auto}
GPU_LAYERS=${HCS_AI_LLM_GPU_LAYERS:-99}
CMAKE_EXTRA=${HCS_AI_LLM_CMAKE_EXTRA:-}

MODEL=${HCS_AI_LLM_MODEL:-}
MODEL_URL=${HCS_AI_LLM_MODEL_URL:-https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct-GGUF/resolve/main/qwen2.5-0.5b-instruct-q4_k_m.gguf}
MODEL_DIR=${HCS_AI_LLM_MODEL_DIR:-/tmp/hcs-ai-llm/models}
DOWNLOAD_MODEL=${HCS_AI_LLM_DOWNLOAD_MODEL:-true}
# Optional sha256 of the GGUF; when set, configured/cached/downloaded models
# are verified before use so benchmark evidence is tied to a known artifact.
MODEL_SHA256=${HCS_AI_LLM_MODEL_SHA256:-}

SOURCE_URL=${HCS_AI_LLM_SOURCE_URL:-https://github.com/ggml-org/llama.cpp.git}
SOURCE_REF=${HCS_AI_LLM_SOURCE_REF:-master}
SOURCE_DIR=${HCS_AI_LLM_SOURCE_DIR:-/tmp/hcs-ai-llm/llama.cpp}
BINARY=${HCS_AI_LLM_BINARY:-${SOURCE_DIR}/build/bin/llama-bench}
BUILD_FROM_SOURCE=${HCS_AI_LLM_BUILD_FROM_SOURCE:-true}

LOG_FILE=${HCS_AI_LLM_LOG_FILE:-/tmp/hcs-ai-llm/ai-llm.log}
RESULT_FILE=${HCS_AI_LLM_RESULT_FILE:-/tmp/hcs-ai-llm/ai-llm.result.json}
BENCH_JSON_FILE=${HCS_AI_LLM_BENCH_JSON_FILE:-/tmp/hcs-ai-llm/ai-llm.llama-bench.json}

BACKEND_RESOLVED=""
BUILD_MODE=""
MODEL_PATH=""
MODEL_SOURCE=""

mkdir -p "$(dirname "$LOG_FILE")" "$(dirname "$RESULT_FILE")" "$(dirname "$BENCH_JSON_FILE")" "$MODEL_DIR"
: >"$LOG_FILE"

function log() {
  printf '[%s] %s\n' "$(date -Is)" "$*" | tee -a "$LOG_FILE"
}

function lower() {
  printf '%s' "$1" | tr '[:upper:]' '[:lower:]'
}

function is_true() {
  case "$(lower "$1")" in
    1|true|yes|y|on) return 0 ;;
    *) return 1 ;;
  esac
}

function json_string() {
  local value=${1-}
  if command -v python3 >/dev/null 2>&1; then
    python3 -c 'import json, sys; print(json.dumps(sys.argv[1]))' "$value"
  else
    printf '"%s"' "$(printf '%s' "$value" | sed 's/\\/\\\\/g; s/"/\\"/g')"
  fi
}

function json_number() {
  local value=${1-}
  case "$value" in
    ''|NA) printf 'null' ;;
    *) printf '%s' "$value" ;;
  esac
}

function write_result() {
  local status=$1
  local reason=$2
  local rc=$3
  local pp_ts=${4-NA}
  local pp_sd=${5-NA}
  local tg_ts=${6-NA}
  local tg_sd=${7-NA}
  local threads=${8-NA}
  cat >"$RESULT_FILE" <<EOF
{
  "schema_version": 1,
  "test_id": "ai_llm",
  "status": $(json_string "$status"),
  "status_reason": $(json_string "$reason"),
  "return_code": $rc,
  "backend": $(json_string "$BACKEND_RESOLVED"),
  "build_mode": $(json_string "$BUILD_MODE"),
  "model": $(json_string "$MODEL_PATH"),
  "model_source": $(json_string "$MODEL_SOURCE"),
  "prompt_tokens": $(json_number "$PROMPT_TOKENS"),
  "gen_tokens": $(json_number "$GEN_TOKENS"),
  "repetitions": $(json_number "$REPETITIONS"),
  "threads": $(json_number "$threads"),
  "prompt_tokens_per_second": $(json_number "$pp_ts"),
  "prompt_tokens_per_second_stddev": $(json_number "$pp_sd"),
  "gen_tokens_per_second": $(json_number "$tg_ts"),
  "gen_tokens_per_second_stddev": $(json_number "$tg_sd"),
  "binary": $(json_string "$BINARY"),
  "log_file": $(json_string "$LOG_FILE"),
  "bench_json_file": $(json_string "$BENCH_JSON_FILE")
}
EOF
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

function resolve_backend() {
  case "$(lower "$BACKEND")" in
    cpu) BACKEND_RESOLVED="cpu" ;;
    cuda) BACKEND_RESOLVED="cuda" ;;
    vulkan) BACKEND_RESOLVED="vulkan" ;;
    hip|rocm) BACKEND_RESOLVED="hip" ;;
    auto|"")
      if command -v nvcc >/dev/null 2>&1 && command -v nvidia-smi >/dev/null 2>&1; then
        BACKEND_RESOLVED="cuda"
      else
        BACKEND_RESOLVED="cpu"
      fi
      ;;
    *)
      log "Unknown backend '$BACKEND'; falling back to cpu"
      BACKEND_RESOLVED="cpu"
      ;;
  esac
  log "AI inference backend: $BACKEND_RESOLVED (requested: $BACKEND)"
}

function ensure_binary() {
  if [ -x "$BINARY" ]; then
    BUILD_MODE="binary"
    log "Using llama-bench binary: $BINARY"
    return
  fi

  if command -v llama-bench >/dev/null 2>&1; then
    BINARY=$(command -v llama-bench)
    BUILD_MODE="binary"
    log "Using llama-bench command on PATH: $BINARY"
    return
  fi

  is_true "$BUILD_FROM_SOURCE" || fail "llama-bench binary not found at $BINARY and source build is disabled" 2

  command -v git >/dev/null 2>&1 || fail "git is required to fetch llama.cpp" 2
  command -v cmake >/dev/null 2>&1 || fail "cmake is required to build llama.cpp" 2
  command -v c++ >/dev/null 2>&1 || command -v g++ >/dev/null 2>&1 || \
    fail "a C++ compiler (gcc-c++) is required to build llama.cpp" 2

  local cmake_flags=(-DLLAMA_CURL=OFF -DGGML_NATIVE=ON -DBUILD_SHARED_LIBS=OFF)
  case "$BACKEND_RESOLVED" in
    cuda) cmake_flags+=(-DGGML_CUDA=ON) ;;
    vulkan) cmake_flags+=(-DGGML_VULKAN=ON) ;;
    hip) cmake_flags+=(-DGGML_HIP=ON) ;;
  esac
  # shellcheck disable=SC2206
  [ -n "$CMAKE_EXTRA" ] && cmake_flags+=($CMAKE_EXTRA)

  if [ ! -d "$SOURCE_DIR/.git" ]; then
    rm -rf "$SOURCE_DIR"
    log "Cloning llama.cpp from $SOURCE_URL ref $SOURCE_REF"
    if ! git clone --depth 1 --branch "$SOURCE_REF" "$SOURCE_URL" "$SOURCE_DIR" >>"$LOG_FILE" 2>&1; then
      log "Branch-specific clone failed; retrying default branch"
      git clone --depth 1 "$SOURCE_URL" "$SOURCE_DIR" >>"$LOG_FILE" 2>&1 || fail "failed to clone llama.cpp" 2
    fi
  fi

  log "Configuring llama.cpp build (${BACKEND_RESOLVED}): cmake ${cmake_flags[*]}"
  cmake -S "$SOURCE_DIR" -B "$SOURCE_DIR/build" "${cmake_flags[@]}" >>"$LOG_FILE" 2>&1 || \
    fail "cmake configure failed for backend $BACKEND_RESOLVED" 2

  log "Building llama-bench"
  cmake --build "$SOURCE_DIR/build" --config Release --target llama-bench -j "$(nproc 2>/dev/null || echo 2)" \
    >>"$LOG_FILE" 2>&1 || fail "failed to build llama-bench" 2

  if [ ! -x "$BINARY" ]; then
    for candidate in "$SOURCE_DIR/build/bin/llama-bench" "$SOURCE_DIR/build/llama-bench" "$SOURCE_DIR/llama-bench"; do
      if [ -x "$candidate" ]; then
        BINARY="$candidate"
        break
      fi
    done
  fi
  [ -x "$BINARY" ] || fail "llama-bench binary was not produced at $BINARY" 2
  BUILD_MODE="source"
}

function model_checksum_ok() {
  # $1 = file to check. True when no checksum is configured or it matches.
  local path=$1 actual
  [ -n "$MODEL_SHA256" ] || return 0
  actual=$(sha256sum "$path" | awk '{print $1}')
  if [ "$actual" != "$MODEL_SHA256" ]; then
    log "Model checksum mismatch for $path (expected $MODEL_SHA256, got $actual)"
    return 1
  fi
  log "Model sha256 verified: $actual"
  return 0
}

function ensure_model() {
  if [ -n "$MODEL" ]; then
    [ -f "$MODEL" ] || unsupported "configured model not found: $MODEL; set ai_llm_model to a readable GGUF file"
    model_checksum_ok "$MODEL" || fail "configured model failed sha256 verification: $MODEL" 3
    MODEL_PATH="$MODEL"
    MODEL_SOURCE="configured"
    log "Using configured model: $MODEL_PATH"
    return
  fi

  MODEL_PATH="$MODEL_DIR/$(basename "$MODEL_URL")"
  if [ -f "$MODEL_PATH" ]; then
    if model_checksum_ok "$MODEL_PATH"; then
      MODEL_SOURCE="cached"
      log "Using cached model: $MODEL_PATH"
      return
    fi
    log "Cached model failed verification; removing and re-downloading"
    rm -f "$MODEL_PATH"
  fi

  is_true "$DOWNLOAD_MODEL" || \
    unsupported "no local model and model download is disabled; set ai_llm_model to a local GGUF or enable ai_llm_download_model"

  log "Downloading model from $MODEL_URL"
  if command -v curl >/dev/null 2>&1; then
    curl -fL --retry 3 -o "$MODEL_PATH.part" "$MODEL_URL" >>"$LOG_FILE" 2>&1
  elif command -v wget >/dev/null 2>&1; then
    wget -O "$MODEL_PATH.part" "$MODEL_URL" >>"$LOG_FILE" 2>&1
  else
    unsupported "neither curl nor wget is available to download the model; set ai_llm_model to a local GGUF"
  fi

  if [ $? -ne 0 ] || [ ! -s "$MODEL_PATH.part" ]; then
    rm -f "$MODEL_PATH.part"
    unsupported "failed to download model from $MODEL_URL (no network?); set ai_llm_model to a local GGUF for air-gapped runs"
  fi
  if ! model_checksum_ok "$MODEL_PATH.part"; then
    rm -f "$MODEL_PATH.part"
    fail "downloaded model failed sha256 verification (corrupted or tampered download from $MODEL_URL)" 3
  fi
  mv "$MODEL_PATH.part" "$MODEL_PATH"
  MODEL_SOURCE="downloaded"
  log "Downloaded model: $MODEL_PATH"
}

function read_metrics() {
  python3 - "$BENCH_JSON_FILE" <<'PY'
import json
import sys

def fmt(value):
    return "%.2f" % value if isinstance(value, (int, float)) else "NA"

pp_ts = pp_sd = tg_ts = tg_sd = None
threads = None
try:
    with open(sys.argv[1]) as handle:
        rows = json.load(handle)
except Exception:
    print("NA NA NA NA NA")
    sys.exit(0)

for row in rows if isinstance(rows, list) else []:
    if row.get("n_threads") is not None:
        threads = row.get("n_threads")
    n_prompt = row.get("n_prompt") or 0
    n_gen = row.get("n_gen") or 0
    if n_prompt and not n_gen:
        pp_ts = row.get("avg_ts")
        pp_sd = row.get("stddev_ts")
    elif n_gen and not n_prompt:
        tg_ts = row.get("avg_ts")
        tg_sd = row.get("stddev_ts")

print(fmt(pp_ts), fmt(pp_sd), fmt(tg_ts), fmt(tg_sd), threads if threads is not None else "NA")
PY
}

resolve_backend
ensure_binary
ensure_model

COMMAND=("$BINARY" -m "$MODEL_PATH" -p "$PROMPT_TOKENS" -n "$GEN_TOKENS" -r "$REPETITIONS" -o json)
if [ "$BACKEND_RESOLVED" != "cpu" ]; then
  COMMAND+=(-ngl "$GPU_LAYERS")
fi
if [ -n "$THREADS" ]; then
  COMMAND+=(-t "$THREADS")
fi

log "Running llama-bench: ${COMMAND[*]}"
"${COMMAND[@]}" >"$BENCH_JSON_FILE" 2>>"$LOG_FILE"
RC=$?

if [ "$RC" -ne 0 ]; then
  cat "$BENCH_JSON_FILE" >>"$LOG_FILE" 2>/dev/null || true
  fail "llama-bench returned $RC" "$RC"
fi

read -r PP_TS PP_SD TG_TS TG_SD M_THREADS < <(read_metrics)

log "Results (backend=$BACKEND_RESOLVED, model=$(basename "$MODEL_PATH"), threads=$M_THREADS):"
log "  prompt processing (pp${PROMPT_TOKENS}): ${PP_TS} t/s (stddev ${PP_SD})"
log "  token generation  (tg${GEN_TOKENS}): ${TG_TS} t/s (stddev ${TG_SD})"

write_result "passed" "ok" 0 "$PP_TS" "$PP_SD" "$TG_TS" "$TG_SD" "$M_THREADS"
log "AI inference benchmark completed successfully"
exit 0
