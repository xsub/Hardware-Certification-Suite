"""Linux distribution identity and runner logo helpers."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import shutil
import subprocess


OS_RELEASE_PATH = Path("/etc/os-release")

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
