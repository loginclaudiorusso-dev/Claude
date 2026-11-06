"""Befehlssuche (0.71) in Strg+K – wie „Was möchten Sie tun?“ in Office. Rein, ohne NiceGUI.

Die Befehle kommen aus dem Menüband (jede Schaltfläche, Datei, Titel- und Statusleiste) – damit findet die Suche immer
genau das, was es im Band gibt – plus Aktionen, die nur in Seiten stecken (Neuer Termin, Neuer Mieter …). Dazu:
* Zimmernummer + Stichwort („2-408 Mangel“) → Zimmerkarte, dort Mangel, Sperre, Verlauf;
* eine Frage („Wie viele Zimmer sind im Dezember frei?“) → direkt an „Fragen & Zahlen“;
* sonst als letzter Vorschlag: „Als Auftrag an die Assistenz“.

Ziele: ("seite", seite, ansicht, zustand) · ("aktion", name) · ("panel", seite, ansicht, name) · ("frage", text) ·
("auftrag", text) · ("zimmer", kurzcode)
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field


@dataclass
class Befehl:
    titel: str
    icon: str
    ziel: tuple
    bereich: str = ""                         # z. B. „Zimmer & Haus“ – wo es im Menüband steht
    worte: tuple = ()                         # weitere Suchwörter (Synonyme)
    taste: str = ""
    zusatz: str = field(default="")


# Zusätzliche Suchwörter je Ziel – was Kolleginnen und Kollegen tippen würden
WORTE = {
    ("anreisen", "zuteilen"): ("zimmer zuteilen", "zuweisen", "vorschläge", "anreise", "belegen", "einchecken"),
    ("anreisen", "personen"): ("teilnehmer", "tn", "leute", "neu"),
    ("anreisen", "abreisen"): ("auszug", "abreise", "auschecken", "schlüssel zurück"),
    ("anreisen", "eintragen"): ("belegungssystem", "trägersystem", "übertragen", "abtippen", "abtipp", "eintragen"),
    ("zimmer", "uebersicht"): ("frei", "freie zimmer", "belegung", "gebäude", "kacheln"),
    ("zimmer", "zeitstrahl"): ("gantt", "kalender", "wochen", "zeitachse"),
    ("zimmer", "liste"): ("tabelle", "excel", "zimmerliste"),
    ("zimmer", "maengel"): ("mängel", "defekt", "kaputt", "fm", "hausmeister", "reparatur", "unbewohnbar"),
    ("zimmer", "aenderungen"): ("verlauf", "historie", "wer hat", "protokoll", "änderungen"),
    ("reinigung", "liste"): ("putzen", "sauber", "reinigungsliste"),
    ("reinigung", "last"): ("vorschau", "planung reinigung"),
    ("reinigung", "facility"): ("prüfungen", "checks", "wartung"),
    ("termine", "liste"): ("wiedervorlage", "erinnerung", "frist"),
    ("termine", "monat"): ("kalender", "monat"),
    ("assistenz", "auftraege"): ("auftrag", "ki", "assistent"),
    ("assistenz", "mails"): ("mail", "e-mail", "outlook", "posteingang"),
    ("assistenz", "fragen"): ("frage", "zahlen", "auskunft", "wie viele"),
    ("auswertung", "lage"): ("überblick", "lage", "dashboard", "kennzahlen"),
    ("auswertung", "prognose"): ("vorhersage", "zukunft", "präsentation", "forecast"),
    ("auswertung", "massnahmen"): ("neuanmeldungen", "kurse", "startwelle", "wirtschaftsplan"),
    ("auswertung", "zimmer"): ("engpass", "knapp", "kapazität"),
    ("steuerung", None): ("renovierung", "budget", "finanzen", "leitung", "vorhaben"),
    ("mieter", None): ("mietvertrag", "vertrag", "miete"),
    ("daten", None): ("import", "einlesen", "hochladen", "pivot", "anreiseliste laden", "gebäudeplan"),
    ("einstellungen", "stammdaten"): ("zimmer anlegen", "stammdaten", "betten"),
    ("einstellungen", "sicherung"): ("backup", "sichern", "wiederherstellen"),
    ("inventar", None): ("möbel", "gegenstand", "ausstattung", "lager"),
    ("heute", None): ("start", "tagesübersicht", "dashboard", "aufgaben"),
    "drucken": ("print", "ausdrucken", "liste drucken", "schilder", "schlüsselliste"),
    "exportieren": ("export", "excel", "pdf", "csv", "tabelle", "speichern unter", "herunterladen", "zwischenablage"),
    "optionen": ("einstellungen", "farbe", "farben", "schrift", "design", "theme", "layout"),
    "hilfe": ("anleitung", "tastenkürzel", "erste schritte", "f1", "?"),
    "neuigkeiten": ("glocke", "meldungen", "nachrichten"),
    "standort": ("goslar", "bad pyrmont", "weser-ems", "wechseln"),
    "rueckgaengig": ("undo", "zurück", "strg+z"),
    "aktualisieren": ("neu laden", "refresh"),
    "modus": ("dunkel", "hell", "nachtmodus", "dark"),
    "dichte": ("kompakt", "eng", "mehr zeilen"),
    "vollbild": ("fullscreen", "groß"),
    "zoom:+": ("größer", "vergrößern", "zoom"),
    "zoom:-": ("kleiner", "verkleinern", "zoom"),
    "zoom:100": ("normal", "100", "zoom zurücksetzen"),
    "leitstand": ("workbench", "leitstand"),
}

# Aktionen, die nicht im Band stehen: (Titel, Symbol, Ziel, Suchwörter, Bereich)
EXTRA = [
    ("Neuer Termin", "event", ("panel", "termine", "liste", "termin_neu"), ("termin anlegen", "wiedervorlage anlegen",
                                                                          "erinnerung"), "Start → Termine"),
    ("Neuer Mieter / Mietvertrag", "person_add", ("panel", "mieter", None, "mieter_neu"), ("mieter anlegen", "vertrag anlegen",
                                                                                       "mietvertrag neu"), "Anreisen → Mieter"),
    ("Wochenblatt drucken", "print", ("panel", "reinigung", "liste", "wochenblatt"), ("aushang", "hausmeister", "wochenplan"),
     "Zimmer & Haus → Reinigung"),
    ("Aufgaben-Center", "task_alt", ("aktion", "aufgaben"), ("aufgaben", "to do", "offen"), "Taste A"),
    ("Optionen: Farben", "palette", ("aktion", "optionen:farben"), ("farbschema", "akzentfarbe"), "Datei → Optionen"),
    ("Optionen: Diagramme", "insert_chart", ("aktion", "optionen:diagramme"), ("diagrammtyp", "säulen", "linie"),
     "Datei → Optionen"),
    ("Optionen: Schrift & Zoom", "format_size", ("aktion", "optionen:anzeige"), ("schriftart", "schriftgröße"),
     "Datei → Optionen"),
]

ZIMMER_RE = re.compile(r"\b(\d(?:\.\d)?)\s*-\s*([A-Za-z]?\d{2,3})\b")
ZIMMER_WORTE = {"mangel": "Mangel melden", "defekt": "Mangel melden", "kaputt": "Mangel melden", "sperr": "Sperre",
                "renov": "Sperre / fertig renoviert", "reinig": "Reinigung", "verlauf": "Verlauf", "schild": "Zimmerschild",
                "frei": "Belegung", "wer": "Bewohner", "bewohner": "Bewohner", "karte": "Zimmerkarte"}
FRAGE_WORTE = ("wie viele", "wieviele", "wie viel", "wann", "welche", "wer ", "gibt es", "wo ", "warum", "wie hoch")


def norm(text: str) -> str:
    """Kleinbuchstaben, ohne Akzente; Umlaute bleiben gleichwertig zu ae/oe/ue/ss."""
    t = text.lower().replace("ä", "ae").replace("ö", "oe").replace("ü", "ue").replace("ß", "ss")
    return "".join(c for c in unicodedata.normalize("NFKD", t) if not unicodedata.combining(c)).replace("­", "")


def katalog(ansichten: dict, leitung: bool = True) -> list[Befehl]:
    from . import menueband as mb

    erg: list[Befehl] = []
    gesehen: set = set()

    def dazu(titel: str, icon: str, ziel: tuple, bereich: str, worte: tuple = ()):
        schluessel = (ziel[0], ziel[1], ziel[2] if len(ziel) > 2 else None,
                      repr(sorted(ziel[3].items())) if len(ziel) > 3 and isinstance(ziel[3], dict) else "")
        if schluessel in gesehen or not ziel:
            return
        gesehen.add(schluessel)
        erg.append(Befehl(titel.replace("­", ""), icon, ziel, bereich, worte))

    for r in mb.reiter(ansichten, leitung):
        for g in r.gruppen:
            for p in g.punkte:
                for q in [p] + p.menue:
                    if not q.ziel:
                        continue
                    if q.ziel[0] == "seite":
                        _s, seite, ans, zustand = q.ziel
                        if seite == "heute":
                            ans = None
                        titel = q.text if q is p or not p.menue else f"{p.text} · {q.text}"
                        worte = WORTE.get((seite, ans), ()) + (WORTE.get((seite, None), ()) if ans else ())
                        dazu(titel, q.icon, q.ziel, f"{r.titel} → {g.titel}", worte)
                    elif q.ziel[0] == "aktion" and not q.ziel[1].startswith(("layout:", "farbe:", "dg_legende:")):
                        titel = q.text if q is p or not p.menue else f"{p.text}: {q.text}"
                        dazu(titel, q.icon if q.icon not in ("haken", "radio_button_unchecked") else "tune", q.ziel,
                             f"{r.titel} → {g.titel}", WORTE.get(q.ziel[1], ()))
    for liste, bereich in ((mb.DATEI, "Datei"), (mb.TITELLEISTE, "Titelleiste"), (mb.STATUSLEISTE, "Statusleiste")):
        for p in liste:
            if p.ziel:
                worte = WORTE.get(p.ziel[1], ()) if p.ziel[0] == "aktion" else WORTE.get((p.ziel[1], p.ziel[2]), ())
                titel = {"zoom:100": "Zoom 100 %", "zoom:+": "Vergrößern (Zoom)", "zoom:-": "Verkleinern (Zoom)"}.get(
                    p.ziel[1], p.text)
                dazu(titel, p.icon or "crop_free", p.ziel, bereich, worte)
    dazu("Leitstand-Workbench", "view_quilt", ("aktion", "leitstand"), "Strg+Umschalt+L", WORTE["leitstand"])
    for titel, icon, ziel, worte, bereich in EXTRA:
        dazu(titel, icon, ziel, bereich, worte)
    return erg


def _punkte(b: Befehl, woerter: list[str], ganz: str) -> int:
    titel = norm(b.titel)
    alles = " ".join([titel, norm(b.bereich)] + [norm(w) for w in b.worte])
    if not all(w in alles for w in woerter):
        return 0
    p = 10
    if titel.startswith(ganz):
        p += 60
    elif ganz in titel:
        p += 40
    if any(norm(w) == ganz or norm(w).startswith(ganz) for w in b.worte):
        p += 30
    p += sum(8 for w in woerter if re.search(rf"\b{re.escape(w)}", titel))
    return p


def suchen(text: str, befehle: list[Befehl], anzahl: int = 6) -> list[Befehl]:
    ganz = norm(text.strip())
    woerter = [w for w in ganz.split() if w]
    if not woerter:
        return []
    bewertet = sorted(((s, i, b) for i, b in enumerate(befehle) if (s := _punkte(b, woerter, ganz))),
                      key=lambda x: (-x[0], x[1]))
    return [b for _s, _i, b in bewertet[:anzahl]]


def vorschlaege(befehle: list[Befehl]) -> list[Befehl]:
    """Leere Eingabe: die häufigsten Befehle (wie die Vorschläge in Office)."""
    wunsch = [("seite", "anreisen", "zuteilen"), ("seite", "heute", None), ("seite", "zimmer", "uebersicht"),
              ("panel", "termine", "liste"), ("aktion", "drucken"), ("aktion", "hilfe"), ("aktion", "optionen")]
    erg = []
    for w in wunsch:
        for b in befehle:
            if b.ziel[:len(w)] == w or (w[0] == "seite" and w[1] == "heute" and b.ziel[:2] == ("seite", "heute")
                                        and b.ziel[3].get("heute_ansicht") == "postfach"):
                erg.append(b)
                break
    return erg


def zimmer_befehl(text: str) -> tuple[str, str] | None:
    """„2-408 Mangel“ → ("2-408", "Mangel melden"); nur mit einem Stichwort (sonst greift die normale Zimmersuche)."""
    m = ZIMMER_RE.search(text)
    if not m:
        return None
    rest = norm(ZIMMER_RE.sub(" ", text))
    for stamm, was in ZIMMER_WORTE.items():
        if stamm in rest:
            return f"{m.group(1)}-{m.group(2).upper()}", was
    return None


def ist_frage(text: str) -> bool:
    t = norm(text.strip())
    return len(t) >= 8 and (t.endswith("?") or any(t.startswith(norm(w)) or f" {norm(w)}" in f" {t}" for w in FRAGE_WORTE))
