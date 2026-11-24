"""1.56: Belegungsplan – „Frei“-Heatmap (welche Zimmer sind in den nächsten Monaten frei), Datum wählen, Legenden."""

from datetime import date
from pathlib import Path
from types import SimpleNamespace

from belegung import zimmerplan as zp
from modern import frei_kern as fr

MO = date(2026, 11, 23)      # Montag


class _Lage:
    def __init__(self, zimmer, bel):
        self.zimmer = {z.id: z for z in zimmer}
        self.belegungen = bel

    def status_am(self, zid, tag):
        heute = [b for b in self.belegungen.get(zid, []) if b.von <= tag <= b.bis]
        if any(b.art == "gesperrt" for b in heute):
            return "gesperrt", heute
        p = [b for b in heute if b.art in ("belegt", "geplant")]
        return ("frei" if not p else "teilweise" if len(p) < self.zimmer[zid].betten else "belegt"), heute


def _z(zid, kurz, betten=1, haus="2"):
    return SimpleNamespace(id=zid, kurz=kurz, haus=haus, etage="1", flur="West", betten=betten, aktiv=True, gaeste=False)


def _stand(zimmer, bel):
    return SimpleNamespace(zimmer=zimmer, lage=_Lage(zimmer, bel))


def _b(zid, von, bis, art="belegt", name="Beispiel, Erika", gruppe="UWT"):
    return zp.Belegung(zid, von, bis, art, name, gruppe)


def test_stufen_und_frei_ab(monkeypatch):
    monkeypatch.setattr(zp, "flur_text", lambda z: "Haus 2 · 1. OG")
    zs = [_z("A", "2-101"), _z("B", "2-102", betten=2), _z("C", "2-103")]
    bel = {"A": [_b("A", date(2026, 11, 1), date(2026, 12, 13))],                 # belegt bis So 13.12.
           "B": [_b("B", date(2026, 11, 1), date(2027, 6, 1))],                   # 1 von 2 Betten belegt
           "C": [_b("C", date(2026, 11, 1), date(2027, 6, 1), art="gesperrt", name="Renovierung")]}
    r = {x.kurz: x for x in fr.raster(_stand(zs, bel), MO + date.resolution * 2, 6)}
    a = r["2-101"]
    assert [c.stufe for c in a.zellen] == ["voll", "voll", "voll", "frei", "frei", "frei"]
    assert a.ganz_frei_ab == date(2026, 12, 14) and a.ganz_frei_tage == 21
    assert a.text == "ganz frei ab 14.12., 3 Wochen"
    b = r["2-102"]
    assert all(c.stufe == "teil" for c in b.zellen) and b.ganz_frei_ab is None
    assert b.frei_ab == MO and b.text.startswith("1 Bett frei ab 23.11.")
    c = r["2-103"]
    assert all(x.stufe == "sperr" for x in c.zellen) and c.text == "im Zeitraum nicht frei"
    s = fr.zusammenfassung(list(r.values()))
    assert s == {"jetzt": 0, "spaeter": 2, "nie": 1}


def test_sortieren_filtern(monkeypatch):
    monkeypatch.setattr(zp, "flur_text", lambda z: "Haus 2 · 1. OG")
    zs = [_z("A", "2-101"), _z("B", "2-102"), _z("C", "2-103")]
    bel = {"A": [_b("A", MO, date(2026, 12, 6))], "B": [], "C": [_b("C", MO, date(2027, 6, 1))]}
    zeilen = fr.raster(_stand(zs, bel), MO, 8)
    assert [r.kurz for r in fr.sortieren(zeilen, "frueh")] == ["2-102", "2-101", "2-103"]
    assert [r.kurz for r in fr.sortieren(zeilen, "lang")][0] == "2-102"
    assert [r.kurz for r in fr.filtern(zeilen, True)] == ["2-101", "2-102"]
    assert [r.kurz for r in fr.filtern(zeilen, True, 7)] == ["2-102"]          # 6 Wochen am Stück reichen nicht für 7


def test_haus_und_unbewohnbar(monkeypatch):
    monkeypatch.setattr(zp, "flur_text", lambda z: "Haus 2 · 1. OG")
    zs = [_z("A", "2-101"), _z("D", "3-101", haus="3")]
    assert [r.kurz for r in fr.raster(_stand(zs, {}), MO, 2, haus="3")] == ["3-101"]
    r = fr.raster(_stand(zs, {}), MO, 2, unbewohnbar={"A"})
    assert all(c.stufe == "sperr" for c in r[0].zellen)


def test_oberflaeche():
    q = (Path(fr.__file__).parent / "seiten.py").read_text(encoding="utf-8")
    assert '"frei": "Frei"' in q and "_frei_zeichnen" in q and "_datum_waehlen" in q
    assert "m-hm-legende" in q          # ausführliche Legende für Flure und Frei


def test_kurze_luecke_zaehlt_nicht_und_ab_heute(monkeypatch):
    monkeypatch.setattr(zp, "flur_text", lambda z: "Haus 2 · 1. OG")
    zs = [_z("A", "2-101")]
    bel = {"A": [_b("A", date(2026, 11, 1), date(2026, 11, 30)),              # Lücke 01.–03.12. (3 Tage)
                 _b("A", date(2026, 12, 4), date(2027, 1, 10))]}
    r = fr.raster(_stand(zs, bel), MO, 12)[0]
    assert r.ganz_frei_ab == date(2027, 1, 11)                                 # erst die lange Strecke zählt
    assert r.strecken[0] == (date(2026, 12, 1), 3)
    leer = fr.raster(_stand(zs, {}), MO, 2, ab=date(2026, 11, 26))[0]
    assert leer.ganz_frei_ab == date(2026, 11, 26) and leer.ganz_frei_tage == 11
    assert leer.zellen[0].stufe == "frei"                                    # die Heatmap zeigt die ganze Woche
