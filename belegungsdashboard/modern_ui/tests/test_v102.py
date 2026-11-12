"""1.02 – Postfach auf „Aufgaben“ mit Öffnen in Outlook, Standorte im Menüband in einer Reihe. Nur erfundene Daten."""

import inspect
from datetime import datetime

from modern import band_ui, outlook_kern as ok, seite_heute, ui_bausteine


def test_mail_merkt_sich_die_kennung_zum_oeffnen():
    m = ok.Mail(datetime(2026, 11, 12, 9, 30), "Anreise Montag", "Erika Muster", True, "ABC123", "STORE1")
    assert (m.eintrag, m.ablage) == ("ABC123", "STORE1")
    assert ok.Mail(datetime(2026, 11, 12), "x", "y", False).eintrag == ""      # alte Aufrufe bleiben gültig


def test_oeffnen_ohne_kennung_oder_ohne_outlook_gibt_verstaendlichen_text():
    assert "nicht öffnen" in ok.oeffnen("")
    text = ok.oeffnen("ABC123")                       # hier ohne Windows/Outlook
    assert text and "Outlook" in text


def test_ordner_oeffnen_ohne_einstellung():
    assert "Kein Outlook-Ordner" in ok.ordner_oeffnen("")


def test_vorschau_merkt_sich_anzahl_getrennt(monkeypatch):
    aufrufe = []
    monkeypatch.setattr(ok, "ordner", lambda: "Internatsdienst")
    monkeypatch.setattr(ok, "lesen", lambda pfad, anzahl=ok.ANZAHL: aufrufe.append(anzahl) or [])
    ok._ZWISCHEN.update(zeit=0.0, pfad=None)
    ok.vorschau(False, 6)
    ok.vorschau(False, 12)
    ok.vorschau(False, 12)
    assert aufrufe == [6, 12]


def test_postfach_steht_auf_der_aufgaben_seite():
    q = inspect.getsource(seite_heute._postfach)
    assert "outlook_kern.block(a, anzahl=12, postfach=True)" in q


def test_mehr_als_drei_optionen_in_einer_reihe():
    assert "reihe" in inspect.signature(band_ui.stapel).parameters
    assert "m-bg-reihe" in band_ui.CSS
    q = inspect.getsource(ui_bausteine.segmente)
    assert 'len(werte) == 4' in q and "raster" in q and "m-bg-raster" in band_ui.CSS
