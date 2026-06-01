"""Command line entry point for the Hardware Certification Suite runner."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

from rich.console import Console

from .config import build_sandbox_paths, config_extra_vars, load_config
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
    run.add_argument("--config", type=Path, help="YAML runner config; defaults to hcs-runner.yml when present")
    run.add_argument("--profile", choices=sorted(PROFILES), default="check")
    run.add_argument("--inventory", default="127.0.0.1,")
    run.add_argument("-c", "--connection", default="local")
    run.add_argument("--playbook", type=Path, default=Path("automated.yml"))
    run.add_argument("--base-dir", type=Path, help="Base directory for generated HCS sandboxes")
    run.add_argument("--sandbox-dir", type=Path, help="Explicit sandbox root for this HCS run")
    run.add_argument("--run-id", help="Stable ID embedded in the sandbox name and reports")
    run.add_argument("--work-dir", dest="legacy_work_dir", type=Path, help="Deprecated alias for --sandbox-dir")
    run.add_argument("--run-dir", dest="legacy_run_dir", type=Path, help="Deprecated alias for --sandbox-dir")
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
            config = load_config(args.config)
            config_vars = config_extra_vars(config)
            cli_vars = parse_extra_vars(args.extra_var)
            extra_vars = {**config_vars, **cli_vars}
            sandbox_dir = args.sandbox_dir or args.legacy_work_dir or args.legacy_run_dir
            paths = build_sandbox_paths(
                config=config,
                profile=args.profile,
                base_dir=args.base_dir,
                sandbox_dir=sandbox_dir,
                run_id=args.run_id,
            )
        except (OSError, ValueError) as exc:
            parser.error(str(exc))

        options = RunnerOptions(
            profile=args.profile,
            inventory=args.inventory,
            connection=args.connection,
            playbook=args.playbook,
            paths=paths,
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
