"""1.30 – Prüfcode auf dem QR-Etikett: zeigt, ob ein Gast die vorausgefüllte Zimmernummer geändert hat. Erfundene Daten."""

from datetime import datetime

import pytest
from openpyxl import Workbook

from modern import qr_meldungen_kern as qm

KOPF = ["ID", "Startzeit", "Fertigstellungszeit", "E-Mail", "Name", "Zimmer", "Art des Problems", "Beschreibung",
        "Code (bitte nicht ändern)"]
LINK = "https://forms.office.com/Pages/ResponsePage.aspx?id=Demo&rA=%22ZIMMER%22&rB=%22CODE%22"


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


def _datei(pfad, zeilen):
    wb = Workbook()
    ws = wb.active
    ws.append(KOPF)
    for z in zeilen:
        ws.append(z)
    wb.save(pfad)
    return pfad


def _zwei(stand):
    zs = [z for z in stand.zimmer if z.aktiv and "-" in z.kurz]
    return zs[0], zs[1]


def test_code_fest_eindeutig_und_ohne_verwechselbare_zeichen(stand):
    g = "a" * 32
    ids = [z.id for z in stand.zimmer]
    codes = [qm.code_fuer(z, g) for z in ids]
    assert qm.code_fuer(ids[0], g) == codes[0] and qm.code_fuer(ids[0], "b" * 32) != codes[0]   # hängt am Geheimwert
    assert all(len(c) == 5 and not set(c) & set("01IO") for c in codes)
    assert len(qm.code_tabelle(ids, g)) >= len(ids) - 2                 # Dopplungen sind extrem selten
    assert qm.code_norm(" ab-c d ") == "ABCD"


def test_spalte_code_wird_erkannt_und_nicht_als_beschreibung_genommen():
    sp = qm.spalten_finden(KOPF)
    assert (sp["zimmer"], sp["art"], sp["text"], sp["code"]) == (5, 6, 7, 8)


def test_link_mit_zimmer_und_code():
    assert qm.zimmer_link(LINK, "2-101", "K7QXA").endswith("rA=%222-101%22&rB=%22K7QXA%22")
    assert "CODE" in qm.zimmer_link(LINK, "2-101")                     # ohne Code bleibt der Platzhalter


def test_etiketten_tragen_den_code(stand):
    from tests.test_maengel_v128_qr_code import decodieren

    from modern import qr_kern

    z, _ = _zwei(stand)
    qm.etiketten_html(LINK, [(z.id, z.kurz)])                          # legt den Geheimwert an
    g = qm.geheim()
    assert len(g) == 32 and qm.geheim() == g                           # bleibt gleich
    url = qm.zimmer_link(LINK, z.kurz, qm.code_fuer(z.id, g))
    assert decodieren(qr_kern.matrix(url)) == url and qm.code_fuer(z.id, g) in url


def test_einlesen_erkennt_geaenderte_zimmernummer(stand, tmp_path):
    z1, z2 = _zwei(stand)
    qm.link_setzen(LINK)
    g = qm.geheim()
    c1 = qm.code_fuer(z1.id, g)
    p = _datei(tmp_path / "a.xlsx", [
        [1, datetime(2026, 11, 19, 8), datetime(2026, 11, 19, 8, 1), "", "", z1.kurz, "Heizung", "kalt", c1],        # passt
        [2, datetime(2026, 11, 19, 9), datetime(2026, 11, 19, 9, 1), "", "", z2.kurz, "", "Lampe", c1.lower()],     # geändert
        [3, datetime(2026, 11, 19, 10), datetime(2026, 11, 19, 10, 1), "", "", z1.kurz, "", "Fenster", "ZZZZZ"],    # unbekannt
        [4, datetime(2026, 11, 19, 11), datetime(2026, 11, 19, 11, 1), "", "", z1.kurz, "", "Tür", ""],             # fehlt
    ])
    neu, fehler = qm.einlesen(str(p))
    assert fehler == "" and len(neu) == 4
    m = {x.text: x for x in qm.neue()}
    assert m["kalt"].zimmer == z1.id and m["kalt"].hinweis == "" and m["kalt"].etikett == z1.id
    assert m["Lampe"].zimmer == z1.id and m["Lampe"].etikett == z1.id                      # Etikett gewinnt
    assert "geändert" in m["Lampe"].hinweis and z2.kurz in m["Lampe"].hinweis and z1.kurz in m["Lampe"].hinweis
    assert "unbekannt" in m["Fenster"].hinweis and m["Fenster"].zimmer == z1.id
    assert "ohne Prüfcode" in m["Tür"].hinweis


def test_ohne_code_im_link_keine_hinweise(stand, tmp_path):
    z1, _ = _zwei(stand)
    qm.link_setzen("https://forms.office.com/r/x?z=ZIMMER")
    p = _datei(tmp_path / "b.xlsx", [[5, datetime(2026, 11, 19, 8), None, "", "", z1.kurz, "", "Tür", ""]])
    qm.einlesen(str(p))
    assert qm.neue()[0].hinweis == ""


def test_uebernehmen_nach_hinweis_wie_immer(stand, tmp_path):
    from belegung import maengel as mg

    z1, z2 = _zwei(stand)
    qm.link_setzen(LINK)
    c1 = qm.code_fuer(z1.id, qm.geheim())
    p = _datei(tmp_path / "c.xlsx", [[6, datetime(2026, 11, 19, 8), None, "", "", z2.kurz, "", "Wasserhahn tropft", c1]])
    qm.einlesen(str(p))
    m = qm.neue()[0]
    assert "Mangel angelegt" in qm.uebernehmen(m.id, m.art, m.zimmer)
    assert [x.art for x in mg.offen(z1.id)] == ["wasser"] and mg.offen(z2.id) == []
