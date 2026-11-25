"""1.64: grafische Konsistenz – farbige Symbole wirken, neue Piktogramme, ruhige Sperre, Chat neben dem Panel,
keine Farb-Altlasten."""

import re
from pathlib import Path

from modern import piktogramme as pk
from modern import symbole as sy
from modern import themes

MODERN = Path(sy.__file__).parent


def test_farbig_wirkt_auch_fuer_piktogramme():
    for name in ("p:kalender", "p:ki", "calendar", "people", "warning"):
        assert "farbig" in sy.html(name, sy.BLAU, True, variante="farbig"), name
        assert "farbig" not in sy.html(name, sy.BLAU, True, variante="fluent"), name
    # Vorschau im Optionen-Dialog: beide Knöpfe sehen verschieden aus
    for name, farbe in sy.VORSCHAU:
        assert sy.html(name, farbe, True, variante="farbig") != sy.html(name, farbe, True, variante="fluent")
    assert all(sy.farbig("p:" + k) for k in sy.PIKTO_FARBIG), "jede Zuordnung zeigt auf ein vorhandenes Motiv"
    assert set(sy.PIKTO_FARBIG) <= set(pk.SYMBOLE)


def test_neue_piktogramme_eindeutig():
    an, ab = pk.SYMBOLE["anreisen"], pk.SYMBOLE["abreisen"]
    assert an != ab and "M4 16.5h11.5" in an and "M16 16.5H4.5" in ab           # Pfeil hinein → / heraus ←
    for k in ("ki", "auftraege", "mails_ki"):                                    # Funkeln statt Dreieck mit 3 Punkten
        assert "Q" in pk.SYMBOLE[k] and pk.SYMBOLE[k].count('class="fa" cx=') == 0, k
    assert pk.SYMBOLE["stammdaten"] != pk.SYMBOLE["defekt"] and "6 27V5.5" not in pk.SYMBOLE["stammdaten"]
    assert "boje" not in pk.SYMBOLE["hilfe"] and "boje" not in pk.CSS
    assert "fa" in pk.SYMBOLE["automatisierung"] and "circle" in pk.SYMBOLE["mieter"]


def test_bereichsfarben_und_option_signal():
    assert "sym-signal" not in themes.klassen({})
    assert "sym-signal" in themes.klassen({"symbol_farben": "signal"})
    assert "sym-signal" in themes.ALLE_KLASSEN
    assert themes.bereinigen({"symbol_farben": "quatsch"})["symbol_farben"] == "bereich"
    for rb in ("anreisen", "zimmer", "planung", "auswertung", "ki", "verwaltung"):
        assert f".rb-{rb} .m-sym:not([style])" in pk.CSS and f"seite-rb-{rb}" in pk.CSS


def test_sperre_ruhig_rot_nur_unbewohnbar():
    css = (MODERN / "themes.py").read_text(encoding="utf-8")
    regel = re.search(r"body\.pro \.m-kachel\.nn, body\.pro \.m-kachel\.gesperrt \{[^}]*\}", css).group(0)
    assert "var(--zi-sperr-rand)" in regel and "2px solid var(--zi-sperr-text)" not in regel and "700" not in regel
    assert "--zi-sperr-text: #B42318" not in css and "--zi-mangel1" in css


def test_chat_neben_dem_panel():
    css = (MODERN / "arbeitsflaeche.py").read_text(encoding="utf-8")
    assert ":has(.m-center.offen) section.m-chat" in css and ":has(.m-center.offen.breit) section.m-chat" in css


def test_keine_farb_altlasten():
    for p in MODERN.glob("*.py"):
        t = p.read_text(encoding="utf-8")
        assert "indigo-4" not in t, p.name
    band = (MODERN / "band_ui.py").read_text(encoding="utf-8")
    assert "#e0f2fe" not in band and "#0369a1" not in band and "var(--ob-an" in band
    af = (MODERN / "arbeitsflaeche.py").read_text(encoding="utf-8")
    assert "--q-primary: var(--akzent)" in af and "--r: 6px; --r2: 10px" in af


def test_eigene_farbige_symbole_v165():
    """1.65: eigene farbige Motive – keine gleichen Bilder in einer Gruppe (Einstellungen ≠ Automatisierung)."""
    for k in ("zimmeruebersicht", "zimmerliste", "reinigung", "reinigungsvorschau", "facility", "defekt", "qr",
              "inventar", "einstellungen", "automatisierung", "a_bett"):
        assert sy.PIKTO_FARBIG[k].startswith("inn_") and "linearGradient" in sy.farbig("p:" + k), k
    assert sy.farbig("p:einstellungen") != sy.farbig("p:automatisierung")
