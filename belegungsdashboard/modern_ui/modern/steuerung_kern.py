"""Steuerung (für die Leitung, selten genutzt): Übersicht, Prognose kurz, Renovierung, Szenarien, Kennzahlen.

Wird erst gerechnet, wenn die Seite geöffnet wird – der Tagesbetrieb bleibt davon unberührt. Rein, ohne NiceGUI.

* **Prognosegüte ehrlich:** Die Spanne der Prognose stammt aus denselben Rückblick-Fehlern, an denen sie gemessen wird
  – die „Trefferquote“ ist deshalb kein Test. Hier werden die Rückblick-Monate geteilt: Die älteren bestimmen die
  Spanne, die jüngsten (``HOLDOUT``) prüfen sie. Für die Leitung ein Satz in Plätzen: „lag im Schnitt ±X daneben“.
* **Buchungsstände:** Einmal im Monat wird festgehalten, was für die kommenden Monate schon gebucht ist. Daraus lässt
  sich später ablesen, wie viel erfahrungsgemäß noch dazukommt (Pickup) – heute gibt es diese Geschichte noch nicht.
* **Kennzahlen** nur aus vorhandenen Daten: verfügbare Kapazität (ohne defekte und Baustellen-Zimmer), Belegtage je
  Gruppe, Ausfalltage durch Defekte, Alter seit Renovierung, Anteil im Zyklus. Was Daten bräuchte, die es nicht gibt
  (Erlöse, Leerstandskosten, Abweisungen), steht als Lücke da.
"""

from __future__ import annotations

import math

from dataclasses import dataclass, field
from datetime import date, timedelta

from belegung import speicher

HOLDOUT = 6
STAENDE = f"{speicher.IMPORT_ORDNER}/modern_buchungsstaende.json"


# ---- Prognose ---------------------------------------------------------------------------------

def prognose_monate(pg) -> dict:
    """{(Jahr, Monat): (erwartet, lo80, hi80)} der Prognosemonate."""
    if not pg:
        return {}
    return {(z.monat.year, z.monat.month): (z.erwartet, z.lo80, z.hi80) for z in pg.zeilen if z.art != "ist"}


@dataclass
class Guete:
    n: int                         # Rückblick-Monate gesamt
    mae: float | None              # Ø Abweichung (Plätze)
    k80: float | None              # Spanne aus den älteren Monaten (± Plätze, 80 % der Fehler darunter)
    test_n: int = 0
    test_treffer: int = 0          # jüngste Monate innerhalb ±k80
    satz: str = ""
    hinweis: str = ""

    @property
    def test_quote(self) -> float | None:
        return self.test_treffer / self.test_n if self.test_n else None


def guete(pg, holdout: int = HOLDOUT) -> Guete:
    """Rückblick (Monat, Ist, Blind-Prognose) aufteilen: ältere Monate → Spanne, jüngste → unabhängige Prüfung."""
    rueck = sorted(getattr(pg, "rueckblick", None) or [])
    fehler = [abs(ist - pr) for _m, ist, pr in rueck]
    if not fehler:
        return Guete(0, None, None, satz="Für diese Prognose gibt es noch keinen Rückblick – ihre Güte ist unbekannt.")
    mae = sum(fehler) / len(fehler)
    satz = f"Die Prognose lag in den letzten {len(fehler)} Monaten im Schnitt um ±{mae:.0f} Plätze daneben."
    if len(fehler) < holdout + 6:
        return Guete(len(fehler), mae, None, satz=satz,
                     hinweis=f"Für eine unabhängige Prüfung der Spanne sind {holdout + 6} Rückblick-Monate nötig.")
    alt, neu = fehler[:-holdout], fehler[-holdout:]
    s = sorted(alt)
    k80 = s[min(len(s) - 1, int(round(0.8 * (len(s) - 1))))]
    treffer = sum(1 for e in neu if e <= k80)
    hinweis = (f"Unabhängige Prüfung: Die Spanne ±{k80:.0f} (aus den {len(alt)} älteren Monaten) traf in {treffer} von "
               f"{holdout} jüngsten Monaten. Bei nur {holdout} Prüfmonaten ist das ein grober Hinweis, kein Beweis.")
    return Guete(len(fehler), mae, k80, holdout, treffer, satz, hinweis)


def buchungsstand_merken(pg, heute: date | None = None) -> bool:
    """Einmal je Monat: was für die kommenden Monate schon gebucht (gesichert) ist – Grundlage für ein späteres
    Pickup-Modell. Liegt im Goslar-Ordner (wie die Prognose)."""
    from .standort_kern import haupt

    heute = heute or date.today()
    if not pg:
        return False
    schl = f"{heute:%Y-%m}"
    with haupt():
        alle = speicher.lesen(STAENDE, {})
        if schl in alle:
            return False
        alle[schl] = {"stichtag": heute.isoformat(),
                      "monate": {f"{z.monat:%Y-%m}": round(z.gesichert, 1) for z in pg.zeilen
                                 if z.art != "ist" and z.gesichert is not None}}
        speicher.schreiben(STAENDE, alle)
    return True


def buchungsstaende() -> dict:
    from .standort_kern import haupt

    with haupt():
        return speicher.lesen(STAENDE, {})


@dataclass
class Linie:
    """Für das Strategie-Diagramm: Ist, Prognose mit Spanne, Vorjahre, Kapazität mit Baustellen."""
    monate: list = field(default_factory=list)        # date
    ist: list = field(default_factory=list)
    prognose: list = field(default_factory=list)
    lo80: list = field(default_factory=list)
    hi80: list = field(default_factory=list)
    vorjahr: list = field(default_factory=list)       # gleicher Monat ein Jahr früher (Ist)
    vorvorjahr: list = field(default_factory=list)
    kapazitaet: list = field(default_factory=list)    # Kapazität minus Baustellen-Betten
    kap_voll: int = 0
    warnschwelle: float | None = None


def linie(pg, plan_zeilen: list, zurueck: int = 12, vor: int = 12, warn_anteil: float = .95) -> Linie:
    from . import renovierung_kern as rk

    erg = Linie()
    if not pg:
        return erg
    ist_je = {(z.monat.year, z.monat.month): z.ist for z in pg.zeilen if z.art == "ist" and z.ist is not None}
    ist_zeilen = [z for z in pg.zeilen if z.art == "ist"]
    prog = [z for z in pg.zeilen if z.art != "ist"]
    auswahl = ist_zeilen[-zurueck:] + prog[:vor]
    erg.kap_voll = int(pg.kapazitaet or 0)
    erg.warnschwelle = round(erg.kap_voll * warn_anteil, 1) if erg.kap_voll else None
    for z in auswahl:
        erg.monate.append(z.monat)
        erg.ist.append(round(z.ist, 1) if z.art == "ist" and z.ist is not None else None)
        p_ = z.art != "ist"
        erg.prognose.append(round(z.erwartet, 1) if p_ else None)
        erg.lo80.append(round(z.lo80, 1) if p_ else None)
        erg.hi80.append(round(z.hi80, 1) if p_ else None)
        erg.vorjahr.append(ist_je.get((z.monat.year - 1, z.monat.month)))
        erg.vorvorjahr.append(ist_je.get((z.monat.year - 2, z.monat.month)))
        erg.kapazitaet.append(round(erg.kap_voll - rk.gesperrte_betten(plan_zeilen, z.monat), 1) if erg.kap_voll else None)
    if prog and ist_zeilen and erg.ist:            # Prognose an den letzten Ist-Monat anschließen
        i = len(ist_zeilen[-zurueck:]) - 1
        if 0 <= i < len(erg.prognose):
            erg.prognose[i] = erg.ist[i]
    return erg


def warnmonate(li: Linie) -> list[date]:
    """Prognosemonate, in denen die obere Spanne die (um Baustellen verringerte) Warnschwelle erreicht."""
    erg = []
    for m, hi, kap in zip(li.monate, li.hi80, li.kapazitaet):
        if hi is not None and kap and li.kap_voll and hi >= kap * (li.warnschwelle / li.kap_voll):
            erg.append(m)
    return erg


# ---- Kennzahlen -------------------------------------------------------------------------------

@dataclass
class Kennzahl:
    titel: str
    wert: str
    unter: str = ""
    stufe: str = ""                # ok | warn | krit | ""
    quelle: str = ""               # woher (für die Nachvollziehbarkeit)


WERTE = f"{speicher.IMPORT_ORDNER}/modern_steuerung.json"
GRUPPEN = ("Reha", "RVL", "RVT", "ASS", "EMR", "UWT", "Mieter", "Gast")


def werte() -> dict:
    """Eigene Eingaben für die Kennzahlen: Tagessätze je Gruppe (€ je Belegtag), Abweisungen je Monat."""
    roh = speicher.lesen(WERTE, {})
    return {"tagessaetze": {g: float(v) for g, v in (roh.get("tagessaetze") or {}).items() if v},
            "abweisungen": {m: int(v) for m, v in (roh.get("abweisungen") or {}).items() if v is not None}}


def werte_speichern(w: dict) -> str:
    speicher.schreiben(WERTE, {"tagessaetze": {g: float(v) for g, v in (w.get("tagessaetze") or {}).items() if v},
                               "abweisungen": {m: int(v) for m, v in (w.get("abweisungen") or {}).items() if v}})
    return "Werte für die Kennzahlen gespeichert"


def werte_schritt(w: dict) -> str:
    from .kern import _schritt

    erg = []
    _schritt("Steuerung: Werte für Kennzahlen", lambda: erg.append(werte_speichern(w)), [WERTE])
    return erg[0]


@dataclass
class Kern:
    """Kernbestand (wird renoviert) und Reserve (wird nur in Betrieb gehalten) – Grundlage, keine Entscheidung."""
    gesamt: int = 0               # Betten aller aktiven Zimmer am Standort
    spitze: float = 0.0           # höchste obere Prognose (Plätze) der nächsten 36 Monate
    ausfall: float = 0.0          # Ø Betten außer Betrieb durch Defekte
    typ: float = 0.0              # Reserve für Zimmertypen
    puffer: float = 0.0
    kern: int = 0
    reserve: int = 0
    etagen: list = field(default_factory=list)       # vorgeschlagene Reserve-Etagen (Flur-Objekte)
    reserve_betten: int = 0       # Betten in den vorgeschlagenen Reserve-Etagen
    fehlend_plus10: int = 0       # fehlende Betten bei +10 % Nachfrage, wenn die Reserve stillgelegt ist
    hinweis: str = ""

    @property
    def text(self) -> str:
        if not self.gesamt:
            return "Kein Kernbestand berechenbar."
        return (f"Kernbestand {self.kern} von {self.gesamt} Betten (Spitze {self.spitze:.0f} + Ausfall {self.ausfall:.0f} + "
                f"Typen {self.typ:.0f} + Puffer {self.puffer:.0f}); strukturelle Reserve {self.reserve} Betten "
                f"({100 * self.reserve / self.gesamt:.0f} %).")


def kernbestand(stand, pg, fl: list, p: dict, heute: date) -> Kern:
    """Kern = Spitzenbedarf (obere Prognose, höchster Monat, max. 36 Monate) + Ausfall (Ø defekte Betten der letzten
    12 Monate) + Typen-Reserve + Puffer. Reserve = Rest. Vorschlag Reserve-Etagen: ganze Etagen (Haus 2/6) mit den
    höchsten Kosten je Zimmer, ohne EMR-/Gäste-/Kurzmaßnahmen-Etagen, solange sie in die Reserve passen."""
    from belegung import maengel as mg

    from . import renovierung_kern as rk

    k = Kern()
    aktiv = [z for z in stand.zimmer if z.aktiv and not z.gaeste]
    k.gesamt = sum(z.betten for z in aktiv)
    prog = [z.hi80 for z in (pg.zeilen if pg else []) if z.art != "ist"][:36]
    if not prog or not k.gesamt:
        k.hinweis = "Ohne Prognose (Pivot) lässt sich kein Kernbestand rechnen."
        return k
    k.spitze = max(prog)
    von = heute - timedelta(days=365)
    tage = 0
    for m in mg.laden():
        if mg.stufe([m]) < 3:
            continue
        a, e = max(m.seit, von), min(m.behoben or heute, heute)
        if a <= e:
            tage += (e - a).days + 1
    k.ausfall = max(tage / 365, len(stand.lage.unbewohnbar) * 1.0)
    k.typ = k.spitze * float(p.get("typ_reserve_pct") or 0) / 100
    k.puffer = k.spitze * float(p.get("kern_puffer_pct") or 0) / 100
    k.kern = min(k.gesamt, math.ceil(k.spitze + k.ausfall + k.typ + k.puffer))
    k.reserve = k.gesamt - k.kern
    jahr = heute.year + 1
    kand = sorted([f for f in fl if not f.sonderzimmer],
                  key=lambda f: (-rk.kosten(p, f.haus, len(f.zimmer), jahr).je_zimmer, -f.bedarf))
    rest = k.reserve
    for f in kand:
        if f.betten <= rest:
            k.etagen.append(f)
            rest -= f.betten
    k.reserve_betten = sum(f.betten for f in k.etagen)
    k.fehlend_plus10 = max(0, math.ceil(k.spitze * 1.1 + k.ausfall) - (k.gesamt - k.reserve_betten))
    if k.reserve <= 0:
        k.hinweis = "Keine strukturelle Reserve – der ganze Bestand wird gebraucht."
    return k


def kennzahlen(stand, heute: date, fl: list, plan_zeilen: list, p: dict, kern: Kern | None = None) -> list[Kennzahl]:
    from belegung import maengel as mg
    from belegung import zimmerplan as zp

    from . import renovierung_kern as rk

    aktiv = [z for z in stand.zimmer if z.aktiv]
    betten = sum(z.betten for z in aktiv)
    defekt = sum(z.betten for z in aktiv if z.id in stand.lage.unbewohnbar)
    bau = rk.gesperrte_betten(plan_zeilen, date(heute.year, heute.month, 1))
    verfuegbar = betten - defekt - bau
    belegt = 0
    for z in aktiv:
        belegt += sum(1 for b in stand.lage.belegungen.get(z.id, [])
                      if b.art in ("belegt", "geplant") and b.von <= heute <= b.bis and b.name)
    erg = [Kennzahl("Verfügbare Betten heute", f"{verfuegbar:g}", f"von {betten} · {defekt} defekt · {bau:g} Baustelle",
                    "warn" if defekt + bau > betten * .05 else "", "Zimmer-Stammdaten, Mängel, Renovierungsplan"),
           Kennzahl("Auslastung auf verfügbar", f"{round(100 * belegt / verfuegbar)} %" if verfuegbar else "–",
                    f"{belegt} belegt/geplant heute", "krit" if verfuegbar and belegt / verfuegbar > .97 else
                    "warn" if verfuegbar and belegt / verfuegbar > .9 else "", "Gebäudeplan und Planung")]
    # Belegtage je Gruppe (letzte 12 Monate, bekannte Belegungen)
    von = heute - timedelta(days=365)
    tage: dict[str, int] = {}
    for z in aktiv:
        for b in stand.lage.belegungen.get(z.id, []):
            if b.art not in ("belegt", "geplant") or not b.name or b.name == zp.PIVOT_NAME:
                continue
            a, e = max(b.von, von), min(b.bis, heute)
            if a <= e:
                g = zp.belegung_gruppe(b) or "sonstige"
                tage[g] = tage.get(g, 0) + (e - a).days + 1
    gesamt = sum(tage.values())
    w = werte()
    saetze = w["tagessaetze"]
    if gesamt and saetze:
        bekannt = {g: t for g, t in tage.items() if g in saetze}
        erloes = sum(t * saetze[g] for g, t in bekannt.items())
        tage_b = sum(bekannt.values())
        schnitt = erloes / tage_b if tage_b else 0
        erg.append(Kennzahl("Erlös (12 Monate)", f"{erloes:,.0f} €".replace(",", "."),
                            f"Ø {schnitt:,.0f} € je Belegtag".replace(",", ".") + (
                                f" · ohne Satz: {', '.join(sorted(set(tage) - set(saetze)))}" if set(tage) - set(saetze) else ""),
                            "", "Belegtage × eingetragene Tagessätze"))
        leer = max(0, round(verfuegbar * 365 * .95) - gesamt)          # 5 % Leerstand sind gewollte Reserve
        erg.append(Kennzahl("Leerstand über der Zielreserve (12 Monate, Schätzung)", f"{leer * schnitt:,.0f} €".replace(",", "."),
                            f"{leer:,} Betttage über 5 % Reserve × Ø-Satz".replace(",", "."), "",
                            "verfügbare Betten × 365 × 95 % − Belegtage, bewertet mit dem Ø-Tagessatz"))
    ab = w["abweisungen"]
    letzte = [f"{(date(heute.year, heute.month, 1) - timedelta(days=31 * i)):%Y-%m}" for i in range(12)]
    if ab:
        n = sum(ab.get(m, 0) for m in letzte)
        erg.append(Kennzahl("Abweisungen (12 Monate)", str(n), "„kein Zimmer frei“ – eingetragen je Monat",
                            "krit" if n >= 10 else "warn" if n else "", "eigene Zählung"))
    if gesamt:
        teile = sorted(tage.items(), key=lambda x: -x[1])
        erg.append(Kennzahl("Belegtage je Gruppe (12 Monate)", f"{gesamt:,}".replace(",", "."),
                            " · ".join(f"{g} {round(100 * t / gesamt)} %" for g, t in teile[:4]), "",
                            "bekannte Belegungen im Gebäudeplan"))
    # Ausfall durch Defekte (unbewohnbar), letzte 12 Monate
    ausfall, dauer = 0, []
    for m in mg.laden():
        if mg.stufe([m]) < 3:
            continue
        a, e = max(m.seit, von), min(m.behoben or heute, heute)
        if a <= e:
            ausfall += (e - a).days + 1
        if m.behoben and m.behoben >= von:
            dauer.append((m.behoben - m.seit).days)
    erg.append(Kennzahl("Ausfalltage durch Defekte (12 Monate)", f"{ausfall}",
                        f"Ø {sum(dauer) / len(dauer):.0f} Tage bis bezugsfertig ({len(dauer)} behoben)" if dauer else
                        "noch keine behobenen Defekte erfasst", "warn" if ausfall > 60 else "", "Mängel"))
    # Bestand
    bekannt = [f for f in fl if f.alter is not None]
    n_bestand = rk.bestand(fl)
    ziel = int(p.get("ziel_zimmer") or 0)
    zy = rk.zyklus(fl, ziel)
    im_zyklus = 0
    if zy:
        from belegung import zimmerliste as zl

        for f in fl:
            for z in f.zimmer:
                d = zl.reno_datum(z)
                if d and (heute - d).days / 365.25 <= zy:
                    im_zyklus += 1
    erg.append(Kennzahl("Offene Klasse-A-Zimmer", str(rk.a_zimmer(fl)),
                        f"Bau oder Möbel dringend · {sum(f.reno_bekannt for f in fl)} von {n_bestand} Zimmern mit Renovierungsdatum",
                        "krit" if rk.a_zimmer(fl) else "", "Mängel, Renovierungsdaten, Zustandsnoten"))
    daten_da = any(f.alter is not None for f in fl)
    erg.append(Kennzahl("Zimmer innerhalb des Zyklus", f"{round(100 * im_zyklus / n_bestand)} %" if n_bestand and zy and daten_da
                        else "–", (f"Zyklus {zy:g} Jahre bei {ziel} Zimmern je Jahr" if daten_da else
                                   "noch keine Renovierungsdaten – Renovierungsliste einfügen") if zy else "kein Zimmerziel",
                        "warn" if n_bestand and zy and daten_da and im_zyklus / n_bestand < .5 else "", "Renovierungsvermerke, Ziel"))
    if kern and kern.gesamt:
        erg.append(Kennzahl("Kernbestand", f"{kern.kern} von {kern.gesamt} Betten",
                            f"Spitze {kern.spitze:.0f} + Ausfall {kern.ausfall:.0f} + Typen {kern.typ:.0f} + Puffer {kern.puffer:.0f}",
                            "", "Prognose (obere Spanne), Mängel, Annahmen"))
        erg.append(Kennzahl("Strukturelle Reserve", f"{kern.reserve} Betten ({100 * kern.reserve / kern.gesamt:.0f} %)",
                            f"als ganze Etagen vorgeschlagen: {kern.reserve_betten} Betten" if kern.etagen else
                            "keine ganze Etage passt hinein", "", "Kernbestand"))
    return erg


def luecken() -> list[tuple[str, str]]:
    """Was noch fehlt – und wo man es einträgt."""
    from . import renovierung_kern as rk

    w = werte()
    erg = []
    if not w["tagessaetze"]:
        erg.append(("Erlös je Belegtag, Leerstandskosten", "Tagessätze je Gruppe – unter „Werte eingeben …“"))
    if not w["abweisungen"]:
        erg.append(("Abweisungen („kein Zimmer frei“)", "Anzahl je Monat – unter „Werte eingeben …“"))
    if not rk.zustandsnoten():
        erg.append(("Zustandsnote je Etage", "eine Begehung (Note 1–5) – unter „Werte eingeben …“"))
    if len(buchungsstaende()) < 12:
        erg.append(("Pickup (erwarteter Zugang nach Vorlauf)", "mindestens 12 Monatsstände – werden automatisch gesammelt"))
    return erg


# ---- Bericht (eine Seite, zum Drucken bzw. als PDF) -------------------------------------------------

def _svg_linie(li: Linie, breite: int = 680, hoehe: int = 200) -> str:
    """Einfaches SVG ohne Bibliothek: Ist, Prognose mit Spanne, Vorjahr, Kapazität mit Baustellen."""
    werte = [v for reihe in (li.ist, li.prognose, li.lo80, li.hi80, li.vorjahr, li.kapazitaet) for v in reihe if v is not None]
    if not li.monate or not werte:
        return "<p>Keine Prognosedaten.</p>"
    lo, hi = min(werte) * .95, max(werte) * 1.03
    n = len(li.monate)
    x = lambda i: 40 + i * (breite - 50) / max(1, n - 1)
    y = lambda v: hoehe - 20 - (v - lo) / (hi - lo or 1) * (hoehe - 30)

    def pfad(reihe, stil):
        punkte = [f"{x(i):.1f},{y(v):.1f}" for i, v in enumerate(reihe) if v is not None]
        return f'<polyline fill="none" {stil} points="{" ".join(punkte)}"/>' if len(punkte) > 1 else ""
    band = [(i, l, h) for i, (l, h) in enumerate(zip(li.lo80, li.hi80)) if l is not None and h is not None]
    poly = ""
    if band:
        oben = " ".join(f"{x(i):.1f},{y(h):.1f}" for i, _l, h in band)
        unten = " ".join(f"{x(i):.1f},{y(l):.1f}" for i, l, _h in reversed(band))
        poly = f'<polygon points="{oben} {unten}" fill="#3b6ea5" fill-opacity=".15"/>'
    achse = "".join(f'<text x="{x(i):.1f}" y="{hoehe - 4}" font-size="9" text-anchor="middle" fill="#555">'
                    f'{"JFMAMJJASOND"[m.month - 1]}{"" if m.month != 1 else str(m.year)[2:]}</text>'
                    for i, m in enumerate(li.monate))
    skala = "".join(f'<text x="34" y="{y(v) + 3:.1f}" font-size="9" text-anchor="end" fill="#555">{v:.0f}</text>'
                    f'<line x1="38" x2="{breite - 8}" y1="{y(v):.1f}" y2="{y(v):.1f}" stroke="#ddd"/>'
                    for v in (lo + (hi - lo) * t / 4 for t in range(5)))
    return (f'<svg viewBox="0 0 {breite} {hoehe}" width="100%" xmlns="http://www.w3.org/2000/svg">{skala}{poly}'
            + pfad(li.vorjahr, 'stroke="#999" stroke-width="1.2" stroke-dasharray="2 3"')
            + pfad(li.kapazitaet, 'stroke="#b33" stroke-width="1.5"')
            + pfad(li.ist, 'stroke="#222" stroke-width="2"')
            + pfad(li.prognose, 'stroke="#3b6ea5" stroke-width="2" stroke-dasharray="6 4"')
            + achse + "</svg>")


def naechste_schritte(zeilen: list, p: dict, heute: date) -> list[tuple[date, str, str]]:
    """Rückwärts gerechnet ab dem ersten Baubeginn: (bis wann, was, wer – Vorschlag)."""
    if not zeilen:
        return []
    erste = min(zeilen, key=lambda z: z.start)
    s = erste.start
    liefer = int(p.get("lieferzeit_tage") or 28)
    schritte = [(s - timedelta(days=liefer + 7), "Möbel bestellen (Lieferzeit " + f"{liefer} Tage)", "Verwaltung / Einkauf"),
                (s - timedelta(days=42), "Bauauftrag vergeben (Termin mit dem Handwerksbetrieb)", "Facility-Management")]
    if any(z.art == "etage" for z in zeilen):
        e = min((z for z in zeilen if z.art == "etage"), key=lambda z: z.start)
        schritte.append((e.stopp_ab, f"Belegungsstopp {e.text} – niemanden mehr neu einplanen", "Internatsverwaltung"))
    beschluss = max(heute, min(d for d, _w, _x in schritte) - timedelta(days=7))
    schritte = [(max(d, heute), w + (" – eigentlich schon fällig" if d < heute else ""), x) for d, w, x in schritte]
    schritte.append((beschluss, "Beschluss der Geschäftsführung", "Geschäftsführung"))
    return sorted(schritte, key=lambda s_: (s_[0], s_[1] != "Beschluss der Geschäftsführung"))


def bericht_html(c: dict) -> str:
    """Entscheidungsvorlage: Seite 1 = Kurzfassung (Beschluss, Beträge je Kostenstelle mit Spanne, Maßnahmen, Warum,
    Nichtstun, Kürzung, Risiken, nächste Schritte, Beschlussfeld). Anhang: Varianten, Zeitplan, Kostenherleitung,
    Belegung, Strategie 5 Jahre, Kennzahlen, Annahmen und Datenquellen, Erläuterungen.

    ``c``: standort, heute, jahr, p, varianten, empfehlung (gewählt), empfohlen, zeilen, strategien, kz, li, guete,
    entscheidungen, luecken, kern, robust."""
    from html import escape as e

    from . import renovierung_kern as rk

    p, jahr, heute = c["p"], c["jahr"], c["heute"]
    vs = c.get("varianten") or []
    v = next((x for x in vs if x.schluessel == c.get("empfehlung")), None)
    zeilen = c.get("zeilen") or []
    strat = {s.schluessel: s for s in c.get("strategien") or []}
    kern = c.get("kern")
    budget = p.get("modus") != "ziel"
    t = rk.tsd
    k = v.kosten if v else rk.Kosten(0, jahr)
    antrag = c.get("antrag") or rk.moebelantrag(v)
    bereits = c.get("bereits") or {}
    bau_von, bau_bis = k.spanne_von("bau")
    bau_ges = k.instandhaltung + bereits.get("bau", 0)
    bau_von, bau_bis = bau_von + bereits.get("bau", 0), bau_bis + bereits.get("bau", 0)
    geschaetzt = k.geschaetzt
    # --- Seite 1
    massn = "".join(f"<tr><td>{e(z.titel)}</td><td>{z.start:%m/%Y}</td><td class=r>{t(z.kosten.instandhaltung)}</td>"
                    f"<td class=r>{t(z.kosten.investition)}</td></tr>" for z in zeilen) or "<tr><td colspan=4>Keine Maßnahme.</td></tr>"
    bb = p.get("budget_bau")
    beschluss = (f"Die Geschäftsführung gibt für {jahr} die unten aufgeführten Maßnahmen frei"
                 + (" (bereits vorgemerkt" + (f" + Vorschlag „{e(v.titel)}“" if v and v.massnahmen else "") + ")"
                    if bereits.get("anzahl") else f" (Vorschlag „{e(v.titel if v else '–')}“)") + ": "
                 f"<b>Bau {t(bau_ges)}</b>" + (f" aus dem Baubudget von {t(bb)}" if budget and bb is not None else "")
                 + f" und beantragt <b>Möbel {t(antrag['summe'])}</b> (Spanne {rk.spanne_text(antrag['von'], antrag['bis'])}).")
    a_heute = rk.a_zimmer([f for f in (c.get("fl") or [])]) if c.get("fl") else None
    warum = []
    if v:
        warum.append(f"{v.a_zimmer} dringende Zimmer (Klasse A) werden erneuert" + (f", {a_heute} gibt es heute" if a_heute is not None else "") + ".")
        warum.append(f"{v.zimmer} Zimmer insgesamt; " + (f"{t(v.rest_bau)} Baubudget bleiben ungenutzt." if budget and v.rest_bau
                                                          and v.rest_bau > 500 else "das Baubudget wird ausgeschöpft." if budget and bb else ""))
    warn = [z for z in zeilen if z.engpass]
    warum.append("Belegung: In den Baumonaten bleibt die Prognose unter der Warnschwelle." if not warn else
                 f"Belegung: {len(warn)} Maßnahme(n) liegen an der Warnschwelle – siehe Anhang B.")
    nichts = strat.get("nichts")
    wenn_nicht = (f"Ohne Maßnahme bleiben {nichts.jahre[min(1, len(nichts.jahre) - 1)]['a_offen']} Zimmer in Klasse A "
                  f"(in 2 Jahren); der Bestand altert weiter." if nichts and nichts.jahre else "–")
    kz, em = strat.get("kuerzung"), strat.get("empfohlen")
    if kz and em and kz.jahre and em.jahre:
        weg = sorted(set(em.jahre[0]["text"].split("; ")) - set(kz.jahre[0]["text"].split("; ")))
        wenn_kurz = ("Bei −20 % entfällt im ersten Jahr: " + "; ".join(weg) + ".") if weg and weg != ["nichts"] else \
            "Bei −20 % ändert sich im ersten Jahr nichts Wesentliches."
    else:
        wenn_kurz = "–"
    risiken = [f"Kostenspanne Bau {rk.spanne_text(bau_von, bau_bis)}, Möbel {rk.spanne_text(antrag['von'], antrag['bis'])}.",
               f"Datenqualität: {100 * geschaetzt:.0f} % der Summe stammen nicht aus einem Angebot.",
               c.get("robust") or ""]
    alt = rk.angebote_alt(p, heute)
    if alt:
        risiken.append("Angebote älter als 12 Monate: " + ", ".join(alt) + ".")
    if any(z.ohne_ausweich for z in zeilen):
        risiken.append("Für einzelne Betroffene fehlt ein Ausweichzimmer.")
    if any(not z.pruefbar for z in zeilen):
        risiken.append("Einige Termine liegen hinter den bekannten Buchungen – Ausweich dort nicht prüfbar, nur Prognose.")
    schritte = naechste_schritte(zeilen, p, heute)
    schr = "".join(f"<tr><td>{d:%d.%m.%Y}</td><td>{e(w)}</td><td>{e(x)}</td></tr>" for d, w, x in schritte)
    knapp = any("schon fällig" in w for _d, w, _x in schritte)
    frist = ((f"<p><b>Ohne Beschluss bis {schritte[0][0]:%d.%m.%Y} verschiebt sich die erste Maßnahme.</b>"
              + (" Die Fristen sind bereits knapp – ggf. die erste Maßnahme einen Monat später legen." if knapp else "")
              + "</p>") if schritte else "")
    band = ('<div class="band">Enthält Schätzungen bzw. Platzhalter – Beträge sind Richtwerte, keine Angebote.</div>'
            if geschaetzt > .2 else "")
    gewaehlt_hinweis = ""
    emp = next((x for x in vs if x.schluessel == c.get("empfohlen")), None)
    if emp and v and emp is not v:
        gewaehlt_hinweis = f"<p class=s>Rechnerisch läge „{e(emp.titel)}“ vorn; gewählt wurde bewusst „{e(v.titel)}“.</p>"
    # --- Anhang
    vz = "".join(f"<tr{' class=empf' if x is v else ''}><td>{e(x.titel)}</td><td class=r>{x.zimmer}</td><td class=r>{x.a_zimmer}</td>"
                 f"<td class=r>{t(x.kosten.instandhaltung)}</td><td class=r>{t(x.kosten.investition)}</td>"
                 f"<td class=r>{t(x.rest_bau) if budget and x.rest_bau is not None else '–'}</td><td class=r>{x.sperr_zimmermonate(p):g}</td></tr>"
                 f"<tr><td colspan=7 class=s>{e(x.erklaerung)} {e(x.hinweis)}</td></tr>" for x in vs)
    zp_ = "".join(f"<tr><td>{e(z.titel)}</td><td>{'vorgemerkt' if z.status == 'vorgemerkt' else 'Vorschlag'}</td>"
                  f"<td>{f'{z.stopp_ab:%d.%m.%Y}' if z.art == 'etage' else '–'}</td><td>{z.start:%d.%m.} – {z.ende:%d.%m.%Y}</td>"
                  f"<td>{'▲ Warnschwelle ' if z.engpass else ''}{'⚑ Ausweich fehlt ' if z.ohne_ausweich else ''}"
                  f"{'nicht prüfbar ' if not z.pruefbar else ''}{'≈ gleichwertig' if z.gleichwertig else ''}</td>"
                  f"<td class=r>{t(z.kosten.summe)}</td></tr>"
                  + (f"<tr><td colspan=6 class=s>{e(', '.join(f'{x[1]} ab {x[2]:%d.%m.}' for x in z.teile))}</td></tr>" if z.teile else "")
                  for z in zeilen) or "<tr><td colspan=6>Nichts geplant.</td></tr>"
    beispiele: dict = {}
    for z in zeilen:
        beispiele.setdefault(z.art, z)
    herl = "".join(f"<h3>{e(z.titel)}</h3><table>" + "".join(f"<tr><td>{e(a)}</td><td class=r>{rk.euro(b)}</td></tr>"
                                                             for a, b in z.kosten.herleitung if b)
                   + f"<tr class=sum><td>Gesamt</td><td class=r>{rk.euro(z.kosten.summe)}</td></tr></table>"
                   for z in beispiele.values())
    sz = "".join(f"<tr><td>{e(s.titel)}</td><td class=r>{s.a_start} → {s.a_ende}</td><td class=r>{s.zimmer}</td>"
                 f"<td class=r>{t(s.summe('bau'))}</td><td class=r>{t(s.summe('moebel'))}</td>"
                 f"<td class=r>{'–' if s.zyklus is None else f'{s.zyklus:g}'}</td></tr><tr><td colspan=6 class=s>{e(s.deutung)}</td></tr>"
                 for s in c.get("strategien") or [])
    kzs = "".join(f"<tr><td>{e(x.titel)}</td><td class=r><b>{e(x.wert)}</b></td><td class=s>{e(x.unter)}</td></tr>"
                  for x in c.get("kz") or [])
    quellen = []
    for h in p["haeuser"]:
        for feld, name in (("bau_etage", "Bau je Etage"), ("moebel_zimmer", "Möbel je Zimmer")):
            quellen.append(f"Haus {h} {name}: {rk.euro((p['kosten'][h] or {}).get(feld) or 0)} netto "
                           f"[{rk.HERKUNFT_TEXT[rk.herkunft(p, h, feld)]}]")
    annahmen = (f"Preisstand {p['preisstand']}, Bau +{p['preis_pct']} %/Jahr, Möbel +{p.get('preis_moebel_pct')} %/Jahr · "
                f"Nebenkosten {p['neben_pct']} % · Puffer Bau {p.get('puffer_bau_pct')} %, Möbel {p.get('puffer_moebel_pct')} % · "
                f"Vorsteuerquote {p['vorsteuer_pct']} % · Belegungsstopp {p['vorlauf_tage']} Tage · Bauzeit "
                + ", ".join(f"Haus {h} {p['kosten'][h].get('dauer_tage', 30)} Tage" for h in p["haeuser"])
                + f" · Möbel-Lieferzeit {p.get('lieferzeit_tage')} Tage.")
    erl = [
        ("Klassen", "A = jetzt nötig (Renovierung nötig, Schimmel, Note 5, ≥ 20 Jahre, Möbel defekt), B = in 1–3 Jahren "
                    "(Note 4, ≥ 15 Jahre, Boden/Wand), C = später. Getrennt für Bau und Möbel. Erst alle A, dann B."),
        ("Baubudget", "Feste Grenze, die verfällt – deshalb soll es möglichst voll in gedeckten Bedarf gehen."),
        ("Möbelantrag", "Möbel für die Bau-Maßnahmen plus „nur Möbel“ für Zimmer mit dringendem Möbelbedarf."),
        ("Spanne", "Unsicherheit nach Herkunft: Angebot ±10 %, Eingabe ±15 %, Schätzung ±25 %, Platzhalter ±40 %."),
        ("Belegungsstopp", "Ab diesem Tag wird niemand mehr neu in die Etage geplant."),
        ("Ausweich ⚑", "Für jede betroffene Person ein passendes freies Zimmer in allen Häusern (Regeln wie beim Zuteilen)."),
        ("Warnschwelle ▲", "95 % der Kapazität ohne gesperrte Zimmer; die obere Prognose darf sie im Baumonat nicht erreichen."),
        ("Nicht prüfbar", "Hinter den bekannten Buchungen kann der Ausweich nicht geprüft werden; dort zählt nur die Prognose."),
        ("Kernbestand", "Spitzenbedarf + Ausfallreserve + Typen-Reserve + Puffer. Der Rest ist Reserve: in Betrieb halten, "
                        "nicht renovieren – Entscheidung der Geschäftsführung, jährlich neu."),
        ("Sperr-Zimmermonate", "Zimmer × Monate, die wegen Arbeiten nicht belegt werden können."),
        ("Vorsteuerquote", "Anteil der Umsatzsteuer, der zurückkommt. 0 % = brutto zählt."),
    ]
    erl_html = "".join(f"<tr><td><b>{e(a)}</b></td><td>{e(b)}</td></tr>" for a, b in erl)
    kern_html = f"<p>{e(kern.text)}</p>" + ("<p>Vorgeschlagene Reserve-Etagen: " + e(", ".join(f.text for f in kern.etagen))
                                             + f". Bei +10 % Nachfrage fehlten {kern.fehlend_plus10} Betten.</p>"
                                             if kern.etagen else "") if kern and kern.gesamt else ""
    return f"""<!doctype html><html lang="de"><head><meta charset="utf-8"><title>Entscheidungsvorlage Renovierung {jahr}</title>
<style>@page {{ size: A4; margin: 13mm 14mm 15mm }} body {{ font: 10.5px/1.45 'Segoe UI', sans-serif; color: #1d1d1d; margin: 0 }}
h1 {{ font-size: 17px; margin: 0 }} h2 {{ font-size: 12.5px; margin: 12px 0 3px; border-bottom: 1.5px solid #3b6ea5; padding-bottom: 2px }}
h3 {{ font-size: 11px; margin: 8px 0 2px }} .s {{ color: #555; font-size: 9.5px }} .kopf {{ color: #555; margin-bottom: 6px }}
table {{ border-collapse: collapse; width: 100%; margin: 3px 0 }} td, th {{ border-bottom: 1px solid #e2e2e2; padding: 2px 4px;
text-align: left; vertical-align: top }} th {{ color: #444; font-weight: 600; background: #f3f5f8 }} .r {{ text-align: right; white-space: nowrap }}
tr.empf td {{ background: #eef4fb; font-weight: 600 }} tr.sum td {{ font-weight: 700; border-top: 1.5px solid #888 }}
.box {{ border: 1.5px solid #3b6ea5; border-radius: 6px; padding: 6px 10px; margin: 6px 0 }} .band {{ background: #fff4d6;
border: 1px solid #c9a227; padding: 4px 8px; margin: 4px 0; font-weight: 600 }} .zwei {{ display: grid; grid-template-columns: 1fr 1fr; gap: 10px }}
.beschluss td {{ border: 1px solid #bbb; padding: 7px }} .seite {{ page-break-before: always }} ul {{ margin: 2px 0; padding-left: 16px }}</style></head><body>
<h1>Entscheidungsvorlage Zimmerrenovierung {jahr} · {e(c.get('standort', ''))}</h1>
<div class="kopf">Stand {heute:%d.%m.%Y} · INNternat · unverbindliche Planung · Beträge auf 1.000 € gerundet</div>{band}
<div class="box"><b>Beschlussvorschlag:</b> {beschluss}</div>{gewaehlt_hinweis}
<div class="zwei"><div><h2>Beträge {jahr}</h2><table><tr><th>Kostenstelle</th><th class=r>erwartet</th><th class=r>Spanne</th></tr>
<tr><td>Bau (Maler, Boden, Nebenkosten)</td><td class=r>{t(bau_ges)}</td><td class=r>{rk.spanne_text(bau_von, bau_bis)}</td></tr>
<tr><td>Möbel (Antrag)</td><td class=r>{t(antrag['summe'])}</td><td class=r>{rk.spanne_text(antrag['von'], antrag['bis'])}</td></tr>
<tr><td class=s>davon für die Bau-Maßnahmen / nur Möbel</td><td class=r colspan=2>{t(antrag['bau_mass'])} / {t(antrag['nur_moebel'])}</td></tr></table></div>
<div><h2>Maßnahmen</h2><table><tr><th>Was</th><th>Ab</th><th class=r>Bau</th><th class=r>Möbel</th></tr>{massn}</table></div></div>
<h2>Warum</h2><ul>{''.join(f'<li>{e(x)}</li>' for x in warum if x)}</ul>
<div class="zwei"><div><h2>Wenn nicht</h2><p>{e(wenn_nicht)}</p></div><div><h2>Wenn −20 %</h2><p>{e(wenn_kurz)}</p></div></div>
<h2>Risiken</h2><ul>{''.join(f'<li>{e(x)}</li>' for x in risiken if x)}</ul>
<h2>Nächste Schritte</h2><table><tr><th>Bis</th><th>Was</th><th>Wer (Vorschlag)</th></tr>{schr or '<tr><td colspan=3>–</td></tr>'}</table>{frist}
<table class="beschluss"><tr><td>☐ Bau freigegeben</td><td>☐ Möbelbudget {t(antrag['summe'])} beantragt / freigegeben</td><td>☐ mit Änderungen: ____________</td>
<td>☐ zurückgestellt</td></tr><tr><td colspan="4">Datum, Unterschrift: ______________________________________</td></tr></table>
<h1 class="seite">Anhang</h1>
<h2>A Varianten {jahr}</h2><table><tr><th>Variante</th><th class=r>Zimmer</th><th class=r>davon A</th><th class=r>Bau</th>
<th class=r>Möbel</th><th class=r>Rest Bau</th><th class=r>Sperr-Zi.-M.</th></tr>{vz}</table>
<p class=s>Rechnerisch beste Variante unter den genannten Annahmen = meister gedeckter Bedarf (erst A, dann B, dann C), dann mehr Zimmer, dann mehr genutztes Baubudget. {e(c.get('robust') or '')}</p>
<h2>B Zeitplan</h2><table><tr><th>Maßnahme</th><th>Status</th><th>Stopp ab</th><th>Bauzeit</th><th>Hinweise</th><th class=r>Kosten</th></tr>{zp_}</table>
<h2>C Wie die Kosten zustande kommen</h2>{herl or '<p>–</p>'}
<h2 class="seite">D Belegung und Kapazität</h2>{_svg_linie(c["li"]) if c.get("li") else ""}
<p class=s>━ Ist · ╍ Prognose mit 80-%-Spanne · ┈ Vorjahr · rot: Kapazität minus Baustellen. {e(c["guete"].satz if c.get("guete") else '')}</p>{kern_html}
<h2>E Strategie 5 Jahre</h2><table><tr><th>Strategie</th><th class=r>A-Zimmer</th><th class=r>Zimmer</th><th class=r>Bau</th><th class=r>Möbel</th><th class=r>Zyklus</th></tr>{sz}</table>
<p class=s>Planungshorizont: {c["jahr"]} belastbar · {c["jahr"] + 1} wahrscheinlich · {c["jahr"] + 2}–{c["jahr"] + 4} nur Orientierung.</p>
<h2>F Kennzahlen</h2><table>{kzs}</table>
<h2>G Annahmen und Datenquellen</h2><p>{e(annahmen)}</p><ul>{''.join(f'<li>{e(x)}</li>' for x in quellen)}</ul>
{('<ul>' + ''.join(f'<li>{e(a)} – braucht: {e(b)}</li>' for a, b in c.get('luecken') or []) + '</ul>') if c.get('luecken') else ''}
<h2>H Erläuterungen</h2><table>{erl_html}</table>
<h2>Offene Punkte</h2><ul>{''.join(f'<li>{e(x)}</li>' for x in c.get('entscheidungen') or []) or '<li>Keine.</li>'}</ul>
</body></html>"""
