"""Austauschdatei zwischen altem und neuem Programm (1.05). Rein, ohne Oberfläche.

Wer mit dem alten, wer mit dem neuen Programm arbeitet, hat je eigene Daten. Die Austauschdatei trägt die Änderungen
an **Anreisen und Abreisen, Zimmerplanung, Umzügen/Zimmertausch, Mietverträgen** (dazu Geschlecht/Tier-Angaben,
UWT-Automatik und Nichtanreisen) von einem Programm ins andere – in beide Richtungen.

So funktioniert es:

* **Basis:** Jede Installation merkt sich nach jedem Export und Import den gemeinsamen Stand (je Eintrag nur einen
  Prüfwert, ``importe/austausch_basis.json``). Exportiert wird, was sich seitdem geändert hat: *neu*, *geändert*,
  *entfernt*. Gibt es noch keine Basis (erster Austausch), wird der ganze Stand exportiert.
* **Prüfwerte:** Jeder Eintrag trägt einen SHA-256-Prüfwert seines Inhalts, die Datei einen über alles. Beim Einlesen
  wird beides nachgerechnet – eine beschädigte oder von Hand veränderte Datei wird abgelehnt.
* **Abgleich in drei Schritten:** Für jede Änderung steht in der Datei, wie der Eintrag *vorher* war (Prüfwert der
  Basis) und wie er *jetzt* ist. Beim Einlesen gilt:
  - Eintrag hier noch wie vorher → Änderung wird übernommen.
  - Eintrag hier schon genauso → nichts zu tun.
  - Eintrag hier inzwischen anders geändert → **Konflikt**: Sie entscheiden je Eintrag (Standard: eigenen behalten).
* Behält man bei einem Konflikt den eigenen Stand, geht er beim nächsten Export zurück – so kommen beide Seiten zum
  selben Ergebnis.

Örtliche Felder (Erinnerungs-Termine in Outlook) werden nie übertragen und beim Einlesen behalten.
"""

from __future__ import annotations

import hashlib
import json
import os
import socket
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any, Callable

FORMAT = "INNternat-Austausch"
VERSION = 1
BASIS_DATEI = "importe/austausch_basis.json"


# ---- Bereiche -------------------------------------------------------------------------------------------------------

def _person_schluessel(r: dict) -> str:
    if r.get("tn_id"):
        return f"id:{r['tn_id']}"
    return f"name:{str(r.get('name', '')).lower()}|{r.get('anreise', '')}"


@dataclass(frozen=True)
class Bereich:
    name: str                        # Kennung in der Datei
    titel: str                       # für Menschen
    datei: str                       # Datei im Datenordner (wie im Hauptprogramm)
    feld: str | None                 # Liste unter diesem Schlüssel; None = die Datei ist ein Wörterbuch Schlüssel → Eintrag
    schluessel: Callable[[Any], str] | None = None
    lokal: tuple[str, ...] = ()      # Felder, die nie übertragen werden


BEREICHE: tuple[Bereich, ...] = (
    Bereich("personen", "Anreisen und Abreisen", "importe/anreisen_goslar.json", "personen", _person_schluessel,
            ("erinnerung_tage", "erinnerung_kanal", "erinnerung_id", "erledigt")),
    Bereich("zuweisungen", "Zimmerplanung", "zimmer_zuweisungen.json", "zuweisungen",
            lambda r: f"{r.get('person', '')}|{r.get('von', '')}"),
    Bereich("umzuege", "Umzüge und Zimmertausch", "importe/umzuege.json", "umzuege", lambda r: str(r.get("id", ""))),
    Bereich("mieter", "Mietverträge", "mieter.json", "mieter", lambda r: str(r.get("nr", ""))),
    Bereich("angaben", "Geschlecht und Tier (Zimmerplan)", "zimmer_personen.json", None),
    Bereich("uwt_auto", "UWT automatisch zugeteilt", "importe/uwt_auto_zugeteilt.json", "personen", lambda r: str(r)),
    Bereich("nichtanreise", "Nicht angereist", "modern_nichtanreise.json", None),
)
NACH_NAME = {b.name: b for b in BEREICHE}


def _kanonisch(x: Any) -> str:
    return json.dumps(x, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)


def pruefwert(x: Any) -> str:
    return hashlib.sha256(_kanonisch(x).encode("utf-8")).hexdigest()[:20]


def _ohne_lokal(b: Bereich, r: Any) -> Any:
    if isinstance(r, dict) and b.lokal:
        return {k: v for k, v in r.items() if k not in b.lokal}
    return r


def eintraege(b: Bereich, roh: Any) -> dict[str, Any]:
    """Datei-Inhalt → {Schlüssel: Eintrag (ohne örtliche Felder)}. Doppelte Schlüssel bekommen „#2“, „#3“ …"""
    erg: dict[str, Any] = {}
    if b.feld is None:
        for k, v in (roh or {}).items() if isinstance(roh, dict) else []:
            erg[str(k)] = _ohne_lokal(b, v)
        return erg
    liste = (roh or {}).get(b.feld, []) if isinstance(roh, dict) else []
    for r in liste:
        k = b.schluessel(r) if b.schluessel else str(r)
        n, k0 = 1, k
        while k in erg:
            n += 1
            k = f"{k0}#{n}"
        erg[k] = _ohne_lokal(b, r)
    return erg


def zurueckschreiben(b: Bereich, roh: Any, neu: dict[str, Any]) -> Any:
    """{Schlüssel: Eintrag} → Datei-Inhalt. Reihenfolge der bestehenden Einträge bleibt; örtliche Felder bleiben."""
    if b.feld is None:
        return dict(neu)
    alt = eintraege(b, roh)
    alt_roh: dict[str, Any] = {}
    liste = (roh or {}).get(b.feld, []) if isinstance(roh, dict) else []
    for k, r in zip(alt.keys(), liste):
        alt_roh[k] = r
    aus = []
    for k in list(alt.keys()) + [k for k in neu if k not in alt]:
        if k not in neu:
            continue
        r = neu[k]
        if isinstance(r, dict) and b.lokal and isinstance(alt_roh.get(k), dict):
            r = {**r, **{f: alt_roh[k][f] for f in b.lokal if f in alt_roh[k]}}
        aus.append(r)
    erg = dict(roh) if isinstance(roh, dict) else {}
    erg[b.feld] = aus
    return erg


# ---- Stand, Basis, Export -------------------------------------------------------------------------------------------

def stand(lesen: Callable[[str, Any], Any]) -> dict[str, dict[str, Any]]:
    """Aktueller Stand aller Bereiche: {Bereich: {Schlüssel: Eintrag}}. ``lesen(datei, standard)`` wie speicher.lesen."""
    return {b.name: eintraege(b, lesen(b.datei, {})) for b in BEREICHE}


def pruefwerte(st: dict[str, dict[str, Any]]) -> dict[str, dict[str, str]]:
    return {n: {k: pruefwert(v) for k, v in xs.items()} for n, xs in st.items()}


@dataclass
class Aenderung:
    bereich: str
    schluessel: str
    art: str                         # neu | geaendert | entfernt | stand
    vorher: str | None               # Prüfwert in der Basis (None = gab es nicht / unbekannt)
    nachher: str | None              # Prüfwert jetzt (None = entfernt)
    eintrag: Any = None

    def zu_dict(self) -> dict:
        return {"bereich": self.bereich, "schluessel": self.schluessel, "art": self.art, "vorher": self.vorher,
                "nachher": self.nachher, "eintrag": self.eintrag}


def aenderungen(st: dict[str, dict[str, Any]], basis: dict[str, dict[str, str]] | None) -> list[Aenderung]:
    """Was sich seit der Basis geändert hat. Ohne Basis: der ganze Stand (Art „stand“)."""
    erg: list[Aenderung] = []
    for b in BEREICHE:
        jetzt = st.get(b.name, {})
        if basis is None:
            erg += [Aenderung(b.name, k, "stand", None, pruefwert(v), v) for k, v in jetzt.items()]
            continue
        vorher = basis.get(b.name, {})
        for k, v in jetzt.items():
            p = pruefwert(v)
            if k not in vorher:
                erg.append(Aenderung(b.name, k, "neu", None, p, v))
            elif vorher[k] != p:
                erg.append(Aenderung(b.name, k, "geaendert", vorher[k], p, v))
        for k, p in vorher.items():
            if k not in jetzt:
                erg.append(Aenderung(b.name, k, "entfernt", p, None, None))
    return erg


def absender() -> str:
    try:
        nutzer = os.environ.get("USERNAME") or os.environ.get("USER") or ""
    except Exception:                                  # noqa: BLE001
        nutzer = ""
    try:
        pc = socket.gethostname()
    except Exception:                                  # noqa: BLE001
        pc = ""
    return " · ".join(x for x in (nutzer, pc) if x)


def datei_bauen(liste: list[Aenderung], programm: str, von: str | None = None, jetzt: datetime | None = None) -> dict:
    """Austauschdatei (als Wörterbuch) mit Prüfwerten je Eintrag und über alles."""
    jetzt = jetzt or datetime.now()
    inhalt = {"format": FORMAT, "version": VERSION, "erstellt": jetzt.isoformat(timespec="seconds"),
              "von": von if von is not None else absender(), "programm": programm,
              "art": "stand" if liste and all(x.art == "stand" for x in liste) else "aenderungen",
              "aenderungen": [x.zu_dict() for x in liste]}
    inhalt["pruefwert"] = pruefwert({k: v for k, v in inhalt.items() if k != "pruefwert"})
    return inhalt


def dateiname(programm: str, jetzt: datetime | None = None) -> str:
    jetzt = jetzt or datetime.now()
    return f"INNternat-Austausch_{programm}_{jetzt:%Y-%m-%d_%H%M}.json"


# ---- Einlesen -------------------------------------------------------------------------------------------------------

class AustauschFehler(ValueError):
    pass


def datei_pruefen(inhalt: Any) -> list[Aenderung]:
    """Prüft Format und Prüfwerte; Rückgabe: die Änderungen. AustauschFehler mit verständlichem Text."""
    if not isinstance(inhalt, dict) or inhalt.get("format") != FORMAT:
        raise AustauschFehler("Das ist keine INNternat-Austauschdatei.")
    if int(inhalt.get("version", 0)) > VERSION:
        raise AustauschFehler("Die Datei stammt von einer neueren Programmversion – bitte zuerst aktualisieren.")
    soll = inhalt.get("pruefwert")
    if not soll or pruefwert({k: v for k, v in inhalt.items() if k != "pruefwert"}) != soll:
        raise AustauschFehler("Prüfwert stimmt nicht – die Datei ist beschädigt oder wurde verändert. Nichts übernommen.")
    erg = []
    for d in inhalt.get("aenderungen") or []:
        if d.get("bereich") not in NACH_NAME:
            raise AustauschFehler(f"Unbekannter Bereich „{d.get('bereich')}“ – bitte Programm aktualisieren.")
        a = Aenderung(d["bereich"], str(d["schluessel"]), d["art"], d.get("vorher"), d.get("nachher"), d.get("eintrag"))
        if a.nachher is not None and pruefwert(a.eintrag) != a.nachher:
            raise AustauschFehler(f"Prüfwert eines Eintrags stimmt nicht ({a.bereich} · {a.schluessel}). Nichts übernommen.")
        erg.append(a)
    return erg


@dataclass
class Punkt:
    aenderung: Aenderung
    status: str                      # uebernehmen | schon_da | konflikt
    hier: Any = None                 # Eintrag hier (bei Konflikt zum Vergleich)
    uebernehmen: bool = True         # Konflikt: Standard nein (eigenen behalten)


def abgleichen(liste: list[Aenderung], st: dict[str, dict[str, Any]]) -> list[Punkt]:
    erg = []
    for a in liste:
        hier = st.get(a.bereich, {}).get(a.schluessel)
        p_hier = pruefwert(hier) if hier is not None else None
        if p_hier == a.nachher:
            erg.append(Punkt(a, "schon_da", hier, False))
        elif p_hier == a.vorher and not (a.art == "stand" and hier is not None):
            erg.append(Punkt(a, "uebernehmen", hier, True))
        else:
            erg.append(Punkt(a, "konflikt", hier, False))
    return erg


def anwenden(punkte: list[Punkt], lesen: Callable[[str, Any], Any], schreiben: Callable[[str, Any], None]) -> dict:
    """Schreibt die gewählten Punkte. Rückgabe: Anzahl je Art (übernommen, entfernt) und geänderte Dateien."""
    gewaehlt = [p for p in punkte if p.uebernehmen and p.status in ("uebernehmen", "konflikt")]
    zahl = {"neu": 0, "geaendert": 0, "entfernt": 0, "dateien": []}
    for b in BEREICHE:
        xs = [p for p in gewaehlt if p.aenderung.bereich == b.name]
        if not xs:
            continue
        roh = lesen(b.datei, {})
        alle = eintraege(b, roh)
        for p in xs:
            a = p.aenderung
            if a.nachher is None:
                if alle.pop(a.schluessel, None) is not None:
                    zahl["entfernt"] += 1
            else:
                zahl["geaendert" if a.schluessel in alle else "neu"] += 1
                alle[a.schluessel] = a.eintrag
        schreiben(b.datei, zurueckschreiben(b, roh, alle))
        zahl["dateien"].append(b.datei)
    return zahl


def basis_nach_import(basis: dict | None, punkte: list[Punkt]) -> dict:
    """Neue Basis nach dem Einlesen: übernommene und schon gleiche Einträge = Stand der Datei; behaltene Konflikte
    = Prüfwert der Datei (damit der eigene Stand beim nächsten Export als Änderung zurückgeht)."""
    # ohne Basis (erster Austausch): nur, was jetzt beide haben – eigene übrige Einträge gehen beim nächsten Export mit
    neu = {n: dict(xs) for n, xs in (basis or {}).items()}
    for p in punkte:
        a = p.aenderung
        ziel = neu.setdefault(a.bereich, {})
        if a.nachher is None:
            if p.status == "konflikt" and not p.uebernehmen and p.hier is not None:
                ziel[a.schluessel] = a.vorher or "entfernt"
            else:
                ziel.pop(a.schluessel, None)
        else:
            ziel[a.schluessel] = a.nachher
    return neu


def basis_lesen(lesen: Callable[[str, Any], Any]) -> dict | None:
    roh = lesen(BASIS_DATEI, None)
    return roh.get("pruefwerte") if isinstance(roh, dict) and isinstance(roh.get("pruefwerte"), dict) else None


def basis_schreiben(schreiben: Callable[[str, Any], None], pw: dict, jetzt: datetime | None = None) -> None:
    schreiben(BASIS_DATEI, {"stand": (jetzt or datetime.now()).isoformat(timespec="seconds"), "pruefwerte": pw})


# ---- Beschreibung für Menschen --------------------------------------------------------------------------------------

def _d(x: Any) -> str:
    try:
        return date.fromisoformat(str(x)[:10]).strftime("%d.%m.%Y")
    except (TypeError, ValueError):
        return str(x or "–")


def beschreibung(bereich: str, eintrag: Any, schluessel: str = "") -> str:
    e = eintrag if isinstance(eintrag, dict) else {}
    z = lambda x: str(x or "").removeprefix("GS-")     # noqa: E731
    if bereich == "personen":
        return (f"{e.get('name', schluessel)} · {e.get('massnahme', '')} · Anreise {_d(e.get('anreise'))}"
                f" · Abreise {_d(e.get('abreise')) if e.get('abreise') else 'offen'}"
                + ("" if e.get("internat", True) is not False else " · ohne Internat"))
    if bereich == "zuweisungen":
        return f"{e.get('name', e.get('person', schluessel))} → Zimmer {z(e.get('zimmer'))} · {_d(e.get('von'))} – {_d(e.get('bis'))}"
    if bereich == "umzuege":
        return (f"{e.get('name', '')}: {z(e.get('von_zimmer'))} → {z(e.get('nach_zimmer'))} ab {_d(e.get('ab'))}"
                + (f" · {e.get('status')}" if e.get("status") else ""))
    if bereich == "mieter":
        return (f"Mietvertrag {e.get('nr', '')}: {e.get('vorname', '')} {e.get('nachname', '')} · Zimmer "
                f"{z(e.get('zimmer'))} · {_d(e.get('von'))} – {_d(e.get('bis'))}")
    if bereich == "angaben":
        teile = [f"{k} {v}" for k, v in e.items()]
        return f"{schluessel}: " + (", ".join(teile) or "–")
    if bereich == "nichtanreise":
        return f"{e.get('name', schluessel)} nicht angereist (Anreise {_d(e.get('anreise'))})"
    return f"{schluessel}"


ART_TEXT = {"neu": "neu", "geaendert": "geändert", "entfernt": "entfernt", "stand": "Stand"}
STATUS_TEXT = {"uebernehmen": "wird übernommen", "schon_da": "schon gleich", "konflikt": "Konflikt – hier anders geändert"}


@dataclass
class Bilanz:
    uebernehmen: int = 0
    schon_da: int = 0
    konflikt: int = 0
    je_bereich: dict = field(default_factory=dict)


def bilanz(punkte: list[Punkt]) -> Bilanz:
    b = Bilanz()
    for p in punkte:
        setattr(b, p.status, getattr(b, p.status) + 1)
        b.je_bereich[p.aenderung.bereich] = b.je_bereich.get(p.aenderung.bereich, 0) + 1
    return b
