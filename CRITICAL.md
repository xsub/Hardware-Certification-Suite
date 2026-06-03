# CRITICAL

Critical defects only: issues that yield **wrong certification evidence**, **lose
evidence**, or **break the documented default run** (`--inventory 127.0.0.1, -c local`).
Lower-severity items live in the audit, not here.

**Status: C1–C8 and P1–P4 implemented, unit-tested, and validated on a live
AlmaLinux 10.2 VPS.** `check` (pipeline), `containers` (podman), and `network`
(`unsupported` on a single host) all behaved as designed; the LTP fixes ran clean
up to an unrelated pre-existing compile failure (see Follow-ups). See git history
for the per-item commits.

## Commit conventions

Commits are authored solely by **Pawel Suchanecki <subdcc@gmail.com>**. Do not add
`Co-Authored-By:` or any AI/assistant attribution trailers to commit messages.
History has been rewritten to enforce this.

Each fix follows the same rules:

- **Fail loud, never silent.** A false `passed` is the worst outcome in a
  certification tool. Detection must not depend on optional formatting.
- **Single source of truth.** One constant/var per cross-cutting concern
  (Ansible env, CRB repo name) instead of scattered literals.
- **Prefer contracts over heuristics.** Roles state their result; the runner
  records it. Don't infer pass/fail from log shape.
- **Guarantee artifacts.** Reports are written in `finally`, not on the happy path.
- **KISS.** Smallest change that fixes the root cause. No new layers, no
  abstraction before a third repeat. Ternary over branching; `package` over `yum`.

## Triage

| ID | Issue | Severity | Breaks | Effort |
| --- | --- | --- | --- | --- |
| C1 | `containers` installs `docker` (absent on AlmaLinux); task names swapped | S1 | required test, default run | S |
| C2 | `network` reads `SSH_CONNECTION`, undefined on `-c local` | S1 | required test, default run | M |
| C3 | Runner trusts default Ansible stdout callback → silent false `passed` | S1 | evidence integrity | S |
| C4 | Sandbox default `/tmp` (tmpfs/reboot-volatile) | S1 | evidence durability | S |
| C5 | `ltp` enables `powertools`; repo is `crb` on EL9/10 | S2 | EL9/10 runs | S |
| C6 | No SIGINT handling → no partial report, orphaned stress children | S2 | long runs | M |
| C7 | Pass/fail keyed on `ignored` recap; conflated with tolerated failures | S2 | result accuracy | M |
| C8 | CI runs syntax + dry-run only; no role executes on AlmaLinux | S2 | lets C1/C2/C5 ship | M |

---

## C1 — `containers` cannot install Docker on stock AlmaLinux

**Where:** `tests/containers/roles/main.yml:3-11`, `tests/containers/run_test.sh`
**Root cause:** AlmaLinux ships `podman`, not `docker`; there is no `docker`
package in base/AppStream. The two install tasks also have swapped names
(`install wget` installs `docker`, and vice-versa). `containers` is **required**
in the `certification` preset, so the default cert run fails here.

**Fix** — one task, podman + the `wget` the script actually needs:

```yaml
# tests/containers/roles/main.yml
- name: Containers - ensure runtime and client
  ansible.builtin.package:
    name: [podman, wget]
    state: present
# ... run test ...
- name: Containers - cleanup
  ansible.builtin.package:
    name: [podman, wget]
    state: absent
```

`run_test.sh`: the `podman` CLI is drop-in for the verbs used here
(`run`, `network`, `inspect -f`, `kill`). Replace the binary, keep the logic:

```sh
RT=${CONTAINER_RUNTIME:-podman}   # podman default; allow docker override
"$RT" run -d --name=testhttpd ...
```

## C2 — `network` breaks on the documented single-host run

**Where:** `vars.yml:4,13,16`, `tests/network/roles/main.yml`
**Root cause:** `lts_ip`/`sut_ip` derive from `ansible_env.SSH_CONNECTION`, which
does not exist on `-c local`. With `error_on_undefined_vars = True`
(`ansible.cfg`) the task errors; if the operator is themselves SSH'd into the
LTS, it silently resolves to the wrong hosts. The test is inherently two-host
(it `ssh root@$SUT` and runs iperf3 across the link).

**Fix** — make the vars total, then mark the test unsupported when there is no
distinct SUT (reuse the existing `HCS_UNSUPPORTED` contract):

```yaml
# vars.yml
_ssh_parts: "{{ (hostvars[inventory_hostname].ansible_env.SSH_CONNECTION | default('')).split() }}"
network_is_remote: "{{ _ssh_parts | length >= 4 }}"
lts_ip: "{{ _ssh_parts[0] if network_is_remote else '' }}"
sut_ip: "{{ _ssh_parts[2] if network_is_remote else '' }}"
```

```yaml
# tests/network/roles/main.yml (top)
- name: Network - requires a separate SUT
  ansible.builtin.debug:
    msg: "HCS_UNSUPPORTED: network test needs a distinct SUT (local/single-host run)"
  when: not network_is_remote | bool
# gate the real work:
- when: network_is_remote | bool
  block:
    # existing setup / run / cleanup
```

Result: single-host runs report `unsupported` (a warning), not a false failure;
two-host runs are unchanged.

## C3 — Runner can report a false `passed`

**Where:** `hcs/runner.py:29-39,408`
**Root cause:** pass/fail is regex over the Ansible recap line. If the operator's
environment sets `ANSIBLE_STDOUT_CALLBACK` (yaml/json/dense — common), the regex
never matches, `ansible_recap` stays empty, and a failing run is reported
`passed`. The runner must own the output format it parses.

**Fix** — pin the callback as a single source of truth; pass an explicit env:

```python
# hcs/runner.py
import os

ANSIBLE_ENV = {
    "ANSIBLE_STDOUT_CALLBACK": "default",   # the format RECAP_RE expects
    "ANSIBLE_NOCOLOR": "1",
    "ANSIBLE_FORCE_COLOR": "0",
}

process = subprocess.Popen(
    command, ...,
    env={**os.environ, **ANSIBLE_ENV},
)
```

Pairs with C7: parsing is now reliable, but the contract (C7) is what makes it
authoritative.

## C4 — Default sandbox base is `/tmp`

**Where:** `hcs/config.py:14`, `hcs-runner.example.yml:5`
**Root cause:** `/tmp` is frequently `tmpfs` (RAM-backed) and is cleared on
reboot. Phoronix needs ~300 GB; burn-in spans days. Risk: OOM, or **loss of the
evidence the suite exists to produce**. The README's own quick-start uses
`/var/tmp`.

**Fix** — one line, plus the example:

```python
# hcs/config.py
DEFAULT_BASE_DIR = Path("/var/tmp")
```

## C5 — `ltp` enables the wrong CRB repo on EL9/10

**Where:** `tests/ltp/roles/main.yml:39`
**Root cause:** `enablerepo: powertools` is EL8-only; EL9/10 name it `crb`.
`phoronix` already handles this by version — `ltp` does not, so its build
dependencies fail to install on AlmaLinux 9/10.

**Fix** — enable the repo by version, drop the hardcoded `enablerepo`:

```yaml
- name: LTP - enable CRB/PowerTools
  community.general.dnf_config_manager:
    name: "{{ 'powertools' if ansible_facts['distribution_major_version'] | int == 8 else 'crb' }}"
    state: enabled
```

This ternary appears in `ltp` and `phoronix`. On the *third* occurrence, lift it
to a single `group_vars/all.yml` value (`crb_repo: ...`) — not before.

## C6 — No graceful stop; no partial report

**Where:** `hcs/runner.py:433,465-528`
**Root cause:** `process.wait()` has no timeout, and `KeyboardInterrupt` unwinds
`run()` before `write_summary()`, so an aborted multi-hour run yields no report
and leaves `ansible`/`stress-ng` children orphaned.

**Fix** — own the child's process group; write the report in `finally`:

```python
# execute_step: child leads its own group, so pid == pgid
process = subprocess.Popen(command, ..., start_new_session=True)
try:
    for line in process.stdout:
        ...
    return_code = process.wait()
except KeyboardInterrupt:
    os.killpg(process.pid, signal.SIGTERM)
    raise

# run(): always summarize
started_at = utc_timestamp()
try:
    overall_exit = self._execute_plan(tests, results)   # existing loop, extracted
except KeyboardInterrupt:
    overall_exit = 130
    self.console.print("[yellow]Interrupted — writing partial report.[/yellow]")
finally:
    self.write_summary(results, started_at, utc_timestamp())
```

## C7 — `ignored` ≠ test failure

**Where:** `hcs/runner.py:107-113`
**Root cause:** the playbook sets `ignore_errors: true` globally, so the runner
treats `ignored > 0` as failure. But `ltp`/`gpu_burn` use task-level
`ignore_errors` for legitimate flow; one benign ignored task flips the whole
step to `failed`. Heuristic, not a contract.

**Fix** — generalize the existing `HCS_UNSUPPORTED` marker into an explicit
result contract; prefer it over recap inference:

```python
# hcs/runner.py
RESULT_RE = re.compile(r"HCS_RESULT:\s*(?P<status>pass|fail|unsupported)\b(?:\s*(?P<reason>.*))?")
# precedence: explicit RESULT_RE  >  return_code  >  recap heuristic
```

```yaml
# end of each role
- ansible.builtin.debug: { msg: "HCS_RESULT: pass" }
```

Roles adopt incrementally; until a role emits a marker, current behavior stands.

## C8 — CI never runs a role on AlmaLinux

**Where:** `.github/workflows/` (`python.yml` = unit tests + **dry-run**;
`ci.yml` = YAML/shell/ansible **syntax** only)
**Root cause:** `--syntax-check` and `--dry-run` execute no Ansible, so C1/C2/C5
(wrong package, undefined var, wrong repo) are invisible to CI.

**Fix** — add a containerized functional job that actually runs the fast path:

```yaml
functional:
  strategy: { matrix: { image: ["almalinux:9", "almalinux:10"] } }
  runs-on: ubuntu-latest
  container: ${{ matrix.image }}
  steps:
    - uses: actions/checkout@v4
    - run: dnf -y install python3 ansible-core
    - run: python3 -m hcs run --profile check --inventory 127.0.0.1, -c local
    # assert run.summary.json status == passed
```

Grow coverage one required test at a time (`containers`, then `kvm`).

---

## Fix order

1. **C3, C4** — one-liners; stop emitting wrong/volatile evidence immediately.
2. **C1, C5** — unblock the required `containers`/`ltp` tests on stock AlmaLinux.
3. **C2, C7** — correct status semantics (single-host + result contract).
4. **C6** — safe long runs.
5. **C8** — regression net so the above cannot silently return.

## Follow-ups surfaced by validation

- **LTP pinned tag `20220121` fails to build on AlmaLinux 10.2** — GCC aborts with
  `bp cannot be used in 'asm' here`, a known old-LTP/modern-GCC incompatibility.
  The VPS run confirmed CRB enable (C5), package install without `redhat-lsb-core`
  (P1), and clone all succeed; only the old-tag compile fails. Fix: bump to a
  modern LTP release and expose it as an `ltp_version` runner var.
