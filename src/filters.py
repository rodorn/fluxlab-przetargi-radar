"""Filtry: dopasowanie fraz IT, wykrywanie wymogu referencji, prog budzetu."""

from __future__ import annotations

import unicodedata

from . import config


_SUFFIXES = (
    "ami",
    "ach",
    " owych",
    "owej",
    "owo",
    "ych",
    "ego",
    "emu",
    "ej",
    "em",
    "ow",
    "om",
    "ie",
    "y",
    "e",
    "a",
    "i",
    "o",
    "u",
)


def strip_pl(text: str) -> str:
    """Usuwa polskie ogonki i sprowadza do lower-case do porownania fraz."""
    if not text:
        return ""
    nfkd = unicodedata.normalize("NFKD", text)
    no_marks = "".join(c for c in nfkd if not unicodedata.combining(c))
    return no_marks.replace("ł", "l").replace("Ł", "l").lower()


def _stem(word: str) -> str:
    """Bardzo lekki stem PL: obcina koncowke fleksyjna (min. rdzen 4 znaki)."""
    w = word
    for suf in _SUFFIXES:
        if w.endswith(suf) and len(w) - len(suf) >= 4:
            return w[: -len(suf)]
    return w


def _words(text: str) -> list[str]:
    return strip_pl(text).replace("/", " ").replace(",", " ").split()


def matched_it_phrases(text: str) -> list[str]:
    """Zwraca frazy IT, ktorych wszystkie tokeny wystepuja w tekscie.

    Odporne na fleksje PL: token frazy pasuje, gdy jakies slowo tekstu zaczyna
    sie od jego rdzenia. Krotkie tokeny (ga4, api) - dokladne dopasowanie slowa.
    """
    words = _words(text)

    def token_present(tok: str) -> bool:
        if len(tok) <= 4:
            return tok in words
        stem = _stem(tok)
        return any(w.startswith(stem) for w in words)

    hits = []
    for phrase in config.IT_PHRASES:
        p_tokens = strip_pl(phrase).split()
        if all(token_present(t) for t in p_tokens):
            hits.append(phrase)
    return hits


def is_it_related(text: str, category: str = "") -> bool:
    """True jesli tekst lub kategoria wskazuja na zapytanie IT."""
    if matched_it_phrases(text):
        return True
    cat_norm = strip_pl(category)
    return any(strip_pl(h) in cat_norm for h in config.IT_CATEGORY_HINTS)


def requires_references(text: str) -> bool:
    """Wykrywa wymog referencji/doswiadczenia (odsiew dla swiezej JDG)."""
    norm = strip_pl(text)
    return any(strip_pl(p) in norm for p in config.REFERENCE_REQUIREMENT_PHRASES)


def matched_reference_phrases(text: str) -> list[str]:
    norm = strip_pl(text)
    return [p for p in config.REFERENCE_REQUIREMENT_PHRASES if strip_pl(p) in norm]


def within_budget(budget_pln, max_budget=config.DEFAULT_MAX_BUDGET_PLN) -> bool:
    """True jesli budzet miesci sie w progu (lub brak progu / brak danych)."""
    if max_budget is None or budget_pln is None:
        return True
    try:
        return float(budget_pln) <= float(max_budget)
    except (TypeError, ValueError):
        return True
