#!/usr/bin/env python3
"""Validate that repository YAML files can be parsed."""

from pathlib import Path
import sys

try:
    import yaml
except ImportError as exc:
    raise SystemExit("PyYAML is required to validate YAML files") from exc


def main():
    paths = sorted(
        path
        for pattern in ("*.yml", "*.yaml")
        for path in Path(".").rglob(pattern)
        if ".git" not in path.parts
    )
    errors = []

    for path in paths:
        try:
            with path.open("r", encoding="utf-8") as handle:
                list(yaml.safe_load_all(handle))
        except yaml.YAMLError as exc:
            errors.append(f"{path}: {exc}")

    if errors:
        print("YAML validation failed:", file=sys.stderr)
        for error in errors:
            print(f"  - {error}", file=sys.stderr)
        return 1

    print(f"Validated {len(paths)} YAML files.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
