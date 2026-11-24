"""1.51: Hausordnung bestätigen – eigener QR-Code je Zimmer, Bestätigung gilt für die Person, die dort wohnt.

* Zweites Formular in Forms (Zimmer und Code vorausgefüllt wie bei den Mängeln, dazu Name und der Haken „gelesen“).
  Power Automate legt je Antwort eine Datei in denselben OneDrive-Ordner wie die QR-Meldungen – mit der Kennung
  ``INNTERNAT-HO`` (Zeilen ID, Zeit, Zimmer, Code, Name, Gelesen, ENDE). Die Mängel-Einlese überspringt diese Dateien.
* Zuordnung: Zimmer (Prüfcode gewinnt) → wer an dem Tag dort wohnt (oder in den nächsten Tagen einzieht); bei zwei
  Personen im Zimmer entscheidet der eingetragene Name.
* **Gilt je Aufenthalt:** Eine Bestätigung zählt nur für den Aufenthalt, in dem sie abgegeben wurde. Zieht jemand
  aus, ist das Zimmer für die nächste Person wieder „offen“ – ohne dass jemand etwas löschen muss.
* Mieter sind ausgenommen (Mietvertrag). „Von Hand bestätigen“ für Papier o. Ä., mit Rückgängig.
Rein bis auf das Lesen und Schreiben der Dateien.
"""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path

from belegung import speicher
from belegung import zimmerplan as zp

DATEI = f"{speicher.IMPORT_ORDNER}/modern_hausordnung.json"
KENNUNG = "INNTERNAT-HO"
VORLAUF = 3                 # Tage: wer in den nächsten 3 Tagen einzieht, darf schon bestätigen
VORSCHAU = 7                # Liste: auch, wer in den nächsten 7 Tagen einzieht
AUFHEBEN_TAGE = 400
FELDER = {"id": "id", "zeit": "zeit", "zimmer": "zimmer", "code": "code", "name": "name", "gelesen": "gelesen"}


def _lesen() -> dict:
    try:
        d = speicher.lesen(DATEI, {})
    except Exception:                                   # noqa: BLE001
        d = {}
    return d if isinstance(d, dict) else {}


def _schreiben(d: dict) -> None:
    speicher.schreiben(DATEI, d)


def link() -> str:
    from .qr_meldungen_kern import _platzhalter_norm

    return _platzhalter_norm(str(_lesen().get("link") or ""))


def link_setzen(wert: str) -> str:
    from .kern import _schritt
    from .qr_meldungen_kern import CODE_PLATZHALTER, PLATZHALTER, _platzhalter_norm

    wert = _platzhalter_norm((wert or "").strip())
    if wert and not re.match(r"^https://", wert, re.I):
        raise ValueError("Bitte den vollständigen Forms-Link einfügen (beginnt mit https://).")

    def tun():
        d = _lesen()
        d["link"] = wert
        _schreiben(d)
    _schritt("Hausordnung-Link", tun, [DATEI])
    if not wert:
        return "Hausordnung-Link entfernt"
    if PLATZHALTER in wert and CODE_PLATZHALTER in wert:
        return "Hausordnung-Link gespeichert – jedes Etikett trägt Zimmernummer und Prüfcode"
    return f"Hausordnung-Link gespeichert – ohne {PLATZHALTER}/{CODE_PLATZHALTER} lässt sich das Zimmer nicht sicher zuordnen"


# ---- Einlesen -------------------------------------------------------------------------------------------------------

@dataclass
class Roh:
    id: str
    zeit: str            # ISO (Minuten)
    zimmer_text: str
    code: str
    name: str


def ist_hausordnung(text: str) -> bool:
    return KENNUNG in (text or "").upper()


def parsen(text: str, eintrag: str = "", empfangen: datetime | None = None) -> Roh | None:
    """Eine Datei/Mail mit ``INNTERNAT-HO`` → Roh (None, wenn es keine ist oder „gelesen“ fehlt)."""
    from .qr_meldungen_kern import _auswahl, _pa_zeit

    t = re.sub(r"<[^>]+>", "\n", str(text or "")).replace("\r", "").replace("&nbsp;", " ")
    if not ist_hausordnung(t):
        return None
    schluessel = r"(?:ID|Zeit|Zimmer|Code|Name|Gelesen)\s*:"
    if len(re.findall(rf"(?im)^\s*{schluessel}", t)) < 2:
        t = re.sub(rf"\s+(?={schluessel}|ENDE\s*$)", "\n", t, flags=re.I)
    werte: dict[str, str] = {}
    for zeile in t.split("\n"):
        z = zeile.strip()
        if z.upper() == "ENDE":
            break
        m = re.match(r"^(ID|Zeit|Zimmer|Code|Name|Gelesen)\s*:\s*(.*)$", z, re.I)
        if m:
            werte[FELDER[m.group(1).lower()]] = m.group(2).strip()
    gelesen = _auswahl(werte.get("gelesen", "")).strip().lower()
    if not gelesen or gelesen in ("nein", "no", "false", "0"):
        return None
    rid = werte.get("id") or eintrag
    if not rid or not (werte.get("zimmer") or werte.get("code")):
        return None
    zeit = _pa_zeit(werte.get("zeit") or "") or (empfangen or datetime.now()).isoformat(timespec="minutes")
    return Roh(f"ho|{rid}", zeit, werte.get("zimmer", ""), werte.get("code", ""), " ".join(werte.get("name", "").split()))


def ordner_lesen(pfad: str) -> tuple[list[Roh], str]:
    from .qr_meldungen_kern import ORDNER_ENDUNGEN, _text_datei

    d = Path(pfad)
    if not d.is_dir():
        return [], f"QR-Ordner nicht gefunden: {pfad}"
    erg = []
    try:
        dateien = [x for x in d.iterdir() if x.is_file() and x.suffix.lower() in ORDNER_ENDUNGEN]
    except OSError as exc:
        return [], f"QR-Ordner nicht lesbar: {exc}"
    for x in dateien:
        try:
            text = _text_datei(x)
            mt = datetime.fromtimestamp(x.stat().st_mtime).replace(second=0, microsecond=0)
        except OSError:
            continue
        r = parsen(text, x.stem, mt)
        if r is not None:
            erg.append(r)
    return erg, ""


def _woerter(name: str) -> frozenset[str]:
    return zp._namenswoerter(name or "")


def _bewohner(stand, zid: str, tag: date, vorlauf: int = VORLAUF) -> list:
    erg = []
    for b in stand.lage.belegungen.get(zid, []):
        if b.art not in ("belegt", "geplant") or not b.name or b.name == zp.PIVOT_NAME:
            continue
        if zp.belegung_gruppe(b) == "Mieter":
            continue
        if b.von - timedelta(days=vorlauf) <= tag <= b.bis:
            erg.append(b)
    return erg


def zuordnen(stand, zid: str, tag: date, name: str):
    """Wer im Zimmer ``zid`` am ``tag`` wohnt (bzw. bald einzieht) – bei mehreren nach dem Namen."""
    leute = _bewohner(stand, zid, tag)
    if not leute:
        return None
    w = _woerter(name)
    if w:
        passend = [b for b in leute if _woerter(b.name) & w]
        if passend:
            return max(passend, key=lambda b: len(_woerter(b.name) & w))
    return leute[0] if len(leute) == 1 else None


def _person(b) -> str:
    return b.person or f"name:{b.name.lower()}"


def einlesen(ordner: str | None = None) -> tuple[int, str]:
    """Neue Bestätigungen aus dem QR-Ordner übernehmen (unter der Sperre). (Anzahl neu, Fehlertext)."""
    from . import netz_kern
    from . import qr_meldungen_kern as qm
    from .kern import _zimmer_aus_text

    ordner = ordner if ordner is not None else qm.dateiordner()
    if not ordner:
        return 0, ""
    roh, fehler = ordner_lesen(ordner)
    if fehler:
        return 0, fehler
    bekannt = {x.get("id") for x in _lesen().get("bestaetigungen") or []}
    neu_roh = [r for r in roh if r.id not in bekannt]
    if not neu_roh:
        return 0, ""
    with netz_kern.sperre():
        stand = zp.laden()
        d = _lesen()
        bekannt = {x.get("id") for x in d.get("bestaetigungen") or []}
        g = qm.geheim_lesen(qm._lesen())
        codes = qm.code_tabelle([z.id for z in stand.zimmer], g) if g else None
        n = 0
        for r in neu_roh:
            if r.id in bekannt:
                continue
            zid = _zimmer_aus_text(stand, r.zimmer_text) or ""
            zid, _etikett, hinweis = qm.pruefen(r.zimmer_text, zid, r.code, codes, bool(codes))
            try:
                tag = datetime.fromisoformat(r.zeit).date()
            except ValueError:
                tag = date.today()
            b = zuordnen(stand, zid, tag, r.name) if zid else None
            d.setdefault("bestaetigungen", []).append({
                "id": r.id, "zeit": r.zeit, "zimmer": zid, "zimmer_text": r.zimmer_text, "name": r.name,
                "person": _person(b) if b else "", "person_name": b.name if b else "", "hinweis": hinweis, "hand": False})
            n += 1
        grenze = (date.today() - timedelta(days=AUFHEBEN_TAGE)).isoformat()
        d["bestaetigungen"] = [x for x in d.get("bestaetigungen") or [] if str(x.get("zeit", "")) >= grenze]
        _schreiben(d)
    return n, ""


# ---- Status je Bewohner ---------------------------------------------------------------------------------------------

@dataclass
class HZeile:
    zimmer: str
    name: str
    person: str
    von: date
    bis: date
    bestaetigt: str = ""        # ISO-Zeit der Bestätigung, "" = offen
    quelle: str = ""            # QR | von Hand
    bid: str = ""               # ID der Bestätigung (zum Zurücknehmen)


def _gilt(x: dict, b, zid: str) -> bool:
    """Bestätigung ``x`` gehört zum Aufenthalt ``b`` in ``zid``: im Zeitraum (ab ``VORLAUF`` Tage vorher) und zur
    Person (Schlüssel) bzw. – ohne Zuordnung – im selben Zimmer mit passendem Namen."""
    try:
        tag = datetime.fromisoformat(str(x.get("zeit"))).date()
    except ValueError:
        return False
    if not (b.von - timedelta(days=VORLAUF) <= tag <= b.bis):
        return False
    if x.get("person"):
        return x["person"] == _person(b)
    return x.get("zimmer") == zid and bool(_woerter(x.get("name", "")) & _woerter(b.name))


def status(stand, heute: date, vorschau: int = VORSCHAU) -> list[HZeile]:
    """Alle, die heute im Haus sind oder in den nächsten ``vorschau`` Tagen einziehen (ohne Mieter) – offen zuerst."""
    best = _lesen().get("bestaetigungen") or []
    erg = []
    for zid, bs in stand.lage.belegungen.items():
        for b in bs:
            if b.art not in ("belegt", "geplant") or not b.name or b.name == zp.PIVOT_NAME:
                continue
            if zp.belegung_gruppe(b) == "Mieter" or b.bis < heute or b.von > heute + timedelta(days=vorschau):
                continue
            treffer = [x for x in best if _gilt(x, b, zid)]
            x = max(treffer, key=lambda t: str(t.get("zeit"))) if treffer else None
            erg.append(HZeile(zid, b.name, _person(b), b.von, b.bis, str(x.get("zeit")) if x else "",
                              ("von Hand" if x.get("hand") else "QR") if x else "", str(x.get("id")) if x else ""))
    return sorted(erg, key=lambda z: (bool(z.bestaetigt), z.von, z.zimmer))


def offene(stand, heute: date) -> list[HZeile]:
    return [z for z in status(stand, heute) if not z.bestaetigt and z.von <= heute]


def von_hand(zimmer: str, person: str, name: str, jetzt: datetime | None = None) -> str:
    from .kern import _schritt, kurz

    jetzt = jetzt or datetime.now()

    def tun():
        d = _lesen()
        d.setdefault("bestaetigungen", []).append({
            "id": f"hand|{uuid.uuid4().hex[:10]}", "zeit": jetzt.isoformat(timespec="minutes"), "zimmer": zimmer,
            "zimmer_text": kurz(zimmer), "name": name, "person": person, "person_name": name, "hinweis": "", "hand": True})
        _schreiben(d)
    _schritt(f"Hausordnung bestätigt: {name}", tun, [DATEI])
    return f"Hausordnung für {name} als bestätigt vermerkt"


def zuruecknehmen(bid: str) -> str:
    from .kern import _schritt

    def tun():
        d = _lesen()
        d["bestaetigungen"] = [x for x in d.get("bestaetigungen") or [] if x.get("id") != bid]
        _schreiben(d)
    _schritt("Hausordnung-Bestätigung zurückgenommen", tun, [DATEI])
    return "Bestätigung zurückgenommen – die Person steht wieder auf „offen“"
