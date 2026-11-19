"""1.28 – Meldungen per QR-Code (Forms, anonym): einlesen, Zimmer erkennen, übernehmen, verwerfen. Erfundene Daten."""

from datetime import date, datetime

import pytest
from openpyxl import Workbook

from modern import qr_meldungen_kern as qm

KOPF = ["ID", "Startzeit", "Fertigstellungszeit", "E-Mail", "Name", "Zimmer", "Art des Problems", "Beschreibung"]


@pytest.fixture
def stand(tmp_path, monkeypatch):
    from belegung import aenderungen
    from modern import kern, standort_kern  # noqa: F401

    monkeypatch.setenv("BELEGUNG_DATEN", str(tmp_path / "daten"))
    (tmp_path / "daten").mkdir()
    aenderungen.verlauf_leeren()
    standort_kern.waehlen("GS", merken_=False)
    qm._STAND.update(mtime=None, pfad="")
    from belegung import zimmerplan as zp

    yield zp.laden()
    aenderungen.verlauf_leeren()


def _datei(pfad, zeilen, kopf=KOPF):
    wb = Workbook()
    ws = wb.active
    ws.append(kopf)
    for z in zeilen:
        ws.append(z)
    wb.save(pfad)
    return pfad


def _zimmer(stand):
    return next(z for z in stand.zimmer if z.aktiv and "-" in z.kurz)


def test_spalten_deutsch_englisch_und_abweichende_fragen():
    sp = qm.spalten_finden(KOPF)
    assert (sp["id"], sp["start"], sp["ende"], sp["zimmer"], sp["art"], sp["text"]) == (0, 1, 2, 5, 6, 7)
    en = qm.spalten_finden(["Id", "Start time", "Completion time", "Email", "Name", "Room number", "What happened?"])
    assert en["zimmer"] == 5 and en["text"] == 6
    anders = qm.spalten_finden(["ID", "Startzeit", "Fertigstellungszeit", "Zimmernummer", "Was ist kaputt?", "Erzähl uns mehr"])
    assert anders["zimmer"] == 3 and anders["art"] == 4 and anders["text"] == 5


@pytest.mark.parametrize("text,art", [
    ("Die Heizung wird nicht warm", "heizung"), ("Rauchmelder piept", "rauchmelder"), ("Es riecht nach Rauch", "geruch"),
    ("Dusche läuft nicht ab", "abfluss"), ("Licht im Flur kaputt", "elektrik"), ("Lampe im Bad flackert", "elektrik"), ("WC-Spülung defekt", "bad"), ("Teppich ist voller Flecken", "boden_dreckig"),
    ("Schrank Tür hängt", "tuer"), ("Rollo klemmt", "fenster"), ("Bitte mal putzen", "grundreinigung"), ("Hallo", "sonstiges"),
])
def test_art_vorschlag(text, art):
    assert qm.art_vorschlag(text) == art


def test_zimmer_erkennen(stand):
    from modern.kern import _zimmer_aus_text

    z = _zimmer(stand)
    f = lambda t: _zimmer_aus_text(stand, t)                        # noqa: E731
    assert qm.zimmer_finden(z.kurz, f) == z.id
    assert qm.zimmer_finden(f"Zimmer {z.kurz}, Haus", f) == z.id
    if "." not in z.kurz:
        assert qm.zimmer_finden(z.kurz.replace("-", ""), f) == z.id
    assert qm.zimmer_finden("weiß nicht", f) == "" and qm.zimmer_finden("", f) == ""


def test_link_je_zimmer():
    v = "https://forms.office.com/Pages/ResponsePage.aspx?id=Beispiel&rAbc=%22ZIMMER%22"
    assert qm.zimmer_link(v, "3.2-111") == "https://forms.office.com/Pages/ResponsePage.aspx?id=Beispiel&rAbc=%223.2-111%22"
    assert qm.zimmer_link("https://forms.office.com/r/ohne", "2-101") == "https://forms.office.com/r/ohne"


def test_einlesen_genau_einmal_und_nur_bei_aenderung(stand, tmp_path):
    z = _zimmer(stand)
    p = _datei(tmp_path / "antworten.xlsx", [
        [1, datetime(2026, 11, 18, 9, 0), datetime(2026, 11, 18, 9, 2), "anonymous", None, z.kurz, "Heizung", "kalt"],
        [2, datetime(2026, 11, 18, 10, 0), datetime(2026, 11, 18, 10, 1), "anonymous", None, "irgendwo", "", "Lampe kaputt"],
    ])
    neu, fehler = qm.einlesen(str(p))
    assert fehler == "" and len(neu) == 2
    assert qm.einlesen(str(p)) == ([], "")                           # unverändert → nicht gelesen
    neu, _ = qm.einlesen(str(p), immer=True)
    assert neu == []                                                  # gelesen, aber nichts doppelt
    ms = {m.zimmer_text: m for m in qm.neue()}
    assert ms[z.kurz].zimmer == z.id and ms[z.kurz].art == "heizung" and ms[z.kurz].dringend
    assert ms["irgendwo"].zimmer == "" and ms["irgendwo"].art == "elektrik"
    assert ms[z.kurz].zeit_text == "18.11. 09:02"


def test_fehlende_spalten_und_datei(stand, tmp_path):
    p = _datei(tmp_path / "falsch.xlsx", [[1, "x"]], kopf=["ID", "Frage 1"])
    p2 = _datei(tmp_path / "ohne_id.xlsx", [["2-101"]], kopf=["Zimmer"])
    assert "Zimmer" in qm.einlesen(str(p))[1]
    assert "ID" in qm.einlesen(str(p2))[1]
    assert "nicht gefunden" in qm.einlesen(str(tmp_path / "fehlt.xlsx"))[1]


def test_uebernehmen_legt_mangel_an_mit_rueckgaengig(stand, tmp_path):
    from belegung import aenderungen
    from belegung import maengel as mg

    z = _zimmer(stand)
    p = _datei(tmp_path / "a.xlsx", [[7, datetime(2026, 11, 18, 8), datetime(2026, 11, 18, 8, 5), "", "", z.kurz,
                                       "", "Wasserhahn tropft"]])
    qm.einlesen(str(p))
    m = qm.neue()[0]
    assert m.art == "wasser"
    text = qm.uebernehmen(m.id, "wasser", m.zimmer, date(2026, 11, 18))
    assert "Mangel angelegt" in text
    offen = mg.offen(z.id)
    assert [x.art for x in offen] == ["wasser"] and "Wasserhahn tropft" in offen[0].notiz and "QR-Meldung" in offen[0].notiz
    assert qm.neue() == [] and qm.meldungen("uebernommen")[0].art == "wasser"
    with pytest.raises(ValueError, match="schon bearbeitet"):
        qm.uebernehmen(m.id, "wasser", m.zimmer)
    aenderungen.rueckgaengig()
    assert mg.offen(z.id) == [] and len(qm.neue()) == 1               # ein Schritt: Mangel UND Status zurück


def test_uebernehmen_braucht_zimmer_und_art_verwerfen(stand, tmp_path):
    p = _datei(tmp_path / "a.xlsx", [[8, "18.11.2026 08:00:00", "18.11.2026 08:01:00", "", "", "??", "", "Fenster"]])
    qm.einlesen(str(p))
    m = qm.neue()[0]
    with pytest.raises(ValueError, match="Zimmer"):
        qm.uebernehmen(m.id, "fenster", "")
    with pytest.raises(ValueError, match="Mangelart"):
        qm.uebernehmen(m.id, "gibtsnicht", "GS-2-101")
    assert qm.verwerfen(m.id) == "Meldung verworfen" and qm.neue() == []
    assert qm.meldungen("verworfen")[0].zeit == "2026-11-18T08:01"


def test_windows_meldung_je_pc_nur_einmal(stand, tmp_path):
    p = _datei(tmp_path / "a.xlsx", [[9, datetime(2026, 11, 18, 8), None, "", "", "x", "", "Heizung"]])
    qm.einlesen(str(p))
    assert len(qm.noch_nicht_gemeldet()) == 1
    assert qm.noch_nicht_gemeldet() == []


def test_link_und_antwortdatei_pruefen(stand, tmp_path):
    with pytest.raises(ValueError, match="https"):
        qm.link_setzen("forms.office.com/x")
    assert "Zimmernummer" in qm.link_setzen("https://forms.office.com/r/x?a=ZIMMER")
    assert qm.link() == "https://forms.office.com/r/x?a=ZIMMER"
    assert "dasselbe Formular" in qm.link_setzen("https://forms.office.com/r/x")
    with pytest.raises(ValueError, match="xlsx"):
        qm.antwortdatei_setzen(str(tmp_path / "a.csv"))
    with pytest.raises(ValueError, match="gibt es auf diesem PC nicht"):
        qm.antwortdatei_setzen(str(tmp_path / "fehlt.xlsx"))
    p = _datei(tmp_path / "ok.xlsx", [])
    qm.antwortdatei_setzen(f'"{p}"')                                  # „Als Pfad kopieren“ setzt Anführungszeichen
    assert qm.antwortdatei() == str(p)


def test_etiketten_druckbogen():
    from tests.test_maengel_v128_qr_code import decodieren
    import re

    from modern import qr_kern

    html = qm.etiketten_html("https://forms.office.com/r/x?z=ZIMMER", [("GS-2-101", "2-101"), ("GS-3.2-111", "3.2-111")])
    assert html.count("<svg") == 2 and "2-101" in html and "3.2-111" in html
    assert decodieren(qr_kern.matrix(qm.zimmer_link("https://forms.office.com/r/x?z=ZIMMER", "3.2-111"))) \
        == "https://forms.office.com/r/x?z=3.2-111"
    assert re.search(r"Etwas kaputt", html)
    with pytest.raises(ValueError, match="Forms-Link"):
        qm.etiketten_html("", [("GS-2-101", "2-101")])
