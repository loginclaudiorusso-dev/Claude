"""Vorhaben → Maßnahmen → Kostenpositionen (0.47) – das Grundmodell der Steuerung. Rein, ohne NiceGUI.

* **Vorhaben**: die Entscheidungseinheit (z. B. „Brandschutztüren Haus 6“). Genau ein **Haupttreiber** (Pflicht,
  Risiko, Wirtschaftlichkeit, Kapazität, Qualität) – Pflicht braucht einen **Nachweis** (Rechtsgrundlage, Vorgabe oder
  Prüfprotokoll), die anderen eine kurze Begründung. So wird nicht einfach alles zur Pflicht erklärt.
* **Drei Statusachsen**: *Entscheidung* von Hand (mit Datum und Wer); *Umsetzung* ergibt sich aus Terminen und Auftrag;
  *Finanzen* aus Auftrag und Rechnungen. Unmögliche Kombinationen werden als Hinweis gemeldet.
* **Kostenposition**: Betrag, Herkunft (Angebot / Eingabe / Schätzung / Platzhalter), Haushaltsjahr, Topf (Bau / Möbel /
  sonstiges), Bemerkung, bei Angeboten „gültig bis“; optional Auftrag (Betrag, Datum) und Rechnungen (Betrag, Datum,
  bezahlt am).
* **Renovierung**: Die Vormerkungen aus „Renovierung planen“ erscheinen automatisch als Vorhaben „Renovierung <Jahr>“
  (abgeleitet, nicht kopiert – es gibt nur eine Quelle). Treiber, Entscheidung, Aufträge und Rechnungen dazu werden hier
  gespeichert (Schlüssel ``reno-<Jahr>``).

Gespeichert in ``importe/modern_vorhaben.json`` (mit gesichert, Rückgängig über ``kern._schritt``).
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import date

from belegung import speicher

DATEI = f"{speicher.IMPORT_ORDNER}/modern_vorhaben.json"

KATEGORIEN = ["Renovierung", "Möbel", "Technik", "Brandschutz", "Außenanlage", "IT", "Sonstiges"]
TREIBER = {"pflicht": "Pflicht", "risiko": "Risiko", "wirtschaftlichkeit": "Wirtschaftlichkeit", "kapazitaet": "Kapazität",
           "qualitaet": "Qualität"}
NACHWEIS = {"pflicht": "Rechtsgrundlage, Vorgabe oder Prüfprotokoll", "risiko": "Risikobeschreibung",
            "wirtschaftlichkeit": "Wirtschaftlichkeitsannahme", "kapazitaet": "Engpassbegründung",
            "qualitaet": "Qualitätsmangel"}
ENTSCHEIDUNG = {"idee": "Idee", "pruefung": "in Prüfung", "beantragt": "beantragt", "freigegeben": "freigegeben",
                "abgelehnt": "abgelehnt"}
PRIORITAET = {"hoch": "hoch", "mittel": "mittel", "niedrig": "niedrig"}
TOEPFE = {"bau": "Bau", "moebel": "Möbel", "sonstiges": "sonstiges"}
HERKUNFT = {"angebot": "Angebot", "eingabe": "Eingabe", "schaetzung": "Schätzung", "platzhalter": "Platzhalter"}


# ---- Speichern ---------------------------------------------------------------------------------------

def _roh() -> dict:
    return speicher.lesen(DATEI, {})


def _schreiben(roh: dict) -> None:
    speicher.schreiben(DATEI, roh)


def gespeichert() -> list[dict]:
    return [dict(v) for v in (_roh().get("vorhaben") or [])]


def _neu_id(praefix: str = "v") -> str:
    return f"{praefix}-{uuid.uuid4().hex[:8]}"


def leer_vorhaben(**werte) -> dict:
    return {"id": _neu_id(), "titel": "", "beschreibung": "", "kategorie": "Sonstiges", "haus": "", "prioritaet": "mittel",
            "treiber": "", "nachweis": "", "entscheidung": {"status": "idee", "datum": "", "wer": ""}, "massnahmen": [],
            "kosten": [], **werte}


def pruefen(v: dict) -> list[str]:
    """Fehler, die das Speichern verhindern."""
    fehler = []
    if not str(v.get("titel") or "").strip():
        fehler.append("Bitte einen Titel eintragen.")
    if v.get("treiber") not in TREIBER:
        fehler.append("Bitte genau einen Haupttreiber wählen.")
    elif not str(v.get("nachweis") or "").strip():
        fehler.append(f"Haupttreiber {TREIBER[v['treiber']]} braucht: {NACHWEIS[v['treiber']]}.")
    if (v.get("entscheidung") or {}).get("status") not in ENTSCHEIDUNG:
        fehler.append("Unbekannter Entscheidungsstatus.")
    for k in v.get("kosten") or []:
        if k.get("topf") not in TOEPFE or k.get("herkunft") not in HERKUNFT:
            fehler.append(f"Kostenposition „{k.get('titel', '')}“: Topf und Herkunft angeben.")
        try:
            int(k.get("jahr"))
            float(k.get("betrag") or 0)
        except (TypeError, ValueError):
            fehler.append(f"Kostenposition „{k.get('titel', '')}“: Jahr und Betrag als Zahl.")
    return fehler


def speichern(v: dict) -> str:
    """Anlegen oder ersetzen (nach ``id``). Wirft ValueError mit allen Fehlern."""
    if fehler := pruefen(v):
        raise ValueError(" ".join(fehler))
    roh = _roh()
    liste = [x for x in roh.get("vorhaben") or [] if x.get("id") != v["id"]]
    liste.append(v)
    roh["vorhaben"] = liste
    _schreiben(roh)
    return f"Vorhaben „{v['titel']}“ gespeichert"


def loeschen(vid: str) -> str:
    roh = _roh()
    vorher = roh.get("vorhaben") or []
    roh["vorhaben"] = [x for x in vorher if x.get("id") != vid]
    _schreiben(roh)
    return "Vorhaben gelöscht" if len(vorher) != len(roh["vorhaben"]) else "Nichts gelöscht"


def speichern_schritt(v: dict) -> str:
    from .kern import _schritt

    erg = []
    _schritt(f"Vorhaben: {v.get('titel', '')}", lambda: erg.append(speichern(v)), [DATEI])
    return erg[0]


def loeschen_schritt(vid: str, titel: str = "") -> str:
    from .kern import _schritt

    erg = []
    _schritt(f"Vorhaben gelöscht: {titel}", lambda: erg.append(loeschen(vid)), [DATEI])
    return erg[0]


# ---- Abgeleitete Status ------------------------------------------------------------------------------

def _d(t) -> date | None:
    try:
        return date.fromisoformat(str(t or "")[:10])
    except ValueError:
        return None


def umsetzung(v: dict, heute: date) -> str:
    """offen · terminiert · beauftragt · in Arbeit · abgeschlossen – aus Maßnahmen-Terminen und Aufträgen."""
    termine = [(_d(m.get("von")), _d(m.get("bis"))) for m in v.get("massnahmen") or []]
    termine = [(a, b) for a, b in termine if a and b]
    if termine and all(b < heute for _a, b in termine):
        return "abgeschlossen"
    if any(a <= heute <= b for a, b in termine):
        return "in Arbeit"
    if any((k.get("auftrag") or {}).get("betrag") for k in v.get("kosten") or []):
        return "beauftragt"
    return "terminiert" if termine else "offen"


def betraege(v: dict) -> dict:
    """Summen über alle Kostenpositionen: geplant, gebunden (Aufträge), abgerechnet (Rechnungen), bezahlt."""
    g = gb = ab = bz = 0.0
    for k in v.get("kosten") or []:
        g += float(k.get("betrag") or 0)
        gb += float((k.get("auftrag") or {}).get("betrag") or 0)
        for r in k.get("rechnungen") or []:
            ab += float(r.get("betrag") or 0)
            if r.get("bezahlt_am"):
                bz += float(r.get("betrag") or 0)
    return {"geplant": g, "gebunden": gb, "abgerechnet": ab, "bezahlt": bz}


def finanzen(v: dict) -> str:
    """geschätzt · gebunden · teilweise bezahlt · abgerechnet – automatisch aus Auftrag und Rechnungen."""
    b = betraege(v)
    if b["abgerechnet"] and b["bezahlt"] >= b["abgerechnet"] - .5 and b["abgerechnet"] >= max(b["gebunden"], 0) - .5:
        return "abgerechnet"
    if b["bezahlt"] or b["abgerechnet"]:
        return "teilweise bezahlt"
    if b["gebunden"]:
        return "gebunden"
    return "geschätzt"


def hinweise(v: dict, heute: date) -> list[str]:
    """Unmögliche bzw. fragwürdige Kombinationen (kein Speicherhindernis, aber sichtbar)."""
    e = (v.get("entscheidung") or {}).get("status", "idee")
    u, f = umsetzung(v, heute), finanzen(v)
    erg = []
    if e in ("idee", "pruefung", "abgelehnt") and u in ("beauftragt", "in Arbeit", "abgeschlossen"):
        erg.append(f"{ENTSCHEIDUNG[e]}, aber schon {u} – Entscheidung nachtragen?")
    if e != "freigegeben" and f in ("gebunden", "teilweise bezahlt", "abgerechnet"):
        erg.append(f"Geld ist {f}, die Entscheidung steht aber auf „{ENTSCHEIDUNG.get(e, e)}“.")
    if u == "abgeschlossen" and f in ("geschätzt", "gebunden"):
        erg.append("Abgeschlossen, aber noch keine Rechnung erfasst.")
    for k in v.get("kosten") or []:
        g = _d(k.get("gueltig_bis"))
        if k.get("herkunft") == "angebot" and g and g < heute and not (k.get("auftrag") or {}).get("betrag"):
            erg.append(f"Angebot „{k.get('titel', '')}“ ist seit {g:%d.%m.%Y} abgelaufen.")
    return erg


# ---- Renovierung als Vorhaben (abgeleitet) -----------------------------------------------------------

def reno_id(jahr: int) -> str:
    return f"reno-{jahr}"


def renovierung(zeilen: list, jahr: int, zusatz: dict | None = None) -> dict | None:
    """Vorhaben „Renovierung <Jahr>“ aus den vorgemerkten Plan-Zeilen (``renovierung_kern.PlanZeile``). Maßnahmen und
    geplante Kosten kommen aus der Planung; Treiber, Entscheidung, Aufträge und Rechnungen aus ``zusatz``."""
    vor = [z for z in zeilen if z.status == "vorgemerkt" and z.start.year == jahr]
    if not vor and not zusatz:
        return None
    z0 = zusatz or {}
    extra = {k["id"]: k for k in z0.get("kosten") or []}                   # Aufträge/Rechnungen je abgeleiteter Position
    massnahmen, kosten = [], []
    for z in vor:
        mid = f"{z.flur}|{z.art}|{z.start.isoformat()}"
        massnahmen.append({"id": mid, "titel": z.titel, "von": z.start.isoformat(), "bis": z.ende.isoformat(),
                           "zimmer": z.zimmer, "abgeleitet": True})
        for topf, betrag, hk in (("bau", z.kosten.instandhaltung, z.kosten.herkunft_bau),
                                 ("moebel", z.kosten.investition, z.kosten.herkunft_moebel)):
            if betrag:
                kid = f"{mid}|{topf}"
                kosten.append({"id": kid, "massnahme": mid, "titel": f"{z.titel} – {TOEPFE[topf]}", "betrag": round(betrag, 2),
                               "herkunft": hk if hk in HERKUNFT else "schaetzung", "jahr": jahr, "topf": topf,
                               "bemerkung": "aus „Renovierung planen“", "abgeleitet": True,
                               "auftrag": (extra.get(kid) or {}).get("auftrag"),
                               "rechnungen": (extra.get(kid) or {}).get("rechnungen") or []})
    kosten += [k for k in z0.get("kosten") or [] if not k.get("abgeleitet") and k["id"] not in {x["id"] for x in kosten}]
    return {**leer_vorhaben(), "id": reno_id(jahr), "titel": f"Renovierung {jahr}", "kategorie": "Renovierung",
            "beschreibung": f"{len(vor)} vorgemerkte Maßnahme(n) aus „Renovierung planen“", "haus": "",
            "treiber": z0.get("treiber", "qualitaet"), "nachweis": z0.get("nachweis", "Zimmer mit Bedarf (Klassen A/B/C)"),
            "prioritaet": z0.get("prioritaet", "hoch"),
            "entscheidung": z0.get("entscheidung") or {"status": "pruefung", "datum": "", "wer": ""},
            "massnahmen": massnahmen, "kosten": kosten, "abgeleitet": True}


def alle(zeilen_je_jahr: dict[int, list]) -> list[dict]:
    """Gespeicherte Vorhaben + abgeleitete Renovierungs-Vorhaben (je Jahr mit Vormerkungen)."""
    eigene = gespeichert()
    zus = {v["id"]: v for v in eigene if str(v.get("id", "")).startswith("reno-")}
    erg = [v for v in eigene if not str(v.get("id", "")).startswith("reno-")]
    for jahr, zeilen in sorted(zeilen_je_jahr.items()):
        if (r := renovierung(zeilen, jahr, zus.get(reno_id(jahr)))) is not None:
            erg.append(r)
    return erg


def zusatz_speichern(v: dict) -> str:
    """Für ein abgeleitetes Renovierungs-Vorhaben nur das Eigene speichern (Treiber, Entscheidung, eigene Positionen,
    Aufträge/Rechnungen zu abgeleiteten Positionen) – Maßnahmen und Plan-Beträge bleiben in der Planung."""
    z = {"id": v["id"], "titel": v["titel"], "treiber": v.get("treiber"), "nachweis": v.get("nachweis"),
         "prioritaet": v.get("prioritaet"), "entscheidung": v.get("entscheidung"), "kategorie": "Renovierung",
         "massnahmen": [],
         "kosten": [({"id": k["id"], "abgeleitet": True, "titel": k["titel"], "betrag": k["betrag"], "jahr": k["jahr"],
                      "topf": k["topf"], "herkunft": k["herkunft"], "auftrag": k.get("auftrag"),
                      "rechnungen": k.get("rechnungen") or []} if k.get("abgeleitet") else k)
                    for k in v.get("kosten") or []]}
    return speichern(z)


def speichern_auto_schritt(v: dict) -> str:
    from .kern import _schritt

    erg = []
    f = zusatz_speichern if v.get("abgeleitet") else speichern
    _schritt(f"Vorhaben: {v.get('titel', '')}", lambda: erg.append(f(v)), [DATEI])
    return erg[0]


# ---- Auswertung --------------------------------------------------------------------------------------

def summe_topf(vorhaben: list[dict], jahr: int, topf: str, ohne_renovierung: bool = True, nur_aktiv: bool = True) -> float:
    """Geplante Kosten eines Topfs im Haushaltsjahr – abgelehnte Vorhaben zählen nicht."""
    s = 0.0
    for v in vorhaben:
        if ohne_renovierung and v.get("abgeleitet"):
            continue
        if nur_aktiv and (v.get("entscheidung") or {}).get("status") == "abgelehnt":
            continue
        s += sum(float(k.get("betrag") or 0) for k in v.get("kosten") or [] if k.get("topf") == topf and int(k.get("jahr") or 0) == jahr)
    return s


@dataclass
class Zeile:
    v: dict
    entscheidung: str
    umsetzung: str
    finanzen: str
    summe: float
    jahre: list = field(default_factory=list)
    hinweise: list = field(default_factory=list)


def liste(vorhaben: list[dict], heute: date, kategorie: str = "", jahr: int | None = None) -> list[Zeile]:
    erg = []
    for v in vorhaben:
        if kategorie and v.get("kategorie") != kategorie:
            continue
        jahre = sorted({int(k.get("jahr") or 0) for k in v.get("kosten") or [] if k.get("jahr")})
        if jahr is not None and jahre and jahr not in jahre:
            continue
        erg.append(Zeile(v, ENTSCHEIDUNG.get((v.get("entscheidung") or {}).get("status"), "–"), umsetzung(v, heute),
                         finanzen(v), betraege(v)["geplant"], jahre, hinweise(v, heute)))
    prio = {"hoch": 0, "mittel": 1, "niedrig": 2}
    erg.sort(key=lambda z: (z.v.get("treiber") != "pflicht", prio.get(z.v.get("prioritaet"), 1), z.v.get("titel", "")))
    return erg
