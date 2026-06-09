"""Built-in runner profiles and test registry."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class TestSpec:
    """A runnable Ansible tag exposed as a runner test step."""

    test_id: str
    display_name: str
    tag: str


@dataclass(frozen=True)
class ProfileSpec:
    """A named test plan with profile-specific Ansible variables."""

    name: str
    description: str
    tests: tuple[str, ...]
    extra_vars: dict[str, str] = field(default_factory=dict)


TESTS: dict[str, TestSpec] = {
    "hw_detection": TestSpec("hw_detection", "Hardware detection", "hw_detection"),
    "containers": TestSpec("containers", "Containers", "containers"),
    "kvm": TestSpec("kvm", "KVM", "kvm"),
    "cpu": TestSpec("cpu", "CPU stress", "cpu"),
    "network": TestSpec("network", "Network", "network"),
    "raid": TestSpec("raid", "MD RAID", "raid"),
    "ltp": TestSpec("ltp", "Linux Test Project", "ltp"),
    "phoronix": TestSpec("phoronix", "Phoronix", "phoronix"),
    "gpu_burn": TestSpec("gpu_burn", "GPU Burn", "gpu_burn"),
    "ai_llm": TestSpec("ai_llm", "AI inference (llama.cpp)", "ai_llm"),
    "cllimits": TestSpec("cllimits", "CloudLinux limits", "cllimits"),
}


PROFILES: dict[str, ProfileSpec] = {
    "check": ProfileSpec(
        name="check",
        description="Fast sanity pass for runner, inventory, and hardware discovery.",
        tests=("hw_detection",),
        extra_vars={
            "cpu_duration": "2m",
            "network_duration": "60",
            "raid_duration": "60",
            "gpu_burn_duration": "60",
            "ai_llm_repetitions": "2",
            "ltp_suites": "fork",
            "phoronix_need_space": "1",
        },
    ),
    "short": ProfileSpec(
        name="short",
        description="Short functional pass for early feedback.",
        tests=("hw_detection", "containers", "kvm", "cpu"),
        extra_vars={
            "cpu_duration": "5m",
            "network_duration": "120",
            "raid_duration": "120",
            "gpu_burn_duration": "300",
            "ai_llm_repetitions": "3",
            "ltp_suites": "fork",
            "phoronix_need_space": "1",
        },
    ),
    "medium": ProfileSpec(
        name="medium",
        description="Practical default certification pass.",
        tests=("hw_detection", "containers", "kvm", "cpu", "network", "raid"),
        extra_vars={
            "cpu_duration": "10m",
            "network_duration": "600",
            "raid_duration": "600",
            "gpu_burn_duration": "900",
            "ai_llm_repetitions": "5",
            "ltp_suites": "fork",
        },
    ),
    "long": ProfileSpec(
        name="long",
        description="Extended certification pass with LTP and Phoronix.",
        tests=("hw_detection", "containers", "kvm", "cpu", "network", "raid", "ltp", "phoronix"),
        extra_vars={
            "cpu_duration": "30m",
            "network_duration": "3600",
            "raid_duration": "3600",
            "gpu_burn_duration": "3600",
            "ai_llm_repetitions": "5",
            "ltp_suites": "syscalls",
        },
    ),
    "very_long": ProfileSpec(
        name="very_long",
        description="Long soak-oriented pass.",
        tests=("hw_detection", "containers", "kvm", "cpu", "network", "raid", "ltp", "phoronix"),
        extra_vars={
            "cpu_duration": "4h",
            "network_duration": "14400",
            "raid_duration": "14400",
            "gpu_burn_duration": "14400",
            "ai_llm_repetitions": "8",
            "ltp_suites": "all",
        },
    ),
    "extreme": ProfileSpec(
        name="extreme",
        description="Maximum built-in coverage and duration.",
        tests=("hw_detection", "containers", "kvm", "cpu", "network", "raid", "ltp", "phoronix"),
        extra_vars={
            "cpu_duration": "8h",
            "network_duration": "28800",
            "raid_duration": "28800",
            "gpu_burn_duration": "28800",
            "ai_llm_repetitions": "10",
            "ltp_suites": "all",
        },
    ),
}
