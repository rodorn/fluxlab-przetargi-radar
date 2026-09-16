"""Konfiguracja radaru zapytan ofertowych IT z Bazy Konkurencyjnosci."""

from __future__ import annotations

import os
from pathlib import Path

BASE_URL = "https://bazakonkurencyjnosci.funduszeeuropejskie.gov.pl"
SEARCH_PATH = "/api/announcements/search"
# Endpoint szczegolow (compact) - do wzbogacenia trafienia
COMPACT_PATH = "/api/announcements/{id}/compact"

USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64; rv:128.0) Gecko/20100101 Firefox/128.0"

# Opcjonalny anonimowy token Bearer (patrz README - sekcja o dostepie live).
# NIGDY nie zaszywac w kodzie. Czytany ze zmiennej srodowiskowej.
BK_TOKEN = os.environ.get("BK_TOKEN", "").strip()

# Throttling miedzy zapytaniami do API/HTML (sekundy).
REQUEST_DELAY_S = float(os.environ.get("BK_DELAY", "1.5"))
REQUEST_TIMEOUT_S = int(os.environ.get("BK_TIMEOUT", "25"))

# Frazy IT, ktorych szukamy w tytule/opisie (male litery, bez ogonkow tez lapane).
IT_PHRASES = [
    "strona internetowa",
    "strona www",
    "serwis internetowy",
    "system informatyczny",
    "system",
    "integracja",
    "automatyzacja",
    "aplikacja webowa",
    "aplikacja internetowa",
    "portal",
    "baza danych",
    "ga4",
    "analityka",
    "analityki internetowej",
    "oprogramowanie",
    "usluga it",
    "uslugi it",
    "wdrozenie systemu",
    "platforma",
    "api",
]

# Frazy sygnalizujace WYMOG referencji / doswiadczenia (odsiew dla swiezej JDG).
REFERENCE_REQUIREMENT_PHRASES = [
    "referencj",  # referencje, referencjami
    "wykaz uslug",
    "wykaz zrealizowanych",
    "nalezycie wykonan",
    "nalezycie wykonal",
    "doswiadczenie w realizacji",
    "co najmniej 3 projekt",
    "co najmniej trzy projekt",
    "min. 3 projekt",
    "poswiadcz",  # poswiadczenie nalezytego wykonania
    "portfolio",
    "zrealizowal co najmniej",
    "wykonal co najmniej",
    "wiedza i doswiadczenie",
    "potencjal techniczny",
    "warunki udzialu",
]

# Kategorie/CPV, ktore traktujemy jako IT (opcjonalny filtr twardy po stronie API).
# Baza Konkurencyjnosci uzywa slownika kategorii; ponizej nazwy fragmentow,
# ktore laczymy z polem category/subcategory zwroconym w wyniku.
IT_CATEGORY_HINTS = [
    "it",
    "informatyc",
    "oprogramowanie",
    "uslugi it",
    "teleinformatyc",
]

# Prog budzetowy (PLN). Trafienia powyzej progu oznaczamy jako "duzy przetarg".
# Domyslnie None = nie filtrujemy po progu, tylko raportujemy budzet gdy podany.
DEFAULT_MAX_BUDGET_PLN = None

# Sciezki projektu
ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "out"
SAMPLES_DIR = ROOT / "samples"
DEFAULT_DB = ROOT / "radar.sqlite3"
SAMPLE_JSON = SAMPLES_DIR / "sample_announcements.json"

# Dane JDG Pawla do stopki oferty (jawne, publiczne - NIP firmy).
JDG = {
    "nazwa": "FluxLab (JDG Pawel Iwanek)",
    "nip": "7831827728",
    "www": "https://fluxlab.pl",
    "portfolio": "https://github.com/rodorn",
}
