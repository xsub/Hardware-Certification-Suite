"""Optional PDF evidence report for the AlmaLinux Hardware Certification Suite.

Colors, fonts, and logo usage follow the AlmaLinux OS Brand Book palette
(Science Blue #0069DA, Atlantis #86DA2F, Candlelight #FFCB12, Black Pearl
#082336, Sunburnt Cyclops #FF4649; Montserrat). The PDF is a best-effort
rendering of the JSON/text evidence: if reportlab is not installed the runner
still writes the text and JSON reports.
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from xml.sax.saxutils import escape as xml_escape

try:
    from reportlab.lib.colors import HexColor, white
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.lib.utils import ImageReader
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    REPORTLAB_AVAILABLE = True
except Exception:  # pragma: no cover - exercised only without reportlab
    REPORTLAB_AVAILABLE = False
    # The module-level _STATUS_BADGE table references `white`, so it must be
    # defined even without reportlab. The drawing code that consumes it only
    # runs when reportlab is available, so this fallback is never rendered.
    white = "#FFFFFF"


ASSETS_DIR = Path(__file__).parent / "assets"
FONTS_DIR = ASSETS_DIR / "fonts"
BRANDING_DIR = ASSETS_DIR / "branding"

# AlmaLinux OS Brand Book palette.
SCIENCE_BLUE = "#0069DA"
SCIENCE_BLUE_DARK = "#004BBC"
ATLANTIS = "#86DA2F"
ATLANTIS_DARK = "#68BC11"
CANDLELIGHT = "#FFCB12"
CANDLELIGHT_DARK = "#E1AD00"
BLACK_PEARL = "#082336"
SOFT_PEACH = "#FAF5F5"
SUNBURNT = "#FF4649"
SLATE = "#5B6B78"

_FONT_FILES = {
    "Montserrat-Light": "Montserrat-Light.ttf",
    "Montserrat": "Montserrat-Medium.ttf",
    "Montserrat-SemiBold": "Montserrat-SemiBold.ttf",
    "Montserrat-Bold": "Montserrat-Bold.ttf",
}


def _register_fonts() -> dict[str, str]:
    """Register Montserrat; fall back to Helvetica when the TTFs are absent."""
    fallback = {
        "light": "Helvetica",
        "body": "Helvetica",
        "semi": "Helvetica-Bold",
        "bold": "Helvetica-Bold",
    }
    if not all((FONTS_DIR / name).exists() for name in _FONT_FILES.values()):
        return fallback
    try:
        for font_name, file_name in _FONT_FILES.items():
            pdfmetrics.registerFont(TTFont(font_name, str(FONTS_DIR / file_name)))
    except Exception:  # pragma: no cover - defensive
        return fallback
    return {
        "light": "Montserrat-Light",
        "body": "Montserrat",
        "semi": "Montserrat-SemiBold",
        "bold": "Montserrat-Bold",
    }


_STATUS_BADGE = {
    "passed": ("PASSED", ATLANTIS_DARK, white),
    "passed_with_warnings": ("PASSED WITH WARNINGS", CANDLELIGHT, BLACK_PEARL),
    "failed": ("FAILED", SUNBURNT, white),
    "interrupted": ("INTERRUPTED — INCOMPLETE", CANDLELIGHT_DARK, white),
    "dry_run": ("DRY RUN — NO TESTS EXECUTED", SLATE, white),
}

_STATUS_TEXT_COLOR = {
    "passed": ATLANTIS_DARK,
    "failed": SUNBURNT,
    "unsupported": CANDLELIGHT_DARK,
    "skipped": SLATE,
    "not_run": SLATE,
}


def _human_duration(seconds: float) -> str:
    seconds = int(seconds)
    if seconds < 60:
        return f"{seconds}s"
    hours, remainder = divmod(seconds, 3600)
    minutes, secs = divmod(remainder, 60)
    if hours:
        return f"{hours}h {minutes}m"
    return f"{minutes}m {secs}s"


def _draw_footer(c, doc, fonts: dict[str, str], run_id: str, version: str) -> None:
    width = doc.pagesize[0]
    c.setStrokeColor(HexColor(SCIENCE_BLUE))
    c.setLineWidth(0.6)
    c.line(18 * mm, 14 * mm, width - 18 * mm, 14 * mm)
    c.setFillColor(HexColor(SLATE))
    c.setFont(fonts["light"], 7.5)
    c.drawString(18 * mm, 9 * mm, f"AlmaLinux Hardware Certification Suite {version}  ·  Run {run_id}")
    c.drawRightString(width - 18 * mm, 9 * mm, f"Page {doc.page}")


def write_pdf_report(
    output_path: Path,
    *,
    run_id: str,
    profile: str,
    preset_name: str | None,
    repeat: int,
    status: str,
    started_at: str,
    finished_at: str,
    generated_at: str,
    system_title: str,
    system_facts: Sequence[tuple[str, str]],
    results: Sequence[dict[str, object]],
    counts: dict[str, int],
    total_seconds: float,
    version: str,
    manual_tests: Sequence[tuple[str, str, str]] = (),
    inventory: str | None = None,
    required_unexercised: Sequence[tuple[str, str]] = (),
    sut_title: str | None = None,
    sut_facts: Sequence[tuple[str, str]] = (),
) -> bool:
    """Write the optional PDF evidence report. Returns False if reportlab is unavailable."""
    if not REPORTLAB_AVAILABLE:
        return False

    fonts = _register_fonts()
    facts = {label: value for label, value in system_facts}
    sut_facts_dict = {label: value for label, value in sut_facts}

    def on_cover(c, doc) -> None:
        width, height = doc.pagesize
        band_h = 44 * mm
        # Science Blue masthead with the negative (white) AlmaLinux logo.
        c.setFillColor(HexColor(SCIENCE_BLUE))
        c.rect(0, height - band_h, width, band_h, fill=1, stroke=0)
        c.setFillColor(HexColor(ATLANTIS))
        c.rect(0, height - band_h - 2.2 * mm, width, 2.2 * mm, fill=1, stroke=0)
        logo = BRANDING_DIR / "almalinux-logo-white.png"
        if logo.exists():
            img = ImageReader(str(logo))
            iw, ih = img.getSize()
            lh = 13 * mm
            lw = lh * iw / ih
            c.drawImage(img, 18 * mm, height - band_h / 2 - lh / 2, width=lw, height=lh, mask="auto")
        c.setFillColor(white)
        c.setFont(fonts["light"], 11)
        c.drawRightString(width - 18 * mm, height - band_h / 2 - 4, "HARDWARE CERTIFICATION")

        # Title.
        top = height - band_h - 20 * mm
        c.setFillColor(HexColor(BLACK_PEARL))
        c.setFont(fonts["semi"], 30)
        c.drawString(18 * mm, top, "Hardware Certification")
        c.drawString(18 * mm, top - 13 * mm, "Report")

        # Status badge.
        label, bg, fg = _STATUS_BADGE.get(status, (status.upper(), SLATE, white))
        c.setFont(fonts["semi"], 12)
        text_w = c.stringWidth(label, fonts["semi"], 12)
        badge_w = text_w + 14 * mm
        badge_h = 10 * mm
        badge_y = top - 30 * mm
        c.setFillColor(HexColor(bg))
        c.roundRect(18 * mm, badge_y, badge_w, badge_h, 2.5 * mm, fill=1, stroke=0)
        c.setFillColor(HexColor(fg) if isinstance(fg, str) else fg)
        c.drawString(18 * mm + 7 * mm, badge_y + 3.1 * mm, label)

        # One-line results summary next to the badge.
        total = sum(counts.get(k, 0) for k in ("passed", "failed", "unsupported", "skipped"))
        summary = (
            f"{counts.get('passed', 0)} passed · {counts.get('failed', 0)} failed · "
            f"{counts.get('unsupported', 0)} unsupported   ·   {total} tests · {_human_duration(total_seconds)}"
        )
        if counts.get("not_run"):
            summary += f"   ·   {counts['not_run']} not run"
        c.setFillColor(HexColor(SLATE))
        c.setFont(fonts["light"], 9.5)
        c.drawString(18 * mm + badge_w + 6 * mm, badge_y + 3.3 * mm, summary)

        # Meta block. The facts describe the controller (runner host), which is
        # the SUT only for local runs — label them truthfully for SIG review.
        meta = [
            ("System under test", sut_title or "SUT identity not collected"),
            ("SUT source", sut_facts_dict.get("Source", "—")),
            ("Controller system", system_title),
            ("Controller OS", facts.get("OS", "—")),
            ("Inventory", inventory or "—"),
            ("Run ID", run_id),
            ("Profile", profile),
            ("Preset", preset_name or "—"),
            ("Passes", str(repeat)),
            ("Started", started_at),
            ("Finished", finished_at),
        ]
        my = badge_y - 16 * mm
        for key, value in meta:
            c.setFillColor(HexColor(SLATE))
            c.setFont(fonts["light"], 9)
            c.drawString(18 * mm, my, key.upper())
            c.setFillColor(HexColor(BLACK_PEARL))
            c.setFont(fonts["body"], 11)
            c.drawString(62 * mm, my, str(value))
            my -= 8.2 * mm

        # Powered-by AlmaLinux lockup + SIG note in the footer area.
        powered = BRANDING_DIR / "powered-by-almalinux-dark.png"
        if powered.exists():
            img = ImageReader(str(powered))
            iw, ih = img.getSize()
            ph = 11 * mm
            pw = ph * iw / ih
            c.drawImage(img, 18 * mm, 23 * mm, width=pw, height=ph, mask="auto")
        c.setStrokeColor(HexColor("#E3E8EC"))
        c.setLineWidth(0.5)
        c.line(18 * mm, 18 * mm, width - 18 * mm, 18 * mm)
        c.setFillColor(HexColor(SLATE))
        c.setFont(fonts["light"], 8.5)
        c.drawString(
            18 * mm,
            12.5 * mm,
            "Evidence for AlmaLinux Certification SIG review — not a self-issued certification.",
        )
        c.setFont(fonts["light"], 7.5)
        c.drawString(18 * mm, 8 * mm, f"Generated {generated_at}  ·  AlmaLinux Hardware Certification Suite {version}")

    def on_later(c, doc) -> None:
        width, height = doc.pagesize
        icon = BRANDING_DIR / "almalinux-icon.png"
        if icon.exists():
            img = ImageReader(str(icon))
            iw, ih = img.getSize()
            ih2 = 7 * mm
            iw2 = ih2 * iw / ih
            c.drawImage(img, 18 * mm, height - 16 * mm, width=iw2, height=ih2, mask="auto")
            text_x = 18 * mm + iw2 + 3 * mm
        else:
            text_x = 18 * mm
        c.setFillColor(HexColor(BLACK_PEARL))
        c.setFont(fonts["semi"], 9)
        c.drawString(text_x, height - 13.5 * mm, "Hardware Certification Evidence")
        c.setFillColor(HexColor(SLATE))
        c.setFont(fonts["light"], 8)
        c.drawRightString(width - 18 * mm, height - 13.5 * mm, run_id)
        c.setStrokeColor(HexColor(SCIENCE_BLUE))
        c.setLineWidth(0.6)
        c.line(18 * mm, height - 18 * mm, width - 18 * mm, height - 18 * mm)
        _draw_footer(c, doc, fonts, run_id, version)

    def cover_page(c, doc) -> None:
        on_cover(c, doc)  # the cover draws its own footer block

    styles = {
        "h2": ParagraphStyle(
            "h2", fontName=fonts["semi"], fontSize=14, textColor=HexColor(BLACK_PEARL),
            spaceBefore=2, spaceAfter=7,
        ),
        "body": ParagraphStyle(
            "body", fontName=fonts["body"], fontSize=9, textColor=HexColor(BLACK_PEARL), leading=13,
        ),
        "reason": ParagraphStyle(
            "reason", fontName=fonts["light"], fontSize=8.5, textColor=HexColor(SLATE), leading=12,
        ),
    }

    story: list[object] = []
    from reportlab.platypus import PageBreak

    story.append(PageBreak())  # the cover is drawn on page 1; detail starts on page 2

    story.append(Paragraph("System under test", styles["h2"]))
    sut_rows = [[label, str(value)] for label, value in sut_facts]
    if sut_rows:
        sut_table = Table(sut_rows, colWidths=[42 * mm, 132 * mm], hAlign="LEFT")
        sut_table.setStyle(
            TableStyle(
                [
                    ("FONTNAME", (0, 0), (0, -1), fonts["semi"]),
                    ("FONTNAME", (1, 0), (1, -1), fonts["body"]),
                    ("FONTSIZE", (0, 0), (-1, -1), 9),
                    ("TEXTCOLOR", (0, 0), (0, -1), HexColor(SCIENCE_BLUE_DARK)),
                    ("TEXTCOLOR", (1, 0), (1, -1), HexColor(BLACK_PEARL)),
                    ("ROWBACKGROUNDS", (0, 0), (-1, -1), [white, HexColor(SOFT_PEACH)]),
                    ("LINEBELOW", (0, 0), (-1, -1), 0.3, HexColor("#E3E8EC")),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                    ("LEFTPADDING", (0, 0), (-1, -1), 7),
                ]
            )
        )
        story.append(sut_table)
    story.append(Spacer(1, 9 * mm))

    story.append(Paragraph("Controller system", styles["h2"]))
    id_rows = [[label, str(value)] for label, value in system_facts]
    if id_rows:
        id_table = Table(id_rows, colWidths=[42 * mm, 132 * mm], hAlign="LEFT")
        id_table.setStyle(
            TableStyle(
                [
                    ("FONTNAME", (0, 0), (0, -1), fonts["semi"]),
                    ("FONTNAME", (1, 0), (1, -1), fonts["body"]),
                    ("FONTSIZE", (0, 0), (-1, -1), 9),
                    ("TEXTCOLOR", (0, 0), (0, -1), HexColor(SCIENCE_BLUE_DARK)),
                    ("TEXTCOLOR", (1, 0), (1, -1), HexColor(BLACK_PEARL)),
                    ("ROWBACKGROUNDS", (0, 0), (-1, -1), [white, HexColor(SOFT_PEACH)]),
                    ("LINEBELOW", (0, 0), (-1, -1), 0.3, HexColor("#E3E8EC")),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                    ("LEFTPADDING", (0, 0), (-1, -1), 7),
                ]
            )
        )
        story.append(id_table)
    story.append(Spacer(1, 9 * mm))

    story.append(Paragraph("Certification results", styles["h2"]))
    header = ["#", "Test", "Scope", "Status", "Duration", "rc"]
    table_rows: list[list[str]] = [header]
    status_styles: list[tuple] = []
    for index, result in enumerate(results, start=1):
        rc = result.get("return_code")
        table_rows.append(
            [
                str(result.get("step", index)).zfill(3),
                str(result.get("display_name", result.get("test_id", ""))),
                str(result.get("scope", "profile")),
                str(result.get("status", "")),
                f"{float(result.get('duration_seconds', 0.0)):.1f}s",
                "-" if rc is None else str(rc),
            ]
        )
        color = _STATUS_TEXT_COLOR.get(str(result.get("status", "")), BLACK_PEARL)
        status_styles.append(("TEXTCOLOR", (3, index), (3, index), HexColor(color)))
        status_styles.append(("FONTNAME", (3, index), (3, index), fonts["semi"]))

    results_table = Table(
        table_rows,
        colWidths=[12 * mm, 64 * mm, 24 * mm, 38 * mm, 20 * mm, 16 * mm],
        repeatRows=1,
        hAlign="LEFT",
    )
    results_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), HexColor(SCIENCE_BLUE)),
                ("TEXTCOLOR", (0, 0), (-1, 0), white),
                ("FONTNAME", (0, 0), (-1, 0), fonts["semi"]),
                ("FONTNAME", (0, 1), (-1, -1), fonts["body"]),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [white, HexColor(SOFT_PEACH)]),
                ("ALIGN", (4, 0), (5, -1), "RIGHT"),
                ("ALIGN", (0, 0), (0, -1), "RIGHT"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ("LEFTPADDING", (0, 0), (-1, -1), 7),
                ("LINEBELOW", (0, 0), (-1, 0), 0.4, HexColor(SCIENCE_BLUE_DARK)),
            ]
            + status_styles
        )
    )
    story.append(results_table)
    story.append(Spacer(1, 5 * mm))

    recap = (
        f"<b>{counts.get('passed', 0)} passed</b>, {counts.get('failed', 0)} failed, "
        f"{counts.get('unsupported', 0)} unsupported, {counts.get('skipped', 0)} skipped"
    )
    if counts.get("not_run"):
        recap += f", {counts['not_run']} not run"
    recap += f" — total {total_seconds:.1f}s"
    story.append(Paragraph(recap, styles["body"]))

    # xml_escape(): reasons are arbitrary role/runner text; reportlab would
    # reject stray <...> sequences and the whole report would be skipped.
    notable = [
        r
        for r in results
        if str(r.get("status")) in {"failed", "unsupported", "not_run"} and r.get("status_reason")
    ]
    if notable:
        story.append(Spacer(1, 6 * mm))
        story.append(Paragraph("Notes", styles["h2"]))
        for result in notable:
            story.append(
                Paragraph(
                    f"<b>{xml_escape(str(result.get('display_name', result.get('test_id', ''))))}</b> "
                    f"({xml_escape(str(result.get('status')))}): {xml_escape(str(result.get('status_reason')))}",
                    styles["reason"],
                )
            )

    if required_unexercised:
        story.append(Spacer(1, 6 * mm))
        story.append(Paragraph("Required tests not exercised in this run", styles["h2"]))
        story.append(
            Paragraph(
                "The selected preset marks these tests required, but this run "
                "produced no pass/fail verdict for them. This report alone is "
                "not complete certification evidence.",
                styles["reason"],
            )
        )
        for test_id, reason in required_unexercised:
            story.append(
                Paragraph(
                    f"<b>{xml_escape(test_id)}</b>: {xml_escape(reason)}",
                    styles["reason"],
                )
            )

    if manual_tests:
        story.append(Spacer(1, 6 * mm))
        story.append(Paragraph("Manual tests — not executed by the runner", styles["h2"]))
        story.append(
            Paragraph(
                "The selected preset also lists the interactive tests below "
                "(run via interactive.yml); this report does not cover them.",
                styles["reason"],
            )
        )
        for test_id, scope, reason in manual_tests:
            story.append(
                Paragraph(
                    f"<b>{xml_escape(test_id)}</b> ({xml_escape(scope)}): {xml_escape(reason)}",
                    styles["reason"],
                )
            )

    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=A4,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=24 * mm,
        bottomMargin=22 * mm,
        title=f"AlmaLinux Hardware Certification Evidence — {run_id}",
        author="AlmaLinux Hardware Certification Suite",
    )
    doc.build(story, onFirstPage=cover_page, onLaterPages=on_later)
    return True
