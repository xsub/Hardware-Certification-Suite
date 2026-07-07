# Runner And Operator Reference

This document is the detailed operator reference for the AlmaLinux Hardware
Certification Suite runner. The product-oriented quick start lives in
[README.md](../README.md).

## Compatibility

The suite targets AlmaLinux and is validated on **AlmaLinux 10.2**. The required
automated tests have been run end to end on AlmaLinux 10.2 and behave as
designed:

| Test | AlmaLinux 10.2 result |
| --- | --- |
| `hw_detection` | passed; requires root (SMBIOS/DMI via `/dev/mem`) and fails loudly without it |
| `containers` | passed (podman; only newly installed packages removed afterward) |
| `kvm` | passed where CPU virtualization is present; `unsupported` where it is not |
| `cpu` | passed (`stress-ng`; operator-preinstalled packages left in place) |
| `network` | `unsupported` on a single host; runs over SSH against a distinct SUT |
| `ltp` | passed; builds the modern `20250930` tag (override with `ltp_version`) |
| `phoronix` | space-bound (100–300 GB); `unsupported` with the available/required sizes when capacity is missing |
| `raid` | stresses only unmounted, signature-free MD arrays by default; `raid_allow_data_loss=true` overrides |

Tests that install packages snapshot the installed set first and remove only
what they added, so a certification run leaves the SUT's package set as it
found it.

CI additionally smoke-tests the runner and Ansible syntax on AlmaLinux 8, 9, and
10, and runs the `check` profile plus the single-host `network` path
functionally on AlmaLinux 9 and 10. Python `3.9+` is required, so the runner
works on AlmaLinux 9's platform Python `3.9` and AlmaLinux 10's `3.12` without
installing a newer interpreter.

## Running Tests

Use the runner for normal certification work. It wraps Ansible, creates one
sandbox per run, streams progress with Rich, writes per-step artifacts, parses
Ansible recap counters, supports repeated passes, and produces the final
plain-text report. The runner currently wraps `automated.yml`; interactive
USB and PXE tests are run directly with Ansible.

Keep lab-wide runner defaults in `hcs-runner.yml`. The runner loads this file
automatically from the repository directory, so normal commands do not need a
manual timestamp, run ID, or base directory.

The local host is the default target, so the examples below omit inventory and
connection flags. The runner infers the Ansible connection from the inventory:
a loopback inventory (`127.0.0.1,`) runs with the local connection, and a
remote `--host <SUT IP>` runs over SSH. Use `--inventory` / `-c` only to take
explicit control, for example a real inventory file or a non-default
connection plugin.

List available runner profiles and test IDs:

```bash
python -m hcs profiles
python -m hcs tests
```

Build or update a named runner preset with the Rich prompt UI:

```bash
python -m hcs configure --preset default
python -m hcs run --preset default
```

Preview the draft certification preset:

```bash
python -m hcs run --preset certification
python -m hcs run --preset certification --dry-run
```

`certification` is a draft preset for ordinary automated hardware certification
evidence. It models the current suite areas for SIG review, runs the proposed
required automated checks by default, and declares optional automated checks in
the preset schema. Local `hcs-runner.yml` can override this preset when the SIG
or a lab wants to test a different policy.

`hcs configure` stores the preset in `hcs-runner.yml`. It asks which tests to
include, which profile each selected test should use, optional duration caps,
and GPU Burn snap behavior. When `run.default_preset` is set, `python -m hcs
run` reads that preset automatically. Passing `--profile` explicitly uses the
profile's normal test list unless `--preset` is also supplied.

Configuration selection example:

```text
$ python -m hcs configure --preset gpu-burn-check

Preset name (gpu-burn-check): gpu-burn-check
Base profile [check/short/medium/long/very_long/extreme] (check): check
Inventory (127.0.0.1,): 127.0.0.1,
Connection (auto = local for loopback, SSH for a remote host) [auto/local/ssh/smart/paramiko] (auto): auto
Repeat passes (1): 2

Select tests
Use Enter to accept defaults. Each selected test can use its own profile.

[x] Hardware detection (hw_detection, optional) [y/n] (y): y
  Profile for hw_detection [check/short/medium/long/very_long/extreme] (check): check

[ ] Containers (containers, optional) [y/n] (n): n
[ ] KVM (kvm, optional) [y/n] (n): n
[ ] CPU stress (cpu, optional) [y/n] (n): n
[ ] Network (network, optional) [y/n] (n): n
[ ] MD RAID (raid, optional) [y/n] (n): n
[ ] Linux Test Project (ltp, optional) [y/n] (n): n
[ ] Phoronix (phoronix, optional) [y/n] (n): n

[ ] GPU Burn (gpu_burn, optional) [y/n] (n): y
  Profile for gpu_burn [check/short/medium/long/very_long/extreme] (check): medium
  Duration cap (empty = profile default): 5m
  Allow installing gpu-burn snap when snapd exists and no binary is available [y/n] (n): y
  Remove gpu-burn snap at the end if HCS installed it [y/n] (y): y

[ ] CloudLinux limits (cllimits, optional) [y/n] (n): n

Saved preset gpu-burn-check to hcs-runner.yml
Run it with: python -m hcs run --preset gpu-burn-check
```

Saved preset excerpt:

```yaml
run:
  base_dir: /var/tmp
  default_preset: gpu-burn-check

presets:
  gpu-burn-check:
    profile: check
    inventory: 127.0.0.1,
    repeat: 2
    tests:
      hw_detection:
        enabled: true
        required: false
        profile: check
      gpu_burn:
        enabled: true
        required: false
        profile: medium
        duration: 5m
        snap:
          package: gpu-burn
          install: true
          remove_after: true
```

Plan preview from the saved preset. The identity header is omitted here so the
example focuses on test selection:

```text
$ python -m hcs run --preset gpu-burn-check --dry-run

╭─────────────────── AlmaLinux Hardware Certification Suite ───────────────────╮
│ Profile: check                                                               │
│ Mode: Fast sanity pass for runner, inventory, and hardware discovery.        │
│ Run ID: check-4f21a9c0                                                       │
│ Sandbox: /var/tmp/AlmaLinux-HCS-20260601T131500Z-RunID-check-4f21a9c0        │
│ Runner artifacts:                                                            │
│ /var/tmp/AlmaLinux-HCS-20260601T131500Z-RunID-check-4f21a9c0/runner          │
│ Inventory: 127.0.0.1,                                                        │
╰──────────────────────────────────────────────────────────────────────────────╯
             Planned certification steps
┏━━━━━┳━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━┳━━━━━━━━━━┓
┃   # ┃ Test               ┃ Tag          ┃ Profile ┃ Scope    ┃
┡━━━━━╇━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━╇━━━━━━━━━━┩
│ 001 │ Hardware detection │ hw_detection │ check   │ optional │
│ 002 │ GPU Burn           │ gpu_burn     │ medium  │ optional │
└─────┴────────────────────┴──────────────┴─────────┴──────────┘
Repeat: 2 passes, 4 total steps

SKIP 001 pass=01/02 Hardware detection
SKIP 002 pass=01/02 GPU Burn
SKIP 003 pass=02/02 Hardware detection
SKIP 004 pass=02/02 GPU Burn

run.report.txt
  Status: passed
  Results:
    001 pass=01/02 hw_detection  optional  skipped  0.0s rc=None dry-run
    002 pass=01/02 gpu_burn      optional  skipped  0.0s rc=None dry-run
    003 pass=02/02 hw_detection  optional  skipped  0.0s rc=None dry-run
    004 pass=02/02 gpu_burn      optional  skipped  0.0s rc=None dry-run
```

Draft certification preset preview:

```text
$ python -m hcs run --preset certification --dry-run

╭─────────────────── AlmaLinux Hardware Certification Suite ───────────────────╮
│ Preset: certification                                                        │
│ Profile: long                                                                │
│ Mode: Extended certification pass with LTP and Phoronix.                     │
│ Run ID: long-31bda138                                                        │
│ Sandbox: /var/tmp/AlmaLinux-HCS-20260601T132150Z-RunID-long-31bda138         │
│ Runner artifacts:                                                            │
│ /var/tmp/AlmaLinux-HCS-20260601T132150Z-RunID-long-31bda138/runner           │
│ Inventory: 127.0.0.1,                                                        │
╰──────────────────────────────────────────────────────────────────────────────╯
                  Planned certification steps
┏━━━━━┳━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━┳━━━━━━━━━━┓
┃   # ┃ Test               ┃ Tag          ┃ Profile ┃ Scope    ┃
┡━━━━━╇━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━╇━━━━━━━━━━┩
│ 001 │ Hardware detection │ hw_detection │ check   │ required │
│ 002 │ Containers         │ containers   │ medium  │ required │
│ 003 │ KVM                │ kvm          │ medium  │ required │
│ 004 │ CPU stress         │ cpu          │ long    │ required │
│ 005 │ Network            │ network      │ long    │ required │
│ 006 │ Linux Test Project │ ltp          │ long    │ required │
│ 007 │ Phoronix           │ phoronix     │ long    │ required │
└─────┴────────────────────┴──────────────┴─────────┴──────────┘

Optional automated tests declared by this preset:
  raid       Run when MD RAID or storage topology is relevant.
  gpu_burn   Run when supported NVIDIA GPUs and nvidia-smi are available.
  cllimits   Run only for CloudLinux-specific validation.

Manual certification checks tracked outside the automated runner:
  usb        Interactive physical-port validation through interactive.yml.
  pxe        Interactive boot/network validation through interactive.yml.
```

Run preflight before a long run:

```bash
python -m hcs preflight --preset certification --host <SUT IP> \
  --lts-ip <LTS IP> --sut-ip <SUT IP>
```

Preflight checks the Python runtime, `ansible-playbook`, the playbook path,
sandbox writability, free space, local privileges for `hw_detection`, network
endpoint readiness, and any existing run artifacts in the target sandbox.
Errors return a non-zero exit code. Warnings do not block the command, but they
call out things an operator should resolve before treating the run as public
submission evidence.

Run one automated test locally through the runner:

```bash
python -m hcs run --profile short --test cpu
```

Run several selected tests locally through the runner:

```bash
python -m hcs run --profile medium \
  --test hw_detection --test cpu --test network
```

Run all tests from a runner profile:

```bash
python -m hcs run --profile medium
```

Run the fullest built-in AlmaLinux automated profile, including LTP and
Phoronix:

```bash
python -m hcs run --profile extreme
```

Run the same profile against a remote SUT over SSH:

```bash
python -m hcs run --profile extreme --host <SUT IP>
```

Repeat the selected plan and keep data from every pass:

```bash
python -m hcs run --profile check --repeat 3
```

Override an Ansible variable while using the runner. `--extra-var` always has
the last word: it overrides profile, config, and preset per-test values
(including preset duration caps).

```bash
python -m hcs run --profile medium --extra-var cpu_duration=20m
```

Cap how long any single step may run. A step that exceeds the limit is
terminated (SIGTERM, then SIGKILL) and recorded as failed; the rest of the
plan continues. Set it once in `hcs-runner.yml` with `run.step_timeout`, or
per run:

```bash
python -m hcs run --preset certification --step-timeout 4h
```

Run the optional NVIDIA [GPU Burn](https://github.com/wilicc/gpu-burn) test.
This test is not part of the default profiles; it records `unsupported` when
NVIDIA drivers are not installed.

```bash
python -m hcs run --profile check --test gpu_burn
```

On AlmaLinux 9 and 10, NVIDIA driver setup is now an AlmaLinux-native package
flow with Secure Boot-capable open GPU kernel module support. Prepare a
machine for `gpu_burn` with:

```bash
dnf install almalinux-release-nvidia-driver
dnf install nvidia-open-kmod nvidia-driver nvidia-driver-cuda
reboot
nvidia-smi
```

The full AlmaLinux instructions are maintained in the
[NVIDIA driver documentation](https://wiki.almalinux.org/documentation/nvidia.html).
HCS does not install these drivers automatically today; it detects the driver
state, records `unsupported` when `nvidia-smi` is missing, and points the
operator at the native AlmaLinux setup path.

If `snapd` is already available on the SUT, GPU Burn can also be supplied by
the Snap Store package. The runner only enables this when the selected preset
asks for it:

```yaml
presets:
  default:
    tests:
      gpu_burn:
        enabled: true
        profile: check
        duration: 60
        snap:
          package: gpu-burn
          install: true
          remove_after: true
```

At runtime the test uses an existing `gpu-burn` binary first, then an installed
`gpu-burn` snap, then installs the snap only when `install: true`. If HCS
installed the snap and `remove_after: true`, it removes the snap at the end of
the test. The GPU driver is still a prerequisite; the snap supplies the GPU
Burn workload, not the NVIDIA driver.

Use Ansible directly only for low-level debugging or when you intentionally do
not need runner reports. Direct Ansible runs still use the sandbox defaults in
`vars.yml`, but they do not create runner JSON summaries, repeated-pass
reports, or Rich progress output.

Run one automated test locally with Ansible:

```bash
ansible-playbook -c local -i 127.0.0.1, automated.yml --tags cpu
```

Run one automated test on a remote SUT with Ansible:

```bash
ansible-playbook -i <SUT IP>, -u root automated.yml --tags cpu
```

Run several automated tests with Ansible:

```bash
ansible-playbook -c local -i 127.0.0.1, automated.yml \
  --tags hw_detection,cpu,network
```

Run the optional NVIDIA GPU Burn test directly with Ansible:

```bash
ansible-playbook -c local -i 127.0.0.1, automated.yml --tags gpu_burn
```

Run the default automated Ansible set. This runs the ordinary automated tags
but does not run `ltp` or `phoronix`, because those tasks are tagged `never`
and must be selected explicitly.

```bash
ansible-playbook -c local -i 127.0.0.1, automated.yml
```

Run the fullest built-in AlmaLinux automated Ansible set, including LTP and
Phoronix:

```bash
ansible-playbook -c local -i 127.0.0.1, automated.yml \
  --tags hw_detection,containers,kvm,cpu,network,raid,ltp,phoronix
```

Run the same full automated set on a remote SUT:

```bash
ansible-playbook -i <SUT IP>, -u root automated.yml \
  --tags hw_detection,containers,kvm,cpu,network,raid,ltp,phoronix
```

The `cllimits` tag is CloudLinux-specific. It is not part of the AlmaLinux
full automated set and is skipped on AlmaLinux systems.

Override the direct Ansible sandbox when needed:

```bash
ansible-playbook -c local -i 127.0.0.1, automated.yml \
  --extra-vars "sandbox_dir=/mnt/certification/run-001"
```

Run all interactive tests:

```bash
ansible-playbook -i <SUT IP>, -u root interactive.yml
```

Run one interactive test family directly:

```bash
ansible-playbook -i <SUT IP>, -u root tests/usb/step1.yml tests/usb/step2.yml
ansible-playbook -i <SUT IP>, -u root tests/pxe/step1.yml tests/pxe/step2.yml
```

## AlmaLinux 10 Setup

AlmaLinux 10 includes platform Python 3.12. CRB can be enabled when you want a
newer interpreter such as Python 3.14.

```bash
dnf -y install git tmux python3.12

# Optional: enable CRB and install Python 3.14.
dnf -y install dnf-plugins-core
dnf config-manager --set-enabled crb
dnf -y install python3.14 python3.14-pip

git clone https://github.com/xsub/Hardware-Certification-Suite.git
cd Hardware-Certification-Suite

# Use python3.12 if you prefer the platform Python.
PYTHON=python3.14

$PYTHON -m venv venv-almalinux-certification-suite
source venv-almalinux-certification-suite/bin/activate
pip install "ansible-core>=2.17,<2.18"
pip install -e .   # runner deps + the `hcs` command; or: pip install -r requirements-runner.txt
cp hcs-runner.example.yml hcs-runner.yml

# Optional for larger runs: edit hcs-runner.yml and set run.base_dir: /var/tmp

tmux new-session -s almalinux-certification-tests
python -m hcs run --profile check
```

## Run Profiles

| Profile | Purpose | Tests |
| --- | --- | --- |
| `check` | Fast sanity pass for runner, inventory, and hardware discovery. | `hw_detection` |
| `short` | Short functional pass for early feedback. | `hw_detection`, `containers`, `kvm`, `cpu` |
| `medium` | Practical default certification pass. | `hw_detection`, `containers`, `kvm`, `cpu`, `network`, `raid` |
| `long` | Extended certification pass with LTP and Phoronix. | `hw_detection`, `containers`, `kvm`, `cpu`, `network`, `raid`, `ltp`, `phoronix` |
| `very_long` | Long soak-oriented pass. | `hw_detection`, `containers`, `kvm`, `cpu`, `network`, `raid`, `ltp`, `phoronix` |
| `extreme` | Maximum built-in coverage and duration. | `hw_detection`, `containers`, `kvm`, `cpu`, `network`, `raid`, `ltp`, `phoronix` |

Useful runner commands:

```bash
python -m hcs --version
python -m hcs profiles
python -m hcs tests
python -m hcs run --help
```

`python -m hcs run` accepts `--host <SUT IP>` as shorthand for
`--inventory <SUT IP>,`. `--host` and `--inventory` are mutually exclusive.

## Run Sandbox

Each run owns one sandbox directory. By default:

```text
/var/tmp/AlmaLinux-HCS-<UTC timestamp>-RunID-<run id>
```

Everything created by HCS for that run belongs under that root:

| Path | Purpose |
| --- | --- |
| `runner/` | Runner JSON, plain-text reports, and per-step console logs. |
| `logs/` | Normalized test logs collected in the run sandbox. |
| `scratch/` | Temporary tool output. |
| `cache/` | Reusable downloads and local caches. |
| `artifacts/` | Structured test artifacts. |
| `sut-tests/` | Copied test scripts on the SUT. |
| `phoronix/` | Phoronix installation and result data. |
| `ltp/` | Linux Test Project checkout and build data. |

For remote LTS/SUT runs, Ansible transfers command output from the SUT into
the LTS/controller sandbox so results survive SUT cleanup. For local runs, the
same paths are used directly; no separate copy step is needed.

Configure the sandbox once per lab checkout:

```bash
cp hcs-runner.example.yml hcs-runner.yml
```

Edit `hcs-runner.yml`:

```yaml
run:
  base_dir: /var/tmp
  id:
  sandbox_dir:
```

`hcs-runner.yml` is auto-loaded when present. Leave `run.id` empty for an
auto-generated run ID. Leave `run.sandbox_dir` empty for the standard
`AlmaLinux-HCS-<UTC timestamp>-RunID-<run id>` directory name under
`run.base_dir`.

Use CLI overrides only when automation needs them:

```bash
python -m hcs run --config lab-runner.yml --profile check
python -m hcs run --profile check --run-id lab-run-001
python -m hcs run --profile check --sandbox-dir /mnt/certification/AlmaLinux-HCS-lab-run-001
```

`hcs-runner.example.yml` keeps all configurable child paths inside the sandbox
root by design.

## Reports And Artifacts

Runner artifacts live under `<sandbox>/runner/`.

| File | Purpose |
| --- | --- |
| `config.requested.json` | Requested profile, inventory, repeat count, variables, and effective paths. |
| `tests/NNN-passNN-test_id/NNN-passNN-test_id.console.log` | Streamed command output for one step. |
| `tests/NNN-passNN-test_id/NNN-passNN-test_id.result.json` | Structured result for one step. |
| `run.summary.json` | Machine-readable summary for the run. |
| `submission.manifest.json` | Proposed submission manifest mapping required and reviewer-convenience artifacts. |
| `run.report.txt` | Plain-text engineering report with timestamps and runner version. |
| `run.report.pdf` | Optional AlmaLinux-styled PDF rendering for review. Skipped if `reportlab` is unavailable. |

Run statuses are truthful by construction: a completed run keeps the
backward-compatible headline `status` of `passed`, `passed_with_warnings`
(some steps `unsupported`), or `failed`; an interrupted run is `interrupted`
and a `--dry-run` is `dry_run` — neither ever reads as `passed`. New tooling
should read the explicit result contract in `run.summary.json`:

- `run_verdict`: `passed`, `failed`, `incomplete`, `dry_run`, or `interrupted`.
- `certification_ready`: `true` only when the selected required evidence has
  pass/fail coverage and no blocking failures.
- `result_contract.blocking_reasons`: machine-readable reasons that prevent
  certification-ready evidence.
- `result_contract.review_notes`: non-blocking issues a reviewer may still
  want to inspect.

Steps planned but never executed (Ctrl-C, `--stop-on-failure`) appear as
`not_run` with the reason. When the preset declares manual tests (`usb`, `pxe`
in `certification`), all three reports list them explicitly as not executed by
the runner, so automated-only evidence states what it does not cover.

Reports also call out **required tests not exercised**: any required-scope
test that produced no pass/fail verdict in the run — unsupported, skipped,
never run, disabled in the preset, or filtered out with `--test` — is listed
in `run.summary.json` (`required_unexercised`), the text report, the console
recap, and the PDF. The runner additionally warns at startup about unknown
`hcs-runner.yml` keys (typos would otherwise be ignored silently) and about
preset durations above the profile cap.

JSON schemas for `config.requested.json`, per-step result JSON, and
`run.summary.json` are packaged under `hcs/schemas/`, along with the proposed
`submission.manifest.json` schema. They are intentionally the contract for
automation; text and PDF reports are renderings of the same evidence.

Validate a completed sandbox before preparing a public submission:

```bash
python -m hcs validate-run /var/tmp/AlmaLinux-HCS-20260601T115819Z-RunID-check-3248b3e5
```

Refresh the manifest and then validate it:

```bash
python -m hcs validate-run --write-manifest /var/tmp/AlmaLinux-HCS-20260601T115819Z-RunID-check-3248b3e5
```

The manifest currently records a conservative target hint,
`systems/<vendor>/<system-or-model>/<run-id>/`, for
`AlmaLinux/certifications`; the final public layout remains a SIG decision.

Before publishing evidence, run the privacy audit:

```bash
python -m hcs audit-artifacts /var/tmp/AlmaLinux-HCS-20260601T115819Z-RunID-check-3248b3e5
```

The audit looks for likely host-specific identifiers such as serial numbers,
MAC addresses, non-loopback IP addresses, DMI UUIDs, host fields, and storage
device IDs. Findings are printed with redacted samples so the audit itself does
not leak the value. Treat manifest privacy labels conservatively:

| Privacy label | Meaning |
| --- | --- |
| `safe` | Expected to be safe for public submission. |
| `review_before_publish` | Inspect for environment-specific identifiers before publishing. |
| `private_or_redacted` | Keep private unless the SIG requests it, or publish only after redaction. |

## Remote LTS/SUT

Use remote mode when the controller and SUT are different machines.

1. Ensure the LTS can SSH to the SUT.
2. Add the LTS public key to the SUT root account or configure another
   privileged account.
3. Verify connectivity:

```bash
ansible all -i <SUT IP>, -m ping -u root
```

Run a profile against the remote SUT over SSH:

```bash
python -m hcs run --profile check --host <SUT IP>
```

`--host <SUT IP>` is shorthand for `--inventory <SUT IP>,`; the runner infers
the SSH connection because the inventory is not loopback. The draft
`certification` preset works the same way: `python -m hcs run --preset
certification --host <SUT IP>`.

For network testing, prefer explicit endpoint addresses when the LTS and SUT
paths are known:

```bash
python -m hcs run --preset certification --host <SUT IP> \
  --lts-ip <LTS IP> --sut-ip <SUT IP>
```

The Ansible role can still infer endpoints from the remote SSH session, but
`--lts-ip` and `--sut-ip` make the evidence and command line explicit. The
runner records them in `config.requested.json` and `run.summary.json`.

Reports separate `sut_system` from `controller_system`. `controller_system`
describes the machine running the runner. `sut_system` is populated from
`logs/hw_detection.log` when `hw_detection` runs and includes non-secret
vendor/model fields; if no hardware detection log exists, the reports say that
SUT identity was not collected.

Full certification runs can take 2 to 5 days depending on the device resources.
Use `tmux` or `screen` on the LTS so the session survives network
interruptions.

## Test Tags

Automated tests can be selected by Ansible tag.

| Tag | Purpose |
| --- | --- |
| `logs_folder` | Create the run logs directory. |
| `tests_copy` | Copy test scripts from the LTS/controller to the SUT sandbox. |
| `tests_cleanup` | Remove copied test scripts from the SUT sandbox. |
| `hw_detection` | Hardware inventory and DMI/PCI/storage/network report. |
| `containers` | Container functionality checks. |
| `kvm` | KVM and virtualization checks. |
| `cpu` | CPU stress test. |
| `network` | Network stress test. |
| `raid` | MD RAID test. |
| `ltp` | Linux Test Project suites. |
| `phoronix` | Phoronix benchmark suites. |
| `gpu_burn` | Optional NVIDIA GPU Burn stress test. |
| `ai_llm` | Optional AI inference benchmark (llama.cpp llama-bench), CPU or GPU. |
| `cllimits` | CloudLinux LVE/CageFS checks. |

Interactive tests are run through `interactive.yml` and are not split into the
same per-test runner profiles yet.

## Certification Areas

The official Hardware Certification Program describes the broad testing areas
the suite should cover. In this repository they map to the current runner and
Ansible entry points as follows:

| Official testing area | Current suite entry point |
| --- | --- |
| Hardware detection | `hw_detection` automated tag and runner test. |
| CPU stress testing | `cpu` automated tag and runner test. |
| Containerization | `containers` automated tag and runner test. |
| KVM functionality | `kvm` automated tag and runner test. |
| Network performance | `network` automated tag and runner test. |
| Linux kernel testing through LTP | `ltp` automated tag and runner test. |
| USB port functionality | `interactive.yml` using `tests/usb/`; requires hands-on coordination. |
| PXE device booting | `interactive.yml` using `tests/pxe/`; requires network/boot coordination. |
| OS feature benchmarking via PTS | `phoronix` automated tag and runner test. |
| GPU/AI workload readiness | Optional `gpu_burn` runner/Ansible test for NVIDIA systems with drivers installed. |

The `check`, `short`, `medium`, `long`, `very_long`, and `extreme` runner
profiles are operational presets. They are not certification types. The
official certification type and final catalog status are determined through the
SIG process.

## Configuration Variables

Most users should configure runs through the runner CLI or
`hcs-runner.example.yml`. The Ansible variables below remain available for
direct playbook use and advanced tuning.

| Variable | Meaning |
| --- | --- |
| `hcs_run_id` | Run identifier used in generated sandbox names. |
| `hcs_run_timestamp` | UTC timestamp used in generated sandbox names. |
| `hcs_base_dir` | Base directory for generated sandboxes. Defaults to `/var/tmp`. |
| `hcs_sandbox_dir` | Run sandbox root. Defaults to `/var/tmp/AlmaLinux-HCS-<timestamp>-RunID-<id>`. |
| `hcs_work_dir` | Suite work directory. Defaults to `hcs_sandbox_dir`. |
| `hcs_scratch_dir` | Scratch directory for temporary tool output. |
| `hcs_cache_dir` | Cache directory for reusable downloads/assets. |
| `hcs_artifacts_dir` | Directory for structured artifacts. |
| `lts_logs_dir` | Log directory inside the active run sandbox. |
| `sut_tests_dir` | Copied test script directory on the SUT. |
| `test_cpu.duration` | CPU stress duration. Accepts stress-ng time suffixes. |
| `test_cpu.scratch_dir` | Directory used by `stress-ng` for temporary files. |
| `test_cpu.log_file` | Temporary CPU log path on the SUT. |
| `test_network.duration` | Network test duration in seconds. |
| `test_network.speed` | Target network test speed in Mbps. |
| `test_network.device` | Optional network device selector. |
| `hcs_lts_ip` | Explicit LTS/controller IP for the network test; runner sets this from `--lts-ip`. |
| `hcs_sut_ip` | Explicit SUT IP for the network test; runner sets this from `--sut-ip`. |
| `test_raid.duration` | RAID test duration in seconds. |
| `test_raid.allow_data_loss` | Stress MD arrays even when they hold a filesystem/LVM/LUKS signature (`raid_allow_data_loss=true`). fio overwrites raw array data; default `false` stresses only unmounted, signature-free arrays. |
| `ltp_version` | LTP git tag or branch to clone and build. Defaults to a recent stable LTP release. |
| `test_ltp.suites` | LTP suite pattern. |
| `test_ltp.log_file` | LTP full log path on the SUT. |
| `test_phoronix.tests` | Phoronix test suite mapping. |
| `test_phoronix.folder` | Phoronix install/results directory under the sandbox. |
| `test_gpu_burn.duration` | GPU Burn duration in seconds. |
| `test_gpu_burn.memory` | GPU memory target passed to `gpu_burn -m`. |
| `test_gpu_burn.devices` | Optional GPU selection passed to `gpu_burn -i`. |
| `test_gpu_burn.snap_package` | Snap package name used when snap mode is enabled. |
| `test_gpu_burn.install_snap` | Install the GPU Burn snap when snapd exists and no binary/snap is already available. |
| `test_gpu_burn.remove_snap_after` | Remove the GPU Burn snap at the end if HCS installed it. |
| `test_gpu_burn.build_from_source` | Clone/build GPU Burn when no binary exists. |
| `test_gpu_burn.binary` | Existing or built GPU Burn binary path. |
| `test_gpu_burn.telemetry_file` | NVIDIA telemetry CSV collected during the run. |
| `test_gpu_burn.result_file` | GPU Burn JSON result artifact. |
| `test_ai_llm.model_sha256` | Optional sha256 of the GGUF model (`ai_llm_model_sha256`). When set, configured, cached, and downloaded models are verified before benchmarking. |

## Adding Tests

Automated tests live under `tests/<test_id>/`:

```text
tests/example/
  README.md
  run_test.sh
  roles/
    main.yml
```

Interactive tests use step playbooks:

```text
tests/example/
  README.md
  step1.yml
  step2.yml
```

Guidelines for new automated tests:

- Add the Ansible task include to `automated.yml`.
- Give the test a clear tag such as `example`.
- Put test settings in `vars.yml` when they need to be configurable.
- Write logs to `{{ lts_logs_dir }}/example.log`; that path is inside the
  active run sandbox.
- Keep temporary files under `hcs_scratch_dir`, `hcs_cache_dir`, or another
  sandbox child path.
- Avoid hard-coded `/root`, `/tmp`, or repository-relative output paths for
  generated data.

## Notes

- Roles execute in the context of the SUT. Use Ansible delegation only when a
  task truly belongs on the LTS/controller.
- Hardware-specific tests, such as RAID or USB, should be selected only when
  the target platform has the expected devices. The `medium` and longer
  profiles include `raid`; when the SUT has no MD array it records
  `unsupported` (a warning) rather than a pass or a failure. `network` and
  `kvm` behave the same way on a single host or without CPU virtualization.
- Phoronix can require more than `100GB` of free space. Keep its folder inside
  the run sandbox by setting `paths.phoronix_dir` or `sandbox_dir`.
- Passing local results should be treated as evidence for SIG review, not as a
  self-issued certification.
- Results intended for public certification should be submitted to the
  [AlmaLinux certifications repository](https://github.com/AlmaLinux/certifications).

This repository is managed by the
[AlmaLinux Certification SIG](https://wiki.almalinux.org/sigs/Certification).
