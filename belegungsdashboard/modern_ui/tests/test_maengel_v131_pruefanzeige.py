"""1.31 – Prüfanzeige „Verbindung prüfen“: warum kommt eine QR-Meldung nicht an? Erfundene Daten."""

from datetime import datetime

import pytest
from openpyxl import Workbook

from modern import qr_meldungen_kern as qm

KOPF = ["ID", "Startzeit", "Fertigstellungszeit", "E-Mail", "Name", "Zimmer", "Art des Problems", "Beschreibung",
        "Code (bitte nicht ändern)"]
LINK = "https://forms.office.com/r/demo?a=ZIMMER&b=CODE"


@pytest.fixture
def daten(tmp_path, monkeypatch):
    from belegung import aenderungen
    from modern import kern, standort_kern  # noqa: F401

    monkeypatch.setenv("BELEGUNG_DATEN", str(tmp_path / "daten"))
    (tmp_path / "daten").mkdir()
    aenderungen.verlauf_leeren()
    standort_kern.waehlen("GS", merken_=False)
    qm._STAND.update(mtime=None, pfad="", gelesen=None, fehler="", neu=0)
    yield tmp_path
    aenderungen.verlauf_leeren()


def _datei(pfad, zeilen=()):
    pfad.parent.mkdir(parents=True, exist_ok=True)
    wb = Workbook()
    ws = wb.active
    ws.append(KOPF)
    for z in zeilen:
        ws.append(z)
    wb.save(pfad)
    return pfad


def _punkte(**kw):
    return {p.titel: p for p in qm.diagnose(**kw)}


def test_ohne_link_und_ohne_antwortdatei(daten):
    p = _punkte()
    assert p["Formular-Link"].stufe == "krit" and p["Antwortdatei"].stufe == "krit"
    assert "DIESEM PC" in p["Antwortdatei"].text and "Inhalt" not in p


def test_link_ohne_code_ist_ein_hinweis(daten):
    qm.link_setzen("https://forms.office.com/r/demo?a=ZIMMER")
    assert _punkte()["Formular-Link"].stufe == "warn"
    qm.link_setzen(LINK)
    assert _punkte()["Formular-Link"].stufe == "ok"


def test_kopie_in_downloads_wird_erkannt(daten):
    qm.link_setzen(LINK)
    f = _datei(daten / "Users" / "demo" / "Downloads" / "Mangel melden.xlsx")
    qm.antwortdatei_setzen(str(f))
    p = _punkte()
    assert p["Antwortdatei"].stufe == "krit" and "KOPIE" in p["Antwortdatei"].text


def test_onedrive_datei_neue_antworten_und_letztes_einlesen(daten):
    qm.link_setzen(LINK)
    f = _datei(daten / "Users" / "demo" / "OneDrive - Beispiel" / "Mangel melden.xlsx",
               [[1, datetime(2026, 11, 20, 8), datetime(2026, 11, 20, 8, 2), "", "", "2-101", "", "Heizung kalt", ""]])
    qm.antwortdatei_setzen(str(f))
    p = _punkte()
    assert p["Antwortdatei"].stufe == "ok" and "Zuletzt geändert" in p
    assert p["Inhalt"].stufe == "warn" and "1 noch nicht eingelesen" in p["Inhalt"].text and "20.11.2026 08:02" in p["Inhalt"].text
    assert "noch nicht" in p["Letztes Einlesen"].text
    qm.einlesen(None, True)
    p = _punkte()
    assert p["Inhalt"].stufe == "ok" and "alle eingelesen" in p["Inhalt"].text
    assert "1 neue Meldung" in p["Letztes Einlesen"].text


def test_leere_datei_und_falsche_spalten(daten):
    qm.link_setzen(LINK)
    f = _datei(daten / "OneDrive" / "leer.xlsx")
    qm.antwortdatei_setzen(str(f))
    assert "noch keine Antworten" in _punkte()["Inhalt"].text
    wb = Workbook()
    wb.active.append(["ID", "Frage 1"])
    wb.save(f)
    assert _punkte()["Inhalt"].stufe == "krit"


def test_datei_verschwunden(daten):
    qm.link_setzen(LINK)
    f = _datei(daten / "OneDrive" / "weg.xlsx")
    qm.antwortdatei_setzen(str(f))
    f.unlink()
    assert "gibt es auf diesem PC nicht" in _punkte()["Antwortdatei"].text


def test_unterpunkt_im_menueband_und_in_der_seitenleiste():
    import pathlib

    from modern import menueband as mb
    from modern.seite_zimmer import ANSICHTEN

    assert ANSICHTEN["qr"] == "QR-Meldungen"
    text = pathlib.Path(mb.__file__).read_text(encoding="utf-8")
    assert '_split("zimmer", ansichten, "Defekte Zimmer", "warning_amber", ["maengel", "qr"]' in text   # Menüband
    assert 'v("zimmer", "qr", "QR-Meldungen")' in text                                                  # Seitenleiste
