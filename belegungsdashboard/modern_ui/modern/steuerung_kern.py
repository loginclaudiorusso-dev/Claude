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


def kennzahlen(stand, heute: date, fl: list, plan_zeilen: list, p: dict) -> list[Kennzahl]:
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
    erg.append(Kennzahl("Ø Jahre seit Renovierung", f"{sum(f.alter for f in bekannt) / len(bekannt):.1f}" if bekannt else "–",
                        f"{sum(f.reno_bekannt for f in fl)} von {n_bestand} Zimmern mit Datum" if fl else "",
                        "", "Renovierungsvermerke"))
    daten_da = any(f.alter is not None for f in fl)
    erg.append(Kennzahl("Zimmer innerhalb des Zyklus", f"{round(100 * im_zyklus / n_bestand)} %" if n_bestand and zy and daten_da
                        else "–", (f"Zyklus {zy:g} Jahre bei {ziel} Zimmern je Jahr" if daten_da else
                                   "noch keine Renovierungsdaten – Renovierungsliste einfügen") if zy else "kein Zimmerziel",
                        "warn" if n_bestand and zy and daten_da and im_zyklus / n_bestand < .5 else "", "Renovierungsvermerke, Ziel"))
    return erg


LUECKEN = [("Erlös je Belegtag, Leerstandskosten", "Tagessätze je Kostenträger und Mietpreise"),
           ("Abweisungen („kein Zimmer frei“), externe Unterbringung", "eine Zählung im Tagesbetrieb bzw. Hotelkosten"),
           ("Zustandsnote je Etage", "eine jährliche Begehung (Note 1–5)"),
           ("Pickup (erwarteter Zugang nach Vorlauf)", "einige Monate Buchungsstände – werden ab jetzt monatlich gesammelt")]


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


def bericht_html(standort: str, heute: date, kz: list[Kennzahl], li: Linie, g: Guete, zeilen: list, szen: list,
                 p: dict, entscheidungen: list[str]) -> str:
    from html import escape as e

    from . import renovierung_kern as rk

    karten = "".join(f'<div class="k"><div class="t">{e(k.titel)}</div><div class="w {k.stufe}">{e(k.wert)}</div>'
                     f'<div class="u">{e(k.unter)}</div></div>' for k in kz[:4])
    plan = "".join(f"<tr><td>{e(z.text)}</td><td>{'vorgemerkt' if z.status == 'vorgemerkt' else 'Vorschlag'}</td>"
                   f"<td>{z.stopp_ab:%d.%m.}</td><td>{z.start:%d.%m.} – {z.ende:%d.%m.%Y}</td><td>{z.zimmer}</td>"
                   f"<td class='r'>{rk.euro(z.kosten.summe)}</td></tr>" for z in zeilen) or \
        "<tr><td colspan=6>Noch nichts geplant.</td></tr>"
    sz = "".join(f"<tr><td>{e(s.titel)}</td><td>{s.zimmer}</td><td class='r'>{rk.euro(s.kosten.summe)}</td>"
                 f"<td>{s.sperr_zimmermonate:g}</td><td>{s.jahre_bis_durch}</td><td>{'–' if s.zyklus is None else f'{s.zyklus:g}'}</td></tr>"
                 for s in szen)
    ent = "".join(f"<li>{e(t)}</li>" for t in entscheidungen) or "<li>Keine offenen Entscheidungen.</li>"
    annahmen = (f"Kosten mit Preisstand {p['preisstand']}, +{p['preis_pct']} % je Jahr, Nebenkosten {p['neben_pct']} %, "
                f"Puffer {p['puffer_pct']} %, Vorsteuerquote {p['vorsteuer_pct']} % (0 % = brutto). Prognose: Plätze laut "
                "Pivot; ab Monat 13 nur fortgeschrieben. Alle Renovierungen unverbindlich.")
    return f"""<!doctype html><html lang="de"><head><meta charset="utf-8"><title>Steuerung {e(standort)} {heute:%d.%m.%Y}</title>
<style>@page {{ size: A4 landscape; margin: 12mm }} body {{ font: 11px 'Segoe UI', sans-serif; color: #222; margin: 0 }}
h1 {{ font-size: 17px; margin: 0 0 2px }} h2 {{ font-size: 12px; margin: 10px 0 4px }} .s {{ color: #666 }}
.ks {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 8px; margin: 8px 0 }} .k {{ border: 1px solid #ccc; border-radius: 6px; padding: 6px 8px }}
.t, .u {{ color: #555; font-size: 10px }} .w {{ font-size: 18px; font-weight: 600 }} .w.warn {{ color: #a66a00 }} .w.krit {{ color: #b3261e }}
.zwei {{ display: grid; grid-template-columns: 1fr 1fr; gap: 12px }} table {{ border-collapse: collapse; width: 100% }}
td, th {{ border-bottom: 1px solid #e3e3e3; padding: 3px 4px; text-align: left }} th {{ font-weight: 600; color: #444 }} .r {{ text-align: right }}
.leg span {{ margin-right: 12px }} ul {{ margin: 0; padding-left: 16px }}</style></head><body>
<h1>Steuerung · {e(standort)}</h1><div class="s">Stand {heute:%d.%m.%Y} · nur zur Planung, keine Buchung</div>
<div class="ks">{karten}</div>
<h2>Belegung: Ist, Prognose (80-%-Spanne), Vorjahr, Kapazität mit Baustellen</h2>{_svg_linie(li)}
<div class="leg s"><span>━ Ist</span><span style="color:#3b6ea5">╍ Prognose</span><span style="color:#999">┈ Vorjahr</span>
<span style="color:#b33">━ Kapazität (minus Baustellen)</span></div><p>{e(g.satz)} {e(g.hinweis)}</p>
<div class="zwei"><div><h2>Renovierung {zeilen[0].start.year if zeilen else ''}</h2><table><tr><th>Etage</th><th>Status</th><th>Stopp ab</th>
<th>Bau</th><th>Zi.</th><th class="r">Kosten</th></tr>{plan}</table></div>
<div><h2>Szenarien je Jahr</h2><table><tr><th>Szenario</th><th>Zi.</th><th class="r">Kosten</th><th>Sperr-Zi.-Monate</th>
<th>Jahre bis durch</th><th>Zyklus (J.)</th></tr>{sz}</table></div></div>
<h2>Zu entscheiden</h2><ul>{ent}</ul><p class="s">{e(annahmen)}</p></body></html>"""
