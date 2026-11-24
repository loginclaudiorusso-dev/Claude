"""1.51 – Hausordnung per eigenem QR-Code bestätigen; gilt je Aufenthalt (Auszug → für die nächste Person wieder
offen); Mieter ausgenommen; die Mängel-Einlese überspringt diese Dateien. Erfundene Namen."""

from datetime import date, datetime, timedelta

import pytest

from modern import hausordnung_kern as hk
from modern import qr_meldungen_kern as qm


@pytest.fixture
def goslar(tmp_path, monkeypatch):
    from belegung import aenderungen
    from modern import kern, standort_kern  # noqa: F401

    monkeypatch.setenv("BELEGUNG_DATEN", str(tmp_path / "daten"))
    (tmp_path / "daten").mkdir()
    aenderungen.verlauf_leeren()
    standort_kern.waehlen("GS", merken_=False)
    yield tmp_path
    aenderungen.verlauf_leeren()


def _datei(ordner, rid, zimmer, name, zeit, code=""):
    (ordner / f"ho-{rid}.txt").write_text(f"INNTERNAT-HO\nID: {rid}\nZeit: {zeit}\nZimmer: {zimmer}\nCode: {code}\n"
                                          f"Name: {name}\nGelesen: [\"Ich habe die Hausordnung gelesen\"]\nENDE\n",
                                          encoding="utf-8")


def test_parsen():
    r = hk.parsen("INNTERNAT-HO\nID: 5\nZeit: 2026-11-24T08:00:00Z\nZimmer: 2-101\nName: Kim Test\nGelesen: Ja\nENDE")
    assert (r.id, r.zimmer_text, r.name) == ("ho|5", "2-101", "Kim Test")
    assert hk.parsen("INNTERNAT-HO\nID: 6\nZimmer: 2-101\nGelesen: \nENDE") is None          # ohne Haken: nichts
    assert hk.parsen("INNTERNAT-QR\nID: 7\nZimmer: 2-101\nBeschreibung: x\nENDE") is None
    assert qm.mail_parsen("", "INNTERNAT-HO\nID: 8\nZimmer: 2-101\nGelesen: Ja\nENDE") is None


def test_bestaetigung_gilt_je_aufenthalt(goslar):
    from belegung import zimmerplan as zp
    from modern import gaeste_kern as gk

    heute = date.today()
    zid = next(iter(gk.zimmer_frei(heute - timedelta(days=2), heute + timedelta(days=3))))
    gk.anlegen("Erster, Kim", heute - timedelta(days=2), heute + timedelta(days=3), "", "", False, "", "", zid)
    gk.anlegen("Zweiter, Alex", heute + timedelta(days=5), heute + timedelta(days=9), "", "", False, "", "", zid)
    o = goslar / "qr"
    o.mkdir()
    qm.dateiordner_setzen(str(o))
    kurz = zid.removeprefix("GS-")
    _datei(o, "1", kurz, "Kim Erster", datetime.now().isoformat(timespec="minutes"))
    assert hk.einlesen() == (1, "")
    assert hk.einlesen() == (0, "")                                 # dieselbe Antwort nicht doppelt
    assert qm.ordner_lesen(str(o)).unbekannt == [] and qm.ordner_lesen(str(o)).zeilen == []
    stand = zp.laden()
    z = {x.name: x for x in hk.status(stand, heute)}
    assert z["Erster, Kim"].bestaetigt and z["Erster, Kim"].quelle == "QR"
    # nach dem Auszug: der Nächste im selben Zimmer ist offen
    spaeter = heute + timedelta(days=6)
    z2 = {x.name: x for x in hk.status(stand, spaeter)}
    assert "Erster, Kim" not in z2 and not z2["Zweiter, Alex"].bestaetigt
    assert [x.name for x in hk.offene(stand, spaeter)] == ["Zweiter, Alex"]
    hk.von_hand(zid, z2["Zweiter, Alex"].person, "Zweiter, Alex", datetime.combine(spaeter, datetime.min.time()))
    z3 = {x.name: x for x in hk.status(zp.laden(), spaeter)}
    assert z3["Zweiter, Alex"].quelle == "von Hand"
    hk.zuruecknehmen(z3["Zweiter, Alex"].bid)
    assert not {x.name: x for x in hk.status(zp.laden(), spaeter)}["Zweiter, Alex"].bestaetigt


def test_mieter_ausgenommen_und_link(goslar):
    from belegung import mieter as mt
    from belegung import zimmerplan as zp
    from modern import mieter_kern as mk

    heute = date.today()
    zimmer = list(mk.zimmer_auswahl(heute - timedelta(days=10), heute + timedelta(days=100), "Frau"))
    mt.anlegen(mt.Mietvertrag("26-901", "Frau", "Erika", "Beispiel", zimmer[0], heute - timedelta(days=10),
                              heute + timedelta(days=100), 400.0))
    assert all(x.name != "Beispiel, Erika" for x in hk.status(zp.laden(), heute))
    assert "Prüfcode" in hk.link_setzen("https://forms.office.com/r/x?a=zimmer&b=Code")
    assert hk.link().endswith("a=ZIMMER&b=CODE")
    with pytest.raises(ValueError):
        hk.link_setzen("forms.office.com/x")
