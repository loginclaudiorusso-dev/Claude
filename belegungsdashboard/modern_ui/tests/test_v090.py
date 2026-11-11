"""0.90 – Review-Härtung: Prüfen und Speichern unter derselben Sperre, Sperre mit Besitzer und Server-Uhr,
Nichtanreise übersteht einen Import, Notfallliste getrennt, Leitungsaussage vorsichtiger. Erfundene Daten."""

from __future__ import annotations

import json
import os
import time
from datetime import date, timedelta
from pathlib import Path

import pytest

from modern import kern, netz_kern, standort_kern  # noqa: F401

MOD = Path(__file__).resolve().parent.parent / "modern"


@pytest.fixture
def ordner(tmp_path, monkeypatch):
    d = tmp_path / "Daten"
    d.mkdir()
    monkeypatch.setenv("BELEGUNG_DATEN", str(d))
    standort_kern.waehlen("GS", merken_=False)
    return d


# ---- Sperre -----------------------------------------------------------------------------------------------------------

def test_sperre_traegt_besitzer_und_fremde_bleibt(ordner):
    with netz_kern.sperre():
        assert netz_kern.eigene_sperre() and netz_kern.sperre_info()["token"]
        # ein anderer PC hat sie (z. B. nach Übernahme) – beim Freigeben NICHT löschen
        (ordner / netz_kern.SPERRE).write_text(json.dumps({"wer": "Probe an PC-09", "token": "fremd"}), encoding="utf-8")
    assert (ordner / netz_kern.SPERRE).exists()


def test_alter_nach_server_uhr_nicht_pc_uhr(ordner, monkeypatch):
    p = ordner / netz_kern.SPERRE
    p.write_text(json.dumps({"wer": "Probe an PC-09", "token": "fremd"}), encoding="utf-8")
    monkeypatch.setattr(time, "time", lambda: 10 ** 10)          # PC-Uhr weit vorgestellt
    with pytest.raises(netz_kern.Besetzt):                       # frische Sperre gilt trotzdem nicht als verwaist
        with netz_kern.sperre(warten=0.3):
            pass


def test_verwaiste_sperre_atomar_uebernommen(ordner):
    p = ordner / netz_kern.SPERRE
    p.write_text(json.dumps({"token": "abgestuerzt"}), encoding="utf-8")
    alt = time.time() - 600
    os.utime(p, (alt, alt))
    with netz_kern.sperre(warten=1):
        assert netz_kern.eigene_sperre()
    assert not list(ordner.glob(".innternat_sperre.*"))         # keine Reste der Übernahme


def test_lebende_sperre_wird_beim_uebernehmen_zurueckgelegt(ordner):
    p = ordner / netz_kern.SPERRE
    p.write_text(json.dumps({"token": "lebt"}), encoding="utf-8")
    assert netz_kern._uebernehmen(p, netz_kern.SPERRE_ALT) is False
    assert json.loads(p.read_text(encoding="utf-8"))["token"] == "lebt"


def test_pruefen_und_speichern_unter_einer_sperre():
    from modern import zimmer_kern as zk

    for fn in (kern.zuweisen, kern.vorschlaege_uebernehmen, zk.zimmer_setzen, zk.wechseln, zk.umzug_speichern,
               zk.auszug, zk.nichtanreise, zk.person_ins_zimmer, zk.fest_setzen, zk.umzug_fest):
        assert getattr(fn, "unter_sperre", False), fn.__name__


def test_zuweisen_wartet_auf_fremde_sperre(ordner, monkeypatch):
    monkeypatch.setattr(netz_kern, "SPERRE_WARTEN", 0.3)
    (ordner / netz_kern.SPERRE).write_text(json.dumps({"wer": "Probe an PC-09", "token": "fremd"}), encoding="utf-8")
    with pytest.raises(netz_kern.Besetzt):                       # liest/prüft gar nicht erst ohne Sperre
        kern.zuweisen("id:1", "GS-2-301")


# ---- Nichtanreise übersteht den Import ------------------------------------------------------------------------------

def test_nichtanreise_bleibt_nach_neuem_import(ordner):
    from belegung import aenderungen, anreiseliste
    from belegung import zimmerplan as zp
    from modern import zimmer_kern as zk

    aenderungen.verlauf_leeren()
    heute = date.today()
    finn = lambda: anreiseliste.Person("Fehlt, Finn", "GS RVL", heute, True, tn_id="7",  # noqa: E731
                                       abreise=heute + timedelta(days=20))
    anreiseliste.speichern([finn()], {})
    st = zp.laden()
    zp.zuweisungen_speichern([zp.Zuteilung(st.bedarf[0], st.lage.zimmer["GS-2-301"])])
    zk.nichtanreise("id:7", heute)
    # dieselbe Liste kommt noch einmal – mit „Internat: ja“
    anreiseliste.importieren(anreiseliste.Anreiseliste("liste.xlsx", heute, "RVL", [finn()]))
    assert "id:7" not in {b.schluessel for b in zp.laden().bedarf}
    assert "id:7" in zk.nichtanreisen()
    # doch angereist → wieder in der Planung
    assert "wieder als Anreise" in zk.nichtanreise_zuruecknehmen("id:7")
    assert "id:7" in {b.schluessel for b in zp.laden().bedarf} and not zk.nichtanreisen()
    aenderungen.verlauf_leeren()


# ---- Band: Gebuchtes über der oberen Grenze ---------------------------------------------------------------------------

def test_band_hebt_an_statt_zu_druecken(monkeypatch):
    from types import SimpleNamespace as NS

    from modern import auswertung_kern as ak

    m = date(2026, 11, 1)
    monkeypatch.setattr(ak, "_monatsprognosen", lambda *a: {m: {
        "art": "laufend", "erwartet": 100.0, "lo80": 95.0, "hi80": 104.0, "lo95": 90.0, "hi95": 108.0,
        "gesichert": 110.0, "ist": None, "vertraege": 0.0}})
    ds = NS(stichtag=date(2026, 11, 10), prognose=NS(modelle={}), kapazitaet=lambda *a: 200)
    z = ak._prognose(ds, "BFW GS", False, 0, 1).zeilen[0]
    assert z.erwartet == 110 and z.lo80 == 110 and z.lo95 == 110          # nie unter dem Gebuchten
    assert z.hi80 >= z.erwartet and z.hi95 >= z.hi80                      # Reihenfolge stimmt


def test_notfallliste_trennt_unbestaetigte():
    from datetime import datetime

    from modern import notfall_kern as nk

    zs = [nk.NZeile("1", "EG", "1-101", "Muster, Max", "RVL", None, "im_haus", ""),
          nk.NZeile("1", "EG", "1-102", "Probe, Pia", "EMR", None, "geplant", "")]
    h = nk.druck_html(zs, datetime(2026, 11, 10, 7, 30))
    assert h.index("Im Haus laut Belegung") < h.index("Muster, Max") < h.index("NICHT bestätigt") < h.index("Probe, Pia")
    assert "Planstand 10.11.2026, 07:30 Uhr – ohne Gäste" in h and "<thead>" in h
