"""1.32 – QR-Meldungen über Power Automate: je Forms-Antwort eine Mail mit festem Aufbau, INNternat liest den
Outlook-Ordner (hier ohne Outlook: das Lesen wird ersetzt). Erfundene Daten."""

from datetime import datetime

import pytest

from modern import qr_meldungen_kern as qm

LINK = "https://forms.office.com/r/demo?a=ZIMMER&b=CODE"


@pytest.fixture
def stand(tmp_path, monkeypatch):
    from belegung import aenderungen
    from modern import kern, standort_kern  # noqa: F401

    monkeypatch.setenv("BELEGUNG_DATEN", str(tmp_path / "daten"))
    (tmp_path / "daten").mkdir()
    aenderungen.verlauf_leeren()
    standort_kern.waehlen("GS", merken_=False)
    qm._STAND.update(mtime=None, pfad="", gelesen=None, fehler="", neu=0)
    from belegung import zimmerplan as zp

    yield zp.laden()
    aenderungen.verlauf_leeren()


def _mail(rid, zimmer, code, art="", text="", zeit="2026-11-19T07:01:23.1234567Z"):
    return (f"INNTERNAT-QR\nID: {rid}\nZeit: {zeit}\nZimmer: {zimmer}\nCode: {code}\nArt: {art}\n"
            f"Beschreibung: {text}\nENDE\n\n-- Diese Mail wurde automatisch erstellt.")


def test_mail_parsen_fester_aufbau():
    r = qm.mail_parsen("INNternat-QR | 2-408 | ABCDE", _mail("17", "2-408", "ABCDE", "Heizung", "kalt"))
    assert (r.id, r.zimmer_text, r.code, r.art_text, r.text) == ("pa|17", "2-408", "ABCDE", "Heizung", "kalt")
    assert r.zeit.startswith("2026-11-19T")                    # UTC → Ortszeit, Minutengenau
    assert len(r.zeit) == 16


def test_mail_parsen_mehrzeilig_html_und_grossklein():
    html = ("<p>INNTERNAT-QR</p><p>id: 5</p><p>ZIMMER: 1-101</p><p>code:</p><p>Art: </p>"
            "<p>Beschreibung: Wasserhahn tropft</p><p>seit gestern&nbsp;Abend</p><p>ENDE</p><p>Zimmer: 9-999</p>")
    r = qm.mail_parsen("", html, empfangen=datetime(2026, 11, 19, 9, 30))
    assert r.zimmer_text == "1-101" and r.code == "" and r.text == "Wasserhahn tropft\nseit gestern Abend"
    assert r.zeit == "2026-11-19T09:30"                          # keine Zeit → Empfangszeit


def test_andere_mails_werden_ignoriert():
    assert qm.mail_parsen("Anfrage Zimmer", "Zimmer: 2-408\nBeschreibung: bitte melden") is None
    assert qm.mail_parsen("INNternat-QR", "INNTERNAT-QR\nnichts") is None


def test_zeitformate_aus_power_automate():
    assert qm._pa_zeit("11/19/2026 8:01:23 AM") == "2026-11-19T08:01"
    assert qm._pa_zeit("19.11.2026 08:01") == "2026-11-19T08:01"
    assert qm._pa_zeit("2026-11-19T08:01:00") == "2026-11-19T08:01"
    assert qm._pa_zeit("Quatsch") == ""


def test_einlesen_aus_outlook_genau_einmal_mit_pruefcode(stand, monkeypatch):
    zs = [z for z in stand.zimmer if z.aktiv and "-" in z.kurz]
    z1, z2 = zs[0], zs[1]
    qm.link_setzen(LINK)
    c1 = qm.code_fuer(z1.id, qm.geheim())
    mails = [qm.mail_parsen("", _mail("1", z1.kurz, c1, "Heizung", "kalt")),
             qm.mail_parsen("", _mail("2", z2.kurz, c1, "", "Lampe"))]      # Zimmer geändert, Etikett z1
    gelesen = []
    monkeypatch.setattr(qm, "outlook_lesen", lambda o, anzahl=300: gelesen.append(o) or qm.Ergebnis(list(mails)))
    neu, fehler = qm.einlesen("", ordner="Posteingang/QR-Meldungen")
    assert fehler == "" and len(neu) == 2 and gelesen == ["Posteingang/QR-Meldungen"]
    m = {x.text: x for x in qm.neue()}
    assert m["kalt"].zimmer == z1.id and m["kalt"].art == "heizung"
    assert m["Lampe"].zimmer == z1.id and "geändert" in m["Lampe"].hinweis
    assert qm.einlesen("", ordner="Posteingang/QR-Meldungen") == ([], "")    # dieselben Mails → nichts Neues
    assert len(qm.neue()) == 2


def test_outlook_fehler_wird_gemeldet_und_angezeigt(stand, monkeypatch):
    monkeypatch.setattr(qm, "outlook_lesen", lambda o, anzahl=300: qm.Ergebnis(fehler="Outlook ist nicht geöffnet"))
    assert qm.einlesen("", ordner="X") == ([], "Outlook ist nicht geöffnet")
    qm.outlook_ordner_setzen("Posteingang/QR-Meldungen")
    p = {x.titel: x for x in qm.diagnose()}
    assert p["Outlook-Ordner"].stufe == "krit"
    assert p["Antwortdatei"].stufe == "info"                       # mit Outlook-Ordner ist keine Datei nötig
    assert p["Letztes Einlesen"].stufe == "krit"


def test_diagnose_zaehlt_qr_mails(stand, monkeypatch):
    qm.outlook_ordner_setzen("Posteingang/QR-Meldungen")
    monkeypatch.setattr(qm, "outlook_lesen", lambda o, anzahl=300: qm.Ergebnis())
    assert {x.titel: x for x in qm.diagnose()}["QR-Mails"].stufe == "warn"
    monkeypatch.setattr(qm, "outlook_lesen",
                        lambda o, anzahl=300: qm.Ergebnis([qm.mail_parsen("", _mail("9", "1-101", ""))]))
    p = {x.titel: x for x in qm.diagnose()}
    assert p["Outlook-Ordner"].stufe == "ok" and "1 noch nicht eingelesen" in p["QR-Mails"].text
