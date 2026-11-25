"""1.66: Alle Reiter im farbigen Stil (eigene inn_*-Symbole) und Gruppenfarben der Zimmerkacheln."""

import re
from pathlib import Path

from modern import symbole, themes

FARBIG = Path(symbole.__file__).parent / "symbole" / "farbig"
NEU = ["uebersicht", "anreisen", "abreisen", "zimmer", "planung", "auswertung", "ki", "verwaltung", "nachrichten",
       "nachricht_neu", "fm_mail", "a_personenliste", "a_person_weiter", "a_schluessel", "zuteilen", "teilnehmer",
       "datenabgleich", "mieter", "belegungsplan", "kalender", "renovierung", "belegung", "prognose", "massnahmen",
       "suche", "engpaesse", "auftraege", "schnellauskunft", "mails_ki", "daten_einlesen", "stammdaten", "benutzer",
       "verlauf", "a_mail"]


def test_alle_reiter_symbole_eigen_und_vorhanden():
    for n in NEU:
        assert symbole.PIKTO_FARBIG[n] == f"inn_{n}", n
        for gr in ("g", "k"):
            svg = (FARBIG / f"inn_{n}.{gr}.svg").read_text(encoding="utf-8")
            assert svg.lstrip().startswith("<svg") and "viewBox" in svg, n


def test_farbig_html_nutzt_eigene_symbole():
    for n in ("anreisen", "planung", "verwaltung"):
        assert "<svg" in symbole.farbig("p:" + n, "g")


def test_verlaufs_ids_eindeutig():
    gesehen = {}
    for f in FARBIG.glob("inn_*.g.svg"):
        for i in re.findall(r'id="([^"]+)"', f.read_text(encoding="utf-8")):
            assert gesehen.setdefault(i, f.name) == f.name, (i, f.name, gesehen[i])


def test_gruppenfarben_im_css():
    css = themes.css() if hasattr(themes, "css") else Path(themes.__file__).read_text(encoding="utf-8")
    for g in ("g-tn", "g-uwt", "g-mieter", "g-gast"):
        assert g in css
