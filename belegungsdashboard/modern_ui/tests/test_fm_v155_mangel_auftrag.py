"""1.55: Mail an FM zu einem Mangel – vollständiger Auftrag (Zimmer, Lage, Mangel, Dringlichkeit, gemeldet am,
Beschreibung, Zimmer heute, nächste Anreise als Frist), ohne Namen von Bewohnern; Klick zeigt Fehler statt still."""

from datetime import date
from pathlib import Path
from types import SimpleNamespace

from belegung import maengel as mg
from belegung import zimmerplan as zp
from modern import zimmer_kern as zk

HEUTE = date(2026, 11, 24)


class _Lage:
    def __init__(self, belegungen):
        self.zimmer = {"GS-2-108": SimpleNamespace(kurz="2-108", haus="2", etage="1", betten=2)}
        self.belegungen = {"GS-2-108": belegungen}

    def status_am(self, zid, tag):
        heute = [b for b in self.belegungen.get(zid, []) if b.von <= tag <= b.bis]
        if any(b.art == "gesperrt" for b in heute):
            return "gesperrt", heute
        p = [b for b in heute if b.art in ("belegt", "geplant")]
        return ("frei" if not p else "teilweise" if len(p) < 2 else "belegt"), heute


def _stand(belegungen):
    return SimpleNamespace(lage=_Lage(belegungen))


def _mangel(monkeypatch, notiz="Fenstergriff lose", art="heizung"):
    m = mg.Mangel("GS-2-108", art, date(2026, 11, 20), notiz=notiz)
    monkeypatch.setattr(mg, "offen", lambda zimmer=None: [m] if zimmer in (None, "GS-2-108") else [])
    monkeypatch.setattr(zp, "flur_text", lambda z: "Haus 2 · 1. OG")
    return m


def test_auftrag_enthaelt_alles_fuer_fm(monkeypatch):
    _mangel(monkeypatch)
    bel = [zp.Belegung("GS-2-108", date(2026, 11, 1), date(2026, 11, 27), "belegt", "Beispiel, Erika", "UWT"),
           zp.Belegung("GS-2-108", date(2026, 12, 1), date(2026, 12, 20), "geplant", "Musterhoff, Kim", "UWT")]
    betreff, text = zk.fm_auftrag(_stand(bel), "GS-2-108", "heizung", HEUTE, "Alex")
    assert betreff == "FM-Auftrag: Zimmer 2-108 – Heizung defekt (dringend), bis 01.12."
    for teil in ("Zimmer: 2-108 (Haus 2 · 1. OG)", "Mangel: Heizung defekt", "Dringlichkeit: Dringend",
                 "Gemeldet am: 20.11.2026 (seit 4 Tagen offen)", "Beschreibung: Fenstergriff lose",
                 "Zimmer heute: 1 Bett frei bis 27.11.2026", "Nächste Anreise: 01.12.2026 – bitte bis dahin erledigen"):
        assert teil in text, teil
    assert text.rstrip().endswith("Alex")
    assert "Erika" not in text and "Musterhoff" not in text        # keine Bewohnernamen an FM


def test_ohne_belegung_und_ohne_notiz(monkeypatch):
    _mangel(monkeypatch, notiz="", art="sonstiges")
    betreff, text = zk.fm_auftrag(_stand([]), "GS-2-108", "sonstiges", HEUTE)
    assert betreff.startswith("FM-Auftrag: Zimmer 2-108 – Sonstiges (leicht)") and ", bis" not in betreff
    assert "Zimmer heute: frei" in text and "Nächste Anreise: keine geplant" in text
    assert "Beschreibung" not in text


def test_unbewohnbar_wird_genannt(monkeypatch):
    m = _mangel(monkeypatch, art="schimmel")
    assert m.unbewohnbar
    _b, text = zk.fm_auftrag(_stand([]), "GS-2-108", "schimmel", HEUTE)
    assert "Dringlichkeit: Nicht bewohnbar – Zimmer ist gesperrt" in text


def test_mangel_schon_behoben_gibt_trotzdem_text(monkeypatch):
    monkeypatch.setattr(mg, "offen", lambda zimmer=None: [])
    monkeypatch.setattr(zp, "flur_text", lambda z: "Haus 2 · 1. OG")
    betreff, text = zk.fm_auftrag(_stand([]), "GS-2-108", "heizung", HEUTE)
    assert "Heizung" in betreff and "Zimmer: 2-108" in text


def test_klick_ist_abgesichert_und_nutzt_art():
    src = Path(zk.__file__).with_name("seite_zimmer.py").read_text(encoding="utf-8")
    assert "async def _fm_mangel(a, zimmer: str, art: str)" in src
    assert "Mail an FM konnte nicht geöffnet werden" in src
    assert "_fm_mangel(a, z.zimmer, art)" in src and "_fm_mangel(a, k.zimmer, art)" in src
    heute = Path(zk.__file__).with_name("seite_heute.py").read_text(encoding="utf-8")
    assert "FM_WARTEN" in heute and "Outlook antwortet nicht" in heute and "Text kopieren" in heute


def test_sammelmail_mehrere_maengel(monkeypatch):
    ms = [mg.Mangel("GS-2-108", "sonstiges", date(2026, 11, 24), notiz="Fenstergriff lose"),
          mg.Mangel("GS-2-108", "heizung", date(2026, 11, 20))]
    monkeypatch.setattr(mg, "offen", lambda zimmer=None: [m for m in ms if zimmer in (None, m.zimmer)])
    monkeypatch.setattr(zp, "flur_text", lambda z: "Haus 2 · 1. OG")
    bel = [zp.Belegung("GS-2-108", date(2026, 12, 1), date(2026, 12, 20), "geplant", "Musterhoff, Kim", "UWT")]
    betreff, text = zk.fm_sammelauftrag(_stand(bel), [("GS-2-108", "sonstiges"), ("GS-2-108", "heizung"),
                                                      ("GS-2-108", "heizung")], HEUTE, "Alex")
    assert betreff == "FM-Sammelauftrag: 2 Mängel in 1 Zimmer (1 dringend), erste Frist 01.12."
    assert "1. Zimmer 2-108 – Heizung defekt (dringend), bis 01.12." in text      # dringend zuerst
    assert "2. Zimmer 2-108 – Sonstiges (leicht), bis 01.12." in text
    assert "--- 1. Zimmer 2-108 (Haus 2 · 1. OG) – Heizung defekt ---" in text
    assert "Beschreibung: Fenstergriff lose" in text and "Musterhoff" not in text
    assert text.rstrip().endswith("Alex")


def test_sammelmail_ein_eintrag_und_leer(monkeypatch):
    _mangel(monkeypatch)
    b1, _ = zk.fm_sammelauftrag(_stand([]), [("GS-2-108", "heizung")], HEUTE)
    assert b1.startswith("FM-Auftrag: Zimmer 2-108")
    import pytest
    with pytest.raises(ValueError):
        zk.fm_sammelauftrag(_stand([]), [], HEUTE)


def test_sammelmail_knopf_und_markierung():
    src = Path(zk.__file__).with_name("seite_zimmer.py").read_text(encoding="utf-8")
    assert "Sammelmail an FM" in src and "a.dz_auswahl" in src and "_fm_sammel(a," in src
    assert "dz_auswahl" in Path(zk.__file__).with_name("oberflaeche.py").read_text(encoding="utf-8")
