"""Klient Bazy Konkurencyjnosci: pobranie i normalizacja ogloszen.

Kolejnosc prob:
1. Live REST: GET /api/announcements/search (jesli dostepny + opcjonalny BK_TOKEN).
2. Fallback: lokalny plik PRZYKLAD (samples/sample_announcements.json),
   dzieki czemu narzedzie dziala end-to-end nawet gdy API wymaga logowania.

Uwaga o dostepie live: endpoint /api/announcements/search bywa chroniony
anonimowym tokenem Bearer generowanym przez keycloak w przegladarce
(realm publiczny nie wydaje service-account tokenu przez client_credentials).
Jesli masz wazny token, ustaw zmienna srodowiskowa BK_TOKEN, a klient go uzyje.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field, asdict
from typing import Any

import requests

from . import config


@dataclass
class Announcement:
    id: str
    number: str
    title: str
    advertiser: str
    category: str
    subcategory: str
    budget_pln: float | None
    deadline: str
    publication_date: str
    place: str
    url: str
    source: str  # "live" albo "PRZYKLAD"
    it_phrases: list[str] = field(default_factory=list)
    requires_references: bool = False
    reference_phrases: list[str] = field(default_factory=list)

    def as_row(self) -> dict[str, Any]:
        d = asdict(self)
        d["it_phrases"] = ", ".join(self.it_phrases)
        d["reference_phrases"] = ", ".join(self.reference_phrases)
        return d


def _headers() -> dict[str, str]:
    h = {
        "User-Agent": config.USER_AGENT,
        "Accept": "application/json",
        "Content-type": "application/json",
        "Referer": f"{config.BASE_URL}/ogloszenia",
    }
    if config.BK_TOKEN:
        h["Authorization"] = f"Bearer {config.BK_TOKEN}"
    return h


def _to_float(val: Any) -> float | None:
    if val is None:
        return None
    if isinstance(val, (int, float)):
        return float(val)
    s = str(val).replace(" ", "").replace(" ", "").replace(",", ".")
    s = "".join(c for c in s if c.isdigit() or c == ".")
    try:
        return float(s) if s else None
    except ValueError:
        return None


def _first(d: dict, *keys, default=""):
    for k in keys:
        v = d.get(k)
        if v not in (None, "", []):
            return v
    return default


def _extract_advertiser(raw: dict) -> str:
    adv = raw.get("advertiser") or raw.get("zamawiajacy")
    if isinstance(adv, dict):
        return _first(adv, "name", "nazwa", "title", default="")
    if isinstance(adv, str):
        return adv
    return _first(raw, "advertiserName", "advertiser_name", default="")


def _extract_budget(raw: dict) -> float | None:
    for k in ("budget", "budzet", "estimatedValue", "value", "threshold", "prog"):
        v = raw.get(k)
        if isinstance(v, dict):
            v = _first(v, "amount", "value", "kwota", default=None)
        f = _to_float(v)
        if f is not None:
            return f
    return None


def normalize(raw: dict) -> Announcement:
    """Mapuje surowy rekord API (elastycznie) na Announcement."""
    aid = str(_first(raw, "id", "announcementId", "ogloszenieId", default=""))
    number = str(_first(raw, "calyNumer", "announcementNumber", "number", default=""))
    title = _first(raw, "title", "announcementTitle", "nazwa", "name", default="")
    category = _first(raw, "category", "categoryName", "kategoria", default="")
    if isinstance(category, dict):
        category = _first(category, "name", "nazwa", default="")
    subcategory = _first(
        raw, "subcategory", "subcategoryName", "podkategoria", default=""
    )
    if isinstance(subcategory, dict):
        subcategory = _first(subcategory, "name", "nazwa", default="")
    deadline = _first(
        raw,
        "terminOfert",
        "submissionDeadline",
        "submission_deadline",
        "deadline",
        "offerSubmissionDeadline",
        default="",
    )
    pub = _first(
        raw,
        "publicationDate",
        "publication_date",
        "announcementPublicationDate",
        "publishDate",
        default="",
    )
    place = _first(
        raw,
        "fulfillmentPlace",
        "fulfillment_place",
        "miejsceRealizacji",
        "place",
        default="",
    )
    if isinstance(place, list):
        place = ", ".join(str(p) for p in place)
    url = f"{config.BASE_URL}/ogloszenia/{aid}" if aid else config.BASE_URL

    return Announcement(
        id=aid,
        number=number,
        title=title,
        advertiser=_extract_advertiser(raw),
        category=str(category),
        subcategory=str(subcategory),
        budget_pln=_extract_budget(raw),
        deadline=str(deadline),
        publication_date=str(pub),
        place=str(place),
        url=url,
        source="live",
    )


def _unwrap_list(payload: Any) -> list[dict]:
    """Wyciaga liste rekordow z roznych ksztaltow odpowiedzi API."""
    if isinstance(payload, list):
        return [x for x in payload if isinstance(x, dict)]
    if isinstance(payload, dict):
        for key in (
            "advertisements",
            "data",
            "content",
            "items",
            "results",
            "announcements",
        ):
            v = payload.get(key)
            if isinstance(v, list):
                return [x for x in v if isinstance(x, dict)]
        # czasem {data:{content:[...]}}
        for key in ("data", "result"):
            inner = payload.get(key)
            if isinstance(inner, dict):
                got = _unwrap_list(inner)
                if got:
                    return got
    return []


def fetch_live(
    pages: int = 1, limit: int = 50, sort: str = "announcementPublicationDate_desc"
) -> list[dict]:
    """Pobiera surowe rekordy z live API. Rzuca wyjatek gdy niedostepne."""
    session = requests.Session()
    out: list[dict] = []
    for page in range(1, pages + 1):
        params = {
            "page": page,
            "limit": limit,
            "status[0]": "PUBLISHED",
            "category": "Usługa",
            "subcategory": "Usługi IT",
        }
        resp = session.get(
            config.BASE_URL + config.SEARCH_PATH,
            params=params,
            headers=_headers(),
            timeout=config.REQUEST_TIMEOUT_S,
        )
        resp.raise_for_status()
        rows = _unwrap_list(resp.json())
        if not rows:
            break
        out.extend(rows)
        time.sleep(config.REQUEST_DELAY_S)
    return out


def load_sample() -> list[dict]:
    """Wczytuje przykladowe dane PRZYKLAD z pliku."""
    with open(config.SAMPLE_JSON, encoding="utf-8") as f:
        payload = json.load(f)
    return _unwrap_list(payload)


def get_announcements(
    pages: int = 1,
    limit: int = 50,
    use_sample: bool = False,
) -> tuple[list[Announcement], str]:
    """Zwraca (lista ogloszen, tryb) gdzie tryb = 'live' lub 'PRZYKLAD'."""
    mode = "PRZYKLAD"
    raw_rows: list[dict] = []
    if not use_sample:
        try:
            raw_rows = fetch_live(pages=pages, limit=limit)
            if raw_rows:
                mode = "live"
        except Exception:  # noqa: BLE001 - fallback jest celowy
            raw_rows = []
    if not raw_rows:
        raw_rows = load_sample()
        mode = "PRZYKLAD"

    anns = []
    for raw in raw_rows:
        ann = normalize(raw)
        ann.source = mode
        if mode == "live" and not ann.category:
            # kategoria filtrowana po stronie API (Usluga / Uslugi IT)
            ann.category = "Usługa"
            ann.subcategory = "Usługi IT"
        anns.append(ann)
    return anns, mode
