"""1.26 – Prognose am Monatsletzten: kein doppelter Monat, keine Verschiebung um zwei Monate (Laufzeit-Korrektur,
Hauptprogramm unverändert). Synthetische Saison-Reihe."""

from datetime import date, timedelta

import numpy as np
import pandas as pd
import pytest

from belegung import konfig
from belegung import prognose as P
from modern import prognose_fix_kern as pf


def _reha(stichtag):
    idx = pd.date_range("2021-01-01", "2029-06-30", freq="D")
    s = 80 + 10 * np.sin(2 * np.pi * (idx.month - 1) / 12)
    df = pd.DataFrame({k: s for k in konfig.STANDORTE}, index=idx)
    df[df.index > pd.Timestamp(stichtag)] = 0
    return df


def _soll(monat: date) -> float:
    return 80 + 10 * np.sin(2 * np.pi * (monat.month - 1) / 12)


@pytest.mark.parametrize("stichtag", [date(2026, 10, 30), date(2026, 10, 31), date(2027, 2, 28), date(2028, 2, 29),
                                      date(2026, 12, 31), date(2026, 11, 13)])
def test_jeder_monat_einmal_und_folgemonat_passt(stichtag):
    assert pf.installieren()
    pg = P.berechne(_reha(stichtag), pd.DataFrame(), stichtag)
    folge = (stichtag + timedelta(days=1)).replace(day=1)
    for st in list(konfig.STANDORTE) + [konfig.GESAMT]:
        w = pg.werte[st]
        monate = [x.monat for x in w]
        assert len(monate) == len(set(monate)), st                       # jeder Monat genau einmal
        erste = next(x for x in w if x.art != "ist")
        monatsende = (stichtag + timedelta(days=1)).day == 1
        assert erste.monat == (folge if monatsende else stichtag.replace(day=1)), st
        if monatsende:                                                   # Folgemonat bekommt seinen eigenen Saisonwert
            faktor = 1 if st != konfig.GESAMT else len(konfig.STANDORTE)
            assert abs(erste.erwartet - faktor * _soll(folge)) < 2.5 * faktor, (st, erste.erwartet)


def test_hauptprogramm_bleibt_unveraendert():
    import inspect

    pf.installieren()
    assert 'pd.Timestamp(stichtag).to_period("M")' in open(inspect.getsourcefile(pf._ORIG["berechne"]),
                                                           encoding="utf-8").read()      # Datei selbst unangetastet
    assert "Monat nach dem Stichtag" in (P.berechne.__doc__ or "")
