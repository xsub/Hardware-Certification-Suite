"""Command line entry point for the Hardware Certification Suite runner."""

from __future__ import annotations

import argparse
from collections.abc import Mapping
from pathlib import Path
import sys

from rich.console import Console
from rich.markup import escape
from rich.prompt import Confirm, IntPrompt, Prompt
import yaml

from .config import DEFAULT_CONFIG_PATH, build_sandbox_paths, config_extra_vars, config_str, load_config
from .presets import (
    DEFAULT_PRESET_NAME,
    DURATION_VAR_BY_TEST,
    PROFILE_ORDER,
    config_default_preset,
    config_warnings,
    get_preset,
    parse_duration_seconds,
    preset_base_profile,
    preset_duration_warnings,
    preset_extra_vars,
    preset_manual_tests,
    preset_positive_int,
    preset_selected_tests,
    preset_str,
    preset_test_extra_vars,
    preset_test_profiles,
    preset_test_scopes,
)
from . import __version__
from .privacy import audit_artifacts
from .profiles import PROFILES, TESTS
from .runner import (
    CertificationRunner,
    RunnerOptions,
    default_connection,
    parse_extra_vars,
    render_profiles,
    render_tests,
)
from .submission import validate_submission


def positive_int(raw: str) -> int:
    value = int(raw)
    if value < 1:
        raise argparse.ArgumentTypeError("value must be >= 1")
    return value


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="hcs", description="AlmaLinux Hardware Certification Suite runner")
    parser.add_argument("--version", action="version", version=f"hcs {__version__}")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("profiles", help="List built-in run profiles")
    subparsers.add_parser("tests", help="List known test steps")

    validate_run = subparsers.add_parser("validate-run", help="Validate a completed HCS run directory")
    validate_run.add_argument("path", type=Path, help="Sandbox directory or its runner/ directory")
    validate_run.add_argument(
        "--write-manifest",
        action="store_true",
        help="Create or refresh runner/submission.manifest.json before validating",
    )

    audit_artifacts_parser = subparsers.add_parser(
        "audit-artifacts",
        help="Scan a completed run directory for likely sensitive public-submission identifiers",
    )
    audit_artifacts_parser.add_argument("path", type=Path, help="Sandbox directory or its runner/ directory")

    configure = subparsers.add_parser("configure", help="Build a named runner preset with prompts")
    configure.add_argument("--config", type=Path, default=DEFAULT_CONFIG_PATH)
    configure.add_argument("--preset", default=DEFAULT_PRESET_NAME)

    run = subparsers.add_parser("run", help="Run certification steps with Rich progress reporting")
    run.add_argument("--config", type=Path, help="YAML runner config; defaults to hcs-runner.yml when present")
    run.add_argument("--preset", help="Named preset from runner config; defaults to run.default_preset when set")
    run.add_argument("--profile", choices=sorted(PROFILES))
    run.add_argument("--inventory", help="Ansible inventory; defaults to 127.0.0.1, (local)")
    run.add_argument("--host", help="Shorthand for --inventory HOST, (a single remote SUT)")
    run.add_argument(
        "-c",
        "--connection",
        help="Ansible connection; inferred from the inventory when omitted "
        "(local for loopback, SSH for a remote host)",
    )
    run.add_argument("--playbook", type=Path, default=Path("automated.yml"))
    run.add_argument("--base-dir", type=Path, help="Base directory for generated HCS sandboxes")
    run.add_argument("--sandbox-dir", type=Path, help="Explicit sandbox root for this HCS run")
    run.add_argument("--run-id", help="Stable ID embedded in the sandbox name and reports")
    run.add_argument("--work-dir", dest="legacy_work_dir", type=Path, help="Deprecated alias for --sandbox-dir")
    run.add_argument("--run-dir", dest="legacy_run_dir", type=Path, help="Deprecated alias for --sandbox-dir")
    run.add_argument("--extra-var", action="append", default=[], metavar="KEY=VALUE")
    run.add_argument("--test", action="append", choices=sorted(TESTS), help="Run only this test id; repeatable")
    run.add_argument("--repeat", type=positive_int, help="Repeat the selected test plan N times")
    run.add_argument("--dry-run", action="store_true", help="Show plan and write dry-run artifacts without executing Ansible")
    run.add_argument("--stop-on-failure", action="store_true")
    run.add_argument(
        "--step-timeout",
        help="Per-step wall-clock limit (e.g. 7200, 90m, 4h); a step exceeding it "
        "is terminated and recorded as failed. Defaults to run.step_timeout from "
        "the config, otherwise no limit.",
    )
    return parser


def load_config_for_write(path: Path) -> dict[str, object]:
    expanded = path.expanduser()
    if not expanded.exists():
        return {}
    return load_config(expanded)


def existing_test_config(preset: Mapping[str, object] | None, test_id: str) -> Mapping[str, object]:
    if preset is None:
        return {}
    tests = preset.get("tests", {})
    if not isinstance(tests, Mapping):
        return {}
    value = tests.get(test_id, {})
    return value if isinstance(value, Mapping) else {}


def existing_test_enabled(preset: Mapping[str, object] | None, test_id: str, default: bool) -> bool:
    if preset is None:
        return default
    tests = preset.get("tests", {})
    if not isinstance(tests, Mapping) or test_id not in tests:
        return default
    value = tests[test_id]
    if value is False:
        return False
    if isinstance(value, Mapping) and value.get("enabled") is False:
        return False
    return True


def configure_preset(args: argparse.Namespace, console: Console) -> int:
    config_path = args.config.expanduser()
    try:
        config = load_config_for_write(config_path)
    except (OSError, ValueError) as exc:
        console.print(f"[red]Failed to load config:[/red] {exc}")
        return 2

    preset_name = Prompt.ask("Preset name", default=args.preset)
    try:
        existing = get_preset(config, preset_name)
    except ValueError:
        existing = None

    base_profile = Prompt.ask(
        "Base profile",
        choices=list(PROFILE_ORDER),
        default=preset_base_profile(existing) or "check",
    )
    inventory = Prompt.ask("Inventory", default=preset_str(existing, "inventory") or "127.0.0.1,")
    connection = Prompt.ask(
        "Connection (auto = local for loopback, SSH for a remote host)",
        choices=["auto", "local", "ssh", "smart", "paramiko"],
        default=preset_str(existing, "connection") or "auto",
    )
    while True:
        repeat = IntPrompt.ask("Repeat passes", default=preset_positive_int(existing, "repeat") or 1)
        if repeat >= 1:
            break
        console.print("[red]Repeat passes must be >= 1.[/red]")

    console.print()
    console.print("[bold]Select tests[/bold]")
    console.print("Use Enter to accept defaults. Each selected test can use its own profile.")

    selected_tests: dict[str, object] = {}
    for test_id, test in TESTS.items():
        test_cfg = existing_test_config(existing, test_id)
        required = isinstance(test_cfg, Mapping) and test_cfg.get("required") is True
        default_enabled = existing_test_enabled(existing, test_id, test_id in PROFILES[base_profile].tests)
        checkbox = escape("[x]" if default_enabled else "[ ]")
        scope = "required" if required else "optional"
        enabled = Confirm.ask(
            f"{checkbox} {test.display_name} ({test_id}, {scope})",
            default=default_enabled,
        )
        if not enabled:
            if required:
                console.print(
                    f"[yellow]{test_id} is required by this preset; runs will record it "
                    "as a required test not exercised.[/yellow]"
                )
            selected_tests[test_id] = {"enabled": False, "required": required}
            continue

        step_profile = Prompt.ask(
            f"  Profile for {test_id}",
            choices=list(PROFILE_ORDER),
            default=str(test_cfg.get("profile") or base_profile),
        )
        entry: dict[str, object] = {"enabled": True, "required": required, "profile": step_profile}

        if test_id in DURATION_VAR_BY_TEST:
            duration = Prompt.ask(
                "  Duration cap (empty = profile default)",
                default=str(test_cfg.get("duration") or ""),
            )
            if duration:
                entry["duration"] = duration

        if test_id == "gpu_burn":
            snap_cfg = test_cfg.get("snap", {}) if isinstance(test_cfg.get("snap", {}), Mapping) else {}
            install_snap = Confirm.ask(
                "  Allow installing gpu-burn snap when snapd exists and no binary is available",
                default=bool(snap_cfg.get("install", False)),
            )
            remove_snap = Confirm.ask(
                "  Remove gpu-burn snap at the end if HCS installed it",
                default=bool(snap_cfg.get("remove_after", install_snap)),
            )
            entry["snap"] = {
                "package": str(snap_cfg.get("package") or "gpu-burn"),
                "install": install_snap,
                "remove_after": remove_snap,
            }

        selected_tests[test_id] = entry

    preset: dict[str, object] = {
        "profile": base_profile,
        "inventory": inventory,
    }
    # "auto" defers to inventory-based inference at run time, so only persist an
    # explicit connection when the operator pins one.
    if connection != "auto":
        preset["connection"] = connection
    preset["repeat"] = repeat
    preset["tests"] = selected_tests
    run_config = config.setdefault("run", {})
    if not isinstance(run_config, dict):
        console.print("[red]Cannot update config:[/red] run section must be a mapping")
        return 2
    run_config.setdefault("base_dir", "/var/tmp")
    run_config["default_preset"] = preset_name

    presets = config.setdefault("presets", {})
    if not isinstance(presets, dict):
        console.print("[red]Cannot update config:[/red] presets section must be a mapping")
        return 2
    presets[preset_name] = preset

    config_path.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")
    console.print(f"\n[green]Saved preset[/green] [bold]{preset_name}[/bold] to {config_path}")
    console.print(f"Run it with: [bold]python -m hcs run --preset {preset_name}[/bold]")
    return 0


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
    if args.command == "validate-run":
        report = validate_submission(args.path, write_manifest=args.write_manifest)
        if args.write_manifest:
            console.print(f"[green]Wrote manifest:[/green] {report.manifest_path}")
        for issue in report.issues:
            color = "red" if issue.severity == "error" else "yellow"
            console.print(f"[{color}]{issue.severity.upper()}:[/{color}] {escape(issue.message)}")
        if report.ok:
            console.print(f"[green]Run directory is structurally valid:[/green] {report.sandbox_dir}")
            return 0
        console.print(f"[red]Run directory has {len(report.errors)} validation error(s).[/red]")
        return 1
    if args.command == "audit-artifacts":
        audit = audit_artifacts(args.path)
        if audit.ok:
            console.print(f"[green]No likely sensitive identifiers found:[/green] {audit.sandbox_dir}")
            return 0
        for finding in audit.findings:
            console.print(
                f"[yellow]{finding.category}[/yellow] "
                f"{finding.path}:{finding.line} {escape(finding.sample)}"
            )
        console.print(f"[yellow]{len(audit.findings)} privacy finding(s); review before publishing.[/yellow]")
        return 1
    if args.command == "configure":
        return configure_preset(args, console)
    if args.command == "run":
        if args.host and args.inventory:
            parser.error("--host and --inventory are mutually exclusive")
        try:
            config = load_config(args.config)
            preset_name = args.preset or (None if args.profile else config_default_preset(config))
            preset = get_preset(config, preset_name)
            profile = args.profile or preset_base_profile(preset) or "check"
            host_inventory = f"{args.host}," if args.host else None
            inventory = args.inventory or host_inventory or preset_str(preset, "inventory") or "127.0.0.1,"
            explicit_connection = (
                args.connection if args.connection is not None else preset_str(preset, "connection")
            )
            connection = explicit_connection if explicit_connection is not None else default_connection(inventory)
            repeat = args.repeat or preset_positive_int(preset, "repeat") or 1
            config_vars = config_extra_vars(config)
            preset_vars = preset_extra_vars(preset)
            cli_vars = parse_extra_vars(args.extra_var)
            extra_vars = {**config_vars, **preset_vars}
            selected_tests = tuple(args.test) if args.test else preset_selected_tests(preset)
            test_profiles = preset_test_profiles(preset)
            test_extra_vars = preset_test_extra_vars(preset)
            test_scopes = preset_test_scopes(preset)
            manual_tests = preset_manual_tests(preset)
            for warning in (*config_warnings(config, preset), *preset_duration_warnings(preset)):
                console.print(f"[yellow]config warning:[/yellow] {escape(warning)}")
            step_timeout_raw = args.step_timeout or config_str(config, "run", "step_timeout")
            step_timeout: float | None = None
            if step_timeout_raw:
                parsed_timeout = parse_duration_seconds(str(step_timeout_raw))
                if parsed_timeout is None or parsed_timeout < 1:
                    raise ValueError(f"invalid step timeout: {step_timeout_raw}")
                step_timeout = float(parsed_timeout)
            sandbox_dir = args.sandbox_dir or args.legacy_work_dir or args.legacy_run_dir
            paths = build_sandbox_paths(
                config=config,
                profile=profile,
                base_dir=args.base_dir,
                sandbox_dir=sandbox_dir,
                run_id=args.run_id,
            )
        except (OSError, ValueError) as exc:
            parser.error(str(exc))

        options = RunnerOptions(
            preset_name=preset_name,
            profile=profile,
            inventory=inventory,
            connection=connection,
            playbook=args.playbook,
            paths=paths,
            extra_vars=extra_vars,
            selected_tests=selected_tests,
            test_profiles=test_profiles,
            test_extra_vars=test_extra_vars,
            test_scopes=test_scopes,
            repeat=repeat,
            dry_run=args.dry_run,
            stop_on_failure=args.stop_on_failure,
            cli_extra_vars=cli_vars,
            step_timeout=step_timeout,
            manual_tests=manual_tests,
        )
        return CertificationRunner(options, console=console).run()

    parser.error(f"unknown command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
