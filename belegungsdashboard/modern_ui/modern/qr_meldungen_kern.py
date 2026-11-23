"""1.28: Meldungen per QR-Code (Microsoft Forms, anonym) – einlesen, zuordnen, als Mangel übernehmen. Rein, ohne NiceGUI.

Ablauf
------
1. In Forms ein Formular „Mangel melden“ (anonym: „Jeder kann antworten“) mit den Fragen *Zimmer*, *Art* und
   *Beschreibung*. Über „… → Vorausgefüllte URL abrufen“ bei *Zimmer* den Platzhalter ``ZIMMER`` eintragen und den Link
   kopieren. Diesen Link in INNternat einfügen (gilt für alle PCs). Je Zimmer ersetzt INNternat ``ZIMMER`` durch die
   Zimmernummer – jedes Etikett öffnet das Formular mit schon eingetragenem Zimmer.
2. Die Antworten speichert Forms in einer Excel-Datei auf OneDrive/SharePoint („In Excel öffnen“). Mit OneDrive
   synchronisiert liegt sie als normale Datei auf dem PC; ihren Pfad trägt man auf diesem PC ein (je PC, weil der
   OneDrive-Pfad je Benutzer anders ist – es reicht EIN PC).
3. INNternat liest die Datei alle paar Minuten (nur, wenn sie sich geändert hat), merkt sich jede Antwort genau einmal
   (Forms-ID + Startzeit) und legt sie als „neu“ im Datenordner ab – alle PCs sehen dieselben Meldungen.
4. 1.30 – Prüfcode: Eine vierte Frage „Code (bitte nicht ändern)“, beim vorausgefüllten Link mit ``CODE``. Jedes
   Etikett trägt neben der Zimmernummer einen 5-stelligen Code (HMAC aus Zimmer-ID und einem Geheimwert im Datenordner).
   Ändert ein Gast die Zimmernummer, erkennt INNternat am Code das Etikett, schlägt dieses Zimmer vor und markiert die
   Meldung. Forms kann vorausgefüllte Felder nicht sperren – der Code macht Änderungen sichtbar.
5. Eine Meldung wird NIE von selbst zum Mangel (den QR-Code kann jeder scannen): „Übernehmen“ legt den Mangel an
   (Art vorgeschlagen, änderbar; Rückgängig wie immer), „Verwerfen“ blendet sie aus.

Gespeichert in ``importe/modern_qr_meldungen.json``: ``{"link": str, "meldungen": [{…}]}``.
"""

from __future__ import annotations

import hashlib
import hmac
import re
import secrets
import shutil
import tempfile
from dataclasses import asdict, dataclass, field
from datetime import date, datetime, timezone
from pathlib import Path
from urllib.parse import quote

from belegung import maengel as mg
from belegung import speicher

DATEI = "importe/modern_qr_meldungen.json"
PLATZHALTER = "ZIMMER"
CODE_PLATZHALTER = "CODE"
CODE_ZEICHEN = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"   # ohne 0/O und 1/I – nicht zu verwechseln
CODE_LAENGE = 5
EINSTELLUNG_DATEI = "qr_antwortdatei"            # je PC (netz_kern.persoenlich)
TAKT_MINUTEN = 5
DRINGEND = mg.STUFE_DRINGEND

# Art aus Freitext vorschlagen: (Mangelart, Muster) – Reihenfolge zählt (Rauchmelder vor Geruch/Rauch …)
ART_MUSTER = [
    ("rauchmelder", r"rauchmelder|brandmelder|piept"),
    ("schimmel", r"schimmel|feucht|stockflecken"),
    ("ungeziefer", r"ungeziefer|wanze|kakerlak|schabe|käfer|maus|mäuse|ratte|motte|ameise"),
    ("heizung", r"heizung|heizkörper|thermostat|kalt im zimmer|zu kalt|heizt"),
    ("abfluss", r"abfluss|verstopf|läuft nicht ab"),
    ("wasser", r"wasserhahn|tropft|undicht|\bleck|kein warmes wasser|\bwasser\b"),
    ("elektrik", r"licht|lampe|steckdose|strom|sicherung|birne|leuchte|kabel"),
    ("bad", r"dusche|toilette|\bwc\b|klo|spülung|waschbecken|\bbad\b|badezimmer"),
    ("fenster", r"fenster|rollo|jalousie|rollladen|vorhang|gardine"),
    ("tuer", r"tür|schloss|schlüssel|klinke|karte geht nicht"),
    ("matratze", r"matratze"),
    ("moebel", r"möbel|schrank|tisch|stuhl|bett|regal|schublade|sessel"),
    ("geruch", r"geruch|riecht|stinkt|rauch"),
    ("wand", r"\bwand\b|wände|tapete|loch in|\bputz\b"),
    ("boden_dreckig", r"(teppich|boden)\w*\W+(\w+\W+){0,3}(dreck|schmutz|fleck)|(dreck|schmutz|fleck)\w*\W+(\w+\W+){0,3}(teppich|boden)"),
    ("boden_kaputt", r"teppich|boden|fliese|laminat"),
    ("grundreinigung", r"reinig|dreck|schmutz|sauber|putzen|staub|müll"),
]

SPALTEN = {
    "id": ("id",),
    "start": ("startzeit", "start time", "starttime"),
    "ende": ("fertigstellungszeit", "completion time", "abschlusszeit"),
    "zimmer": ("zimmer", "raum", "room", "zimmernummer"),
    "code": ("code", "prüfcode", "pruefcode"),
    "art": ("art", "kategorie", "was ist", "worum", "thema", "category", "type"),
    "text": ("beschreib", "was ist passiert", "nachricht", "hinweis", "bemerk", "details", "kommentar", "description",
             "text"),
}


@dataclass
class Meldung:
    id: str
    zeit: str                    # ISO (Fertigstellungszeit, sonst Startzeit)
    zimmer_text: str             # wie eingegeben
    zimmer: str                  # Zimmer-ID, leer = nicht erkannt
    art_text: str
    text: str
    art: str                     # vorgeschlagene Mangelart (Katalog)
    status: str = "neu"          # neu | uebernommen | verworfen
    erledigt: str = ""           # ISO-Datum
    hinweis: str = ""
    code: str = ""               # 1.30: Prüfcode aus dem Formular
    etikett: str = ""            # 1.30: Zimmer-ID laut Prüfcode (vom Etikett)
    fm: str = ""                 # 1.46: an FM weitergeleitet am (ISO-Datum)
    archiviert: str = ""         # 1.46: archiviert am (ISO-Datum) – erscheint dann nur noch unter „Archiv“

    @property
    def dringend(self) -> bool:
        return self.art in DRINGEND

    @property
    def zeit_text(self) -> str:
        try:
            return f"{datetime.fromisoformat(self.zeit):%d.%m. %H:%M}"
        except ValueError:
            return self.zeit


# ---- Speicher ----------------------------------------------------------------------------------------------------

def _lesen() -> dict:
    try:
        d = speicher.lesen(DATEI, {})
    except Exception:                                   # noqa: BLE001 – beschädigt: leer anfangen, nicht abstürzen
        d = {}
    return d if isinstance(d, dict) else {}


def _schreiben(d: dict) -> None:
    speicher.schreiben(DATEI, d)


def _platzhalter_norm(wert: str) -> str:
    """1.45: In Forms vorausgefüllte Werte „Zimmer“/„code“ o. Ä. gelten wie ZIMMER/CODE (nur ganze Link-Werte)."""
    return re.sub(r"=(zimmer|code)(?=&|#|$)", lambda m: "=" + m.group(1).upper(), wert or "", flags=re.I)


def link() -> str:
    return _platzhalter_norm(str(_lesen().get("link") or ""))


def link_setzen(wert: str) -> str:
    wert = _platzhalter_norm((wert or "").strip())
    if wert and not re.match(r"^https://", wert, re.I):
        raise ValueError("Bitte den vollständigen Forms-Link einfügen (beginnt mit https://).")
    from .kern import _schritt

    def aktion():
        d = _lesen()
        d["link"] = wert
        _schreiben(d)
    _schritt("QR-Formular-Link", aktion, [DATEI])
    if not wert:
        return "Formular-Link entfernt"
    if PLATZHALTER in wert and CODE_PLATZHALTER in wert:
        return "Formular-Link gespeichert – jedes Etikett trägt Zimmernummer und Prüfcode"
    return ("Formular-Link gespeichert – jedes Etikett trägt seine Zimmernummer (ohne Prüfcode: im Formular die Frage "
            f"„Code“ mit {CODE_PLATZHALTER} vorausfüllen)" if PLATZHALTER in wert else
            f"Formular-Link gespeichert – ohne Platzhalter {PLATZHALTER}: alle Etiketten öffnen dasselbe Formular, das "
            "Zimmer wird dort eingetragen")


def meldungen(status: str | None = None) -> list[Meldung]:
    erg = []
    for x in _lesen().get("meldungen") or []:
        try:
            m = Meldung(**{k: x.get(k, "") for k in Meldung.__dataclass_fields__})
        except TypeError:
            continue
        if status is None or (status == ARCHIV and m.archiviert) or (m.status == status and not m.archiviert):
            erg.append(m)
    return sorted(erg, key=lambda m: m.zeit, reverse=True)


# ---- 1.46: an FM weiterleiten, Archiv -----------------------------------------------------------------------------

ARCHIV = "archiv"


def fm_vorlage(m: Meldung, kurz=lambda z: z.removeprefix("GS-")) -> tuple[str, str, str]:
    """(Zimmer kurz, Mangelart, Notiz) für die FM-Mail – die Notiz trägt Eingang und Text der Meldung."""
    wo = kurz(m.zimmer) if m.zimmer else (m.zimmer_text or "")
    notiz = f"Meldung per QR-Code vom {m.zeit_text}: {m.text or m.art_text or '(ohne Text)'}"
    if m.art_text and m.text:
        notiz += f" (Auswahl: {m.art_text})"
    return wo, mg.NAMEN.get(m.art, m.art) if m.art else "", notiz


def fm_vermerken(mid: str, heute: date | None = None) -> str:
    """Vermerk „an FM weitergeleitet am …“ (ein Schritt, rückgängig machbar)."""
    from .kern import _schritt

    heute = heute or date.today()

    def aktion():
        d = _lesen()
        _finden(d, mid)["fm"] = heute.isoformat()
        _schreiben(d)
    _schritt("QR-Meldung an FM", aktion, [DATEI])
    return "Als „an FM weitergeleitet“ vermerkt"


def archivieren(mids: list[str], an: bool = True, heute: date | None = None) -> str:
    """Erledigte (übernommen/verworfen) ins Archiv legen bzw. zurückholen. Neue bleiben immer sichtbar."""
    from .kern import _schritt

    heute = heute or date.today()
    n = {"z": 0}

    def aktion():
        d = _lesen()
        for mid in mids:
            x = _finden(d, mid)
            if an and x.get("status") == "neu":
                continue
            x["archiviert"] = heute.isoformat() if an else ""
            n["z"] += 1
        _schreiben(d)
    if not mids:
        return "Nichts zu archivieren"
    _schritt("QR-Meldungen archiviert" if an else "QR-Meldung zurückgeholt", aktion, [DATEI])
    if an:
        return f"{n['z']} Meldung(en) archiviert" if n["z"] else "Neue Meldungen werden nicht archiviert – erst prüfen"
    return "Meldung zurückgeholt"


def erledigte_ids() -> list[str]:
    return [m.id for m in meldungen() if m.status in ("uebernommen", "verworfen") and not m.archiviert]


def neue() -> list[Meldung]:
    return meldungen("neu")


# ---- QR-Link je Zimmer ---------------------------------------------------------------------------------------------

def zimmer_link(vorlage: str, kurz: str, code: str = "") -> str:
    """Link für ein Zimmer: ``ZIMMER`` durch die (URL-kodierte) Zimmernummer, ``CODE`` durch den Prüfcode ersetzen."""
    erg = vorlage.replace(PLATZHALTER, quote(kurz, safe="")) if PLATZHALTER in vorlage else vorlage
    return erg.replace(CODE_PLATZHALTER, code) if code and CODE_PLATZHALTER in erg else erg


# ---- 1.30: Prüfcode ----------------------------------------------------------------------------------------------

def code_fuer(zid: str, geheim: str) -> str:
    """5 Zeichen, fest je Zimmer und Installation; ohne den Geheimwert nicht zu erraten."""
    h = hmac.new(geheim.encode(), zid.encode(), hashlib.sha256).digest()
    n = int.from_bytes(h[:8], "big")
    return "".join(CODE_ZEICHEN[(n >> (5 * i)) & 31] for i in range(CODE_LAENGE))


def code_norm(text) -> str:
    """Wie eingegeben → vergleichbar (Groß-/Kleinschreibung und Leer-/Sonderzeichen egal)."""
    return re.sub(r"[^0-9A-Za-z]", "", str(text or "")).upper()


def code_tabelle(zids, geheim: str) -> dict[str, str]:
    """Code → Zimmer-ID. Kommt ein Code doppelt vor (sehr selten), gilt er für keines der Zimmer."""
    erg: dict[str, str] = {}
    doppelt = set()
    for zid in zids:
        c = code_fuer(zid, geheim)
        if c in erg:
            doppelt.add(c)
        erg[c] = zid
    return {c: z for c, z in erg.items() if c not in doppelt}


def geheim_lesen(d: dict | None = None) -> str:
    return str((d if d is not None else _lesen()).get("geheim") or "")


def geheim() -> str:
    """Geheimwert der Installation (Datenordner, alle PCs gleich) – beim ersten Druck angelegt."""
    if g := geheim_lesen():
        return g
    from . import netz_kern

    with netz_kern.sperre():
        d = _lesen()
        if not d.get("geheim"):
            d["geheim"] = secrets.token_hex(16)
            _schreiben(d)
        return d["geheim"]


# ---- Einlesen ------------------------------------------------------------------------------------------------------

def _norm(s) -> str:
    return re.sub(r"\s+", " ", str(s or "")).strip().lower()


def spalten_finden(kopf: list) -> dict[str, int]:
    """Spalten der Forms-Datei erkennen (deutsch/englisch). Fragen dürfen etwas anders heißen („Zimmernummer“ …)."""
    k = [_norm(x) for x in kopf]
    erg: dict[str, int] = {}
    for feld in ("id", "start", "ende"):
        for i, t in enumerate(k):
            if any(t == s or t.startswith(s) for s in SPALTEN[feld]) and feld not in erg:
                erg[feld] = i
    fest = set(erg.values()) | {i for i, t in enumerate(k) if t in ("e-mail", "email", "name", "zeitpunkt der letzten änderung",
                                                                     "last modified time")}
    for feld in ("zimmer", "code", "text", "art"):
        for i, t in enumerate(k):
            if i in fest or i in erg.values():
                continue
            if any(re.search(rf"(^|\W){re.escape(s)}", t) for s in SPALTEN[feld]):
                erg[feld] = i
                break
    rest = [i for i, t in enumerate(k) if t and i not in fest and i not in erg.values()]
    if "text" not in erg and rest:                      # Fragen heißen anders: letzte freie Frage = Beschreibung
        erg["text"] = rest.pop()
    if "art" not in erg and rest:
        erg["art"] = rest[0]
    return erg


def _zeit(x) -> str:
    if isinstance(x, datetime):
        return x.isoformat(timespec="minutes")
    if isinstance(x, date):
        return datetime(x.year, x.month, x.day).isoformat(timespec="minutes")
    t = str(x or "").strip()
    for f in ("%d.%m.%Y %H:%M:%S", "%d.%m.%Y %H:%M", "%m/%d/%Y %H:%M:%S", "%m/%d/%y %H:%M:%S", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(t, f).isoformat(timespec="minutes")
        except ValueError:
            pass
    return t


@dataclass
class Roh:
    id: str
    zeit: str
    zimmer_text: str
    art_text: str
    text: str
    code: str = ""


@dataclass
class Ergebnis:
    zeilen: list[Roh] = field(default_factory=list)
    fehler: str = ""
    unbekannt: list[str] = field(default_factory=list)  # 1.45: Dateien im QR-Ordner, die keine QR-Meldung sind
    gesamt: int = 0


def lesen_xlsx(pfad: Path) -> Ergebnis:
    """Antworten aus der Forms-Excel-Datei. Erst kopieren: OneDrive/Excel halten die Datei oft geöffnet."""
    from openpyxl import load_workbook

    pfad = Path(pfad)
    if not pfad.exists():
        return Ergebnis(fehler=f"Antwortdatei nicht gefunden: {pfad}")
    with tempfile.TemporaryDirectory(prefix="innternat_qr_") as tmp:
        kopie = Path(tmp) / "antworten.xlsx"
        try:
            shutil.copy2(pfad, kopie)
            wb = load_workbook(kopie, read_only=True, data_only=True)
        except Exception as exc:                        # noqa: BLE001 – gesperrt, halb synchronisiert, kein Excel …
            return Ergebnis(fehler=f"Antwortdatei nicht lesbar: {exc}")
        try:
            zeilen = list(wb.worksheets[0].iter_rows(values_only=True))
        finally:
            wb.close()
    if not zeilen:
        return Ergebnis(fehler="Die Antwortdatei ist leer.")
    sp = spalten_finden(list(zeilen[0]))
    if "zimmer" not in sp:
        return Ergebnis(fehler="In der Antwortdatei fehlt eine Spalte „Zimmer“ – die Frage im Formular muss das Wort "
                               "„Zimmer“ enthalten.")
    if "id" not in sp:
        return Ergebnis(fehler="In der Antwortdatei fehlt die Spalte „ID“ – ist das die Antwortdatei von Forms?")

    def wert(z, feld):
        i = sp.get(feld)
        return z[i] if i is not None and i < len(z) else None
    erg = Ergebnis()
    for z in zeilen[1:]:
        if z is None or all(v in (None, "") for v in z):
            continue
        rid = str(wert(z, "id") or "").strip()
        if not rid:
            continue
        zeit = _zeit(wert(z, "ende") or wert(z, "start"))
        erg.zeilen.append(Roh(f"{rid}|{_zeit(wert(z, 'start'))}", zeit, str(wert(z, "zimmer") or "").strip(),
                              str(wert(z, "art") or "").strip(), str(wert(z, "text") or "").strip(),
                              str(wert(z, "code") or "").strip()))
    return erg


def art_vorschlag(*texte: str) -> str:
    t = " ".join(texte).lower()
    for art, muster in ART_MUSTER:
        if re.search(muster, t):
            return art
    return "sonstiges"


ZIMMER_IM_TEXT = re.compile(r"(?:GS[- ]?)?\d(?:\.\d)?\s*[- /]?\s*[A-Z]?\d{2,4}[A-Z]?", re.I)


def zimmer_finden(text: str, aus_text) -> str:
    """Zimmer-ID aus der Eingabe („2-408“, „Zimmer 2408“, „2/408“ …). ``aus_text`` = kern._zimmer_aus_text mit Stand."""
    text = (text or "").strip()
    if not text:
        return ""
    if zid := aus_text(text):
        return zid
    for m in ZIMMER_IM_TEXT.finditer(text):
        if zid := aus_text(m.group(0)):
            return zid
    nur = re.sub(r"\D", "", text)                       # „2408“ → „2-408“
    if 4 <= len(nur) <= 5 and (zid := aus_text(f"{nur[0]}-{nur[1:]}")):
        return zid
    return ""


def pruefen(zimmer_text: str, zimmer: str, code: str, codes: dict[str, str] | None, erwartet: bool,
            kurz=lambda z: z.removeprefix("GS-")) -> tuple[str, str, str]:
    """1.30: Zimmer gegen den Prüfcode prüfen → (Zimmer-ID, Etikett-ID, Hinweis). Der Code gewinnt: er stammt vom
    Etikett, die Zimmernummer kann der Gast überschrieben haben."""
    c = code_norm(code)
    if not c or codes is None:
        return zimmer, "", ("ohne Prüfcode – Zimmer bitte prüfen" if erwartet and codes is not None else "")
    etikett = codes.get(c, "")
    if not etikett:
        return zimmer, "", f"Prüfcode „{code}“ unbekannt – Zimmer bitte genau prüfen"
    if zimmer != etikett:
        return etikett, etikett, (f"Zimmer im Formular geändert („{zimmer_text or 'leer'}“) – Etikett war {kurz(etikett)}")
    return zimmer, etikett, ""


def zusammenfuehren(d: dict, zeilen: list[Roh], aus_text, codes: dict[str, str] | None = None,
                    code_erwartet: bool = False, kurz=lambda z: z.removeprefix("GS-")) -> list[Meldung]:
    """Neue Antworten in den gespeicherten Stand übernehmen (je ID genau einmal). Gibt die neuen Meldungen zurück."""
    bekannt = {x.get("id") for x in d.get("meldungen") or []}
    neu = []
    for r in zeilen:
        if r.id in bekannt:
            continue
        bekannt.add(r.id)
        zid, etikett, hinweis = pruefen(r.zimmer_text, zimmer_finden(r.zimmer_text, aus_text), r.code, codes,
                                        code_erwartet, kurz)
        m = Meldung(r.id, r.zeit, r.zimmer_text[:60], zid, r.art_text[:80], r.text[:1000],
                    art_vorschlag(r.art_text, r.text), hinweis=hinweis, code=code_norm(r.code)[:12], etikett=etikett)
        neu.append(m)
    if neu:
        d.setdefault("meldungen", []).extend(asdict(m) for m in neu)
    return neu


def antwortdatei() -> str:
    from .netz_kern import persoenlich

    return str(persoenlich(EINSTELLUNG_DATEI, "", je_standort=True) or "")


def antwortdatei_setzen(pfad: str) -> str:
    from .netz_kern import persoenlich_setzen

    pfad = (pfad or "").strip().strip('"')
    if pfad and not pfad.lower().endswith(".xlsx"):
        raise ValueError("Bitte den Pfad der Excel-Datei (.xlsx) mit den Forms-Antworten angeben.")
    if pfad and not Path(pfad).exists():
        raise ValueError(f"Die Datei gibt es auf diesem PC nicht: {pfad}")
    persoenlich_setzen(EINSTELLUNG_DATEI, pfad, je_standort=True)
    return "Antwortdatei gespeichert – sie wird alle paar Minuten gelesen" if pfad else "Antwortdatei entfernt"


_STAND = {"mtime": None, "pfad": "", "gelesen": None, "fehler": "", "neu": 0}   # 1.31: letztes Einlesen (je PC)


def einlesen(pfad: str | None = None, immer: bool = False, ordner: str | None = None,
             dateien: str | None = None) -> tuple[list[Meldung], str]:
    """Neue Antworten holen und ablegen (unter der Schreibsperre – mehrere PCs können einlesen). Drei Quellen, je PC:
    die Forms-Excel-Datei (nur wenn sie sich geändert hat, außer ``immer``), – 1.32 – der Outlook-Ordner, in den
    Power Automate je Antwort eine Mail legt, und – 1.44 – ein OneDrive-Ordner mit je einer Textdatei pro Antwort.
    (neue, Fehlertext)."""
    from belegung import zimmerplan as zp

    from . import netz_kern
    from .kern import _zimmer_aus_text, kurz

    pfad = pfad if pfad is not None else antwortdatei()
    ordner = ordner if ordner is not None else outlook_ordner()
    dateien = dateien if dateien is not None else dateiordner()
    if not pfad and not ordner and not dateien:
        return [], ""
    zeilen: list[Roh] = []
    fehler: list[str] = []
    gelesen = False
    mt = None
    xlsx_ok = False
    if pfad:
        try:
            mt = Path(pfad).stat().st_mtime
        except OSError:
            if not ordner and not dateien:
                return [], f"Antwortdatei nicht gefunden: {pfad}"
            fehler.append(f"Antwortdatei nicht gefunden: {pfad}")
        else:
            if immer or _STAND["pfad"] != pfad or _STAND["mtime"] != mt:
                erg = lesen_xlsx(Path(pfad))
                gelesen = True
                if erg.fehler:
                    fehler.append(erg.fehler)
                else:
                    zeilen += erg.zeilen
                    xlsx_ok = True
    if ordner:
        erg = outlook_lesen(ordner)
        gelesen = True
        if erg.fehler:
            fehler.append(erg.fehler)
        zeilen += erg.zeilen
    if dateien:
        erg = ordner_lesen(dateien)
        gelesen = True
        if erg.fehler:
            fehler.append(erg.fehler)
        elif erg.unbekannt and not erg.zeilen:
            fehler.append(f"{len(erg.unbekannt)} Datei(en) im QR-Ordner ohne erkennbare Meldung (z. B. "
                          f"{erg.unbekannt[0]}) – Dateiinhalt in Power Automate prüfen")
        zeilen += erg.zeilen
    if not gelesen:
        return [], ""
    text = " · ".join(fehler)
    _STAND.update(gelesen=datetime.now(), fehler=text, neu=0)
    bekannt = {x.get("id") for x in _lesen().get("meldungen") or []}
    neu: list[Meldung] = []
    if any(r.id not in bekannt for r in zeilen):        # nur dann die Sperre holen
        with netz_kern.sperre():
            stand = zp.laden()
            d = _lesen()
            g = geheim_lesen(d)
            codes = code_tabelle([z.id for z in stand.zimmer], g) if g else None
            neu = zusammenfuehren(d, zeilen, lambda t: _zimmer_aus_text(stand, t), codes,
                                  CODE_PLATZHALTER in str(d.get("link") or ""), kurz)
            if neu:
                _schreiben(d)
    if xlsx_ok:
        _STAND.update(mtime=mt, pfad=pfad)
    _STAND.update(neu=len(neu))
    return neu, text


# ---- Erledigen ------------------------------------------------------------------------------------------------------

def _finden(d: dict, mid: str) -> dict:
    for x in d.get("meldungen") or []:
        if x.get("id") == mid:
            return x
    raise ValueError("Diese Meldung gibt es nicht mehr – bitte neu laden.")


def uebernehmen(mid: str, art: str, zimmer: str, heute: date | None = None) -> str:
    """Meldung als Mangel anlegen (ein Schritt, ein Rückgängig)."""
    from .kern import _schritt, kurz

    heute = heute or date.today()
    if art not in mg.NAMEN:
        raise ValueError("Bitte eine Mangelart wählen.")
    if not zimmer:
        raise ValueError("Bitte zuerst das Zimmer wählen – die Eingabe im Formular wurde nicht erkannt.")
    erg = {}

    def aktion():
        d = _lesen()
        x = _finden(d, mid)
        if x.get("status") != "neu":
            raise ValueError("Diese Meldung wurde schon bearbeitet.")
        notiz = f"QR-Meldung {Meldung(**{k: x.get(k, '') for k in Meldung.__dataclass_fields__}).zeit_text}: " \
                f"{x.get('text') or x.get('art_text') or ''}".strip()
        neu = mg.setzen(zimmer, art, True, heute=heute, notiz=notiz[:300])
        x.update(status="uebernommen", erledigt=heute.isoformat(), zimmer=zimmer, art=art,
                 hinweis="" if neu else "Mangel war schon offen")
        erg["neu"] = neu
        _schreiben(d)
    _schritt("QR-Meldung übernommen", aktion, [DATEI, mg.DATEI])
    text = f"{mg.NAMEN.get(art, art)} in {kurz(zimmer)}"
    return f"Mangel angelegt: {text}" if erg.get("neu") else f"{text} war schon offen – Meldung erledigt"


def verwerfen(mid: str, heute: date | None = None) -> str:
    from .kern import _schritt

    heute = heute or date.today()

    def aktion():
        d = _lesen()
        x = _finden(d, mid)
        x.update(status="verworfen", erledigt=heute.isoformat())
        _schreiben(d)
    _schritt("QR-Meldung verworfen", aktion, [DATEI])
    return "Meldung verworfen"


# ---- Windows-Meldung (je PC einmal) ----------------------------------------------------------------------------------

def noch_nicht_gemeldet() -> list[Meldung]:
    """Neue Meldungen, die DIESER PC noch nicht als Windows-Meldung gezeigt hat (merkt sie sich danach)."""
    from .netz_kern import persoenlich, persoenlich_setzen

    gezeigt = set(persoenlich("qr_gemeldet", []) or [])
    offen = neue()
    rest = [m for m in offen if m.id not in gezeigt]
    if rest:
        persoenlich_setzen("qr_gemeldet", sorted(gezeigt & {m.id for m in offen} | {m.id for m in rest}))
    return rest


def kurztext(m: Meldung, kurz=lambda z: z.removeprefix("GS-")) -> str:
    wo = kurz(m.zimmer) if m.zimmer else (m.zimmer_text or "Zimmer ?")
    was = m.text or m.art_text or mg.NAMEN.get(m.art, m.art)
    return f"{wo}: {was[:80]}"


# ---- Etiketten (Druckbogen) ---------------------------------------------------------------------------------------

def etiketten_html(vorlage: str, zimmer: list[tuple[str, str]], titel: str = "Etwas kaputt?",
                   zeile: str = "Hier scannen und melden – anonym") -> str:
    """Druckbogen A4: 3 × 4 Etiketten je Seite (Zimmernummer, QR-Code, Hinweis). ``zimmer`` = [(ID, kurz)]."""
    from html import escape

    from .qr_kern import svg

    if not vorlage:
        raise ValueError("Zuerst den Forms-Link eintragen.")
    g = geheim() if CODE_PLATZHALTER in vorlage else ""
    karten = []
    for zid, kurz in zimmer:
        url = zimmer_link(vorlage, kurz, code_fuer(zid, g) if g else "")
        karten.append(f'<div class="e"><div class="n">{escape(kurz)}</div>{svg(url, modul=1)}'
                      f'<div class="t">{escape(titel)}</div><div class="z">{escape(zeile)}</div></div>')
    return ("<!doctype html><html lang='de'><meta charset='utf-8'><title>QR-Etiketten</title><style>"
            "@page{size:A4;margin:10mm}body{font-family:Segoe UI,Arial,sans-serif;margin:0}"
            ".b{display:grid;grid-template-columns:repeat(3,1fr);gap:6mm}"
            ".e{border:0.3mm dashed #999;border-radius:3mm;padding:4mm;text-align:center;break-inside:avoid;"
            "height:62mm;box-sizing:border-box;display:flex;flex-direction:column;align-items:center;justify-content:center}"
            ".e svg{width:36mm;height:36mm}.n{font-size:16pt;font-weight:700;margin-bottom:1mm}"
            ".t{font-size:11pt;font-weight:600;margin-top:1mm}.z{font-size:8pt;color:#444}"
            f"</style><body><div class='b'>{''.join(karten)}</div></body></html>")


# ---- 1.31: Prüfanzeige – warum kommt eine Meldung nicht an? -----------------------------------------------------

@dataclass
class Punkt:
    stufe: str                   # ok | warn | krit | info
    titel: str
    text: str


def _alter(sek: float) -> str:
    if sek < 90:
        return "gerade eben"
    if sek < 3600:
        return f"vor {int(sek // 60)} Min."
    if sek < 2 * 86400:
        return f"vor {int(sek // 3600)} Std."
    return f"vor {int(sek // 86400)} Tagen"


def diagnose(jetzt: datetime | None = None) -> list[Punkt]:
    """Alles, woran das Einlesen scheitern kann – in der Reihenfolge, in der man es prüft. Liest die Antwortdatei
    (nur lesen, nichts wird übernommen)."""
    jetzt = jetzt or datetime.now()
    erg: list[Punkt] = []
    d = _lesen()
    l_ = str(d.get("link") or "")
    if not l_:
        erg.append(Punkt("krit", "Formular-Link", "Noch kein Link gespeichert – ohne Link gibt es keine Etiketten."))
    elif PLATZHALTER not in l_:
        erg.append(Punkt("warn", "Formular-Link", f"Gespeichert, aber ohne {PLATZHALTER}: alle Etiketten öffnen dasselbe "
                                                  "Formular, das Zimmer muss der Gast selbst eintragen."))
    elif CODE_PLATZHALTER not in l_:
        erg.append(Punkt("warn", "Formular-Link", f"Mit {PLATZHALTER}, aber ohne {CODE_PLATZHALTER} – geänderte "
                                                  "Zimmernummern fallen nicht auf."))
    else:
        erg.append(Punkt("ok", "Formular-Link", f"Gespeichert, mit {PLATZHALTER} und {CODE_PLATZHALTER}."))
    dateien = dateiordner()
    if dateien:
        erg += _diagnose_dateiordner(dateien, d)
    ordner = outlook_ordner()
    if ordner:
        erg += _diagnose_outlook(ordner, d)
    pfad = antwortdatei()
    if not pfad:
        if ordner or dateien:
            weg = "einen OneDrive-Ordner" if dateien else "Outlook"
            erg.append(Punkt("info", "Antwortdatei", f"Nicht nötig – die Meldungen kommen per Power Automate über {weg}."))
            erg.append(_letztes_einlesen())
        else:
            erg.append(Punkt("krit", "Antwortdatei", "Auf DIESEM PC ist weder ein QR-Ordner (OneDrive), ein "
                                                     "Outlook-Ordner noch eine Antwortdatei eingetragen. Eingelesen wird "
                                                     "nur auf PCs, auf denen eins davon eingetragen ist."))
        return erg
    p = Path(pfad)
    teile = {t.lower() for t in p.parts}
    if not p.exists():
        erg.append(Punkt("krit", "Antwortdatei", f"Die Datei gibt es auf diesem PC nicht: {pfad}"))
        return erg
    if "downloads" in teile:
        erg.append(Punkt("krit", "Antwortdatei", "Die Datei liegt im Ordner Downloads – das ist eine einmalige KOPIE der "
                                                 "Antworten, sie bekommt keine neuen. Bitte die Arbeitsmappe aus OneDrive "
                                                 "nehmen (Forms → Antworten → In Excel öffnen → Datei in OneDrive)."))
    elif not any("onedrive" in t or "sharepoint" in t for t in teile):
        erg.append(Punkt("warn", "Antwortdatei", "Die Datei liegt nicht in einem OneDrive-Ordner. Nur die mit dem Formular "
                                                 "verbundene Arbeitsmappe in OneDrive wird bei neuen Antworten ergänzt."))
    else:
        erg.append(Punkt("ok", "Antwortdatei", pfad))
    try:
        st = p.stat()
        erg.append(Punkt("info", "Zuletzt geändert", f"{datetime.fromtimestamp(st.st_mtime):%d.%m.%Y %H:%M} "
                                                     f"({_alter((jetzt - datetime.fromtimestamp(st.st_mtime)).total_seconds())}) "
                                                     "– kommt eine neue Antwort, muss sich diese Zeit ändern (OneDrive "
                                                     "lädt meist binnen 1–5 Minuten nach)."))
    except OSError:
        pass
    inhalt = lesen_xlsx(p)
    if inhalt.fehler:
        erg.append(Punkt("krit", "Inhalt", inhalt.fehler))
    else:
        bekannt = {x.get("id") for x in d.get("meldungen") or []}
        neu = [r for r in inhalt.zeilen if r.id not in bekannt]
        letzte = max((r.zeit for r in inhalt.zeilen), default="")
        try:
            letzte_t = f"{datetime.fromisoformat(letzte):%d.%m.%Y %H:%M}" if letzte else "–"
        except ValueError:
            letzte_t = letzte
        if not inhalt.zeilen:
            erg.append(Punkt("warn", "Inhalt", "Die Datei enthält noch keine Antworten. Ist eine Testantwort abgeschickt, "
                                               "aber hier nicht zu sehen, ist es nicht die mit dem Formular verbundene Datei "
                                               "oder OneDrive hat sie noch nicht geladen."))
        else:
            erg.append(Punkt("ok" if not neu else "warn", "Inhalt",
                             f"{len(inhalt.zeilen)} Antwort(en) in der Datei, neueste vom {letzte_t}; "
                             + (f"{len(neu)} noch nicht eingelesen – „Jetzt einlesen“ klicken." if neu else
                                "alle eingelesen.")))
    erg.append(_letztes_einlesen())
    return erg


def _letztes_einlesen() -> Punkt:
    if _STAND.get("gelesen"):
        t = _STAND["gelesen"]
        return Punkt("krit" if _STAND.get("fehler") else "info", "Letztes Einlesen",
                     f"{t:%d.%m. %H:%M} – " + (_STAND["fehler"] or f"{_STAND.get('neu', 0)} neue Meldung(en)"))
    return Punkt("info", "Letztes Einlesen", f"seit dem Start noch nicht – automatisch alle {TAKT_MINUTEN} Minuten")


def _diagnose_outlook(ordner: str, d: dict) -> list[Punkt]:
    """1.32: Outlook-Ordner lesbar? Wie viele QR-Mails, wie viele davon noch nicht eingelesen?"""
    inhalt = outlook_lesen(ordner)
    if inhalt.fehler:
        return [Punkt("krit", "Outlook-Ordner", inhalt.fehler)]
    erg = [Punkt("ok", "Outlook-Ordner", ordner)]
    if not inhalt.zeilen:
        erg.append(Punkt("warn", "QR-Mails", "Im Ordner liegt noch keine QR-Mail. Ist eine Testantwort abgeschickt: in "
                                             "Power Automate unter „Ausführungsverlauf“ nachsehen, ob der Flow gelaufen "
                                             "ist, und ob die Outlook-Regel die Mail in diesen Ordner verschiebt."))
        return erg
    bekannt = {x.get("id") for x in d.get("meldungen") or []}
    neu = [r for r in inhalt.zeilen if r.id not in bekannt]
    letzte = max(r.zeit for r in inhalt.zeilen)
    try:
        letzte = f"{datetime.fromisoformat(letzte):%d.%m.%Y %H:%M}"
    except ValueError:
        pass
    erg.append(Punkt("ok" if not neu else "warn", "QR-Mails",
                     f"{len(inhalt.zeilen)} QR-Mail(s) im Ordner, neueste vom {letzte}; "
                     + (f"{len(neu)} noch nicht eingelesen – „Jetzt einlesen“ klicken." if neu else "alle eingelesen.")))
    return erg


# ---- 1.32: Quelle Outlook – Power Automate schickt je Forms-Antwort eine Mail mit festem Aufbau ------------------
#
# Betreff:  INNternat-QR | <Zimmer> | <Code>
# Text:     INNTERNAT-QR
#           ID: <Antwort-ID>
#           Zeit: <Übermittlungszeit>
#           Zimmer: <Zimmer>
#           Code: <Code>
#           Art: <Art des Problems>
#           Beschreibung: <Beschreibung – darf mehrzeilig sein>
#           ENDE
# Eine Outlook-Regel verschiebt diese Mails in einen eigenen Ordner; INNternat liest NUR diesen Ordner (nichts wird
# verschoben, gelöscht oder als gelesen markiert). Das ist ein festes Format – keine unscharfe Mail-Erkennung.

MAIL_KENNUNG = "INNTERNAT-QR"
EINSTELLUNG_OUTLOOK = "qr_outlook_ordner"          # je PC (Outlook-Profil), z. B. „Internatsdienst/Posteingang/QR-Meldungen“
MAIL_FELDER = {"id": "id", "zeit": "zeit", "zimmer": "zimmer", "code": "code", "art": "art", "beschreibung": "text"}


def mail_parsen(betreff: str, text: str, eintrag: str = "", empfangen: datetime | None = None) -> Roh | None:
    """Eine Power-Automate-Mail → Roh (None, wenn es keine ist). Robust gegen Leerzeilen, Groß/klein, HTML-Reste."""
    t = re.sub(r"<[^>]+>", "\n", str(text or "")).replace("\r", "")
    t = re.sub(r"&nbsp;", " ", t)
    if MAIL_KENNUNG not in t.upper() and MAIL_KENNUNG not in str(betreff or "").upper():
        return None
    schluessel = r"(?:ID|Zeit|Zimmer|Code|Art|Beschreibung)\s*:"
    if len(re.findall(rf"(?im)^\s*{schluessel}", t)) < 2:      # 1.45: alles in einer Zeile → an den Wörtern trennen
        t = re.sub(rf"\s+(?={schluessel}|ENDE\s*$)", "\n", t, flags=re.I)
    werte: dict[str, str] = {}
    feld = None
    for zeile in t.split("\n"):
        z = zeile.strip()
        if z.upper() == "ENDE":
            break
        m = re.match(r"^(ID|Zeit|Zimmer|Code|Art|Beschreibung)\s*:\s*(.*)$", z, re.I)
        if m:
            feld = MAIL_FELDER[m.group(1).lower()]
            werte[feld] = m.group(2).strip()
        elif feld == "text" and z:                      # Beschreibung über mehrere Zeilen
            werte["text"] = (werte.get("text", "") + "\n" + z).strip()
    if "zimmer" not in werte and "text" not in werte:
        return None
    rid = werte.get("id") or eintrag
    if not rid:
        return None
    zeit = _pa_zeit(werte.get("zeit") or "") or (empfangen or datetime.now()).isoformat(timespec="minutes")
    return Roh(f"pa|{rid}", zeit, werte.get("zimmer", ""), _auswahl(werte.get("art", "")), werte.get("text", ""),
               werte.get("code", ""))


def _auswahl(t: str) -> str:
    """1.44: Auswahlfragen kommen aus Forms als Liste – „["Heizung"]“ bzw. „["Heizung","Fenster"]“ → „Heizung, Fenster“."""
    t = (t or "").strip()
    if t.startswith("[") and t.endswith("]"):
        teile = [x.strip().strip('"').strip("'") for x in t[1:-1].split(",")]
        return ", ".join(x for x in teile if x)
    return t


def _pa_zeit(t: str) -> str:
    """Übermittlungszeit aus Power Automate: ISO in UTC („2026-11-19T07:01:23.1234567Z“) → Ortszeit; sonst die
    üblichen Formate (auch „11/19/2026 8:01:23 AM“). "" wenn nicht lesbar."""
    t = (t or "").strip()
    m = re.match(r"^(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(?::\d{2})?)(?:\.\d+)?(Z|[+-]\d{2}:?\d{2})?$", t)
    if m:
        try:
            x = datetime.fromisoformat(m.group(1) + ("+00:00" if m.group(2) == "Z" else (m.group(2) or "")))
        except ValueError:
            return ""
        if x.tzinfo is not None:
            x = x.astimezone().replace(tzinfo=None)
        return x.isoformat(timespec="minutes")
    for f in ("%m/%d/%Y %I:%M:%S %p", "%m/%d/%Y %I:%M %p"):   # 1.44: so schreibt Forms die Übermittlungszeit – in UTC
        try:
            x = datetime.strptime(t, f).replace(tzinfo=timezone.utc).astimezone().replace(tzinfo=None)
            return x.isoformat(timespec="minutes")
        except ValueError:
            pass
    z = _zeit(t)
    return z if re.match(r"^\d{4}-\d{2}-\d{2}T", z) else ""


def outlook_ordner() -> str:
    from .netz_kern import persoenlich

    return str(persoenlich(EINSTELLUNG_OUTLOOK, "", je_standort=True) or "")


def outlook_ordner_setzen(pfad: str) -> str:
    from .netz_kern import persoenlich_setzen

    pfad = (pfad or "").strip().strip('"')
    persoenlich_setzen(EINSTELLUNG_OUTLOOK, pfad, je_standort=True)
    return f"Outlook-Ordner für QR-Meldungen: {pfad}" if pfad else "Outlook-Ordner für QR-Meldungen entfernt"


def outlook_lesen(pfad: str, anzahl: int = 300) -> Ergebnis:
    """Die neuesten Mails des Ordners lesen (nur lesen) und die Power-Automate-Mails herausziehen."""
    from . import outlook_kern as ok

    try:
        pythoncom, ol = ok._outlook("Outlook ist nicht geöffnet – QR-Meldungen kommen, sobald Outlook läuft.")
    except ValueError as exc:
        return Ergebnis(fehler=str(exc))
    erg = Ergebnis()
    try:
        ns = ol.GetNamespace("MAPI")
        try:
            f = ok._ordner_finden(ns, pfad)
        except ValueError as exc:
            return Ergebnis(fehler=f"Outlook-Ordner: {exc}")
        items = f.Items
        items.Sort("[ReceivedTime]", True)
        m, n = items.GetFirst(), 0
        while m is not None and n < anzahl:
            n += 1
            try:
                if int(getattr(m, "Class", 0) or 0) == 43:
                    rt = m.ReceivedTime
                    r = mail_parsen(str(m.Subject or ""), str(m.Body or ""), str(getattr(m, "EntryID", "") or ""),
                                    datetime(rt.year, rt.month, rt.day, rt.hour, rt.minute))
                    if r is not None:
                        erg.zeilen.append(r)
            except Exception:                           # noqa: BLE001 – eine kaputte Mail stoppt das Einlesen nicht
                pass
            m = items.GetNext()
        return erg
    finally:
        pythoncom.CoUninitialize()


# ---- 1.44: Quelle OneDrive-Ordner – Power Automate legt je Antwort eine Textdatei ab -------------------------------
#
# Für Firmenkonten, in denen weder „Office 365 Outlook“ noch der Mail-Baustein freigegeben ist: Power Automate
# („OneDrive for Business – Datei erstellen“) schreibt je Forms-Antwort eine Datei „qr-<Antwort-ID>.txt“ mit genau
# dem Aufbau der QR-Mail (INNTERNAT-QR, ID:, Zeit:, Zimmer:, Code:, Art:, Beschreibung:, ENDE) in einen Ordner, den
# OneDrive auf den PC synchronisiert. INNternat liest die Dateien nur (nichts wird verschoben oder gelöscht).

EINSTELLUNG_ORDNER = "qr_datei_ordner"              # je PC, z. B. „C:\\Users\\…\\OneDrive - …\\INNternat-QR“
ORDNER_MAX = 500                                    # nur die neuesten Dateien – ältere sind längst eingelesen
ORDNER_ENDUNGEN = (".txt", ".text")


def dateiordner() -> str:
    from .netz_kern import persoenlich

    return str(persoenlich(EINSTELLUNG_ORDNER, "", je_standort=True) or "")


def dateiordner_setzen(pfad: str) -> str:
    from .netz_kern import persoenlich_setzen

    pfad = (pfad or "").strip().strip('"')
    if pfad and not Path(pfad).is_dir():
        raise ValueError(f"Den Ordner gibt es auf diesem PC nicht: {pfad}")
    persoenlich_setzen(EINSTELLUNG_ORDNER, pfad, je_standort=True)
    return (f"QR-Ordner gespeichert – neue Dateien werden alle {TAKT_MINUTEN} Minuten gelesen" if pfad
            else "QR-Ordner entfernt")


def _text_datei(p: Path) -> str:
    roh = p.read_bytes()
    for kod in ("utf-8-sig", "utf-16", "cp1252"):
        try:
            t = roh.decode(kod)
        except UnicodeDecodeError:
            continue
        if kod != "utf-16" or MAIL_KENNUNG in t.upper():
            return t
    return roh.decode("utf-8", errors="replace")


def ordner_lesen(pfad: str, anzahl: int = ORDNER_MAX) -> Ergebnis:
    """Die neuesten Textdateien des Ordners lesen (nur lesen) und die QR-Meldungen herausziehen."""
    d = Path(pfad)
    if not d.is_dir():
        return Ergebnis(fehler=f"QR-Ordner nicht gefunden: {pfad} – ist OneDrive auf diesem PC angemeldet?")
    try:
        dateien = [(x.stat().st_mtime, x) for x in d.iterdir()
                   if x.is_file() and x.suffix.lower() in ORDNER_ENDUNGEN and not x.name.startswith((".", "~"))]
    except OSError as exc:
        return Ergebnis(fehler=f"QR-Ordner nicht lesbar: {exc}")
    dateien.sort(key=lambda t: t[0], reverse=True)
    erg = Ergebnis()
    for mt, x in dateien[:anzahl]:
        try:
            # 1.45: die Kennzeile INNTERNAT-QR ist in der Datei nicht nötig – der Ordner gehört nur INNternat
            r = mail_parsen(MAIL_KENNUNG, _text_datei(x), x.stem, datetime.fromtimestamp(mt).replace(second=0, microsecond=0))
        except OSError:                                 # z. B. gerade von OneDrive gesperrt – beim nächsten Mal
            continue
        if r is not None:
            erg.zeilen.append(r)
        else:
            erg.unbekannt.append(x.name)
    erg.gesamt = len(dateien)
    return erg


def _diagnose_dateiordner(ordner: str, d: dict) -> list[Punkt]:
    inhalt = ordner_lesen(ordner)
    if inhalt.fehler:
        return [Punkt("krit", "QR-Ordner", inhalt.fehler)]
    p = Path(ordner)
    teile = {t.lower() for t in p.parts}
    if not any("onedrive" in t or "sharepoint" in t for t in teile):
        erg = [Punkt("warn", "QR-Ordner", f"{ordner} – liegt nicht in einem OneDrive-Ordner. Power Automate schreibt in "
                                         "OneDrive; nur ein synchronisierter Ordner bekommt die neuen Dateien.")]
    else:
        erg = [Punkt("ok", "QR-Ordner", ordner)]
    if inhalt.unbekannt:
        erg.append(Punkt("krit" if not inhalt.zeilen else "warn", "Unlesbare Dateien",
                         f"{len(inhalt.unbekannt)} Textdatei(en) ohne Zeilen „ID:“ und „Zimmer:“ bzw. „Beschreibung:“ "
                         f"(z. B. {inhalt.unbekannt[0]}). In Power Automate beim Schritt „Datei erstellen“ den "
                         "Dateiinhalt prüfen: jede Angabe in eine eigene Zeile, links genau „ID:“, „Zimmer:“ … "
                         "„ENDE“."))
    if not inhalt.zeilen and not inhalt.unbekannt:
        erg.append(Punkt("warn", "QR-Dateien", "Im Ordner liegt noch keine QR-Datei. Ist eine Testantwort abgeschickt: "
                                               "in Power Automate unter „Ausführungsverlauf“ nachsehen, ob der Flow "
                                               "gelaufen ist, und ob OneDrive auf diesem PC synchronisiert (Wolke in "
                                               "der Taskleiste)."))
        return erg
    if not inhalt.zeilen:
        return erg
    bekannt = {x.get("id") for x in d.get("meldungen") or []}
    neu = [r for r in inhalt.zeilen if r.id not in bekannt]
    letzte = max(r.zeit for r in inhalt.zeilen)
    try:
        letzte = f"{datetime.fromisoformat(letzte):%d.%m.%Y %H:%M}"
    except ValueError:
        pass
    erg.append(Punkt("ok" if not neu else "warn", "QR-Dateien",
                     f"{len(inhalt.zeilen)} QR-Datei(en) im Ordner, neueste vom {letzte}; "
                     + (f"{len(neu)} noch nicht eingelesen – „Jetzt einlesen“ klicken." if neu else "alle eingelesen.")))
    return erg
