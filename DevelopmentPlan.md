# Hardware Certification Suite Development Plan

This document captures a proposed development roadmap for turning the
AlmaLinux Hardware Certification Suite into a polished, client-runnable
certification platform.

The goal is not only to run tests. The suite should guide an operator through a
well-thought certification process, collect quality benchmark data, preserve raw
evidence, and produce consistent reports that AlmaLinux can use for review,
comparison, and long-term certification records.

Last updated: 2026-06-01.

## Current Fork Baseline

The `xsub/Hardware-Certification-Suite` fork now contains the first practical
runner foundation. This changes the roadmap from "build the runner first" to
"harden, validate, and productize the runner."

Implemented in the fork:

- Python/Rich runner package under `hcs/`.
- Runner commands for listing profiles, listing tests, configuring presets,
  and running Ansible-backed plans.
- Profiles from `check` through `extreme`.
- Built-in `certification` preset with required automated tests, optional
  automated tests, and manual USB/PXE checks tracked separately.
- Named presets saved in `hcs-runner.yml` with per-test profile selection,
  duration caps, repeat count, inventory, connection mode, and GPU Burn snap
  behavior.
- One generated sandbox per run:
  `AlmaLinux-HCS-<UTC timestamp>-RunID-<run id>`.
- Runner artifacts under the sandbox, including requested config JSON,
  per-step console logs, per-step result JSON, `run.summary.json`, and
  `run.report.txt`.
- Repeated passes with all pass artifacts preserved.
- Ansible recap parsing so `failed`, `unreachable`, or `ignored` counters are
  treated as runner failures even when Ansible exits successfully.
- Built-in AlmaLinux identity header and controller system facts in console and
  report artifacts.
- Sandboxed defaults for CPU scratch data, Phoronix, LTP, copied SUT tests,
  logs, cache, artifacts, and GPU Burn telemetry.
- Optional NVIDIA `gpu_burn` test with `nvidia-smi` detection, unsupported
  reporting when drivers are absent, AlmaLinux native NVIDIA setup guidance,
  and opt-in snap workload install/remove behavior.
- AlmaLinux 10 Phoronix compatibility patch for stale Fedora dependency names.
- GitHub Actions for CI, Python runner checks, Ansible syntax checks, and
  AlmaLinux container smoke checks.
- Product-first README plus detailed `docs/runner.md` operator reference.

Still roadmap, not yet complete:

- Formal schema validation for config, summaries, events, reports, and test
  result artifacts.
- `python -m hcs env doctor` / `python -m hcs preflight` command.
- Resume/checkpoint/event replay model.
- Rich dashboard refinements such as ETA, log tail controls, warnings, and
  bottleneck hints.
- Metrics time-series model and aggregation across repeated passes.
- Cache warm/verify/offline mode.
- GUI run browser and analysis frontend.
- Extension/plugin framework for ISV or workload packs.
- Live USB or appliance-style deployment.

## Guiding Principles

- Keep Ansible as the low-level executor for remote/local system actions.
- Treat the Python/Rich runner as the suite control plane.
- Build CLI/TUI first. Treat a GUI as a later frontend over the same core.
- Make every run reproducible, resumable, auditable, and reportable.
- Preserve raw evidence. Reports must summarize, not replace, raw artifacts.
- Use stable schemas for config, profiles, artifacts, events, metrics, and
  reports.
- Design the text runner with GUI integration in mind from the beginning.
- Keep the suite AlmaLinux-first but Linux-generic where possible, so other
  enterprise Linux projects can reuse the runner patterns, artifact contracts,
  and burn-in workflows.
- Prefer incremental, mergeable PRs over one large rewrite.

## Current Issue Triage

The existing GitHub issues are still useful, but they should be interpreted in a
broader suite-quality context.

- `#21` Stop using `/root` for Phoronix download/test location: mostly
  addressed in the fork through sandboxed `hcs_work_dir`, `hcs_scratch_dir`,
  `hcs_cache_dir`, `hcs_artifacts_dir`, `sut_tests_dir`, `lts_logs_dir`,
  Phoronix, and LTP defaults. Keep this open until remote SUT runs and every
  tool-native output path is audited end to end.
- `#10` Make CPU test use `--temp-path`: addressed in the fork. CPU now passes
  a sandboxed scratch directory into `stress-ng --temp-path`. Follow-up work
  should add artifact contract tests and cleanup verification.
- `#7` Deprecated Ansible `include`: upstream mostly fixed it; keep watching
  older branch work and any future ISV/test-pack imports.
- `#22` Reduce runtime: addressed structurally by runner profiles and named
  presets. Follow-up work should tune profile durations from real validation
  data rather than guessing.
- `#20` Cache downloadable test files: still valid. The sandbox has a cache
  directory, but cache warm/verify/offline behavior and checksums are not
  finished.
- `#19` Live USB image: still valuable, but it should come after preflight,
  cache/offline support, resume/checkpointing, and stable report schemas.
- `#6`, `#11`, `#12` MariaDB and ISV involvement: valid, but should become an
  extension framework, with MariaDB as the first concrete plugin/test pack.

## Strategic Product Direction

The suite should be useful beyond a narrow certification checklist. AlmaLinux
Hardware Certification can become a practical enterprise validation platform
that demonstrates AlmaLinux as a dependable base for modern infrastructure,
AI, VFX, virtualization, storage, networking, and long-running production
workloads.

From a product and ecosystem perspective, the strongest ROI comes from:

- making AlmaLinux easier to validate on new enterprise installations
- giving IHVs, ISVs, homelab users, AI teams, and infrastructure operators a
  repeatable way to prove a system is ready for real work
- producing credible, shareable artifacts that support certification,
  benchmarking, support cases, and procurement decisions
- making the runner generic enough that other Linux projects can borrow the
  tooling model while AlmaLinux remains the best-integrated reference platform
- creating test packs that map to commercially important use cases: AI/GPU,
  virtualization, containers, databases, storage, networking, and long burn-in
  stability

The project should therefore treat certification, burn-in, benchmarking, and
system readiness as related workflows over the same runner core.

## Target User Experience

The suite should be easy to run at a client installation.

An operator should be able to do something like:

```bash
python -m hcs run --profile check --inventory 127.0.0.1, -c local
python -m hcs run --preset certification --inventory 127.0.0.1, -c local
python -m hcs configure --preset lab-default
python -m hcs run --preset lab-default
python -m hcs run --preset certification --inventory <SUT IP>,
```

The current runner is invoked as `python -m hcs`. A future packaged entry point
can provide a shorter `hcs` command once packaging lands.

The runner should clearly show:

- selected profile: `check`, `short`, `medium`, `long`, `very_long`, `extreme`
- target platform and connection mode
- tests planned, running, complete, skipped, failed, and left
- current test and current attempt
- elapsed time and estimated remaining time
- live log output
- artifact locations
- warnings, outliers, and possible bottlenecks

The operator should not need to understand internal Ansible tags to perform a
guided evidence-collection run, if the runner path is accepted.

Initial interactive runner behavior:

- provide `python -m hcs configure` as a Rich prompt UI for building a named
  preset in `hcs-runner.yml`
- show checkbox-style prompts for each known test and record whether that test
  is enabled in the preset
- let each enabled test choose its own profile from `check` through `extreme`
- allow duration caps for tests that support time limits; when both a profile
  and a duration cap are present, use the more restrictive value
- provide a draft `certification` preset that models required automated tests,
  optional automated tests, and manual checks for SIG review
- show required/optional scope in the runner plan and write it into report
  artifacts
- store the default preset name under `run.default_preset`, so
  `python -m hcs run` can use the saved lab configuration without requiring
  the operator to repeat flags
- keep explicit CLI commands authoritative: `--profile` runs the normal
  profile test list unless `--preset` is also supplied

## Distribution Identity And Portability

The runner should communicate clearly which Linux platform it is running on,
without making the core runner impossible to reuse elsewhere.

Initial behavior:

- detect the local distribution from `/etc/os-release`
- render a built-in AlmaLinux ASCII logo when the controller is running on
  AlmaLinux, without requiring `fastfetch` or any other system package
- print a compact system identity table next to the logo with OS, host,
  kernel, uptime, RPM package count, Python mode, shell, CPU, GPU, memory,
  swap, root filesystem, local IP, locale, SELinux, and FIPS state when those
  facts are available
- if `fastfetch` is available in the operator environment, optionally use it
  only as a presentation enhancement; it must never be required for a normal
  HCS run
- record distribution identity in the requested/effective config and run
  manifest
- keep UI branding AlmaLinux-first while keeping executor, profiles, artifacts,
  and report formats generic

Future behavior:

- expand report facts with virtualization, container status, firmware, secure
  boot state, disk controller details, NIC inventory, accelerator topology, and
  loaded kernel modules
- allow downstream projects to provide their own branding/logo/plugin layer
  without forking the runner core
- split tests into generic Linux tests, AlmaLinux-specific tests, and
  vendor/plugin tests
- mark unsupported distro-specific tests as `unsupported`, not failed
- provide a clean compatibility matrix showing which tests are generic and
  which require AlmaLinux, EPEL, vendor repositories, or hardware-specific
  drivers

## Python Environment Reproducibility

The first implementation should keep the Python virtual environment as the
operator-controlled bootstrap environment. It must be simple to create, inspect,
and reuse, because the runner itself is the control plane and should not delete
the interpreter it is currently running inside.

Recommended near-term behavior:

- document a single supported bootstrap venv flow for AlmaLinux 10 using
  Python `3.12+`
- record Python version, venv/system mode, executable path, and dependency
  metadata in the run artifacts
- add an explicit `python -m hcs env doctor` command that validates the current
  venv, Ansible version, required Python packages, and expected runner entry
  points
- add an explicit `python -m hcs env rebuild` command or wrapper script later that
  recreates a named venv before starting the runner
- never silently rebuild or delete the active venv as part of
  `python -m hcs run`

For highly reproducible lab runs, a future wrapper can create a clean per-run
tool environment before invoking the runner:

```bash
./scripts/hcs-run --rebuild-venv --python python3.14 --profile check
```

That wrapper should:

- create a fresh venv under the run sandbox or a configured tools directory
- install pinned runner dependencies from a lock file
- write `pip freeze`, Python version, Ansible version, and lock-file checksum
  into the run artifacts
- keep the venv path stable enough for debugging, but isolated from test
  scratch/cache/artifact directories
- avoid network access when a local wheelhouse or cache is configured

This is a real enhancement, but it should land after the runner has stable
config, artifact, and reporting contracts. The immediate priority is to make
the current venv visible and auditable in every run.

## Runtime Profiles

Profiles should define a certification mode and expected test intensity.

Initial profile set:

- `check`: quick preflight and smoke validation
- `short`: short functional run for early feedback
- `medium`: practical default vendor/community run
- `long`: stronger certification run
- `very_long`: extended soak and benchmark run
- `extreme`: exhaustive lab mode

Profiles should be defined in YAML and should control:

- enabled tests
- test order
- duration per test
- repetitions per test
- timeout per test
- required vs optional tests
- skip/unsupported behavior
- benchmark intensity
- artifact retention

Example:

```yaml
profiles:
  check:
    description: Fast sanity check
    repetitions: 1
    tests:
      preflight:
        enabled: true
      hw_detection:
        enabled: true
      containers:
        enabled: true
      cpu:
        enabled: true
        duration: 2m
      network:
        enabled: false
      phoronix:
        enabled: false
      ltp:
        enabled: false

  medium:
    description: Practical certification run
    repetitions: 3
    tests:
      preflight:
        enabled: true
      hw_detection:
        enabled: true
      containers:
        enabled: true
      kvm:
        enabled: true
      cpu:
        enabled: true
        duration: 30m
      network:
        enabled: true
        duration: 600
      raid:
        enabled: auto
        duration: 600
      phoronix:
        enabled: true
        repetitions: 2
      ltp:
        enabled: true
        suites: smoke
```

## Burn-In And Continuous Validation Profiles

Many operators need more than one certification run. A new AlmaLinux-based
enterprise installation often needs a burn-in mode that can run for hours or
days, surface intermittent failures, and prove the system remains stable under
realistic sustained pressure.

Recommended additional operating modes:

- `burn_in_short`: 1 to 4 hour functional soak for new lab systems
- `burn_in_medium`: overnight validation for new production hosts
- `burn_in_long`: 24 to 72 hour pre-production acceptance
- `continuous`: recurring validation loop for dedicated validation systems
- `post_change`: focused validation after firmware, kernel, driver, BIOS, or
  hardware changes
- `rma_triage`: stress-focused mode for suspicious or flaky systems

Burn-in should collect:

- thermal data
- CPU frequency and throttling data
- memory pressure and ECC/MCE events
- disk SMART/NVMe health
- storage latency and error counters
- network link state, retransmits, drops, and throughput variance
- GPU temperature, clocks, ECC, power, and reset events where applicable
- kernel logs, warnings, machine checks, and OOM events
- time-series metrics so spikes and instability are visible

Useful burn-in workload families:

- CPU integer and floating point stress
- memory bandwidth and allocation stress
- storage sustained write/read and latency stress
- network throughput and packet-loss stress
- virtualization and container churn
- mixed workload mode combining CPU, memory, disk, network, and optional GPU
- idle stability mode that catches firmware, suspend, clock, or power issues

The runner should support long-running operation ergonomics:

- tmux/screen-friendly output
- periodic checkpointing
- resumable runs
- heartbeat files
- watchdog warnings
- configurable sampling interval
- graceful stop with partial report
- periodic report snapshots
- optional systemd timer/service integration for continuous validation

Prime95-like value comes from sustained, repeatable pressure plus credible
evidence. HCS should not clone a single stress tool; it should orchestrate the
right combination of stressors, sensors, logs, and reports.

## Config Model

The suite should have a requested config and an effective config.

The requested config is what the user provides. The effective config is what the
runner resolves after applying defaults, profile settings, detected hardware,
and command-line overrides.

Current near-term config shape:

```yaml
run:
  base_dir: /var/tmp
  default_preset: certification
  id:
  sandbox_dir:

paths:
  runner_dir: runner
  logs_dir: logs
  scratch_dir: scratch
  cache_dir: cache
  artifacts_dir: artifacts
  sut_tests_dir: sut-tests
  phoronix_dir: phoronix
  ltp_dir: ltp

ansible:
  extra_vars: {}

presets:
  lab-default:
    profile: medium
    inventory: 127.0.0.1,
    connection: local
    repeat: 3
    tests:
      hw_detection:
        enabled: true
        profile: check
      cpu:
        enabled: true
        profile: long
        duration: 30m
```

Future config work should add schema validation, explicit effective-config
artifacts, documented compatibility guarantees, and migration helpers when the
config format changes.

## Work Directory Layout

The suite should not default to `/root` for working data.

Current default sandbox:

```text
/tmp/AlmaLinux-HCS-<UTC timestamp>-RunID-<run id>/
  runner/
  logs/
  scratch/
  cache/
  artifacts/
  sut-tests/
  phoronix/
  ltp/
```

Labs can set `run.base_dir: /var/tmp` or another filesystem in
`hcs-runner.yml`. Future work should add `run.events.jsonl`,
`config.effective.json`, manifest checksums, and stronger retention controls.

## Artifact Contract

All test artifacts should use unified names. Tool-native artifacts are allowed,
but they should be copied or linked into the suite artifact tree with normalized
names.

Filename pattern:

```text
<step-number>-pass<pass-number>-<test-id>.<artifact-type>.<extension>
```

Examples:

```text
001-pass01-hw_detection.console.log
001-pass01-hw_detection.result.json
002-pass01-cpu.console.log
002-pass01-cpu.result.json
003-pass02-network.console.log
003-pass02-network.result.json
gpu-burn/gpu-burn.nvidia-smi.csv
gpu-burn/gpu-burn.result.json
```

Every test should produce at least:

- `NNN-passNN-test_id.result.json`
- `NNN-passNN-test_id.console.log`

Optional artifacts:

- `metrics.json`
- `report.txt`
- `report.md`
- native logs
- native JSON
- native PDF
- screenshots or images if a future test needs them

Future schema work can decide whether to preserve `passNN` terminology or
introduce an explicit `attemptNN` directory layer. The important rule is that
operators and automation must be able to identify step number, pass number,
test ID, artifact type, and file format without parsing tool-native output.

## Test Result Schema

Each test should emit a structured result.

Example:

```json
{
  "schema_version": 1,
  "test_id": "cpu",
  "step": 3,
  "profile": "medium",
  "status": "passed",
  "started_at": "2026-06-01T10:15:30Z",
  "finished_at": "2026-06-01T10:25:30Z",
  "duration_seconds": 600,
  "attempts": 3,
  "valid_attempts": 3,
  "failed_attempts": 0,
  "artifacts": [
    "003-cpu.console.log",
    "003-cpu.metrics.json"
  ],
  "summary": {},
  "warnings": []
}
```

Allowed statuses:

- `passed`
- `failed`
- `passed_with_warnings`
- `skipped`
- `unsupported`
- `incomplete`

Unsupported hardware should not be represented as a test failure if preflight
can prove the test is not applicable.

## Repetitions And Aggregation

The runner should support repeated test passes.

Model:

```text
suite run
  test step
    attempt / repetition
```

Example artifact layout:

```text
tests/
  003-cpu/
    attempts/
      001/
        003-cpu.attempt-001.result.json
        003-cpu.attempt-001.console.log
        003-cpu.attempt-001.stress-ng.log
      002/
        003-cpu.attempt-002.result.json
        003-cpu.attempt-002.console.log
      003/
        003-cpu.attempt-003.result.json
        003-cpu.attempt-003.console.log
    003-cpu.result.json
    003-cpu.report.txt
    003-cpu.report.md
```

Aggregated benchmark data should include:

- mean
- median
- minimum
- maximum
- standard deviation
- coefficient of variation
- best attempt
- worst attempt
- valid attempt count
- failed attempt count

Pass/fail rules should be conservative:

- required attempts must pass
- high variance should create a warning
- repeated failures should fail the test
- unsupported tests should be reported as unsupported
- incomplete runs should remain explicit

## Metrics Model

Each benchmark-capable test should define the metrics it can emit.

Example:

```yaml
metrics:
  throughput_mbps:
    unit: Mbps
    better: higher
    aggregate:
      - mean
      - median
      - min
      - max
      - stdev
  latency_ms:
    unit: ms
    better: lower
    aggregate:
      - mean
      - median
      - min
      - max
      - stdev
```

Metrics should support:

- scalar values
- time-series values
- per-attempt summaries
- per-run aggregate summaries
- outlier flags
- warning thresholds

## AI, GPU, CUDA, And VFX Workload Track

AI-enabled and GPU-heavy environments are a strong opportunity for AlmaLinux.
The suite should grow a dedicated accelerator test track that validates whether
AlmaLinux is ready for CUDA, AI inference/training, rendering, and VFX-style
workloads on real hardware.

The first goal is not to replace vendor validation suites. The goal is to make
AlmaLinux a credible, easy-to-test base layer for GPU-enabled systems.

The first implementation should be based on existing open source tools rather
than a custom CUDA renderer. [GPU Burn](https://github.com/wilicc/gpu-burn) is a
strong first move because it is a known, focused NVIDIA CUDA stress workload
and keeps HCS responsible for orchestration, telemetry, sandboxing, and
reporting rather than GPU algorithm correctness.

Recommended test IDs:

- `gpu_detection`: detect PCI GPU devices, driver state, kernel modules, IOMMU,
  display/compute role, firmware, and relevant logs
- `nvidia_driver`: validate NVIDIA driver installation state and collect
  `nvidia-smi` facts
- `gpu_burn`: run the open source GPU Burn workload when NVIDIA drivers are
  already installed and `nvidia-smi` can list GPUs
- `cuda_smoke`: compile and run a tiny CUDA program that exercises memory copy,
  kernel launch, and basic floating-point computation
- `cuda_burn`: longer CUDA stress workload with temperature, power, clock, ECC,
  and error monitoring
- `gpu_vfx`: graphics-oriented workload for display/VFX cards using OpenGL,
  Vulkan, or Blender where available
- `gpu_ai`: AI-oriented workload using CUDA libraries, ONNX Runtime, PyTorch, or
  TensorRT where licensing and repository setup allow it

Hardware discovery should reuse existing artifacts where possible:

- consume `hw_detection` output if present
- fall back to direct probing with `lspci`, `lsmod`, `modinfo`, `dmesg`,
  `/sys`, `nvidia-smi`, `rocm-smi`, `vulkaninfo`, and `glxinfo`
- classify devices as AI accelerator, graphics/VFX GPU, integrated GPU,
  passthrough/virtual GPU, or unsupported/unknown
- record device IDs, vendor IDs, driver versions, firmware versions, PCIe link
  speed/width, BAR/resizable BAR, NUMA locality, and thermal/power capabilities

Driver installation must be careful:

- default to detect/report mode
- require an explicit config flag before installing vendor drivers
- on AlmaLinux 9 and 10, prefer the native AlmaLinux NVIDIA package path:
  `almalinux-release-nvidia-driver`, `nvidia-open-kmod`, `nvidia-driver`, and
  `nvidia-driver-cuda`
- support offline/local repository paths
- record every repository and package installed
- detect Secure Boot and DKMS/kernel-devel prerequisites before modifying the
  system
- produce a clear warning when driver installation would make the system
  non-compliant with the operator's policy
- leave room for a future `nvidia_driver` test that can validate or optionally
  prepare this native package stack before CUDA/GPU Burn workloads run

Baseline `gpu_burn` workload design:

- do not install NVIDIA drivers implicitly in the first implementation
- check `nvidia-smi` first and report `unsupported` when NVIDIA drivers or GPUs
  are not available
- when running on AlmaLinux 9/10 without `nvidia-smi`, print the native
  AlmaLinux NVIDIA setup hint so the operator can fix the host without leaving
  the HCS workflow
- use a configured/prebuilt `gpu_burn` binary when present
- use an already installed `gpu-burn` snap when available
- if `snapd` is available and the saved preset explicitly allows it, install
  the `gpu-burn` snap before the workload
- if HCS installed the snap and the preset requested cleanup, remove that snap
  after the workload finishes
- otherwise clone/build GPU Burn into the run cache when `git`, `make`, and
  `nvcc` are available
- collect `nvidia-smi` telemetry before and during the workload
- keep the GPU Burn log, build log, telemetry CSV, and result JSON inside the
  HCS sandbox
- fail on GPU Burn non-zero exit, Xid/device reset signs, driver/runtime
  mismatch, thermal shutdown, or telemetry collection errors that invalidate
  the result

Custom CUDA workload design, later:

- start with a small C/CUDA program built with `nvcc` when available
- add a Rust/CUDA path only after the C smoke test is stable
- test host-to-device copy, device-to-host copy, kernel launch, synchronization,
  memory bandwidth, and numerical correctness
- collect `nvidia-smi --query-gpu` telemetry before, during, and after the run
- keep raw build logs, binary metadata, telemetry, and result JSON
- fail on correctness errors, device resets, Xid errors, ECC errors, thermal
  shutdown, or driver/runtime mismatch

For graphics/VFX GPUs, a visually meaningful workload could render many
revolving AlmaLinux logo meshes, particles, or shader-heavy scenes. This is
attractive from a demo and product-story perspective, but it creates the
classic risk of testing bugs in our own workload rather than the system under
test. It should be treated as a future optional workload, not the first GPU
certification signal:

- first use proven tools such as Blender benchmark, glmark2, vkmark, or
  Phoronix GPU suites where packages and licensing permit
- later add a custom open scene that renders AlmaLinux-branded geometry and
  produces deterministic frame timing and image artifacts
- keep the renderer optional and headless-friendly using EGL/Vulkan offscreen
  modes where possible

The accelerator track should support NVIDIA first because CUDA is the most
urgent enterprise AI target. The architecture should leave room for AMD ROCm,
Intel GPU/oneAPI, and non-GPU accelerators.

## Event Stream

The runner core should not print directly. It should emit typed events that
frontends consume.

The CLI/TUI consumes events for progress reporting. A future GUI consumes the
same events for dashboards. Stored events allow run replay and analysis.

Example `run.events.jsonl` records:

```json
{"event": "run_started", "profile": "medium", "run_id": "20260601T101530Z-medium-host01"}
{"event": "test_started", "test_id": "network", "step": 4, "attempt": 2}
{"event": "metric", "test_id": "network", "name": "throughput_mbps", "value": 941.2, "timestamp": "2026-06-01T10:45:00Z"}
{"event": "artifact_created", "test_id": "network", "path": "tests/004-network/attempts/002/004-network.attempt-002.iperf3.json"}
{"event": "test_completed", "test_id": "network", "status": "passed"}
```

## Runner Architecture

The runner should be a headless core library first. CLI, TUI, and GUI should be
frontends over the same core.

Suggested structure:

```text
hcs_core/
  config.py
  registry.py
  executor.py
  events.py
  artifacts.py
  metrics.py
  analysis.py
  reports.py

hcs_cli/
  main.py
  tui.py

hcs_gui/
  app.py
  models.py
  charts.py
```

Core responsibilities:

- load and validate requested config
- resolve effective config
- load test registry
- plan the run
- launch Ansible or subprocess steps
- capture stdout/stderr
- write artifacts
- emit events
- support resume
- support repeated attempts
- aggregate results
- generate reports

CLI/TUI responsibilities:

- parse command-line arguments
- display progress
- show live logs
- show warnings
- invoke reporting commands

GUI responsibilities, later:

- select profiles and config
- run or inspect suite runs
- show graphs
- compare multiple passes
- identify spikes and outliers
- explore possible bottlenecks
- export reports

## Console/TUI Experience

The console runner should feel like a control panel.

Example:

```text
AlmaLinux Hardware Certification Suite

Target: host01.example.com    Profile: medium    Run: 20260601T101530Z-medium-host01
Overall: [##########----------] 5/10 tests complete   elapsed 01:12:44

Current: network
Attempt: 2/3
Status: running   elapsed 00:08:13   estimate 00:30:00

Tests:
  PASS  preflight        00:00:22
  PASS  hw_detection     00:00:07
  PASS  containers       00:02:41
  PASS  kvm              00:01:10
  RUN   network          00:08:13
  WAIT  cpu
  WAIT  raid
  WAIT  phoronix
  WAIT  ltp

Live log:
  [network] Testing device eno1...
  [network] iperf3 interval 7/30...
```

`rich` is a good first implementation choice. `textual` can be considered later
if a fuller terminal application is needed.

## Reporting

Plain text should be the first-class report format. Markdown should be produced
alongside it. RTF, HTML, and PDF can come later.

Initial report set:

- `run.report.txt`
- `run.report.md`
- `run.summary.json`
- `run.manifest.json`

Later report formats:

- `run.report.rtf`
- `run.report.html`
- `run.report.pdf`

Each report should include:

- suite name
- run ID
- selected profile
- target host
- started timestamp
- finished timestamp
- generated timestamp
- suite version
- runner version
- git SHA
- Ansible version
- OS version
- kernel version
- hardware summary
- test status table
- metrics table
- warnings
- outliers
- possible bottlenecks
- artifact manifest checksum

Every report should have a footer:

```text
Generated by AlmaLinux Hardware Certification Suite <version>
Run ID <run-id> | Generated <timestamp> | Artifact manifest sha256 <hash>
```

## Manifest And Auditability

`run.manifest.json` should index all artifacts.

Example:

```json
{
  "schema_version": 1,
  "run_id": "20260601T101530Z-medium-host01",
  "profile": "medium",
  "status": "passed",
  "target": "host01",
  "artifacts": [
    {
      "path": "tests/003-cpu/003-cpu.result.json",
      "sha256": "...",
      "size": 1234,
      "type": "test-result"
    }
  ]
}
```

This allows:

- upload validation
- report reproducibility
- artifact integrity checks
- future portal ingestion
- independent review

## Analysis And GUI Readiness

The GUI should be an enhanced version of the runner and analysis layer, not a
separate implementation.

The core should store enough structured data for:

- live progress
- graphs
- multiple pass comparison
- spike detection
- outlier detection
- bottleneck investigation
- baseline comparison
- report export

Recommended data storage:

- raw artifacts on disk
- `run.events.jsonl` for replay
- `run.summary.json` for quick summaries
- `run.sqlite` or normalized JSON for metrics and analysis

SQLite is a strong candidate because it is local, simple, queryable,
GUI-friendly, and does not require a service.

Bottleneck detection should be evidence-based and conservative. Reports should
say "possible bottleneck" and list the metrics that caused the warning.

Examples:

- network low throughput plus retransmits
- disk latency spikes during RAID/fio tests
- CPU throttling or thermal warnings during stress tests
- memory pressure during Phoronix or LTP runs
- high coefficient of variation across repeated attempts

## Internal Testing And Badges

The suite certifies hardware, but the repository must also continuously test the
suite itself.

CI layers:

- `yamllint`
- `ansible-lint`
- ShellCheck
- Ansible syntax checks
- Python unit tests
- profile schema tests
- artifact contract tests
- report generation tests
- resume behavior tests
- manifest checksum tests

Useful badges:

- CI
- Ansible lint
- ShellCheck
- schema tests
- artifact contract
- runner tests
- coverage
- nightly smoke
- latest release

Coverage mainly applies to the Python runner/reporting/analysis code. For
Ansible and shell scripts, lint, syntax, and smoke-test badges are more useful.

## Cache And Offline Support

Caching is required for repeated client runs and environments with slow or
unreliable downloads.

Add:

- cache directory
- checksums
- pinned downloadable assets
- Phoronix cache support
- LTP source/archive cache support
- container image cache/pull policy
- cache validation command
- offline or preloaded mode

Example:

```bash
python -m hcs cache warm --profile medium
python -m hcs cache verify
python -m hcs run --profile medium --offline
```

## Preflight

Preflight should run before certification tests and decide what is supported,
what is missing, and what needs operator attention.

Preflight should collect:

- OS version
- kernel version
- architecture
- CPU model and flags
- memory
- disks
- NICs
- virtualization support
- RAID presence
- USB expectations
- PXE expectations
- free space
- internet/cache availability
- required packages
- locale
- time sync

Preflight output should include:

- `001-preflight.result.json`
- `001-preflight.console.log`
- `001-preflight.system.json`
- `001-preflight.report.txt`

Preflight should turn non-applicable tests into `unsupported` or `skipped`
instead of letting them fail later in confusing ways.

## ISV Extension Framework

MariaDB should not be a one-off hardcoded path. It should become the first
plugin/test pack in a reusable extension model.

Test registry fields:

- `test_id`
- `display_name`
- `category`
- `tags`
- `profiles`
- `executor`
- `required_tools`
- `preflight_checks`
- `metrics`
- `artifacts`
- `reporting`

Example:

```yaml
tests:
  isv_mariadb:
    display_name: MariaDB ISV test
    category: isv
    tags:
      - isv
      - mariadb
    profiles:
      medium:
        enabled: false
      long:
        enabled: true
    executor:
      type: ansible_tag
      tag: isv-mariadb
```

## Live USB

A Live USB image is valuable, but it should be built after the core workflow is
clean.

Dependencies:

- configurable work directories
- profiles
- runner
- reporting
- cache/offline support
- preflight

The Live USB should boot into a guided console runner first. GUI can come later.

## Implemented Foundation In This Fork

These roadmap items have already landed in the `xsub` fork and should now be
treated as the base for follow-up PRs:

- configurable sandbox directories and CPU `stress-ng --temp-path`
- profile registry from `check` through `extreme`
- Python/Rich runner core
- test listing and profile listing
- Rich console progress and planned step table
- repeated passes with per-pass artifacts
- stable per-step console/result file names
- plain-text `run.report.txt` and machine-readable `run.summary.json`
- `python -m hcs configure` preset prompt UI
- draft `certification` preset
- per-test profile and duration override support
- optional `gpu_burn` test with NVIDIA detection and snap workload support
- AlmaLinux 10 Phoronix dependency compatibility patch
- GitHub Actions and README badges
- product-first README plus detailed `docs/runner.md`

## Recommended Next PR Order

### PR 1: Preflight And Environment Doctor

Purpose: make the runner tell operators what is missing before a long run
starts.

Includes:

- `python -m hcs env doctor`
- `python -m hcs preflight`
- Python, Ansible, privilege, disk space, SELinux/FIPS, repository, EPEL/CRB,
  package availability, and writable-sandbox checks
- Phoronix/LTP/GPU Burn-specific readiness checks
- actionable remediation text
- preflight JSON artifact in the sandbox

### PR 2: Schema Validation And Artifact Contract Tests

Purpose: make reports and artifacts stable enough for automation, PR review,
and future GUI import.

Includes:

- JSON schemas for requested config, summary, per-step result, system identity,
  and future events
- pytest coverage for generated artifact paths and file names
- sample fixtures for passed, failed, unsupported, and dry-run steps
- documentation of compatibility guarantees

### PR 3: Effective Config And Manifest

Purpose: make every run fully reproducible from artifacts.

Includes:

- `config.effective.json`
- `run.manifest.json`
- runner version, git commit, Python version, Ansible version, OS facts, command
  line, selected preset/profile, resolved tests, extra vars, and path map
- manifest checksums for key report files

### PR 4: Cache And Offline Support

Purpose: make client-site and repeated lab runs reliable when the network is
slow, restricted, or absent.

Includes:

- cache warm/verify commands
- checksums for downloaded assets
- offline mode
- Phoronix, LTP, container, GPU Burn, and package cache strategy
- clear reporting when a test cannot run because required cached assets are
  missing

### PR 5: Event Stream, Resume, And Checkpointing

Purpose: make long runs safer and prepare the GUI.

Includes:

- `run.events.jsonl`
- typed runner events
- periodic checkpoints
- resumable runs where feasible
- graceful stop with partial report
- replay support for console and GUI views

### PR 6: Burn-In Telemetry Profiles

Purpose: turn HCS into a credible long-running stability and acceptance tool.

Includes:

- `burn_in_short`, `burn_in_medium`, `burn_in_long`, `continuous`,
  `post_change`, and `rma_triage` presets or profile family
- periodic sampling for thermals, clocks, memory pressure, disk health,
  network counters, kernel logs, and GPU telemetry where available
- report sections for spikes, warnings, throttling, resets, and variance
- partial report snapshots for multi-day runs

### PR 7: GPU Track Phase 2

Purpose: make AlmaLinux more attractive for AI, CUDA, and VFX-ready systems.

Includes:

- `gpu_detection` facts independent of GPU Burn
- `nvidia_driver` validation for AlmaLinux native NVIDIA packages
- optional CUDA smoke test when toolchain is present
- richer GPU telemetry and Xid/ECC/error analysis
- future room for ROCm, oneAPI, Vulkan, Blender, and Phoronix GPU suites

### PR 8: GUI-Ready Run Store

Purpose: give the future PyQt5 GUI a clean backend instead of scraping text.

Includes:

- run index/database under a configured lab directory
- import of historical sandbox runs
- query APIs for runs, steps, artifacts, metrics, warnings, and comparisons
- report export hooks

### PR 9: PyQt5 Analysis GUI

Purpose: provide the enhanced visual runner and analysis tool after the CLI
contracts are stable.

Includes:

- live run dashboard
- test selection and preset editor
- artifact browser
- charts for repeated passes
- outlier/spike analysis
- bottleneck exploration
- report export

### PR 10: Extension Framework And Live Media

Purpose: grow beyond the core AlmaLinux certification runner.

Includes:

- plugin/test-pack registry
- MariaDB or another ISV pack as the first concrete extension
- generic Linux compatibility labels for tests
- Live USB or appliance-style deployment once cache/offline and preflight are
  mature

## Near-Term Recommendation

The next best mergeable step is preflight/environment doctor plus schema
validation. Those two pieces make the current runner safer for client
installations, make failures easier to understand, and create the stable data
contracts needed for cache/offline, resume, burn-in telemetry, and the future
PyQt5 GUI.

Keep GUI work behind the data contracts. The GUI should consume the same run
events, summaries, metrics, and artifacts as the CLI instead of becoming a
parallel implementation.
