# AI inference (llama.cpp)

The `ai_llm` test is an AI inference benchmark built on the open source
[llama.cpp](https://github.com/ggml-org/llama.cpp) `llama-bench` tool. It
measures how fast the system under test runs a small large-language-model
workload and reports throughput in tokens per second for two phases:

- **prompt processing** (`pp`, compute-bound prefill), and
- **token generation** (`tg`, memory-bandwidth-bound decode).

Unlike `gpu_burn` (a GPU *stability/stress* test), `ai_llm` is a *functional and
performance* test: it answers "can this hardware actually run AI workloads on
AlmaLinux, and how fast?" The CPU path runs on any SUT. GPU backends are opt-in.
This is optional accelerator evidence, not part of the core certification
preset unless the Certification SIG creates such a profile.

## Backends

| `ai_llm_backend` | Build flag | Requires |
| --- | --- | --- |
| `auto` (default) | CUDA when present, else CPU | — |
| `cpu` | none | a C++ compiler |
| `cuda` | `-DGGML_CUDA=ON` | CUDA toolkit (`nvcc`) + NVIDIA driver |
| `vulkan` | `-DGGML_VULKAN=ON` | Vulkan SDK + `glslc` |
| `hip` | `-DGGML_HIP=ON` | ROCm/HIP toolchain |

`auto` only selects CUDA when both `nvcc` and `nvidia-smi` are present;
otherwise it builds the always-available CPU backend. Vulkan and HIP are
explicit because they need their own toolchains to build.

## Model

The benchmark needs a GGUF model. By default it downloads the small, openly
licensed (Apache-2.0) `Qwen2.5-0.5B-Instruct` Q4_K_M model (~491 MB) into
`ai_llm_model_dir`. For air-gapped runs, point `ai_llm_model` at a local GGUF
file and the test will use it directly. If no model can be obtained, the test
emits an `HCS_UNSUPPORTED` marker and the runner records the step as unsupported
instead of failing the machine.

For submit-worthy benchmark evidence, set `ai_llm_submission_evidence=true`.
That mode requires:

- `ai_llm_model_sha256` for the exact GGUF model artifact,
- a pinned `ai_llm_source_ref` rather than `main`, `master`, or `HEAD`, and
- `ai_llm_binary_sha256` when using a prebuilt binary with
  `ai_llm_build_from_source=false`.

Without those inputs, keep `ai_llm` results experimental or reviewer-context
only. The result JSON records model source, model checksum, source ref/commit,
binary checksum, backend, thread count, and throughput.

## Running

```bash
# via the runner (CPU path works everywhere)
python -m hcs run --profile check --test ai_llm --inventory 127.0.0.1, -c local

# directly via Ansible
ansible-playbook -c local -i 127.0.0.1, automated.yml --tags ai_llm
```

## Important variables

| Variable | Default | Purpose |
| --- | --- | --- |
| `ai_llm_repetitions` | profile-scaled (`5`) | `llama-bench -r`; runs per measurement. |
| `ai_llm_prompt_tokens` | `512` | Prompt-processing token count (`-p`). |
| `ai_llm_gen_tokens` | `128` | Token-generation count (`-n`). |
| `ai_llm_threads` | empty | CPU threads (`-t`); empty lets llama-bench choose. |
| `ai_llm_backend` | `auto` | `auto`/`cpu`/`cuda`/`vulkan`/`hip`. |
| `ai_llm_gpu_layers` | `99` | Layers offloaded to GPU (`-ngl`) for non-CPU backends. |
| `ai_llm_cmake_extra` | empty | Extra cmake flags for the build. |
| `ai_llm_submission_evidence` | `false` | Require pinned/checksummed benchmark inputs for submit-worthy evidence. |
| `ai_llm_model` | empty | Path to a local GGUF (overrides the download). |
| `ai_llm_model_url` | Qwen2.5-0.5B Q4_K_M | Model download URL. |
| `ai_llm_model_sha256` | empty | Required when `ai_llm_submission_evidence=true`; verifies configured/cached/downloaded models. |
| `ai_llm_model_dir` | `<cache>/ai-llm/models` | Where downloaded models are cached. |
| `ai_llm_download_model` | `true` | Allow downloading the model when no local file exists. |
| `ai_llm_build_from_source` | `true` | Clone/build llama.cpp when no binary exists. |
| `ai_llm_binary` | `<cache>/llama.cpp/build/bin/llama-bench` | Existing or built binary. |
| `ai_llm_binary_sha256` | empty | Required for submit-worthy evidence when using a prebuilt binary. |
| `ai_llm_source_url` | `https://github.com/ggml-org/llama.cpp.git` | llama.cpp source repository. |
| `ai_llm_source_ref` | `b9601` | Pinned llama.cpp ref to build. |

The test writes its console log under the run logs directory and a JSON result
(`ai-llm.result.json`) plus the raw `llama-bench` JSON under the run artifacts
directory.
