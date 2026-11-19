"""Seite „Steuerung“ (ganz unten in der Seitenleiste): für die Leitung, selten genutzt – Übersicht, Renovierung,
Strategie 5 Jahre, Belegung, Kennzahlen. Gerechnet wird erst beim Öffnen (im Hintergrund).

Daten: ``steuerung_kern`` (Kennzahlen, Prognosegüte, Kernbestand, Entscheidungsvorlage) und ``renovierung_kern``
(Bedarf in Klassen, Kosten mit Herkunft, Varianten, Termine, Strategien).

1.29: Die Renovierungs-Oberfläche liegt in ``steuerung_renovierung_ui`` (nur verschoben).
"""

from __future__ import annotations

from datetime import date

from nicegui import ui

from . import renovierung_kern as rk
from . import seiten, standort_kern
from . import steuerung_kern as sk
from . import vorhaben_kern as vk
from .ui_bausteine import attr, knopf, leer, segmente, tabelle

# 1.29: aufgeteilt – diese Namen liegen jetzt in steuerung_renovierung_ui.py (hier weiter erreichbar)
from .steuerung_renovierung_ui import (  # noqa: F401
    GANZZAHL, HAUS_FELDER, HK_KLASSE, _alle_uebernehmen, _angebot_pruefen, _annahmen, _annahmen_liste, _buendeln,
    _empfehlung_karte, _etage_panel, _etage_waehlen, _etagen_block, _fenster, _gantt, _hk, _monate,
    _platzhalter_banner, _renovierung, _varianten_block, _vorgabe_block, _zeile_panel, _zone, gantt_kosten,
    gantt_text,
)

# 0.46: nach Fragen statt nach Werkzeugen – Cockpit (nur lesen) · Vorhaben (planen) · Zeitplan & Kapazität · Finanzen ·
# Grundlagen. Alte Namen (aus Links anderer Seiten) werden umgeleitet.
ANSICHTEN = {"cockpit": "Cockpit", "vorhaben": "Vorhaben", "zeitplan": "Zeitplan & Kapazität", "finanzen": "Finanzen",
             "grundlagen": "Grundlagen"}
# 1.20: „Cockpit (neu)“ ist jetzt das Cockpit
ALT = {"cockpit_neu": "cockpit", "uebersicht": "cockpit", "renovierung": "vorhaben", "prognose": "zeitplan",
       "szenarien": "finanzen", "kennzahlen": "grundlagen"}


def ansicht(a) -> str:
    v = a.ansicht_von("steuerung", "cockpit")
    v = ALT.get(v, v)
    return v if v in ANSICHTEN else "cockpit"
GOSLAR = "BFW GS"


def _jahr_standard(heute: date) -> int:
    return heute.year + 1 if heute.month >= 10 else heute.year


# ---- Daten (im Hintergrund) -----------------------------------------------------------------

def _prognose(a):
    from . import auswertung_kern as ak

    ds, fehler = ak.datenstand()
    if ds is None:
        return None, fehler
    try:
        return ak.prognose(ds, GOSLAR, bool(getattr(a, "aw_brutto", False)), 36, 36), ""
    except Exception as exc:                 # noqa: BLE001 – Prognose darf die Seite nicht verhindern
        return None, f"Prognose nicht verfügbar: {exc}"


def _abgleich(a, pg) -> list:
    """1.14: Bettenprognose gegen Maßnahmen-Prognose im Internat (nur netto vergleichbar: ohne UWTler und Mieter)."""
    if pg is None or getattr(a, "aw_brutto", False):
        return []
    try:
        from . import massnahmen_kern as mk

        mp = mk.prognose(None, a.heute, 0, 12, internat=True)
        return sk.prognosen_abgleich(pg.zeilen, mp.zeilen if mp else [], 12)
    except Exception:                        # noqa: BLE001 – der Abgleich ist eine Zugabe
        return []


def _platzhalter(p: dict) -> list[str]:
    erg = []
    for h in p["haeuser"]:
        if rk.herkunft(p, h, "bau_etage") == "platzhalter":
            erg.append(f"Haus {h}: kein Bau-Angebot – gerechnet wird mit dem Platzhalter "
                       f"{rk.euro(p['kosten'][h]['bau_etage'])} netto je Etage")
        if not p["kosten"][h].get("moebel_zimmer"):
            erg.append(f"Haus {h}: kein Möbelpreis – Möbel zählen mit 0 €")
    return erg


def daten(a) -> None:
    ansicht_ = ansicht(a)
    if not standort_kern.ist_goslar():
        a.daten = {"fremd": True}
        return
    if getattr(a, "st_jahr", None) is None:
        a.st_jahr = _jahr_standard(a.heute)
    jahr = a.st_jahr
    p = rk.parameter()
    pg, fehler = _prognose(a)
    try:
        sk.buchungsstand_merken(pg, a.heute)
    except Exception:                        # noqa: BLE001 – Mitschreiben ist nur Zugabe
        pass
    prog = sk.prognose_monate(pg)
    fl = rk.flure(a.stand, a.heute, p)
    kap = float(pg.kapazitaet) if pg and pg.kapazitaet else None
    schon = {zid for e in rk.plan() if e["start"][:4] == str(jahr) for zid in (
        e["zimmer"] if e["art"] != "etage" else [z.id for f in fl if f.schluessel == e["flur"] for z in f.zimmer])}
    machbar = rk.machbare_etagen(a.stand, fl, jahr, a.heute, p)
    kern = sk.kernbestand(a.stand, pg, fl, p, a.heute)
    reserve_alle = {f.schluessel for f in kern.etagen}
    reserve = reserve_alle if p.get("kernbestand") else None
    kw = {"schon": schon, "machbar": machbar, "reserve": reserve}
    # Schon Vorgemerktes (z. B. eine selbst gewählte Etage) verbraucht Budget bzw. Ziel – vorgeschlagen wird der Rest
    vorgemerkt = [z for z in rk.jahresplan(a.stand, jahr, None, p) if z.start.year == jahr]
    bereits = {"bau": sum(z.kosten.instandhaltung for z in vorgemerkt), "moebel": sum(z.kosten.investition for z in vorgemerkt),
               "zimmer": sum(z.zimmer for z in vorgemerkt), "anzahl": len(vorgemerkt),
               "moebel_von": sum(z.kosten.spanne_von("moebel")[0] for z in vorgemerkt),
               "moebel_bis": sum(z.kosten.spanne_von("moebel")[1] for z in vorgemerkt)}
    # 0.47: Vorhaben – gespeicherte + „Renovierung <Jahr>“ aus den Vormerkungen; andere Vorhaben verbrauchen ihren Topf
    jahre = {int(e["start"][:4]) for e in rk.plan()} | {jahr}
    vorhaben = vk.alle({y: rk.jahresplan(a.stand, y, None, p) for y in jahre})
    andere = {t: vk.summe_topf(vorhaben, jahr, t) for t in vk.TOEPFE}
    # 0.48: Budget je Topf und Haushaltsjahr – verbraucht nach Regel (Standard: beim Auftrag), offen = geplant
    ein = vk.einstellungen()
    budgets = {"bau": vk.budget(jahr, "bau", p.get("budget_bau"), ein),
               "moebel": vk.budget(jahr, "moebel", p.get("moebel_obergrenze"), ein), "sonstiges": vk.budget(jahr, "sonstiges", None, ein)}
    konten = {t: vk.konto(vorhaben, jahr, t, budgets[t], ein) for t in vk.TOEPFE}
    konten2 = {t: vk.konto(vorhaben, jahr + 1, t, vk.budget(jahr + 1, t, None, ein), ein) for t in vk.TOEPFE}
    p_rest = dict(p)
    p_rest["budget_bau"] = None if budgets["bau"] is None else max(0.0, budgets["bau"] - konten["bau"].belastet)
    if budgets["moebel"] is not None:
        p_rest["moebel_obergrenze"] = max(0.0, budgets["moebel"] - konten["moebel"].belastet)
    if p.get("modus") == "ziel":
        p_rest["ziel_zimmer"] = max(0, int(p.get("ziel_zimmer") or 0) - bereits["zimmer"])
    varianten, empf = rk.varianten(fl, p_rest, jahr, **kw)
    wahl = getattr(a, "st_var", None)
    if wahl not in {v.schluessel for v in varianten if v.massnahmen}:
        wahl = empf
    gewaehlt = next((v for v in varianten if v.schluessel == wahl), None)
    vs = rk.vorschlaege_variante(a.stand, fl, jahr, a.heute, p, prog, gewaehlt, kap) if (
        p.get("modus") == "ziel" and p_rest["ziel_zimmer"] > 0 or p.get("modus") != "ziel") else []
    zeilen = rk.jahresplan(a.stand, jahr, vs, p)
    kap_zeilen = {(z.flur, z.art, z.start): z for y in {a.heute.year, a.heute.year + 1, jahr}
                  for z in rk.jahresplan(a.stand, y, None, p)}
    kap_zeilen.update({(z.flur, z.art, z.start): z for z in zeilen})
    li = sk.linie(pg, list(kap_zeilen.values()), 12, 12 if ansicht_ == "cockpit" else 24)
    d = {"p": p, "pg": pg, "fehler": fehler, "fl": fl, "varianten": varianten, "empfehlung": empf, "wahl": wahl,
         "gewaehlt": gewaehlt, "vs": vs, "zeilen": zeilen, "li": li, "guete": sk.guete(pg), "jahr": jahr, "kern": kern,
         "robust": rk.robustheit(fl, p_rest, jahr, empf, **kw) if empf else "", "antrag": _antrag(gewaehlt, bereits),
         "platzhalter": _platzhalter(p), "machbar": machbar, "bereits": bereits, "p_rest": p_rest, "prog": prog,
         "kap": kap, "vorhaben": vorhaben, "andere": andere, "budgets": budgets, "konten": konten, "konten2": konten2,
         "einstellungen": ein, "abgleich": _abgleich(a, pg),
         "vorschlag": {"bau": sum(z.kosten.instandhaltung for z in zeilen if z.status != "vorgemerkt"),
                       "moebel": sum(z.kosten.investition for z in zeilen if z.status != "vorgemerkt")}}
    if ansicht_ == "finanzen":
        d["strategien"] = rk.strategien(fl, p, jahr, a.heute, 5, reserve_alle,
                                        f"Bei +10 % Nachfrage fehlten {kern.fehlend_plus10} Betten." if kern.etagen else "")
    d["kz"] = sk.kennzahlen(a.stand, a.heute, fl, list(kap_zeilen.values()), p, kern)
    d["luecken"] = sk.luecken()
    d["entscheidungen"] = _entscheidungen(d)
    if ansicht_ == "vorhaben":
        if getattr(a, "rv_flur", None) not in {f.schluessel for f in fl}:
            a.rv_flur = fl[0].schluessel if fl else None
        f = next((x for x in fl if x.schluessel == a.rv_flur), None)
        if f:
            fs = rk.monatsfenster(a.stand, f, jahr, p, prog)
            rk.engpass_markieren(fs, f, kap, rk.jahresplan(a.stand, jahr, None, p),
                                 defekt=rk.defekte_betten(a.stand, {z.id for z in f.zimmer}))
            d["monate"] = (f, fs, rk.bester_monat(fs, a.heute))
    if ansicht_ == "zeitplan":
        d["staende"] = sk.buchungsstaende()
    if ansicht_ == "cockpit":                     # 1.16/1.20: Karten je Monat einmal vorrechnen – danach wirkt jeder Klick sofort
        from . import cockpit_kern as ck

        d["heute"] = a.heute
        d["ck_karten"] = ck.karten(a.stand, fl, p, jahr, a.heute, zeilen, machbar, prog)
        d["ck_bedarf"] = ck.bedarf(pg, jahr, a.heute, kap, rk.defekte_betten(a.stand))
        d["ck_rho"] = ck.beharrung(pg)                                                  # 1.19: Wenn-dann
        reno = next((v for v in vorhaben if v.get("id") == vk.reno_id(jahr)), None)      # 1.17: Stand der Vormerkungen
        d["ck_phase"] = vk.phase(reno, a.heute) if reno else ("Vorschlag", "")
    if ansicht_ == "grundlagen":
        d["werte"] = sk.werte()
        d["noten"] = rk.zustandsnoten()
    a.daten = d


def _antrag(v, bereits: dict) -> dict:
    """Möbelantrag = schon Vorgemerktes + Vorschlag."""
    a = rk.moebelantrag(v)
    return {**a, "summe": a["summe"] + bereits["moebel"], "bau_mass": a["bau_mass"] + bereits["moebel"],
            "von": a["von"] + bereits["moebel_von"], "bis": a["bis"] + bereits["moebel_bis"]}


def _entscheidungen(d: dict) -> list[str]:
    erg = list(d["platzhalter"])
    for v in d["vs"]:
        if v.art != "etage":
            if v.teile:
                erg.append(f"{v.flur.text}: {len(v.teile)} Zimmer {rk.ARTEN[v.art]} ab {min(t[1] for t in v.teile):%d.%m.%Y} "
                           "(Kampagne) übernehmen?")
            if v.ohne_fenster:
                erg.append(f"{v.flur.text}: für {', '.join(z.kurz for z in v.ohne_fenster)} gibt es {d['jahr']} keinen "
                           "ausreichend langen Leerstand.")
            continue
        if v.fenster:
            fe = v.fenster
            erg.append(f"{v.flur.text}: {rk.MONATE[fe.start.month - 1]} {fe.start.year} übernehmen? Belegungsstopp ab "
                       f"{fe.stopp_ab:%d.%m.%Y}" + (" – Monat gleichwertig, frei wählbar" if fe.gleichwertig else "")
                       + (f" – ⚑ für {len(fe.ohne_ausweich)} Person(en) fehlt ein Ausweichzimmer" if fe.ohne_ausweich else "")
                       + (" – ▲ auch der beste Monat liegt an der Warnschwelle" if fe.engpass else "")
                       + (" – hinter den bekannten Buchungen, Ausweich nicht prüfbar" if not fe.pruefbar else ""))
        else:
            erg.append(f"{v.flur.text}: in {d['jahr']} ist kein Monat möglich (gesperrt oder Vorlauf zu kurz).")
    p, gew = d["p_rest"], d["gewaehlt"]
    if p.get("modus") != "ziel" and gew and p.get("budget_bau") is not None and (gew.rest_bau or 0) > 500:
        erg.append(f"{rk.tsd(gew.rest_bau)} Baubudget frei – verfällt am 31.12.{d['jahr']}. Keine weitere Maßnahme mit "
                   "erfasstem Bedarf passt hinein; INNternat schlägt nichts nur zum Ausschöpfen vor. Bedarf pflegen "
                   "(Zustandsnoten, Renovierungsdaten) oder eine Etage bewusst selbst planen.")
    if d["wahl"] != d["empfehlung"] and d["empfehlung"]:
        erg.append("Gewählt ist nicht die rechnerisch beste Variante – bewusst so?")
    warn = sk.warnmonate(d["li"])
    if warn:
        erg.append(f"Belegung erreicht in {len(warn)} Monat(en) die Warnschwelle (ab {rk.MONATE[warn[0].month - 1]} "
                   f"{warn[0].year}).")
    return erg


# ---- Zeichnen -------------------------------------------------------------------------------

def zeichnen(a) -> None:
    ansicht_ = ansicht(a)
    with a.werkzeuge:
        segmente(ANSICHTEN, ansicht_, lambda v: a.oeffnen("steuerung", ansicht=v), ansicht=True)
    d = a.daten
    if d.get("fremd"):
        with a.inhalt:
            leer("Die Steuerung rechnet für Goslar (Prognose, Renovierung Haus 2 und 6). Bitte oben Standort Goslar wählen.")
        return
    with a.leiste:
        if ansicht_ == "finanzen":
            ui.label("Planjahr bzw. 5 Jahre ab").classes("m-zweite")
        segmente({j: str(j) for j in (a.heute.year, a.heute.year + 1, a.heute.year + 2)}, d["jahr"],
                 lambda j: a.setzen(st_jahr=j, nur_seite=True), sofort=True)
        knopf("Entscheidungsvorlage (PDF)", lambda: _bericht(a), "primaer", "picture_as_pdf").style("margin-left:auto")
    if ansicht_ == "cockpit":                     # 1.20: das neue Cockpit ersetzt das alte
        from . import cockpit_ui

        cockpit_ui.zeichnen(a)
        return
    {"vorhaben": _vorhaben, "zeitplan": _zeitplan, "finanzen": _finanzen,
     "grundlagen": _grundlagen}[ansicht_](a)


def _bericht(a) -> None:
    d = dict(a.daten)
    if "strategien" not in d:
        d["strategien"] = rk.strategien(d["fl"], d["p"], d["jahr"], a.heute, 5, {f.schluessel for f in d["kern"].etagen})
    html = sk.bericht_html({**d, "standort": "Goslar", "heute": a.heute, "empfehlung": d["wahl"], "empfohlen": d["empfehlung"]})
    seiten.html_drucken(a, html, f"Entscheidungsvorlage_Renovierung_{d['jahr']}")


def _kpi(titel: str, wert: str, unter: str = "", stufe: str = "", tipp: str = "", ziel=None) -> None:
    k = ui.element("button" if ziel else "div").classes("m-kpikarte" + (" m-kpi-klick" if ziel else ""))
    if tipp or ziel:
        attr(k, title=(tipp + " · " if tipp else "") + ("Klick: zur Liste" if ziel else ""))
    if ziel:
        k.on("click", ziel)
    with k:
        ui.label(titel).classes("m-zweite")
        ui.label(wert).classes("m-kpiwert" + (f" m-{stufe}" if stufe in ("krit", "warn") else ""))
        if unter:
            ui.label(unter).classes("m-zweite")


def _chart(a, li: sk.Linie, hoehe: str = "300px") -> None:
    from . import seite_auswertung as sa

    if not li.monate:
        leer("Keine Prognosedaten – Pivot unter „Daten & Import“ wählen.")
        return
    T = sa._T()
    opt = sa._chart_basis()
    opt["xAxis"]["data"] = [f"{rk.MONATE[m.month - 1]} {str(m.year)[2:]}" for m in li.monate]
    opt["series"] = [
        {"name": "80-%-Spanne unten", "type": "line", "data": li.lo80, "stack": "band", "lineStyle": {"opacity": 0},
         "symbol": "none", "tooltip": {"show": False}},
        {"name": "80-%-Spanne", "type": "line", "stack": "band", "symbol": "none", "lineStyle": {"opacity": 0},
         "data": [None if h is None or lo is None else round(h - lo, 1) for h, lo in zip(li.hi80, li.lo80)],
         "areaStyle": {"color": T["akzent"], "opacity": .15}},
        {"name": "Vorjahr", "type": "line", "data": li.vorjahr, "symbol": "none",
         "lineStyle": {"color": T["text3"], "width": 1.2, "type": "dotted"}},
        {"name": "Ist", "type": "line", "data": li.ist, "symbol": "none", "lineStyle": {"color": T["text"], "width": 2}},
        {"name": "Prognose", "type": "line", "data": li.prognose, "symbol": "none",
         "lineStyle": {"color": T["akzent"], "width": 2, "type": "dashed"}},
        {"name": "Kapazität (minus Baustellen)", "type": "line", "data": li.kapazitaet, "symbol": "none", "step": "middle",
         "lineStyle": {"color": T.get("rot", "#c0392b"), "width": 1.5}},
    ]
    if li.warnschwelle:
        opt["series"][-1]["markLine"] = {"symbol": "none", "silent": True, "label": {"formatter": "Warnschwelle", "position": "insideEndTop",
                                                                                     "color": T["text3"]},
                                         "lineStyle": {"type": "dashed", "color": T.get("orange", "#d68910")},
                                         "data": [{"yAxis": li.warnschwelle}]}
    opt["yAxis"]["name"] = "Plätze"
    opt["legend"]["data"] = [s["name"] for s in opt["series"] if not s["name"].endswith("unten")]
    opt["grid"]["top"] = 40
    sa._chart(opt)
    ui.query(".m-chart").style(f"height:{hoehe}")


# ---- Übersicht ------------------------------------------------------------------------------

def horizont(jahr: int, start: int) -> str:
    """Planungshorizont: Jahr 1 belastbar, Jahr 2 wahrscheinlich, Jahre 3–5 Orientierung."""
    n = jahr - start
    return "belastbar" if n <= 0 else "wahrscheinlich" if n == 1 else "Orientierung"


STATUS_STUFE = {"abgeschlossen": "ok", "abgerechnet": "ok", "freigegeben": "ok", "in Arbeit": "blau", "beauftragt": "blau",
                "gebunden": "blau", "teilweise bezahlt": "blau", "abgelehnt": "krit"}


def phasen_leiste(phase: str, luecke: str = "", tipp: str = "") -> None:
    """1.17: Stand als eine Leiste Vorschlag → Freigegeben → Beauftragt → In Umsetzung → Abgerechnet."""
    box = ui.element("div").classes("m-phasen")
    if tipp:
        attr(box, title=tipp)
    with box:
        if phase == "Abgelehnt":
            ui.label("Abgelehnt").classes("m-pille krit")
        else:
            i = vk.PHASEN.index(phase)
            with ui.element("div").classes("m-phasen-leiste"):
                for j, p_ in enumerate(vk.PHASEN):
                    ui.label(p_).classes("da" if j < i else "jetzt" if j == i else "")
        if luecke:
            ui.label(("⚠ " if luecke in ("Freigabe fehlt", "Rechnung fehlt") else "") + luecke).classes(
                "m-phasen-luecke" + (" warn" if luecke in ("Freigabe fehlt", "Rechnung fehlt") else ""))


def _vorhaben(a) -> None:
    """Vorhaben: Portfolio-Liste (alle Arten, gefiltert) + Werkzeug „Renovierung planen“."""
    d = a.daten
    kat = getattr(a, "vh_kat", "")
    zeilen = vk.liste(d["vorhaben"], a.heute, kat, d["jahr"])
    with a.leiste:
        knopf("Neues Vorhaben …", lambda: _vorhaben_panel(a, vk.leer_vorhaben(haus="")), "primaer", "add")
    with a.inhalt:
        with ui.element("div").classes("m-rv"):
            with ui.element("section").classes("m-block m-breit"):
                with ui.element("div").classes("m-zeile-flex"):
                    ui.label(f"Vorhaben {d['jahr']} ({len(zeilen)})").classes("m-btitel")
                    segmente({"": "Alle", **{k: k for k in vk.KATEGORIEN if any(v.get("kategorie") == k for v in d["vorhaben"])}},
                             kat, lambda k: a.setzen(vh_kat=k, nur_seite=True), sofort=True)
                if not zeilen:
                    ui.label("Noch keine Vorhaben in diesem Jahr. „Neues Vorhaben …“ legt eines an; vorgemerkte Renovierungen "
                             "erscheinen hier automatisch als „Renovierung <Jahr>“.").classes("m-zweite").style("white-space:normal")
                else:
                    with tabelle("minmax(200px, 2fr) auto auto minmax(300px, 1.4fr) auto auto"):
                        with ui.element("div").classes("m-raster m-tkopf"):
                            for t in ("Vorhaben", "Kategorie", "Haupttreiber", "Stand", "Kosten", "Jahr"):
                                ui.label(t)
                        for z in zeilen:
                            v = z.v
                            r = ui.element("div").classes("m-raster m-zeile m-rv-zeile")
                            with r:
                                with ui.element("div"):
                                    ui.label(v["titel"] + (f" · Haus {v['haus']}" if v.get("haus") else "")).classes("m-name")
                                    if z.hinweise:
                                        attr(ui.label(f"⚠ {z.hinweise[0]}").classes("m-zweite m-warn"), title="\n".join(z.hinweise))
                                ui.label(v.get("kategorie", "")).classes("m-zweite")
                                attr(ui.label(vk.TREIBER.get(v.get("treiber"), "–")).classes(
                                    "m-pille " + ("krit" if v.get("treiber") == "pflicht" else "neutral")), title=v.get("nachweis", ""))
                                phasen_leiste(z.phase, z.luecke, f"Entscheidung: {z.entscheidung} · Umsetzung: {z.umsetzung} · "
                                              f"Finanzen: {z.finanzen}")
                                ui.label(rk.euro(z.summe)).classes("m-mono")
                                ui.label(", ".join(str(j) for j in z.jahre) or "–").classes("m-mono")
                            r.on("click", lambda v=v: _vorhaben_panel(a, v))
                ui.label("Klick: Vorhaben öffnen – Treiber mit Nachweis, Entscheidung, Maßnahmen, Kostenpositionen mit Auftrag und "
                         "Rechnungen. Umsetzung und Finanzen ergeben sich daraus.").classes("m-xk-hinweis")
    _renovierung(a)


def _vorhaben_panel(a, v0: dict) -> None:
    """Vorhaben bearbeiten. Arbeitskopie ``w`` – gespeichert wird erst mit „Speichern“ (Rückgängig wie immer)."""
    import copy

    w = copy.deepcopy(v0)
    abg = bool(w.get("abgeleitet"))
    p = a.daten["p"]
    neu = not any(x.get("id") == w["id"] for x in a.daten["vorhaben"])

    def setz(dct, k, umwandeln=None):
        def f(e):
            wert = e.value
            dct[k] = umwandeln(wert) if umwandeln and wert not in (None, "") else wert
        return f

    def bauen():
        if abg:
            ui.label("Abgeleitet aus „Renovierung planen“: Maßnahmen und geplante Beträge kommen aus der Planung. Hier: Treiber, "
                     "Entscheidung, Aufträge und Rechnungen.").classes("m-pille neutral").style("white-space:normal")
        ui.label("Allgemein").classes("m-ktitel")
        ui.input("Titel", value=w["titel"], on_change=setz(w, "titel")).classes("m-feld").props(
            "dense outlined dark" + (" readonly" if abg else ""))
        ui.input("Beschreibung", value=w.get("beschreibung", ""), on_change=setz(w, "beschreibung")).classes("m-feld").props(
            "dense outlined dark")
        with ui.element("div").classes("m-kap").style("grid-template-columns: repeat(3, 1fr)"):
            ui.select(vk.KATEGORIEN, value=w.get("kategorie") or "Sonstiges", label="Kategorie",
                      on_change=setz(w, "kategorie")).classes("m-feld").props(
                'dense outlined dark popup-content-class="m-popup"' + (" readonly" if abg else ""))
            ui.select({"": "alle / übergreifend", **{h: f"Haus {h}" for h in p["haeuser"]}}, value=w.get("haus") or "",
                      label="Haus", on_change=setz(w, "haus")).classes("m-feld").props('dense outlined dark popup-content-class="m-popup"')
            ui.select(vk.PRIORITAET, value=w.get("prioritaet") or "mittel", label="Priorität",
                      on_change=setz(w, "prioritaet")).classes("m-feld").props('dense outlined dark popup-content-class="m-popup"')
        ui.label("Haupttreiber (genau einer)").classes("m-ktitel")
        nachweis = None

        def treiber_neu(e):
            w["treiber"] = e.value
            nachweis.props(f'label="{vk.NACHWEIS.get(e.value, "Begründung")}"')
        ui.select(vk.TREIBER, value=w.get("treiber") or None, label="Haupttreiber", on_change=treiber_neu).classes("m-feld").props(
            'dense outlined dark popup-content-class="m-popup"')
        nachweis = ui.input(vk.NACHWEIS.get(w.get("treiber"), "Begründung"), value=w.get("nachweis", ""),
                            on_change=setz(w, "nachweis")).classes("m-feld").props("dense outlined dark")
        ui.label("Pflicht nur mit Nachweis – sonst Risiko, Qualität usw. Pflicht-Vorhaben stehen in der Liste oben.").classes(
            "m-zweite")
        ui.label("Entscheidung").classes("m-ktitel")
        e = w.setdefault("entscheidung", {"status": "idee", "datum": "", "wer": ""})
        with ui.element("div").classes("m-kap").style("grid-template-columns: repeat(3, 1fr)"):
            ui.select(vk.ENTSCHEIDUNG, value=e.get("status") or "idee", label="Status", on_change=setz(e, "status")).classes(
                "m-feld").props('dense outlined dark popup-content-class="m-popup"')
            ui.input("Datum", value=e.get("datum", ""), on_change=setz(e, "datum")).classes("m-feld").props(
                "dense outlined dark type=date")
            ui.input("Wer (Gremium/Person)", value=e.get("wer", ""), on_change=setz(e, "wer")).classes("m-feld").props(
                "dense outlined dark")
        status = ui.label("").classes("m-zweite")

        def status_neu():
            hs = vk.hinweise(w, a.heute)
            status.set_text(f"Umsetzung: {vk.umsetzung(w, a.heute)} · Finanzen: {vk.finanzen(w)}"
                            + ("" if not hs else " · ⚠ " + " ⚠ ".join(hs)))
        status_neu()

        @ui.refreshable
        def massnahmen():
            ui.label(f"Maßnahmen ({len(w['massnahmen'])})").classes("m-ktitel")
            for m in w["massnahmen"]:
                with ui.element("div").classes("m-liste-zeile"):
                    if m.get("abgeleitet"):
                        ui.label(m["titel"]).classes("m-name")
                        ui.label(f"{m['von']} – {m['bis']}").classes("m-mono")
                        continue
                    ui.input("Maßnahme", value=m.get("titel", ""), on_change=setz(m, "titel")).classes("m-feld").props(
                        "dense outlined dark").style("flex:2")
                    ui.input("von", value=m.get("von", ""), on_change=lambda ev, m=m: (setz(m, "von")(ev), status_neu())).classes(
                        "m-feld").props("dense outlined dark type=date")
                    ui.input("bis", value=m.get("bis", ""), on_change=lambda ev, m=m: (setz(m, "bis")(ev), status_neu())).classes(
                        "m-feld").props("dense outlined dark type=date")
                    knopf("", lambda m=m: (w["massnahmen"].remove(m), massnahmen.refresh(), status_neu()), "leise", "delete",
                          "Maßnahme entfernen")
            if not abg:
                knopf("Maßnahme hinzufügen", lambda: (w["massnahmen"].append({"id": vk._neu_id("m"), "titel": "", "von": "",
                                                                                "bis": ""}), massnahmen.refresh()),
                      "leise", "add")
            else:
                async def zur_planung():
                    a.panel_zu()
                    await a.oeffnen("steuerung", ansicht="vorhaben")
                knopf("In „Renovierung planen“ ändern", zur_planung,
                      "leise", "edit_calendar")
        massnahmen()

        @ui.refreshable
        def kosten():
            ui.label(f"Kostenpositionen ({len(w['kosten'])}) · geplant {rk.euro(vk.betraege(w)['geplant'])}").classes("m-ktitel")
            for k in w["kosten"]:
                with ui.element("div").classes("m-block").style("padding:10px 12px; gap:6px"):
                    fest = bool(k.get("abgeleitet"))
                    ro = " readonly" if fest else ""
                    with ui.element("div").classes("m-kap").style("grid-template-columns: 2fr 1fr 1fr"):
                        ui.input("Position", value=k.get("titel", ""), on_change=setz(k, "titel")).classes("m-feld").props(
                            "dense outlined dark" + ro)
                        ui.number("Betrag €", value=k.get("betrag") or 0, min=0, step=100,
                                  format="%.2f", on_change=setz(k, "betrag", float)).classes("m-feld").props("dense outlined dark" + ro)
                        ui.number("Haushaltsjahr", value=k.get("jahr") or a.daten["jahr"], min=2000, max=2100, step=1, format="%d",
                                  on_change=setz(k, "jahr", int)).classes("m-feld").props("dense outlined dark" + ro)
                    with ui.element("div").classes("m-kap").style("grid-template-columns: repeat(3, 1fr)"):
                        ui.select(vk.TOEPFE, value=k.get("topf") or "bau", label="Topf", on_change=setz(k, "topf")).classes(
                            "m-feld").props('dense outlined dark popup-content-class="m-popup"' + ro)
                        ui.select(vk.HERKUNFT, value=k.get("herkunft") or "schaetzung", label="Herkunft",
                                  on_change=setz(k, "herkunft")).classes("m-feld").props('dense outlined dark popup-content-class="m-popup"' + ro)
                        ui.input("Angebot gültig bis", value=k.get("gueltig_bis", ""), on_change=setz(k, "gueltig_bis")).classes(
                            "m-feld").props("dense outlined dark type=date" + ro)
                    au = k.get("auftrag") or {}
                    with ui.element("div").classes("m-kap").style("grid-template-columns: 1.5fr 1fr 1.5fr"):
                        def auftrag(feld, umw=None, k=k):
                            def f(ev):
                                k["auftrag"] = {**(k.get("auftrag") or {}), feld: umw(ev.value) if umw and ev.value not in (None, "") else ev.value}
                                status_neu()
                            return f
                        ui.number("Auftrag €", value=au.get("betrag") or None, min=0, step=100, format="%.2f",
                                  on_change=auftrag("betrag", float)).classes("m-feld").props("dense outlined dark clearable")
                        ui.input("Auftrag am", value=au.get("datum", ""), on_change=auftrag("datum")).classes("m-feld").props(
                            "dense outlined dark type=date")
                        ui.input("Bemerkung", value=k.get("bemerkung", ""), on_change=setz(k, "bemerkung")).classes("m-feld").props(
                            "dense outlined dark" + ro)
                    for r in k.setdefault("rechnungen", []):
                        with ui.element("div").classes("m-kap").style("grid-template-columns: 1fr 1fr 1fr auto"):
                            ui.number("Rechnung €", value=r.get("betrag") or 0, min=0, step=100, format="%.2f",
                                      on_change=lambda ev, r=r: (setz(r, "betrag", float)(ev), status_neu())).classes("m-feld").props(
                                "dense outlined dark")
                            ui.input("Rechnung vom", value=r.get("datum", ""), on_change=setz(r, "datum")).classes("m-feld").props(
                                "dense outlined dark type=date")
                            ui.input("bezahlt am", value=r.get("bezahlt_am", ""),
                                     on_change=lambda ev, r=r: (setz(r, "bezahlt_am")(ev), status_neu())).classes("m-feld").props(
                                "dense outlined dark type=date")
                            knopf("", lambda k=k, r=r: (k["rechnungen"].remove(r), kosten.refresh(), status_neu()), "leise",
                                  "delete", "Rechnung entfernen")
                    with ui.element("div").classes("m-zeile-flex"):
                        knopf("Rechnung erfassen", lambda k=k: (k["rechnungen"].append({"betrag": 0, "datum": a.heute.isoformat(),
                                                                                         "bezahlt_am": ""}), kosten.refresh()),
                              "leise", "receipt_long")
                        if not fest:
                            knopf("Position entfernen", lambda k=k: (w["kosten"].remove(k), kosten.refresh(), status_neu()),
                                  "leise", "delete")
            knopf("Kostenposition hinzufügen", lambda: (w["kosten"].append(
                {"id": vk._neu_id("k"), "titel": "", "betrag": 0.0, "herkunft": "schaetzung", "jahr": a.daten["jahr"],
                 "topf": "bau", "bemerkung": "", "gueltig_bis": "", "auftrag": None, "rechnungen": []}), kosten.refresh()),
                "leise", "add")
        kosten()

        async def speichern():
            if await a.aendern(vk.speichern_auto_schritt, w):
                a.panel_zu()

        async def loeschen():
            if await a.aendern(vk.loeschen_schritt, w["id"], w["titel"]):
                a.panel_zu()

        with ui.element("div").classes("m-paktionen"):
            knopf("Speichern", speichern, "primaer", "check")
            if not abg and not neu:
                knopf("Löschen", loeschen, "leise", "delete")
            knopf("Abbrechen", a.panel_zu, "leise")

    a.panel(("Neues Vorhaben" if neu and not abg else f"Vorhaben: {w['titel']}"), bauen, breit=True)


def _zeitplan(a) -> None:
    d = a.daten
    with a.inhalt:
        with ui.element("div").classes("m-rv"):
            with ui.element("section").classes("m-block m-breit"):
                ui.label(f"Zeitplan {d['jahr']} – Renovierung").classes("m-btitel")
                _gantt(a, d["zeilen"], d["jahr"])
                knopf("Planen", lambda: a.oeffnen("steuerung", ansicht="vorhaben"), "leise", "arrow_forward")
            termine = sorted(((v, m) for v in d["vorhaben"] if not v.get("abgeleitet") for m in v.get("massnahmen") or []
                              if str(m.get("von") or "")[:4] <= str(d["jahr"]) <= str(m.get("bis") or "")[:4]),
                             key=lambda x: str(x[1].get("von")))
            with ui.element("section").classes("m-block m-breit"):
                ui.label(f"Weitere Vorhaben {d['jahr']} – Termine ({len(termine)})").classes("m-btitel")
                if not termine:
                    ui.label("Keine Maßnahmen mit Termin. Termine trägt man im Vorhaben unter „Maßnahmen“ ein.").classes("m-zweite")
                else:
                    with tabelle("minmax(180px, 1.5fr) minmax(160px, 1.5fr) auto auto auto"):
                        with ui.element("div").classes("m-raster m-tkopf"):
                            for t in ("Vorhaben", "Maßnahme", "von", "bis", "Umsetzung"):
                                ui.label(t)
                        for v, m in termine:
                            r = ui.element("div").classes("m-raster m-zeile m-rv-zeile")
                            with r:
                                ui.label(v["titel"]).classes("m-name")
                                ui.label(m.get("titel") or "–").classes("m-zweite")
                                for t in (m.get("von"), m.get("bis")):
                                    ui.label(f"{vk._d(t):%d.%m.%Y}" if vk._d(t) else "–").classes("m-mono")
                                u = vk.umsetzung(v, a.heute)
                                ui.label(u).classes(f"m-pille {STATUS_STUFE.get(u, 'neutral')}")
                            r.on("click", lambda v=v: _vorhaben_panel(a, v))
    _prognose_seite(a)


def _finanzen(a) -> None:
    """Budget je Topf und Haushaltsjahr (= Kalenderjahr): verbraucht nach Regel, geplant offen, Vorschlag, frei."""
    d = a.daten
    jahr, ant, ein = d["jahr"], d["antrag"], d["einstellungen"]
    with a.leiste:
        knopf("Budget je Jahr & Regeln …", lambda: _budget_panel(a), "", "account_balance_wallet")
    with a.inhalt:
        with ui.element("div").classes("m-rv"):
            for j_, konten, mit_vorschlag in ((jahr, d["konten"], True), (jahr + 1, d["konten2"], False)):
                with ui.element("section").classes("m-block m-breit"):
                    ui.label(f"Budget {j_} je Topf · {horizont(j_, jahr)}").classes("m-btitel")
                    with tabelle("minmax(150px, 1.2fr) auto auto auto auto auto auto auto auto minmax(150px, 1.6fr)"):
                        with ui.element("div").classes("m-raster m-tkopf"):
                            for t in ("Topf", "Budget", "Verbraucht", "Geplant offen", "Vorschlag", "Frei", "gebunden",
                                      "abgerechnet", "bezahlt", "Regel / Hinweis"):
                                ui.label(t)
                        for t, kt in konten.items():
                            vs = d["vorschlag"].get(t, 0.0) if mit_vorschlag else 0.0
                            if t == "sonstiges" and not (kt.geplant or kt.verbraucht or kt.budget):
                                continue
                            frei = None if kt.budget is None else kt.budget - kt.belastet - vs
                            r = ui.element("div").classes("m-raster m-zeile m-rv-zeile")
                            with r:
                                ui.label({"bau": "Bau (Instandhaltung)", "moebel": "Möbel / Einrichtung",
                                          "sonstiges": "Sonstiges"}[t]).classes("m-name")
                                ui.label("–" if kt.budget is None else rk.euro(kt.budget)).classes("m-mono")
                                for w_ in (kt.verbraucht, kt.offen, vs):
                                    ui.label(rk.euro(w_)).classes("m-mono")
                                ui.label("–" if frei is None else rk.euro(frei)).classes(
                                    "m-mono" + (" m-krit" if frei is not None and frei < -500 else ""))
                                for w_ in (kt.gebunden, kt.abgerechnet, kt.bezahlt):
                                    ui.label(rk.euro(w_)).classes("m-mono m-zweite")
                                hinweis = f"verbraucht {vk.REGELN[kt.regel]}"
                                if t == "bau" and kt.budget is not None:
                                    hinweis += f" · verfällt am 31.12.{j_}"
                                if t == "moebel" and mit_vorschlag:
                                    hinweis += f" · Antrag Renovierung {rk.tsd(ant['summe'])}"
                                ui.label(hinweis).classes("m-zweite")
                            r.on("click", lambda kt=kt: _konto_panel(a, kt))
                    if not mit_vorschlag:
                        ui.label("Folgejahr: Aufträge, Rechnungen und Zahlungen mit Datum in diesem Jahr (z. B. Schlussrechnung im "
                                 "Januar) erscheinen hier – bei „beim Auftrag“ verbrauchen sie das Budget des Auftragsjahres, "
                                 "nicht dieses.").classes("m-xk-hinweis")
            ui.label("Verbraucht = nach der Regel des Topfs im Jahr des Ereignisses (Standard: beim Auftrag) · Geplant offen = "
                     "Kostenpositionen dieses Haushaltsjahres, die noch nicht verbraucht sind · Vorschlag = Renovierung, noch "
                     "nicht vorgemerkt · Frei = Budget − verbraucht − offen − Vorschlag · abgelehnte Vorhaben zählen nicht. "
                     "Klick auf einen Topf: alle Positionen.").classes("m-xk-hinweis")
            ui.label(f"Planungshorizont: {jahr} belastbar · {jahr + 1} wahrscheinlich · {jahr + 2}–{jahr + 4} Orientierung · "
                     f"Freigabe: {ein['entscheider']} (eine Stufe)").classes("m-pille neutral")
    _szenarien(a)


def _konto_panel(a, kt) -> None:
    def bauen():
        ui.label(f"{vk.TOEPFE[kt.topf]} {kt.jahr}: verbraucht {rk.euro(kt.verbraucht)}, geplant offen {rk.euro(kt.offen)}"
                 + ("" if kt.budget is None else f", Budget {rk.euro(kt.budget)}")).classes("m-ptext")
        if not kt.positionen:
            ui.label("Keine Positionen.").classes("m-zweite")
        with tabelle("minmax(160px, 1.5fr) minmax(160px, 1.5fr) auto auto"):
            with ui.element("div").classes("m-raster m-tkopf"):
                for t in ("Vorhaben", "Position", "Betrag", "zählt als"):
                    ui.label(t)
            for v, pos, betrag, wie in kt.positionen:
                with ui.element("div").classes("m-raster m-zeile"):
                    ui.label(v).classes("m-name")
                    ui.label(pos).classes("m-zweite")
                    ui.label(rk.euro(betrag)).classes("m-mono")
                    ui.label(wie).classes("m-pille " + ("neutral" if wie == "geplant" else "blau"))
    a.panel(f"{vk.TOEPFE[kt.topf]} {kt.jahr} – Positionen", bauen, breit=True)


def _budget_panel(a) -> None:
    """Budget je Topf und Jahr, Regel je Topf, wer freigibt."""
    import copy

    d = a.daten
    e = copy.deepcopy(d["einstellungen"])
    jahre = [d["jahr"] - 1, d["jahr"], d["jahr"] + 1, d["jahr"] + 2]

    def bauen():
        ui.label("Wann gilt ein Topf als verbraucht?").classes("m-ktitel")
        with ui.element("div").classes("m-kap").style("grid-template-columns: repeat(3, 1fr)"):
            for t in vk.TOEPFE:
                ui.select(vk.REGELN, value=e["regel"].get(t, "auftrag"), label=vk.TOEPFE[t],
                          on_change=lambda ev, t=t: e["regel"].__setitem__(t, ev.value)).classes("m-feld").props(
                    'dense outlined dark popup-content-class="m-popup"')
        ui.label("Budget je Haushaltsjahr (= Kalenderjahr). Leer = Bau aus der Vorgabe, Möbel ohne Obergrenze.").classes("m-ktitel")
        for j in jahre:
            with ui.element("div").classes("m-kap").style("grid-template-columns: 70px repeat(3, 1fr)"):
                ui.label(str(j)).classes("m-name").style("align-self:center")
                b = e["budgets"].setdefault(str(j), {})
                for t in vk.TOEPFE:
                    ui.number(f"{vk.TOEPFE[t]} €", value=b.get(t), min=0, step=1000, format="%.0f",
                              on_change=lambda ev, b=b, t=t: b.__setitem__(t, ev.value)).classes("m-feld").props(
                        "dense outlined dark clearable")
        ui.input("Wer gibt frei (eine Stufe)", value=e["entscheider"],
                 on_change=lambda ev: e.__setitem__("entscheider", ev.value or "Leitung")).classes("m-feld").props(
            "dense outlined dark")
        ui.label("Wird beim Freigeben eines Vorhabens eingetragen, wenn dort niemand steht.").classes("m-zweite")

        async def speichern():
            e["budgets"] = {j: {t: float(x) for t, x in b.items() if x not in (None, "")} for j, b in e["budgets"].items()}
            e["budgets"] = {j: b for j, b in e["budgets"].items() if b}
            if await a.aendern(vk.einstellungen_schritt, e):
                a.panel_zu()
        with ui.element("div").classes("m-paktionen"):
            knopf("Speichern", speichern, "primaer", "check")
            knopf("Abbrechen", a.panel_zu, "leise")
    a.panel("Budget je Jahr & Regeln", bauen, breit=True)


def _grundlagen(a) -> None:
    d = a.daten
    p, fl = d["p"], d["fl"]
    with a.leiste:
        knopf("Annahmen & Angebote …", lambda: _annahmen(a), "", "request_quote")
    with a.inhalt:
        with ui.element("div").classes("m-rv"):
            _platzhalter_banner(a, d)
            with ui.element("div").classes("m-zwei"):
                with ui.element("section").classes("m-block"):
                    liste = _annahmen_liste(p, fl)
                    ui.label(f"Annahmen ({len(liste)})").classes("m-btitel")
                    for text, hk in liste:
                        with ui.element("div").classes("m-liste-zeile"):
                            ui.label(text).classes("m-zweite").style("white-space:normal")
                            if hk:
                                _hk(hk)
                    knopf("Annahmen & Angebote ändern …", lambda: _annahmen(a), "leise", "request_quote")
                with ui.element("section").classes("m-block"):
                    ang = p.get("angebote") or []
                    ui.label(f"Angebote ({len(ang)})").classes("m-btitel")
                    if not ang:
                        ui.label("Noch kein Angebot eingelesen.").classes("m-zweite")
                    alt = set(rk.angebote_alt(p, a.heute))
                    for x in ang:
                        art = "Möbel" if x.get("art") == "moebel" else "Bau"
                        g = x.get("gueltig_bis") or ""
                        abgelaufen = bool(g) and g < a.heute.isoformat()
                        with ui.element("div").classes("m-liste-zeile"):
                            ui.label(f"Haus {x.get('haus')} · {art}").classes("m-name")
                            ui.label(rk.euro(float(x.get("netto") or 0)) + " netto").classes("m-mono")
                            ui.label((f"vom {x.get('datum')}" if x.get("datum") else "ohne Datum")
                                     + (f" · gültig bis {g}" if g else " · Gültigkeit unbekannt")).classes(
                                "m-zweite" + (" m-warn" if abgelaufen else ""))
                            if abgelaufen:
                                ui.label("abgelaufen – wird hochgerechnet").classes("m-pille warn")
                            elif any(s.startswith(f"Haus {x.get('haus')} {art}") for s in alt):
                                ui.label("älter als 12 Monate").classes("m-pille warn")
            _abgleich_block(d.get("abgleich") or [])
    _kennzahlen(a)


def _abgleich_block(zeilen: list) -> None:
    """1.14: Bettenprognose gegen Teilnehmer-Prognose (× Internatsanteil) – je Monat, Abweichung nur hervorgehoben,
    wenn sie größer ist als die halbe 80-%-Spanne."""
    with ui.element("section").classes("m-block m-breit"):
        ui.label("Abgleich: Betten- und Teilnehmerprognose").classes("m-btitel")
        if not zeilen:
            ui.label("Kein Abgleich möglich – es fehlt der Maßnahmen-Pivot oder die Belegungsprognose, oder die Prognose "
                     "zeigt „Brutto“ (mit UWTlern und Mietern; der Abgleich braucht „Netto“).").classes("m-zweite")
            return
        ui.label("Betten = Belegungsprognose (Teilnehmende ohne UWTler/Mieter). Teilnehmende = Maßnahmen-Prognose × "
                 "Internatsanteil der Art. Markiert ist ein Monat, wenn der Unterschied größer ist als die halbe "
                 "80-%-Spanne der Bettenprognose, mindestens aber 10 % des Planwerts bzw. 2 Plätze.").classes("m-zweite").style("white-space:normal")
        with tabelle("minmax(110px, 1fr) auto auto auto auto"):
            with ui.element("div").classes("m-raster m-tkopf"):
                for t in ("Monat", "Betten (Planwert)", "80-%-Spanne", "Teilnehmende im Internat", "Unterschied"):
                    ui.label(t)
            for z in zeilen:
                with ui.element("div").classes("m-raster m-zeile"):
                    ui.label(f"{rk.MONATE[z.monat.month - 1]} {z.monat.year}").classes("m-name")
                    ui.label(f"{z.betten:.0f}").classes("m-mono")
                    ui.label(f"{z.lo80:.0f}–{z.hi80:.0f}").classes("m-mono")
                    ui.label(f"{z.teilnehmende:.0f}").classes("m-mono")
                    ui.label(f"{z.differenz:+.0f}" + (" ⚠" if z.auffaellig else "")).classes(
                        "m-mono" + (" m-warn" if z.auffaellig else ""))
        if satz := sk.abgleich_satz(zeilen):
            ui.label(satz + ". Prüfen: Fehlt ein Kurs im Maßnahmen-Pivot, stimmt der Internatsanteil, sind geplante Plätze "
                     "eingetragen?").classes("m-zweite m-warn").style("white-space:normal")


def _prognose_seite(a) -> None:
    d, li, g = a.daten, a.daten["li"], a.daten["guete"]
    with a.inhalt:
        with ui.element("div").classes("m-rv"):
            if d["fehler"]:
                ui.label(d["fehler"]).classes("m-pille warn").style("white-space:normal")
            with ui.element("section").classes("m-block m-breit"):
                ui.label("Goslar: 12 Monate Ist, 24 Monate Prognose").classes("m-btitel")
                _chart(a, li, "340px")
                ui.label("Gepunktet: derselbe Monat ein Jahr früher (Ist). Rote Stufenlinie: Kapazität minus Betten in "
                         "Renovierung (vorgemerkt und Vorschläge). Ab Monat 13 ist die Prognose nur fortgeschrieben. Dieselbe "
                         "Berechnung wie unter Auswertung → Prognose.").classes("m-zweite").style("white-space:normal")
            with ui.element("div").classes("m-zwei"):
                with ui.element("section").classes("m-block"):
                    ui.label("Wie gut war die Prognose?").classes("m-btitel")
                    ui.label(g.satz).classes("m-ptext")
                    if g.hinweis:
                        ui.label(g.hinweis).classes("m-zweite").style("white-space:normal")
                with ui.element("section").classes("m-block"):
                    ui.label("Kernbestand und Reserve").classes("m-btitel")
                    kern = d["kern"]
                    ui.label(kern.text if kern.gesamt else kern.hinweis).classes("m-ptext").style("white-space:normal")
                    if kern.etagen:
                        ui.label("Vorschlag Reserve-Etagen: " + ", ".join(f.text for f in kern.etagen)
                                 + f". Bei +10 % Nachfrage fehlten {kern.fehlend_plus10} Betten.").classes(
                            "m-zweite").style("white-space:normal")
                    st = d.get("staende") or {}
                    ui.label(f"Buchungsstände: {len(st)} gesammelt" + (f" (seit {min(st)})" if st else "")
                             + " – Grundlage für ein späteres Pickup-Modell.").classes("m-xk-hinweis")
                    knopf("Ausführliche Prognose (Auswertung)", lambda: a.oeffnen("auswertung", ansicht="prognose"),
                          "leise", "insights")


# ---- Strategie 5 Jahre ----------------------------------------------------------------------------

def _strategie_tabelle(strategien, kompakt: bool = False) -> None:
    sp = "minmax(150px, 2fr) 90px 60px 90px 90px 64px" + ("" if kompakt else " 70px")
    with tabelle(sp):
        with ui.element("div").classes("m-raster m-tkopf").style(f"grid-template-columns:{sp}"):
            for t in ("Strategie", "A-Zimmer", "Zimmer", "Bau", "Möbel", "Zyklus") + (() if kompakt else ("Sperr",)):
                ui.label(t)
        for s in strategien or []:
            z = ui.element("div").classes("m-raster m-zeile").style(f"grid-template-columns:{sp}")
            attr(z, title=s.deutung)
            with z:
                ui.label(s.titel).classes("m-name")
                ui.label(f"{s.a_start} → {s.a_ende}").classes("m-mono" + (" m-krit" if s.a_ende > s.a_start else ""))
                ui.label(str(s.zimmer)).classes("m-mono")
                ui.label(rk.tsd(s.summe("bau"))).classes("m-mono")
                ui.label(rk.tsd(s.summe("moebel"))).classes("m-mono")
                ui.label("–" if s.zyklus is None else f"{s.zyklus:g} J.").classes("m-mono")
                if not kompakt:
                    ui.label(f"{s.summe('sperr'):g}").classes("m-mono")


def _szenarien(a) -> None:
    from . import seite_auswertung as sa

    d = a.daten
    st = d["strategien"]
    with a.inhalt:
        with ui.element("div").classes("m-rv"):
            ui.label(f"Fünf Jahre ab {d['jahr']}, Jahr für Jahr gerechnet: Zimmer werden älter (Klassen steigen), erneuerte "
                     "Zimmer fallen heraus, Preise steigen. „A-Zimmer“ = dringende Zimmer heute → am Ende.").classes("m-ptext")
            with ui.element("section").classes("m-block m-breit"):
                ui.label("Vergleich").classes("m-btitel")
                _strategie_tabelle(st)
            if st and any(s.jahre for s in st):
                T = sa._T()
                farben = [T["text3"], T["akzent"], T.get("orange", "#d68910"), T.get("blau", "#5b8def"), T.get("gruen", "#3aa76d")]
                jahre = [str(j["jahr"]) for j in st[0].jahre]
                with ui.element("div").classes("m-zwei"):
                    for titel, feld, kum, einheit in (("Offene Klasse-A-Zimmer", "a_offen", False, "Zimmer"),
                                                      ("Kosten kumuliert", "summe", True, "€")):
                        with ui.element("section").classes("m-block"):
                            ui.label(titel).classes("m-btitel")
                            opt = sa._chart_basis()
                            opt["xAxis"]["data"] = jahre
                            opt["yAxis"]["name"] = einheit
                            opt["grid"]["top"] = 50
                            opt["legend"]["type"] = "scroll"
                            reihen = []
                            for i, s in enumerate(st):
                                summe, werte = 0.0, []
                                for j in s.jahre:
                                    summe = summe + j[feld] if kum else j[feld]
                                    werte.append(round(summe))
                                reihen.append({"name": s.titel, "type": "line", "data": werte,
                                               "lineStyle": {"color": farben[i % len(farben)], "width": 2}, "symbol": "circle"})
                            opt["series"] = reihen
                            sa._chart(opt)
            for s in st:
                with ui.element("section").classes("m-block m-breit"):
                    ui.label(s.titel).classes("m-btitel")
                    ui.label(s.erklaerung).classes("m-zweite").style("white-space:normal")
                    ui.label(s.deutung).classes("m-ptext").style("white-space:normal")
                    sp = "auto minmax(220px, 3fr) auto auto auto auto auto"
                    with tabelle(sp):
                        with ui.element("div").classes("m-raster m-tkopf").style(f"grid-template-columns:{sp}"):
                            for t in ("Jahr", "Maßnahmen", "Zimmer", "Bau", "Möbel", "Sperr", "A offen"):
                                ui.label(t)
                        for j in s.jahre:
                            with ui.element("div").classes("m-raster m-zeile").style(f"grid-template-columns:{sp}"):
                                attr(ui.label(f"{j['jahr']} · {horizont(j['jahr'], d['jahr'])}").classes("m-mono"),
                                 title="Jahr 1 belastbar · Jahr 2 wahrscheinlich · Jahre 3–5 Orientierung")
                                attr(ui.label(j["text"]).classes("m-zweite"), title=j["text"])
                                ui.label(str(j["zimmer"])).classes("m-mono")
                                ui.label(rk.tsd(j["bau"])).classes("m-mono")
                                ui.label(rk.tsd(j["moebel"])).classes("m-mono")
                                ui.label(f"{j['sperr']:g}").classes("m-mono")
                                ui.label(str(j["a_offen"])).classes("m-mono")


# ---- Kennzahlen -----------------------------------------------------------------------------------

def _kennzahlen(a) -> None:
    d = a.daten
    with a.leiste:
        knopf("Werte eingeben …", lambda: _werte_panel(a), "", "dialpad")
    with a.inhalt:
        with ui.element("div").classes("m-rv"):
            with ui.element("div").classes("m-kpis"):
                for k in d["kz"]:
                    _kpi(k.titel, k.wert, k.unter, k.stufe, f"Quelle: {k.quelle}" if k.quelle else "")
            if d["luecken"]:
                with ui.element("section").classes("m-block m-breit"):
                    ui.label("Was noch fehlt – und wo man es einträgt").classes("m-btitel")
                    for titel, bedarf in d["luecken"]:
                        with ui.element("div").classes("m-liste-zeile"):
                            ui.label(titel).classes("m-name")
                            ui.label(f"braucht: {bedarf}").classes("m-zweite")
            ui.label("Zum Ausprobieren gehen auch erfundene Zahlen – Rückgängig wie immer. Engpässe je Haus und Zimmertyp: "
                     "Auswertung → Zimmer & Engpässe.").classes("m-xk-hinweis")
            knopf("Zu den Engpässen", lambda: a.oeffnen("auswertung", ansicht="zimmer"), "leise", "insights")


def _werte_panel(a) -> None:
    w, noten, fl = sk.werte(), rk.zustandsnoten(), a.daten["fl"]

    def bauen():
        ui.label("Tagessätze je Gruppe (€ je Belegtag) – für Erlös und Leerstand. Leer = unbekannt.").classes("m-ktitel")
        saetze = {}
        with ui.element("div").classes("m-kap").style("grid-template-columns: repeat(4, 1fr)"):
            for g in sk.GRUPPEN:
                saetze[g] = ui.number(g, value=w["tagessaetze"].get(g), min=0, step=5, format="%.2f").classes(
                    "m-feld").props("dense outlined dark clearable")
        ui.label("Abweisungen „kein Zimmer frei“ je Monat").classes("m-ktitel")
        monate = []
        m = date(a.heute.year, a.heute.month, 1)
        for _i in range(12):
            monate.append(m)
            m = date(m.year - (m.month == 1), (m.month - 2) % 12 + 1, 1)
        ab = {}
        with ui.element("div").classes("m-kap").style("grid-template-columns: repeat(6, 1fr)"):
            for m in reversed(monate):
                k = f"{m:%Y-%m}"
                ab[k] = ui.number(f"{rk.MONATE[m.month - 1]} {str(m.year)[2:]}", value=w["abweisungen"].get(k), min=0, step=1,
                                  format="%d").classes("m-feld").props("dense outlined dark")
        ui.label("Zustandsnote je Etage (1 sehr gut … 5 sehr schlecht) – bestimmt die Bau-Klasse mit").classes("m-ktitel")
        nf = {}
        with ui.element("div").classes("m-kap").style("grid-template-columns: repeat(4, 1fr)"):
            for f in sorted(fl, key=lambda x: (x.haus, rk.zp._etage_sort(x.etage))):
                nf[f.schluessel] = ui.select({0: "–", 1: "1", 2: "2", 3: "3", 4: "4", 5: "5"}, value=noten.get(f.schluessel, 0),
                                             label=f.text).classes("m-feld").props('dense outlined dark popup-content-class="m-popup"')

        async def speichern():
            ok1 = await a.aendern(sk.werte_schritt, {"tagessaetze": {g: f.value for g, f in saetze.items() if f.value},
                                                     "abweisungen": {k: f.value for k, f in ab.items() if f.value}})
            neu = {k: int(f.value or 0) for k, f in nf.items() if f.value}
            ok2 = True if neu == noten else await a.aendern(rk.zustand_schritt, neu)
            if ok1 and ok2:
                a.panel_zu()
        with ui.element("div").classes("m-paktionen"):
            knopf("Speichern", speichern, "primaer", "check")
            knopf("Abbrechen", a.panel_zu, "leise")

    a.panel("Werte für die Kennzahlen", bauen, breit=True)
