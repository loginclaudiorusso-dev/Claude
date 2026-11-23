"""1.44 – QR-Meldungen ohne Mail-Verbindung: Power Automate legt je Forms-Antwort eine Textdatei in einen OneDrive-
Ordner, INNternat liest den Ordner. Erfundene Daten."""

import pytest

from modern import qr_meldungen_kern as qm

INHALT = "INNTERNAT-QR\nID: {rid}\nZeit: 2026-11-23T13:41:54Z\nZimmer: {zimmer}\nCode: {code}\nArt: [\"Heizung\"]\n" \
         "Beschreibung: {text}\nENDE\n"


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


def _datei(ordner, rid, zimmer, code="", text="kalt", kodierung="utf-8-sig"):
    (ordner / f"qr-{rid}.txt").write_bytes(INHALT.format(rid=rid, zimmer=zimmer, code=code, text=text).encode(kodierung))


def test_ordner_lesen_formate_und_fremdes(tmp_path):
    o = tmp_path / "OneDrive - Demo" / "INNternat-QR"
    o.mkdir(parents=True)
    _datei(o, "1", "2-101", text="Heizung rauscht")
    _datei(o, "2", "2-102", text="Tür klemmt", kodierung="utf-16")
    _datei(o, "3", "2-103", text="Fenster zieht – kälter", kodierung="cp1252")
    (o / "notiz.txt").write_text("Irgendwas anderes", encoding="utf-8")
    (o / "qr-4.docx").write_bytes(b"x")
    erg = qm.ordner_lesen(str(o))
    assert erg.fehler == ""
    m = {r.id: r for r in erg.zeilen}
    assert set(m) == {"pa|1", "pa|2", "pa|3"}               # dieselbe ID wie per Mail – kein Doppel beim Wechsel
    assert m["pa|1"].art_text == "Heizung" and m["pa|2"].text == "Tür klemmt" and "kälter" in m["pa|3"].text
    assert qm.ordner_lesen(str(tmp_path / "fehlt")).fehler.startswith("QR-Ordner nicht gefunden")


def test_einlesen_aus_ordner_genau_einmal(stand, tmp_path):
    z = next(z for z in stand.zimmer if z.aktiv and "-" in z.kurz)
    o = tmp_path / "OneDrive - Demo" / "INNternat-QR"
    o.mkdir(parents=True)
    _datei(o, "7", z.kurz)
    neu, fehler = qm.einlesen("", ordner="", dateien=str(o))
    assert fehler == "" and len(neu) == 1 and neu[0].zimmer == z.id
    assert qm.einlesen("", ordner="", dateien=str(o)) == ([], "")
    _datei(o, "8", z.kurz, text="Lampe")
    assert len(qm.einlesen("", ordner="", dateien=str(o))[0]) == 1


def test_einstellung_und_diagnose(stand, tmp_path):
    with pytest.raises(ValueError):
        qm.dateiordner_setzen(str(tmp_path / "gibt_es_nicht"))
    o = tmp_path / "OneDrive - Demo" / "INNternat-QR"
    o.mkdir(parents=True)
    assert "gespeichert" in qm.dateiordner_setzen(f'"{o}"')
    assert qm.dateiordner() == str(o)
    p = {x.titel: x for x in qm.diagnose()}
    assert p["QR-Ordner"].stufe == "ok" and p["QR-Dateien"].stufe == "warn"
    assert p["Antwortdatei"].stufe == "info" and "OneDrive" in p["Antwortdatei"].text
    _datei(o, "9", "1-101")
    assert "1 noch nicht eingelesen" in {x.titel: x for x in qm.diagnose()}["QR-Dateien"].text
    assert qm.dateiordner_setzen("") == "QR-Ordner entfernt"
