"""0.65: Menüband wie in Office, sachliche Überschriften, Leitstand ohne Fachjargon. Ohne echte Daten."""

from modern import menueband as mb

ANS = {"anreisen": {"zuteilen": "Zuteilen", "personen": "Personen", "abreisen": "Abreisen", "eintragen": "Firmenprogramm"},
       "zimmer": {"uebersicht": "Übersicht", "karten": "Karten", "zeitstrahl": "Zeitstrahl", "liste": "Liste",
                  "maengel": "Defekte Zimmer", "aenderungen": "Änderungen"},
       "auswertung": {"lage": "Lage", "prognose": "Prognose"}, "steuerung": {"cockpit": "Cockpit"},
       "einstellungen": {"allgemein": "Allgemein", "sicherung": "Sicherung & Verlauf"}}


class _K:
    def __init__(self, stufe):
        self.stufe = stufe


def _alle(reiter):
    for r in reiter:
        for g in r.gruppen:
            for p in g.punkte:
                yield r, p
                for q in p.menue:
                    yield r, q


def test_reiter_wie_office():
    r = mb.reiter(ANS)
    assert [x.titel for x in r] == ["Start", "Belegung", "Planung", "Auswertung", "Verwalten", "Ansicht"]
    zimmer = next(p for _r, p in _alle(r[:1]) if p.text == "Zimmer")
    assert [q.text for q in zimmer.menue] == list(ANS["zimmer"].values())          # Ausklappmenü = Unteransichten
    assert all(p.icon for _r, p in _alle(r))                                       # jede Schaltfläche mit Symbol
    ziele = [p.ziel for _r, p in _alle(r) if p.ziel]
    assert all(z[0] in ("seite", "aktion") for z in ziele)
    assert ("aktion", "layout:original") in ziele                                   # Weg zurück zum Original


def test_aktiv_und_reiter_von():
    r = mb.reiter(ANS)
    zeit = next(p for x, p in _alle(r) if x.key == "belegung" and p.text == "Zeitstrahl")
    assert mb.aktiv(zeit, "zimmer", lambda s: "zeitstrahl")
    assert not mb.aktiv(zeit, "zimmer", lambda s: "liste")
    zimmer = next(p for _r, p in _alle(r[:1]) if p.text == "Zimmer")
    assert mb.aktiv(zimmer, "zimmer", lambda s: "liste")                           # Menü leuchtet, wenn eine Ansicht offen
    pf = next(p for _r, p in _alle(r[:1]) if p.text == "Postfach")
    assert mb.aktiv(pf, "heute", lambda s: "", "postfach") and not mb.aktiv(pf, "heute", lambda s: "", "zentrale")
    assert mb.reiter_von("auswertung", ANS) == "auswertung"
    assert mb.reiter_von("einstellungen", ANS) == "verwalten"
    assert mb.reiter_von("heute", ANS) == "start"


def test_statuszeile():
    t = mb.statuszeile("Erfundenstadt", [_K("dringend"), _K("bald")], "Stand 10:00")
    assert "Erfundenstadt" in t and "2 offene Aufgaben · 1 dringend" in t and "Stand 10:00" in t
    assert "1 offene Aufgabe" in mb.statuszeile("X", [_K("info")], "")


def test_layout_office_bekannt():
    from modern import themes

    assert "office" in themes.LAYOUTS
    d = themes.bereinigen({"layout": "office", "theme": "innternat", "modus": "hell"})
    assert d["layout"] == "office" and "lay-office" in themes.klassen(d)


def test_sachliche_ueberschriften():
    from pathlib import Path

    from modern import leitstand_ui as ls
    from modern import seite_heute as sh

    assert sh.untertitel(2, 3) == "2 dringende Aufgaben, 3 weitere offen."
    assert sh.untertitel(1, 0) == "1 dringende Aufgabe."
    assert sh.untertitel(0, 4) == "Keine dringenden Aufgaben – 4 weitere offen."
    assert sh.untertitel(0, 0) == "Keine offenen Aufgaben."
    quelle = Path(sh.__file__).read_text(encoding="utf-8")
    assert "Der Tag im Griff" not in quelle and "Nichts kann schiefgehen" not in quelle
    assert [t for _n, t, _i in ls.BUEHNEN.values()] == ["Disposition", "Verwaltung", "Auswertung", "Bau & Budget"]
    texte = " ".join(w for _t, w in ls.KUERZEL)
    assert "Bühne" not in texte and "Inspektor" not in texte and "Omnibar" not in texte
