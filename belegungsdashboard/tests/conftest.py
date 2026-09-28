import sys
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

HAEUSER = {"BFW BP": ["A Gebäude", "B Gebäude"], "BFW GS": ["GS-Haus-2"], "BFW WE": ["Internat A", "Internat B"]}


def pivot_matrix(von: date, bis: date, stichtag: date, seed: int = 3) -> list[list]:
    """Matrix im Layout von pivot_neu.xlsx: Gruppenzeilen, Tageszeilen, Zwischensummen,
    'keine Zuordnung' und 'Gesamtergebnis'. Nach dem Stichtag fällt der Bestand ab."""
    rng = np.random.default_rng(seed)
    spalten = [(s, h) for s, hs in HAEUSER.items() for h in hs]
    zeile_standort = [None]
    zeile_haus = ["Zeilenbeschriftungen"]
    for s, hs in HAEUSER.items():
        for i, h in enumerate(hs):
            zeile_standort.append(s if i == 0 else None)
            zeile_haus.append(h)
    zeile_standort += ["keine Zuordnung", "Gesamtergebnis"]
    zeile_haus += ["keine Zuordnung", None]
    m = [["Belegungen", "Spaltenbeschriftungen"] + [None] * (len(zeile_haus) - 2), zeile_standort, zeile_haus]
    tag = von
    letzter_monat = None
    while tag <= bis:
        if (tag.year, tag.month) != letzter_monat:
            m.append([f"{['Jan','Feb','Mär','Apr','Mai','Jun','Jul','Aug','Sep','Okt','Nov','Dez'][tag.month-1]} {tag.year}"] + [None] * (len(zeile_haus) - 1))
            letzter_monat = (tag.year, tag.month)
        saison = 1 + 0.08 * np.sin(2 * np.pi * (tag.month - 3) / 12)
        werte = []
        for s, h in spalten:
            basis = {"BFW BP": 40, "BFW GS": 60, "BFW WE": 35}[s] * saison
            if tag > stichtag:
                basis *= max(0.0, 1 - (tag - stichtag).days / 500)
            werte.append(int(round(basis + rng.normal(0, 2))) if tag <= stichtag else int(round(basis)))
        m.append([tag.strftime("%d.%m.%Y")] + werte + [3, sum(werte) + 3])
        tag += timedelta(days=1)
    m.append(["Gesamtergebnis"] + [0] * (len(zeile_haus) - 1))
    return m


@pytest.fixture(scope="session")
def stichtag():
    return date(2026, 6, 15)


@pytest.fixture(scope="session")
def pivotdaten(stichtag):
    from belegung import pivot

    d = pivot.parse_matrix(pivot_matrix(date(2021, 1, 1), date(2027, 12, 31), stichtag), pivot.PivotProfil())
    d.abrufdatum = stichtag
    return d


@pytest.fixture(scope="session")
def datenstand(pivotdaten):
    from belegung import prognose
    from belegung.datenstand import Datenstand, Eintrag

    eintraege = [
        Eintrag("Mieter", "BFW GS", date(2026, 1, 1), date(2099, 12, 31), 5, "Firma X", "mieten"),
        Eintrag("FRAI", "BFW GS", date(2026, 1, 1), date(2026, 12, 31), 4, "", "manuell"),
        Eintrag("Anreise", "BFW BP", date(2026, 6, 20), date(2027, 6, 19), 3, "Neue", "anreisen"),
        Eintrag("Anreise", "BFW BP", date(2026, 6, 1), date(2027, 5, 31), 2, "Schon da", "anreisen"),
    ]
    kap = {"BFW BP": {"netto": 120, "brutto": 130}, "BFW GS": {"netto": 80, "brutto": 100},
           "BFW WE": {"netto": 90, "brutto": 90}}
    ds = Datenstand(pivot=pivotdaten, eintraege=eintraege, kapazitaeten=kap, importe={"anreisen": {"anzahl": 2}})
    ds.prognose = prognose.berechne(pivotdaten.reha, ds.anreise_bestand(), ds.stichtag)
    return ds
