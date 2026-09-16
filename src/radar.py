"""CLI radaru: pobierz -> filtruj IT -> dedup -> digest (MD/CSV/PDF) -> mail."""

from __future__ import annotations

import argparse
import os
import smtplib
import sys
from datetime import date
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

from . import config, filters, store
from .bk_client import Announcement, get_announcements
from .digest import build_markdown, write_csv, write_pdf


def enrich(anns: list[Announcement]) -> list[Announcement]:
    """Uzupelnia flagi filtrow na kazdym ogloszeniu."""
    for a in anns:
        blob = " ".join([a.title, a.category, a.subcategory, a.place])
        a.it_phrases = filters.matched_it_phrases(blob)
        a.requires_references = filters.requires_references(blob)
        a.reference_phrases = filters.matched_reference_phrases(blob)
    return anns


def select_it(anns: list[Announcement], max_budget=None) -> list[Announcement]:
    out = []
    for a in anns:
        blob = " ".join([a.title, a.category, a.subcategory])
        if not filters.is_it_related(blob, a.category):
            continue
        if not filters.within_budget(a.budget_pln, max_budget):
            continue
        out.append(a)
    return out


def send_email(subject: str, md_body: str, csv_path: Path) -> bool:
    """Wysyla digest mailem. Konfiguracja WYLACZNIE przez env (bez sekretow w kodzie)."""
    host = os.environ.get("SMTP_HOST")
    user = os.environ.get("SMTP_USER")
    pwd = os.environ.get("SMTP_PASS")
    to = os.environ.get("DIGEST_TO")
    if not all([host, user, pwd, to]):
        print("[mail] pominieto - brak SMTP_HOST/SMTP_USER/SMTP_PASS/DIGEST_TO w env")
        return False
    port = int(os.environ.get("SMTP_PORT", "587"))
    msg = MIMEMultipart()
    msg["From"] = user
    msg["To"] = to
    msg["Subject"] = subject
    msg.attach(MIMEText(md_body, "plain", "utf-8"))
    if csv_path.exists():
        att = MIMEText(csv_path.read_text(encoding="utf-8"), "csv", "utf-8")
        att.add_header("Content-Disposition", "attachment", filename=csv_path.name)
        msg.attach(att)
    with smtplib.SMTP(host, port, timeout=30) as s:
        s.starttls()
        s.login(user, pwd)
        s.send_message(msg)
    print(f"[mail] wyslano do {to}")
    return True


def run(args: argparse.Namespace) -> int:
    config.OUT_DIR.mkdir(exist_ok=True)
    anns, mode = get_announcements(
        pages=args.pages, limit=args.limit, use_sample=args.sample
    )
    print(f"[fetch] pobrano {len(anns)} ogloszen (tryb={mode})")

    it_anns = select_it(anns, max_budget=args.max_budget)
    enrich(it_anns)
    print(f"[filter] trafien IT: {len(it_anns)}")

    conn = store.connect(Path(args.db))
    if args.no_dedup:
        new = it_anns
    else:
        new = store.filter_new(conn, it_anns)
    print(f"[dedup] nowych: {len(new)} (w bazie lacznie: {store.count(conn)})")

    day = date.today().isoformat()
    md = build_markdown(new, mode, day)
    md_path = config.OUT_DIR / f"{args.prefix}_{day}.md"
    csv_path = config.OUT_DIR / f"{args.prefix}_{day}.csv"
    md_path.write_text(md, encoding="utf-8")
    write_csv(new, csv_path)
    print(f"[digest] {md_path}")
    print(f"[digest] {csv_path}")

    if args.pdf:
        pdf_path = config.OUT_DIR / f"{args.prefix}_{day}.pdf"
        if write_pdf(md, pdf_path):
            print(f"[digest] {pdf_path}")
        else:
            print("[digest] PDF pominiety (brak google-chrome-stable)")

    if args.email and new:
        send_email(f"Radar przetargi IT {day}: {len(new)} nowych", md, csv_path)

    if not args.no_dedup:
        store.mark_seen(conn, new)
    conn.close()
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="radar",
        description="Radar zapytan ofertowych IT z Bazy Konkurencyjnosci (FluxLab #51)",
    )
    p.add_argument("--pages", type=int, default=2, help="ile stron API pobrac (live)")
    p.add_argument("--limit", type=int, default=50, help="rekordow na strone")
    p.add_argument(
        "--sample", action="store_true", help="wymus dane PRZYKLAD (offline)"
    )
    p.add_argument("--db", default=str(config.DEFAULT_DB), help="sciezka SQLite dedup")
    p.add_argument(
        "--no-dedup", action="store_true", help="nie filtruj po bazie, nie zapisuj"
    )
    p.add_argument(
        "--max-budget",
        type=float,
        default=config.DEFAULT_MAX_BUDGET_PLN,
        help="prog budzetu PLN (odsiej wieksze)",
    )
    p.add_argument(
        "--pdf", action="store_true", help="generuj PDF (google-chrome-stable)"
    )
    p.add_argument(
        "--email", action="store_true", help="wyslij digest mailem (env SMTP_*)"
    )
    p.add_argument("--prefix", default="digest", help="prefiks nazw plikow w out/")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return run(args)


if __name__ == "__main__":
    sys.exit(main())
