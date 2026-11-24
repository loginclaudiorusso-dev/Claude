"""1.42 – Zimmerkacheln mit hohem Kontrast und Legende, Protokoll „Heute geändert“ im Cockpit (je Person, Klick zur
Stelle, falsche Meldungen ausblenden). Nur erfundene Namen."""

import contextlib
import inspect
from datetime import date, datetime

from modern import protokoll_kern as pk
from modern import seite_heute as sh
from modern import seite_zimmer as sz
from modern import themes


def _kontrast(a: str, b: str) -> float:
    def lum(h):
        r, g, bl = (int(h[i:i + 2], 16) / 255 for i in (1, 3, 5))
        f = lambda c: c / 12.92 if c <= .03928 else ((c + .055) / 1.055) ** 2.4    # noqa: E731
        return .2126 * f(r) + .7152 * f(g) + .0722 * f(bl)
    x, y = sorted((lum(a), lum(b)), reverse=True)
    return (x + .05) / (y + .05)


def test_kacheln_kraeftig_und_lesbar():
    css = themes.CSS
    for k in ("--zi-frei:", "--zi-belegt:", "--zi-geplant-rand:", "--zi-nn1:", "--zi-mangel1:"):
        assert k in css
    # Schrift auf belegt (weiß auf Blau) und frei (Dunkelgrün auf Hellgrün) gut lesbar – hell und dunkel
    assert _kontrast("#FFFFFF", "#1D5BB8") >= 4.5 and _kontrast("#173D07", "#D3EDC4") >= 7
    assert _kontrast("#FFFFFF", "#3D74C2") >= 4.5 and _kontrast("#EEF9E6", "#2D5A20") >= 4.5
    # frei und belegt unterscheiden sich deutlich (nicht nur im Farbton)
    assert _kontrast("#D3EDC4", "#1D5BB8") >= 3
    assert "body.pro .m-kachel.nn.unbew" in css and "body.pro .m-zi-legende" in css


def test_legende_erklaert_jeden_zustand():
    klassen = [k for k, _z, _t in sz.LEGENDE]
    assert klassen == ["frei", "teilweise", "geplant", "belegt", "belegt emr", "nn", "nn unbew"]   # 1.53: EMR-Zimmer
    texte = " ".join(t for _k, _z, t in sz.LEGENDE) + " ".join(t for _z, t in sz.ZEICHEN)
    for wort in ("frei", "geplant", "belegt", "gesperrt", "Mangel", "bezugsfertig", "Gebäudeplan"):
        assert wort in texte, wort
    assert "legende()" in inspect.getsource(sz)


def test_protokoll_je_person_und_ausblenden(tmp_path, monkeypatch):
    from belegung import speicher

    daten = {}
    monkeypatch.setattr(speicher, "lesen", lambda name, standard=None: daten.get(name, standard))
    monkeypatch.setattr(speicher, "schreiben", lambda name, inhalt: daten.__setitem__(name, inhalt))
    from modern import netz_kern

    monkeypatch.setattr(netz_kern, "sperre", contextlib.nullcontext)
    t = datetime(2026, 11, 23, 9, 30)
    pk.anhaengen("Person hinzugefügt: Probe, Anna", "Alex", t)
    pk.anhaengen("Zuteilung übernommen", "Alex", t.replace(minute=40))
    pk.anhaengen("Mangel gemeldet: 2-101", "Kim", t.replace(hour=10))
    pk.anhaengen("Nachricht gelesen", "Kim", t.replace(hour=11))          # Lesen erscheint nicht
    pk.anhaengen("Gestern", "Kim", datetime(2026, 11, 22, 8))
    es = pk.heute(date(2026, 11, 23))
    assert [e.titel for e in es] == ["Mangel gemeldet: 2-101", "Zuteilung übernommen", "Person hinzugefügt: Probe, Anna"]
    assert list(pk.je_person(es)) == ["Alex", "Kim"]
    assert pk.zusammenfassung(es) == "Alex: 2 Änderungen · Kim: 1 Änderung"
    assert pk.ausblenden(es[0].id).startswith("Aus der Liste")
    assert [e.wer for e in pk.heute(date(2026, 11, 23))] == ["Alex", "Alex"]
    assert len(pk.heute(date(2026, 11, 23), auch_aus=True)) == 3


def test_ziel_aus_dem_titel():
    assert pk.ziel("Person hinzugefügt: Probe, Anna") == ("anreisen", "personen")
    assert pk.ziel("Mangel gemeldet: 2-101") == ("zimmer", "maengel")
    assert pk.ziel("Reinigung erledigt") == ("reinigung", "liste")
    assert pk.ziel("Termin angelegt") == ("termine", "liste")
    assert pk.ziel("Irgendetwas") == ("zimmer", "aenderungen")


def test_cockpit_zeigt_heute_geaendert():
    kopf = inspect.getsource(sh._liste_kopf)
    assert "Heute geändert" in kopf and "zeigen(AENDERUNGEN)" in kopf
    assert "pk.ausblenden" in inspect.getsource(sh._aenderungen)
    assert sh.auswahl(type("A", (), {"karten": [], "pf_auswahl": sh.AENDERUNGEN})()) == sh.AENDERUNGEN
    from modern import netz_kern

    assert "protokoll_kern.anhaengen(titel, wer())" in inspect.getsource(netz_kern.notieren)
