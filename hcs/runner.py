"""Rich-powered CLI runner for the Hardware Certification Suite."""

from __future__ import annotations

import json
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import time
from dataclasses import dataclass
from datetime import UTC, datetime

from rich.console import Console
from rich.panel import Panel
from rich.progress import BarColumn, Progress, SpinnerColumn, TaskID, TextColumn, TimeElapsedColumn
from rich.table import Table

from . import __version__
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


@dataclass
class RunnerOptions:
    profile: str
    inventory: str
    connection: str | None
    playbook: Path
    work_dir: Path
    run_dir: Path | None
    extra_vars: dict[str, str]
    selected_tests: tuple[str, ...] | None
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
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def run_id(profile: str) -> str:
    return datetime.now(UTC).strftime(f"%Y%m%dT%H%M%SZ-{profile}")


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


def recap_has_failures(recap: dict[str, dict[str, int]]) -> bool:
    return any(
        stats.get("unreachable", 0) > 0
        or stats.get("failed", 0) > 0
        or stats.get("ignored", 0) > 0
        for stats in recap.values()
    )


class CertificationRunner:
    def __init__(self, options: RunnerOptions, console: Console | None = None) -> None:
        self.options = options
        self.console = console or Console()
        self.profile = PROFILES[options.profile]
        self.run_dir = options.run_dir or options.work_dir / "runs" / run_id(options.profile)

    def selected_tests(self) -> list[TestSpec]:
        test_ids = self.options.selected_tests or self.profile.tests
        return [TESTS[test_id] for test_id in test_ids]

    def render_plan(self, tests: list[TestSpec]) -> None:
        table = Table(title="Planned certification steps")
        table.add_column("#", justify="right")
        table.add_column("Test")
        table.add_column("Tag")
        table.add_column("Profile")

        for index, test in enumerate(tests, start=1):
            table.add_row(f"{index:03d}", test.display_name, test.tag, self.profile.name)

        self.console.print(
            Panel(
                f"[bold]Profile:[/bold] {self.profile.name}\n"
                f"[bold]Mode:[/bold] {self.profile.description}\n"
                f"[bold]Run dir:[/bold] {self.run_dir}\n"
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
        extra_vars.update(self.options.extra_vars)
        extra_vars.setdefault("work_dir", str(self.options.work_dir))
        command.extend(["--extra-vars", json.dumps(extra_vars)])
        return command

    def prepare_run_dir(self) -> None:
        self.run_dir.mkdir(parents=True, exist_ok=True)
        (self.run_dir / "tests").mkdir(exist_ok=True)

    def write_requested_config(self, tests: list[TestSpec]) -> None:
        requested = {
            "schema_version": 1,
            "runner_version": __version__,
            "profile": self.profile.name,
            "inventory": self.options.inventory,
            "connection": self.options.connection,
            "playbook": str(self.options.playbook),
            "work_dir": str(self.options.work_dir),
            "run_dir": str(self.run_dir),
            "dry_run": self.options.dry_run,
            "stop_on_failure": self.options.stop_on_failure,
            "extra_vars": self.options.extra_vars,
            "tests": [test.test_id for test in tests],
            "repeat": self.options.repeat,
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
            "profile": self.profile.name,
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
        status = "passed" if all(result.status in {"passed", "skipped"} for result in results) else "failed"
        summary = {
            "schema_version": 1,
            "runner_version": __version__,
            "profile": self.profile.name,
            "repeat": self.options.repeat,
            "status": status,
            "started_at": started_at,
            "finished_at": finished_at,
            "run_dir": str(self.run_dir),
            "results": [
                {
                    "step": result.step,
                    "pass_index": result.pass_index,
                    "test_id": result.test_id,
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
            f"Run directory: {self.run_dir}",
            f"Profile: {self.profile.name}",
            f"Status: {status}",
            f"Started: {started_at}",
            f"Finished: {finished_at}",
            f"Runner version: {__version__}",
            "",
            "Results:",
        ]
        for result in results:
            lines.append(
                f"  {result.step:03d} pass={result.pass_index:02d}/{result.pass_count:02d} "
                f"{result.test_id:16} {result.status:8} {result.duration_seconds:.1f}s "
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
        with console_log.open("w", encoding="utf-8", errors="replace") as handle:
            handle.write(f"$ {shlex.join(command)}\n\n")
            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                bufsize=1,
            )
            assert process.stdout is not None
            for line in process.stdout:
                handle.write(line)
                stripped = line.strip()
                if stripped:
                    recap = parse_recap_line(stripped)
                    if recap:
                        host, stats = recap
                        ansible_recap[host] = stats
                    progress.update(
                        task_id,
                        description=f"[cyan]{test.display_name}[/cyan] {stripped[:80]}",
                    )
            return_code = process.wait()

        finished_at = utc_timestamp()
        if return_code != 0:
            status = "failed"
            status_reason = f"ansible-playbook returned {return_code}"
        elif recap_has_failures(ansible_recap):
            status = "failed"
            status_reason = "ansible recap reported failed, unreachable, or ignored tasks"
        else:
            status = "passed"
            status_reason = "ok"
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

        finished_at = utc_timestamp()
        self.write_summary(results, started_at, finished_at)
        self.console.print(Panel(f"Run artifacts written to:\n[bold]{self.run_dir}[/bold]", title="Run complete"))
        return overall_exit


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
