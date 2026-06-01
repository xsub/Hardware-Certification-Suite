# Changelog

## 2026-06-01 - README product-first structure

- Reworked the README opening into a product-first flow with a short
  certification value statement, minimal install commands, fast `check` run,
  and one-command `certification` preset path before deeper operator details.
- Renamed the roadmap file to `DevelopmentPlan.md` and updated the README
  roadmap link.
- Updated `DevelopmentPlan.md` so the roadmap starts from the current fork
  baseline, marks landed runner/sandbox/preset/GPU Burn work, refreshes issue
  triage, and defines the next PR sequence around preflight, schemas, cache,
  events, burn-in telemetry, GPU phase 2, and GUI readiness.
- Renamed the README value table headers to `HCS Features` and
  `Provides / Value`.
- Removed the AlmaLinux identity row from the README feature table to keep the
  top-level value list tighter.
- Reduced the README to a concise onboarding page and moved detailed runner,
  Ansible, preset, GPU Burn, sandbox, remote SUT, profile, and variable
  reference material into `docs/runner.md`.
- Condensed the runner console preview while keeping the AlmaLinux identity
  header, planned steps, repeated pass output, artifact names, and final
  report summary visible near the top.
- Removed the repository-local `.vscode` settings file and ignored `.vscode/`
  so editor state does not return to the fork.
- Replaced validation machine wording in TODO with generic "validation host"
  wording.

## 2026-06-01 - certification policy preset

- Added a built-in `certification` runner preset for ordinary automated
  AlmaLinux hardware certification evidence.
- The preset marks required automated tests separately from optional automated
  tests and records manual USB/PXE checks that remain outside the automated
  runner.
- Runner plans, requested config, JSON step results, JSON summaries, and
  plain-text reports now include a per-test scope such as `required`,
  `optional`, or `profile`.
- Local `hcs-runner.yml` can override the built-in `certification` preset when
  Certification SIG or ALOSF policy changes.
- Updated README and the example runner config with the certification preset
  and text preview.

## 2026-06-01 - interactive presets and GPU Burn snap support

- Added `hcs configure`, a Rich prompt UI for creating named runner presets in
  `hcs-runner.yml`.
- Presets can enable/disable tests, assign a profile from `check` through
  `extreme` per test, set duration caps, configure repeat count, and become the
  default preset for `hcs run`.
- The runner now loads `run.default_preset` automatically, while an explicit
  `--profile` keeps the classic profile-based test list unless `--preset` is
  also supplied.
- Added per-test profile and per-test extra-var support to the runner command
  builder.
- Added GPU Burn snap support: use an existing `gpu-burn` snap, optionally
  install it when `snapd` is present and the preset allows it, and optionally
  remove the snap at the end when HCS installed it.
- Added duration-cap handling so a saved test duration and selected profile use
  the more restrictive runtime where both are present.
- Updated the example runner YAML, README, GPU Burn docs, and development plan
  for named presets and snap-based GPU Burn setup.
- Added README text screenshots for the preset configuration prompts, saved
  YAML, and dry-run test plan preview.

## 2026-06-01 - AlmaLinux native NVIDIA guidance

- Added AlmaLinux 9/10 native NVIDIA package guidance to the GPU Burn workflow.
- When `gpu_burn` runs on AlmaLinux 9/10 without `nvidia-smi`, the unsupported
  reason now points operators at `almalinux-release-nvidia-driver`,
  `nvidia-open-kmod`, `nvidia-driver`, and `nvidia-driver-cuda`.
- Documented the native driver preparation commands in README and the GPU Burn
  test README.
- Updated the development plan so future NVIDIA driver validation/install
  work uses AlmaLinux's native package path first, while keeping automatic
  driver installation behind an explicit operator-controlled flag.

## 2026-06-01 - built-in system identity header

- Added a built-in neofetch-style runner header for AlmaLinux controllers.
- The runner now prints the AlmaLinux ASCII logo together with a system
  identity table covering OS, host, kernel, uptime, RPM package count, Python
  mode, shell, CPU, GPU, memory, swap, root filesystem, local IP, locale,
  SELinux, and FIPS state when available.
- The header does not require installing `fastfetch`, `neofetch`, or any
  system-wide package; optional `fastfetch` logo support remains a presentation
  enhancement when it already exists.
- Added controller system identity to `config.requested.json`,
  `run.summary.json`, and `run.report.txt` so the console header is preserved
  as auditable certification evidence.
- Added unit coverage for memory, swap, uptime, default route, and supplied OS
  summary behavior.
- Updated the development plan with explicit Python environment
  reproducibility guidance, including future `hcs env doctor` and
  `hcs env rebuild` style workflows.

## 2026-06-01 - GPU Burn test

- Added an optional `gpu_burn` runner/Ansible test for NVIDIA systems.
- The test checks for working NVIDIA drivers with `nvidia-smi` before doing any
  stress work.
- If NVIDIA drivers or GPUs are not available, the test emits
  `HCS_UNSUPPORTED` and the runner records the step as `unsupported` instead of
  marking the machine failed.
- The test can use a configured/prebuilt `gpu_burn` binary or clone/build the
  open source GPU Burn workload into the HCS cache when `git`, `make`, and
  `nvcc` are available.
- Added GPU Burn logs, NVIDIA telemetry CSV, and JSON result artifacts under
  the HCS sandbox.
- Updated the runner summary model so unsupported tests produce a
  `passed_with_warnings` run status unless another step fails.
- Updated README and the development plan to position custom CUDA/render
  workloads as later optional extensions, with GPU Burn as the first pragmatic
  open source baseline.

## 2026-06-01 - generic Linux and accelerator roadmap

- Added distro-aware runner logo support.
- The runner now attempts to use `fastfetch` for the detected Linux
  distribution when available.
- Added a built-in AlmaLinux ASCII logo fallback for AlmaLinux systems where
  `fastfetch` is not installed.
- Added unit coverage for `/etc/os-release` parsing and AlmaLinux logo
  fallback behavior.
- Updated the development plan with a more generic Linux positioning: keep the
  project AlmaLinux-first while making runner patterns, artifact contracts, and
  burn-in workflows useful for other Linux projects.
- Added roadmap sections for distribution identity, portability, enterprise
  burn-in, continuous validation, post-change validation, RMA triage, and
  long-running system readiness testing.
- Added an AI/GPU/CUDA/VFX workload track proposal covering GPU detection,
  NVIDIA driver validation, CUDA smoke/burn tests, telemetry collection, and
  future graphics workloads such as AlmaLinux-branded 3D render scenes.

## 2026-06-01 - xsub fork development delta

This entry summarizes the work currently present in the
`xsub/Hardware-Certification-Suite` fork compared with
`AlmaLinux/Hardware-Certification-Suite` upstream `main`.

### Runner and user experience

- Added a Python/Rich runner package under `hcs/`.
- Added runner commands for listing profiles, listing tests, and running test
  plans through Ansible.
- Added Rich progress output with a visible suite plan, current pass, current
  step, overall progress, and final run summary.
- Added built-in run profiles:
  `check`, `short`, `medium`, `long`, `very_long`, and `extreme`.
- Added runner support for selected tests, repeated passes, dry-runs,
  stop-on-failure behavior, and extra Ansible variables.
- Added Ansible recap parsing so `failed`, `unreachable`, or `ignored` tasks
  make a runner step fail even when Ansible itself exits successfully.
- Added Python unit coverage for default runner configuration loading.

### Sandboxed run layout

- Moved HCS-generated data into a single per-run sandbox directory:
  `AlmaLinux-HCS-<UTC timestamp>-RunID-<run id>`.
- Added canonical run subdirectories for runner data, logs, scratch space,
  cache, artifacts, copied SUT tests, Phoronix data, and LTP data.
- Added `hcs-runner.example.yml` as the shared runner configuration template.
- Added automatic loading of local `hcs-runner.yml` so lab defaults such as
  `run.base_dir` do not need to be passed on every command.
- Added `hcs-runner.yml` to `.gitignore` because it is host/lab-specific local
  configuration.
- Preserved CLI overrides for automation and debugging, while documenting YAML
  as the normal configuration path.

### Reports and artifacts

- Added a consistent runner artifact layout under `<sandbox>/runner/`.
- Added `config.requested.json` with requested profile, inventory, repeat
  count, variables, selected tests, and effective paths.
- Added per-step console logs using stable names:
  `tests/NNN-passNN-test_id/NNN-passNN-test_id.console.log`.
- Added per-step JSON result files using stable names:
  `tests/NNN-passNN-test_id/NNN-passNN-test_id.result.json`.
- Added `run.summary.json` for machine-readable run summaries.
- Added `run.report.txt` as the plain-text engineering report with timestamps,
  runner version, status, pass index, durations, return codes, and result
  reasons.
- Captured repeated test passes independently while also producing a final
  aggregate run summary.

### GitHub Actions and badges

- Added repository-level CI for YAML validation, shell syntax checks, and
  Ansible syntax checks.
- Added Python runner smoke CI for Python `3.11`, `3.12`, and `3.14`.
- Added AlmaLinux container smoke CI for AlmaLinux `8`, `9`, and `10`.
- Added a dedicated Ansible syntax-check workflow.
- Added validation helper scripts under `.github/scripts/`.
- Added README badges for CI, Python, Ansible, and AlmaLinux workflows.

### Ansible and test execution changes

- Updated `automated.yml` to create and use the sandbox directories before
  running test roles.
- Updated `vars.yml` with HCS sandbox variables for run ID, timestamp, base
  directory, sandbox root, scratch directory, cache directory, artifacts
  directory, logs directory, copied SUT test directory, Phoronix directory, and
  LTP directory.
- Updated CPU test execution so stress-ng logs and scratch data are written
  under the active sandbox instead of ad-hoc locations.
- Updated LTP configuration and logs to use the sandbox scratch area.
- Updated Phoronix execution to use the sandbox work directory and scratch log
  path.
- Added AlmaLinux 10 Phoronix dependency adjustments for package name changes
  and unavailable dependencies.
- Updated network test messaging so users look for logs in the run log
  artifacts rather than a hard-coded legacy path.

### Documentation

- Reworked the README structure around the normal runner workflow.
- Added a real runner output excerpt from an AlmaLinux 10.2 test system using
  Python `3.14`, showing the generated run ID, sandbox path, pass results, recap
  counters, durations, and final report summary.
- Moved that runner output near the README introduction so users see the suite
  result before setup details.
- Documented the official AlmaLinux Hardware Certification Program context and
  clarified that a local passing run is evidence for SIG review, not automatic
  certification by itself.
- Documented AlmaLinux 10 setup, Python `3.12` platform usage, optional CRB
  enablement for newer Python such as `3.14`, virtualenv setup, Ansible
  installation, tmux usage, and runner invocation.
- Documented how to run one test and full profiles through the runner.
- Documented how to run one test and full automated sets directly through
  Ansible for low-level debugging.
- Documented local and remote LTS/SUT terminology and runner configuration.
- Clarified sandbox log collection for local and remote runs.
- Documented Python `3.11+` as the intended minimum runner support level.

### Planning

- Added `DevelopmentPlan.md` with the broader roadmap for turning the
  suite into a repeatable, client-friendly, enterprise-grade hardware
  certification runner.
- The plan covers run profiles, global YAML configuration, sandboxing,
  repeatable passes, artifact naming, plain-text reports, structured JSON,
  future GUI integration, multi-pass analysis, outlier detection, graphs,
  internal testing, and CI/quality badges.

### Known follow-ups

- Add `pyproject.toml` so the runner can be installed as a normal Python
  package and exposed as an `hcs` console script.
- Add coverage reporting and a coverage badge once the Python test suite grows.
- Expand internal runner tests beyond configuration loading.
- Define and version the report JSON schema.
- Add richer multi-pass analysis for averages, spikes, outliers, and
  bottleneck detection.
- Keep GUI work as a later layer on top of the CLI runner model.
