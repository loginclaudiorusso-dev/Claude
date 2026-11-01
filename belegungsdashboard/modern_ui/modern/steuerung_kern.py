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
        leer = max(0, verfuegbar * 365 - gesamt)
        erg.append(Kennzahl("Leerstandskosten (12 Monate, Schätzung)", f"{leer * schnitt:,.0f} €".replace(",", "."),
                            f"{leer:,} freie Betttage × Ø-Satz".replace(",", "."), "",
                            "verfügbare Betten × 365 − Belegtage, bewertet mit dem Ø-Tagessatz"))
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
    erg.append(Kennzahl("Ø Jahre seit Renovierung", f"{sum(f.alter for f in bekannt) / len(bekannt):.1f}" if bekannt else "–",
                        f"{sum(f.reno_bekannt for f in fl)} von {n_bestand} Zimmern mit Datum" if fl else "",
                        "", "Renovierungsvermerke"))
    daten_da = any(f.alter is not None for f in fl)
    erg.append(Kennzahl("Zimmer innerhalb des Zyklus", f"{round(100 * im_zyklus / n_bestand)} %" if n_bestand and zy and daten_da
                        else "–", (f"Zyklus {zy:g} Jahre bei {ziel} Zimmern je Jahr" if daten_da else
                                   "noch keine Renovierungsdaten – Renovierungsliste einfügen") if zy else "kein Zimmerziel",
                        "warn" if n_bestand and zy and daten_da and im_zyklus / n_bestand < .5 else "", "Renovierungsvermerke, Ziel"))
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


def bericht_html(c: dict) -> str:
    """Entscheidungsvorlage (A4, mehrseitig, zum Drucken bzw. als PDF): Empfehlung, Varianten, Zeitplan, Kosten mit
    Herleitung, Belegung, Szenarien, Kennzahlen – jeweils mit Erklärung, was es bedeutet und wie es zustande kommt.

    ``c``: standort, heute, jahr, p, kz, li, guete, varianten, empfehlung, zeilen, strategien, entscheidungen, luecken."""
    from html import escape as e

    from . import renovierung_kern as rk

    p, jahr, heute = c["p"], c["jahr"], c["heute"]
    vs = c.get("varianten") or []
    empf = next((v for v in vs if v.schluessel == c.get("empfehlung")), None)
    budget = p.get("modus") == "budget"
    eu = rk.euro

    def erkl(text: str) -> str:
        return f'<p class="erkl"><b>So zu lesen:</b> {e(text)}</p>'

    # 1 Worum es geht
    worum = (f"Welche Zimmer bzw. Etagen in Haus {', '.join(p['haeuser'])} sollen {jahr} renoviert werden, wann, und was "
             "kostet es? " + (f"Vorgabe sind die verfügbaren Budgets: Bau {eu(p['budget_bau']) if p.get('budget_bau') is not None else 'ohne Grenze'}"
                             f" und Möbel {eu(p['budget_moebel']) if p.get('budget_moebel') is not None else 'ohne Grenze'}. "
                             if budget else f"Vorgabe ist ein Ziel von {p.get('ziel_zimmer')} Zimmern im Jahr. ")
             + "INNternat vergleicht dafür vier Wege und schlägt Termine vor, an denen möglichst niemand umziehen muss "
               "und die Belegung nicht an die Warnschwelle kommt. Alles ist unverbindliche Planung.")
    # 2 Empfehlung
    if empf:
        k = empf.kosten
        rest = ""
        if budget:
            rb = None if p.get("budget_bau") is None else p["budget_bau"] - k.instandhaltung
            rm = None if p.get("budget_moebel") is None else p["budget_moebel"] - k.investition
            rest = (f" Rest Bau {eu(rb)}" if rb is not None else "") + (f", Rest Möbel {eu(rm)}" if rm is not None else "") + "."
        empfehlung = (f"<p><b>Variante „{e(empf.titel)}“:</b> {e(empf.erklaerung)}</p><ul>"
                      + "".join(f"<li>{e(m.text)} – {eu(m.kosten.summe)}</li>" for m in empf.massnahmen)
                      + f"</ul><p><b>{empf.zimmer} Zimmer, {eu(k.summe)}</b> (Bau {eu(k.instandhaltung)}, Möbel "
                      f"{eu(k.investition)}).{e(rest)} Gedeckter Bedarf: {empf.punkte:g} Punkte.</p>")
        andere = next((v for v in vs if v.schluessel == c.get("empfohlen")), None)
        if andere and andere is not empf:
            empfehlung += (f"<p class=s>Hinweis: Nach den Regeln von INNternat (meister Bedarf, dann mehr Zimmer, dann "
                           f"günstiger) läge „{e(andere.titel)}“ vorn – gewählt wurde bewusst „{e(empf.titel)}“.</p>")
    else:
        empfehlung = "<p>Keine Variante möglich – Budget zu klein oder keine Kosten eingetragen.</p>"
    beschluss = ('<table class="beschluss"><tr><td>☐ Zustimmung zur Empfehlung</td><td>☐ Zustimmung mit Änderungen: '
                 '__________________</td><td>☐ Ablehnung / zurückstellen</td></tr><tr><td colspan="3">Datum, Unterschrift: '
                 '________________________________________</td></tr></table>')
    # 3 Varianten
    vz = "".join(f"<tr{' class=empf' if empf and v is empf else ''}><td>{e(v.titel)}{' ★' if empf and v is empf else ''}</td>"
                 f"<td class=r>{v.zimmer}</td><td class=r>{v.punkte:g}</td><td class=r>{eu(v.kosten.instandhaltung)}</td>"
                 f"<td class=r>{eu(v.kosten.investition)}</td><td class=r>{eu(v.kosten.summe)}</td>"
                 f"<td class=r>{v.sperr_zimmermonate(p):g}</td></tr>" + (f"<tr><td colspan=7 class=s>{e(v.erklaerung)} {e(v.hinweis)}</td></tr>")
                 for v in vs)
    # 4 Zeitplan
    zp_ = "".join(f"<tr><td>{e(z.titel)}</td><td>{'vorgemerkt' if z.status == 'vorgemerkt' else 'Vorschlag'}</td>"
                  f"<td>{f'{z.stopp_ab:%d.%m.%Y}' if z.art == 'etage' else '–'}</td><td>{z.start:%d.%m.} – {z.ende:%d.%m.%Y}</td><td class=r>{z.zimmer}</td>"
                  f"<td>{'Warnschwelle! ' if z.engpass else ''}{f'{z.ohne_ausweich} ohne Ausweich' if z.ohne_ausweich else ''}"
                  f"{'gleichwertige Monate' if z.gleichwertig else ''}</td><td class=r>{eu(z.kosten.summe)}</td></tr>"
                  + (f"<tr><td colspan=7 class=s>Zimmer: {e(', '.join(f'{t[1]} ab {t[2]:%d.%m.}' for t in z.teile))}</td></tr>" if z.teile else "")
                  for z in c.get("zeilen") or []) or "<tr><td colspan=7>Nichts geplant.</td></tr>"
    # 5 Kosten-Herleitung (je Art ein Beispiel)
    beispiele = {}
    for z in c.get("zeilen") or []:
        beispiele.setdefault(z.art, z)
    herl = ""
    for art, z in beispiele.items():
        rows = "".join(f"<tr><td>{e(t)}</td><td class=r>{eu(b)}</td></tr>" for t, b in z.kosten.herleitung if b)
        herl += (f"<h3>{e(z.titel)}</h3><table>{rows}<tr class=sum><td>Gesamt (wie es bei uns zählt)</td><td class=r>"
                 f"{eu(z.kosten.summe)}</td></tr><tr><td>davon Bau + Nebenkosten (Instandhaltung)</td><td class=r>"
                 f"{eu(z.kosten.instandhaltung)}</td></tr><tr><td>davon Möbel + Aufbau</td><td class=r>{eu(z.kosten.investition)}"
                 f"</td></tr></table>")
    # 6 Szenarien
    sz = "".join(f"<tr><td>{e(s.titel)}</td><td class=r>{s.zimmer}</td><td class=r>{s.anteil:.0f} %</td>"
                 f"<td class=r>{eu(s.summe('summe'))}</td><td class=r>{eu(s.summe('summe') / s.zimmer) if s.zimmer else '–'}</td>"
                 f"<td class=r>{'–' if s.zyklus is None else f'{s.zyklus:g}'}</td><td class=r>{s.summe('sperr'):g}</td></tr>"
                 f"<tr><td colspan=7 class=s>{e(s.deutung)}</td></tr>" for s in c.get("strategien") or [])
    # 7 Kennzahlen
    kz = "".join(f"<tr><td>{e(k.titel)}</td><td class=r><b>{e(k.wert)}</b></td><td class=s>{e(k.unter)}"
                 f"{(' · Quelle: ' + e(k.quelle)) if k.quelle else ''}</td></tr>" for k in c.get("kz") or [])
    luecken_ = "".join(f"<li>{e(t)} – braucht: {e(b)}</li>" for t, b in c.get("luecken") or [])
    ent = "".join(f"<li>{e(t)}</li>" for t in c.get("entscheidungen") or []) or "<li>Keine.</li>"
    g = c.get("guete")
    annahmen = (f"Preisstand {p['preisstand']}, +{p['preis_pct']} % Preissteigerung je Jahr · Nebenkosten {p['neben_pct']} % "
                f"vom Bau · Puffer {p['puffer_pct']} % · Vorsteuerquote {p['vorsteuer_pct']} % (0 % = die Umsatzsteuer ist "
                f"voll Kosten) · Einzelzimmer: Bau anteilig aus dem Etagenangebot + {p.get('einzel_aufschlag_pct')} % · "
                f"Belegungsstopp {p['vorlauf_tage']} Tage vor Baubeginn · Bauzeit je Etage "
                + ", ".join(f"Haus {h}: {p['kosten'][h].get('dauer_tage', 30)} Tage" for h in p["haeuser"])
                + f" · Einzelzimmer {p.get('zimmer_tage')} Tage, Möbeltausch {p.get('moebel_tage')} Tage Leerstand.")
    glossar = [
        ("Bedarf (Punkte)", "Je Zimmer: „Renovierung nötig“ 4, seit über 15 Jahren nicht renoviert 2, Zustandsnote 4/5 der "
                            "Etage +2/+4, offene Mängel 0,5–1,5, in den letzten 5 Jahren renoviert −3. Nur Möbel deckt die "
                            "Hälfte, weil Wände und Böden bleiben."),
        ("Belegungsstopp", "Ab diesem Tag wird niemand mehr neu in die Etage geplant, damit sie zum Baubeginn leer ist."),
        ("Ausweich", "Für jede Person, die im Bauzeitraum dort wohnt oder anreist, wird ein passendes freies Zimmer in allen "
                     "Häusern gesucht – nach denselben Regeln wie beim Zuteilen."),
        ("Warnschwelle", "95 % der Kapazität. Die obere Prognose-Spanne darf sie im Baumonat nicht erreichen; die Kapazität "
                         "zählt dabei ohne die gesperrten Zimmer."),
        ("80-%-Spanne", "Bereich, in dem die Belegung nach den bisherigen Prognosefehlern meist liegt – kein Versprechen."),
        ("Gleichwertig", "Zwei Monate unterscheiden sich weniger als die Unsicherheit der Prognose; dann ist die Wahl frei."),
        ("Sperr-Zimmermonate", "Zimmer × Monate, die wegen Bauarbeiten nicht belegt werden können."),
        ("Zyklus", "Bei gleichem Tempo ist jedes Zimmer etwa alle N Jahre einmal dran."),
        ("Vorsteuerquote", "Anteil der Umsatzsteuer, den die Einrichtung zurückbekommt. 0 % = brutto zählt."),
    ]
    gl = "".join(f"<tr><td><b>{e(a)}</b></td><td>{e(b)}</td></tr>" for a, b in glossar)
    return f"""<!doctype html><html lang="de"><head><meta charset="utf-8"><title>Entscheidungsvorlage Renovierung {jahr}</title>
<style>@page {{ size: A4; margin: 14mm 14mm 16mm }} body {{ font: 10.5px/1.45 'Segoe UI', sans-serif; color: #1d1d1d; margin: 0 }}
h1 {{ font-size: 18px; margin: 0 }} h2 {{ font-size: 13px; margin: 16px 0 4px; border-bottom: 1.5px solid #3b6ea5; padding-bottom: 2px }}
h3 {{ font-size: 11px; margin: 8px 0 2px }} .s {{ color: #555; font-size: 9.5px }} .kopf {{ color: #555; margin-bottom: 8px }}
table {{ border-collapse: collapse; width: 100%; margin: 4px 0 }} td, th {{ border-bottom: 1px solid #e2e2e2; padding: 3px 4px;
text-align: left; vertical-align: top }} th {{ color: #444; font-weight: 600; background: #f3f5f8 }} .r {{ text-align: right; white-space: nowrap }}
tr.empf td {{ background: #eef4fb; font-weight: 600 }} tr.sum td {{ font-weight: 700; border-top: 1.5px solid #888 }}
.erkl {{ background: #f6f6f2; border-left: 3px solid #b9a24a; padding: 4px 8px; margin: 4px 0; font-size: 9.5px }}
.box {{ border: 1.5px solid #3b6ea5; border-radius: 6px; padding: 6px 10px; margin: 6px 0 }}
.beschluss td {{ border: 1px solid #bbb; padding: 8px }} .seite {{ page-break-before: always }} ul {{ margin: 2px 0; padding-left: 16px }}
.leg span {{ margin-right: 12px }}</style></head><body>
<h1>Entscheidungsvorlage: Zimmerrenovierung {jahr} · {e(c.get('standort', ''))}</h1>
<div class="kopf">Stand {heute:%d.%m.%Y} · erstellt mit INNternat · unverbindliche Planung, keine Buchung</div>
<h2>1. Worum es geht</h2><p>{e(worum)}</p>
<h2>2. Empfehlung und Beschluss</h2><div class="box">{empfehlung}</div>{beschluss}
{erkl("Empfohlen wird die Variante, die den meisten erfassten Bedarf deckt; bei Gleichstand die mit mehr Zimmern, dann die günstigere. Nur Möbel zählt halb, weil Wände und Böden bleiben.")}
<h2>3. Die Varianten im Vergleich</h2><table><tr><th>Variante</th><th class=r>Zimmer</th><th class=r>Bedarf</th><th class=r>Bau</th>
<th class=r>Möbel</th><th class=r>Gesamt</th><th class=r>Sperr-Zi.-Mon.</th></tr>{vz}</table>
{erkl("Alle Varianten nutzen dieselben Preise und Budgets. „Bedarf“ = gedeckte Punkte (siehe Glossar). „Sperr-Zimmermonate“ zeigt, wie viel Belegungskapazität die Bauarbeiten kosten. Einzelzimmer-Bau ist aus dem Etagenangebot geschätzt – vor einer Beauftragung ein eigenes Angebot einholen.")}
<h2>4. Zeitplan {jahr}</h2><table><tr><th>Maßnahme</th><th>Status</th><th>Belegungsstopp ab</th><th>Bauzeit</th><th class=r>Zi.</th>
<th>Hinweise</th><th class=r>Kosten</th></tr>{zp_}</table>
{erkl("Termine sind so gewählt, dass (1) alle Betroffenen ein passendes Ausweichzimmer haben, (2) die Belegung im Baumonat unter der Warnschwelle bleibt, (3) möglichst wenige umziehen müssen. Einzelzimmer werden in den ersten Leerstand gelegt, der lang genug ist. Zwei Etagen liegen nie im selben Monat.")}
<h2 class="seite">5. Wie die Kosten zustande kommen</h2>{herl or '<p>Keine Maßnahme im Plan.</p>'}
{erkl("Ausgangspunkt sind die eingelesenen Angebote (netto). Darauf kommen die Preissteigerung bis zum Baujahr, Nebenkosten, Möbel und Aufbau je Zimmer, ein Puffer für Unvorhergesehenes und – je nach Vorsteuerquote – die Umsatzsteuer. Darum liegt die Summe über dem reinen Maler-/Bodenangebot.")}
<h2>6. Belegung und Kapazität</h2>{_svg_linie(c["li"])}
<div class="leg s"><span>━ Ist</span><span style="color:#3b6ea5">╍ Prognose mit 80-%-Spanne</span><span style="color:#999">┈ Vorjahr</span>
<span style="color:#b33">━ Kapazität minus Baustellen</span></div>
<p>{e(g.satz if g else '')} {e(g.hinweis if g else '')}</p>
{erkl("Die rote Linie knickt dort ein, wo Zimmer wegen Bauarbeiten fehlen. Liegt die blaue Spanne darüber oder nahe dran, wird es eng. Ab dem 13. Monat ist die Prognose nur fortgeschrieben und unsicherer.")}
<h2>7. Szenarien über {len((c.get('strategien') or [None])[0].jahre) if c.get('strategien') else 5} Jahre</h2>
<table><tr><th>Strategie</th><th class=r>Zimmer</th><th class=r>Bestand</th><th class=r>Kosten</th><th class=r>je Zimmer</th>
<th class=r>Zyklus (J.)</th><th class=r>Sperr-Zi.-Mon.</th></tr>{sz}</table>
{erkl("Jede Strategie wird Jahr für Jahr durchgerechnet; jede Etage bzw. jedes Zimmer zählt höchstens einmal, Preise steigen je Jahr. „Bestand“ = Anteil der Zimmer in Haus 2 und 6, die in dieser Zeit erneuert werden. „Ein Jahr warten“ zeigt, was Aufschieben kostet.")}
<h2 class="seite">8. Kennzahlen</h2><table>{kz}</table>
{erkl("Nur aus vorhandenen Daten gerechnet. Erlös und Leerstandskosten erscheinen, sobald Tagessätze eingetragen sind; Abweisungen, sobald sie gezählt werden.")}
{('<h3>Was noch fehlt</h3><ul>' + luecken_ + '</ul>') if luecken_ else ''}
<h2>9. Offene Punkte</h2><ul>{ent}</ul>
<h2>10. Annahmen</h2><p>{e(annahmen)}</p>
<h2>11. Begriffe</h2><table>{gl}</table>
</body></html>"""
