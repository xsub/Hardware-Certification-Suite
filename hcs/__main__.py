"""Command line entry point for the Hardware Certification Suite runner."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

from rich.console import Console

from .profiles import PROFILES, TESTS
from .runner import CertificationRunner, RunnerOptions, parse_extra_vars, render_profiles, render_tests


def positive_int(raw: str) -> int:
    value = int(raw)
    if value < 1:
        raise argparse.ArgumentTypeError("value must be >= 1")
    return value


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="hcs", description="AlmaLinux Hardware Certification Suite runner")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("profiles", help="List built-in run profiles")
    subparsers.add_parser("tests", help="List known test steps")

    run = subparsers.add_parser("run", help="Run certification steps with Rich progress reporting")
    run.add_argument("--profile", choices=sorted(PROFILES), default="check")
    run.add_argument("--inventory", default="127.0.0.1,")
    run.add_argument("-c", "--connection", default="local")
    run.add_argument("--playbook", type=Path, default=Path("automated.yml"))
    run.add_argument("--work-dir", type=Path, default=Path("/var/tmp/almalinux-certification"))
    run.add_argument("--run-dir", type=Path)
    run.add_argument("--extra-var", action="append", default=[], metavar="KEY=VALUE")
    run.add_argument("--test", action="append", choices=sorted(TESTS), help="Run only this test id; repeatable")
    run.add_argument("--repeat", type=positive_int, default=1, help="Repeat the selected test plan N times")
    run.add_argument("--dry-run", action="store_true", help="Show plan and write dry-run artifacts without executing Ansible")
    run.add_argument("--stop-on-failure", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    console = Console()

    if args.command == "profiles":
        render_profiles(console)
        return 0
    if args.command == "tests":
        render_tests(console)
        return 0
    if args.command == "run":
        try:
            extra_vars = parse_extra_vars(args.extra_var)
        except ValueError as exc:
            parser.error(str(exc))

        options = RunnerOptions(
            profile=args.profile,
            inventory=args.inventory,
            connection=args.connection,
            playbook=args.playbook,
            work_dir=args.work_dir,
            run_dir=args.run_dir,
            extra_vars=extra_vars,
            selected_tests=tuple(args.test) if args.test else None,
            repeat=args.repeat,
            dry_run=args.dry_run,
            stop_on_failure=args.stop_on_failure,
        )
        return CertificationRunner(options, console=console).run()

    parser.error(f"unknown command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
