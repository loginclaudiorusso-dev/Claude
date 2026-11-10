"""0.75 – Diagramme groß und ziehbar, Diagramm ⇄ Tabelle, Klick → Detailpanel, ƒx Berechnung (Kennzahlen-Katalog),
Engpass-Zone, Heatmap Engpässe, Design-Vorlagen, Knopf- und Symbolstil, hoher Kontrast."""

from pathlib import Path

from modern import darstellung_kern as dk
from modern import diagramm_ui
from modern import kennzahlen_katalog as kk
from modern import themes

MOD = Path(__file__).resolve().parent.parent / "modern"


def test_katalog_drei_ebenen():
    for k, z in kk.KATALOG.items():
        assert z.name and z.satz and z.formel and z.grundlage, k
    for name, k in kk.REIHE.items():
        assert k in kk.KATALOG, name


def test_einsetzen_mit_werten():
    assert kk.einsetzen("auslastung", {"belegung": 145, "kapazitaet": 290}) == "145 ÷ 290 = 50,0 %"
    assert kk.einsetzen("reserve", {"belegung": 250, "kapazitaet": 290}) == "290 − 250 = 40"
    assert kk.einsetzen("prognose", {"erwartet": 242, "vertraege": 8}) == "234 Modell (Reha) + 8 Verträge = 242"
    assert kk.einsetzen("band80", {"lo": 231, "hi": 254}) == "231 bis 254 (Breite 23)"
    assert kk.einsetzen("nicht_nutzbar", {"gesperrt": 9, "unbewohnbar": 3}) == "9 gesperrt + 3 unbewohnbar = 12"
    # fehlende Werte → allgemeine Formel statt Fehler
    assert kk.einsetzen("auslastung", {}) == kk.KATALOG["auslastung"].formel
    assert kk.einsetzen("auslastung", {"belegung": 1, "kapazitaet": 0}) == kk.KATALOG["auslastung"].formel


def test_werte_an_stelle_baender_als_spanne():
    opt = {"xAxis": {"data": ["Jan", "Feb"]}, "series": [
        {"name": "u80", "stack": "b80", "data": [None, 230], "tooltip": {"show": False}},
        {"name": "80 %-Band", "stack": "b80", "data": [None, 24]},
        {"name": "Ist", "data": [250.0, None]},
        {"name": "Prognose (erwartet)", "data": [None, 242.5]},
        {"name": "Kapazität", "data": [{"value": 290}, {"value": 290}]},
        {"name": "", "data": [1, 1]}]}
    assert kk.werte_an(opt, 1) == [("80 %-Band", "230 – 254"), ("Prognose (erwartet)", "242,5"), ("Kapazität", "290")]
    assert kk.werte_an(opt, 0) == [("Ist", "250"), ("Kapazität", "290")]
    assert kk.kategorie(opt, 1) == "Feb" and kk.kategorie(opt, 9) == "10"


def test_engpass_bereiche():
    assert kk.engpass_bereiche([None, 280, 291, 295, 285, 300], 290) == [(2, 3), (5, 5)]
    assert kk.engpass_bereiche([300, 300], None) == []


def test_diagramm_leiste_und_ziehen():
    js = diagramm_ui.JS
    for teil in ("m-dg-griff", "Tabelle", "Kopieren", "Berechnung", "m_achse", "localStorage", "--af-pb", "convertFromPixel"):
        assert teil in js, teil
    assert "calc(100vh - var(--af-oben, 216px) - 390px)" in diagramm_ui.CSS          # Graph + Karten auf einen Blick
    q = (MOD / "seite_prognose.py").read_text(encoding="utf-8")
    assert "karte.anbinden" in q and "karte.fx(" in q and "Engpass möglich" not in q       # 0.87: über die Diagramm-Karte
    assert "def _engpass_heatmap" in (MOD / "seiten.py").read_text(encoding="utf-8")


def test_vorlagen_und_stile():
    assert set(dk.VORLAGEN) == {"petrol", "nordic", "sand", "praesentation", "kontrast"}
    for k, (_n, _t, werte) in dk.VORLAGEN.items():
        d = dk.bereinigen({**dk.STANDARD, **werte})
        assert dk.vorlage_von(d) == k, k
    d = themes.bereinigen({"layout": "office", "theme": "innternat", "knopfstil": "kontur", "symbolstil": "rund",
                           "kontrast": True})
    k = themes.klassen(d)
    assert "knopf-kontur" in k and "sym-rund" in k and "kontrast" in k
    assert dk.bereinigen({"knopfstil": "glanz", "symbolstil": "emoji"})["knopfstil"] == "klar"
    assert dk.bereinigen({"symbolstil": "emoji"})["symbolstil"] == "linie"
    for kl in ("knopf-weich", "knopf-kontur", "knopf-kraeftig", "sym-gefuellt", "sym-rund", "kontrast"):
        assert kl in themes.ALLE_KLASSEN


def test_optionen_modul_laedt():
    from modern import optionen_ui  # noqa: F401 – Syntax und Import der Optionen (Vorlagen, Knöpfe, Symbole)
