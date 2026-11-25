"""1.63: Abwesenheiten, Schlüssel, „Aktuell im Haus“, Notfallliste mit Abwesenden, Kündigung (rein)."""

from datetime import date, datetime

import pytest

from modern import haus_kern as hk
from modern import kuendigung_kern as kk
from modern import notfall_kern as nk

H = date(2026, 11, 25)


@pytest.fixture
def ablage(monkeypatch):
    daten = {}
    from belegung import speicher

    monkeypatch.setattr(speicher, "lesen", lambda name, std=None, *a, **k: daten.get(name, std))
    monkeypatch.setattr(speicher, "schreiben", lambda name, wert, *a, **k: daten.__setitem__(name, wert))
    import modern.kern as kern

    monkeypatch.setattr(kern, "_schritt", lambda titel, fn, dateien=None: fn())
    return daten


def _nz(name, zimmer="2-101", art="im_haus", haus="2"):
    return nk.NZeile(haus, "EG", zimmer, name, "Gast", date(2026, 12, 4), art, "")


def test_abwesenheit_und_im_haus(ablage):
    hk.abw_anlegen("Beispiel, Erika", "GS-2-101", date(2026, 11, 24), date(2026, 11, 27), "heimfahrt")
    with pytest.raises(ValueError):
        hk.abw_anlegen("", "", H, H)
    with pytest.raises(ValueError):
        hk.abw_anlegen("X", "", H, date(2026, 11, 1))
    abw = hk.abw_laden()
    assert hk.abwesend_am(abw, "Erika Beispiel", "GS-2-101", H) is not None      # Reihenfolge egal
    assert hk.abwesend_am(abw, "Beispiel, Erika", "GS-2-101", date(2026, 11, 28)) is None
    hk.ausgeben("Musterhoff, Kim", "GS-2-103", 2, "Zimmer + Haustür", H, date(2026, 11, 26))
    zs = hk.im_haus([_nz("Beispiel, Erika"), _nz("Musterhoff, Kim", "2-103")], abw, hk.schl_laden(), H,
                    lambda k: "GS-" + k)
    assert [z.art for z in zs] == ["abwesend", "im_haus"] and zs[1].schluessel == 2
    assert hk.zaehlen(zs) == {"im_haus": 1, "abwesend": 1, "geplant": 0}
    assert [z.name for z in hk.filtern(zs, "abwesend")] == ["Beispiel, Erika"]
    assert [z.name for z in hk.filtern(zs, "", "2-103")] == ["Musterhoff, Kim"]


def test_schluessel_zurueck_und_ueberfaellig(ablage):
    hk.ausgeben("Probehaus, Alex", "GS-6-101", 1, am=date(2026, 11, 1), bis=date(2026, 11, 20))
    x = hk.schl_laden()[0]
    assert x.ueberfaellig(H)
    hk.zuruecknehmen(x.id, H)
    assert not hk.schl_laden()[0].offen
    with pytest.raises(ValueError, match="Schon zurück"):
        hk.zuruecknehmen(x.id, H)
    with pytest.raises(ValueError):
        hk.ausgeben("", "")


def test_notfallliste_abwesende_getrennt(ablage):
    hk.abw_anlegen("Beispiel, Erika", "", date(2026, 11, 24), date(2026, 11, 27))
    zs = nk.abwesende_markieren([_nz("Beispiel, Erika"), _nz("Musterhoff, Kim", "2-103")], hk.abw_laden(), H)
    n = nk.zaehlen(zs)["2"]
    assert n["personen"] == 1 and n["abwesend"] == 1 and n["zimmer"] == 1
    html = nk.druck_html(zs, datetime(2026, 11, 25, 9), "Probehaus")
    assert "Abwesend – laut Eintrag nicht im Haus" in html and "1 Person im Haus" in html


def test_kuendigung_pruefen_und_bestaetigung():
    assert kk.pruefen(date(2026, 1, 1), date(2027, 1, 1), date(2026, 12, 31), H) == []
    assert kk.pruefen(date(2026, 1, 1), date(2027, 1, 1), date(2027, 3, 1), H)       # nach Vertragsende
    assert kk.pruefen(date(2026, 1, 1), date(2027, 1, 1), date(2025, 3, 1), H)       # vor Mietbeginn
    mv = type("MV", (), {"anrede": "Frau", "vorname": "Erika", "nachname": "Beispiel", "zimmer_kurz": "6-101",
                         "nr": "26-001"})()
    k = kk.Kuendigung("26-001", "2026-11-20", "2026-12-31", "mieter")
    h = kk.bestaetigung_html(mv, k)
    assert "31.12.2026" in h and "Sehr geehrte Frau Beispiel" in h and "20.11.2026" in h
    assert kk.status_text(k) == "gekündigt zum 31.12.2026 (durch den Mieter)"


def test_vorgabe_aus_gebaeudeplan():
    v = kk.vorgabe("Beispiel, Erika", "GS-6-101", date(2026, 1, 1), date(2026, 12, 31))
    assert (v["vorname"], v["nachname"], v["zimmer"]) == ("Erika", "Beispiel", "GS-6-101")
    assert kk.vorgabe("Kim Musterhoff", "", H, H)["nachname"] == "Musterhoff"
