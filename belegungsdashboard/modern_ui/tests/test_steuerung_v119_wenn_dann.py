"""1.19 – Wenn-dann im Cockpit: angenommener Wert in einem Monat, Abweichung klingt mit gemessener Beharrung ab."""

import inspect
from datetime import date
from types import SimpleNamespace as NS

import pytest

from modern import cockpit_kern as ck
from test_steuerung_v116_cockpit import _bedarf, _karte


def test_abweichung_klingt_ab_und_spanne_waechst_wieder():
    bd = _bedarf()                                                   # erwartet 90, oben 100, fest 80
    w = ck.wenn_dann(bd, 2, 110, 0.5)
    assert w.abweichung == 20 and w.bedarf.erwartet[:2] == [90, 90]  # vor dem Monat unverändert
    assert w.bedarf.erwartet[2:5] == [110, 100, 95]                  # 20 · 0,5ᵏ
    assert w.bedarf.hoch[2] == 110                                   # im angenommenen Monat keine Spanne
    assert w.bedarf.hoch[3] == pytest.approx(100 + 10 * (1 - .25) ** .5, abs=.1)
    assert bd.erwartet[2] == 90                                      # Original bleibt unverändert


def test_nicht_unter_fest_und_nicht_in_der_vergangenheit():
    bd = _bedarf()
    w = ck.wenn_dann(bd, 0, 20, 0.9)
    assert min(x for x in w.bedarf.erwartet) >= 80                   # fest gebucht ist die Untergrenze
    bd.ist[1] = True
    assert ck.wenn_dann(bd, 1, 120) is None                          # Ist-Monate sind keine Annahme


def test_beharrung_aus_der_geschichte():
    assert ck.beharrung(None) == ck.BEHARRUNG_STANDARD
    zeilen = [NS(monat=date(2023 + (i // 12), i % 12 + 1, 1), art="ist", ist=float(100 + (i // 6) % 2 * 10))
              for i in range(36)]                                    # Blöcke von 6 Monaten: hohe Beharrung
    assert ck.beharrung(NS(zeilen=zeilen)) >= 0.6
    saison = [NS(monat=z.monat, art="ist", ist=100.0 + (10 if i % 2 else -10)) for i, z in enumerate(zeilen)]
    assert ck.beharrung(NS(zeilen=saison)) == ck.BEHARRUNG_STANDARD  # jedes Jahr gleich = reine Saison, keine Abweichung
    wechsel = [NS(monat=z.monat, art="ist", ist=100.0 + 10 * (-1) ** (i + i // 12)) for i, z in enumerate(zeilen)]
    assert ck.beharrung(NS(zeilen=wechsel)) == 0.3                   # springt jeden Monat: untere Grenze


def test_wirkung_auf_engpass_und_satz():
    a = _karte("a", 10, 1, 0, 3)
    bd = _bedarf()
    vorher = ck.bewerten([a], {"a": 3}, bd, None, 0, [])
    w = ck.wenn_dann(bd, 2, 110, 0.5)
    nachher = ck.bewerten([a], {"a": 3}, w.bedarf, None, 0, [])
    assert nachher.reserve[2] == 120 - 5 - 10 - 110 and nachher.engpaesse == [2]
    s = ck.wenn_dann_satz(w, vorher, nachher)
    assert s.startswith("Wenn im Mär 110 statt 90 belegt sind") and "fehlen 5 Betten" in s and "50 %" in s
    o = ck.diagramm(w.bedarf, nachher, wd=w)
    assert {"ohne Wenn-dann", "Wenn-dann"} <= {x["name"] for x in o["series"]}


def test_oberflaeche():
    from modern import cockpit_ui

    q = inspect.getsource(cockpit_ui)
    assert '"m_achse"' in q and "keydown.enter" in q and "Achtung: gerechnet mit der Annahme" in q
