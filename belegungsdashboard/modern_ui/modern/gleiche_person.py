"""1.67: Gebäudeplan-Eintrag (aus RIOS) und Person der Anreiseliste – „Ist das dieselbe Person?“

Der Gebäudeplan aus RIOS enthält keine Teilnehmernummer. Das Hauptprogramm verbindet einen Eintrag deshalb nur, wenn
alle Namensteile der Anreiseliste im Gebäudeplan stehen und die Zeiträume höchstens 3 Tage abweichen. Bei EMR (Anreise
am Vortag, Zimmer länger gebucht) oder anderer Schreibweise (zweiter Vorname, „ae“ statt „ä“) scheitert das: Die Person
steht dann zweimal da – im Gebäudeplan ohne Anreise-Daten, in der Anreiseliste „ohne Zimmer“; fehlt bei den Abreisen;
und wer sie von Hand zuteilt, belegt das Zimmer doppelt.

Hier:
* ``vorschlaege``: Gebäudeplan-Einträge ohne verbundene Person, zu denen eine Person der Anreiseliste ähnlich heißt
  (Umlaute und Groß-/Kleinschreibung egal, jeder Namensteil zu mind. 75 % gleich) und zeitlich passt (bis 14 Tage
  Abweichung). Nur solche Fälle werden gefragt – eindeutige verbindet das Hauptprogramm weiter selbst.
* ``verbinden``: „Ja, dieselbe Person“ – gespeichert je Standort (``importe/modern_gleiche_person.json``), übersteht ein
  neues Einlesen des Gebäudeplans. Die eigene Planung der Person wird auf das Zimmer laut Gebäudeplan gesetzt (der
  Gebäudeplan gilt), eine doppelte Planung in einem anderen Zimmer entfällt. Ein Rückgängig-Schritt.
* ``ablehnen``: „Nein, andere Person“ – wird nicht wieder gefragt.
* ``installieren``: hängt sich an ``zimmerplan.lage_bauen`` (nur in der neuen Oberfläche): Der Gebäudeplan-Eintrag
  bekommt den Schlüssel der Person (Abreisen, Suche, Termine finden das Zimmer), die eigene Planung im selben Zeitraum
  wird nicht zusätzlich gezählt.
Rein bis auf Lesen und Schreiben der Dateien.
"""

from __future__ import annotations

import functools
import re
import unicodedata
from dataclasses import dataclass
from datetime import date, datetime, timedelta

DATEI = "importe/modern_gleiche_person.json"
TOLERANZ = timedelta(days=14)       # Zeitraum Gebäudeplan ↔ Anreiseliste (EMR-Vortag, länger gebuchtes Zimmer …)
NAH = timedelta(days=30)            # gespeicherte Verbindung findet ihren Eintrag nach neuem Einlesen wieder
_ORIG: dict = {}


# ---- Namen vergleichen ------------------------------------------------------------------------------------------------

@functools.lru_cache(maxsize=8192)
def woerter(name: str) -> frozenset[str]:
    """Namensteile ohne Umlaut-/Akzent- und Schreibweisen-Unterschiede („Müller“ = „Mueller“ = „MÜLLER“)."""
    s = (name or "").lower().replace("ß", "ss").replace("ä", "ae").replace("ö", "oe").replace("ü", "ue")
    s = "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))
    return frozenset(w for w in re.split(r"[^a-z0-9]+", s) if len(w) > 1)


SCHWELLE = 0.75                     # 1.70: je Namensteil mindestens 75 % gleiche Buchstaben


@functools.lru_cache(maxsize=65536)
def _teil_aehnlich(x: str, y: str) -> float:
    from difflib import SequenceMatcher

    return 1.0 if x == y else SequenceMatcher(None, x, y).ratio()


def aehnlich(person: str, eintrag: str) -> tuple[float, frozenset[str]]:
    """(Übereinstimmung 0–1, passende Namensteile).

    1.70: Jeder Teil des kürzeren Namens (Nachname UND Vorname) braucht im anderen Namen einen Teil mit mindestens
    75 % gleichen Buchstaben – „Schmidt/Schmitt“, „Erika/Erica“ passen, „Meyer, Anna“/„Meyer, Paul“ nicht. Ein
    zusätzlicher zweiter Vorname stört nicht. Ein einzelner Namensteil reicht nie (sonst jeder „Meyer“).
    Ergebnis: Mittelwert der Teil-Übereinstimmungen, 0 wenn ein Teil nicht passt."""
    a, b = woerter(person), woerter(eintrag)
    kurz, lang = (a, b) if len(a) <= len(b) else (b, a)
    if len(kurz) < 2:
        return 0.0, frozenset()
    werte, gleich = [], set()
    for w in kurz:
        bester = max(lang, key=lambda v: _teil_aehnlich(w, v))
        q = _teil_aehnlich(w, bester)
        if q < SCHWELLE:
            return 0.0, frozenset()
        werte.append(q)
        gleich.add(w)
    return sum(werte) / len(werte), frozenset(gleich)


def gleicher_name(a: str, b: str) -> bool:
    return bool(woerter(a)) and woerter(a) == woerter(b)


def _abstand(v1: date, b1: date, v2: date, b2: date) -> int:
    """Tage zwischen zwei Zeiträumen (0 = sie überschneiden sich)."""
    if v1 <= b2 and v2 <= b1:
        return 0
    return min(abs((v1 - b2).days), abs((v2 - b1).days))


# ---- Speichern ---------------------------------------------------------------------------------------------------------

def laden() -> dict:
    from belegung import speicher

    d = speicher.lesen(DATEI, {})
    d = d if isinstance(d, dict) else {}
    return {"verbunden": [x for x in d.get("verbunden", []) if isinstance(x, dict) and x.get("person")],
            "nein": [x for x in d.get("nein", []) if isinstance(x, dict) and x.get("person")]}


def _speichern(d: dict) -> None:
    from belegung import speicher

    speicher.schreiben(DATEI, d)


def _gp_kennung(name: str, zimmer: str) -> str:
    return f"{zimmer}|{' '.join(sorted(woerter(name)))}"


# ---- Vorschläge --------------------------------------------------------------------------------------------------------

@dataclass
class Vorschlag:
    gp_name: str             # Name laut Gebäudeplan
    zimmer: str              # Zimmer-ID laut Gebäudeplan
    gp_von: date
    gp_bis: date
    gp_massnahme: str
    person: str              # Schlüssel der Person (Anreiseliste/UWT)
    name: str
    von: date
    bis: date
    massnahme: str
    gruppe: str
    anteil: float            # gleiche Namensteile (0–1)
    tage: int                # Abstand der Zeiträume in Tagen (0 = überschneiden sich)
    geplant: str = ""        # Zimmer-ID der eigenen Planung der Person (wenn vorhanden – sonst doppelt)

    @property
    def schluessel(self) -> str:
        return f"{self.person}#{_gp_kennung(self.gp_name, self.zimmer)}"

    @property
    def grund(self) -> str:
        t = ("Namen gleich (andere Schreibweise)" if self.anteil >= 1
             else f"Namen zu {round(self.anteil * 100)} % gleich (wenige Buchstaben anders)")
        t += " · Zeitraum überschneidet sich" if self.tage == 0 else f" · Zeitraum {self.tage} Tage auseinander"
        return t


def _streng(b, eintrag) -> bool:
    """Verbindet das Hauptprogramm die beiden schon selbst? (alle Namensteile enthalten, ±3 Tage)"""
    from belegung import zimmerplan as zp

    w = zp._namenswoerter(b.name)
    t = timedelta(days=3)
    return bool(w) and w <= zp._namenswoerter(eintrag.name) and b.von <= eintrag.bis + t and eintrag.von - t <= b.bis


def gp_eintraege(stand, heute: date) -> list:
    """Belegungen laut Gebäudeplan (nicht eigene Planung), die noch laufen oder kommen, mit echtem Namen."""
    from belegung import zimmerplan as zp

    erg = []
    for b in (stand.plan.belegungen if stand.plan else []):
        if (b.art == "belegt" and b.name and not b.person and not zp.name_fehlt(b.name) and b.name != zp.PIVOT_NAME
                and b.bis >= heute - timedelta(days=7) and zp.gruppe_von(b.massnahme or "", "") != "Mieter"):
            erg.append(b)
    return erg


def vorschlaege(stand, heute: date, daten: dict | None = None) -> list[Vorschlag]:
    """Mögliche gleiche Personen – je Gebäudeplan-Eintrag ohne Verbindung alle passenden Personen.

    1.72: je Datenstand nur einmal berechnet (Cockpit und jede Anreise im Zuteilen fragten sonst jedes Mal neu – bei
    vielen Gebäudeplan-Einträgen dauerte das Sekunden je Aufruf)."""
    if daten is not None:
        return _vorschlaege(stand, heute, daten)
    d = laden()
    schluessel = (heute, repr(d))
    alt = getattr(stand, "_gleich_cache", None)
    if alt is not None and alt[0] == schluessel:
        return list(alt[1])
    erg = _vorschlaege(stand, heute, d)
    try:
        stand._gleich_cache = (schluessel, erg)
    except AttributeError:                         # z. B. Testobjekte ohne Attribute
        pass
    return list(erg)


def _vorschlaege(stand, heute: date, daten: dict) -> list[Vorschlag]:
    from belegung import zimmerplan as zp

    nein = {(x["person"], x.get("gp", "")) for x in daten["nein"]}
    verbunden_p = {x["person"] for x in daten["verbunden"]}
    verbunden_gp = {_gp_kennung(x.get("gp_name", ""), x.get("zimmer", "")) for x in daten["verbunden"]}
    personen = [b for b in stand.bedarf if not b.schluessel.startswith("mv:") and b.schluessel not in verbunden_p
                and b.bis >= heute - timedelta(days=7)]
    eintraege = gp_eintraege(stand, heute)
    # 1.72: Namensteile nur einmal zerlegen; zuerst der (billige) Zeitraum, dann der Name
    p_streng = [(b, zp._namenswoerter(b.name)) for b in personen]
    e_streng = [(e, zp._namenswoerter(e.name)) for e in eintraege]
    drei = timedelta(days=3)
    # Wen das Hauptprogramm schon verbindet, der ist geklärt – Person wie Eintrag
    geklaert_p, geklaert_e = set(), set()
    for e, ew in e_streng:
        for b, bw in p_streng:
            if b.von <= e.bis + drei and e.von - drei <= b.bis and bw and bw <= ew:
                geklaert_p.add(b.schluessel)
                geklaert_e.add(id(e))
    geplant = {z["person"]: z["zimmer"] for z in stand.zuweisungen}
    offen_p = [b for b in personen if b.schluessel not in geklaert_p]
    erg = []
    for e in eintraege:
        kennung = _gp_kennung(e.name, e.zimmer)
        if id(e) in geklaert_e or kennung in verbunden_gp:
            continue
        for b in offen_p:
            tage = _abstand(b.von, b.bis, e.von, e.bis)
            if tage > TOLERANZ.days or (b.schluessel, kennung) in nein:
                continue
            anteil, gleich = aehnlich(b.name, e.name)
            if anteil < SCHWELLE or not any(len(w) >= 3 for w in gleich):
                continue
            erg.append(Vorschlag(e.name, e.zimmer, e.von, e.bis, e.massnahme or "", b.schluessel, b.name, b.von, b.bis,
                                 b.massnahme, b.gruppe, anteil, tage, geplant.get(b.schluessel, "")))
    return sorted(erg, key=lambda v: (v.von, v.name, -v.anteil, v.tage))


def fuer_person(stand, person: str, heute: date) -> list[Vorschlag]:
    return [v for v in vorschlaege(stand, heute) if v.person == person]


# ---- Entscheiden -------------------------------------------------------------------------------------------------------

def verbinden(v: Vorschlag) -> str:
    """„Ja, dieselbe Person“: Verbindung merken, eigene Planung = Zimmer laut Gebäudeplan (Gebäudeplan gilt)."""
    from belegung import protokoll, speicher
    from belegung import zimmerplan as zp

    from .kern import _schritt

    def tun():
        d = laden()
        d["verbunden"] = [x for x in d["verbunden"] if x["person"] != v.person] + [{
            "person": v.person, "name": v.name, "gp_name": v.gp_name, "zimmer": v.zimmer, "von": v.gp_von.isoformat(),
            "bis": v.gp_bis.isoformat(), "am": datetime.now().isoformat(timespec="seconds")}]
        _speichern(d)
        alle = [z for z in zp.zuweisungen_laden() if z["person"] != v.person]
        alle.append({"person": v.person, "name": v.name, "massnahme": v.massnahme, "gruppe": v.gruppe, "geschlecht": "",
                     "zimmer": v.zimmer, "von": v.von.isoformat(), "bis": v.bis.isoformat(), "vorrang": "plan",
                     "quelle": "gleiche Person (Gebäudeplan)"})
        speicher.schreiben(zp.ZUWEISUNGEN, {"zuweisungen": alle})
        protokoll.eintragen([{"aktion": "Gleiche Person bestätigt", "name": v.name, "person": v.person,
                              "alt": v.geplant or "", "neu": v.zimmer, "von": v.von.isoformat(),
                              "quelle": f"Gebäudeplan: {v.gp_name}"}])
    _schritt(f"Gleiche Person: {v.name}", tun, [DATEI, zp.ZUWEISUNGEN])
    doppelt = f" – die Planung in {v.geplant.split('-', 1)[-1]} entfällt" if v.geplant and v.geplant != v.zimmer else ""
    return f"{v.name} = {v.gp_name} (Gebäudeplan, Zimmer {v.zimmer.split('-', 1)[-1]}){doppelt}"


def ablehnen(v: Vorschlag) -> str:
    from .kern import _schritt

    def tun():
        d = laden()
        d["nein"].append({"person": v.person, "gp": _gp_kennung(v.gp_name, v.zimmer), "name": v.name,
                          "gp_name": v.gp_name, "am": datetime.now().isoformat(timespec="seconds")})
        _speichern(d)
    _schritt(f"Andere Person: {v.name}", tun, [DATEI])
    return f"{v.name} und {v.gp_name} sind verschiedene Personen – wird nicht wieder gefragt"


def loesen(person: str) -> str:
    """Verbindung aufheben (die Planung bleibt im Zimmer, bis sie geändert wird)."""
    from .kern import _schritt

    d = laden()
    x = next((x for x in d["verbunden"] if x["person"] == person), None)
    if x is None:
        raise ValueError("Diese Verbindung gibt es nicht mehr.")

    def tun():
        d2 = laden()
        d2["verbunden"] = [y for y in d2["verbunden"] if y["person"] != person]
        _speichern(d2)
    _schritt(f"Verbindung gelöst: {x.get('name', '')}", tun, [DATEI])
    return f"Verbindung {x.get('name', '')} ↔ {x.get('gp_name', '')} gelöst"


# ---- Im Planstand wirken -----------------------------------------------------------------------------------------------

def anwenden(lage, verbunden: list[dict]) -> int:
    """Gebäudeplan-Einträge der bestätigten Verbindungen bekommen den Schlüssel der Person; deren eigene Planung im
    gleichen Zeitraum entfällt (sonst stünde die Person doppelt im Plan). Gibt die Zahl der angewandten zurück."""
    n = 0
    for x in verbunden:
        person, zid = x["person"], x.get("zimmer", "")
        try:
            von, bis = date.fromisoformat(x["von"]), date.fromisoformat(x["bis"])
        except (KeyError, TypeError, ValueError):
            continue
        eintrag = next((b for b in lage.belegungen.get(zid, []) if b.art == "belegt" and not b.person
                        and gleicher_name(b.name, x.get("gp_name", "")) and b.von <= bis + NAH and von - NAH <= b.bis),
                       None)
        if eintrag is None:                       # nicht mehr im Gebäudeplan → die eigene Planung gilt wie bisher
            continue
        for z, bs in lage.belegungen.items():
            lage.belegungen[z] = [b for b in bs if not (b.person == person and b is not eintrag and b.art == "geplant"
                                                        and b.von <= eintrag.bis + NAH and eintrag.von - NAH <= b.bis)]
        eintrag.person = person
        lage.abgleich = [a for a in (lage.abgleich or []) if a.person != person]
        n += 1
    return n


def _lage_bauen(*args, **kwargs):
    lage = _ORIG["lage_bauen"](*args, **kwargs)
    try:
        verbunden = laden()["verbunden"]
        if verbunden:
            anwenden(lage, verbunden)
    except Exception:                              # noqa: BLE001 – die Verbindung darf das Laden nie verhindern
        pass
    return lage


def installieren() -> None:
    from belegung import zimmerplan as zp

    if _ORIG:
        return
    _ORIG["lage_bauen"] = zp.lage_bauen
    zp.lage_bauen = _lage_bauen


def zuruecksetzen() -> None:
    from belegung import zimmerplan as zp

    if _ORIG:
        zp.lage_bauen = _ORIG.pop("lage_bauen")
