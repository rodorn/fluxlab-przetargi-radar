import os
import sqlite3
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src import filters, store  # noqa: E402
from src.bk_client import Announcement, normalize  # noqa: E402


def _ann(**kw):
    base = dict(
        id="1",
        number="N1",
        title="",
        advertiser="A",
        category="",
        subcategory="",
        budget_pln=None,
        deadline="",
        publication_date="",
        place="",
        url="u",
        source="test",
    )
    base.update(kw)
    return Announcement(**base)


# --- frazy IT ---
def test_matches_strona_internetowa():
    assert "strona internetowa" in filters.matched_it_phrases(
        "Wykonanie strony internetowej dla gminy"
    )


def test_matches_ignoring_pl_diacritics():
    # "wdrozenie" bez ogonka lapie "wdrożenie" i odwrotnie
    assert filters.matched_it_phrases("Wdrożenie systemu ERP")


def test_matches_ga4():
    assert "ga4" in filters.matched_it_phrases("Konfiguracja GA4 i raporty")


def test_non_it_not_matched():
    assert filters.matched_it_phrases("Dostawa mebli biurowych") == []


def test_is_it_related_by_category():
    assert filters.is_it_related("cokolwiek", category="Uslugi IT")


def test_is_it_related_false_for_furniture():
    assert not filters.is_it_related("Dostawa mebli", category="Dostawy")


# --- wymog referencji ---
def test_requires_references_detected():
    assert filters.requires_references("wymagane referencje z co najmniej 3 projektow")


def test_requires_references_wykaz_uslug():
    assert filters.requires_references("Nalezy zlozyc wykaz uslug oraz poswiadczenia")


def test_no_reference_requirement():
    assert not filters.requires_references("Prosta strona wizytowka bez wymogow")


def test_reference_phrases_list():
    hits = filters.matched_reference_phrases("wymagane referencje i portfolio")
    assert "referencj" in hits
    assert "portfolio" in hits


# --- prog budzetu ---
def test_within_budget_none_max():
    assert filters.within_budget(500000, None)


def test_within_budget_ok():
    assert filters.within_budget(10000, 20000)


def test_over_budget():
    assert not filters.within_budget(30000, 20000)


def test_within_budget_missing_value():
    assert filters.within_budget(None, 20000)


# --- normalizacja ---
def test_normalize_maps_fields():
    raw = {
        "id": "X1",
        "calyNumer": "2026-1",
        "title": "Portal z baza danych",
        "advertiser": {"name": "Firma"},
        "category": "Uslugi IT",
        "budget": 12000,
        "terminOfert": "2026-10-01",
    }
    a = normalize(raw)
    assert a.number == "2026-1"
    assert a.advertiser == "Firma"
    assert a.budget_pln == 12000.0
    assert a.url.endswith("/ogloszenia/X1")


def test_normalize_budget_string_with_currency():
    a = normalize({"id": "1", "budget": "18 000,50 PLN"})
    assert a.budget_pln == 18000.5


# --- dedup ---
def test_dedup_filters_seen(tmp_path):
    db = tmp_path / "t.sqlite3"
    conn = store.connect(db)
    a1 = _ann(id="1")
    a2 = _ann(id="2")
    assert len(store.filter_new(conn, [a1, a2])) == 2
    store.mark_seen(conn, [a1])
    new = store.filter_new(conn, [a1, a2])
    assert [a.id for a in new] == ["2"]
    conn.close()


def test_dedup_count(tmp_path):
    conn = store.connect(tmp_path / "t2.sqlite3")
    store.mark_seen(conn, [_ann(id="a"), _ann(id="b")])
    assert store.count(conn) == 2
    conn.close()
