"""1.50 – Gast bearbeiten/entfernen, Programmsymbol aus dem Logo (nicht im Repository), Ersteller sichtbar.
Erfundene Namen; das Symbol ist ein selbst erzeugtes Test-PNG."""

import struct
import zlib
from datetime import date
from pathlib import Path

import pytest


@pytest.fixture
def goslar(tmp_path, monkeypatch):
    from belegung import aenderungen
    from modern import kern, standort_kern  # noqa: F401

    monkeypatch.setenv("BELEGUNG_DATEN", str(tmp_path))
    aenderungen.verlauf_leeren()
    standort_kern.waehlen("GS", merken_=False)
    yield tmp_path
    aenderungen.verlauf_leeren()


VON, BIS = date(2027, 5, 3), date(2027, 5, 7)


def _paar():
    from modern import gaeste_kern as gk

    zid = next(iter(gk.zimmer_frei(VON, BIS, zu_zweit=True)))
    gk.anlegen("Beispiel, Erika", VON, BIS, "w", "Hospitation", True, "Musterhoff, Alex", "m", zid)
    return zid


def test_bearbeiten_zieht_die_begleitung_mit(goslar):
    from belegung import zimmerplan as zp
    from modern import gaeste_kern as gk

    zid = _paar()
    g = next(x for x in gk.liste(zp.laden(), VON) if x.name == "Beispiel, Erika")
    neu_bis = date(2027, 5, 9)
    text = gk.bearbeiten(g.schluessel, "Beispiel, Erika", VON, neu_bis, "w", "Hospitation Pflege", True, None)
    assert "Musterhoff" in text
    zeilen = {x.name: x for x in gk.liste(zp.laden(), VON)}
    assert zeilen["Beispiel, Erika"].bis == neu_bis and zeilen["Musterhoff, Alex"].bis == neu_bis
    assert zeilen["Beispiel, Erika"].zimmer == zid == zeilen["Musterhoff, Alex"].zimmer
    assert zeilen["Beispiel, Erika"].bemerkung == "Hospitation Pflege"


def test_umbenennen_und_zimmer_wechseln(goslar):
    from belegung import zimmerplan as zp
    from modern import gaeste_kern as gk

    gk.anlegen("Allein, Kim", VON, BIS, "", "", False, "", "", "")
    s = gk.liste(zp.laden(), VON)[0].schluessel
    ziel = next(iter(gk.zimmer_frei(VON, BIS, doppelzimmer=True)))
    gk.bearbeiten(s, "Allein-Neu, Kim", VON, BIS, "d", "", True, ziel)
    g = gk.liste(zp.laden(), VON)[0]
    assert g.name == "Allein-Neu, Kim" and g.zimmer == ziel and g.dz_wunsch
    assert zp.angaben_laden()[g.schluessel]["geschlecht"] == "d"
    gk.bearbeiten(g.schluessel, g.name, VON, BIS, "d", "", True, "")      # Zimmer freigeben
    assert gk.liste(zp.laden(), VON)[0].zimmer == ""


def test_paar_trennen_und_entfernen(goslar):
    from belegung import zimmerplan as zp
    from modern import gaeste_kern as gk

    _paar()
    zeilen = {x.name: x for x in gk.liste(zp.laden(), VON)}
    gk.bearbeiten(zeilen["Beispiel, Erika"].schluessel, "Beispiel, Erika", VON, BIS, "w", "", False, None)
    zeilen = {x.name: x for x in gk.liste(zp.laden(), VON)}
    assert zeilen["Beispiel, Erika"].begleitung == "" and zeilen["Musterhoff, Alex"].begleitung == ""
    assert "entfernt" in gk.entfernen(zeilen["Musterhoff, Alex"].schluessel)
    assert [x.name for x in gk.liste(zp.laden(), VON)] == ["Beispiel, Erika"]


def _png(groesse=256) -> bytes:
    roh = b"".join(b"\x00" + b"\x00\x80\x80\xff" * groesse for _ in range(groesse))
    def block(art, daten):
        return struct.pack(">I", len(daten)) + art + daten + struct.pack(">I", zlib.crc32(art + daten) & 0xFFFFFFFF)
    return (b"\x89PNG\r\n\x1a\n" + block(b"IHDR", struct.pack(">IIBBBBB", groesse, groesse, 8, 6, 0, 0, 0))
            + block(b"IDAT", zlib.compress(roh)) + block(b"IEND", b""))


def test_symbol_aus_dem_datenordner(goslar, tmp_path):
    from modern import icon_kern as ik

    assert ik.finden() is None or ik.finden().name in (ik.ICON_DATEI, ik.LOGO_DATEI)
    (goslar / ik.ICON_DATEI).write_bytes(_png())
    assert ik.finden() == goslar / ik.ICON_DATEI
    ico = ik.ico_aus_png(_png())
    assert ico[:6] == struct.pack("<HHH", 0, 1, 1) and ico[6] == 0 and ico[22:30] == b"\x89PNG\r\n\x1a\n"
    assert ik.ico_aus_png(_png(32))[6] == 32
    with pytest.raises(ValueError):
        ik.ico_aus_png(b"kein bild")
    lokal = tmp_path / "lokal"
    assert ik.windows_einrichten(lokal)                       # neu geschrieben
    assert ik.windows_einrichten(lokal) == ""                 # unverändert → nichts zu tun
    assert (lokal / ik.ICO_DATEI).read_bytes() == ico


def test_ersteller_sichtbar_und_logo_nicht_im_programm():
    from modern import impressum

    assert impressum.AUTOR and impressum.AUTOR in impressum.zeile() and impressum.AUTOR in impressum.kurz()
    wurzel = Path(__file__).parents[1]
    assert "impressum.kurz()" in (wurzel / "modern" / "menueband_ui.py").read_text(encoding="utf-8")
    assert "_ueber()" in (wurzel / "modern" / "seite_einstellungen.py").read_text(encoding="utf-8")
    assert not list(wurzel.rglob("INNternat_Logo.png")) and not list(wurzel.rglob("INNternat_Icon.png"))
    q = (wurzel / "modern" / "seiten.py").read_text(encoding="utf-8")
    assert "def gast_bearbeiten_panel" in q and "Gast entfernen" in q
