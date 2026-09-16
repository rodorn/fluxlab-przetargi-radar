# FluxLab - Radar zapytan ofertowych IT (Baza Konkurencyjnosci)

Narzedzie CLI / cron, ktore monitoruje nowe zapytania ofertowe (unijne mikro-przetargi)
w [Bazie Konkurencyjnosci](https://bazakonkurencyjnosci.funduszeeuropejskie.gov.pl)
w kategoriach IT i filtruje je pod katem uslug, ktore realizuje FluxLab
(strony www, systemy, integracje, automatyzacja, aplikacje webowe, portale,
bazy danych, GA4/analityka).

Radar jest po stronie **wykonawcy**: szuka zlecen, na ktore mozna zlozyc oferte,
a nie ogloszen o zamowieniach publicznych, ktore sie oglasza.

## Co robi

Dla kazdego trafienia zwraca:

- tytul zapytania,
- zamawiajacego,
- budzet / prog (jesli podany),
- termin skladania ofert,
- link do ogloszenia,
- **flage "wymaga referencji/doswiadczenia"** - zeby odsiac zlecenia,
  ktorych swieza JDG bez portfolio jeszcze nie spelni (warunki udzialu,
  wykaz uslug, poswiadczenia nalezytego wykonania, min. 3 projekty itp.).

Wynik to dzienny digest w formatach:

- **Markdown** (`out/digest_<data>.md`) - podzielony na "kandydatow dla swiezej JDG"
  i "wymagajace referencji",
- **CSV** (`out/digest_<data>.csv`) - do arkusza,
- opcjonalnie **PDF** (`--pdf`, render przez `google-chrome-stable --headless`),
- opcjonalnie **e-mail** (`--email`, konfiguracja przez zmienne srodowiskowe).

Deduplikacja w SQLite (`radar.sqlite3`) sprawia, ze kolejny digest pokazuje
tylko **nowe** ogloszenia.

## Dostep do danych (live vs PRZYKLAD)

Radar w pierwszej kolejnosci probuje oficjalnego endpointu REST
`GET /api/announcements/search`. Endpoint bywa chroniony **anonimowym tokenem
Bearer**, ktory front generuje przez keycloak w przegladarce (realm publiczny
nie wydaje tokenu service-account przez `client_credentials`), i wtedy zwraca
`HTTP 500/401` dla zapytania bez tokena.

- Jesli masz wazny token, ustaw `BK_TOKEN` (patrz nizej) - radar uzyje go
  automatycznie i pobierze **dane live**.
- Jesli tokena brak, radar **automatycznie przechodzi na dane PRZYKLAD**
  (`samples/sample_announcements.json`), zeby dzialac end-to-end. Digest jest
  wtedy wyraznie oznaczony jako fallback. Struktura, filtry i format sa
  identyczne jak dla danych live - po podaniu tokena nic wiecej nie trzeba
  zmieniac.

Aby wymusic tryb offline (bez odpytywania serwera): flaga `--sample`.

## Uruchomienie

```bash
git clone https://github.com/rodorn/fluxlab-przetargi-radar.git
cd fluxlab-przetargi-radar
python -m venv .venv && . .venv/bin/activate
pip install -r requirements-dev.txt

# testy
python -m pytest -q

# dzienny digest (live jesli sie da, inaczej PRZYKLAD)
python -m src.radar --pages 2 --limit 50

# wymus dane przykladowe + PDF
python -m src.radar --sample --pdf

# odsiej duze przetargi (np. tylko do 50 000 PLN)
python -m src.radar --max-budget 50000
```

Najwazniejsze flagi:

| flaga              | opis                                         |
| ------------------ | -------------------------------------------- |
| `--pages N`        | ile stron API pobrac (live)                  |
| `--limit N`        | rekordow na strone                           |
| `--sample`         | wymus dane PRZYKLAD (offline)                |
| `--max-budget PLN` | odsiej ogloszenia powyzej progu              |
| `--pdf`            | dodatkowo wygeneruj PDF                      |
| `--email`          | wyslij digest mailem (env `SMTP_*`)          |
| `--no-dedup`       | nie filtruj po bazie i nie zapisuj (podglad) |
| `--db PATH`        | inna sciezka bazy dedup                      |

## Sekrety (NIE w kodzie)

Wszystkie sekrety czytane sa ze zmiennych srodowiskowych:

```bash
export BK_TOKEN="..."          # opcjonalny token do API live
export SMTP_HOST="smtp.gmail.com"
export SMTP_PORT="587"
export SMTP_USER="ty@example.com"
export SMTP_PASS="haslo-aplikacji"
export DIGEST_TO="ty@example.com"
```

Wygodnie trzymac je w pliku `.env` (jest w `.gitignore`) i zaladowac przed uruchomieniem.

## Cron / codzienny digest

Przyklad wpisu crona (codziennie o 08:00, digest na maila):

```cron
0 8 * * *  cd /home/rodorn/Projekty/zarobek/fluxlab-przetargi-radar && \
  BK_TOKEN="$BK_TOKEN" SMTP_HOST=smtp.gmail.com SMTP_USER=... SMTP_PASS=... DIGEST_TO=... \
  .venv/bin/python -m src.radar --pages 3 --email --pdf >> out/cron.log 2>&1
```

Wariant systemd timer (zamiast crona): utworz `radar.service` (`Type=oneshot`,
`ExecStart=.../.venv/bin/python -m src.radar --pages 3 --email`) oraz
`radar.timer` (`OnCalendar=*-*-* 08:00:00`). Sekrety przez `EnvironmentFile=`.

## Jak Pawel sklada oferte (proces)

1. Codzienny digest wskazuje trafienia IT bez wymogu referencji (sekcja
   "Kandydaci dla swiezej JDG").
2. Wybierz 3-5 zlecen o **niskim progu budzetu** i **bez** flagi referencji.
3. Wejdz na link ogloszenia w Bazie Konkurencyjnosci i zloz oferte przez
   formularz na portalu (przycisk "Zloz oferte"; wymaga konta w Bazie).
4. W ofercie podaj dane JDG:
   - **FluxLab, Pawel Iwanek**, NIP **7831827728**,
   - strona **https://fluxlab.pl**,
   - portfolio/realizacje: **https://fluxlab.pl/realizacje** oraz repozytoria
     **https://github.com/rodorn** jako dowod kompetencji technicznych.
5. Trzymaj sie zakresu, ktory realnie dowozisz (Python, automatyzacja,
   integracje, strony/systemy, GA4). Nie deklaruj doswiadczenia ani realizacji,
   ktorych nie masz - przy warunkach udzialu z wymogiem referencji po prostu
   pomin ogloszenie (radar oznacza je osobno).

## Testy i CI

- `pytest` (18 testow): dopasowanie fraz IT z fleksja PL, wykrywanie wymogu
  referencji, prog budzetu, normalizacja pol API, deduplikacja SQLite.
- GitHub Actions (`.github/workflows/ci.yml`): testy + smoke-run offline
  przy kazdym push / PR.

## Struktura

```
src/
  config.py     # frazy IT, frazy referencji, endpointy, dane JDG
  bk_client.py  # pobranie live (REST) + fallback PRZYKLAD + normalizacja
  filters.py    # dopasowanie fraz (stemming PL), referencje, prog
  store.py      # deduplikacja SQLite
  digest.py     # Markdown + CSV + PDF
  radar.py      # CLI (fetch -> filtr -> dedup -> digest -> mail)
samples/        # dane PRZYKLAD (fallback)
tests/          # pytest
out/            # wygenerowane digesty (sample_digest.* w repo)
```

---

Projekt FluxLab - automatyzacja procesow i wdrozenia AI dla malych firm.
https://fluxlab.pl
