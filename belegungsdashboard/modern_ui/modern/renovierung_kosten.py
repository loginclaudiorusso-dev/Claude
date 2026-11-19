"""1.29: Renovierung – Kosten, Unsicherheit, Einheitspreise und Angebote einlesen. Rein, ohne Oberfläche.

Aus renovierung_kern.py ausgelagert (nur verschoben, keine Funktionsänderung); dort weiter erreichbar."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date

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
UNSICHER = {"angebot": .10, "eingabe": .15, "schaetzung": .25, "platzhalter": .40}
# 1.14: Kostenspannen hängen zusammen (gleicher Rahmenvertrag, gleiche Preissteigerung, oft dieselbe Firma). Ein Teil
# ρ der Unsicherheit wirkt gemeinsam (addiert sich), der Rest ist unabhängig (addiert sich quadratisch):
#   Spanne² = (Σ ρ·uᵢ)² + Σ (1 − ρ²)·uᵢ²       – für eine einzelne Position bleibt es genau uᵢ.
# Einfaches Addieren (bis 1.13) machte die Gesamtspanne zu breit, rein quadratisch wäre sie zu schmal.
KOSTEN_GEMEINSAM = 0.5
HERKUNFT_TEXT = {"angebot": "Angebot", "eingabe": "Eingabe", "schaetzung": "Schätzung", "platzhalter": "Platzhalter"}


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
    u_bau: float = 0.0            # Unsicherheit (± €) des Bau-Teils – ab 1.14 aus uc/vi zusammengesetzt
    u_moebel: float = 0.0
    ungewiss: float = 0.0         # Betrag, der nicht aus einem Angebot stammt
    uc_bau: float = 0.0           # 1.14: gemeinsamer Teil der Unsicherheit (addiert sich)
    uc_moebel: float = 0.0
    vi_bau: float = 0.0           # 1.14: unabhängiger Teil als Varianz (addiert sich quadratisch)
    vi_moebel: float = 0.0

    def _unsicherheit(self) -> "Kosten":
        self.u_bau = self.instandhaltung * UNSICHER.get(self.herkunft_bau, .4)
        self.u_moebel = self.investition * UNSICHER.get(self.herkunft_moebel, .4)
        r = KOSTEN_GEMEINSAM
        self.uc_bau, self.vi_bau = r * self.u_bau, (1 - r * r) * self.u_bau ** 2
        self.uc_moebel, self.vi_moebel = r * self.u_moebel, (1 - r * r) * self.u_moebel ** 2
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
        """(von, bis) – Unsicherheit nach Herkunft der Werte (Angebot ±10 % … Platzhalter ±40 %); Bau und Möbel
        zusammen wie mehrere Positionen (gemeinsamer Teil + unabhängiger Rest, 1.14)."""
        d = gesamt_unsicherheit(self.uc_bau + self.uc_moebel, self.vi_bau + self.vi_moebel,
                                self.u_bau + self.u_moebel)
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
                      gesamt_unsicherheit(self.uc_bau + o.uc_bau, self.vi_bau + o.vi_bau, self.u_bau + o.u_bau),
                      gesamt_unsicherheit(self.uc_moebel + o.uc_moebel, self.vi_moebel + o.vi_moebel,
                                          self.u_moebel + o.u_moebel),
                      self.ungewiss + o.ungewiss, self.uc_bau + o.uc_bau, self.uc_moebel + o.uc_moebel,
                      self.vi_bau + o.vi_bau, self.vi_moebel + o.vi_moebel)


def gesamt_unsicherheit(gemeinsam: float, varianz: float, linear: float = 0.0) -> float:
    """1.14: ± € aus gemeinsamem Teil und unabhängiger Varianz. Ohne Aufteilung (alte Objekte): die lineare Summe."""
    if gemeinsam == 0 and varianz == 0:
        return linear
    return (gemeinsam * gemeinsam + varianz) ** 0.5


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
    if not ang.get("gueltig_bis") and str(ang.get("datum") or "")[:4].isdigit():
        ang = {**ang, "gueltig_bis": f"{str(ang['datum'])[:4]}-12-31"}         # 0.48: Angebote gelten meist im laufenden Jahr
        neu["angebote"][-1]["gueltig_bis"] = ang["gueltig_bis"]
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
