"""Named runner preset helpers."""

from __future__ import annotations

from collections.abc import Mapping
import re

from .profiles import PROFILES, TESTS


DEFAULT_PRESET_NAME = "default"
CERTIFICATION_PRESET_NAME = "certification"
PROFILE_ORDER = ("check", "short", "medium", "long", "very_long", "extreme")
DURATION_VAR_BY_TEST = {
    "cpu": "cpu_duration",
    "network": "network_duration",
    "raid": "raid_duration",
    "gpu_burn": "gpu_burn_duration",
}
SECONDS_DURATION_TESTS = {"network", "raid", "gpu_burn"}
GPU_BURN_SNAP_VARS = {
    "install": "gpu_burn_install_snap",
    "remove_after": "gpu_burn_remove_snap_after",
    "package": "gpu_burn_snap_package",
}
BUILTIN_PRESETS: dict[str, dict[str, object]] = {
    CERTIFICATION_PRESET_NAME: {
        "description": "ALOSF certification policy preset for ordinary automated hardware certification evidence.",
        "profile": "long",
        "inventory": "127.0.0.1,",
        "repeat": 1,
        "tests": {
            "hw_detection": {
                "enabled": True,
                "required": True,
                "profile": "check",
            },
            "containers": {
                "enabled": True,
                "required": True,
                "profile": "medium",
            },
            "kvm": {
                "enabled": True,
                "required": True,
                "profile": "medium",
            },
            "cpu": {
                "enabled": True,
                "required": True,
                "profile": "long",
                "duration": "30m",
            },
            "network": {
                "enabled": True,
                "required": True,
                "profile": "long",
                "duration": "3600",
            },
            "ltp": {
                "enabled": True,
                "required": True,
                "profile": "long",
            },
            "phoronix": {
                "enabled": True,
                "required": True,
                "profile": "long",
            },
            "raid": {
                "enabled": False,
                "required": False,
                "profile": "medium",
                "duration": "600",
                "reason": "Run when the SUT has MD RAID or storage topology relevant to certification.",
            },
            "gpu_burn": {
                "enabled": False,
                "required": False,
                "profile": "medium",
                "duration": "900",
                "reason": "Run when the SUT includes supported NVIDIA GPUs and nvidia-smi works.",
                "snap": {
                    "package": "gpu-burn",
                    "install": False,
                    "remove_after": True,
                },
            },
            "ai_llm": {
                "enabled": False,
                "required": False,
                "profile": "medium",
                "reason": "Optional AI inference benchmark (llama.cpp); enable to record tokens/sec evidence on CPU or GPU.",
            },
            "cllimits": {
                "enabled": False,
                "required": False,
                "profile": "medium",
                "reason": "CloudLinux-specific validation, not part of ordinary AlmaLinux hardware certification.",
            },
        },
        "manual_tests": {
            "usb": {
                "required": True,
                "reason": "Interactive physical-port validation is handled through interactive.yml.",
            },
            "pxe": {
                "required": True,
                "reason": "Interactive boot/network validation is handled through interactive.yml.",
            },
        },
    }
}


def validate_profile(profile: str) -> str:
    if profile not in PROFILES:
        raise ValueError(f"unknown profile in runner preset: {profile}")
    return profile


def validate_test_id(test_id: str) -> str:
    if test_id not in TESTS:
        raise ValueError(f"unknown test id in runner preset: {test_id}")
    return test_id


def config_default_preset(config: Mapping[str, object]) -> str | None:
    run = config.get("run", {})
    if not isinstance(run, Mapping):
        return None
    value = run.get("default_preset")
    if value in (None, ""):
        return None
    return str(value)


def get_preset(config: Mapping[str, object], name: str | None) -> dict[str, object] | None:
    if not name:
        return None
    presets = config.get("presets", {})
    if not isinstance(presets, Mapping):
        raise ValueError("runner config presets must be a mapping")
    preset = presets.get(name)
    if preset is None:
        preset = BUILTIN_PRESETS.get(name)
    if preset is None:
        raise ValueError(f"runner preset not found: {name}")
    if not isinstance(preset, Mapping):
        raise ValueError(f"runner preset must be a mapping: {name}")
    return dict(preset)


def preset_base_profile(preset: Mapping[str, object] | None) -> str | None:
    if preset is None:
        return None
    value = preset.get("profile")
    if value in (None, ""):
        return None
    return validate_profile(str(value))


def preset_str(preset: Mapping[str, object] | None, key: str) -> str | None:
    if preset is None:
        return None
    value = preset.get(key)
    if value in (None, ""):
        return None
    return str(value)


def preset_positive_int(preset: Mapping[str, object] | None, key: str) -> int | None:
    if preset is None:
        return None
    value = preset.get(key)
    if value in (None, ""):
        return None
    parsed = int(str(value))
    if parsed < 1:
        raise ValueError(f"runner preset {key} must be >= 1")
    return parsed


def preset_extra_vars(preset: Mapping[str, object] | None) -> dict[str, str]:
    if preset is None:
        return {}
    value = preset.get("extra_vars", {})
    if value is None:
        return {}
    if not isinstance(value, Mapping):
        raise ValueError("runner preset extra_vars must be a mapping")
    return {str(key): str(raw) for key, raw in value.items()}


def preset_tests_section(preset: Mapping[str, object] | None) -> object:
    if preset is None:
        return None
    return preset.get("tests")


def preset_selected_tests(preset: Mapping[str, object] | None) -> tuple[str, ...] | None:
    tests = preset_tests_section(preset)
    if tests is None:
        return None
    if isinstance(tests, list):
        return tuple(validate_test_id(str(test_id)) for test_id in tests)
    if isinstance(tests, Mapping):
        selected: list[str] = []
        for raw_test_id, raw_config in tests.items():
            test_id = validate_test_id(str(raw_test_id))
            if raw_config is False:
                continue
            if isinstance(raw_config, Mapping) and raw_config.get("enabled") is False:
                continue
            selected.append(test_id)
        return tuple(selected)
    raise ValueError("runner preset tests must be a list or mapping")


def preset_test_scopes(preset: Mapping[str, object] | None) -> dict[str, str]:
    tests = preset_tests_section(preset)
    if not isinstance(tests, Mapping):
        return {}
    scopes: dict[str, str] = {}
    for raw_test_id, raw_config in tests.items():
        test_id = validate_test_id(str(raw_test_id))
        if not isinstance(raw_config, Mapping):
            continue
        scopes[test_id] = "required" if raw_config.get("required") is True else "optional"
    return scopes


def preset_test_profiles(preset: Mapping[str, object] | None) -> dict[str, str]:
    tests = preset_tests_section(preset)
    if not isinstance(tests, Mapping):
        return {}
    profiles: dict[str, str] = {}
    for raw_test_id, raw_config in tests.items():
        test_id = validate_test_id(str(raw_test_id))
        if not isinstance(raw_config, Mapping):
            continue
        value = raw_config.get("profile")
        if value in (None, ""):
            continue
        profiles[test_id] = validate_profile(str(value))
    return profiles


def preset_test_extra_vars(preset: Mapping[str, object] | None) -> dict[str, dict[str, str]]:
    tests = preset_tests_section(preset)
    if not isinstance(tests, Mapping):
        return {}

    base_profile = preset_base_profile(preset) or "check"
    test_profiles = preset_test_profiles(preset)
    by_test: dict[str, dict[str, str]] = {}

    for raw_test_id, raw_config in tests.items():
        test_id = validate_test_id(str(raw_test_id))
        if not isinstance(raw_config, Mapping):
            continue

        extra_vars = mapping_to_str_dict(raw_config.get("extra_vars", {}), f"{test_id}.extra_vars")
        duration = raw_config.get("duration")
        if duration not in (None, ""):
            duration_value = limiting_duration_value(
                test_id=test_id,
                profile=test_profiles.get(test_id, base_profile),
                requested=str(duration),
            )
            if duration_value is not None:
                extra_vars[DURATION_VAR_BY_TEST[test_id]] = duration_value

        if test_id == "gpu_burn":
            snap = raw_config.get("snap", {})
            if isinstance(snap, Mapping):
                for snap_key, var_name in GPU_BURN_SNAP_VARS.items():
                    snap_value = snap.get(snap_key)
                    if snap_value not in (None, ""):
                        extra_vars[var_name] = (
                            str(snap_value).lower()
                            if snap_key in {"install", "remove_after"}
                            else str(snap_value)
                        )

        if extra_vars:
            by_test[test_id] = extra_vars

    return by_test


def mapping_to_str_dict(value: object, name: str) -> dict[str, str]:
    if value is None:
        return {}
    if not isinstance(value, Mapping):
        raise ValueError(f"runner preset {name} must be a mapping")
    return {str(key): str(raw) for key, raw in value.items()}


def parse_duration_seconds(raw: str) -> int | None:
    value = raw.strip().lower()
    if not value:
        return None
    match = re.fullmatch(r"(\d+)([smhdy]?)", value)
    if not match:
        return None

    amount = int(match.group(1))
    multiplier = {
        "": 1,
        "s": 1,
        "m": 60,
        "h": 3600,
        "d": 86400,
        "y": 31536000,
    }[match.group(2)]
    return amount * multiplier


def limiting_duration_value(test_id: str, profile: str, requested: str) -> str | None:
    if test_id not in DURATION_VAR_BY_TEST:
        return None

    requested_seconds = parse_duration_seconds(requested)
    if requested_seconds is None:
        return requested

    duration_var = DURATION_VAR_BY_TEST[test_id]
    profile_value = PROFILES[profile].extra_vars.get(duration_var)
    profile_seconds = parse_duration_seconds(profile_value) if profile_value else None
    effective_seconds = min(requested_seconds, profile_seconds) if profile_seconds else requested_seconds

    if test_id in SECONDS_DURATION_TESTS:
        return str(effective_seconds)
    return f"{effective_seconds}s"
