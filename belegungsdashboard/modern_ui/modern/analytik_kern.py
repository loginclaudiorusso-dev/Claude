"""Executive Analytics – reine Datenschicht (ohne NiceGUI) für die Prognose-Ansicht.

Alle Zahlen stammen aus dem Datenstand des Hauptprogramms (Pivot, Listen, Kapazitäten, Prognosemodelle):

* **Ist** – Ø belegte Plätze eines vergangenen Monats (Pivot + Listen).
* **laufend** – aktueller Monat: Ist der bisherigen Tage + Prognose der Resttage (unvollständig).
* **Erwartet / 80 % / 95 %** – Prognose inkl. Verträgen; Bänder aus den Backtest-Fehlern je Horizont.
* **Gebucht** (im Hauptprogramm „gesichert“) – bereits bekannter Bestand (Teilnehmende mit geplantem Ende +
  Verträge), Ø der künftigen Tage des Monats. Die Prognose fällt nie darunter → Untergrenze.
* **Reserve** – Kapazität − Erwartet; **Reserve ungünstig** – Kapazität − obere 80 %-Grenze.
* **Risiko** – Ampel des Hauptprogramms auf die obere 80 %-Grenze (≥ 70 % knapp, ≥ 85 % kritisch, > 100 % über).

Nichts wird erfunden: Fehlt eine Grundlage (z. B. Vorjahreswert, Backtest-Verlauf für „Gesamt“), sagt der Text das.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta

from belegung import konfig

from . import auswertung_kern as ak

# Standortfarben wie im bisherigen Programm (hell / dunkel) – in allen Diagrammen gleich
STANDORT_FARBEN = {
    False: {"BFW BP": "#1A9C9F", "BFW GS": "#CC7A22", "BFW WE": "#9085E9", konfig.GESAMT: "#C9D1D9"},
    True: {"BFW BP": "#00908F", "BFW GS": "#D4700A", "BFW WE": "#5646C0", konfig.GESAMT: "#344054"},
}

# Status-Aufteilung: UWTler (Deep Blue), Mieter (Slate), übrige Belegung neutral – hell / dunkel
STATUS_FARBEN = {
    False: {"UWT": "#4F6FE8", "Mieter": "#A3B1C6", "uebrige": "#6B7280"},
    True: {"UWT": "#1E3A8A", "Mieter": "#64748B", "uebrige": "#CBD5E1"},
}
STATUS_NAMEN = {"UWT": "UWTler", "Mieter": "Mieter", "uebrige": "Teilnehmende & Sonstige"}


def _z(x: float | None) -> str:
    if x is None:
        return "–"
    return f"{x:,.0f}".replace(",", ".").replace("-", "−")


def _z1(x: float | None) -> str:
    """Eine Nachkommastelle unter 10 (Prognosefehler), sonst ganze Zahl."""
    if x is None:
        return "–"
    return f"{x:.1f}".replace(".", ",") if abs(x) < 10 else _z(x)


def _p(x: float | None) -> str:
    return "–" if x is None else f"{round(100 * x)} %"


def _monat_minus(m: date, n: int) -> date:
    j, mo = divmod(m.month - 1 - n, 12)
    return date(m.year + j, mo + 1, 1)


# ---------------------------------------------------------------------------------------
# Ebene A: KPI-Karten
# ---------------------------------------------------------------------------------------

@dataclass
class Kpi:
    schluessel: str
    titel: str
    wert: str
    einheit: str
    bezug: str                    # Bezugszeitraum, z. B. „Stichtag 25.10.2026“ / „Nov 2026 (Prognose)“
    vergleich: str = ""           # z. B. „+12 ggü. Vorjahr (gleicher Wochentag)“
    richtung: int = 0             # +1 / −1 / 0 (für Pfeil; keine Wertung)
    stufe: str = ""               # ok | warn | krit | neutral
    hinweis: str = ""             # Tooltip: wie gerechnet


@dataclass
class Executive:
    kpis: list[Kpi]
    erkenntnisse: list[tuple[str, str]]          # (Fakt | Prognose | Einschätzung | Hinweis, Text)
    zielmonat: date | None
    stichtag: date
    kapazitaet: int


def _stufe(anteil: float | None) -> str:
    st, _t = konfig.ampel_stufe(anteil)
    return {"ok": "ok", "knapp": "warn", "kritisch": "krit", "ueber": "krit"}.get(st, "neutral")


def executive(ds, standort: str, brutto: bool, pg: ak.Prognose, kap: int | None = None, offset: float = 0.0,
              horizont: int = 12) -> Executive:
    """KPI-Karten und priorisierte Erkenntnisse – aus echten Daten; ``kap``/``offset`` nur für ein Szenario."""
    kap_echt = pg.kapazitaet or 0
    kap = kap_echt if kap is None else kap
    szen = kap != kap_echt or bool(offset)
    zs = ak.szenario(pg, kap, offset)
    kuenftig = [z for z in zs if z.art != "ist"][:horizont]
    voll = [z for z in kuenftig if z.art == "prognose"]
    ziel = voll[0] if voll else (kuenftig[0] if kuenftig else None)
    ist_je_monat = {z.monat: z.ist for z in pg.zeilen if z.art == "ist" and z.ist is not None}
    stich = ds.stichtag
    kpis: list[Kpi] = []
    er: list[tuple[str, str]] = []

    # 1 Aktuelle Belegung am Stichtag (Fakt) – Vergleich: gleicher Wochentag vor 52 Wochen
    lage = ds.aufschluesselung(standort, stich, brutto)
    vorjahr_tag = stich - timedelta(days=364)
    vj = None
    if vorjahr_tag >= ds.erster_tag:
        try:
            vj = float(ds.verlauf(standort, vorjahr_tag, vorjahr_tag, brutto)["wert"].iloc[0])
        except (IndexError, KeyError, ValueError):
            vj = None
    d = (lage.belegt - vj) if vj is not None else None
    kpis.append(Kpi("aktuell", "Aktuelle Belegung", _z(lage.belegt), "Plätze",
                    f"Stichtag {stich:%d.%m.%Y}" + (f" · {_p(lage.belegt / kap_echt)} von {_z(kap_echt)}" if kap_echt else ""),
                    (f"{'+' if d >= 0 else '−'}{_z(abs(d))} ggü. {vorjahr_tag:%d.%m.%Y} (gleicher Wochentag)" if d is not None
                     else "kein Vorjahreswert"), (d > 0) - (d < 0) if d is not None else 0,
                    _stufe(lage.belegt / kap_echt if kap_echt else None),
                    "Belegte Plätze am letzten Tag mit Ist-Daten (Pivot + Listen)."))

    # 2 Prognose Zielmonat (nächster voller Monat) – Vergleich: Ist im Vorjahresmonat
    if ziel:
        vjm = ist_je_monat.get(_monat_minus(ziel.monat, 12))
        d2 = (ziel.erwartet - vjm) if vjm is not None else None
        kpis.append(Kpi("ziel", "Prognose Belegung", _z(ziel.erwartet), "Plätze Ø",
                        f"{ak.monat_text(ziel.monat)} · 80 %: {_z(ziel.lo80)}–{_z(ziel.hi80)}"
                        + (f" · {_p(ziel.erwartet / kap)}" if kap else ""),
                        (f"{'+' if d2 >= 0 else '−'}{_z(abs(d2))} ggü. Ist {ak.monat_text(_monat_minus(ziel.monat, 12))}"
                         if d2 is not None else "kein Vorjahresmonat in den Daten"), (d2 > 0) - (d2 < 0) if d2 else 0,
                        _stufe(ziel.hi80 / kap if kap else None),
                        "Erwarteter Ø-Bestand des nächsten vollständigen Monats (Modell + Verträge, nie unter gebucht)."))

    # 3 Reserve im Zielmonat + knappster Monat
    if ziel and kap:
        knapp = min(kuenftig, key=lambda z: z.reserve)
        kpis.append(Kpi("reserve", "Freie Reserve", _z(ziel.reserve), "Plätze",
                        f"{ak.monat_text(ziel.monat)} (erwartet) · ungünstig {_z(kap - ziel.hi80)}",
                        f"am knappsten {ak.monat_text(knapp.monat)}: {_z(knapp.reserve)}", 0,
                        "krit" if knapp.reserve < 0 else _stufe(1 - knapp.reserve / kap) if kap else "neutral",
                        "Kapazität − erwartete Belegung; „ungünstig“ = Kapazität − obere 80 %-Grenze."))

    # 4 Kapazitätsrisiko (Einschätzung nach Ampel auf obere 80 %-Grenze)
    if kap:
        risk = [z for z in kuenftig if z.stufe in ("kritisch", "ueber")]
        knapp_m = [z for z in kuenftig if z.stufe == "knapp"]
        if risk:
            kpis.append(Kpi("risiko", "Kapazitätsrisiko", str(len(risk)), f"von {len(kuenftig)} Monaten",
                            f"ab {ak.monat_text(risk[0].monat)} ≥ {round(100 * konfig.AMPEL_ROT)} % (obere 80 %)",
                            f"höchstens {_p(max(z.hi80 for z in risk) / kap)}", 1, "krit",
                            "Monate, deren obere 80 %-Grenze die Schwelle „kritisch“ erreicht oder die Kapazität übersteigt."))
        else:
            kpis.append(Kpi("risiko", "Kapazitätsrisiko", "0", f"von {len(kuenftig)} Monaten",
                            f"nächste {len(kuenftig)} Monate unter {round(100 * konfig.AMPEL_ROT)} % (obere 80 %)",
                            f"{len(knapp_m)} Monat(e) knapp (≥ {round(100 * konfig.AMPEL_GELB)} %)" if knapp_m else "durchgehend Reserve",
                            0, "warn" if knapp_m else "ok",
                            "Kein Monat erreicht mit der oberen 80 %-Grenze die Schwelle „kritisch“."))

    # 5 Prognosegüte (Backtest)
    if pg.mae_1m is not None or pg.abdeckung80 is not None:
        kpis.append(Kpi("guete", "Prognosegüte", f"± {_z1(pg.mae_1m)}" if pg.mae_1m is not None else "–", "Plätze Ø-Fehler",
                        "Backtest, 1 Monat voraus" + (f" · bis 12 Monate: ± {_z1(pg.mae)}" if pg.mae is not None else ""),
                        f"{_p(pg.abdeckung80)} der Fälle im 80 %-Band (Soll 80 %)" if pg.abdeckung80 is not None else "",
                        0, ("ok" if pg.abdeckung80 >= .7 else "warn") if pg.abdeckung80 is not None else "neutral",
                        "Blind gerechnete Prognosen der Vergangenheit mit den damaligen Daten, verglichen mit dem Ist."))
    else:
        kpis.append(Kpi("guete", "Prognosegüte", "–", "", "kein Backtest vorhanden", "", 0, "neutral"))

    # Ebene B: Erkenntnisse – Fakt / Prognose / Einschätzung / Hinweis
    if vj is not None:
        er.append(("Fakt", f"Am {stich:%d.%m.%Y} waren {_z(lage.belegt)} Plätze belegt"
                           + (f" ({_p(lage.belegt / kap_echt)} der Kapazität)" if kap_echt else "")
                           + f", {'+' if d >= 0 else '−'}{_z(abs(d))} gegenüber dem gleichen Wochentag im Vorjahr."))
    if kuenftig:
        spitze = max(kuenftig, key=lambda z: z.erwartet)
        er.append(("Prognose", f"Höchststand voraussichtlich {ak.monat_text(spitze.monat)} mit {_z(spitze.erwartet)} Plätzen "
                               f"(80 %: {_z(spitze.lo80)}–{_z(spitze.hi80)})" + (f", {_p(spitze.erwartet / kap)} Auslastung." if kap else ".")))
        if kap:
            weit = max(kuenftig, key=lambda z: z.reserve)
            er.append(("Prognose", f"Größte freie Reserve {ak.monat_text(weit.monat)}: {_z(weit.reserve)} Plätze."))
            risk = [z for z in kuenftig if z.stufe in ("kritisch", "ueber")]
            if risk:
                er.append(("Einschätzung", f"Kapazitätsrisiko in {len(risk)} Monat(en), zuerst {ak.monat_text(risk[0].monat)} "
                                           f"(obere 80 %-Grenze {_z(risk[0].hi80)} von {_z(kap)})."))
            else:
                er.append(("Einschätzung", f"Kein Kapazitätsrisiko in den nächsten {len(kuenftig)} Monaten – die obere "
                                           f"80 %-Grenze bleibt unter {round(100 * konfig.AMPEL_ROT)} %."))
        # Vorjahr: Prognose der nächsten Monate vs. Ist derselben Monate im Vorjahr (nur wo beides vorhanden)
        paare = [(z.erwartet, ist_je_monat[_monat_minus(z.monat, 12)]) for z in kuenftig
                 if _monat_minus(z.monat, 12) in ist_je_monat]
        if len(paare) >= 3:
            p = sum(a for a, _b in paare) / len(paare)
            v = sum(b for _a, b in paare) / len(paare)
            er.append(("Prognose", f"Ø der nächsten {len(paare)} Monate {_z(p)} Plätze – "
                                   f"{'+' if p >= v else '−'}{_z(abs(p - v))} ({'+' if p >= v else '−'}{abs(round(100 * (p - v) / v)) if v else 0} %) "
                                   "gegenüber denselben Monaten im Vorjahr (Ist)."))
    if pg.rueckblick:
        groesste = max(pg.rueckblick, key=lambda r: abs(r[2] - r[1]))
        abw = abs(groesste[2] - groesste[1])
        if pg.mae_1m and abw > max(2 * pg.mae_1m, 3.0, 0.05 * groesste[1]):
            er.append(("Fakt", f"Auffällige Abweichung im Backtest: {ak.monat_text(groesste[0])} "
                               f"Prognose {_z(groesste[2])} statt Ist {_z(groesste[1])}."))
    elif standort == konfig.GESAMT:
        er.append(("Hinweis", "Backtest-Verlauf je Monat gibt es nur je Standort – oben einen Standort wählen."))
    tage = (date.today() - stich).days
    if tage > 7:
        er.append(("Hinweis", f"Ist-Daten reichen bis {stich:%d.%m.%Y} ({tage} Tage alt) – danach ist alles Prognose."))
    if szen:
        er.insert(0, ("Hinweis", "Szenario aktiv – Werte mit angenommener Kapazität "
                                 f"{_z(kap)}" + (f" und Auslastung {offset:+g} %" if offset else "") + ", nicht die echten Daten."))
    return Executive(kpis, er, ziel.monat if ziel else None, stich, kap)


# ---------------------------------------------------------------------------------------
# Standortvergleich
# ---------------------------------------------------------------------------------------

@dataclass
class StandortZeile:
    standort: str
    name: str
    belegt: float
    kapazitaet: int
    auslastung: float | None
    reserve: float | None
    spitze_monat: date | None
    spitze_erwartet: float | None
    spitze_hi80: float | None
    spitze_quote: float | None
    mae_1m: float | None
    abdeckung80: float | None
    verlauf: list = field(default_factory=list)   # (Monat, Wert, ist?) – für das Vergleichsdiagramm


def standort_vergleich(ds, brutto: bool, horizont: int = 12, zurueck: int = 12) -> list[StandortZeile]:
    erg = []
    for s in konfig.STANDORTE:
        lage = ds.aufschluesselung(s, ds.stichtag, brutto)
        kap = ds.kapazitaet(s, brutto)
        pg = ak.prognose(ds, s, brutto, zurueck, horizont)
        kuenftig = [z for z in (pg.zeilen if pg else []) if z.art != "ist"][:horizont]
        sp = max(kuenftig, key=lambda z: z.erwartet) if kuenftig else None
        erg.append(StandortZeile(
            s, konfig.STANDORT_LABEL[s], lage.belegt, kap, lage.belegt / kap if kap else None,
            (kap - lage.belegt) if kap else None, sp.monat if sp else None, sp.erwartet if sp else None,
            sp.hi80 if sp else None, (sp.hi80 / kap) if sp and kap else None,
            pg.mae_1m if pg else None, pg.abdeckung80 if pg else None,
            [(z.monat, z.ist if z.art == "ist" and z.ist is not None else z.erwartet, z.art == "ist")
             for z in (pg.zeilen if pg else [])]))
    return erg


# ---------------------------------------------------------------------------------------
# Szenario: Ausgang vs. Annahme (getrennte Rechnung – verändert keine Daten)
# ---------------------------------------------------------------------------------------

@dataclass
class SzVergleich:
    titel: str
    ausgang: str
    szenario: str
    schlechter: bool


def szenario_vergleich(pg: ak.Prognose, kap: int, offset: float, horizont: int = 12) -> list[SzVergleich]:
    a = [z for z in ak.szenario(pg, pg.kapazitaet or 0, 0) if z.art != "ist"][:horizont]
    b = [z for z in ak.szenario(pg, kap, offset) if z.art != "ist"][:horizont]
    if not a or not b:
        return []
    sa, sb = max(a, key=lambda z: z.erwartet), max(b, key=lambda z: z.erwartet)
    ra, rb = min(a, key=lambda z: z.reserve or 0), min(b, key=lambda z: z.reserve or 0)
    ea = sum(1 for z in a if z.stufe in ("kritisch", "ueber"))
    eb = sum(1 for z in b if z.stufe in ("kritisch", "ueber"))
    k0 = pg.kapazitaet or 0
    return [
        SzVergleich("Kapazität", f"{_z(k0)} Plätze", f"{_z(kap)} Plätze", kap < k0),
        SzVergleich("Auslastungsannahme", "Prognose", f"{offset:+g} %" if offset else "Prognose", offset > 0),
        SzVergleich("Höchststand (erwartet)", f"{_z(sa.erwartet)} · {ak.monat_text(sa.monat)}",
                    f"{_z(sb.erwartet)} · {ak.monat_text(sb.monat)}", sb.erwartet > sa.erwartet),
        SzVergleich("Kleinste Reserve", f"{_z(ra.reserve)} · {ak.monat_text(ra.monat)}" if k0 else "–",
                    f"{_z(rb.reserve)} · {ak.monat_text(rb.monat)}" if kap else "–", (rb.reserve or 0) < (ra.reserve or 0)),
        SzVergleich("Monate mit Kapazitätsrisiko", f"{ea} von {len(a)}", f"{eb} von {len(b)}", eb > ea),
    ]


# ---------------------------------------------------------------------------------------
# Vorjahresvergleich: aktueller 12-Monats-Zeitraum vs. dieselben Kalendermonate ein Jahr früher
# ---------------------------------------------------------------------------------------

@dataclass
class Vorjahr:
    monate: list[date]                 # aktueller Zeitraum (letzte 6 Ist-Monate + nächste 6 Monate)
    aktuell: list[float | None]
    aktuell_ist: list[bool]
    vorjahr: list[float | None]
    vorvorjahr: list[float | None]


def vorjahr(pg: ak.Prognose, zurueck: int = 6, vor: int = 6) -> Vorjahr:
    alle = {z.monat: z for z in pg.zeilen}
    ist = {z.monat: z.ist for z in pg.zeilen if z.art == "ist" and z.ist is not None}
    erste_prog = next((z.monat for z in pg.zeilen if z.art != "ist"), None)
    if erste_prog is None:
        return Vorjahr([], [], [], [], [])
    monate = [_monat_minus(erste_prog, n) for n in range(zurueck, -vor, -1)]
    akt, akt_ist = [], []
    for m in monate:
        z = alle.get(m)
        if z is None:
            akt.append(None)
            akt_ist.append(False)
        elif z.art == "ist":
            akt.append(z.ist)
            akt_ist.append(True)
        else:
            akt.append(z.erwartet)
            akt_ist.append(False)
    return Vorjahr(monate, akt, akt_ist, [ist.get(_monat_minus(m, 12)) for m in monate],
                   [ist.get(_monat_minus(m, 24)) for m in monate])


# ---------------------------------------------------------------------------------------
# Export: kompakte Executive Summary (Druckansicht / PDF)
# ---------------------------------------------------------------------------------------

def summary_html(ex: Executive, pg: ak.Prognose, standort: str, brutto: bool, kap: int, offset: float,
                 vergleich: list[StandortZeile] | None = None) -> str:
    from html import escape

    zs = [z for z in ak.szenario(pg, kap, offset) if z.art != "ist"][:12]
    kp = "".join(f"<div class='k'><div class='t'>{escape(k.titel)}</div><div class='w'>{escape(k.wert)} "
                 f"<span>{escape(k.einheit)}</span></div><div class='b'>{escape(k.bezug)}</div>"
                 f"<div class='v'>{escape(k.vergleich)}</div></div>" for k in ex.kpis)
    er = "".join(f"<li><b>{escape(a)}:</b> {escape(t)}</li>" for a, t in ex.erkenntnisse
                 if "oben einen Standort" not in t)          # Bedienhinweis gehört nicht ins Dokument
    rows = "".join(f"<tr><td>{ak.monat_text(z.monat)}{' (laufend)' if z.art == 'laufend' else ''}</td>"
                   f"<td>{_z(z.erwartet)}</td><td>{_z(z.lo80)}–{_z(z.hi80)}</td><td>{_z(z.lo95)}–{_z(z.hi95)}</td>"
                   f"<td>{_z(z.gesichert)}</td><td>{_z(z.reserve)}</td><td>{escape(z.text)}</td></tr>" for z in zs)
    sv = ""
    if vergleich:
        sv = ("<h2>Standorte</h2><table><tr><th>Standort</th><th>Belegt</th><th>Kapazität</th><th>Auslastung</th>"
              "<th>Spitze 12 Monate (erwartet)</th><th>Ø-Fehler 1 Monat</th></tr>"
              + "".join(f"<tr><td>{escape(v.name)}</td><td>{_z(v.belegt)}</td><td>{_z(v.kapazitaet)}</td><td>{_p(v.auslastung)}</td>"
                        f"<td>{_z(v.spitze_erwartet)} ({ak.monat_text(v.spitze_monat) if v.spitze_monat else '–'})</td>"
                        f"<td>± {_z1(v.mae_1m)}</td></tr>" for v in vergleich) + "</table>")
    titel = f"Belegungsprognose {konfig.STANDORT_LABEL.get(standort, standort)} · {'Brutto' if brutto else 'Netto'}"
    szen = (f"<p class='sz'>Szenario: Kapazität {_z(kap)}" + (f", Auslastung {offset:+g} %" if offset else "")
            + " – nicht die echten Werte.</p>") if (kap != (pg.kapazitaet or 0) or offset) else ""
    return f"""<!doctype html><html lang="de"><meta charset="utf-8"><title>{escape(titel)}</title>
<style>body{{font:13px "Segoe UI",system-ui,sans-serif;color:#14213d;margin:28px 34px}}h1{{font-size:20px;margin:0}}
h2{{font-size:14px;margin:22px 0 6px}}.u{{color:#5b6880;margin:2px 0 16px}}.ks{{display:grid;grid-template-columns:repeat(5,1fr);gap:10px}}
.k{{border:1px solid #dde3ec;border-radius:8px;padding:10px}}.t{{color:#5b6880;font-size:11px}}.w{{font-size:20px;font-weight:600}}
.w span{{font-size:11px;color:#5b6880;font-weight:400}}.b,.v{{font-size:11px;color:#3b4a63}}ul{{padding-left:18px;line-height:1.55}}
table{{border-collapse:collapse;width:100%;font-variant-numeric:tabular-nums}}th,td{{text-align:left;padding:4px 8px;border-bottom:1px solid #dde3ec;font-size:12px}}
th{{color:#5b6880;font-weight:600}}.sz{{background:#fffaeb;border:1px solid #fedf89;padding:6px 10px;border-radius:6px}}
@media print{{body{{margin:12mm}}}}</style>
<h1>{escape(titel)}</h1><p class="u">Ist bis {ex.stichtag:%d.%m.%Y}, danach Prognose · Kapazität {_z(kap)} Plätze ·
Modell: {escape(pg.modell or '–')} · erstellt {date.today():%d.%m.%Y}</p>{szen}
<div class="ks">{kp}</div><h2>Erkenntnisse</h2><ul>{er}</ul>
<h2>Nächste 12 Monate</h2><table><tr><th>Monat</th><th>Erwartet</th><th>80 %-Band</th><th>95 %-Band</th><th>Gebucht</th>
<th>Reserve</th><th>Einschätzung</th></tr>{rows}</table>{sv}
<p class="u" style="margin-top:14px">Erwartet = Ø belegte Plätze (Modell + Verträge, nie unter dem gebuchten Bestand) · Gebucht =
bereits bekannter Bestand · Reserve = Kapazität − Erwartet · Einschätzung nach oberer 80 %-Grenze (≥ 70 % knapp, ≥ 85 % kritisch).</p>
</html>"""


# ---------------------------------------------------------------------------------------
# Status-Aufteilung: UWTler und Mieter gegenüber der übrigen Belegung
# ---------------------------------------------------------------------------------------

@dataclass
class StatusMonat:
    monat: date
    art: str                 # ist | laufend | prognose
    uwt: float               # Ø Plätze UWT (Ist bzw. gebucht – UWT-Blöcke sind vertraglich fest)
    mieter: float            # Ø Plätze Mieter (Ist bzw. laufende Mietverträge)
    uebrige: float           # Gesamt − UWT − Mieter (Teilnehmende, Gäste, DRK …; in der Zukunft: Prognose)
    gesamt: float            # Ist bzw. erwartete Gesamtbelegung (wie im Graph)


def status_monate(ds, standort: str, brutto: bool, pg: ak.Prognose) -> list[StatusMonat]:
    """Ø-Plätze je Monat nach Status. UWT und Mieter stammen aus den Listen (Ist bzw. bereits gebucht), die übrige
    Belegung ist der Rest bis zur Gesamtzahl – die Unsicherheit der Prognose liegt damit allein bei den übrigen."""
    import pandas as pd

    if not pg or not pg.zeilen:
        return []
    von = pg.zeilen[0].monat
    bis = (pd.Timestamp(pg.zeilen[-1].monat) + pd.offsets.MonthEnd(0)).date()
    kat = ds.kategorien(standort, von, bis, brutto)
    mittel = kat.groupby(kat.index.to_period("M")).mean()

    def wert(spalte: str, periode) -> float:
        if spalte not in mittel.columns or periode not in mittel.index:
            return 0.0
        return float(mittel.at[periode, spalte])
    erg = []
    for z in pg.zeilen:
        p = pd.Period(z.monat, "M")
        gesamt = z.ist if z.art == "ist" and z.ist is not None else z.erwartet
        uwt, mieter = wert("UWT", p), wert("Mieter", p)
        erg.append(StatusMonat(z.monat, z.art, uwt, mieter, max(gesamt - uwt - mieter, 0.0), gesamt))
    return erg


@dataclass
class StatusLage:
    """Kompakte Aufteilung für einen Standort: heute und die nächsten Monate."""
    stichtag: date
    kapazitaet: int
    heute: dict              # UWT / Mieter / uebrige / frei → Plätze am Stichtag
    monate: list[StatusMonat]   # nächste Monate (laufend + Prognose)
    fest_max: float          # höchste Summe UWT + Mieter in diesen Monaten
    fest_max_monat: date | None
    saetze: list[str]        # Aussagen (aus den Zahlen, nichts geschätzt)


def status_lage(ds, standort: str, brutto: bool, sm: list[StatusMonat], monate: int = 6) -> StatusLage:
    lage = ds.aufschluesselung(standort, ds.stichtag, brutto)
    kap = lage.kapazitaet
    uwt, mieter = lage.teile.get("UWT", 0.0), lage.teile.get("Mieter", 0.0)
    heute = {"UWT": uwt, "Mieter": mieter, "uebrige": max(lage.belegt - uwt - mieter, 0.0),
             "frei": max(kap - lage.belegt, 0.0) if kap else 0.0}
    kommend = [m for m in sm if m.art != "ist"][:monate]
    spitze = max(kommend, key=lambda m: m.uwt + m.mieter, default=None)
    saetze = []
    if kap:
        saetze.append(f"Heute binden UWTler {_z(uwt)} und Mieter {_z(mieter)} Plätze – zusammen {_p((uwt + mieter) / kap)} "
                      f"der Kapazität von {_z(kap)}.")
    if spitze is not None and kap:
        saetze.append(f"Fest gebucht (UWT + Mieter) höchstens {_z(spitze.uwt + spitze.mieter)} Plätze im "
                      f"{ak.monat_text(spitze.monat)} ({_p((spitze.uwt + spitze.mieter) / kap)}); für Teilnehmende "
                      f"und Sonstige bleiben dann {_z(kap - spitze.uwt - spitze.mieter)}.")
        eng = [m for m in kommend if m.gesamt > kap * konfig.AMPEL_ROT]
        if eng:
            saetze.append(f"In {len(eng)} Monat(en) liegt die erwartete Gesamtbelegung über {round(100 * konfig.AMPEL_ROT)} % – "
                          f"zuerst {ak.monat_text(eng[0].monat)}; davon UWT + Mieter {_z(eng[0].uwt + eng[0].mieter)}.")
    return StatusLage(ds.stichtag, kap, heute, kommend, (spitze.uwt + spitze.mieter) if spitze else 0.0,
                      spitze.monat if spitze else None, saetze)


def sanierung_plaetze(lage, standort: str) -> int | None:
    """Betten in Zimmern, die ein offener Mangel unbewohnbar macht (Gebäudeplan, nur Goslar). None = keine Grundlage."""
    if lage is None or standort not in ("BFW GS", konfig.GESAMT):
        return None
    zimmer = getattr(lage, "zimmer", {}) or {}
    return sum(zimmer[z].betten for z in (getattr(lage, "unbewohnbar", {}) or {}) if z in zimmer and zimmer[z].aktiv)


# ---------------------------------------------------------------------------------------
# Kontingente: geplante prozentuale Aufteilung der Kapazität (UWT / Mieter / Teilnehmende & Sonstige)
# ---------------------------------------------------------------------------------------

@dataclass
class KZeile:
    monat: date
    art: str
    uwt: float
    mieter: float
    uebrige: float
    k_uwt: float             # Kontingent in Plätzen
    k_mieter: float
    k_uebrige: float
    stufe: dict              # Schlüssel → ok | knapp | ueber  (Belegung gegenüber dem eigenen Kontingent)


def kontingent_vorschlag(sm: list[StatusMonat], kap: int, monate: int = 12) -> dict:
    """Ausgangsvorschlag aus den Daten: höchster gebuchter Anteil von UWT bzw. Mietern an der Kapazität in den nächsten
    Monaten, auf ganze Prozent aufgerundet – so passen die gebuchten Spitzen hinein."""
    import math

    kommend = [m for m in sm if m.art != "ist"][:monate]
    if not kap or not kommend:
        return {"UWT": 0.0, "Mieter": 0.0}
    return {"UWT": float(math.ceil(100 * max(m.uwt for m in kommend) / kap)),
            "Mieter": float(math.ceil(100 * max(m.mieter for m in kommend) / kap))}


def kontingent_pruefung(sm: list[StatusMonat], kap: int, anteile: dict, monate: int = 12) -> list[KZeile]:
    """Je Monat: Belegung je Gruppe gegen ihr Kontingent. knapp = ≥ 90 % des Kontingents, ueber = mehr als das Kontingent."""
    k_u = kap * anteile.get("UWT", 0) / 100
    k_m = kap * anteile.get("Mieter", 0) / 100
    k_r = max(kap - k_u - k_m, 0.0)

    def st(wert: float, grenze: float) -> str:
        if wert > grenze + 0.05:
            return "ueber"
        return "knapp" if grenze and wert >= .9 * grenze else "ok"
    return [KZeile(m.monat, m.art, m.uwt, m.mieter, m.uebrige, k_u, k_m, k_r,
                   {"UWT": st(m.uwt, k_u), "Mieter": st(m.mieter, k_m), "uebrige": st(m.uebrige, k_r)})
            for m in [x for x in sm if x.art != "ist"][:monate]]


def kontingent_saetze(zeilen: list[KZeile], anteile: dict) -> list[str]:
    erg = []
    namen = {"UWT": "UWT", "Mieter": "Mieter", "uebrige": "Teilnehmende & Sonstige"}
    for schl in ("UWT", "Mieter", "uebrige"):
        feld = schl.lower()
        ueber = [z for z in zeilen if z.stufe[schl] == "ueber"]
        if ueber:
            groesst = max(ueber, key=lambda z: getattr(z, feld) - getattr(z, "k_" + feld))
            erg.append(f"{namen[schl]}: Kontingent in {len(ueber)} von {len(zeilen)} Monaten überschritten – am stärksten "
                       f"{ak.monat_text(groesst.monat)} ({_z(getattr(groesst, feld))} statt {_z(getattr(groesst, 'k_' + feld))} Plätze).")
    if not erg and zeilen:
        erg.append(f"Alle Gruppen bleiben in den nächsten {len(zeilen)} Monaten innerhalb ihres Kontingents "
                   f"(UWT {anteile.get('UWT', 0):g} %, Mieter {anteile.get('Mieter', 0):g} %).")
    return erg
