"""Tab-Vervollständigung für die Chat-Eingabe (ohne Qt, testbar).

* Leeres Feld: die aktuellen Vorschläge der Reihe nach.
* Mit Text: zuerst ganze Vorschläge/frühere Fragen, die so anfangen, dann solche, die den
  Text enthalten; passt keiner, wird das letzte Wort ergänzt („Belegung Gos“ → „Belegung Goslar“).
"""

from __future__ import annotations

WORTSCHATZ = [
    "Goslar", "Bad Pyrmont", "Weser-Ems", "alle Standorte", "Belegung", "Auslastung", "Prognose", "Kapazität",
    "frei", "freie Plätze", "Anreisen", "Mieter", "Gäste", "Häuser", "Personentage", "Vergleich", "Trend",
    "Höchststand", "Tiefststand", "heute", "morgen", "gestern", "diese Woche", "nächste Woche", "letzte Woche",
    "diesen Monat", "nächsten Monat", "letzten Monat", "nächste 4 Wochen", "letzte 6 Monate", "dieses Jahr",
    "Januar", "Februar", "März", "April", "Mai", "Juni", "Juli", "August", "September", "Oktober",
    "November", "Dezember", "brutto", "netto", "Modellgüte",
]


def _eindeutig(texte):
    gesehen, ergebnis = set(), []
    for t in texte:
        k = t.strip().lower()
        if k and k not in gesehen:
            gesehen.add(k)
            ergebnis.append(t.strip())
    return ergebnis


def kandidaten(eingabe: str, vorschlaege: list[str], historie: list[str] | None = None,
               wortschatz: list[str] | None = None) -> list[str]:
    text = eingabe.strip()
    saetze = _eindeutig(list(vorschlaege) + list(reversed(historie or [])))
    if not text:
        return saetze
    t = text.lower()
    anfang = [s for s in saetze if s.lower().startswith(t) and s.lower() != t]
    enthalten = [s for s in saetze if t in s.lower() and s not in anfang and s.lower() != t]
    if anfang or enthalten:
        return anfang + enthalten
    # letztes Wort ergänzen
    kopf, _, wort = eingabe.rstrip().rpartition(" ")
    if not wort:
        return []
    w = wort.lower()
    worte = [x for x in (wortschatz or WORTSCHATZ) if x.lower().startswith(w) and x.lower() != w]
    return [(kopf + " " if kopf else "") + x for x in worte]
