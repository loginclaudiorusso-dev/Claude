"""Renovierung (Steuerung → Renovierung): Welche Etagen bzw. Zimmer – wann – was kostet es – wohin mit den Bewohnern?

Ein Flur ist die ganze Etage (Haus 2 und Haus 6). Nur Planung: Hier wird nichts gesperrt, niemand umgezogen und keine
Buchung verschoben. Gespeichert werden nur Annahmen und – nach Bestätigung – Vormerkungen
(``importe/modern_renovierung.json``, nur im Datenordner, nie im Programm).

0.44 – Grundsätze:

* **Bedarf getrennt nach Bau und Möbel, in Klassen A (jetzt) / B (1–3 Jahre) / C (später)** – aus Mängelarten
  (Boden, Wand, Schimmel, Geruch → Bau; Möbel, Matratze → Möbel; „Renovierung nötig“ → beides), Jahren seit der
  Renovierung und der Zustandsnote der Etage. In den letzten 5 Jahren renoviert = kein Bau (harte Regel), Möbel geht.
  Gewichte 100/10/1: erst alle A, dann B, dann C.
* **Baubudget = feste Grenze, die verfällt** → es soll möglichst voll in gedeckten Bedarf gehen; ein Rest ist ein
  Warnhinweis. **Möbel = Antrag**: INNternat rechnet den Möbelbedarf aus (für die Bau-Maßnahmen + „nur Möbel“ für
  Klasse-A-Zimmer); eine realistische Obergrenze ist optional.
* **Auswahl**: jede Etagenkombination im Baubudget, aufgefüllt mit Einzelzimmern nach Bedarf je Euro – die beste
  Gesamtlösung gewinnt. Etagen ohne machbaren Monat und Reserve-Etagen (Kernbestand) fallen vorher heraus.
* **Kosten mit Herkunft** (Angebot / Eingabe / Schätzung / Platzhalter), Puffer je Budget, Spanne statt Scheingenauigkeit.
  Einzelzimmer aus Einheitspreisen des Angebots × Zimmerfläche, sonst anteilig + Aufschlag (Schätzung).
* **Termine**: Etagen in den besten Monat (Ausweich → Warnschwelle → Umzüge); ohne Buchungen „nicht prüfbar“.
  Einzelzimmer gebündelt in Kampagnen je Haus, frühestens nach der Möbel-Lieferzeit.

Rein, ohne NiceGUI.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from datetime import date, timedelta

from belegung import speicher
from belegung import zimmerplan as zp

DATEI = f"{speicher.IMPORT_ORDNER}/modern_renovierung.json"
MONATE = ["Jan", "Feb", "Mär", "Apr", "Mai", "Jun", "Jul", "Aug", "Sep", "Okt", "Nov", "Dez"]
UST = 0.19

_HAUS_STANDARD = {"bau_etage": 0, "bau_zimmer": 0, "moebel_zimmer": 0, "aufbau_zimmer": 500, "dauer_tage": 30,
                  "zimmer_boden_m2": 0, "zimmer_wand_m2": 0, "zimmer_tueren": 1,
                  "einheit_boden": 0, "einheit_wand": 0, "einheit_tuer": 0}
# Keine Angebotswerte im Programm: Die echten Preise kommen über „Angebot einlesen“ bzw. die Eingabe (Datenordner).
STANDARD = {
    "haeuser": ["2", "6"],
    "kosten": {"2": {**_HAUS_STANDARD, "bau_etage": 100000}, "6": {**_HAUS_STANDARD, "bau_etage": 30000}},
    "einzel_aufschlag_pct": 25,   # Einzelzimmer ohne Einheitspreise: anteilig aus der Etage + Aufschlag (Schätzung)
    "moebel_tage": 3,             # Möbeltausch: so viele Tage muss das Zimmer leer sein
    "zimmer_tage": 14,            # Einzelzimmer komplett
    "lieferzeit_tage": 28,        # Möbel-Lieferzeit ab Bestellung
    "modus": "budget",            # budget = Baubudget fest | ziel = Zimmerziel
    "ziel_zimmer": 9,
    "budget_bau": None,           # feste Grenze je Jahr (verfällt)
    "moebel_obergrenze": None,    # optional: was realistisch genehmigt wird (weiche Grenze)
    "neben_pct": 0,               # Elektro, Sanitär, Entsorgung … in % vom Bau
    "puffer_bau_pct": 0,          # Puffer nur, wenn gewollt – sonst gilt der Angebotspreis
    "puffer_moebel_pct": 0,
    "vorsteuer_pct": 0,           # 0 = Umsatzsteuer ist voll Kosten (brutto)
    "preis_pct": 3,               # Preissteigerung Bau je Jahr
    "preis_moebel_pct": 3,        # Preissteigerung Möbel je Jahr
    "preisstand": 0,              # Jahr der Preise (0 = laufendes Jahr)
    "vorlauf_tage": 56,           # Belegungsstopp vor Baubeginn
    "gesperrt": [],               # Monate (1–12) ohne Renovierung
    "haus_vorrang": "",           # "" | "2" | "6"
    "kernbestand": False,         # Reserve-Etagen von der Renovierung ausnehmen
    "kern_puffer_pct": 5,         # Sicherheitspuffer auf den Spitzenbedarf
    "typ_reserve_pct": 3,         # Reserve für Zimmertypen (nur Männer, EMR, Doppel …)
    "angebote": [],               # eingelesene Angebote: {haus, art, netto, zimmer, datum, datei}
    "herkunft": {},               # "Haus.Feld" → "eingabe" (von Hand geändert)
}
KURZ_GRUPPEN = ("EMR", "ASS", "UWT", "Gast")
FRISCH_JAHRE = 5
BAU_MAENGEL = {"boden_kaputt", "boden_dreckig", "wand", "schimmel", "geruch"}
MOEBEL_MAENGEL = {"moebel", "matratze"}
KLASSEN_WERT = {"A": 100, "B": 10, "C": 1, None: 0}
UNSICHER = {"angebot": .10, "eingabe": .15, "schaetzung": .25, "platzhalter": .40}
HERKUNFT_TEXT = {"angebot": "Angebot", "eingabe": "Eingabe", "schaetzung": "Schätzung", "platzhalter": "Platzhalter"}
ARTEN = {"etage": "ganze Etage", "zimmer": "Einzelzimmer komplett", "moebel": "nur Möbel tauschen"}


# ---- Ablage -------------------------------------------------------------------------------

def _roh() -> dict:
    return speicher.lesen(DATEI, {})


def parameter() -> dict:
    roh = _roh().get("parameter") or {}
    p = {**STANDARD, **{k: v for k, v in roh.items() if k in STANDARD}}
    if "moebel_obergrenze" not in roh and roh.get("budget_moebel") is not None:     # 0.42/0.43: Möbelbudget → Obergrenze
        p["moebel_obergrenze"] = roh["budget_moebel"]
    if "modus" not in roh:
        p["modus"] = "budget"
    kosten_ = {}
    for h in p["haeuser"]:
        alt = (roh.get("kosten") or {}).get(h) or {}
        if "bau_etage" not in alt:                 # Annahmen von 0.39/0.40 (Flur-Pauschale) nicht übernehmen
            alt = {}
        kosten_[h] = {**_HAUS_STANDARD, **STANDARD["kosten"].get(h, {}), **alt}
    p["kosten"] = kosten_
    p["herkunft"] = dict(p.get("herkunft") or {})
    if not p.get("preisstand"):
        p["preisstand"] = date.today().year
    return p


def parameter_speichern(p: dict) -> str:
    roh = _roh()
    roh["parameter"] = {k: p[k] for k in STANDARD if k in p}
    speicher.schreiben(DATEI, roh)
    return "Planungsannahmen gespeichert"


def herkunft(p: dict, haus: str, feld: str) -> str:
    """angebot | eingabe | platzhalter – woher ein Kostenwert stammt."""
    art = "moebel" if feld == "moebel_zimmer" else "bau" if feld.startswith(("bau_etage", "einheit_")) else ""
    if art and any(str(a.get("haus")) == haus and a.get("art") == art for a in p.get("angebote") or []):
        return "angebot"
    if p.get("herkunft", {}).get(f"{haus}.{feld}") == "eingabe":
        return "eingabe"
    std = (STANDARD["kosten"].get(haus) or _HAUS_STANDARD).get(feld, _HAUS_STANDARD.get(feld))
    wert = (p["kosten"].get(haus) or {}).get(feld)
    return "platzhalter" if wert == std or not wert else "eingabe"


def herkunft_merken(alt: dict, neu: dict) -> dict:
    """Von Hand geänderte Kostenwerte als „Eingabe“ kennzeichnen."""
    h = dict(neu.get("herkunft") or alt.get("herkunft") or {})
    for haus, werte in (neu.get("kosten") or {}).items():
        for feld, wert in werte.items():
            if (alt.get("kosten", {}).get(haus) or {}).get(feld) != wert:
                h[f"{haus}.{feld}"] = "eingabe"
    return {**neu, "herkunft": h}


# ---- Kosten -------------------------------------------------------------------------------------

@dataclass
class Kosten:
    zimmer: int
    jahr: int
    bau: float = 0.0              # Maler/Boden (netto, mit Preissteigerung)
    neben: float = 0.0
    moebel: float = 0.0
    aufbau: float = 0.0
    puffer_bau: float = 0.0
    puffer_moebel: float = 0.0
    ust_bau: float = 0.0          # nicht abziehbare Umsatzsteuer auf den Bau-Teil
    ust_moebel: float = 0.0
    luecken: list = field(default_factory=list)
    art: str = "etage"
    herleitung: list = field(default_factory=list)   # (Text, Betrag)
    herkunft_bau: str = "platzhalter"
    herkunft_moebel: str = "platzhalter"
    basis_bau: float = 0.0        # Bau netto wie im Angebot (ohne Steigerung, Nebenkosten, Puffer)
    ust_satz: float = 0.0         # nicht abziehbarer Steuersatz
    u_bau: float = 0.0            # Unsicherheit (± €) des Bau-Teils – addiert sich beim Zusammenrechnen
    u_moebel: float = 0.0
    ungewiss: float = 0.0         # Betrag, der nicht aus einem Angebot stammt

    def _unsicherheit(self) -> "Kosten":
        self.u_bau = self.instandhaltung * UNSICHER.get(self.herkunft_bau, .4)
        self.u_moebel = self.investition * UNSICHER.get(self.herkunft_moebel, .4)
        self.ungewiss = ((self.instandhaltung if self.herkunft_bau != "angebot" else 0)
                         + (self.investition if self.herkunft_moebel != "angebot" else 0))
        return self

    @property
    def basis_brutto(self) -> float:
        """Bau so, wie er im Angebot steht (inkl. nicht abziehbarer Steuer) – zum Abgleich mit dem Angebot."""
        return self.basis_bau * (1 + self.ust_satz)

    @property
    def puffer(self) -> float:
        return self.puffer_bau + self.puffer_moebel

    @property
    def ust(self) -> float:
        return self.ust_bau + self.ust_moebel

    @property
    def netto(self) -> float:
        return self.bau + self.neben + self.moebel + self.aufbau + self.puffer

    @property
    def instandhaltung(self) -> float:
        """Bau-Budget: Bau + Nebenkosten + Bau-Puffer + darauf nicht abziehbare Steuer."""
        return self.bau + self.neben + self.puffer_bau + self.ust_bau

    @property
    def investition(self) -> float:
        """Möbel-Budget: Möbel + Aufbau + Möbel-Puffer + Steuer."""
        return self.moebel + self.aufbau + self.puffer_moebel + self.ust_moebel

    @property
    def summe(self) -> float:
        return self.instandhaltung + self.investition

    @property
    def je_zimmer(self) -> float:
        return self.summe / self.zimmer if self.zimmer else 0.0

    @property
    def spanne(self) -> tuple[float, float]:
        """(von, bis) – Unsicherheit nach Herkunft der Werte (Angebot ±10 % … Platzhalter ±40 %)."""
        d = self.u_bau + self.u_moebel
        return self.summe - d, self.summe + d

    def spanne_von(self, teil: str) -> tuple[float, float]:
        wert = self.instandhaltung if teil == "bau" else self.investition
        u = self.u_bau if teil == "bau" else self.u_moebel
        return wert - u, wert + u

    @property
    def geschaetzt(self) -> float:
        """Anteil (0–1) der Summe, der nicht aus einem Angebot stammt."""
        return self.ungewiss / self.summe if self.summe else 0.0

    def plus(self, o: "Kosten") -> "Kosten":
        schlechter = lambda a, b: max(a, b, key=lambda h: UNSICHER.get(h, .4)) if (a and b) else (a or b)
        return Kosten(self.zimmer + o.zimmer, max(self.jahr, o.jahr), self.bau + o.bau, self.neben + o.neben,
                      self.moebel + o.moebel, self.aufbau + o.aufbau, self.puffer_bau + o.puffer_bau,
                      self.puffer_moebel + o.puffer_moebel, self.ust_bau + o.ust_bau, self.ust_moebel + o.ust_moebel,
                      sorted(set(self.luecken) | set(o.luecken)), self.art if self.art == o.art else "gemischt", [],
                      schlechter(self.herkunft_bau if self.instandhaltung else "", o.herkunft_bau if o.instandhaltung else "")
                      or "angebot",
                      schlechter(self.herkunft_moebel if self.investition else "", o.herkunft_moebel if o.investition else "")
                      or "angebot", self.basis_bau + o.basis_bau, max(self.ust_satz, o.ust_satz),
                      self.u_bau + o.u_bau, self.u_moebel + o.u_moebel, self.ungewiss + o.ungewiss)


def gueltig_bis(p: dict, haus: str | None, moebel: bool = False) -> date | None:
    """Bis wann gilt das Angebot (Festpreis)? Eintrag je Haus und Art, sonst None."""
    if not haus:
        return None
    try:
        return date.fromisoformat(str((p["kosten"].get(haus) or {}).get("gueltig_moebel" if moebel else "gueltig_bau") or "")[:10])
    except ValueError:
        return None


def preisfaktor(p: dict, jahr: int, moebel: bool = False, haus: str | None = None) -> float:
    """Preissteigerung ab Preisstand. 0.46: Solange ein Angebot gilt (Festpreis), wird nicht hochgerechnet – erst ab dem
    Jahr nach Ablauf."""
    pct = p.get("preis_moebel_pct") if moebel else p.get("preis_pct")
    basis = int(p.get("preisstand") or jahr)
    if (g := gueltig_bis(p, haus, moebel)) is not None:
        basis = max(basis, g.year)
    return (1 + float(pct or 0) / 100) ** max(0, jahr - basis)


def bau_je_einzelzimmer(p: dict, haus: str, n_etage: int) -> tuple[float, str, str]:
    """(Bau netto je Einzelzimmer, Herkunft, Erklärung): eigener Preis › Einheitspreise × Zimmerfläche ›
    anteilig aus der Etage + Aufschlag (Schätzung)."""
    k = p["kosten"].get(haus) or {}
    if k.get("bau_zimmer"):
        return float(k["bau_zimmer"]), "eingabe", "eigener Preis je Einzelzimmer"
    if k.get("zimmer_boden_m2") and (k.get("einheit_boden") or k.get("einheit_wand")):
        je = (float(k.get("zimmer_boden_m2") or 0) * float(k.get("einheit_boden") or 0)
              + float(k.get("zimmer_wand_m2") or 0) * float(k.get("einheit_wand") or 0)
              + float(k.get("zimmer_tueren") or 0) * float(k.get("einheit_tuer") or 0))
        hk = "angebot" if herkunft(p, haus, "einheit_boden") == "angebot" else "eingabe"
        return je, hk, (f"Einheitspreise × Fläche: Boden {k.get('zimmer_boden_m2')} m² × {euro2(k.get('einheit_boden'))}, "
                        f"Wand/Decke {k.get('zimmer_wand_m2')} m² × {euro2(k.get('einheit_wand'))}, "
                        f"{k.get('zimmer_tueren')} Tür × {euro2(k.get('einheit_tuer'))}")
    je = float(k.get("bau_etage") or 0) / max(1, n_etage) * (1 + float(p.get("einzel_aufschlag_pct") or 0) / 100)
    return je, "schaetzung", f"anteilig aus der Etage + {p.get('einzel_aufschlag_pct')} % Aufschlag"


def kosten(p: dict, haus: str, zimmer: int, jahr: int | None = None, art: str = "etage", n_etage: int | None = None) -> Kosten:
    """Kosten einer Maßnahme im Jahr ``jahr``: ``etage`` = ganze Etage, ``zimmer`` = Einzelzimmer komplett,
    ``moebel`` = nur Möbel tauschen. Puffer je Budget, Steuer laut Vorsteuerquote, Herkunft je Teil."""
    jahr = jahr or int(p.get("preisstand") or date.today().year)
    k = p["kosten"].get(haus) or {}
    fb, fm = preisfaktor(p, jahr, False, haus), preisfaktor(p, jahr, True, haus)
    h = []
    hk_bau = "angebot"
    if art == "etage":
        bau0 = float(k.get("bau_etage") or 0)
        hk_bau = herkunft(p, haus, "bau_etage")
        h.append((f"Bau (Maler, Boden) je Etage, netto [{HERKUNFT_TEXT[hk_bau]}]", bau0))
    elif art == "zimmer":
        je, hk_bau, wie = bau_je_einzelzimmer(p, haus, n_etage or zimmer)
        bau0 = je * zimmer
        h.append((f"Bau je Einzelzimmer {euro(je)} × {zimmer} ({wie}) [{HERKUNFT_TEXT[hk_bau]}]", bau0))
    else:
        bau0 = 0.0
    hk_m = herkunft(p, haus, "moebel_zimmer")
    erg = Kosten(zimmer, jahr, bau0 * fb, art=art, herkunft_bau=hk_bau, herkunft_moebel=hk_m, basis_bau=bau0,
                 ust_satz=UST * (1 - float(p.get("vorsteuer_pct") or 0) / 100))
    if fb != 1 and bau0:
        h.append((f"Preissteigerung Bau bis {jahr} (× {fb:.3f})", erg.bau - bau0))
    elif bau0 and (g := gueltig_bis(p, haus)) and jahr <= g.year:
        h.append((f"Festpreis – Angebot gilt bis {g:%d.%m.%Y}, keine Preissteigerung", 0.0))
    erg.neben = erg.bau * float(p.get("neben_pct") or 0) / 100
    if erg.neben:
        h.append((f"Nebenkosten {p.get('neben_pct')} % vom Bau", erg.neben))
    erg.moebel = float(k.get("moebel_zimmer") or 0) * zimmer * fm
    erg.aufbau = float(k.get("aufbau_zimmer") or 0) * zimmer * fm
    h.append((f"Möbel {euro(float(k.get('moebel_zimmer') or 0))} × {zimmer} Zimmer [{HERKUNFT_TEXT[hk_m]}]"
              + (f", Preissteigerung × {fm:.3f}" if fm != 1 else ""), erg.moebel))
    h.append((f"Aufbau {euro(float(k.get('aufbau_zimmer') or 0))} × {zimmer} Zimmer", erg.aufbau))
    erg.puffer_bau = (erg.bau + erg.neben) * float(p.get("puffer_bau_pct") or 0) / 100
    erg.puffer_moebel = (erg.moebel + erg.aufbau) * float(p.get("puffer_moebel_pct") or 0) / 100
    satz = UST * (1 - float(p.get("vorsteuer_pct") or 0) / 100)
    erg.ust_bau = (erg.bau + erg.neben + erg.puffer_bau) * satz
    erg.ust_moebel = (erg.moebel + erg.aufbau + erg.puffer_moebel) * satz
    if erg.puffer_bau:
        h.append((f"Puffer Bau {p.get('puffer_bau_pct')} % (Untergrund, Feuchte, Elektro)", erg.puffer_bau))
    if erg.puffer_moebel:
        h.append((f"Puffer Möbel {p.get('puffer_moebel_pct')} % (Fracht, Preisänderung)", erg.puffer_moebel))
    h.append((f"Umsatzsteuer 19 %, davon nicht abziehbar {100 - float(p.get('vorsteuer_pct') or 0):g} %", erg.ust))
    erg.herleitung = h
    erg._unsicherheit()
    if art != "moebel" and hk_bau in ("platzhalter",):
        erg.luecken.append(f"Haus {haus}: Baukosten sind ein Platzhalter – Angebot einlesen")
    if not k.get("moebel_zimmer"):
        erg.luecken.append(f"Haus {haus}: Möbelpreis je Zimmer fehlt")
    return erg


def euro(x: float) -> str:
    return f"{x:,.0f} €".replace(",", ".")


def euro2(x) -> str:
    return f"{float(x or 0):,.2f} €".replace(",", "X").replace(".", ",").replace("X", ".")


def tsd(x: float) -> str:
    """Auf 1.000 € gerundet: „95 T€“."""
    return f"{round(x / 1000):,} T€".replace(",", ".")


def spanne_text(von: float, bis: float) -> str:
    return f"{tsd(von)}–{tsd(bis)}" if round(von / 1000) != round(bis / 1000) else tsd(von)


# ---- Angebot einlesen ------------------------------------------------------------------------------

# Abstand bis zur Zahl großzügig: PDF-Texte im Layout-Modus haben dort oft Dutzende Leerzeichen („Nettosumme   =   EUR   12.345,67“)
_SUMME = re.compile(r"(?:Nettosumme|Netto-?Summe|Summe\s+netto|Gesamt\s*netto|Nettobetrag|Warenwert\s+o\.?\s*MwSt\.?)"
                    r"[^\d\n]{0,200}?(\d{1,3}(?:\.\d{3})*,\d{2})", re.I)
_BRUTTO = re.compile(r"(?:Bruttosumme|Brutto-?Summe|Gesamtbetrag|Summe\s+brutto|Gesamt\s*brutto)"
                     r"[^\d\n]{0,200}?(\d{1,3}(?:\.\d{3})*,\d{2})", re.I)
_STUECK = re.compile(r"^\s*(\d{1,3})\s+St(?:ü|ue|u)?ck\b", re.I | re.M)
_HAUS = re.compile(r"(?:Geb(?:ä|ae)ude|Haus)\s*(\d+(?:\.\d)?)", re.I)
_POS = re.compile(r"^\s*(\d{1,3})\s+(?:ca\.\s*)?(\d{1,3}(?:\.\d{3})*,\d{2})\s*(m²|m2|qm|lfm|Stk\.?|Stck\.?|Stück|Std\.?|kg)\s+"
                  r"(.+?)\s+(\d{1,3}(?:\.\d{3})*,\d{2})\s*€?\s+(\d{1,3}(?:\.\d{3})*,\d{2})\s*€?\s*$", re.I | re.M)
_BODEN = re.compile(r"Boden|Belag|Sockel|Ausgleich|grundier|Spachtel|Streifen|Profil|Teppich|Textil|Vinyl", re.I)
_WAND = re.compile(r"Wand|Decke|Tapete|Raufaser|Anstrich|Dämm|Daemm|Kleber|Heizk", re.I)
_TUER = re.compile(r"T(?:ü|ue)r", re.I)


def _zahl(t: str) -> float:
    return float(t.replace(".", "").replace(",", "."))


def positionen(text: str) -> list[dict]:
    """Angebotspositionen: {menge, einheit, text, einzel, betrag, gruppe (boden|wand|tuer|sonst)}."""
    erg = []
    for m in _POS.finditer(text):
        menge, einheit, txt = _zahl(m.group(2)), m.group(3).lower().rstrip("."), m.group(4).strip()
        gruppe = "tuer" if _TUER.search(txt) else "wand" if _WAND.search(txt) else "boden" if _BODEN.search(txt) else "sonst"
        erg.append({"menge": menge, "einheit": "m²" if einheit in ("m2", "qm", "m²") else einheit, "text": txt,
                    "einzel": _zahl(m.group(5)), "betrag": _zahl(m.group(6)), "gruppe": gruppe})
    return erg


def einheitspreise(pos: list[dict]) -> dict:
    """€/m² Boden, €/m² Wand+Decke, € je Tür aus den Positionen eines Bau-Angebots. Material und Nebenarbeiten der
    Gruppe sind eingerechnet (Summe der Gruppe ÷ größte m²-Menge der Gruppe); „sonstige“ Positionen anteilig."""
    def gruppe(g):
        teile = [x for x in pos if x["gruppe"] == g]
        flaeche = max((x["menge"] for x in teile if x["einheit"] == "m²"), default=0)
        return sum(x["betrag"] for x in teile), flaeche
    sb, fb = gruppe("boden")
    sw, fw = gruppe("wand")
    st = [x for x in pos if x["gruppe"] == "tuer"]
    sonst = sum(x["betrag"] for x in pos if x["gruppe"] == "sonst")
    faktor = 1 + sonst / (sb + sw) if sb + sw else 1
    return {"einheit_boden": round(sb / fb * faktor, 2) if fb else 0, "einheit_wand": round(sw / fw * faktor, 2) if fw else 0,
            "einheit_tuer": round(st[0]["einzel"], 2) if st else 0, "boden_m2": fb, "wand_m2": fw}


def angebot_auswerten(text: str) -> dict:
    """Aus dem Text eines Angebots: Nettosumme, Art (Bau oder Möbel), Haus, bei Möbeln die Zimmerzahl, bei Bau die
    Einheitspreise. Nur Vorschlag – die Oberfläche zeigt es vor dem Speichern zur Bestätigung."""
    netto = [_zahl(m) for m in _SUMME.findall(text)]
    brutto = [_zahl(m) for m in _BRUTTO.findall(text)]
    if not netto and brutto:
        netto = [round(brutto[-1] / (1 + UST), 2)]
    moebel = bool(re.search(r"Warenwert|Bettgestell|Matratze|Schreibtisch|Kleiderschrank|Möbel", text, re.I))
    stueck = [int(x) for x in _STUECK.findall(text)]
    zimmer = max(set(stueck), key=stueck.count) if stueck else 0
    haus = _HAUS.search(text)
    erg = {"netto": netto[-1] if netto else 0.0, "art": "moebel" if moebel else "bau",
           "haus": haus.group(1) if haus else "", "zimmer": zimmer if moebel else 0}
    if not moebel:
        erg.update(einheitspreise(positionen(text)))
    if g := _GUELTIG.search(text):                       # „gültig bis 31.03.2027“, „Bindefrist: …“
        t, m, j = (int(x) for x in g.group(1, 2, 3))
        try:
            erg["gueltig_bis"] = date(j + 2000 if j < 100 else j, m, t).isoformat()
        except ValueError:
            pass
    return erg


_GUELTIG = re.compile(r"(?:gültig\s+bis(?:\s+zum)?|Bindefrist(?:\s+bis)?|Angebot\s+gilt\s+bis)[:\s]*(\d{1,2})\.(\d{1,2})\.(\d{2,4})",
                      re.I)


def angebot_lesen(pfad) -> dict:
    from .pdf_anreise_kern import text_lesen

    return angebot_auswerten(text_lesen(pfad))


def angebot_uebernehmen(p: dict, ang: dict) -> dict:
    """Ein bestätigtes Angebot in die Annahmen übernehmen (Bau je Etage + Einheitspreise bzw. Möbel je Zimmer)."""
    if str(ang.get("haus") or "") == "alle":                  # z. B. Möbel: gleiche Ausstattung in allen Häusern
        for haus in p["haeuser"]:
            p = angebot_uebernehmen(p, {**ang, "haus": haus})
        return p
    neu = {**p, "kosten": {h: dict(v) for h, v in p["kosten"].items()}, "angebote": list(p.get("angebote") or [])}
    h = str(ang.get("haus") or "")
    if h not in neu["kosten"]:
        raise ValueError(f"Haus „{h}“ wird nicht geplant (Häuser: {', '.join(neu['haeuser'])}).")
    if ang["art"] == "moebel":
        n = int(ang.get("zimmer") or 0)
        if n <= 0:
            raise ValueError("Für ein Möbel-Angebot bitte angeben, für wie viele Zimmer es gilt.")
        neu["kosten"][h]["moebel_zimmer"] = round(float(ang["netto"]) / n, 2)
    else:
        neu["kosten"][h]["bau_etage"] = round(float(ang["netto"]), 2)
        for f in ("einheit_boden", "einheit_wand", "einheit_tuer"):
            if ang.get(f):
                neu["kosten"][h][f] = round(float(ang[f]), 2)
    neu["angebote"] = [x for x in neu["angebote"] if not (x.get("haus") == h and x.get("art") == ang["art"])]
    neu["angebote"].append({k: ang.get(k) for k in ("haus", "art", "netto", "zimmer", "datum", "datei", "gueltig_bis")})
    feld = "gueltig_moebel" if ang["art"] == "moebel" else "gueltig_bau"
    if ang.get("gueltig_bis"):
        neu["kosten"][h][feld] = str(ang["gueltig_bis"])[:10]
    else:
        neu["kosten"][h].pop(feld, None)
    if ang.get("datum"):
        neu["preisstand"] = int(str(ang["datum"])[:4])
    return neu


def angebote_alt(p: dict, heute: date, monate: int = 12) -> list[str]:
    """Angebote, die älter als ``monate`` sind (Datum beim Einlesen)."""
    erg = []
    for a in p.get("angebote") or []:
        try:
            d = date.fromisoformat(str(a.get("datum") or "")[:10])
        except ValueError:
            continue
        if (heute - d).days > monate * 30.5:
            erg.append(f"Haus {a.get('haus')} {'Möbel' if a.get('art') == 'moebel' else 'Bau'} vom {d:%d.%m.%Y}")
    return erg


# ---- Vormerkungen ------------------------------------------------------------------------------------

def plan() -> list[dict]:
    """Vorgemerkte Renovierungen: {flur: "2|3|", start, ende (ISO), art (etage|zimmer|moebel), zimmer: [IDs], notiz}."""
    return [{"art": "etage", "zimmer": [], **e} for e in (_roh().get("plan") or [])]


def _gleich(e: dict, flur: str, art: str, zimmer: list, jahr: int) -> bool:
    return (e["flur"] == flur and e.get("art", "etage") == art and sorted(e.get("zimmer") or []) == sorted(zimmer or [])
            and e["start"][:4] == str(jahr))


def vormerken(flur: str, start: date, ende: date, notiz: str = "", art: str = "etage", zimmer: list | None = None) -> str:
    roh = _roh()
    eintraege = [e for e in roh.get("plan") or [] if not _gleich(e, flur, art, zimmer or [], start.year)]
    neu = {"flur": flur, "start": start.isoformat(), "ende": ende.isoformat(), "notiz": notiz}
    if art != "etage":
        neu.update(art=art, zimmer=list(zimmer or []))
    eintraege.append(neu)
    roh["plan"] = sorted(eintraege, key=lambda e: (e["start"], e["flur"]))
    speicher.schreiben(DATEI, roh)
    was = flur_text_schluessel(flur) if art == "etage" else f"{len(zimmer or [])} Zimmer ({ARTEN[art]})"
    return f"{was} vorgemerkt: {start:%d.%m.} – {ende:%d.%m.%Y} (unverbindlich)"


def entfernen(flur: str, start: str, art: str | None = None) -> str:
    roh = _roh()
    roh["plan"] = [e for e in roh.get("plan") or [] if not (e["flur"] == flur and e["start"] == start
                                                           and (art is None or e.get("art", "etage") == art))]
    speicher.schreiben(DATEI, roh)
    return f"{flur_text_schluessel(flur)}: Vormerkung entfernt"


# ---- Etagen und Bedarf (Klassen) -------------------------------------------------------------------

def schluessel(haus: str, etage: str, flur: str) -> str:
    return f"{haus}|{etage}|{flur}"


def flur_text_schluessel(k: str) -> str:
    haus, etage, flur = (k.split("|") + ["", "", ""])[:3]
    return f"Haus {haus} · {zp.etage_text(etage)}" + (f" {flur}" if flur else "")


def zustandsnoten() -> dict:
    """Etage → Note 1–5 aus einer Begehung (Steuerung → Kennzahlen → Werte eingeben)."""
    return {k: int(v) for k, v in (_roh().get("zustand") or {}).items() if v}


def zustandsnoten_speichern(noten: dict) -> str:
    roh = _roh()
    roh["zustand"] = {k: int(v) for k, v in noten.items() if v}
    speicher.schreiben(DATEI, roh)
    return f"Zustandsnoten für {len(roh['zustand'])} Etagen gespeichert"


@dataclass
class ZBedarf:
    """Bedarf eines Zimmers: Klasse A/B/C/None je Bau und Möbel, Gründe, Bau gesperrt (frisch renoviert)."""
    bau: str | None = None
    moebel: str | None = None
    gruende: list = field(default_factory=list)
    frisch: bool = False
    alter: float | None = None

    @property
    def wert_bau(self) -> int:
        return 0 if self.frisch else KLASSEN_WERT[self.bau]

    @property
    def wert_moebel(self) -> int:
        return KLASSEN_WERT[self.moebel]

    @property
    def a(self) -> bool:
        return (self.bau == "A" and not self.frisch) or self.moebel == "A"


def _max_klasse(*k):
    for x in ("A", "B", "C"):
        if x in k:
            return x
    return None


def zimmer_bedarf(z, maengel_: list, heute: date, note: int | None) -> ZBedarf:
    """Klassen je Zimmer. Bau: A = „Renovierung nötig“, Schimmel, Note 5, ≥ 20 Jahre; B = Note 4, ≥ 15 Jahre, Boden-/
    Wand-/Geruchsmangel; C = Note 3, ≥ 10 Jahre. Möbel: A = Möbel-/Matratzenmangel, „Renovierung nötig“; B = ≥ 15
    Jahre; C = ≥ 10 Jahre. In den letzten 5 Jahren renoviert: kein Bau."""
    from belegung import zimmerliste as zl

    zb = ZBedarf()
    bau, mob = [], []
    arten = {m.art for m in maengel_}
    if "renovierung" in arten:
        bau.append("A"), mob.append("A"), zb.gruende.append("Renovierung nötig")
    if "schimmel" in arten:
        bau.append("A"), zb.gruende.append("Schimmel")
    if arten & (BAU_MAENGEL - {"schimmel"}):
        bau.append("B"), zb.gruende.append("Boden/Wand/Geruch")
    if arten & MOEBEL_MAENGEL:
        mob.append("A"), zb.gruende.append("Möbel/Matratze")
    if note:
        bau.append({5: "A", 4: "B", 3: "C"}.get(note))
        if note >= 4:
            zb.gruende.append(f"Zustandsnote {note}")
    d = zl.reno_datum(z) if z.renoviert else None
    if d:
        j = (heute - d).days / 365.25
        zb.alter = round(j, 1)
        if j < FRISCH_JAHRE:
            zb.frisch = True
            zb.gruende.append(f"renoviert vor {max(j, 0):.0f} J. – kein Bau")
        else:
            bau.append("A" if j >= 20 else "B" if j >= 15 else "C" if j >= 10 else None)
            mob.append("B" if j >= 15 else "C" if j >= 10 else None)
            if j >= 15:
                zb.gruende.append(f"seit {j:.0f} J. nicht renoviert")
    zb.bau, zb.moebel = _max_klasse(*bau), _max_klasse(*mob)
    return zb


@dataclass
class Flur:
    schluessel: str
    haus: str
    etage: str
    flur: str
    zimmer: list = field(default_factory=list)     # zp.Zimmer
    bedarf: float = 0.0                            # Ø Wert je Zimmer (für die Reihenfolge)
    gruende: list = field(default_factory=list)    # (Wert, Text)
    luecken: list = field(default_factory=list)
    reno_bekannt: int = 0
    alter: float | None = None
    sonder: list = field(default_factory=list)
    kosten: Kosten | None = None
    bedarfe: dict = field(default_factory=dict)    # Zimmer-ID → ZBedarf
    zustand: int | None = None

    @property
    def text(self) -> str:
        return flur_text_schluessel(self.schluessel)

    @property
    def betten(self) -> int:
        return sum(z.betten for z in self.zimmer)

    @property
    def wert(self) -> float:
        return sum(b.wert_bau + b.wert_moebel for b in self.bedarfe.values())

    def klassen(self, art: str = "bau") -> dict:
        erg = {"A": 0, "B": 0, "C": 0}
        for b in self.bedarfe.values():
            k = b.bau if art == "bau" and not b.frisch else b.moebel if art == "moebel" else None
            if k:
                erg[k] += 1
        return erg

    @property
    def klassen_text(self) -> str:
        teile = []
        for art, name in (("bau", "Bau"), ("moebel", "Möbel")):
            k = self.klassen(art)
            if any(k.values()):
                teile.append(f"{name} " + " ".join(f"{x}{n}" for x, n in k.items() if n))
        return " · ".join(teile) or "kein Bedarf erfasst"

    @property
    def ampel(self) -> str:
        if any(b.a for b in self.bedarfe.values()):
            return "krit"
        return "warn" if any("B" in (b.bau, b.moebel) for b in self.bedarfe.values()) else "ok"

    @property
    def sonderzimmer(self) -> bool:
        """EMR-, Gäste- oder Kurzmaßnahmen-Etage – nie als Reserve vorschlagen."""
        return any(zp.nur_emr(z) or z.gaeste or zp.nur_kurz(z) for z in self.zimmer)


def flure(stand: zp.Planstand, heute: date | None = None, p: dict | None = None, offen: dict | None = None,
          noten: dict | None = None) -> list[Flur]:
    """Alle Etagen der gewählten Häuser mit Bedarf je Zimmer – höchster Bedarf zuerst."""
    from belegung import maengel as mg
    from belegung import zimmerliste as zl

    heute = heute or date.today()
    p = p or parameter()
    offen = mg.offen_je_zimmer() if offen is None else offen
    noten = zustandsnoten() if noten is None else noten
    je: dict[str, Flur] = {}
    for z in stand.zimmer:
        if not z.aktiv or z.haus not in p["haeuser"]:
            continue
        k = schluessel(z.haus, z.etage, "")
        je.setdefault(k, Flur(k, z.haus, z.etage, "")).zimmer.append(z)
    for f in je.values():
        n = len(f.zimmer)
        f.zustand = noten.get(f.schluessel)
        jahre, ohne_datum, unbew = [], 0, 0
        for z in f.zimmer:
            f.bedarfe[z.id] = b = zimmer_bedarf(z, offen.get(z.id, []), heute, f.zustand)
            if b.alter is not None:
                jahre.append(b.alter)
            if z.renoviert:
                f.reno_bekannt += 1
                if zl.reno_datum(z) is None:
                    ohne_datum += 1
            if z.id in stand.lage.unbewohnbar:
                unbew += 1
        for art, name in (("bau", "Bau"), ("moebel", "Möbel")):
            for kl, anz in f.klassen(art).items():
                if anz:
                    f.gruende.append((KLASSEN_WERT[kl] * anz, f"{anz} × {name} Klasse {kl}"))
        frisch = sum(1 for b in f.bedarfe.values() if b.frisch)
        if frisch:
            f.gruende.append((0, f"{frisch} Zimmer in den letzten {FRISCH_JAHRE} Jahren renoviert – dort kein Bau"))
        if unbew:
            f.gruende.append((0, f"{unbew} Zimmer derzeit unbewohnbar"))
        f.bedarf = round(f.wert / n, 1) if n else 0.0
        f.alter = round(sum(jahre) / len(jahre), 1) if jahre else None
        if f.reno_bekannt < n:
            f.luecken.append(f"{n - f.reno_bekannt} von {n} Zimmern ohne Renovierungsdatum – unbekannt, nicht „nie“")
        if ohne_datum:
            f.luecken.append(f"{ohne_datum} Zimmer „renoviert“ ohne Datum")
        if not f.zustand:
            f.luecken.append("keine Zustandsnote")
        if emr := sum(1 for z in f.zimmer if zp.nur_emr(z)):
            f.sonder.append(f"{emr} reine EMR-Zimmer")
        if any(zp.nur_kurz(z) for z in f.zimmer):
            f.sonder.append("Etage für Kurzmaßnahmen/Allergiker")
        if g := sum(1 for z in f.zimmer if z.gaeste):
            f.sonder.append(f"{g} Gästezimmer")
        if nm := sum(1 for z in f.zimmer if z.nur_maenner):
            f.sonder.append(f"{nm} „nur Männer“ (eigenes Bad über den Flur)")
        if dz := sum(1 for z in f.zimmer if z.betten > 1):
            f.sonder.append(f"{dz} Doppelzimmer")
        f.kosten = kosten(p, f.haus, n)
    return sorted(je.values(), key=lambda f: (-f.bedarf, f.haus, zp._etage_sort(f.etage), f.flur))


def a_zimmer(fl: list[Flur], ohne: set | None = None) -> int:
    """Zimmer mit Klasse A (Bau oder Möbel), ohne die in ``ohne``."""
    return sum(1 for f in fl for zid, b in f.bedarfe.items() if b.a and zid not in (ohne or set()))


# ---- Machbarkeit je Zeitfenster ---------------------------------------------------------------

@dataclass
class Fenster:
    start: date
    ende: date
    stopp_ab: date                                  # ab hier keine Neubelegung mehr (Vorlauf)
    umzug: list = field(default_factory=list)       # (Name, Zimmer kurz, bis, Gruppe) – wohnt im Bauzeitraum
    umleiten: list = field(default_factory=list)    # (Name, Zimmer kurz, Anreise, Gruppe) – reist im Bauzeitraum an
    nach_stopp: list = field(default_factory=list)  # zwischen Stopp und Start neu – sollte dann woanders hin
    mieter: int = 0
    frei_im_haus: int = 0                           # Zimmer im selben Haus (außerhalb des Flurs) im ganzen Zeitraum frei
    frei_gesamt: int = 0                            # passende Zimmer in allen Häusern im ganzen Zeitraum frei
    ohne_ausweich: list = field(default_factory=list)   # (Name, Gruppe, Grund) – kein passendes freies Zimmer
    ausweich: dict = field(default_factory=dict)    # Haus → Anzahl der Ausweichzimmer
    gesperrt: bool = False
    prognose: tuple | None = None                   # (erwartet, lo80, hi80) Standort – nur Orientierung
    engpass: bool = False                           # obere Prognose erreicht die Warnschwelle der (verringerten) Kapazität
    gleichwertig: bool = False                      # Unterschied zu anderen Monaten kleiner als die Unsicherheit
    pruefbar: bool = True                           # liegt der Monat noch im Bereich bekannter Buchungen?

    @property
    def betroffen(self) -> int:
        return len(self.umzug) + len(self.umleiten)

    @property
    def stufe(self) -> str:
        if self.gesperrt:
            return "gesperrt"
        if not self.betroffen:
            return "frei" if self.pruefbar else "offen"
        return "eng" if self.ohne_ausweich else "ok"


def _gruppe(b) -> str:
    return zp.belegung_gruppe(b) or ""


def _geschlecht(b) -> str:
    return (b.grund if b.person else "") or zp.geschlecht_raten(b.name)


def _ausweichen(stand: zp.Planstand, fe: Fenster, personen: list, ohne: set[str]) -> None:
    """Für jede betroffene Person ein passendes, im ganzen Bauzeitraum freies Zimmer außerhalb der Baustelle(n) –
    wie beim Zuteilen: Gruppe erlaubt, „nur Männer“, Gäste-/EMR-/Doppelzimmer. Engste Personen zuerst."""
    frei = [z for z in stand.zimmer if z.aktiv and z.id not in ohne and z.id not in stand.lage.unbewohnbar
            and stand.lage.freie_betten(z.id, fe.start, fe.ende) > 0]
    fe.frei_gesamt = len(frei)

    def passend(gruppe: str, g: str):
        return [z for z in frei if zp.erlaubt(z, gruppe or "Reha") and (not z.nur_maenner or g == "m")]
    vergeben: set[str] = set()
    for name, gruppe, g in sorted(personen, key=lambda x: len(passend(x[1], x[2]))):
        z = next((z for z in passend(gruppe, g) if z.id not in vergeben), None)
        if z is None:
            grund = "kein passendes Zimmer frei" + (" (nur Frauen-taugliche fehlen)" if g == "w" else "")
            fe.ohne_ausweich.append((name, gruppe or "–", grund))
            continue
        vergeben.add(z.id)
        fe.ausweich[z.haus] = fe.ausweich.get(z.haus, 0) + 1


def fenster(stand: zp.Planstand, f: Flur, start: date, p: dict | None = None, ohne: set[str] | None = None) -> Fenster:
    """``ohne`` = Zimmer, die gleichzeitig anderweitig gesperrt sind (weitere Baustellen) – zählen nicht als Ausweich."""
    p = p or parameter()
    dauer = int((p["kosten"].get(f.haus) or {}).get("dauer_tage") or p.get("dauer_tage") or 30)
    ende = start + timedelta(days=dauer - 1)
    fe = Fenster(start, ende, start - timedelta(days=int(p["vorlauf_tage"])), gesperrt=start.month in (p.get("gesperrt") or []),
                 pruefbar=start <= buchungshorizont(stand))
    ids = {z.id for z in f.zimmer}
    personen = []
    for z in f.zimmer:
        for b in stand.lage.belegungen.get(z.id, []):
            if b.art not in ("belegt", "geplant") or not b.name or b.name == zp.PIVOT_NAME:
                continue
            if b.bis < start or b.von > ende:
                if fe.stopp_ab <= b.von < start:
                    fe.nach_stopp.append((zp.anzeige_name(b.name), z.kurz, b.von, _gruppe(b)))
                continue
            g = _gruppe(b)
            if g == "Mieter":
                fe.mieter += 1
            if b.von < start:
                fe.umzug.append((zp.anzeige_name(b.name), z.kurz, b.bis, g))
            else:
                fe.umleiten.append((zp.anzeige_name(b.name), z.kurz, b.von, g))
            personen.append((zp.anzeige_name(b.name), g, _geschlecht(b)))
    fe.frei_im_haus = sum(1 for z in stand.zimmer if z.aktiv and z.haus == f.haus and z.id not in ids
                          and z.id not in stand.lage.unbewohnbar and stand.lage.freie_betten(z.id, start, ende) > 0)
    _ausweichen(stand, fe, personen, ids | (ohne or set()))
    return fe


_HORIZONT: dict = {}


def buchungshorizont(stand: zp.Planstand) -> date:
    """Bis wann Buchungen bekannt sind (späteste bekannte Anreise) – danach sagt die Ausweichprüfung nichts."""
    if _HORIZONT.get("id") is not stand:
        tage = [b.von for b in getattr(stand, "bedarf", []) or []]
        tage += [b.von for v in stand.lage.belegungen.values() for b in v if b.art in ("belegt", "geplant") and b.name
                 and b.name != zp.PIVOT_NAME]
        _HORIZONT.update(id=stand, wert=max(tage) if tage else date.today())
    return _HORIZONT["wert"]


def monatsfenster(stand: zp.Planstand, f: Flur, jahr: int, p: dict | None = None,
                  prognose: dict | None = None) -> list[Fenster]:
    """Je Monat des Jahres ein Bauzeitraum ab dem Monatsersten. ``prognose``: {(Jahr, Monat): (erwartet, lo80, hi80)} –
    nur zur Orientierung, wo Buchungen noch nichts sagen."""
    p = p or parameter()
    fs = [fenster(stand, f, date(jahr, m, 1), p) for m in range(1, 13)]
    if prognose:
        for fe in fs:
            fe.prognose = prognose.get((jahr, fe.start.month))
    return fs


def bester_monat(fs: list[Fenster], heute: date) -> Fenster | None:
    """Erst die Machbarkeit (Ausweich für alle, wenig Betroffene, wenig Mieter). Sind mehrere Monate nach Buchungen
    gleich gut, entscheidet die Prognose – aber nur, wenn ihr Abstand größer ist als die halbe 80-%-Spanne; sonst
    heißen die Monate „gleichwertig“ und es gilt der früheste."""
    moeglich = [x for x in fs if not x.gesperrt and x.stopp_ab >= heute]
    if not moeglich:
        return None
    rang = lambda x: (bool(x.ohne_ausweich), x.engpass, x.betroffen, x.mieter)
    top = [x for x in moeglich if rang(x) == min(rang(y) for y in moeglich)]
    mit = [x for x in top if x.prognose]
    if len(mit) >= 2:
        best = min(mit, key=lambda x: x.prognose[0])
        rest = sorted(x.prognose[0] for x in mit if x is not best)
        mitte = rest[len(rest) // 2]
        spanne = (best.prognose[2] - best.prognose[1]) / 2
        if mitte - best.prognose[0] > spanne:
            return best
        for x in top:
            x.gleichwertig = True
    elif len(top) > 1:
        for x in top:
            x.gleichwertig = True
    return min(top, key=lambda x: x.start)


# ---- Ziel ------------------------------------------------------------------------------------------

@dataclass
class Auswahl:
    titel: str
    flure: list
    zimmer: int
    kosten: Kosten

    @property
    def text(self) -> str:
        return ", ".join(f.text for f in self.flure)


def _auswahl(titel: str, fl: list[Flur], p: dict, jahr: int) -> Auswahl:
    k = Kosten(0, jahr)
    for f in fl:
        k = k.plus(kosten(p, f.haus, len(f.zimmer), jahr))
    return Auswahl(titel, fl, sum(len(f.zimmer) for f in fl), k)


def ziel_auswahl(fl: list[Flur], p: dict, jahr: int, ziel: int | None = None) -> list[Auswahl]:
    """Ganze Etagen nach Bedarf, bis das Zimmerziel erreicht ist. Zwei Vorschläge, wenn das Ziel nicht aufgeht:
    knapp darunter und knapp darüber – jeweils mit Kosten."""
    ziel = int(ziel if ziel is not None else p.get("ziel_zimmer") or 0)
    if ziel <= 0 or not fl:
        return []
    gew, n = [], 0
    for f in fl:
        if n >= ziel:
            break
        gew.append(f)
        n += len(f.zimmer)
    erg = []
    if n > ziel and len(gew) > 1:
        unter = gew[:-1]
        erg.append(_auswahl(f"{sum(len(f.zimmer) for f in unter)} Zimmer (knapp unter dem Ziel)", unter, p, jahr))
    erg.append(_auswahl(f"{n} Zimmer" + (" (Ziel genau)" if n == ziel else " (knapp über dem Ziel)" if n > ziel else
                                         " (alle geplanten Etagen)"), gew, p, jahr))
    return erg


def bestand(fl: list[Flur]) -> int:
    return sum(len(f.zimmer) for f in fl)


def zyklus(fl: list[Flur], zimmer_je_jahr: float) -> float | None:
    """Jedes Zimmer etwa alle N Jahre (Bestand der geplanten Häuser ÷ Zimmer je Jahr)."""
    return round(bestand(fl) / zimmer_je_jahr, 1) if zimmer_je_jahr > 0 else None


def engpass_markieren(fs: list[Fenster], f: Flur, kap: float | None, belegt: list | None = None,
                      warn_anteil: float = .95) -> None:
    """Monat ist ein Engpass, wenn die obere Prognose die Warnschwelle der Kapazität erreicht – Kapazität minus diese
    Etage und minus Etagen, die im selben Monat schon im Bau sind (``belegt``: PlanZeilen)."""
    if not kap:
        return
    for fe in fs:
        if not fe.prognose:
            continue
        weg = f.betten + gesperrte_betten(belegt or [], date(fe.start.year, fe.start.month, 1))
        fe.engpass = fe.prognose[2] >= (kap - weg) * warn_anteil




# ---- Maßnahmen, Varianten, Auswahl ----------------------------------------------------------------

@dataclass
class Massnahme:
    art: str                      # etage | zimmer | moebel
    flur: Flur
    zimmer: list                  # zp.Zimmer
    wert: float                   # gedeckter Bedarf (Klassenwerte)
    kosten: Kosten
    a_zimmer: int = 0             # davon Klasse-A-Zimmer

    @property
    def text(self) -> str:
        if self.art == "etage":
            return f"{self.flur.text} (ganze Etage)"
        return f"{', '.join(z.kurz for z in self.zimmer)} ({ARTEN[self.art]})"


@dataclass
class Variante:
    schluessel: str
    titel: str
    erklaerung: str
    massnahmen: list = field(default_factory=list)
    hinweis: str = ""
    rest_bau: float | None = None

    @property
    def zimmer(self) -> int:
        return sum(len(m.zimmer) for m in self.massnahmen)

    @property
    def wert(self) -> float:
        return sum(m.wert for m in self.massnahmen)

    @property
    def a_zimmer(self) -> int:
        return sum(m.a_zimmer for m in self.massnahmen)

    @property
    def kosten(self) -> Kosten:
        k = Kosten(0, 0, herkunft_bau="", herkunft_moebel="")
        for m in self.massnahmen:
            k = k.plus(m.kosten)
        return k

    @property
    def etagen(self) -> list:
        return [m.flur for m in self.massnahmen if m.art == "etage"]

    def sperr_zimmermonate(self, p: dict) -> float:
        s = 0.0
        for m in self.massnahmen:
            tage = (int((p["kosten"].get(m.flur.haus) or {}).get("dauer_tage") or 30) if m.art == "etage" else
                    int(p.get("zimmer_tage") or 14) if m.art == "zimmer" else int(p.get("moebel_tage") or 3))
            s += len(m.zimmer) * tage / 30
        return round(s, 1)


def _wert(b: ZBedarf, art: str) -> float:
    return (b.wert_bau if art != "moebel" else 0) + b.wert_moebel


def _massnahme(p, f: Flur, zimmer: list, art: str, jahr: int) -> Massnahme:
    bs = [f.bedarfe.get(z.id) or ZBedarf() for z in zimmer]
    k = kosten(p, f.haus, len(zimmer), jahr, art, len(f.zimmer))
    return Massnahme(art, f, list(zimmer), sum(_wert(b, art) for b in bs), k,
                     sum(1 for b in bs if (b.a if art != "moebel" else b.moebel == "A")))


def _gruppieren(p, liste: list, jahr: int) -> list[Massnahme]:
    """(Flur, Zimmer, Art) → Maßnahmen je Etage und Art."""
    je: dict[tuple, list] = {}
    for f, z, art in liste:
        je.setdefault((f.schluessel, art), [f, []])[1].append(z)
    return [_massnahme(p, f, zs, art, jahr) for (_s, art), (f, zs) in je.items()]


def _zimmer_kandidaten(fl: list[Flur], frei: set, p: dict, jahr: int, art: str) -> list[tuple]:
    """(Wert je €, Wert, Bau-€, Möbel-€, Flur, Zimmer) – nur Zimmer mit Bedarf in dieser Art."""
    erg = []
    cache: dict[tuple, Kosten] = {}
    for f in fl:
        for z in f.zimmer:
            if z.id not in frei:
                continue
            b = f.bedarfe.get(z.id) or ZBedarf()
            w = _wert(b, art)
            if art == "zimmer" and not b.wert_bau:
                continue                                  # ohne Bau-Bedarf kein „komplett“
            if w <= 0:
                continue
            k = cache.setdefault((f.haus, art, len(f.zimmer)), kosten(p, f.haus, 1, jahr, art, len(f.zimmer)))
            preis = k.instandhaltung if art == "zimmer" else k.investition
            erg.append((w / max(preis, 1), w, k.instandhaltung, k.investition, f, z))
    return sorted(erg, key=lambda x: (-x[0], -x[1], x[4].haus, x[5].id))


def _fuellen(kand: list, rest_b: float | None, rest_m: float | None, belegt: set, ziel: int | None = None):
    """Gierig nach Bedarf je €: (Auswahl[(Flur, Zimmer)], Rest Bau, Rest Möbel)."""
    wahl = []
    for _r, _w, kb, km, f, z in kand:
        if z.id in belegt or (ziel is not None and len(wahl) >= ziel):
            continue
        if (rest_b is not None and kb > rest_b + .5) or (rest_m is not None and km > rest_m + .5):
            continue
        rest_b = None if rest_b is None else rest_b - kb
        rest_m = None if rest_m is None else rest_m - km
        wahl.append((f, z))
        belegt = belegt | {z.id}
    return wahl, rest_b, rest_m


def _moebel_a(fl: list[Flur], belegt: set) -> list[tuple]:
    """Zimmer mit Möbel-Klasse A, die noch keine Maßnahme haben → „nur Möbel“ (Teil des Möbelantrags)."""
    return [(f, z, "moebel") for f in fl for z in f.zimmer if z.id not in belegt and (f.bedarfe.get(z.id) or ZBedarf()).moebel == "A"]


def optimieren(fl: list[Flur], p: dict, jahr: int, budget_bau: float | None, moebel_grenze: float | None,
               ziel: int | None = None, mit_etagen: bool = True, mit_zimmern: bool = True, vorrang: str = "") -> tuple[list, float | None]:
    """Beste Kombination aus ganzen Etagen und Einzelzimmern: jede Etagenkombination im Baubudget (bzw. bis zum
    Zimmerziel), Rest gierig mit Einzelzimmern nach Bedarf je €. Ziel: meister Bedarf (Vorrang-Haus zuerst), dann
    mehr Zimmer, dann weniger Geld (0.46: nie nur zum Ausschöpfen). Ergebnis: ([(Flur, Zimmer, Art)], Rest Bau)."""
    etagen = [(f, kosten(p, f.haus, len(f.zimmer), jahr)) for f in fl][:16] if mit_etagen else []
    alle = {z.id for f in fl for z in f.zimmer}
    kand = _zimmer_kandidaten(fl, alle, p, jahr, "zimmer") if mit_zimmern else []
    best, best_wert, best_rest = [], None, budget_bau
    if budget_bau is None and ziel is None and moebel_grenze is None:
        return [(f, z, "etage") for f, _k in etagen for z in f.zimmer], None      # keine Grenze: alle Etagen

    def kombis(i: int, gew: list, sb: float, sm: float, nz: int):
        """Alle Etagenkombinationen, die in Budget bzw. Ziel passen (Äste, die schon zu teuer sind, werden abgeschnitten)."""
        yield gew, sb, sm, nz
        for j in range(i, len(etagen)):
            f, k = etagen[j]
            sb2, sm2, nz2 = sb + k.instandhaltung, sm + k.investition, nz + len(f.zimmer)
            if budget_bau is not None and sb2 > budget_bau + .5:
                continue
            if moebel_grenze is not None and sm2 > moebel_grenze + .5:
                continue
            if ziel is not None and nz >= ziel:
                continue                                  # Ziel schon erreicht: keine weitere Etage
            yield from kombis(j + 1, gew + [(f, k)], sb2, sm2, nz2)

    for gew, sb, sm, nz in kombis(0, [], 0.0, 0.0, 0):
        belegt = {z.id for f, _k in gew for z in f.zimmer}
        rest_b = None if budget_bau is None else budget_bau - sb
        rest_m = None if moebel_grenze is None else moebel_grenze - sm
        einzel, rest_b, _rm = _fuellen(kand, rest_b, rest_m, belegt, None if ziel is None else max(0, ziel - nz))
        if budget_bau is None and ziel is None:
            einzel = []                                   # ohne Grenze und ohne Ziel: nur Etagen
        liste = [(f, z, "etage") for f, _k in gew for z in f.zimmer] + [(f, z, "zimmer") for f, z in einzel]
        w_v = sum(_wert(f.bedarfe.get(z.id) or ZBedarf(), "etage") for f, z, _a in liste if f.haus == vorrang)
        w = sum(_wert(f.bedarfe.get(z.id) or ZBedarf(), "etage") for f, z, _a in liste)
        genutzt = (budget_bau - rest_b) if budget_bau is not None and rest_b is not None else sb
        # 0.46: Zimmer ohne Bedarf zählen nicht (außer beim Zimmerziel) – bei gleichem Bedarf die günstigere Lösung,
        # nie eine Etage nur zum Ausschöpfen des Budgets
        n = len(liste) if ziel is not None else sum(1 for f, z, _a in liste if _wert(f.bedarfe.get(z.id) or ZBedarf(), "etage") > 0)
        wert = (w_v, w, n, -genutzt)
        if best_wert is None or wert > best_wert:
            best, best_wert, best_rest = liste, wert, rest_b
    return best, best_rest


def _als_massnahmen(p, liste: list, jahr: int) -> list[Massnahme]:
    etagen: dict[str, Flur] = {}
    rest = []
    for f, z, art in liste:
        if art == "etage":
            etagen[f.schluessel] = f
        else:
            rest.append((f, z, art))
    return [_massnahme(p, f, f.zimmer, "etage", jahr) for f in etagen.values()] + _gruppieren(p, rest, jahr)


def machbare_etagen(stand: zp.Planstand, fl: list[Flur], jahr: int, heute: date, p: dict) -> set[str]:
    """Etagen mit mindestens einem Monat, in dem gebaut werden kann (nicht gesperrt, Vorlauf reicht, Ausweich für
    alle). Ohne Buchungen gilt ein Monat als machbar (nicht prüfbar)."""
    erg = set()
    for f in fl:
        for m in range(1, 13):
            fe = fenster(stand, f, date(jahr, m, 1), p)
            if not fe.gesperrt and fe.stopp_ab >= heute and not fe.ohne_ausweich:
                erg.add(f.schluessel)
                break
    return erg


def varianten(fl: list[Flur], p: dict, jahr: int, ziel: int | None = None, schon: set | None = None,
              machbar: set | None = None, reserve: set | None = None, budget_faktor: float = 1.0) -> tuple[list[Variante], str]:
    """Varianten des Jahres. Budget-Modus: Baubudget fest (Obergrenze – Rest bleibt frei, wenn kein Bedarf passt), Möbel als Antrag (optionale
    Obergrenze). Ziel-Modus: Zimmerziel. ``schon``: im Jahr vorgemerkte Zimmer; ``machbar``: Etagen mit machbarem
    Monat; ``reserve``: Reserve-Etagen (Kernbestand) – fallen heraus. Empfehlung = rechnerisch beste Variante."""
    budget = p.get("modus") != "ziel"
    bb = p.get("budget_bau") if budget else None
    bb = None if bb is None else bb * budget_faktor
    mg = p.get("moebel_obergrenze") if budget else None
    ziel = None if budget else int(ziel if ziel is not None else p.get("ziel_zimmer") or 0)
    schon, reserve = schon or set(), reserve or set()
    fl_ok = [f for f in fl if f.schluessel not in reserve]
    fl_etage = [f for f in fl_ok if not any(z.id in schon for z in f.zimmer)
                and (machbar is None or f.schluessel in machbar) and (not budget or f.wert > 0)]
    frei = {z.id for f in fl_ok for z in f.zimmer} - schon
    fl_z = [Flur(f.schluessel, f.haus, f.etage, f.flur, [z for z in f.zimmer if z.id in frei], bedarfe=f.bedarfe)
            for f in fl_ok]
    vorrang = p.get("haus_vorrang") or ""

    def mit_moebel_a(liste):
        belegt = {z.id for _f, z, _a in liste}
        return liste + _moebel_a(fl_z, belegt)

    a_liste, a_rest = optimieren(fl_etage, p, jahr, bb, mg, ziel, True, False, vorrang)
    b_liste, b_rest = optimieren(fl_etage, p, jahr, bb, mg, ziel, True, True, vorrang)
    b_liste = b_liste if b_liste else []
    # Einzelzimmer dürfen auch auf Etagen liegen, die selbst nicht machbar sind (kein Belegungsstopp nötig)
    if fl_z:
        extra, b_rest2, _m = _fuellen(_zimmer_kandidaten(fl_z, frei, p, jahr, "zimmer"),
                                      b_rest, None, {z.id for _f, z, _a in b_liste},
                                      None if ziel is None else max(0, ziel - len(b_liste)))
        if budget and bb is not None:
            b_liste += [(f, z, "zimmer") for f, z in extra]
            b_rest = b_rest2
    c_liste, c_rest = optimieren(fl_z, p, jahr, bb, mg, ziel, False, True, vorrang)
    d_kand = _zimmer_kandidaten(fl_z, frei, p, jahr, "moebel")
    d_wahl, _rb, _rm = _fuellen(d_kand, None, mg, set(), ziel if ziel is not None else None)
    a = Variante("etagen", "Nur ganze Etagen", "Ganze Etagen nach Bedarf – so, wie die Angebote gelten. Belegungsstopp "
                 "und Ausweich für die ganze Etage.", _als_massnahmen(p, a_liste, jahr), rest_bau=a_rest)
    b = Variante("kombi", "Beste Kombination", "Jede mögliche Etagenkombination im Baubudget, der Rest in die "
                 "bedürftigsten Einzelzimmer (Bedarf je €); dazu „nur Möbel“ für Zimmer mit Möbel-Klasse A.",
                 _als_massnahmen(p, mit_moebel_a(b_liste), jahr), rest_bau=b_rest)
    c = Variante("zimmer", "Nur Einzelzimmer", "Keine ganze Etage, sondern die bedürftigsten Zimmer einzeln – kein "
                 "Belegungsstopp für ganze Flure, dafür Termine je Zimmer (gebündelt in Kampagnen).",
                 _als_massnahmen(p, mit_moebel_a(c_liste), jahr), rest_bau=c_rest)
    d = Variante("moebel", "Nur Möbel tauschen", "Nur neue Möbel für Zimmer mit Möbel-Bedarf – braucht kein Baubudget. "
                 "Wände und Böden bleiben, wie sie sind.", _als_massnahmen(p, [(f, z, "moebel") for f, z in d_wahl], jahr),
                 rest_bau=bb)
    vs = [a, b, c, d]
    if not any(b_.wert_bau + b_.wert_moebel for f in fl for b_ in f.bedarfe.values()):
        for v in (b, c, d):
            v.hinweis = "Für einzelne Zimmer ist kein Bedarf erfasst (Mängel, Renovierungsdaten, Zustandsnote)."
    if budget and not any(f.wert > 0 for f in fl_ok):
        a.hinweis = "Für keine Etage ist Bedarf erfasst – Renovierungsdaten, Mängel oder Zustandsnoten pflegen."
    elif budget and bb is not None and not a.massnahmen:
        a.hinweis = "Mit diesem Baubudget passt keine ganze Etage mit Bedarf."
    kandidaten = [v for v in vs[:3] if v.massnahmen]
    empf = max(kandidaten, key=lambda v: (v.wert, v.zimmer, -(v.rest_bau or 0))).schluessel if kandidaten else (
        "moebel" if d.massnahmen else "")
    return vs, empf


def robustheit(fl: list[Flur], p: dict, jahr: int, empf: str, **kw) -> str:
    """Bleibt die Empfehlung, wenn alle Kosten 15 % höher bzw. niedriger sind? (= Budget ÷ 1,15 bzw. ÷ 0,85)"""
    vs, e = varianten(fl, p, jahr, budget_faktor=1, **kw)
    basis = {(m.art, m.flur.schluessel, len(m.zimmer)) for v in vs if v.schluessel == e for m in v.massnahmen}
    saetze = []
    for faktor, text in ((1 / 1.15, "15 % teurer"), (1 / 0.85, "15 % günstiger")):
        vs2, e2 = varianten(fl, p, jahr, budget_faktor=faktor, **kw)
        v2 = next((v for v in vs2 if v.schluessel == e2), None)
        andere = {(m.art, m.flur.schluessel, len(m.zimmer)) for m in (v2.massnahmen if v2 else [])}
        if e2 != e:
            saetze.append(f"wenn alles {text} ist, wäre „{v2.titel if v2 else '–'}“ vorn")
        elif {x for x in andere if x[0] == "etage"} != {x for x in basis if x[0] == "etage"}:
            saetze.append(f"wenn alles {text} ist, ändern sich die Etagen")
    if p.get("modus") == "ziel" or p.get("budget_bau") is None:
        return "Ohne Baubudget hängt die Auswahl nicht an den Preisen."
    return "Empfehlung stabil bei Kosten ±15 %." if not saetze else "Achtung: " + "; ".join(saetze) + "."


def moebelantrag(v: Variante | None) -> dict:
    """Was beantragt werden muss: Möbel für die Bau-Maßnahmen + „nur Möbel“ – mit Spanne."""
    if not v:
        return {"summe": 0.0, "bau_mass": 0.0, "nur_moebel": 0.0, "von": 0.0, "bis": 0.0}
    bm = sum(m.kosten.investition for m in v.massnahmen if m.art != "moebel")
    nm = sum(m.kosten.investition for m in v.massnahmen if m.art == "moebel")
    von = sum(m.kosten.spanne_von("moebel")[0] for m in v.massnahmen)
    bis = sum(m.kosten.spanne_von("moebel")[1] for m in v.massnahmen)
    return {"summe": bm + nm, "bau_mass": bm, "nur_moebel": nm, "von": von, "bis": bis}


def guenstigste(fl: list[Flur], p: dict, jahr: int) -> tuple[Flur, Kosten] | None:
    erg = [(f, kosten(p, f.haus, len(f.zimmer), jahr)) for f in fl]
    return min(erg, key=lambda x: x[1].instandhaltung) if erg else None


# ---- Strategien über mehrere Jahre (mit Alterung) ------------------------------------------------------

@dataclass
class Strategie:
    schluessel: str
    titel: str
    erklaerung: str
    jahre: list = field(default_factory=list)       # {jahr, text, zimmer, bau, moebel, summe, sperr, a_offen}
    bestand: int = 0
    a_start: int = 0
    zimmer_ids: set = field(default_factory=set)
    zusatz: str = ""

    @property
    def zimmer(self) -> int:
        return len(self.zimmer_ids)

    def summe(self, feld: str) -> float:
        return sum(j[feld] for j in self.jahre)

    @property
    def anteil(self) -> float:
        return 100 * self.zimmer / self.bestand if self.bestand else 0.0

    @property
    def je_jahr(self) -> float:
        return self.zimmer / len(self.jahre) if self.jahre else 0.0

    @property
    def zyklus(self) -> float | None:
        return round(self.bestand / self.je_jahr, 1) if self.je_jahr else None

    @property
    def a_ende(self) -> int:
        return self.jahre[-1]["a_offen"] if self.jahre else self.a_start

    @property
    def deutung(self) -> str:
        n = len(self.jahre)
        teile = [f"Klasse-A-Zimmer: heute {self.a_start}, nach {n} Jahren {self.a_ende}."]
        if self.zimmer:
            teile.append(f"{self.zimmer} von {self.bestand} Zimmern ({self.anteil:.0f} %) erneuert für "
                         f"{tsd(self.summe('summe'))} (Bau {tsd(self.summe('bau'))}, Möbel {tsd(self.summe('moebel'))}).")
            if self.zyklus:
                teile.append(f"Bei diesem Tempo ist jedes Zimmer etwa alle {self.zyklus:g} Jahre dran.")
        else:
            teile.append("Es wird nichts erneuert.")
        if self.zusatz:
            teile.append(self.zusatz)
        return " ".join(teile)


def _altern(fl: list[Flur], heute: date, p: dict, offen: dict, noten: dict) -> list[Flur]:
    """Bedarf neu einstufen, wie er in ``heute`` wäre (Zimmer werden älter, offene Mängel bleiben)."""
    from types import SimpleNamespace

    stand = SimpleNamespace(zimmer=[z for f in fl for z in f.zimmer], lage=SimpleNamespace(unbewohnbar=set()))
    return flure(stand, heute, p, offen, noten)


def strategien(fl: list[Flur], p: dict, start_jahr: int, heute: date, jahre: int = 5, reserve: set | None = None,
               kern_text: str = "") -> list[Strategie]:
    """Nichtstun · Empfohlen · Kürzung −20 % · Beschleunigt (+50 %) · Kernbestand. Jahr für Jahr: Bedarf altert,
    erneuerte Zimmer zählen als frisch (kein Bau-Bedarf mehr, kein A)."""
    from belegung import maengel as mg

    offen = mg.offen_je_zimmer()
    noten = zustandsnoten()
    bestand_ = bestand(fl)
    a0 = a_zimmer(fl)

    def lauf(schl, titel, erkl, faktor: float | None, res: set | None = None, zusatz: str = "") -> Strategie:
        s = Strategie(schl, titel, erkl, bestand=bestand_ - sum(len(f.zimmer) for f in fl if f.schluessel in (res or set())),
                      a_start=a0, zusatz=zusatz)
        for i, j in enumerate(range(start_jahr, start_jahr + jahre)):
            stichtag = date(j, 1, 1) if j > heute.year else heute
            fl_j = _altern(fl, stichtag, p, offen, noten)
            for f in fl_j:                                   # erneuerte Zimmer: frisch
                for zid in list(f.bedarfe):
                    if zid in s.zimmer_ids:
                        f.bedarfe[zid] = ZBedarf(frisch=True)
            massnahmen = []
            if faktor is not None:
                pj = dict(p)
                if pj.get("modus") == "ziel":
                    pj["ziel_zimmer"] = round(int(p.get("ziel_zimmer") or 0) * faktor)
                vs, e = varianten(fl_j, pj, j, schon=set(s.zimmer_ids), reserve=res, budget_faktor=faktor)
                massnahmen = next((v.massnahmen for v in vs if v.schluessel == e), [])
            neu_ids = {z.id for m in massnahmen for z in m.zimmer} - s.zimmer_ids
            s.zimmer_ids |= neu_ids
            k = Kosten(0, j, herkunft_bau="", herkunft_moebel="")
            for m in massnahmen:
                k = k.plus(m.kosten)
            a_offen = sum(1 for f in fl_j for zid, b in f.bedarfe.items() if b.a and zid not in s.zimmer_ids)
            s.jahre.append({"jahr": j, "text": "; ".join(m.text for m in massnahmen) or "nichts", "zimmer": len(neu_ids),
                            "bau": k.instandhaltung, "moebel": k.investition, "summe": k.summe,
                            "sperr": Variante("", "", "", massnahmen).sperr_zimmermonate(p), "a_offen": a_offen})
        return s

    erg = [lauf("nichts", "Nichtstun", "Keine Renovierung – zeigt, wie der Bedarf mit dem Alter der Zimmer wächst.", None),
           lauf("empfohlen", "Empfohlen", "Jedes Jahr die rechnerisch beste Variante mit dem eingestellten Budget bzw. Ziel.", 1.0),
           lauf("kuerzung", "Kürzung −20 %", "Wie „Empfohlen“, aber mit 20 % weniger Budget bzw. Zimmerziel.", .8),
           lauf("schneller", "Beschleunigt +50 %", "Wie „Empfohlen“, aber mit 50 % mehr Budget bzw. Zimmerziel.", 1.5)]
    if reserve:
        erg.append(lauf("kern", "Kernbestand", "Wie „Empfohlen“, aber Reserve-Etagen werden nicht renoviert, nur in "
                        "Betrieb gehalten.", 1.0, reserve, kern_text))
    return erg


# ---- Termine für Einzelzimmer: Kampagnen ----------------------------------------------------------------

def _frei_ab(stand: zp.Planstand, z, d: date, tage: int) -> bool:
    return stand.lage.freie_betten(z.id, d, d + timedelta(days=tage - 1)) >= z.betten


def kampagnen(stand: zp.Planstand, zimmer: list, ab: date, bis: date, tage: int, gesperrt: list,
              hoechstens: int = 2) -> tuple[list[tuple], list]:
    """Einzelzimmer gebündelt: je Kampagne der Wochenbeginn, an dem die meisten Zimmer gleichzeitig leer sind.
    Höchstens ``hoechstens`` Kampagnen; was übrig bleibt, einzeln im ersten Leerstand. → ([(Zimmer, von, bis)], ohne)."""
    offen = list(zimmer)
    erg = []
    starts = []
    d = ab + timedelta(days=(7 - ab.weekday()) % 7)
    while d + timedelta(days=tage - 1) <= bis:
        if d.month not in gesperrt:
            starts.append(d)
        d += timedelta(days=7)
    for _k in range(hoechstens):
        if not offen or not starts:
            break
        best = max(starts, key=lambda s: (sum(1 for z in offen if _frei_ab(stand, z, s, tage)), -s.toordinal()))
        drin = [z for z in offen if _frei_ab(stand, z, best, tage)]
        if not drin:
            break
        erg += [(z, best, best + timedelta(days=tage - 1)) for z in drin]
        offen = [z for z in offen if z not in drin]
    ohne = []
    for z in offen:
        d = ab
        while d + timedelta(days=tage - 1) <= bis and not (d.month not in gesperrt and _frei_ab(stand, z, d, tage)):
            d += timedelta(days=1)
        if d + timedelta(days=tage - 1) <= bis:
            erg.append((z, d, d + timedelta(days=tage - 1)))
        else:
            ohne.append(z)
    return erg, ohne


@dataclass
class Vorschlag:
    flur: Flur
    fenster: Fenster | None
    art: str = "etage"
    teile: list = field(default_factory=list)       # Einzelzimmer: (Zimmer, von, bis)
    ohne_fenster: list = field(default_factory=list)


def vorschlaege_variante(stand: zp.Planstand, fl: list[Flur], jahr: int, heute: date, p: dict, prognose: dict | None,
                         v: Variante | None, kap: float | None = None) -> list[Vorschlag]:
    """Etagen: bester Monat. Einzelzimmer: Kampagnen je Haus und Art, frühestens nach Bestellung + Möbel-Lieferzeit."""
    if v is None:
        return []
    etagen = [m.flur for m in v.massnahmen if m.art == "etage"]
    erg = vorschlaege(stand, fl, jahr, heute, p, prognose, Auswahl("", etagen, 0, Kosten(0, jahr)), kap) if etagen else []
    ab = max(date(jahr, 1, 1), heute + timedelta(days=int(p.get("lieferzeit_tage") or 28) + 14))
    je_haus: dict[tuple, list] = {}
    for m in v.massnahmen:
        if m.art != "etage":
            je_haus.setdefault((m.flur.haus, m.art), []).append(m)
    for (_haus, art), ms in je_haus.items():
        tage = int(p.get("zimmer_tage") or 14) if art == "zimmer" else int(p.get("moebel_tage") or 3)
        alle = [z for m in ms for z in m.zimmer]
        teile, ohne = kampagnen(stand, alle, ab, date(jahr, 12, 31), tage, p.get("gesperrt") or [])
        nach_flur = {z.id: m.flur for m in ms for z in m.zimmer}
        for m in ms:
            vs = Vorschlag(m.flur, None, art, [t for t in teile if nach_flur[t[0].id] is m.flur],
                           [z for z in ohne if nach_flur[z.id] is m.flur])
            erg.append(vs)
    return erg


def vorschlaege(stand: zp.Planstand, fl: list[Flur], jahr: int, heute: date, p: dict | None = None,
                prognose: dict | None = None, auswahl: Auswahl | None = None, kap: float | None = None) -> list[Vorschlag]:
    """Für die Etagen der Ziel-Auswahl (ohne schon vorgemerkte) je den besten Monat – keine zwei Baustellen im
    selben Monat (die Ausweichzimmer würden doppelt gezählt)."""
    p = p or parameter()
    schon = {e["flur"] for e in plan() if e["start"][:4] == str(jahr) and e["art"] == "etage"}
    belegt_monate = {date.fromisoformat(e["start"]).month for e in plan() if e["start"][:4] == str(jahr) and e["art"] == "etage"}
    auswahl = auswahl or (ziel_auswahl(fl, p, jahr) or [None])[-1]
    erg = []
    bau = jahresplan(stand, jahr, None, p) if kap else []          # schon vorgemerkte Baustellen senken die Kapazität
    for f in (auswahl.flure if auswahl else []):
        if f.schluessel in schon:
            continue
        fs = [x for x in monatsfenster(stand, f, jahr, p, prognose) if x.start.month not in belegt_monate]
        engpass_markieren(fs, f, kap, bau)
        best = bester_monat(fs, heute)
        if best:
            belegt_monate.add(best.start.month)
            bau.append(PlanZeile(f.schluessel, f.text, len(f.zimmer), f.betten, best.start, best.ende, best.stopp_ab,
                                 "vorschlag", Kosten(len(f.zimmer), jahr)))
        erg.append(Vorschlag(f, best))
    return erg


# ---- Jahresplan (Gantt) und Kapazität ---------------------------------------------------------------

@dataclass
class PlanZeile:
    flur: str                     # Schlüssel
    text: str
    zimmer: int
    betten: int
    start: date
    ende: date
    stopp_ab: date
    status: str                   # vorgemerkt | vorschlag
    kosten: Kosten
    gleichwertig: bool = False
    ohne_ausweich: int = 0
    engpass: bool = False
    art: str = "etage"
    teile: list = field(default_factory=list)      # Einzelzimmer: (Zimmer-ID, kurz, von, bis, Betten)
    pruefbar: bool = True

    @property
    def titel(self) -> str:
        return self.text if self.art == "etage" else f"{self.text} – {self.zimmer} Zi. {ARTEN[self.art]}"


def jahresplan(stand: zp.Planstand, jahr: int, vorschl: list[Vorschlag] | None = None,
               p: dict | None = None) -> list[PlanZeile]:
    """Zeilen für das Gantt: vorgemerkte Etagen (fest) und Vorschläge (gestrichelt)."""
    p = p or parameter()
    nach_schl: dict[str, list] = {}
    for z in stand.zimmer:
        nach_schl.setdefault(schluessel(z.haus, z.etage, ""), []).append(z)
    erg = []
    nach_id = {z.id: z for z in stand.zimmer}
    gruppen: dict[tuple, list] = {}
    for e in plan():
        s, en = date.fromisoformat(e["start"]), date.fromisoformat(e["ende"])
        if not (s.year <= jahr <= en.year):
            continue
        zs = nach_schl.get(e["flur"], [])
        if e["art"] != "etage":
            gruppen.setdefault((e["flur"], e["art"], "vorgemerkt"), []).extend(
                (zid, nach_id[zid].kurz, s, en, nach_id[zid].betten) for zid in e["zimmer"] if zid in nach_id)
            continue
        erg.append(PlanZeile(e["flur"], flur_text_schluessel(e["flur"]), len(zs), sum(z.betten for z in zs), s, en,
                             s - timedelta(days=int(p["vorlauf_tage"])), "vorgemerkt",
                             kosten(p, e["flur"].split("|")[0], len(zs), s.year)))
    for v in vorschl or []:
        if v.art != "etage":
            if v.teile:
                gruppen.setdefault((v.flur.schluessel, v.art, "vorschlag"), []).extend(
                    (z.id, z.kurz, a, b, z.betten) for z, a, b in v.teile)
            continue
        if v.fenster is None:
            continue
        fe, f = v.fenster, v.flur
        erg.append(PlanZeile(f.schluessel, f.text, len(f.zimmer), f.betten, fe.start, fe.ende, fe.stopp_ab, "vorschlag",
                             kosten(p, f.haus, len(f.zimmer), jahr), fe.gleichwertig, len(fe.ohne_ausweich),
                             fe.engpass, pruefbar=fe.pruefbar))
    for (schl, art, status), teile in gruppen.items():
        n = len(teile)
        start, ende = min(t[2] for t in teile), max(t[3] for t in teile)
        erg.append(PlanZeile(schl, flur_text_schluessel(schl), n, sum(t[4] for t in teile), start, ende, start, status,
                             kosten(p, schl.split("|")[0], n, start.year, art, len(nach_schl.get(schl, [])) or n),
                             art=art, teile=sorted(teile, key=lambda t: t[2])))
    return sorted(erg, key=lambda z: (z.art != "etage", z.start, z.text))


def jahresuebersicht(stand: zp.Planstand, jahr: int, p: dict | None = None) -> list[dict]:
    """Je Monat: vorgemerkte Flure, Zimmer, Betten, Kosten (im Startmonat)."""
    p = p or parameter()
    monate = [{"monat": m, "flure": [], "zimmer": 0, "betten": 0, "kosten": 0.0} for m in range(1, 13)]
    for z in jahresplan(stand, jahr, None, p):
        for mo in monate:
            m0 = date(jahr, mo["monat"], 1)
            m1 = date(jahr + (mo["monat"] == 12), mo["monat"] % 12 + 1, 1) - timedelta(days=1)
            if z.start <= m1 and z.ende >= m0:
                mo["flure"].append(z.text)
                mo["zimmer"] += z.zimmer
                mo["betten"] += z.betten
                if z.start.year == jahr and z.start.month == mo["monat"]:
                    mo["kosten"] += z.kosten.summe
    return monate


def gesperrte_betten(zeilen: list[PlanZeile], monat: date) -> float:
    """Betten, die im Monat (anteilig nach Tagen) wegen Bauarbeiten fehlen – für die Kapazitätslinie."""
    m1 = date(monat.year + (monat.month == 12), monat.month % 12 + 1, 1) - timedelta(days=1)
    tage = (m1 - monat).days + 1
    summe = 0.0
    for z in zeilen:
        for von, bis, betten in ([(t[2], t[3], t[4]) for t in z.teile] if z.teile else [(z.start, z.ende, z.betten)]):
            a, b = max(von, monat), min(bis, m1)
            if a <= b:
                summe += betten * ((b - a).days + 1) / tage
    return round(summe, 1)


def excel(stand: zp.Planstand, jahr: int, pfad, zeilen: list[PlanZeile] | None = None) -> int:
    import openpyxl
    from openpyxl.styles import Font

    p = parameter()
    zeilen = zeilen if zeilen is not None else jahresplan(stand, jahr, None, p)
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = f"Plan {jahr}"
    ws.append([f"Renovierungsplan {jahr} (unverbindlich)"])
    ws["A1"].font = Font(bold=True, size=13)
    ws.append([f"Kosten: Preisstand {p['preisstand']}, +{p['preis_pct']} % je Jahr, Nebenkosten {p['neben_pct']} %, "
               f"Puffer {p['puffer_pct']} %, Vorsteuerquote {p['vorsteuer_pct']} %"])
    ws.append([])
    kopf = ["Maßnahme", "Status", "Belegungsstopp ab", "Bau von", "Bau bis", "Zimmer", "Betten", "Bau + Neben (€)",
            "Möbel + Aufbau (€)", "Gesamt (€)", "netto (€)"]
    ws.append(kopf)
    for c in ws[4]:
        c.font = Font(bold=True)
    for z in zeilen:
        ws.append([z.titel + (": " + ", ".join(t[1] for t in z.teile) if z.teile else ""), z.status,
                   z.stopp_ab if z.art == "etage" else None, z.start, z.ende, z.zimmer, z.betten, round(z.kosten.instandhaltung),
                   round(z.kosten.investition), round(z.kosten.summe), round(z.kosten.netto)])
        for sp in (3, 4, 5):
            ws.cell(ws.max_row, sp).number_format = "DD.MM.YYYY"
    ws.append(["Summe", "", "", "", "", sum(z.zimmer for z in zeilen), sum(z.betten for z in zeilen),
               round(sum(z.kosten.instandhaltung for z in zeilen)), round(sum(z.kosten.investition for z in zeilen)),
               round(sum(z.kosten.summe for z in zeilen)), round(sum(z.kosten.netto for z in zeilen))])
    for spalte, breite in zip("ABCDEFGHIJK", (22, 12, 16, 12, 12, 8, 8, 16, 18, 14, 14)):
        ws.column_dimensions[spalte].width = breite
    pfad.parent.mkdir(parents=True, exist_ok=True)
    wb.save(pfad)
    return len(zeilen)


# ---- Mit Rückgängig (für die Oberfläche) ---------------------------------------------------------

def vormerken_schritt(flur: str, start: date, ende: date) -> str:
    from .kern import _schritt

    erg = []
    _schritt(f"Renovierung vorgemerkt: {flur_text_schluessel(flur)}", lambda: erg.append(vormerken(flur, start, ende)), [DATEI])
    return erg[0]


def vormerken_mehrere_schritt(eintraege: list) -> str:
    """Mehrere Vorschläge auf einmal übernehmen – ein Schritt, ein Rückgängig. Einträge: (Flur, Start, Ende) oder
    (Flur, Start, Ende, Art, [Zimmer-IDs])."""
    from .kern import _schritt

    def tun():
        for e in eintraege:
            flur, start, ende, *rest = e
            vormerken(flur, start, ende, "", *(rest[:1] or ["etage"]), *(rest[1:2] or [None]))
    _schritt(f"Renovierung: {len(eintraege)} Vorschläge übernommen", tun, [DATEI])
    return f"{len(eintraege)} Maßnahme{'n' if len(eintraege) != 1 else ''} vorgemerkt (unverbindlich)"


def zustand_schritt(noten: dict) -> str:
    from .kern import _schritt

    erg = []
    _schritt("Zustandsnoten der Etagen", lambda: erg.append(zustandsnoten_speichern(noten)), [DATEI])
    return erg[0]


def entfernen_schritt(flur: str, start: str, art: str | None = None) -> str:
    from .kern import _schritt

    erg = []
    _schritt(f"Vormerkung entfernt: {flur_text_schluessel(flur)}", lambda: erg.append(entfernen(flur, start, art)), [DATEI])
    return erg[0]


def entfernen_mehrere_schritt(eintraege: list[tuple[str, str, str]]) -> str:
    """(Flur, Start ISO, Art) – z. B. alle Einzelzimmer einer Gruppe, ein Rückgängig."""
    from .kern import _schritt

    def tun():
        for flur, start, art in eintraege:
            entfernen(flur, start, art)
    _schritt(f"Renovierung: {len(eintraege)} Vormerkungen entfernt", tun, [DATEI])
    return f"{len(eintraege)} Vormerkung{'en' if len(eintraege) != 1 else ''} entfernt"


def parameter_schritt(p: dict) -> str:
    from .kern import _schritt

    erg = []
    p = herkunft_merken(parameter(), p)
    _schritt("Renovierung: Planungsannahmen", lambda: erg.append(parameter_speichern(p)), [DATEI])
    return erg[0]


def excel_speichern(stand: zp.Planstand, jahr: int) -> tuple[str, object]:
    from pathlib import Path

    ziel = Path(speicher.einstellungen().get("export_ordner") or speicher.pfad("Exporte"))
    pfad = ziel / f"Renovierungsplan_{jahr}.xlsx"
    excel(stand, jahr, pfad)
    return "Renovierungsplan gespeichert", pfad
