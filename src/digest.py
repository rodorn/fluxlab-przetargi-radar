"""Generowanie digestu: Markdown + CSV (+ opcjonalnie PDF przez Chrome)."""

from __future__ import annotations

import csv
import html
import shutil
import subprocess
import tempfile
from datetime import date
from pathlib import Path

from .bk_client import Announcement

CSV_COLUMNS = [
    "number",
    "title",
    "advertiser",
    "category",
    "budget_pln",
    "deadline",
    "requires_references",
    "it_phrases",
    "url",
    "source",
]


def _budget_str(ann: Announcement) -> str:
    if ann.budget_pln is None:
        return "brak danych"
    return f"{ann.budget_pln:,.0f} PLN".replace(",", " ")


def _ref_flag(ann: Announcement) -> str:
    return "TAK (wymaga referencji/doswiadczenia)" if ann.requires_references else "nie"


def build_markdown(anns: list[Announcement], mode: str, day: str | None = None) -> str:
    day = day or date.today().isoformat()
    lines: list[str] = []
    lines.append(f"# Radar zapytan ofertowych IT - Baza Konkurencyjnosci ({day})")
    lines.append("")
    if mode != "live":
        lines.append(
            "> UWAGA: dane z trybu PRZYKLAD (fallback). Live API wymaga tokena "
            "(patrz README). Struktura i filtry sa identyczne jak dla danych live."
        )
        lines.append("")

    latwe = [a for a in anns if not a.requires_references]
    trudne = [a for a in anns if a.requires_references]

    lines.append(
        f"Nowych trafien IT: {len(anns)} "
        f"(bez wymogu referencji: {len(latwe)}, z wymogiem: {len(trudne)})"
    )
    lines.append("")

    def block(title: str, group: list[Announcement]) -> None:
        lines.append(f"## {title} ({len(group)})")
        lines.append("")
        if not group:
            lines.append("_brak_")
            lines.append("")
            return
        for a in group:
            lines.append(f"### {a.title or '(bez tytulu)'}")
            lines.append("")
            lines.append(f"- Numer: {a.number or 'brak'}")
            lines.append(f"- Zamawiajacy: {a.advertiser or 'brak danych'}")
            lines.append(
                f"- Kategoria: {a.category or 'brak'} / {a.subcategory or ''}".rstrip(
                    " /"
                )
            )
            lines.append(f"- Budzet/prog: {_budget_str(a)}")
            lines.append(f"- Termin skladania: {a.deadline or 'brak danych'}")
            lines.append(f"- Miejsce: {a.place or 'brak danych'}")
            lines.append(f"- Frazy IT: {', '.join(a.it_phrases) or 'kategoria'}")
            lines.append(f"- Wymog referencji: {_ref_flag(a)}")
            lines.append(f"- Link: {a.url}")
            lines.append("")

    block("Kandydaci dla swiezej JDG (bez wymogu referencji)", latwe)
    block("Wymagaja referencji/doswiadczenia (odsiane)", trudne)
    return "\n".join(lines)


def write_csv(anns: list[Announcement], path: Path) -> None:
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS, extrasaction="ignore")
        writer.writeheader()
        for a in anns:
            writer.writerow(a.as_row())


def _markdown_to_html(md_text: str, title: str) -> str:
    body = html.escape(md_text)
    return (
        "<!doctype html><html lang=pl><head><meta charset=utf-8>"
        f"<title>{html.escape(title)}</title>"
        "<style>body{font-family:sans-serif;margin:2rem;line-height:1.5}"
        "pre{white-space:pre-wrap;word-wrap:break-word}</style></head>"
        f"<body><pre>{body}</pre></body></html>"
    )


def write_pdf(md_text: str, path: Path) -> bool:
    """Renderuje PDF przez google-chrome-stable --headless. Zwraca True gdy sie udalo."""
    chrome = shutil.which("google-chrome-stable") or shutil.which("google-chrome")
    if not chrome:
        return False
    with tempfile.NamedTemporaryFile(
        "w", suffix=".html", delete=False, encoding="utf-8"
    ) as tmp:
        tmp.write(_markdown_to_html(md_text, "Radar przetargi IT"))
        tmp_path = tmp.name
    try:
        subprocess.run(
            [
                chrome,
                "--headless",
                "--no-sandbox",
                "--disable-gpu",
                f"--print-to-pdf={path}",
                "--no-pdf-header-footer",
                f"file://{tmp_path}",
            ],
            check=True,
            capture_output=True,
            timeout=60,
        )
        return path.exists()
    except (subprocess.SubprocessError, OSError):
        return False
    finally:
        Path(tmp_path).unlink(missing_ok=True)
