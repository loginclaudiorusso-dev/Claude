"""0.61: Sperre früher beenden, Zimmer trotzdem nehmen, Jahr der Vertragsnummer, Nummer nachträglich ändern.
Erfundene Namen und Beträge."""

from datetime import date
from types import SimpleNamespace

import pytest

from belegung.gebaeudeplan import Belegung


@pytest.fixture
def goslar(tmp_path, monkeypatch):
    from belegung import aenderungen
    from modern import kern, standort_kern  # noqa: F401

    monkeypatch.setenv("BELEGUNG_DATEN", str(tmp_path))
    aenderungen.verlauf_leeren()
    standort_kern.waehlen("GS", merken_=False)
    yield tmp_path
    aenderungen.verlauf_leeren()


# ---- Sperre früher beenden ----------------------------------------------------------------------------------

def test_sperre_wird_gekuerzt_und_angezeigt(goslar):
    from modern import sperre_kern as sk

    sk.setzen_schritt("GS-6-305", date(2027, 3, 1), "Abnahme FM")
    assert sk.frei_ab("GS-6-305") == date(2027, 3, 1)
    lage = SimpleNamespace(belegungen={
        "GS-6-305": [Belegung("GS-6-305", date(2026, 10, 1), date(2027, 6, 30), "gesperrt", grund="Renoviert"),
                     Belegung("GS-6-305", date(2027, 7, 1), date(2027, 12, 31), "belegt", name="Erfunden, Max")],
        "GS-6-306": [Belegung("GS-6-306", date(2026, 10, 1), date(2027, 6, 30), "gesperrt", grund="Renoviert")]})
    sk._kuerzen(lage)
    s = [b for b in lage.belegungen["GS-6-305"] if b.art == "gesperrt"]
    assert len(s) == 1 and s[0].bis == date(2027, 2, 28)                    # endet am Vortag
    assert any(b.art == "belegt" for b in lage.belegungen["GS-6-305"])     # Personen bleiben
    assert lage.belegungen["GS-6-306"][0].bis == date(2027, 6, 30)         # andere Zimmer unberührt
    sp = sk.sperren(SimpleNamespace(lage=lage), "GS-6-305", date(2026, 11, 5))
    assert sp and sp[0].bis == date(2027, 6, 30) and sp[0].frei_ab == date(2027, 3, 1)
    assert "früher frei ab 01.03.2027" in sp[0].text


def test_sperre_ganz_danach_entfaellt_nicht_im_internat_bleibt(goslar):
    from modern import sperre_kern as sk

    sk.setzen("GS-6-307", date(2026, 9, 1))
    sk.setzen("GS-6-308", date(2026, 9, 1))
    lage = SimpleNamespace(belegungen={
        "GS-6-307": [Belegung("GS-6-307", date(2026, 10, 1), date(2027, 6, 30), "gesperrt", grund="Renoviert")],
        "GS-6-308": [Belegung("GS-6-308", date(2000, 1, 1), date(2099, 12, 31), "gesperrt", grund=sk.NIE)]})
    sk._kuerzen(lage)
    assert lage.belegungen["GS-6-307"] == []
    assert lage.belegungen["GS-6-308"][0].bis == date(2099, 12, 31)


def test_sperre_zuruecknehmen_und_rueckgaengig(goslar):
    from modern import kern
    from modern import sperre_kern as sk

    sk.setzen_schritt("GS-6-305", date(2027, 3, 1))
    sk.setzen_schritt("GS-6-305", None)
    assert sk.frei_ab("GS-6-305") is None
    ok, _ = kern.rueckgaengig()
    assert ok and sk.frei_ab("GS-6-305") == date(2027, 3, 1)


def test_lage_bauen_ist_umgeleitet(goslar):
    from belegung import zimmerplan as zp
    from modern import sperre_kern as sk

    assert zp.lage_bauen is sk._lage_bauen
    zp.laden()                                                               # läuft ohne Fehler durch


# ---- Vertragsnummer -------------------------------------------------------------------------------------------

def test_vertragsjahr():
    from modern import mieter_kern as mk

    assert mk.vertragsjahr(date(2027, 1, 1), date(2026, 12, 10)) == 2027    # im Dezember für Januar
    assert mk.vertragsjahr(date(2026, 12, 1), date(2027, 1, 5)) == 2027     # im neuen Jahr erstellt
    assert mk.vertragsjahr(date(2026, 3, 1), date(2026, 2, 1)) == 2026
    assert mk._jahr_pruefen("26-001", date(2027, 1, 1), date(2026, 12, 10)).startswith("Die Vertragsnummer muss mit 27")
    assert mk._jahr_pruefen("27-001", date(2027, 1, 1), date(2026, 12, 10)) is None


def _vertrag(nr="26-001"):
    from belegung import mieter as mt
    from modern import mieter_kern as mk

    zimmer = list(mk.zimmer_auswahl(date(2027, 3, 1), date(2027, 8, 31), "Frau"))
    mv = mt.Mietvertrag(nr, "Frau", "Erika", "Erfunden", zimmer[0], date(2027, 3, 1), date(2027, 8, 31), 400.0,
                        erstellt="2026-12-10T10:00:00")
    mt.anlegen(mv)
    return mv, zimmer


def _werte(mv, **neu):
    w = {"anrede": mv.anrede, "vorname": mv.vorname, "nachname": mv.nachname, "zimmer": mv.zimmer, "von": mv.von,
         "bis": mv.bis, "miete": mv.miete, "flaeche": mv.flaeche, "schluessel": mv.schluessel, "kaution": mv.kaution,
         "kaution_bis": mv.kaution_bis, "email": mv.email}
    w.update(neu)
    return w


def test_nummer_nachtraeglich_aendern(goslar):
    from belegung import mieter as mt
    from belegung import zimmerplan as zp
    from modern import mieter_kern as mk

    mv, _z = _vertrag("26-001")
    text, _ = mk.vertrag_aendern("26-001", _werte(mv, nr="27-001"), unterlagen=False)
    assert "Vertragsnummer 26-001 → 27-001" in text
    assert mt.nach_nummer("26-001") is None and mt.nach_nummer("27-001") is not None
    personen = [z["person"] for z in zp.zuweisungen_laden()]
    assert "mv:27-001" in personen and "mv:26-001" not in personen
    with pytest.raises(ValueError, match="muss mit 27"):
        mk.vertrag_aendern("27-001", _werte(mt.nach_nummer("27-001"), nr="26-002"), unterlagen=False)


def test_zimmer_trotzdem_nehmen(goslar):
    from belegung import mieter as mt
    from belegung import protokoll
    from modern import mieter_kern as mk

    mv, zimmer = _vertrag("27-001")
    mt.anlegen(mt.Mietvertrag("27-002", "Herr", "Max", "Erfunden", zimmer[2], date(2027, 3, 1), date(2027, 8, 31), 400.0))
    with pytest.raises(ValueError, match="trotzdem"):
        mk.vertrag_aendern("27-001", _werte(mv, zimmer=zimmer[2]), unterlagen=False)
    mk.vertrag_aendern("27-001", _werte(mv, zimmer=zimmer[2], trotzdem=True), unterlagen=False)
    assert mt.nach_nummer("27-001").zimmer == zimmer[2]
    assert any(e.get("aktion") == "Zimmer trotz Hinweis gewählt" for e in protokoll.laden())
