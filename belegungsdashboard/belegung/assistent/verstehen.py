"""Deutsches Sprachverständnis für Belegungsfragen (regelbasiert, ohne Modell).

Ergebnis ist eine ``Anfrage`` mit Absicht, Standorten und Zeiträumen. Fehlende Angaben
werden aus der vorherigen Anfrage übernommen, damit Folgefragen wie "und Goslar?" oder
"und im November?" funktionieren.
"""

from __future__ import annotations

import calendar
import re
from dataclasses import dataclass, field, replace
from datetime import date, timedelta

from ..konfig import GESAMT, STANDORTE

MONATE = {
    "januar": 1, "jan": 1, "jänner": 1, "februar": 2, "feb": 2, "märz": 3, "maerz": 3, "marz": 3, "mär": 3,
    "april": 4, "apr": 4, "mai": 5, "juni": 6, "jun": 6, "juli": 7, "jul": 7, "august": 8, "aug": 8,
    "september": 9, "sept": 9, "sep": 9, "oktober": 10, "okt": 10, "november": 11, "nov": 11,
    "dezember": 12, "dez": 12,
}
MONATSNAMEN = ["Januar", "Februar", "März", "April", "Mai", "Juni", "Juli", "August", "September",
               "Oktober", "November", "Dezember"]
_MONAT_RE = "|".join(sorted(map(re.escape, MONATE), key=len, reverse=True))

ZAHLWORTE = {"einen": 1, "einem": 1, "ein": 1, "eine": 1, "zwei": 2, "drei": 3, "vier": 4, "fünf": 5,
             "sechs": 6, "sieben": 7, "acht": 8, "neun": 9, "zehn": 10, "elf": 11, "zwölf": 12}
_ZAHL_RE = r"(\d+|" + "|".join(ZAHLWORTE) + r")"

ABSICHTEN = [
    "hilfe", "modell", "anreisen", "mieter", "gaeste", "haeuser", "frei", "kapazitaet", "personentage",
    "trend", "vergleich", "extrem", "prognose", "auslastung", "bestand", "belegung", "ueberblick",
]

_ABSICHT_MUSTER: dict[str, str] = {
    "hilfe": r"\bhilfe\b|was kannst du|was weißt du|beispiel|wie funktionierst|welche fragen",
    "modell": r"\bmodell|genauigkeit|zuverlässig|treffsicher|treffer|backtest|wie gut (ist|war|sind) die prognose|wie genau|abweichung der prognose",
    "anreisen": r"anreise|ankunft|ankommen|kommen an\b|neuaufnahme|aufnahmen|zugänge|neuzugänge|neue teilnehmer",
    "mieter": r"\bmieter|\bmiete|mietvertr|vermietet",
    "gaeste": r"\bgäste|\bgast\b|\bgaeste",
    "haeuser": r"\bhaus\b|häuser|haeuser|gebäude|gebaeude|internat [a-z]\b|je haus|pro haus",
    "frei": r"\bfrei(e|en)?\b|verfügbar|noch platz|platz für|reserve|unbelegt|aufnehmen können|können wir .*aufnehmen",
    "kapazitaet": r"kapazit|wie viele plätze|wie viele betten|plätze gibt|anzahl plätze|platzzahl",
    "personentage": r"personentag|übernachtung|uebernachtung|belegungstag|nächte\b|naechte",
    "trend": r"\btrend|entwick|gestiegen|gesunken|veränder|zunahme|abnahme|wachstum|rückgang|steigt|sinkt|zugenommen|abgenommen",
    "vergleich": r"vergleich|unterschied|gegenüber|\bvs\.?\b|versus|verglichen|im gegensatz",
    "extrem": r"höchst|hoechst|größt|grösst|maximal|maximum|spitze|am meisten|am vollsten|niedrigst|minimum|minimal|tiefst|am wenigsten|am leersten|rekord",
    "prognose": r"prognos|vorhersag|voraussicht|erwart|zukunft|zukünftig|\bwird\b|\bwerden\b|rechnen wir|planung|absehbar",
    "auslastung": r"auslastung|ausgelastet|prozent|%|quote|wie voll",
    "bestand": r"gesichert|gebucht|fest eingeplant|\bbestand\b",
    "belegung": r"belegung|belegt|wie viele|wieviele|anzahl|personen|teilnehmer|\bleute\b|bewohner|\btn\b|anwesend|untergebracht|\bda\b",
    "ueberblick": r"überblick|übersicht|zusammenfassung|\blage\b|status|wie sieht es aus|wie läuft|wie steht|was gibt es neues|kurz(er)? bericht",
}
_ABSICHT_RE = {k: re.compile(v, re.I) for k, v in _ABSICHT_MUSTER.items()}

_STANDORT_MUSTER = [
    (re.compile(r"bad\s*pyrmont|pyrmont|\bbp\b", re.I), "BFW BP"),
    (re.compile(r"goslar|\bgs\b", re.I), "BFW GS"),
    (re.compile(r"weser[\s-]*ems|\bwe\b", re.I), "BFW WE"),
]
_ALLE_RE = re.compile(r"alle[nr]?\s+standort|jede[nmr]?\s+standort|je\s+standort|pro\s+standort|standorte\b|einzeln|aufgeteilt|aufgeschlüsselt", re.I)
_GESAMT_RE = re.compile(r"\bgesamt|insgesamt|zusammen|summe|alle\b", re.I)
_ABSEITS_RE = re.compile(
    r"gedicht|witz|geschichte|märchen|lied\b|songtext|rezept|übersetz|programmier|\bcode\b|python|"
    r"schreib (mir )?(eine?n?|was)|erzähl|wetter|nachrichten|politik|fußball|ignorier|vergiss|rolle|"
    r"system.?prompt|du bist (jetzt|nun|ab)|tu so|stell dir vor|\d+\s*[-+*/x]\s*\d+", re.I)
_ZUKUNFT_RE = re.compile(r"\bwird\b|\bwerden\b|erwart|prognos|voraussicht|nächst|kommend|künftig|zukunft|planung|geplant", re.I)
_VERGANGEN_RE = re.compile(r"\bwar\b|\bwaren\b|hatten|\bgab\b|vergangen|letzt|vorig|damals|gewesen", re.I)


@dataclass
class Zeitraum:
    von: date
    bis: date
    art: str            # tag | woche | monat | quartal | jahr | bereich
    text: str

    @property
    def ist_tag(self) -> bool:
        return self.von == self.bis


@dataclass
class Anfrage:
    frage: str
    absicht: str | None = None
    standorte: list[str] = field(default_factory=list)   # leer = nicht genannt
    alle_standorte: bool = False
    zeitraeume: list[Zeitraum] = field(default_factory=list)
    aggregat: str | None = None       # max | min | mittel
    brutto: bool | None = None
    folgefrage: bool = False

    @property
    def zeit(self) -> Zeitraum | None:
        return self.zeitraeume[0] if self.zeitraeume else None

    @property
    def erkannt(self) -> bool:
        return self.absicht is not None


def _zahl(text: str) -> int:
    return int(text) if text.isdigit() else ZAHLWORTE.get(text.lower(), 1)


def _monatsende(jahr: int, monat: int) -> date:
    return date(jahr, monat, calendar.monthrange(jahr, monat)[1])


def _monat_verschieben(d: date, n: int) -> date:
    m = d.month - 1 + n
    return date(d.year + m // 12, m % 12 + 1, 1)


def monat_zeitraum(jahr: int, monat: int) -> Zeitraum:
    return Zeitraum(date(jahr, monat, 1), _monatsende(jahr, monat), "monat", f"{MONATSNAMEN[monat - 1]} {jahr}")


def _jahr_zweistellig(j: str) -> int:
    return int(j) + 2000 if len(j) == 2 else int(j)


class Versteher:
    def __init__(self, heute: date):
        self.heute = heute

    # ---- Zeit ------------------------------------------------------------------------

    def _tag(self, d: date, text: str | None = None) -> Zeitraum:
        return Zeitraum(d, d, "tag", text or d.strftime("%d.%m.%Y"))

    def _monat_ohne_jahr(self, monat: int, zukunft: bool | None) -> int:
        """Monat ohne Jahresangabe: bei klarer Zeitform die nächste bzw. letzte Gelegenheit,
        sonst der zeitlich nächstgelegene Monat (bei Gleichstand der künftige)."""
        h = self.heute
        kommend = h.year if monat >= h.month else h.year + 1
        vergangen = h.year if monat <= h.month else h.year - 1
        if zukunft is True:
            return kommend
        if zukunft is False:
            return vergangen
        abstand_vor = (kommend - h.year) * 12 + monat - h.month
        abstand_zurueck = (h.year - vergangen) * 12 + h.month - monat
        return vergangen if abstand_zurueck < abstand_vor else kommend

    def zeitraeume(self, t: str, zukunft: bool | None) -> list[Zeitraum]:
        h = self.heute
        treffer: list[tuple[int, Zeitraum]] = []
        belegt: list[tuple[int, int]] = []

        def frei(m: re.Match) -> bool:
            return not any(a < m.end() and m.start() < b for a, b in belegt)

        def nimm(m: re.Match, z: Zeitraum):
            belegt.append((m.start(), m.end()))
            treffer.append((m.start(), z))

        datum = r"(\d{1,2})\.\s?(\d{1,2})\.(\d{2,4})?"
        datum_lang = rf"(\d{{1,2}})\.?\s+({_MONAT_RE})\.?(?:\s+(\d{{4}}))?"

        def datum_aus(g: tuple) -> date | None:
            tag, monat, jahr = g
            try:
                if jahr:
                    return date(_jahr_zweistellig(jahr), int(monat), int(tag))
                j = self._monat_ohne_jahr(int(monat), zukunft)
                return date(j, int(monat), int(tag))
            except ValueError:
                return None

        def datum_lang_aus(g: tuple) -> date | None:
            tag, mname, jahr = g
            monat = MONATE[mname.lower()]
            j = int(jahr) if jahr else self._monat_ohne_jahr(monat, zukunft)
            try:
                return date(j, monat, int(tag))
            except ValueError:
                return None

        # Bereiche "vom X bis Y" / "zwischen X und Y" / "X - Y"
        for muster, umwandeln in ((datum, datum_aus), (datum_lang, datum_lang_aus)):
            bereich = re.compile(rf"(?:vom|von|zwischen|ab)?\s*{muster}\s*(?:bis|und|-|–)\s*(?:zum\s+)?{muster}", re.I)
            for m in bereich.finditer(t):
                g = m.groups()
                n = len(g) // 2
                a, b = umwandeln(g[:n]), umwandeln(g[n:])
                if a and b and frei(m):
                    if a > b:
                        a, b = b, a
                    nimm(m, Zeitraum(a, b, "bereich", f"{a:%d.%m.%Y} – {b:%d.%m.%Y}"))

        for m in re.finditer(datum, t):
            d = datum_aus(m.groups())
            if d and frei(m):
                nimm(m, self._tag(d))
        for m in re.finditer(datum_lang, t, re.I):
            d = datum_lang_aus(m.groups())
            if d and frei(m):
                nimm(m, self._tag(d))

        # Quartale
        for m in re.finditer(r"\bq([1-4])\s*(\d{4})?|([1-4])\.\s*quartal\s*(\d{4})?|(erste|zweite|dritte|vierte)[sn]?\s+quartal\s*(\d{4})?", t, re.I):
            if not frei(m):
                continue
            q = int(m.group(1) or m.group(3) or ["erste", "zweite", "dritte", "vierte"].index(m.group(5).lower()) + 1)
            jahr_text = m.group(2) or m.group(4) or m.group(6)
            j = int(jahr_text) if jahr_text else h.year
            nimm(m, Zeitraum(date(j, 3 * q - 2, 1), _monatsende(j, 3 * q), "quartal", f"Q{q} {j}"))

        # Monatsnamen mit optionalem Jahr
        for m in re.finditer(rf"\b({_MONAT_RE})\b\.?(?:\s+(\d{{4}}|\d{{2}}\b))?", t, re.I):
            if not frei(m):
                continue
            monat = MONATE[m.group(1).lower()]
            j = _jahr_zweistellig(m.group(2)) if m.group(2) else self._monat_ohne_jahr(monat, zukunft)
            seit = re.search(rf"seit\s+(?:anfang\s+)?{re.escape(m.group(1))}", t, re.I)
            if seit:
                nimm(m, Zeitraum(date(j, monat, 1), h, "bereich", f"seit {MONATSNAMEN[monat - 1]} {j}"))
            else:
                nimm(m, monat_zeitraum(j, monat))

        relativ: list[tuple[str, callable]] = [
            (r"übermorgen|uebermorgen", lambda m: self._tag(h + timedelta(days=2), "übermorgen")),
            (r"vorgestern", lambda m: self._tag(h - timedelta(days=2), "vorgestern")),
            (r"\bheute\b|\baktuell|\bderzeit|\bmomentan|\bjetzt\b|\bgerade\b|im moment", lambda m: self._tag(h, "heute")),
            (r"\bgestern\b", lambda m: self._tag(h - timedelta(days=1), "gestern")),
            (r"\bmorgen\b", lambda m: self._tag(h + timedelta(days=1), "morgen")),
            (rf"(?:in|nach)\s+{_ZAHL_RE}\s+(tag|tagen|woche|wochen|monat|monaten|jahr|jahren)\b", self._in_n),
            (rf"(?:letzte[nr]?|vergangene[nr]?|vorige[nr]?|seit)\s+{_ZAHL_RE}\s+(tag|tage|tagen|woche|wochen|monat|monate|monaten|jahr|jahre|jahren)\b", self._letzte_n),
            (rf"(?:nächste[nr]?|naechste[nr]?|kommende[nr]?|folgende[nr]?)\s+{_ZAHL_RE}\s+(tag|tage|tagen|woche|wochen|monat|monate|monaten|jahr|jahre|jahren)\b", self._naechste_n),
            (r"(diese|aktuelle|laufende)[rn]?\s+woche", lambda m: self._woche(0)),
            (r"(letzte|vergangene|vorige)[rn]?\s+woche|vorwoche", lambda m: self._woche(-1)),
            (r"(nächste|naechste|kommende)[rn]?\s+woche", lambda m: self._woche(1)),
            (r"(diese[nm]?|aktuelle[nm]?|laufende[nm]?)\s+monat", lambda m: monat_zeitraum(h.year, h.month)),
            (r"(letzte[nm]?|vergangene[nm]?|vorige[nm]?)\s+monat|vormonat", lambda m: self._monat_rel(-1)),
            (r"(nächste[nm]?|naechste[nm]?|kommende[nm]?)\s+monat|folgemonat", lambda m: self._monat_rel(1)),
            (r"(dieses|aktuelle[ns]?|laufende[ns]?)\s+jahr|\bheuer\b", lambda m: self._jahr(h.year)),
            (r"(letzte[ns]?|vergangene[ns]?|vorige[ns]?)\s+jahr|vorjahr", lambda m: self._jahr(h.year - 1)),
            (r"(nächste[ns]?|naechste[ns]?|kommende[ns]?)\s+jahr", lambda m: self._jahr(h.year + 1)),
            (r"jahresende|ende des jahres|bis silvester", lambda m: Zeitraum(h, date(h.year, 12, 31), "bereich", "bis Jahresende")),
        ]
        for muster, bauen in relativ:
            for m in re.finditer(muster, t, re.I):
                if frei(m):
                    nimm(m, bauen(m))

        # Jahreszahl allein
        for m in re.finditer(r"\b(20\d{2})\b", t):
            if frei(m):
                nimm(m, self._jahr(int(m.group(1))))

        return [z for _, z in sorted(treffer, key=lambda x: x[0])]

    def _einheit(self, wort: str) -> str:
        return {"t": "tag", "w": "woche", "m": "monat", "j": "jahr"}[wort[0].lower()]

    def _in_n(self, m: re.Match) -> Zeitraum:
        n, einheit = _zahl(m.group(1)), self._einheit(m.group(2))
        h = self.heute
        if einheit == "tag":
            return self._tag(h + timedelta(days=n), f"in {n} Tagen")
        if einheit == "woche":
            return self._tag(h + timedelta(weeks=n), f"in {n} Wochen")
        ziel = _monat_verschieben(h, n * (12 if einheit == "jahr" else 1))
        return monat_zeitraum(ziel.year, ziel.month)

    def _letzte_n(self, m: re.Match) -> Zeitraum:
        n, einheit = _zahl(m.group(1)), self._einheit(m.group(2))
        tage = {"tag": 1, "woche": 7}.get(einheit)
        h = self.heute
        von = h - timedelta(days=n * tage - 1) if tage else (
            date(h.year - n, h.month, 1) if einheit == "jahr" else _monat_verschieben(h, -n))
        label = {"tag": "Tage", "woche": "Wochen", "monat": "Monate", "jahr": "Jahre"}[einheit]
        return Zeitraum(von, h, "bereich", f"letzte {n} {label}")

    def _naechste_n(self, m: re.Match) -> Zeitraum:
        n, einheit = _zahl(m.group(1)), self._einheit(m.group(2))
        h = self.heute
        tage = {"tag": 1, "woche": 7}.get(einheit)
        bis = h + timedelta(days=n * tage) if tage else (
            _monat_verschieben(h, n * (12 if einheit == "jahr" else 1)) - timedelta(days=1))
        label = {"tag": "Tage", "woche": "Wochen", "monat": "Monate", "jahr": "Jahre"}[einheit]
        return Zeitraum(h + timedelta(days=1), bis, "bereich", f"nächste {n} {label}")

    def _woche(self, versatz: int) -> Zeitraum:
        montag = self.heute - timedelta(days=self.heute.weekday()) + timedelta(weeks=versatz)
        text = {0: "diese Woche", -1: "letzte Woche", 1: "nächste Woche"}[versatz]
        return Zeitraum(montag, montag + timedelta(days=6), "woche", text)

    def _monat_rel(self, versatz: int) -> Zeitraum:
        d = _monat_verschieben(self.heute, versatz)
        return monat_zeitraum(d.year, d.month)

    def _jahr(self, j: int) -> Zeitraum:
        return Zeitraum(date(j, 1, 1), date(j, 12, 31), "jahr", str(j))

    # ---- Gesamt --------------------------------------------------------------------

    def verstehe(self, frage: str, vorher: Anfrage | None = None) -> Anfrage:
        t = " " + frage.strip().lower().replace("’", "'") + " "
        zukunft: bool | None = None
        if _ZUKUNFT_RE.search(t) and not _VERGANGEN_RE.search(t):
            zukunft = True
        elif _VERGANGEN_RE.search(t) and not _ZUKUNFT_RE.search(t):
            zukunft = False

        a = Anfrage(frage=frage)
        for muster, standort in _STANDORT_MUSTER:
            if muster.search(t):
                a.standorte.append(standort)
        if _ALLE_RE.search(t) or ("vergleich" in t and not a.standorte):
            a.alle_standorte = True
        elif not a.standorte and _GESAMT_RE.search(t):
            a.standorte = [GESAMT]

        a.zeitraeume = self.zeitraeume(t, zukunft)
        if re.search(r"brutto", t):
            a.brutto = True
        elif re.search(r"netto", t):
            a.brutto = False
        if re.search(r"höchst|hoechst|größt|grösst|maxim|spitze|am meisten|am vollsten|rekord", t):
            a.aggregat = "max"
        elif re.search(r"niedrigst|minim|tiefst|am wenigsten|am leersten", t):
            a.aggregat = "min"
        elif re.search(r"durchschnitt|schnitt|\bø|mittel", t):
            a.aggregat = "mittel"

        gefunden = {k for k, r in _ABSICHT_RE.items() if r.search(t)}
        # "wird"/"werden" allein ist nur ein Prognose-Signal, wenn es um die Zukunft geht
        if "prognose" in gefunden and not re.search(r"prognos|vorhersag|voraussicht|erwart|zukunft|zukünftig|planung|rechnen wir|absehbar", t):
            if not any(z.bis > self.heute for z in a.zeitraeume):
                gefunden.discard("prognose")
        if "vergleich" not in gefunden and (len(a.standorte) >= 2 or len(a.zeitraeume) >= 2) and (
                gefunden & {"belegung", "auslastung", "frei", "personentage"} or not gefunden):
            gefunden.add("vergleich")
        if "extrem" in gefunden and "trend" in gefunden:
            gefunden.discard("extrem")
        a.absicht = next((k for k in ABSICHTEN if k in gefunden), None)
        # Zukünftiger Zeitpunkt + Belegung/Auslastung/Frei -> bleibt die Absicht, die
        # Antwort nutzt automatisch die Prognose. Nur Kapazität/Häuser/Listen bleiben unberührt.

        # Folgefragen: fehlende Teile aus der vorherigen Anfrage übernehmen
        if _ABSEITS_RE.search(t):
            a.absicht = "abseits"
            return a
        kurz = len(t.split()) <= 4
        folge = bool(re.match(r"\s*(und|u\.|was ist mit|wie ist es mit|wie sieht('?s| es) (mit|in|im|bei)|und bei|und in|und im|dort|da)\b", t))
        konkret = bool(a.standorte or a.zeitraeume or a.alle_standorte or a.brutto is not None)
        if vorher and vorher.absicht and (folge or (kurz and a.absicht is None and konkret)):
            a.folgefrage = True
            if a.absicht is None or (folge and a.absicht in ("belegung",) and vorher.absicht not in ("belegung", "ueberblick")):
                a.absicht = vorher.absicht
            if not a.standorte and not a.alle_standorte:
                a.standorte, a.alle_standorte = list(vorher.standorte), vorher.alle_standorte
            if not a.zeitraeume:
                a.zeitraeume = list(vorher.zeitraeume)
            if a.brutto is None:
                a.brutto = vorher.brutto
            if a.aggregat is None:
                a.aggregat = vorher.aggregat
        elif a.absicht is None and (a.standorte or a.zeitraeume) and kurz:
            a.absicht = "belegung"
        return a


def standorte_fuer(anfrage: Anfrage, standard: list[str] | None = None) -> list[str]:
    if anfrage.alle_standorte:
        return STANDORTE + [GESAMT]
    if anfrage.standorte:
        return anfrage.standorte
    return standard or [GESAMT]


def mit_zeit(anfrage: Anfrage, zeit: Zeitraum) -> Anfrage:
    return replace(anfrage, zeitraeume=[zeit])
