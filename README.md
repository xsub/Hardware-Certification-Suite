# AlmaLinux Hardware Certification Suite

[![CI](https://github.com/xsub/Hardware-Certification-Suite/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/xsub/Hardware-Certification-Suite/actions/workflows/ci.yml)
[![Python 3.11+](https://github.com/xsub/Hardware-Certification-Suite/actions/workflows/python.yml/badge.svg?branch=main)](https://github.com/xsub/Hardware-Certification-Suite/actions/workflows/python.yml)
[![Ansible](https://github.com/xsub/Hardware-Certification-Suite/actions/workflows/ansible.yml/badge.svg?branch=main)](https://github.com/xsub/Hardware-Certification-Suite/actions/workflows/ansible.yml)
[![AlmaLinux](https://github.com/xsub/Hardware-Certification-Suite/actions/workflows/build.yml/badge.svg?branch=main)](https://github.com/xsub/Hardware-Certification-Suite/actions/workflows/build.yml)

The AlmaLinux Hardware Certification Suite is the open source test toolkit used
by the AlmaLinux Certification SIG to collect hardware compatibility,
reliability, performance, and stability evidence for AlmaLinux OS.

This suite helps run and package the tests. Official certification status is
granted through the AlmaLinux Hardware Certification Program after review by
the Certification SIG; a local passing run does not, by itself, make hardware
certified.

The preferred entry point is the Python/Rich runner:

```bash
python -m hcs run --profile check --inventory 127.0.0.1, -c local
```

## Runner Output

Excerpt from a real two-pass `check` run captured on an AlmaLinux 10.2 VPS
with Python 3.14. The command is the normal user-facing invocation: the
timestamp and run ID are generated automatically, and `hcs-runner.yml` supplies
`/var/tmp` as the sandbox base directory. The identity header is built into
HCS and does not require `fastfetch`, `neofetch`, or other system-wide helper
packages. Repeated Rich live-refresh frames are omitted, and color is stripped
for Markdown readability. The generated run ID, recap counters, timings,
system facts, and artifact paths come from the actual run.

```text
$ python -m hcs run --profile check --repeat 2 --inventory 127.0.0.1, -c local

         'c:.
        lkkkx, ..       ..   ,cc,
        okkkk:ckkx'  .lxkkx.okkkkd
        .:llcokkx'  :kkkxkko:xkkd,
      .xkkkkdood:  ;kx,  .lkxlll;
       xkkx.       xk'     xkkkkk:
       'xkx.       xd      .....,.
      .. :xkl'     :c      ..''..
    .dkx'  .:ldl:'. '  ':lollldkkxo;
  .''lkkko'                     ckkkx.
'xkkkd:kkd.       ..  ;'        :kkxo.
,xkkkd;kk'      ,d;    ld.   ':dkd::cc,
 .,,.;xkko'.';lxo.      dx,  :kkk'xkkkkc
     'dkkkkkxo:.        ;kx  .kkk:;xkkd.
       .....   .;dk:.   lkk.  :;,
             :kkkkkkkdoxkkx
              ,c,,;;;:xkkd.
                ;kkkkl...
                ;kkkkl
                 ,od;

almalinux@vps-ac97e687.vps.ovh.net
----------------------------------
      OS: AlmaLinux 10.2 (Lavender Lion) x86_64
    Host: OpenStack Foundation OpenStack Nova 19.3.2
  Kernel: Linux 6.12.0-211.7.4.el10_2.x86_64 x86_64
  Uptime: 2 days, 19 hours, 34 mins
Packages: 586 (rpm)
  Python: 3.14.4 (venv)
   Shell: bash 5.2.26(1)-release
     CPU: Intel Core Processor (Haswell, no TSX) (1 logical CPUs)
     GPU: Cirrus Logic GD 5446
  Memory: 607.7 MiB / 1.87 GiB (32%)
    Swap: Disabled
Disk (/): 3.92 GiB / 18.7 GiB (21%) - xfs
Local IP: 141.95.86.222 (eth0)
  Locale: en_US.UTF-8
 SELinux: Enforcing
    FIPS: disabled

╭────────────────────────────── AlmaLinux Hardware Certification Suite ──────────────────────────────╮
│ Profile: check                                                                                      │
│ Mode: Fast sanity pass for runner, inventory, and hardware discovery.                               │
│ Run ID: check-3248b3e5                                                                              │
│ Sandbox: /var/tmp/AlmaLinux-HCS-20260601T115819Z-RunID-check-3248b3e5                               │
│ Runner artifacts:                                                                                   │
│ /var/tmp/AlmaLinux-HCS-20260601T115819Z-RunID-check-3248b3e5/runner                                 │
│ Inventory: 127.0.0.1,                                                                               │
╰─────────────────────────────────────────────────────────────────────────────────────────────────────╯
             Planned certification steps
┏━━━━━┳━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━┓
┃   # ┃ Test               ┃ Tag          ┃ Profile ┃
┡━━━━━╇━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━┩
│ 001 │ Hardware detection │ hw_detection │ check   │
└─────┴────────────────────┴──────────────┴─────────┘
Repeat: 2 passes, 2 total steps

Suite progress 0/2
Pass 1/2: running Hardware detection
  TASK [Gathering Facts]
  TASK [Create LTS logs dir]
  TASK [Create SUT work dirs]
  TASK [Copy tests]
  TASK [Test Hardware Detection - run test]
  TASK [Test Hardware Detection - copy log]
  TASK [Remove tests]
PASS 001 pass=01/02 Hardware detection
  recap 127.0.0.1: ok=8 changed=4 unreachable=0 failed=0 skipped=0 rescued=0 ignored=0
  duration 68.2s
  artifact tests/001-pass01-hw_detection/001-pass01-hw_detection.console.log

Suite progress 1/2
Pass 2/2: running Hardware detection
  TASK [Gathering Facts]
  TASK [Create LTS logs dir]
  TASK [Create SUT work dirs]
  TASK [Copy tests]
  TASK [Test Hardware Detection - run test]
  TASK [Test Hardware Detection - copy log]
  TASK [Remove tests]
PASS 002 pass=02/02 Hardware detection
  recap 127.0.0.1: ok=8 changed=3 unreachable=0 failed=0 skipped=0 rescued=0 ignored=0
  duration 75.0s
  artifact tests/002-pass02-hw_detection/002-pass02-hw_detection.console.log

Suite progress 2/2
╭──────────────────────────────────────────── Run complete ───────────────────────────────────────────╮
│ Sandbox:                                                                                            │
│ /var/tmp/AlmaLinux-HCS-20260601T115819Z-RunID-check-3248b3e5                                        │
│                                                                                                     │
│ Runner artifacts:                                                                                   │
│ /var/tmp/AlmaLinux-HCS-20260601T115819Z-RunID-check-3248b3e5/runner                                 │
╰─────────────────────────────────────────────────────────────────────────────────────────────────────╯

run.report.txt
  Status: passed
  Started: 2026-06-01T11:58:20Z
  Finished: 2026-06-01T12:00:43Z
  Controller system:
    OS: AlmaLinux 10.2 (Lavender Lion) x86_64
    Host: OpenStack Foundation OpenStack Nova 19.3.2
    Kernel: Linux 6.12.0-211.7.4.el10_2.x86_64 x86_64
    Python: 3.14.4 (venv)
    CPU: Intel Core Processor (Haswell, no TSX) (1 logical CPUs)
    GPU: Cirrus Logic GD 5446
  Results:
    001 pass=01/02 hw_detection  passed  68.2s rc=0 ok
    002 pass=02/02 hw_detection  passed  75.0s rc=0 ok
```

## Official Program

The public process is documented on the
[AlmaLinux Hardware Certification](https://almalinux.org/certification/hardware-certification/)
and
[Hardware Certification Program](https://almalinux.org/certification/hardware-certification/hardware-certification-program/)
pages.

| Program item | What it means for this repository |
| --- | --- |
| Certification requests | Start through the official program flow or the [AlmaLinux/certifications](https://github.com/AlmaLinux/certifications) repository. |
| Certification coordination | Work with the [Certification SIG](https://wiki.almalinux.org/sigs/Certification.html), especially for IHV-assisted runs, private/NDA work, or hardware hosted by ALOSF. |
| Certification types | Results may support IHV-facilitated, ALOSF-facilitated, or community validated certification paths. |
| Public records | Accepted results and certification status are published through the [Ecosystem Catalog](https://almalinux.org/certification/ecosystem-catalog/), not by this repository alone. |
| Result submission | After the suite is run, share results through a pull request to [AlmaLinux/certifications](https://github.com/AlmaLinux/certifications). |
| Lifecycle | Certification is scoped to AlmaLinux major versions; minor versions are expected to carry forward unless the SIG requests another run. |

## What You Get

- A guided CLI runner with Rich progress output.
- A built-in AlmaLinux identity header with logo and system facts, without
  requiring `fastfetch`, `neofetch`, or any system-wide helper package.
- Built-in run profiles from `check` through `extreme`.
- One sandbox directory per certification run.
- Plain-text reports first, with structured JSON next to them.
- Controller system identity recorded in both human and JSON artifacts.
- Per-step console logs and result files with consistent names.
- Ansible recap parsing, so `ignored>0`, `failed>0`, or `unreachable>0` marks the step failed even if Ansible exits `0`.
- Optional NVIDIA [GPU Burn](https://github.com/wilicc/gpu-burn) stress
  testing when NVIDIA drivers are already installed and `nvidia-smi` can see
  the GPUs.
- Coverage for the certification testing areas documented by the official
  program, including automated and interactive checks.

## Requirements

| Requirement | Notes |
| --- | --- |
| AlmaLinux SUT | Prefer a blank, freshly installed and updated AlmaLinux system. |
| Python | `3.11+` for the Rich runner. CI validates Python `3.11`, `3.12`, and `3.14`. |
| Ansible | `ansible-core>=2.17,<2.18` is the tested range. |
| Tools | `git`, `tmux` or `screen`, and shell access. |
| Storage | At least `300GB`, preferably SSD/NVMe, for long Phoronix/LTP runs. |

Terminology:

- `LTS` - Local Testing Server, the host running the runner/Ansible controller.
- `SUT` - System Under Test, the host being certified.

For the simplest and most reliable run, use the same host as both LTS and SUT:
`--inventory 127.0.0.1, -c local`.

## Quick Start

```bash
git clone https://github.com/AlmaLinux/Hardware-Certification-Suite.git
cd Hardware-Certification-Suite

python3.11 -m venv venv
source venv/bin/activate
pip install "ansible-core>=2.17,<2.18"
pip install -r requirements-runner.txt
cp hcs-runner.example.yml hcs-runner.yml

python -m hcs profiles
python -m hcs tests
python -m hcs run --profile check --inventory 127.0.0.1, -c local
```

Preview a longer plan without running Ansible:

```bash
python -m hcs run --profile medium --repeat 3 --dry-run
```

Detailed examples for single-test and full-suite runs are in
[Running Tests](#running-tests).

## Running Tests

Use the runner for normal certification work. It wraps Ansible, creates one
sandbox per run, streams progress with Rich, writes per-step artifacts, parses
Ansible recap counters, supports repeated passes, and produces the final
plain-text report. The runner currently wraps `automated.yml`; interactive
USB and PXE tests are run directly with Ansible.

Keep lab-wide runner defaults in `hcs-runner.yml`. The runner loads this file
automatically from the repository directory, so normal commands do not need a
manual timestamp, run ID, or base directory.

List available runner profiles and test IDs:

```bash
python -m hcs profiles
python -m hcs tests
```

Run one automated test locally through the runner:

```bash
python -m hcs run --profile short --test cpu --inventory 127.0.0.1, -c local
```

Run several selected tests locally through the runner:

```bash
python -m hcs run --profile medium \
  --test hw_detection --test cpu --test network \
  --inventory 127.0.0.1, -c local
```

Run all tests from a runner profile:

```bash
python -m hcs run --profile medium --inventory 127.0.0.1, -c local
```

Run the fullest built-in AlmaLinux automated profile, including LTP and
Phoronix:

```bash
python -m hcs run --profile extreme --inventory 127.0.0.1, -c local
```

Run the same profile against a remote SUT:

```bash
python -m hcs run --profile extreme --inventory <SUT IP>,
```

Repeat the selected plan and keep data from every pass:

```bash
python -m hcs run --profile check --repeat 3 --inventory 127.0.0.1, -c local
```

Override an Ansible variable while using the runner:

```bash
python -m hcs run --profile medium --extra-var cpu_duration=20m
```

Run the optional NVIDIA [GPU Burn](https://github.com/wilicc/gpu-burn) test.
This test is not part of the default profiles; it records `unsupported` when
NVIDIA drivers are not installed.

```bash
python -m hcs run --profile check --test gpu_burn --inventory 127.0.0.1, -c local
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

git clone https://github.com/AlmaLinux/Hardware-Certification-Suite.git
cd Hardware-Certification-Suite

# Use python3.12 if you prefer the platform Python.
PYTHON=python3.14

$PYTHON -m venv venv-almalinux-certification-suite
source venv-almalinux-certification-suite/bin/activate
pip install "ansible-core>=2.17,<2.18"
pip install -r requirements-runner.txt
cp hcs-runner.example.yml hcs-runner.yml

# Optional for larger runs: edit hcs-runner.yml and set run.base_dir: /var/tmp

tmux new-session -s almalinux-certification-tests
python -m hcs run --profile check --inventory 127.0.0.1, -c local
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
python -m hcs profiles
python -m hcs tests
python -m hcs run --help
```

## Run Sandbox

Each run owns one sandbox directory. By default:

```text
/tmp/AlmaLinux-HCS-<UTC timestamp>-RunID-<run id>
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
| `run.report.txt` | Plain-text engineering report with timestamps and runner version. |

## Remote LTS/SUT

Use remote mode when the controller and SUT are different machines.

1. Ensure the LTS can SSH to the SUT.
2. Add the LTS public key to the SUT root account or configure another
   privileged account.
3. Verify connectivity:

```bash
ansible all -i <SUT IP>, -m ping -u root
```

Run a profile against the remote SUT:

```bash
python -m hcs run --profile check --inventory <SUT IP>,
```

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
| `hcs_base_dir` | Base directory for generated sandboxes. Defaults to `/tmp`. |
| `hcs_sandbox_dir` | Run sandbox root. Defaults to `/tmp/AlmaLinux-HCS-<timestamp>-RunID-<id>`. |
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
| `test_raid.duration` | RAID test duration in seconds. |
| `test_ltp.suites` | LTP suite pattern. |
| `test_ltp.log_file` | LTP full log path on the SUT. |
| `test_phoronix.tests` | Phoronix test suite mapping. |
| `test_phoronix.folder` | Phoronix install/results directory under the sandbox. |
| `test_gpu_burn.duration` | GPU Burn duration in seconds. |
| `test_gpu_burn.memory` | GPU memory target passed to `gpu_burn -m`. |
| `test_gpu_burn.devices` | Optional GPU selection passed to `gpu_burn -i`. |
| `test_gpu_burn.build_from_source` | Clone/build GPU Burn when no binary exists. |
| `test_gpu_burn.binary` | Existing or built GPU Burn binary path. |
| `test_gpu_burn.telemetry_file` | NVIDIA telemetry CSV collected during the run. |
| `test_gpu_burn.result_file` | GPU Burn JSON result artifact. |

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
  the target platform has the expected devices.
- Phoronix can require more than `100GB` of free space. Keep its folder inside
  the run sandbox by setting `paths.phoronix_dir` or `sandbox_dir`.
- Passing local results should be treated as evidence for SIG review, not as a
  self-issued certification.
- Results intended for public certification should be submitted to the
  [AlmaLinux certifications repository](https://github.com/AlmaLinux/certifications).

This repository is managed by the
[AlmaLinux Certification SIG](https://wiki.almalinux.org/sigs/Certification).
