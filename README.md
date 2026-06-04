# AlmaLinux Hardware Certification Suite

[![CI](https://github.com/xsub/Hardware-Certification-Suite/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/xsub/Hardware-Certification-Suite/actions/workflows/ci.yml)
[![Python 3.11+](https://github.com/xsub/Hardware-Certification-Suite/actions/workflows/python.yml/badge.svg?branch=main)](https://github.com/xsub/Hardware-Certification-Suite/actions/workflows/python.yml)
[![Ansible](https://github.com/xsub/Hardware-Certification-Suite/actions/workflows/ansible.yml/badge.svg?branch=main)](https://github.com/xsub/Hardware-Certification-Suite/actions/workflows/ansible.yml)
[![AlmaLinux](https://github.com/xsub/Hardware-Certification-Suite/actions/workflows/build.yml/badge.svg?branch=main)](https://github.com/xsub/Hardware-Certification-Suite/actions/workflows/build.yml)
[![AlmaLinux 10 validated](https://img.shields.io/badge/AlmaLinux%209%20%7C%2010-validated-1a3a63?logo=almalinux&logoColor=white)](docs/runner.md#compatibility)

Turn a fresh AlmaLinux system into repeatable hardware certification evidence.
HCS wraps the existing Ansible test suite with a Python/Rich runner that plans
the work, streams progress, keeps every artifact in one sandbox, and produces
plain-text plus JSON reports for review.

HCS creates certification evidence. Official certification status is granted
through the
[AlmaLinux Hardware Certification Program](https://almalinux.org/certification/hardware-certification/)
after review by the Certification SIG.

## Start Here

On a fresh AlmaLinux 10 system, install once:

```bash
dnf -y install git tmux python3.12
git clone https://github.com/AlmaLinux/Hardware-Certification-Suite.git
cd Hardware-Certification-Suite

python3.12 -m venv .venv
source .venv/bin/activate
pip install "ansible-core>=2.17,<2.18"
pip install -e .
cp hcs-runner.example.yml hcs-runner.yml
```

`pip install -e .` pulls in the runner dependencies and adds an `hcs` command, so
`hcs run --profile check` works as a shortcut for `python -m hcs run --profile
check`. Both forms are equivalent; the examples below use `python -m hcs` so they
also work without installing.

Run the fast smoke test (the local host is the default target):

```bash
python -m hcs run --profile check
```

Run the certification policy preset:

```bash
python -m hcs run --preset certification
```

To certify a remote machine instead, add `--host <SUT IP>` and HCS runs it over
SSH:

```bash
python -m hcs run --preset certification --host <SUT IP>
```

For long runs, start inside `tmux` or `screen`. Run from a privileged shell
when selected tests need package installation or direct hardware access.

## The Promise

| HCS Features | Provides / Value |
| --- | --- |
| Guided Rich console runner | Operators see the plan, current step, pass counters, and final result without reading raw Ansible output first. |
| Certification preset | The built-in `certification` preset separates required automated checks, optional hardware-dependent checks, and manual checks. |
| Sandboxed evidence | Each run gets one `AlmaLinux-HCS-<timestamp>-RunID-<id>` directory with consistent report, log, and artifact names. |
| Repeatable burn-in | Profiles from `check` through `extreme`, repeated passes, named presets, and per-test duration/profile controls. |
| Plain-text first reports | `run.report.txt` is readable by engineers; JSON summaries sit next to it for automation. |

## Console Preview

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
  recap 127.0.0.1: ok=8 changed=4 unreachable=0 failed=0 skipped=0 rescued=0 ignored=0
  duration 68.2s
  artifact tests/001-pass01-hw_detection/001-pass01-hw_detection.console.log

PASS 002 pass=02/02 Hardware detection
  recap 127.0.0.1: ok=8 changed=3 unreachable=0 failed=0 skipped=0 rescued=0 ignored=0
  duration 75.0s
  artifact tests/002-pass02-hw_detection/002-pass02-hw_detection.console.log

run.report.txt
  Status: passed
  Results:
    001 pass=01/02 hw_detection  profile  passed  68.2s rc=0 ok
    002 pass=02/02 hw_detection  profile  passed  75.0s rc=0 ok
```

## Choose A Run

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

## Certification Flow

| Step | Where it happens |
| --- | --- |
| Prepare the system | Install AlmaLinux, update it, and install the runner prerequisites. |
| Run HCS | Start with `check`, then run `--preset certification` for ordinary automated certification evidence. |
| Review artifacts | Inspect `run.report.txt`, `run.summary.json`, per-step logs, and collected artifacts in the sandbox. |
| Submit results | Follow the official program flow and share accepted results through [AlmaLinux/certifications](https://github.com/AlmaLinux/certifications). |
| Publish status | Final status is published through the [Ecosystem Catalog](https://almalinux.org/certification/ecosystem-catalog/) after SIG review. |

## Requirements

| Requirement | Notes |
| --- | --- |
| AlmaLinux SUT | Prefer a blank, freshly installed and updated AlmaLinux system. Validated on AlmaLinux 10.2; CI covers AlmaLinux 8/9/10. See [Compatibility](docs/runner.md#compatibility). |
| Python | `3.11+` for the Rich runner. AlmaLinux 10 includes Python `3.12`; CI validates Python `3.11`, `3.12`, and `3.14`. |
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

HCS is AlmaLinux-first, but the runner patterns are intentionally useful for
other Linux hardware validation work: predictable sandboxes, repeatable
profiles, plain-text reports, machine-readable JSON, and optional long-running
burn-in workflows.

Passing local results should be treated as evidence for SIG review, not as a
self-issued certification. Results intended for public certification should be
submitted through the official AlmaLinux certification process.

This repository is managed by the
[AlmaLinux Certification SIG](https://wiki.almalinux.org/sigs/Certification).
