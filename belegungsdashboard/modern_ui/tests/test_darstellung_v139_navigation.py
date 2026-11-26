"""1.39 – Navigation 2.0 (Konzept C „Hybrid“): sieben Arbeitsbereiche, Cockpit als Start, eigene Piktogramme,
Kontext-Registerkarten nur bei Bedarf, alte Namen finden über die Suche zum neuen Ort. Ohne echte Daten."""

import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path
from types import SimpleNamespace

from modern import befehle_kern as bk
from modern import menueband as mb
from modern import menueband_ui as mbu
from modern import piktogramme as pk
from modern import register
from modern import seite_heute as sh

BEREICHE = ["Übersicht", "Anreisen", "Zimmer & Haus", "Planung", "Auswertung", "KI-Assistent", "Verwaltung"]


def _reiter(leitung=True):
    return mb.reiter(mbu._ansichten(), leitung, {"G": "Gesamt", "A": "Alpha"})


def _feste():
    return [r for r in _reiter() if not r.kontext]


def test_sieben_bereiche_mit_eigenem_symbol():
    feste = _feste()
    assert [r.titel for r in feste] == BEREICHE
    assert all(r.symbol.startswith("p:") and pk.vorhanden(r.symbol[2:]) for r in feste)
    assert len({r.symbol for r in feste}) == len(feste)


def test_jede_funktion_ein_eigenes_piktogramm():
    """Keine zwei Knöpfe der festen Registerkarten (und kein Bereich) teilen sich ein Bild – über alle Karten hinweg."""
    syms = [mb.symbol(p)[0] for r in _feste() for g in r.gruppen for p in g.punkte]
    assert all(s.startswith("p:") for s in syms)
    zaehl = Counter(syms)
    erlaubt = {"p:uebersicht"}                         # Bereich „Übersicht“ und Knopf „Cockpit“ sind dieselbe Funktion
    assert [s for s, n in zaehl.items() if n > 1] == []
    bereiche = {r.symbol for r in _feste()}
    assert (bereiche & set(syms)) <= erlaubt


def test_piktogramme_sind_gueltiges_svg():
    for name in pk.SYMBOLE:
        wurzel = ET.fromstring(pk.svg(name, 32))
        assert wurzel.get("viewBox") == "0 0 32 32", name
        klassen = {e.get("class") for e in wurzel.iter() if e.get("class")}
        assert klassen <= {"s", "sa", "f", "fa", "fw", "sw", "k", "k2", "dot", "dot a", "sa w", "s w", "sa dash", "s dash", "boje", "m-pk"}, name
    assert len(set(pk.SYMBOLE.values())) == len(pk.SYMBOLE)            # keine zwei gleich
    assert pk.svg("gibt_es_nicht") == ""
    from modern import symbole

    html = symbole.html("p:ki", gross=True)
    assert "m-sym gross pikto" in html and "<svg" in html


def test_hoechstens_acht_und_kein_versteckter_pfeil():
    for r in _reiter():
        assert sum(len(g.punkte) for g in r.gruppen) <= 8, r.titel
    for r in _feste():                                  # Ansichten sichtbar – keine Split-Buttons mehr in den Bereichen
        assert not any(p.menue for g in r.gruppen for p in g.punkte), r.titel


# Ansichten, die man in der Werkzeug-Registerkarte ihrer Seite umschaltet (Raster | Karten, Liste | Monat …)
IN_DER_SEITE = {("zimmer", "karten"), ("termine", "monat"), ("inventar", "zimmer"), ("inventar", "haeuser"),
                ("steuerung", "vorhaben"), ("steuerung", "zeitplan"), ("steuerung", "finanzen"), ("steuerung", "grundlagen")}


def test_jede_ansicht_erreichbar():
    ziele = {(z[1], z[2]) for z in mb.alle_ziele(mbu._ansichten())}
    for seite, views in mbu._ansichten().items():
        for k in views:
            assert (seite, k) in ziele or (seite, k) in IN_DER_SEITE, (seite, k)
    assert {("mieter", "mieter"), ("mieter", "gaeste"), ("daten", None)} <= ziele   # 1.49: Gäste & Mieter
    for seite in register.SEITEN:
        assert any(z[0] == seite for z in ziele), seite
    root = Path(mb.__file__).parent
    assert 'segmente(ANSICHTEN, ansicht, lambda v: a.oeffnen("termine", ansicht=v))' in (root / "seite_termine.py").read_text(encoding="utf-8")
    assert 'segmente(DARSTELLUNG, ansicht' in (root / "seite_zimmer.py").read_text(encoding="utf-8")
    for datei in ("seite_inventar.py", "seite_steuerung.py"):          # nicht mehr im Band versteckt (ansicht=True)
        assert "ansicht=v), ansicht=True)" not in (root / datei).read_text(encoding="utf-8")


def test_kontextkarten_nur_wo_gebraucht():
    k = {r.key: r for r in _reiter() if r.kontext}
    assert set(k) == {"prognose", "diagramm"}
    assert mb.sichtbar(k["prognose"], "auswertung", "prognose") and not mb.sichtbar(k["prognose"], "auswertung", "lage")
    assert mb.KONTEXT_TITEL == {"termine": "Kalender", "zimmer": "Zimmer", "inventar": "Inventar", "steuerung": "Renovierung"}
    assert mbu.seiten_reiter_titel(SimpleNamespace(seite="termine")) == "Kalender"
    for r in _feste():
        assert mb.sichtbar(r, "heute", None)


def test_planung_und_haus_sauber_getrennt():
    rs = {r.key: r for r in _feste()}
    def ziele(key):
        return {(p.ziel[1], p.ziel[2]) for g in rs[key].gruppen for p in g.punkte if p.ziel[0] == "seite"}
    assert ("zimmer", "zeitstrahl") in ziele("planung")
    assert {("reinigung", "liste"), ("reinigung", "last"), ("reinigung", "facility")} <= ziele("zimmer")   # 1.61: gebündelt
    assert ("termine", "liste") in ziele("planung") and ("steuerung", "cockpit") in ziele("planung")
    assert ("reinigung", "liste") in ziele("zimmer") and ("inventar", "gegenstaende") in ziele("zimmer")
    assert ("auswertung", "prognose") in ziele("auswertung")             # Prognose wird gelesen, nicht geplant
    assert not any(k[0] == "zimmer" and k[1] == "zeitstrahl" for k in ziele("zimmer"))
    assert "Renovierung & Budget" not in [p.text for g in {r.key: r for r in _reiter(False)}["planung"].gruppen
                                          for p in g.punkte]


def test_verwaltung_buendelt_einrichten():
    rs = {r.key: r for r in _feste()}
    texte = [p.text.replace("­", "") for g in rs["verwaltung"].gruppen for p in g.punkte]
    assert texte == ["Daten einlesen", "Zimmer-Stammdaten", "Benutzer & Rechte", "Einstellungen", "Automatisierung",
                     "Änderungsverlauf", "Versandprotokoll", "Ladezeiten"]   # 1.59, 1.72
    assert mb.A("automatisierung") in [p.ziel for g in rs["verwaltung"].gruppen for p in g.punkte]
    assert "qr_ui.fenster(a)" in (Path(mbu.__file__)).read_text(encoding="utf-8")


def test_datei_nur_ausgabe_und_persoenliches():
    assert [p.text for p in mb.DATEI] == ["Drucken … (Strg+P)", "Exportieren …", "Informationen & Sicherung", "Konto"]
    assert all(p.icon.startswith("p:") for p in mb.DATEI)
    assert [p.text for p in mb.TITELLEISTE][:2] == ["Chat", "Benachrichtigungen"]      # 1.43: Chat vorne


def test_alte_namen_finden_den_neuen_ort():
    kat = bk.katalog(mbu._ansichten())
    def erster(text):
        return bk.suchen(text, kat)[0].ziel
    assert erster("Posteingang")[:2] == ("seite", "heute")
    assert erster("Tagesübersicht")[:2] == ("seite", "heute")
    assert erster("Steuerung")[:2] == ("seite", "steuerung")
    assert erster("RIOS-Daten")[:3] == ("seite", "anreisen", "eintragen")
    assert erster("Fragen & Zahlen")[:3] == ("seite", "assistenz", "fragen")
    assert erster("Zeitstrahl")[:3] == ("seite", "zimmer", "zeitstrahl")
    assert erster("Importieren")[:2] == ("seite", "daten")
    assert erster("Optionen") == ("aktion", "optionen")
    assert erster("Termine")[:3] in (("seite", "termine", "liste"), ("panel", "termine", "liste"))


def test_cockpit_eine_startseite_und_sprung_zu_nachrichten():
    assert sh.ANSICHTEN == {"postfach": "Cockpit"}
    for alt in ("zentrale", "uebersicht", "postfach", None):
        assert sh.ansicht(SimpleNamespace(heute_ansicht=alt)) == "postfach"
    n = SimpleNamespace(id="ab12")
    a = SimpleNamespace(karten=[], pf_auswahl=sh.NACHRICHTEN, daten=SimpleNamespace(nachrichten=[n]))
    assert sh.auswahl(a) == "nachricht:ab12"
    a.daten.nachrichten = []
    assert sh.auswahl(a) == sh.UEBERBLICK
    assert sh.NACHRICHTEN == mb.NACHRICHTEN
    quelle = Path(sh.__file__).read_text(encoding="utf-8")
    assert "def _zentrale" not in quelle and "_woche_tabelle(a, t)" in quelle and "_frei_saeulen(a, t)" in quelle
    assert register.TITEL["heute"] == "Übersicht" and mbu.seitentitel(SimpleNamespace(seite="heute"), "Übersicht") == \
        "Übersicht · Cockpit"


def test_neue_namen_in_den_seiten():
    from modern import seite_anreisen, seite_assistenz, seite_auswertung, seite_einstellungen, seite_steuerung, seite_zimmer

    assert seite_anreisen.ANSICHTEN["personen"] == "Teilnehmerliste" and seite_anreisen.ANSICHTEN["eintragen"] == "Datenabgleich"
    assert seite_zimmer.ANSICHTEN["zeitstrahl"] == "Belegungsplan" and seite_zimmer.ANSICHTEN["aenderungen"] == "Änderungsverlauf"
    assert seite_assistenz.ANSICHTEN["fragen"] == "Schnellauskunft"
    assert "lage" not in seite_auswertung.ANSICHTEN                  # 1.41: in „Belegung“ aufgegangen
    assert seite_einstellungen.ANSICHTEN["benutzer"] == "Benutzer & Rechte"
    assert seite_steuerung.ANSICHTEN["grundlagen"] == "Annahmen"
    # „Übersicht“ gibt es nur noch als Bereich
    alle = [t for v in mbu._ansichten().values() for t in v.values()]
    assert "Übersicht" not in alle and "Cockpit" not in alle
