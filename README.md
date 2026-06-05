# AlmaLinux Hardware Certification Suite

[![CI](https://github.com/xsub/Hardware-Certification-Suite/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/xsub/Hardware-Certification-Suite/actions/workflows/ci.yml)
[![Python 3.9+](https://github.com/xsub/Hardware-Certification-Suite/actions/workflows/python.yml/badge.svg?branch=main)](https://github.com/xsub/Hardware-Certification-Suite/actions/workflows/python.yml)
[![Ansible](https://github.com/xsub/Hardware-Certification-Suite/actions/workflows/ansible.yml/badge.svg?branch=main)](https://github.com/xsub/Hardware-Certification-Suite/actions/workflows/ansible.yml)
[![AlmaLinux](https://github.com/xsub/Hardware-Certification-Suite/actions/workflows/build.yml/badge.svg?branch=main)](https://github.com/xsub/Hardware-Certification-Suite/actions/workflows/build.yml)

[![AlmaLinux 10 validated](https://img.shields.io/badge/AlmaLinux%209%20%7C%2010-validated-1a3a63?logo=almalinux&logoColor=white)](docs/runner.md#compatibility)
[![ansible-core](https://img.shields.io/badge/ansible--core-2.17-1a1a1a?logo=ansible&logoColor=white)](https://github.com/ansible/ansible)
[![Certification SIG](https://img.shields.io/badge/AlmaLinux-Certification%20SIG-1a3a63?logo=almalinux&logoColor=white)](https://wiki.almalinux.org/sigs/Certification)

The AlmaLinux Hardware Certification Suite (HCS) is the open-source toolset
behind the
[AlmaLinux Hardware Certification Program](https://almalinux.org/certification/hardware-certification/).
It exercises a system's hardware on AlmaLinux and produces repeatable evidence
that the AlmaLinux Certification SIG reviews to grant official certification.

📄 **See a sample:** [a rendered Hardware Certification report (PDF)](docs/sample-report.pdf) produced by the runner.

## AlmaLinux Hardware Certification

The program ensures hardware compatibility with AlmaLinux and promotes OS
adoption, with a focus on long-term reliability and performance. Hardware
compatibility issues can lead to system instability or performance degradation,
so vendors use certification to demonstrate that their hardware runs AlmaLinux
reliably, and users get a public, vetted catalog of certified systems.

HCS is how that hardware is exercised and evidenced:

| Step | Where it happens |
| --- | --- |
| Validate the hardware | Run HCS on the system under test to produce certification evidence. |
| Submit results | Open a request in [AlmaLinux/certifications](https://github.com/AlmaLinux/certifications) with the evidence. |
| SIG review | The Certification SIG reviews the submission and grants official status. |
| Publish | Certified hardware is listed in the [Ecosystem Catalog](https://almalinux.org/certification/ecosystem-catalog/). |

A passing local run is **evidence for SIG review, not a self-issued
certification**. The program is managed by the
[AlmaLinux Certification SIG](https://wiki.almalinux.org/sigs/Certification).

## What the Suite Tests

HCS covers the certification testing areas as Ansible-driven tests — automated
where possible, interactive where physical interaction is required:

| Testing area | HCS test |
| --- | --- |
| Hardware detection and inventory | `hw_detection` (DMI / PCI / storage / network report) |
| CPU stress | `cpu` (stress-ng) |
| Containerization | `containers` (podman) |
| KVM / virtualization | `kvm` |
| Network performance | `network` (iperf3 across the link) |
| Linux kernel testing | `ltp` (Linux Test Project) |
| OS and feature benchmarking | `phoronix` (Phoronix Test Suite) |
| USB port functionality | `interactive.yml` — `tests/usb/` |
| PXE device booting | `interactive.yml` — `tests/pxe/` |
| GPU / accelerator readiness | optional `gpu_burn` (NVIDIA) |

These tests are the substance of a certification run. To make running and
collecting them repeatable, the suite also ships a guided runner, shown next.

## Running the Suite

On a fresh AlmaLinux 10 system, install once:

```bash
dnf -y install git tmux python3.12
git clone https://github.com/xsub/Hardware-Certification-Suite.git
cd Hardware-Certification-Suite

python3.12 -m venv .venv
source .venv/bin/activate
pip install "ansible-core>=2.17,<2.18"
pip install -e .
cp hcs-runner.example.yml hcs-runner.yml
```

The suite ships a Python/Rich runner (`hcs`) — the recommended way to produce
certification evidence. It plans the work, streams progress, keeps every
artifact in one per-run sandbox, and writes a branded PDF plus plain-text and
JSON reports for SIG review. `pip install -e .` adds the `hcs` command;
`python -m hcs` works without installing.

```bash
# fast smoke test (the local host is the default target)
python -m hcs run --profile check

# the certification policy preset (required automated checks)
python -m hcs run --preset certification

# certify a separate machine over SSH
python -m hcs run --preset certification --host <SUT IP>
```

For long runs, start inside `tmux` or `screen`, from a privileged shell when
selected tests need package installation or direct hardware access.

### What the Runner Provides

| Runner feature | Provides / Value |
| --- | --- |
| Guided Rich console runner | Operators see the plan, current step, pass counters, and final result without reading raw Ansible output first. |
| Certification preset | The built-in `certification` preset separates required automated checks, optional hardware-dependent checks, and manual checks. |
| Sandboxed evidence | Each run gets one `AlmaLinux-HCS-<timestamp>-RunID-<id>` directory with consistent report, log, and artifact names. |
| Repeatable burn-in | Profiles from `check` through `extreme`, repeated passes, named presets, and per-test duration/profile controls. |
| Reports for review | A branded `run.report.pdf` in official AlmaLinux styling, plus `run.report.txt` for engineers and `run.summary.json` for automation. |

### Console Preview

Condensed excerpt from a real two-pass `check` run on an AlmaLinux 10.2 test
system. Host and IP values are anonymized.

```text
$ python -m hcs run --profile check --repeat 2

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

almalinux@almalinux-sut.example
-------------------------------
      OS: AlmaLinux 10.2 (Lavender Lion) x86_64
  Kernel: Linux 6.12.0-211.7.4.el10_2.x86_64 x86_64
  Python: 3.14.4 (venv)
     CPU: Intel Core Processor (Haswell, no TSX)
     GPU: Cirrus Logic GD 5446
  Memory: 607.7 MiB / 1.87 GiB (32%)
 SELinux: Enforcing

╭──────────────────── AlmaLinux Hardware Certification Suite ────────────────────╮
│ Profile: check                                                                 │
│ Run ID: check-3248b3e5                                                         │
│ Sandbox: /var/tmp/AlmaLinux-HCS-20260601T115819Z-RunID-check-3248b3e5          │
│ Inventory: 127.0.0.1,                                                          │
╰────────────────────────────────────────────────────────────────────────────────╯
             Planned certification steps
┏━━━━━┳━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━┳━━━━━━━━━┓
┃   # ┃ Test               ┃ Tag          ┃ Profile ┃ Scope   ┃
┡━━━━━╇━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━╇━━━━━━━━━┩
│ 001 │ Hardware detection │ hw_detection │ check   │ profile │
└─────┴────────────────────┴──────────────┴─────────┴─────────┘
Repeat: 2 passes, 2 total steps

PASS 001 pass=01/02 Hardware detection
PASS 002 pass=02/02 Hardware detection

                       Run recap
┏━━━━━┳━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━┳━━━━━━━━┳━━━━━━━━━━┳━━━━┓
┃   # ┃ Test               ┃ Scope   ┃ Status ┃ Duration ┃ rc ┃
┡━━━━━╇━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━╇━━━━━━━━╇━━━━━━━━━━╇━━━━┩
│ 001 │ Hardware detection │ profile │ passed │    68.2s │  0 │
│ 002 │ Hardware detection │ profile │ passed │    75.0s │  0 │
└─────┴────────────────────┴─────────┴────────┴──────────┴────┘
2 passed, 0 failed, 0 unsupported, 0 skipped — total 143.2s, slowest Hardware detection 75.0s
╭───────────────────────────── Run complete ──────────────────────────────╮
│ Sandbox:                                                                 │
│ /var/tmp/AlmaLinux-HCS-20260601T115819Z-RunID-check-3248b3e5             │
│                                                                          │
│ Runner artifacts:                                                        │
│ /var/tmp/AlmaLinux-HCS-20260601T115819Z-RunID-check-3248b3e5/runner      │
╰──────────────────────────────────────────────────────────────────────────╯
```
The runner also writes run.report.pdf, run.report.txt, and run.summary.json into the sandbox.

### Choosing a Run

| Goal | Command |
| --- | --- |
| Fast sanity check | `python -m hcs run --profile check` |
| Certification evidence | `python -m hcs run --preset certification` |
| Preview without running tests | `python -m hcs run --preset certification --dry-run` |
| Build a named preset | `python -m hcs configure --preset lab-default` |
| Run selected tests | `python -m hcs run --profile medium --test cpu --test network` |
| Remote SUT | `python -m hcs run --preset certification --host <SUT IP>` |
| Optional NVIDIA GPU Burn | `python -m hcs run --profile check --test gpu_burn` |

The local host is the default target, so plain commands run against it. The
runner infers the Ansible connection from the inventory: loopback runs with the
local connection, and `--host <SUT IP>` runs over SSH. Pass `-c <connection>`
only to override that.

Keep lab defaults in `hcs-runner.yml`. The runner auto-loads that file, so
normal commands do not need a manual timestamp, run ID, or sandbox path.

```yaml
run:
  base_dir: /var/tmp
  default_preset: certification
```

## Running Tests Directly With Ansible

For low-level debugging, or when you do not need the runner's reports, run the
Ansible playbooks directly. Direct runs use the same sandbox variables but do
not produce the runner's JSON summaries, repeated-pass reports, or Rich output.

```bash
# one automated test, locally
ansible-playbook -c local -i 127.0.0.1, automated.yml --tags cpu

# the same against a remote SUT
ansible-playbook -i <SUT IP>, -u root automated.yml --tags cpu

# interactive USB / PXE tests
ansible-playbook -i <SUT IP>, -u root interactive.yml
```

The [operator reference](docs/runner.md) documents the full command set,
profiles, presets, sandbox layout, variables, and how to add tests.

## Requirements

| Requirement | Notes |
| --- | --- |
| AlmaLinux SUT | Prefer a blank, freshly installed and updated AlmaLinux system. Validated on AlmaLinux 10.2; CI covers AlmaLinux 8/9/10. See [Compatibility](docs/runner.md#compatibility). |
| Python | `3.9+` for the Rich runner — runs on AlmaLinux 9's platform Python `3.9` and AlmaLinux 10's `3.12`. CI validates Python `3.9`, `3.10`, `3.11`, `3.12`, and `3.14`. |
| Ansible | `ansible-core>=2.17,<2.18` is the tested range. |
| Tools | `git`, `tmux` or `screen`, and shell access. |
| Optional snapd | Used only when a preset allows installing the `gpu-burn` snap workload. |
| Storage | At least `300GB`, preferably SSD/NVMe, for long Phoronix/LTP runs. |

`LTS` means the Local Testing Server, the host running the runner/Ansible
controller. `SUT` means System Under Test, the host being certified. The
simplest setup uses the same host as both LTS and SUT, which is the default —
plain commands target the local host. Add `--host <SUT IP>` to certify a
separate machine over SSH.

## Operator Guides

| Need | Guide |
| --- | --- |
| Detailed runner commands, profiles, presets, direct Ansible, remote SUT, sandbox layout, variables, and adding tests | [Runner and operator reference](docs/runner.md) |
| Optional NVIDIA stress testing behavior | [GPU Burn test README](tests/gpu_burn/README.md) |
| Long-term product and runner roadmap | [Development plan](DevelopmentPlan.md) |
| Current follow-up tasks | [TODO](TODO.md) |
| Official certification process | [AlmaLinux Hardware Certification](https://almalinux.org/certification/hardware-certification/) |

## Project Scope

HCS is AlmaLinux-first: it implements the AlmaLinux Hardware Certification
Program's testing areas and produces the evidence the Certification SIG reviews.
This repository corrects and extends that suite — the guided runner, sandboxed
evidence, result contracts, and AlmaLinux 9/10 test hardening — on top of the
AlmaLinux baseline.

The runner's patterns (predictable sandboxes, repeatable profiles, plain-text
and JSON reports, optional long-running burn-in) are reusable for other Linux
hardware validation too, but the suite's purpose is AlmaLinux certification.
