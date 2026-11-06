"""Kennzahlen-Katalog (0.75) – EINE Stelle, an der steht, was eine Zahl bedeutet und wie sie gerechnet wird.

„ƒx Berechnung“ unter den Diagrammen, das Detailpanel nach einem Klick auf einen Wert und die Tabellenansicht lesen
von hier. Jede Kennzahl hat drei Ebenen:

1. **In Worten** – ein Satz, was gerechnet wird,
2. **Formel mit Werten** – die Rechnung mit den echten Zahlen der gewählten Stelle,
3. **Grundlage** – Quelle, was abgezogen oder ausgeschlossen ist, Annahmen.

Die Texte beschreiben die Rechnung so, wie sie im Programm tatsächlich läuft (``belegung/prognose.py``,
``auswertung_kern``, ``belegung/eintragen``). Rein – ohne Oberfläche.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Kennzahl:
    name: str
    satz: str            # 1 · in Worten
    formel: str          # 2 · allgemein (die Werte setzt ``einsetzen`` ein)
    grundlage: str       # 3 · Quelle, Abzüge, Annahmen
    einheit: str = ""


KATALOG: dict[str, Kennzahl] = {
    "belegung": Kennzahl(
        "Belegung (Ø belegte Plätze)", "Durchschnitt der an jedem Tag des Monats belegten Plätze.",
        "Belegung = Summe der belegten Plätze aller Tage ÷ Tage im Monat",
        "Belegungs-Pivot (Ist) und Listen. Netto: ohne UWTler und Mieter; Brutto: alle.", "Plätze"),
    "prognose": Kennzahl(
        "Prognose (erwartet)",
        "Das Modell, das in den letzten Monaten im Blindtest am wenigsten danebenlag, rechnet die Reha-Belegung "
        "vorwärts; dazu kommen die bekannten Verträge (Mieter, UWT) aus den Listen.",
        "Prognose = Modellwert (Reha) + Ø Verträge im Monat – nie unter dem bereits gebuchten Bestand",
        "Auswahl per Backtest (mittlerer absoluter Fehler) unter mehreren Modellen, z. B. Holt-Winters mit gedämpftem "
        "Trend, Saisonprofil auf aktuellem Niveau oder deren Mittel. Ab Monat 13 nur fortgeschrieben, nicht geprüft.",
        "Plätze"),
    "band80": Kennzahl(
        "80 %-Band", "In 8 von 10 Fällen lag der echte Wert bisher in diesem Bereich.",
        "Band = Prognose ± Fehlerbreite für diesen Monatsabstand (80 %-Quantil der Blindtest-Fehler, wächst mit √Monate)",
        "Fehler aus dem rollierenden Blindtest je Prognoseabstand (1–12 Monate), darüber hinaus fortgeschrieben. "
        "Die Untergrenze fällt nie unter den gebuchten Bestand.", "Plätze"),
    "band95": Kennzahl(
        "95 %-Band", "In 19 von 20 Fällen lag der echte Wert bisher in diesem Bereich.",
        "Band = Prognose ± Fehlerbreite (95 %-Quantil der Blindtest-Fehler, mindestens 80 %-Breite × 1,96 ÷ 1,28)",
        "Wie das 80 %-Band, mit dem 95 %-Quantil.", "Plätze"),
    "kapazitaet": Kennzahl(
        "Kapazität", "So viele Plätze können am Standort belegt werden.",
        "Kapazität = hinterlegte Plätze des Standorts (netto oder brutto)",
        "Einstellungen → Kapazitäten. Im Szenario änderbar (z. B. minus unbewohnbare Betten).", "Plätze"),
    "auslastung": Kennzahl(
        "Auslastung", "Anteil der belegten an den verfügbaren Plätzen.",
        "Auslastung = Belegung ÷ Kapazität", "Belegung wie oben (Ist oder Prognose), Kapazität laut Einstellungen.", "%"),
    "reserve": Kennzahl(
        "Kapazitätsreserve", "So viele Plätze bleiben bis zur Kapazität frei.",
        "Reserve = Kapazität − Belegung (ungünstiger Fall: Kapazität − obere 80 %-Grenze)",
        "Negativ heißt: mehr Bedarf als Plätze – Engpass.", "Plätze"),
    "backtest": Kennzahl(
        "Backtest (1 Monat vorher)", "Was das Modell einen Monat vorher für diesen Monat vorhergesagt hätte.",
        "Abweichung = Ist − Vorhersage von vor einem Monat; im Mittel = mittlerer absoluter Fehler",
        "Rollierend gerechnet, nur mit den Daten, die damals vorlagen.", "Plätze"),
    "frei_jetzt": Kennzahl(
        "Frei jetzt", "Zimmer, die in der Woche an allen Tagen frei sind – mit den heute gespeicherten Zuteilungen.",
        "Frei jetzt = nutzbare Zimmer − belegte − geplante",
        "Gebäudeplan und gespeicherte Planung; gesperrte und unbewohnbare Zimmer zählen nicht.", "Zimmer"),
    "frei_nach_planung": Kennzahl(
        "Frei nach Planung", "Freie Zimmer, wenn auch alle bekannten Anreisen ohne Zimmer probeweise nach den Regeln "
        "zugeteilt wären (nichts wird gespeichert).",
        "Frei nach Planung = frei jetzt − probeweise zugeteilte Anreisen",
        "Anreiselisten der nächsten 12 Wochen, Regeln der Zuteilung; Ampel nach den Grenzen in den Einstellungen.",
        "Zimmer"),
    "emr": Kennzahl(
        "EMR frei", "Freie Einzelzimmer mit eigenem Bad (EMR) nach Planung.",
        "EMR frei = EMR-Zimmer − belegte − probeweise zugeteilte", "Wie „Frei nach Planung“, nur EMR-Zimmer.", "Zimmer"),
    "doppel": Kennzahl(
        "Doppelzimmer UWT frei", "Freie Betten in Doppelzimmern für Umschüler (UWT) nach Planung.",
        "Doppel frei = freie Doppelzimmer-Betten − probeweise zugeteilte UWT",
        "Wie „Frei nach Planung“, nur Doppelzimmer.", "Betten"),
    "nicht_nutzbar": Kennzahl(
        "Nicht nutzbar", "Zimmer, die an dem Tag niemand beziehen kann.",
        "Nicht nutzbar = gesperrt laut Gebäudeplan + wegen eines Mangels unbewohnbar",
        "Gebäudeplan (Sperren, Renovierung) und Mängelliste; geht von der Kapazität ab.", "Zimmer"),
}

# Reihen-Namen in den Diagrammen → Kennzahl (für Detailpanel und ƒx)
REIHE = {"Ist": "belegung", "laufender Monat": "belegung", "Prognose (erwartet)": "prognose", "80 %-Band": "band80",
         "95 %-Band": "band95", "Kapazität": "kapazitaet", "Backtest (1 Monat vorher)": "backtest"}


def _z(x, nk: int = 0) -> str:
    if x is None:
        return "–"
    s = f"{x:,.{nk}f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return s


def _p(x) -> str:
    return "–" if x is None else f"{x * 100:.1f} %".replace(".", ",")


def einsetzen(schluessel: str, w: dict) -> str:
    """Formel mit den echten Werten (Ebene 2). Fehlt ein Wert, bleibt die allgemeine Formel stehen."""
    k = KATALOG[schluessel]
    try:
        if schluessel == "auslastung":
            return f"{_z(w['belegung'])} ÷ {_z(w['kapazitaet'])} = {_p(w['belegung'] / w['kapazitaet'])}"
        if schluessel == "reserve":
            return f"{_z(w['kapazitaet'])} − {_z(w['belegung'])} = {_z(w['kapazitaet'] - w['belegung'])}"
        if schluessel == "prognose":
            v = w.get("vertraege") or 0.0
            teil = f"{_z(w['erwartet'] - v)} Modell (Reha) + {_z(v)} Verträge" if v else f"{_z(w['erwartet'])} Modell (Reha)"
            return f"{teil} = {_z(w['erwartet'])}" + (f" · gebucht mind. {_z(w['gesichert'])}" if w.get("gesichert") else "")
        if schluessel in ("band80", "band95"):
            return f"{_z(w['lo'])} bis {_z(w['hi'])} (Breite {_z(w['hi'] - w['lo'])})"
        if schluessel == "backtest":
            return f"{_z(w['ist'])} Ist − {_z(w['vorher'])} vorhergesagt = {_z(w['ist'] - w['vorher'], 1)}"
        if schluessel == "frei_nach_planung":
            return f"{_z(w['frei_jetzt'])} − {_z(w['frei_jetzt'] - w['frei_nach'])} = {_z(w['frei_nach'])}"
        if schluessel == "nicht_nutzbar":
            return f"{_z(w['gesperrt'])} gesperrt + {_z(w['unbewohnbar'])} unbewohnbar = {_z(w['gesperrt'] + w['unbewohnbar'])}"
    except (KeyError, TypeError, ZeroDivisionError):
        pass
    return k.formel


def werte_an(option: dict, index: int) -> list[tuple[str, str]]:
    """Alle Werte einer Stelle der x-Achse aus einer ECharts-Option – für Detailpanel und Tabelle. Gestapelte Bänder
    (untere Grenze + Breite) werden zu „von – bis“; Hilfsreihen ohne Tooltip und leere Namen fallen weg."""
    reihen = option.get("series") or []
    unten: dict = {}
    erg = []
    for se in reihen:
        daten = se.get("data") or []
        roh = daten[index] if 0 <= index < len(daten) else None
        if isinstance(roh, dict):
            roh = roh.get("value")
        if isinstance(roh, (list, tuple)):
            roh = roh[-1] if roh else None
        stapel = se.get("stack")
        name = se.get("name") or ""
        versteckt = (se.get("tooltip") or {}).get("show") is False or not name
        if stapel and versteckt:
            unten[stapel] = roh
            continue
        if versteckt or roh is None:
            continue
        if stapel and unten.get(stapel) is not None:
            lo = unten[stapel]
            erg.append((name, f"{_z(lo)} – {_z(lo + roh)}"))
        else:
            erg.append((name, _z(roh, 1 if isinstance(roh, float) and roh != int(roh) else 0)))
    return erg


def kategorie(option: dict, index: int) -> str:
    x = option.get("xAxis") or {}
    if isinstance(x, list):
        x = x[0] if x else {}
    daten = x.get("data") or []
    return str(daten[index]) if 0 <= index < len(daten) else str(index + 1)


def engpass_bereiche(oben: list, kapazitaet: float | None) -> list[tuple[int, int]]:
    """Zusammenhängende Abschnitte (von, bis – Indizes), in denen die obere Bandgrenze die Kapazität erreicht."""
    if not kapazitaet:
        return []
    erg, start = [], None
    for i, v in enumerate(list(oben) + [None]):
        drin = v is not None and v >= kapazitaet
        if drin and start is None:
            start = i
        elif not drin and start is not None:
            erg.append((start, i - 1))
            start = None
    return erg
