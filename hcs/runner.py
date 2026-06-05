"""Rich-powered CLI runner for the Hardware Certification Suite."""

from __future__ import annotations

import json
import os
from pathlib import Path
import re
import shlex
import shutil
import signal
import subprocess
import time
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime, timezone

from rich.columns import Columns
from rich.console import Console
from rich.console import Group
from rich.panel import Panel
from rich.progress import BarColumn, Progress, SpinnerColumn, TaskID, TextColumn, TimeElapsedColumn
from rich.table import Table
from rich.text import Text

from . import __version__
from .config import SandboxPaths
from .identity import SystemSummary, collect_system_summary, distro_logo
from .profiles import PROFILES, TESTS, TestSpec


RECAP_RE = re.compile(
    r"^(?P<host>\S+)\s*:\s*"
    r"ok=(?P<ok>\d+)\s+"
    r"changed=(?P<changed>\d+)\s+"
    r"unreachable=(?P<unreachable>\d+)\s+"
    r"failed=(?P<failed>\d+)\s+"
    r"skipped=(?P<skipped>\d+)\s+"
    r"rescued=(?P<rescued>\d+)\s+"
    r"ignored=(?P<ignored>\d+)"
)
UNSUPPORTED_RE = re.compile(r"HCS_UNSUPPORTED:\s*(?P<reason>[^\"}]+)")
RESULT_RE = re.compile(r"HCS_RESULT:\s*(?P<status>pass|fail|unsupported)\b[ \t]*(?P<reason>[^\"}]*)")

# The runner parses Ansible's default recap format; pin it so a user's
# ANSIBLE_STDOUT_CALLBACK cannot silently break pass/fail detection.
ANSIBLE_ENV = {
    "ANSIBLE_STDOUT_CALLBACK": "default",
    "ANSIBLE_NOCOLOR": "1",
    "ANSIBLE_FORCE_COLOR": "0",
}

# Inventories naming only these hosts run with the local connection; anything
# that names a distinct host must run over SSH.
LOOPBACK_HOSTS = frozenset({"127.0.0.1", "localhost", "::1", "ip6-localhost"})


def default_connection(inventory: str) -> str | None:
    """Infer the Ansible connection from the inventory when none is set.

    A loopback-only inventory runs locally; anything that names a distinct host
    returns ``None`` so the runner omits ``-c`` and Ansible uses its configured
    default (SSH). This stops a remote SUT from being silently certified on the
    controller via a hardcoded ``-c local`` — wrong-machine evidence.
    """
    hosts = [host.strip() for host in inventory.split(",") if host.strip()]
    if hosts and all(host in LOOPBACK_HOSTS for host in hosts):
        return "local"
    return None


def ansible_subprocess_env(base: Mapping[str, str] | None = None) -> dict[str, str]:
    env = dict(os.environ if base is None else base)
    env.update(ANSIBLE_ENV)
    return env


def terminate_process_group(process: subprocess.Popen) -> None:
    """Stop a child started with start_new_session and its descendants."""
    try:
        os.killpg(process.pid, signal.SIGTERM)
    except (ProcessLookupError, PermissionError):
        pass


UI_REFRESH_SECONDS = 0.1


def should_refresh_ui(last: float, now: float, interval: float = UI_REFRESH_SECONDS) -> bool:
    """Throttle live-line UI updates; verbose suites emit thousands of lines."""
    return (now - last) >= interval


@dataclass
class RunnerOptions:
    preset_name: str | None
    profile: str
    inventory: str
    connection: str | None
    playbook: Path
    paths: SandboxPaths
    extra_vars: dict[str, str]
    selected_tests: tuple[str, ...] | None
    test_profiles: dict[str, str]
    test_extra_vars: dict[str, dict[str, str]]
    test_scopes: dict[str, str]
    repeat: int
    dry_run: bool
    stop_on_failure: bool


@dataclass
class StepResult:
    step: int
    pass_index: int
    pass_count: int
    test_id: str
    display_name: str
    status: str
    status_reason: str
    return_code: int | None
    started_at: str
    finished_at: str
    duration_seconds: float
    command: list[str]
    artifacts: list[str]
    ansible_recap: dict[str, dict[str, int]]


def utc_timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_extra_vars(values: list[str]) -> dict[str, str]:
    parsed: dict[str, str] = {}
    for value in values:
        if "=" not in value:
            raise ValueError(f"extra var must use KEY=VALUE syntax: {value}")
        key, raw = value.split("=", 1)
        if not key:
            raise ValueError(f"extra var key cannot be empty: {value}")
        parsed[key] = raw
    return parsed


def parse_recap_line(line: str) -> tuple[str, dict[str, int]] | None:
    match = RECAP_RE.match(line.strip())
    if not match:
        return None

    host = match.group("host")
    stats = {
        key: int(match.group(key))
        for key in ("ok", "changed", "unreachable", "failed", "skipped", "rescued", "ignored")
    }
    return host, stats


def recap_has_hard_failures(recap: dict[str, dict[str, int]]) -> bool:
    """Recap shows a real failure: a failed or unreachable task."""
    return any(
        stats.get("unreachable", 0) > 0 or stats.get("failed", 0) > 0
        for stats in recap.values()
    )


def recap_has_failures(recap: dict[str, dict[str, int]]) -> bool:
    """Recap shows a hard failure or a tolerated ``ignored`` task."""
    return recap_has_hard_failures(recap) or any(
        stats.get("ignored", 0) > 0 for stats in recap.values()
    )


def derive_status(
    *,
    return_code: int | None,
    result_status: str | None,
    result_reason: str | None,
    unsupported_reason: str | None,
    recap: dict[str, dict[str, int]],
) -> tuple[str, str]:
    """Map run signals to a step status, most authoritative signal first.

    An explicit ``HCS_RESULT: fail`` from a role wins, then a non-zero ansible
    return code, then a hard recap failure (a failed/unreachable task, which an
    explicit pass must never mask), then an explicit ``HCS_RESULT: pass`` (which
    *does* override tolerated ``ignored`` recap noise), then an unsupported
    marker, then the recap heuristic for the no-contract path.
    """
    if result_status == "fail":
        return "failed", result_reason or "HCS_RESULT: fail"
    if return_code not in (0, None):
        return "failed", f"ansible-playbook returned {return_code}"
    if recap_has_hard_failures(recap):
        return "failed", "ansible recap reported failed or unreachable tasks"
    if result_status == "pass":
        return "passed", result_reason or "ok"
    if result_status == "unsupported" or unsupported_reason is not None:
        return "unsupported", result_reason or unsupported_reason or "unsupported"
    if recap_has_failures(recap):
        return "failed", "ansible recap reported ignored tasks"
    return "passed", "ok"


def run_status(results: list[StepResult]) -> str:
    if any(result.status == "failed" for result in results):
        return "failed"
    if any(result.status == "unsupported" for result in results):
        return "passed_with_warnings"
    return "passed"


@dataclass
class RunRecap:
    counts: dict[str, int]
    total_seconds: float
    slowest: StepResult | None


def summarize_results(results: list[StepResult]) -> RunRecap:
    counts = {"passed": 0, "failed": 0, "unsupported": 0, "skipped": 0}
    for result in results:
        counts[result.status] = counts.get(result.status, 0) + 1
    total = sum(result.duration_seconds for result in results)
    slowest = max(results, key=lambda result: result.duration_seconds, default=None)
    return RunRecap(counts=counts, total_seconds=total, slowest=slowest)


class CertificationRunner:
    def __init__(self, options: RunnerOptions, console: Console | None = None) -> None:
        self.options = options
        self.console = console or Console()
        self.profile = PROFILES[options.profile]
        self.paths = options.paths
        self.run_dir = self.paths.runner_dir
        self.system_summary = collect_system_summary()

    def selected_tests(self) -> list[TestSpec]:
        test_ids = self.options.selected_tests or self.profile.tests
        return [TESTS[test_id] for test_id in test_ids]

    def render_identity_header(self) -> None:
        renderables: list[object] = []
        logo = distro_logo()
        if logo is not None:
            if logo.ansi:
                renderables.append(Text.from_ansi(logo.text))
            elif logo.alma_fallback:
                renderables.append(almalinux_logo_text(logo.text))
            else:
                renderables.append(logo.text)

        renderables.append(system_summary_renderable(self.system_summary))
        self.console.print(Columns(renderables, padding=(0, 4), expand=False))

    def render_plan(self, tests: list[TestSpec]) -> None:
        table = Table(title="Planned certification steps")
        table.add_column("#", justify="right")
        table.add_column("Test")
        table.add_column("Tag")
        table.add_column("Profile")
        table.add_column("Scope")

        for index, test in enumerate(tests, start=1):
            step_profile = self.options.test_profiles.get(test.test_id, self.profile.name)
            scope = self.options.test_scopes.get(test.test_id, "profile")
            table.add_row(f"{index:03d}", test.display_name, test.tag, step_profile, scope)

        self.render_identity_header()
        preset_line = f"[bold]Preset:[/bold] {self.options.preset_name}\n" if self.options.preset_name else ""
        self.console.print(
            Panel(
                preset_line +
                f"[bold]Profile:[/bold] {self.profile.name}\n"
                f"[bold]Mode:[/bold] {self.profile.description}\n"
                f"[bold]Run ID:[/bold] {self.paths.run_id}\n"
                f"[bold]Sandbox:[/bold] {self.paths.sandbox_dir}\n"
                f"[bold]Runner artifacts:[/bold] {self.run_dir}\n"
                f"[bold]Inventory:[/bold] {self.options.inventory}",
                title="AlmaLinux Hardware Certification Suite",
            )
        )
        self.console.print(table)
        if self.options.repeat > 1:
            self.console.print(
                f"[bold]Repeat:[/bold] {self.options.repeat} passes, "
                f"{len(tests) * self.options.repeat} total steps"
            )

    def build_command(self, test: TestSpec) -> list[str]:
        command = [
            "ansible-playbook",
            "-i",
            self.options.inventory,
            str(self.options.playbook),
            "--tags",
            test.tag,
        ]
        if self.options.connection:
            command.extend(["-c", self.options.connection])

        extra_vars = dict(self.profile.extra_vars)
        step_profile = self.options.test_profiles.get(test.test_id)
        if step_profile:
            extra_vars.update(PROFILES[step_profile].extra_vars)
        extra_vars.update(self.options.extra_vars)
        extra_vars.update(self.options.test_extra_vars.get(test.test_id, {}))
        sandbox_extra_vars = {
            "hcs_run_id": self.paths.run_id,
            "hcs_run_timestamp": self.paths.timestamp,
            "sandbox_dir": str(self.paths.sandbox_dir),
            "work_dir": str(self.paths.sandbox_dir),
            "scratch_dir": str(self.paths.scratch_dir),
            "cache_dir": str(self.paths.cache_dir),
            "artifacts_dir": str(self.paths.artifacts_dir),
            "unique_logs_folder": str(self.paths.logs_dir),
            "tests_dir": str(self.paths.sut_tests_dir),
            "phoronix_folder": str(self.paths.phoronix_dir),
            "ltp_clone_path": str(self.paths.ltp_dir),
        }
        sandbox_extra_vars.update(extra_vars)
        command.extend(["--extra-vars", json.dumps(sandbox_extra_vars)])
        return command

    def prepare_run_dir(self) -> None:
        for directory in (
            self.paths.sandbox_dir,
            self.paths.runner_dir,
            self.paths.logs_dir,
            self.paths.scratch_dir,
            self.paths.cache_dir,
            self.paths.artifacts_dir,
        ):
            directory.mkdir(parents=True, exist_ok=True)
        (self.run_dir / "tests").mkdir(exist_ok=True)

    def write_requested_config(self, tests: list[TestSpec]) -> None:
        requested = {
            "schema_version": 1,
            "runner_version": __version__,
            "preset": self.options.preset_name,
            "profile": self.profile.name,
            "inventory": self.options.inventory,
            "connection": self.options.connection,
            "playbook": str(self.options.playbook),
            "paths": self.paths.as_dict(),
            "dry_run": self.options.dry_run,
            "stop_on_failure": self.options.stop_on_failure,
            "extra_vars": self.options.extra_vars,
            "test_profiles": self.options.test_profiles,
            "test_extra_vars": self.options.test_extra_vars,
            "test_scopes": self.options.test_scopes,
            "tests": [test.test_id for test in tests],
            "repeat": self.options.repeat,
            "controller_system": system_summary_payload(self.system_summary),
        }
        (self.run_dir / "config.requested.json").write_text(
            json.dumps(requested, indent=2) + "\n",
            encoding="utf-8",
        )

    def write_step_result(self, step_dir: Path, result: StepResult) -> None:
        result_name = f"{result.step:03d}-pass{result.pass_index:02d}-{result.test_id}.result.json"
        result_path = step_dir / result_name
        payload = {
            "schema_version": 1,
            "runner_version": __version__,
            "step": result.step,
            "pass_index": result.pass_index,
            "pass_count": result.pass_count,
            "test_id": result.test_id,
            "display_name": result.display_name,
            "preset": self.options.preset_name,
            "profile": self.profile.name,
            "scope": self.options.test_scopes.get(result.test_id, "profile"),
            "status": result.status,
            "status_reason": result.status_reason,
            "return_code": result.return_code,
            "started_at": result.started_at,
            "finished_at": result.finished_at,
            "duration_seconds": round(result.duration_seconds, 3),
            "command": result.command,
            "artifacts": result.artifacts,
            "ansible_recap": result.ansible_recap,
        }
        result_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    def write_summary(self, results: list[StepResult], started_at: str, finished_at: str) -> None:
        status = run_status(results)
        summary = {
            "schema_version": 1,
            "runner_version": __version__,
            "preset": self.options.preset_name,
            "profile": self.profile.name,
            "repeat": self.options.repeat,
            "status": status,
            "started_at": started_at,
            "finished_at": finished_at,
            "paths": self.paths.as_dict(),
            "controller_system": system_summary_payload(self.system_summary),
            "results": [
                {
                    "step": result.step,
                    "pass_index": result.pass_index,
                    "test_id": result.test_id,
                    "scope": self.options.test_scopes.get(result.test_id, "profile"),
                    "status": result.status,
                    "status_reason": result.status_reason,
                    "return_code": result.return_code,
                    "duration_seconds": round(result.duration_seconds, 3),
                    "artifacts": result.artifacts,
                    "ansible_recap": result.ansible_recap,
                }
                for result in results
            ],
        }
        (self.run_dir / "run.summary.json").write_text(
            json.dumps(summary, indent=2) + "\n",
            encoding="utf-8",
        )
        self.write_text_report(results, status, started_at, finished_at)
        self.write_pdf_report(results, status, started_at, finished_at)

    def write_pdf_report(
        self,
        results: list[StepResult],
        status: str,
        started_at: str,
        finished_at: str,
    ) -> None:
        """Write the branded PDF report; never let it break a run."""
        try:
            from .report_pdf import write_pdf_report as render_pdf
        except Exception:
            return
        recap = summarize_results(results)
        result_dicts = [
            {
                "step": result.step,
                "test_id": result.test_id,
                "display_name": result.display_name,
                "scope": self.options.test_scopes.get(result.test_id, "profile"),
                "status": result.status,
                "status_reason": result.status_reason,
                "return_code": result.return_code,
                "duration_seconds": result.duration_seconds,
            }
            for result in results
        ]
        try:
            written = render_pdf(
                self.run_dir / "run.report.pdf",
                run_id=self.paths.run_id,
                profile=self.profile.name,
                preset_name=self.options.preset_name,
                repeat=self.options.repeat,
                status=status,
                started_at=started_at,
                finished_at=finished_at,
                generated_at=utc_timestamp(),
                system_title=self.system_summary.title,
                system_facts=[(fact.label, fact.value) for fact in self.system_summary.facts],
                results=result_dicts,
                counts=recap.counts,
                total_seconds=recap.total_seconds,
                version=__version__,
            )
        except Exception as exc:  # never fail the run over a report
            self.console.print(f"[yellow]PDF report skipped:[/yellow] {exc}")
            return
        if not written:
            self.console.print("[dim]PDF report skipped: reportlab not installed.[/dim]")

    def write_text_report(
        self,
        results: list[StepResult],
        status: str,
        started_at: str,
        finished_at: str,
    ) -> None:
        lines = [
            "AlmaLinux Hardware Certification Suite",
            "",
            f"Run ID: {self.paths.run_id}",
            f"Sandbox directory: {self.paths.sandbox_dir}",
            f"Runner directory: {self.run_dir}",
            f"Preset: {self.options.preset_name or 'none'}",
            f"Profile: {self.profile.name}",
            f"Status: {status}",
            f"Started: {started_at}",
            f"Finished: {finished_at}",
            f"Runner version: {__version__}",
            "",
            "Controller system:",
        ]
        for fact in self.system_summary.facts:
            lines.append(f"  {fact.label}: {fact.value}")
        lines.extend(
            [
                "",
                "Results:",
            ]
        )
        for result in results:
            scope = self.options.test_scopes.get(result.test_id, "profile")
            lines.append(
                f"  {result.step:03d} pass={result.pass_index:02d}/{result.pass_count:02d} "
                f"{result.test_id:16} {scope:8} {result.status:8} {result.duration_seconds:.1f}s "
                f"rc={result.return_code} {result.status_reason}"
            )
        lines.extend(
            [
                "",
                f"Generated by AlmaLinux Hardware Certification Suite {__version__}",
                f"Generated: {utc_timestamp()}",
            ]
        )
        (self.run_dir / "run.report.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")

    def execute_step(
        self,
        step: int,
        pass_index: int,
        test: TestSpec,
        progress: Progress,
        task_id: TaskID,
    ) -> StepResult:
        started_at = utc_timestamp()
        start = time.monotonic()
        artifact_base = f"{step:03d}-pass{pass_index:02d}-{test.test_id}"
        step_dir = self.run_dir / "tests" / artifact_base
        step_dir.mkdir(parents=True, exist_ok=True)
        console_log = step_dir / f"{artifact_base}.console.log"
        command = self.build_command(test)

        progress.update(
            task_id,
            description=f"[cyan]Pass {pass_index}/{self.options.repeat}: running {test.display_name}",
        )
        if self.options.dry_run:
            console_log.write_text("Dry run; command not executed.\n" + shlex.join(command) + "\n", encoding="utf-8")
            finished_at = utc_timestamp()
            return StepResult(
                step=step,
                pass_index=pass_index,
                pass_count=self.options.repeat,
                test_id=test.test_id,
                display_name=test.display_name,
                status="skipped",
                status_reason="dry-run",
                return_code=None,
                started_at=started_at,
                finished_at=finished_at,
                duration_seconds=time.monotonic() - start,
                command=command,
                artifacts=[str(console_log.relative_to(self.run_dir))],
                ansible_recap={},
            )

        ansible_recap: dict[str, dict[str, int]] = {}
        unsupported_reason: str | None = None
        result_status: str | None = None
        result_reason: str | None = None
        with console_log.open("w", encoding="utf-8", errors="replace") as handle:
            handle.write(f"$ {shlex.join(command)}\n\n")
            with subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                bufsize=1,
                env=ansible_subprocess_env(),
                start_new_session=True,
            ) as process:
                assert process.stdout is not None
                last_ui = 0.0
                try:
                    for line in process.stdout:
                        handle.write(line)
                        stripped = line.strip()
                        if stripped:
                            result = RESULT_RE.search(stripped)
                            if result and result_status is None:
                                result_status = result.group("status")
                                result_reason = (result.group("reason") or "").strip() or None
                            unsupported = UNSUPPORTED_RE.search(stripped)
                            if unsupported and unsupported_reason is None:
                                unsupported_reason = unsupported.group("reason").strip()
                            recap = parse_recap_line(stripped)
                            if recap:
                                host, stats = recap
                                ansible_recap[host] = stats
                            now = time.monotonic()
                            if should_refresh_ui(last_ui, now):
                                last_ui = now
                                progress.update(
                                    task_id,
                                    description=f"[cyan]{test.display_name}[/cyan] {stripped[:80]}",
                                )
                    return_code = process.wait()
                except KeyboardInterrupt:
                    terminate_process_group(process)
                    raise

        finished_at = utc_timestamp()
        status, status_reason = derive_status(
            return_code=return_code,
            result_status=result_status,
            result_reason=result_reason,
            unsupported_reason=unsupported_reason,
            recap=ansible_recap,
        )
        return StepResult(
            step=step,
            pass_index=pass_index,
            pass_count=self.options.repeat,
            test_id=test.test_id,
            display_name=test.display_name,
            status=status,
            status_reason=status_reason,
            return_code=return_code,
            started_at=started_at,
            finished_at=finished_at,
            duration_seconds=time.monotonic() - start,
            command=command,
            artifacts=[str(console_log.relative_to(self.run_dir))],
            ansible_recap=ansible_recap,
        )

    def render_recap(self, results: list[StepResult]) -> None:
        if not results:
            return
        recap = summarize_results(results)
        styles = {"passed": "green", "failed": "red", "unsupported": "yellow", "skipped": "dim"}
        table = Table(title="Run recap")
        table.add_column("#", justify="right")
        table.add_column("Test")
        table.add_column("Scope")
        table.add_column("Status")
        table.add_column("Duration", justify="right")
        table.add_column("rc", justify="right")
        for result in results:
            scope = self.options.test_scopes.get(result.test_id, "profile")
            style = styles.get(result.status, "")
            status_cell = f"[{style}]{result.status}[/{style}]" if style else result.status
            return_code = "-" if result.return_code is None else str(result.return_code)
            table.add_row(
                f"{result.step:03d}",
                result.display_name,
                scope,
                status_cell,
                f"{result.duration_seconds:.1f}s",
                return_code,
            )
        self.console.print(table)
        counts = recap.counts
        totals = (
            f"[bold]{counts['passed']} passed[/bold], {counts['failed']} failed, "
            f"{counts['unsupported']} unsupported, {counts['skipped']} skipped"
            f" — total {recap.total_seconds:.1f}s"
        )
        if recap.slowest is not None:
            totals += f", slowest {recap.slowest.display_name} {recap.slowest.duration_seconds:.1f}s"
        self.console.print(totals)

    def run(self) -> int:
        tests = self.selected_tests()
        self.prepare_run_dir()
        self.write_requested_config(tests)
        self.render_plan(tests)

        if not self.options.dry_run and shutil.which("ansible-playbook") is None:
            self.console.print("[red]ansible-playbook was not found on PATH.[/red]")
            return 127

        started_at = utc_timestamp()
        results: list[StepResult] = []
        overall_exit = 0
        interrupted = False
        try:
            overall_exit = self._execute_plan(tests, results)
        except KeyboardInterrupt:
            interrupted = True
            overall_exit = 130
            self.console.print("\n[yellow]Interrupted — writing partial report.[/yellow]")
        finally:
            self.write_summary(results, started_at, utc_timestamp())

        self.render_recap(results)
        self.console.print(
            Panel(
                f"Sandbox:\n[bold]{self.paths.sandbox_dir}[/bold]\n\n"
                f"Runner artifacts:\n[bold]{self.run_dir}[/bold]",
                title="Run interrupted" if interrupted else "Run complete",
            )
        )
        return overall_exit

    def _execute_plan(self, tests: list[TestSpec], results: list[StepResult]) -> int:
        overall_exit = 0
        with Progress(
            SpinnerColumn(),
            TextColumn("{task.description}"),
            BarColumn(),
            TextColumn("{task.completed}/{task.total}"),
            TimeElapsedColumn(),
            console=self.console,
        ) as progress:
            overall = progress.add_task("[bold]Suite progress", total=len(tests) * self.options.repeat)
            current = progress.add_task("[dim]Waiting", total=None)

            step = 0
            should_stop = False
            for pass_index in range(1, self.options.repeat + 1):
                for test in tests:
                    step += 1
                    result = self.execute_step(step, pass_index, test, progress, current)
                    results.append(result)
                    step_dir = self.run_dir / "tests" / f"{step:03d}-pass{pass_index:02d}-{test.test_id}"
                    self.write_step_result(step_dir, result)
                    progress.advance(overall)

                    label = f"{step:03d} pass={pass_index:02d}/{self.options.repeat:02d} {test.display_name}"
                    if result.status == "passed":
                        self.console.print(f"[green]PASS[/green] {label}")
                    elif result.status == "skipped":
                        self.console.print(f"[yellow]SKIP[/yellow] {label}")
                    elif result.status == "unsupported":
                        self.console.print(f"[yellow]UNSUPPORTED[/yellow] {label} {result.status_reason}")
                    else:
                        overall_exit = result.return_code or 1
                        self.console.print(
                            f"[red]FAIL[/red] {label} rc={result.return_code} {result.status_reason}"
                        )
                        if self.options.stop_on_failure:
                            should_stop = True
                            break
                if should_stop:
                    break
        return overall_exit


def almalinux_logo_text(logo: str) -> Text:
    lines = logo.splitlines()
    width = max((len(line) for line in lines), default=1)
    rendered = Text()
    for y, line in enumerate(lines):
        for x, character in enumerate(line):
            if character == " ":
                rendered.append(character)
                continue
            if y < len(lines) * 0.42 and x < width * 0.45:
                style = "bold red"
            elif y < len(lines) * 0.42:
                style = "bold yellow"
            elif x < width * 0.34:
                style = "bold blue"
            elif x < width * 0.67:
                style = "bold cyan"
            else:
                style = "bold green"
            rendered.append(character, style=style)
        rendered.append("\n")
    return rendered


def system_summary_renderable(summary: SystemSummary) -> Group:
    facts = Table.grid(padding=(0, 1))
    facts.add_column(justify="right", style="bold yellow", no_wrap=True)
    facts.add_column(style="bold green", overflow="fold")
    for fact in summary.facts:
        facts.add_row(f"{fact.label}:", fact.value)
    return Group(
        Text(summary.title, style="bold"),
        Text("-" * len(summary.title), style="green"),
        facts,
    )


def system_summary_payload(summary: SystemSummary) -> dict[str, object]:
    return {
        "title": summary.title,
        "facts": [{"label": fact.label, "value": fact.value} for fact in summary.facts],
    }


def render_profiles(console: Console) -> None:
    table = Table(title="Available profiles")
    table.add_column("Profile")
    table.add_column("Tests")
    table.add_column("Description")
    for profile in PROFILES.values():
        table.add_row(profile.name, ", ".join(profile.tests), profile.description)
    console.print(table)


def render_tests(console: Console) -> None:
    table = Table(title="Available tests")
    table.add_column("Test ID")
    table.add_column("Display name")
    table.add_column("Ansible tag")
    for test in TESTS.values():
        table.add_row(test.test_id, test.display_name, test.tag)
    console.print(table)
