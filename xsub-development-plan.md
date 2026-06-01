# Hardware Certification Suite Development Plan

This document captures a proposed development roadmap for turning the
AlmaLinux Hardware Certification Suite into a polished, client-runnable
certification platform.

The goal is not only to run tests. The suite should guide an operator through a
well-thought certification process, collect quality benchmark data, preserve raw
evidence, and produce consistent reports that AlmaLinux can use for review,
comparison, and long-term certification records.

## Guiding Principles

- Keep Ansible as the low-level executor for remote/local system actions.
- Add a Python runner as the suite control plane.
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

- `#21` Stop using `/root` for Phoronix download/test location: still valid.
  Current defaults still place Phoronix, LTP, copied tests, and logs under
  `/root` or root-adjacent locations.
- `#10` Make CPU test use `--temp-path`: still valid. `stress-ng` should use a
  controlled scratch directory.
- `#7` Deprecated Ansible `include`: mostly fixed on current upstream `main`,
  but still relevant to older branch work such as the MariaDB/ISV branch.
- `#22` Reduce runtime: valid, but should become a profile system rather than
  random test removal.
- `#20` Cache downloadable test files: valid. This becomes important for client
  installs, repeated test passes, and offline or unreliable-network
  environments.
- `#19` Live USB image: valuable, but it should come after clean work
  directories, profiles, runner, cache, and reporting exist.
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
hcs run --profile check --target 192.168.1.50
hcs run --profile medium --inventory hosts.yml --config site.yml
hcs resume ./runs/latest
hcs report ./runs/latest
hcs validate ./runs/latest
```

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
normal certification run.

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
- add an explicit `hcs env doctor` command that validates the current venv,
  Ansible version, required Python packages, and expected runner entry points
- add an explicit `hcs env rebuild` command or wrapper script later that
  recreates a named venv before starting the runner
- never silently rebuild or delete the active venv as part of `hcs run`

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

Important config areas:

```yaml
certification:
  profile: medium
  work_dir: /var/tmp/almalinux-certification
  logs_dir: "{{ work_dir }}/logs"
  scratch_dir: "{{ work_dir }}/scratch"
  artifacts_dir: "{{ work_dir }}/artifacts"
  cache_dir: "{{ work_dir }}/cache"

target:
  inventory: null
  host: 127.0.0.1
  connection: local

runner:
  resume: true
  stop_on_failure: false
  collect_raw_logs: true
  collect_metrics: true

reporting:
  formats:
    - txt
    - md
  include_raw_artifact_index: true
```

## Work Directory Layout

The suite should not default to `/root` for working data.

Recommended default:

```text
/var/tmp/almalinux-certification/
  cache/
  scratch/
  runs/
  tmp/
```

Each run should get its own directory:

```text
runs/20260601T101530Z-medium-host01/
  run.manifest.json
  run.summary.json
  run.events.jsonl
  run.report.txt
  run.report.md
  config.requested.yml
  config.effective.yml
  preflight.system.json
  tests/
```

## Artifact Contract

All test artifacts should use unified names. Tool-native artifacts are allowed,
but they should be copied or linked into the suite artifact tree with normalized
names.

Filename pattern:

```text
<step-number>-<test-id>[.attempt-NNN].<artifact-type>.<extension>
```

Examples:

```text
001-preflight.result.json
001-preflight.console.log
002-hw-detection.hardware.json
003-cpu.attempt-001.result.json
003-cpu.attempt-001.console.log
003-cpu.attempt-001.stress-ng.log
004-network.attempt-002.iperf3.json
004-network.metrics.json
006-phoronix.native-result.json
006-phoronix.report.pdf
007-ltp.full.log
```

Every test should produce at least:

- `NNN-test-id.result.json`
- `NNN-test-id.console.log`

Optional artifacts:

- `metrics.json`
- `report.txt`
- `report.md`
- native logs
- native JSON
- native PDF
- screenshots or images if a future test needs them

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
- support offline/local repository paths
- record every repository and package installed
- detect Secure Boot and DKMS/kernel-devel prerequisites before modifying the
  system
- produce a clear warning when driver installation would make the system
  non-compliant with the operator's policy

Baseline `gpu_burn` workload design:

- do not install NVIDIA drivers implicitly in the first implementation
- check `nvidia-smi` first and report `unsupported` when NVIDIA drivers or GPUs
  are not available
- use a configured/prebuilt `gpu_burn` binary when present
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
hcs cache warm --profile medium
hcs cache verify
hcs run --profile medium --offline
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

## Recommended PR Order

### PR 1: Configurable Work Directories And CPU Temp Path

Purpose: make runtime state safe and predictable.

Includes:

- `work_dir`, `logs_dir`, `scratch_dir`, `artifacts_dir`, `cache_dir`
- no `/root` defaults for Phoronix, LTP, copied tests, or scratch data
- `stress-ng --temp-path`
- no `0777` copy permissions
- README update

Closes or addresses:

- `#21`
- `#10`

Suggested branch:

```text
fix/configurable-workdir
```

### PR 2: Profile YAML And Test Registry

Purpose: define `check`, `short`, `medium`, `long`, `very_long`, and `extreme`.

Includes:

- profile schema
- test registry
- effective config generation
- documentation

### PR 3: Artifact Naming And Result Schema

Purpose: enforce enterprise-quality output consistency.

Includes:

- artifact contract
- result JSON schema
- manifest schema
- initial validators

### PR 4: Python Runner Core

Purpose: introduce the headless control plane.

Includes:

- config loader
- test planner
- executor wrapper
- event emitter
- artifact manager
- resume model skeleton

### PR 5: Rich-Based Console Runner

Purpose: make client runs easy to observe.

Includes:

- live progress
- current test/attempt
- test list
- elapsed time
- log tail
- artifact pointers

### PR 6: Repetition And Aggregation

Purpose: support multiple attempts and benchmark-quality summaries.

Includes:

- per-test repetitions
- per-attempt artifact directories
- aggregate metrics
- variance warnings

### PR 7: Plain-Text And Markdown Reports

Purpose: produce engineering-friendly reports.

Includes:

- `run.report.txt`
- `run.report.md`
- report footers
- timestamps
- versions
- manifest checksum

### PR 8: Internal Tests And Badges

Purpose: validate the suite itself.

Includes:

- CI workflow
- lint checks
- schema tests
- artifact contract tests
- initial coverage badge for Python code

### PR 9: Cache And Offline Support

Purpose: make repeated and client-site runs reliable.

Includes:

- cache warm/verify
- checksums
- offline mode
- Phoronix/LTP/container asset strategy

### PR 10: ISV Extension Framework

Purpose: support MariaDB and future ISV tests cleanly.

Includes:

- plugin/test-pack registry
- MariaDB migration
- ISV documentation

### PR 11: Live USB

Purpose: simplify client-site certification setup.

Includes:

- bootable certification environment
- preloaded cache
- guided console runner

### PR 12: GUI

Purpose: analysis and visualization frontend.

Includes:

- run browser
- live dashboard
- graphs
- multi-pass comparison
- spike/outlier analysis
- bottleneck exploration
- report export

## Near-Term Recommendation

Start with a small, mergeable fix branch for work directories and CPU temp path.

That creates immediate value, closes still-valid issues, and prepares the
ground for profiles, artifacts, runner, reports, and eventually the GUI.

After that, implement profiles and the artifact contract before building the
runner UI. The UI will be much better if the suite already knows what a test is,
where its artifacts go, and how to report status consistently.
