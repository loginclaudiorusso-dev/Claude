"""0.74 – Arbeitsfläche: eine Kontextzeile, feste Skalen, Dichte 28/36/44, Detailpanel angedockt, Menüband einklappbar."""

from pathlib import Path

from modern import arbeitsflaeche as af
from modern import darstellung_kern as dk
from modern import themes

MOD = Path(__file__).resolve().parent.parent / "modern"


def test_mehrzahl_grammatik():
    assert af.mehrzahl(1, "laufender Vertrag", "laufende Verträge") == "1 laufender Vertrag"
    assert af.mehrzahl(2, "laufender Vertrag", "laufende Verträge") == "2 laufende Verträge"
    assert af.mehrzahl(0, "Änderung", "Änderungen") == "0 Änderungen"


def test_zeilen_bei_1440x900():
    # 767 px App-Höhe: heute 9 Zeilen in Zimmer · Liste – Ziel ≥ 13, kompakt 17, Menüband eingeklappt 16
    assert af.sichtbare_zeilen(767) >= 13
    assert af.sichtbare_zeilen(767, "kompakt") >= 17
    assert af.sichtbare_zeilen(767, band_zu=True) >= 16
    assert af.sichtbare_zeilen(767, "komfort") < af.sichtbare_zeilen(767)


def test_skalen_fest():
    groessen = sorted({g for g, _z, _w, _t in af.SKALA.values()})
    assert groessen[0] == 12 and groessen[-1] == 24            # nie kleiner als 12 px
    assert {w for _g, _z, w, _t in af.SKALA.values()} == {400, 600}
    assert af.ZEILE == {"kompakt": 28, "normal": 36, "komfort": 44}
    assert all(a % 4 == 0 for a in af.ABSTAENDE)


def test_status_mit_symbol_und_symbolwoerterbuch():
    assert set(af.STATUS) == {"frei", "belegt", "geplant", "warnung", "dringend", "nicht_nutzbar"}
    assert all(sym for _bg, _fg, sym in af.STATUS.values())      # kein Zustand nur über Farbe
    for k in ("person", "zimmer", "haus", "anreise", "abreise", "mangel", "mehr", "filter", "drucken", "exportieren"):
        assert af.SYMBOL[k]
    # eine Bedeutung = ein Symbol (keine Doppelbelegung)
    assert len(set(af.SYMBOL.values())) == len(af.SYMBOL)


def test_reihenfolge_kontextzeile():
    r = af.REIHENFOLGE
    assert r["titel"] < r["kontext"] < r["chips"] < r["luft"] < r["suche"] < r["knoepfe"] < r["mehr"] < r["haupt"]
    assert ".m-knopf.primaer { order: 90" in af.CSS                 # Hauptaktion immer rechts außen
    assert "display: contents" in af.CSS and "body.lay-office .m-kz" in af.CSS


def test_null_chips_bleiben_stehen():
    assert "body.lay-office .m-stat.null { display: flex; }" in af.CSS


def test_detailpanel_angedockt():
    assert "body.lay-office .m-schleier { display: none" in af.CSS  # kein Abdunkeln – Liste bleibt bedienbar
    assert f"margin-right: var(--af-pb, {af.PANEL_BREITE}px)" in af.CSS
    assert "--af-oben" in af.JS


def test_dichte_komfort_und_band_zu():
    d = themes.bereinigen({"layout": "office", "theme": "innternat", "dichte": "komfort", "band_zu": True})
    assert d["dichte"] == "komfort" and d["band_zu"] is True
    k = themes.klassen(d)
    assert "dichte-komfort" in k and "band-zu" in k
    assert "band-zu" not in themes.klassen(themes.bereinigen({"layout": "grid", "theme": "innternat", "band_zu": True}))
    assert themes.bereinigen({"dichte": "quatsch"})["dichte"] == "normal"
    assert dk.bereinigen({})["band_zu"] is False


def test_oberflaeche_baut_kontextzeile_und_strg_f1():
    q = (MOD / "oberflaeche.py").read_text(encoding="utf-8")
    assert 'classes("m-kz")' in q and "m-kz-luft" in q
    assert 'band_zu=not self.design.get("band_zu")' in q
    assert "status_info" in q


def test_zimmer_liste_einzeilig():
    q = (MOD / "seite_zimmer.py").read_text(encoding="utf-8")
    assert "Schnellfilter" in q                                   # Mängel, Vinyl … jetzt unter „Filter“
    assert "m-hauswahl" in q                                      # Haus als Auswahl statt Segment-Leiste
    assert 'knopf("Für Mail kopieren", lambda: _fm(a, "mail"), "primaer"' in q
    assert 'knopf("Drucken & Export"' not in q                    # Drucken/Export → ⋯
