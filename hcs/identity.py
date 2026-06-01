"""System identity and runner logo helpers."""

from __future__ import annotations

from dataclasses import dataclass
import getpass
import locale
import os
from pathlib import Path
import platform
import shutil
import socket
import struct
import subprocess
import sys


OS_RELEASE_PATH = Path("/etc/os-release")
MEMINFO_PATH = Path("/proc/meminfo")
UPTIME_PATH = Path("/proc/uptime")
CPUINFO_PATH = Path("/proc/cpuinfo")
DEFAULT_ROUTE_PATH = Path("/proc/net/route")

ALMALINUX_ASCII_LOGO = "\n".join(
    [
        "         'c:.",
        "        lkkkx, ..       ..   ,cc,",
        "        okkkk:ckkx'  .lxkkx.okkkkd",
        "        .:llcokkx'  :kkkxkko:xkkd,",
        "      .xkkkkdood:  ;kx,  .lkxlll;",
        "       xkkx.       xk'     xkkkkk:",
        "       'xkx.       xd      .....,.",
        "      .. :xkl'     :c      ..''..",
        "    .dkx'  .:ldl:'. '  ':lollldkkxo;",
        "  .''lkkko'                     ckkkx.",
        "'xkkkd:kkd.       ..  ;'        :kkxo.",
        ",xkkkd;kk'      ,d;    ld.   ':dkd::cc,",
        " .,,.;xkko'.';lxo.      dx,  :kkk'xkkkkc",
        "     'dkkkkkxo:.        ;kx  .kkk:;xkkd.",
        "       .....   .;dk:.   lkk.  :;,",
        "             :kkkkkkkdoxkkx",
        "              ,c,,;;;:xkkd.",
        "                ;kkkkl...",
        "                ;kkkkl",
        "                 ,od;",
    ]
)


@dataclass(frozen=True)
class DistroIdentity:
    distro_id: str
    name: str
    pretty_name: str


@dataclass(frozen=True)
class DistroLogo:
    text: str
    ansi: bool = False
    alma_fallback: bool = False


@dataclass(frozen=True)
class SystemFact:
    label: str
    value: str


@dataclass(frozen=True)
class SystemSummary:
    title: str
    facts: tuple[SystemFact, ...]


def parse_os_release(content: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw_line in content.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, raw_value = line.split("=", 1)
        value = raw_value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
        values[key] = value
    return values


def detect_distro(os_release_path: Path = OS_RELEASE_PATH) -> DistroIdentity | None:
    try:
        values = parse_os_release(os_release_path.read_text(encoding="utf-8"))
    except OSError:
        return None

    distro_id = values.get("ID", "").lower()
    name = values.get("NAME", distro_id)
    pretty_name = values.get("PRETTY_NAME", name)
    if not any((distro_id, name, pretty_name)):
        return None
    return DistroIdentity(distro_id=distro_id, name=name, pretty_name=pretty_name)


def fastfetch_logo_name(identity: DistroIdentity | None) -> str | None:
    if identity is None:
        return None
    if identity.distro_id == "almalinux":
        return "AlmaLinux"
    return identity.distro_id or identity.name or None


def fastfetch_logo(identity: DistroIdentity | None, timeout: float = 2.0) -> str | None:
    fastfetch = shutil.which("fastfetch")
    logo_name = fastfetch_logo_name(identity)
    if fastfetch is None or logo_name is None:
        return None

    commands = (
        [fastfetch, "--logo", logo_name, "--logo-only"],
        [fastfetch, "--logo-only"],
    )
    for command in commands:
        try:
            completed = subprocess.run(
                command,
                check=False,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=timeout,
            )
        except (OSError, subprocess.TimeoutExpired):
            continue
        output = completed.stdout.rstrip()
        if completed.returncode == 0 and output:
            return output
    return None


def distro_logo(
    identity: DistroIdentity | None = None,
    *,
    use_fastfetch: bool = True,
) -> DistroLogo | None:
    detected = identity or detect_distro()
    if use_fastfetch:
        logo = fastfetch_logo(detected)
        if logo:
            return DistroLogo(text=logo, ansi=True)

    if detected is not None and detected.distro_id == "almalinux":
        return DistroLogo(text=ALMALINUX_ASCII_LOGO, alma_fallback=True)
    return None


def command_output(command: list[str], timeout: float = 1.5) -> str | None:
    try:
        completed = subprocess.run(
            command,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if completed.returncode != 0:
        return None
    output = completed.stdout.strip()
    return output or None


def read_text(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None


def format_bytes(value: int) -> str:
    units = ("B", "KiB", "MiB", "GiB", "TiB", "PiB")
    amount = float(value)
    unit = units[0]
    for unit in units:
        if amount < 1024 or unit == units[-1]:
            break
        amount /= 1024
    if unit in {"B", "KiB"}:
        return f"{amount:.0f} {unit}"
    if amount >= 10:
        return f"{amount:.1f} {unit}"
    return f"{amount:.2f} {unit}"


def format_uptime(seconds: float) -> str:
    def unit(value: int, singular: str) -> str:
        suffix = singular if value == 1 else f"{singular}s"
        return f"{value} {suffix}"

    total = int(seconds)
    days, remainder = divmod(total, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, _ = divmod(remainder, 60)
    parts: list[str] = []
    if days:
        parts.append(unit(days, "day"))
    if hours:
        parts.append(unit(hours, "hour"))
    parts.append(unit(minutes, "min"))
    return ", ".join(parts)


def parse_meminfo(content: str) -> dict[str, int]:
    values: dict[str, int] = {}
    for line in content.splitlines():
        if ":" not in line:
            continue
        key, raw_value = line.split(":", 1)
        key = key.strip()
        parts = raw_value.split()
        if not parts:
            continue
        try:
            values[key] = int(parts[0]) * 1024
        except ValueError:
            continue
    return values


def memory_summary(meminfo: dict[str, int]) -> str | None:
    total = meminfo.get("MemTotal")
    available = meminfo.get("MemAvailable")
    if total is None or available is None or total <= 0:
        return None
    used = max(total - available, 0)
    percent = round((used / total) * 100)
    return f"{format_bytes(used)} / {format_bytes(total)} ({percent}%)"


def swap_summary(meminfo: dict[str, int]) -> str | None:
    total = meminfo.get("SwapTotal")
    free = meminfo.get("SwapFree", 0)
    if total is None:
        return None
    if total <= 0:
        return "Disabled"
    used = max(total - free, 0)
    percent = round((used / total) * 100)
    return f"{format_bytes(used)} / {format_bytes(total)} ({percent}%)"


def uptime_summary(path: Path = UPTIME_PATH) -> str | None:
    content = read_text(path)
    if content is None:
        return None
    try:
        seconds = float(content.split()[0])
    except (IndexError, ValueError):
        return None
    return format_uptime(seconds)


def package_summary() -> str | None:
    if shutil.which("rpm") is None:
        return None
    output = command_output(["rpm", "-qa"], timeout=3.0)
    if output is None:
        return None
    return f"{len(output.splitlines())} (rpm)"


def shell_summary() -> str | None:
    shell = os.environ.get("SHELL")
    if not shell:
        return None
    shell_name = Path(shell).name
    if shell_name == "bash" and shutil.which("bash"):
        first_line = command_output(["bash", "--version"])
        if first_line:
            line = first_line.splitlines()[0]
            version = line.split("version ", 1)[1].split()[0] if "version " in line else shell_name
            return f"bash {version}"
    return shell_name


def terminal_summary() -> str | None:
    try:
        return os.ttyname(1)
    except OSError:
        return os.environ.get("TERM")


def cpu_summary(path: Path = CPUINFO_PATH) -> str | None:
    content = read_text(path)
    if content is None:
        processor = platform.processor()
        return processor or None

    model = None
    logical_cpus = 0
    for line in content.splitlines():
        if line.startswith("processor"):
            logical_cpus += 1
        if model is None and line.lower().startswith("model name"):
            _, value = line.split(":", 1)
            model = value.strip()

    if model is None:
        model = platform.processor() or platform.machine()
    if logical_cpus:
        return f"{model} ({logical_cpus} logical CPUs)"
    return model


def host_summary() -> str | None:
    base = Path("/sys/class/dmi/id")
    product = read_text(base / "product_name")
    version = read_text(base / "product_version")
    vendor = read_text(base / "sys_vendor")
    parts = [part.strip() for part in (vendor, product, version) if part and part.strip()]
    if not parts:
        return None
    seen: list[str] = []
    for part in parts:
        if part not in seen:
            seen.append(part)
    return " ".join(seen)


def gpu_summary() -> str | None:
    output = command_output(["lspci", "-mm"])
    if output:
        for line in output.splitlines():
            if any(kind in line for kind in ('"VGA compatible controller"', '"3D controller"', '"Display controller"')):
                parts = line.split('"')
                quoted = [parts[index] for index in range(1, len(parts), 2)]
                if len(quoted) >= 3:
                    return f"{quoted[1]} {quoted[2]}"

    gpu = first_sysfs_gpu()
    if gpu:
        return gpu
    return None


def first_sysfs_gpu() -> str | None:
    pci_root = Path("/sys/bus/pci/devices")
    vendor_names = {
        "0x10de": "NVIDIA",
        "0x1002": "AMD",
        "0x1022": "AMD",
        "0x8086": "Intel",
        "0x1013": "Cirrus Logic",
    }
    try:
        devices = sorted(pci_root.iterdir())
    except OSError:
        return None

    for device in devices:
        pci_class = (read_text(device / "class") or "").strip().lower()
        if not pci_class.startswith("0x03"):
            continue
        vendor_id = (read_text(device / "vendor") or "").strip().lower()
        device_id = (read_text(device / "device") or "").strip().lower()
        vendor = vendor_names.get(vendor_id, vendor_id or "unknown")
        if device_id:
            return f"{vendor} GPU {device_id} ({device.name})"
        return f"{vendor} GPU ({device.name})"
    return None


def disk_summary(path: str = "/") -> str | None:
    try:
        usage = shutil.disk_usage(path)
    except OSError:
        return None
    used = usage.total - usage.free
    percent = round((used / usage.total) * 100) if usage.total else 0
    fs_type = root_filesystem_type()
    suffix = f" - {fs_type}" if fs_type else ""
    return f"{format_bytes(used)} / {format_bytes(usage.total)} ({percent}%){suffix}"


def root_filesystem_type() -> str | None:
    content = read_text(Path("/proc/mounts"))
    if content is None:
        return None
    for line in content.splitlines():
        parts = line.split()
        if len(parts) >= 3 and parts[1] == "/":
            return parts[2]
    return None


def default_interface(path: Path = DEFAULT_ROUTE_PATH) -> str | None:
    content = read_text(path)
    if content is None:
        return None
    for line in content.splitlines()[1:]:
        parts = line.split()
        if len(parts) >= 2 and parts[1] == "00000000":
            return parts[0]
    return None


def interface_ip(interface: str) -> str | None:
    try:
        import fcntl

        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            request = struct.pack("256s", interface[:15].encode("utf-8"))
            response = fcntl.ioctl(sock.fileno(), 0x8915, request)
            return socket.inet_ntoa(response[20:24])
    except OSError:
        return None


def local_ip_summary() -> str | None:
    interface = default_interface()
    if interface:
        address = interface_ip(interface)
        if address:
            return f"{address} ({interface})"

    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.connect(("1.1.1.1", 80))
            return sock.getsockname()[0]
    except OSError:
        return None


def locale_summary() -> str | None:
    value = os.environ.get("LC_ALL") or os.environ.get("LANG")
    if value:
        return value
    current = locale.setlocale(locale.LC_CTYPE)
    return current or None


def selinux_summary() -> str | None:
    enforce = read_text(Path("/sys/fs/selinux/enforce"))
    if enforce is None:
        return None
    return "Enforcing" if enforce.strip() == "1" else "Permissive"


def fips_summary() -> str | None:
    enabled = read_text(Path("/proc/sys/crypto/fips_enabled"))
    if enabled is None:
        return None
    return "enabled" if enabled.strip() == "1" else "disabled"


def python_summary() -> str:
    mode = "venv" if sys.prefix != sys.base_prefix else "system"
    return f"{platform.python_version()} ({mode})"


def collect_system_summary(identity: DistroIdentity | None = None) -> SystemSummary:
    detected = identity or detect_distro()
    meminfo = parse_meminfo(read_text(MEMINFO_PATH) or "")
    title = f"{getpass.getuser()}@{socket.gethostname()}"

    facts: list[SystemFact] = []
    if detected is not None:
        facts.append(SystemFact("OS", f"{detected.pretty_name} {platform.machine()}".strip()))

    candidates = (
        ("Host", host_summary()),
        ("Kernel", f"{platform.system()} {platform.release()} {platform.machine()}".strip()),
        ("Uptime", uptime_summary()),
        ("Packages", package_summary()),
        ("Python", python_summary()),
        ("Shell", shell_summary()),
        ("Terminal", terminal_summary()),
        ("CPU", cpu_summary()),
        ("GPU", gpu_summary()),
        ("Memory", memory_summary(meminfo)),
        ("Swap", swap_summary(meminfo)),
        ("Disk (/)", disk_summary("/")),
        ("Local IP", local_ip_summary()),
        ("Locale", locale_summary()),
        ("SELinux", selinux_summary()),
        ("FIPS", fips_summary()),
    )
    for label, value in candidates:
        if value:
            facts.append(SystemFact(label, value))
    return SystemSummary(title=title, facts=tuple(facts))
