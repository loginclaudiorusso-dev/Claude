"""Cockpit (1.16) – Oberfläche: oben vier Kennzahlen, links Karten zum An- und Abhaken (Monat ◄ ►, Details an Ort und
Stelle), rechts das Diagramm „Decke gegen Bedarf“ und der Satz für die Vorlage. Jede Änderung rechnet nur
``cockpit_kern.bewerten`` (Addieren) – deshalb sofort. Gespeichert wird erst mit „Übernehmen“ (ein Rückgängig)."""

from __future__ import annotations

from nicegui import ui

from . import cockpit_kern as ck
from . import renovierung_kern as rk
from .ui_bausteine import attr, knopf, leer

CSS = """
.m-ck { display: grid; gap: 12px; padding: 4px 20px 16px; }
.m-ck-kz { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 12px; }
.m-ck-kachel { background: var(--fl); border: 1px solid var(--rand); border-radius: 10px; padding: 10px 14px; }
.m-ck-kachel .k { color: var(--text2); font-size: 12px; font-weight: 600; text-transform: uppercase; letter-spacing: .03em; }
.m-ck-kachel .w { font-size: 25px; font-weight: 700; margin-top: 2px; line-height: 1.2; }
.m-ck-kachel .w small { font-size: 14px; color: var(--text2); font-weight: 500; }
.m-ck-kachel .s { color: var(--text2); font-size: 12.5px; margin-top: 2px; }
.m-ck-kachel.krit { border-color: var(--rot); } .m-ck-kachel.krit .w { color: var(--rot); }
.m-ck-kachel.warn .w { color: #b45309; } .m-ck-kachel.ok .w { color: #047857; }
.m-ck-balken { height: 7px; background: color-mix(in srgb, var(--text3) 25%, transparent); border-radius: 4px; margin-top: 7px;
  overflow: hidden; display: flex; }
.m-ck-balken i { display: block; height: 100%; }
.m-ck-hinweise { display: flex; flex-wrap: wrap; gap: 8px; }
.m-ck-hinweise > * { background: #fff7ed; border: 1px solid #fed7aa; color: #9a3412; border-radius: 8px; padding: 6px 10px;
  font-size: 12.5px; white-space: normal; }
body:not(.hell) .m-ck-hinweise > * { background: rgba(245,158,11,.12); color: #fbbf24; border-color: rgba(245,158,11,.35); }
.m-ck-haupt { display: grid; grid-template-columns: minmax(0, 2fr) minmax(0, 3fr); gap: 12px; align-items: start; }
.m-ck-box { background: var(--fl); border: 1px solid var(--rand); border-radius: 10px; padding: 12px 14px; }
.m-ck-box h3 { margin: 0 0 8px; font-size: 14px; display: flex; gap: 8px; align-items: baseline; }
.m-ck-box h3 .hint { margin-left: auto; font-weight: 400; color: var(--text3); font-size: 12px; }
.m-ck-karte { border: 1px solid var(--rand); border-radius: 9px; padding: 9px 11px; display: grid;
  grid-template-columns: 24px minmax(0, 1fr) auto; gap: 4px 10px; align-items: start; }
.m-ck-karte + .m-ck-karte { margin-top: 8px; }
.m-ck-karte.aus { background: color-mix(in srgb, var(--text3) 6%, transparent); }
.m-ck-karte.aus .m-ck-titel { color: var(--text2); }
.m-ck-cb { width: 20px; height: 20px; border-radius: 5px; border: 2px solid var(--text3); margin-top: 1px; cursor: pointer;
  display: flex; align-items: center; justify-content: center; color: #fff; font-weight: 700; font-size: 13px; background: none; padding: 0; }
.m-ck-cb.an { background: var(--akzent); border-color: var(--akzent); }
.m-ck-titel { font-weight: 600; font-size: 13.5px; display: flex; gap: 6px; align-items: center; flex-wrap: wrap; }
.m-ck-pill { font-size: 11px; font-weight: 700; padding: 1px 7px; border-radius: 999px; }
.m-ck-pill.A { background: #fee2e2; color: #b91c1c; } .m-ck-pill.B { background: #fef3c7; color: #92400e; }
.m-ck-pill.C { background: #e2e8f0; color: #475569; }
.m-ck-phase { font-size: 11px; color: var(--text2); border: 1px solid var(--rand); border-radius: 999px; padding: 0 8px; }
.m-ck-phase.vm { color: #0369a1; border-color: #7dd3fc; }
.m-ck-kosten { text-align: right; font-weight: 700; font-size: 13.5px; white-space: nowrap; }
.m-ck-kosten small { display: block; font-weight: 400; color: var(--text3); font-size: 11.5px; }
.m-ck-z2 { grid-column: 2 / 4; display: flex; gap: 12px; align-items: center; color: var(--text2); font-size: 12.5px; flex-wrap: wrap; }
.m-ck-monat { display: inline-flex; align-items: center; border: 1px solid var(--rand); border-radius: 6px; overflow: hidden; }
.m-ck-monat button { border: 0; background: none; cursor: pointer; padding: 1px 6px; color: var(--text2); font: inherit; }
.m-ck-monat button:hover { background: color-mix(in srgb, var(--akzent) 12%, transparent); }
.m-ck-monat span { font-weight: 700; color: var(--text); min-width: 30px; text-align: center; }
.m-ck-w.ok { color: #047857; font-weight: 600; } .m-ck-w.warn { color: #b45309; font-weight: 600; } .m-ck-w.krit { color: var(--rot); font-weight: 700; }
body:not(.hell) .m-ck-w.ok { color: #34d399; } body:not(.hell) .m-ck-w.warn { color: #fbbf24; }
.m-ck-mehr { margin-left: auto; color: var(--akzent); font-weight: 600; cursor: pointer; background: none; border: 0; font: inherit; }
.m-ck-drawer { grid-column: 2 / 4; border-top: 1px dashed var(--rand); margin-top: 6px; padding-top: 7px; font-size: 12px;
  color: var(--text2); display: grid; gap: 4px; }
.m-ck-drawer b { color: var(--text); }
.m-ck-mt { display: grid; grid-template-columns: repeat(12, minmax(0, 1fr)); gap: 2px; margin-top: 2px; }
.m-ck-mt span { text-align: center; font-size: 10.5px; padding: 2px 0; border-radius: 3px; background: color-mix(in srgb, var(--text3) 12%, transparent); }
.m-ck-mt span.gut { background: color-mix(in srgb, #10b981 22%, transparent); }
.m-ck-mt span.eng { background: color-mix(in srgb, #f59e0b 30%, transparent); }
.m-ck-mt span.nein { opacity: .45; text-decoration: line-through; }
.m-ck-mt span.wahl { outline: 2px solid var(--akzent); }
.m-ck-satz { font-size: 13.5px; background: color-mix(in srgb, var(--akzent) 8%, transparent);
  border: 1px solid color-mix(in srgb, var(--akzent) 35%, transparent); border-radius: 8px; padding: 9px 12px; }
.m-ck-fuss { display: flex; gap: 8px; margin-top: 10px; align-items: center; flex-wrap: wrap; }
/* 1.19: Wenn-dann unter dem Diagramm */
.m-ck-wd { display: flex; gap: 10px; align-items: center; flex-wrap: wrap; margin-top: 8px; }
.m-ck-wd-t { font-weight: 700; color: #7c3aed; } .m-ck-wd-m { min-width: 120px; } .m-ck-wd-z { width: 96px; }
.m-ck-wd-satz { margin-top: 6px; font-size: 13px; color: #6d28d9; white-space: normal; }
body:not(.hell) .m-ck-wd-t, body:not(.hell) .m-ck-wd-satz { color: #c4b5fd; }
/* 1.18: Vorschau beim Überfahren einer Karte */
.m-ck-vor { display: none; margin-top: 6px; font-size: 12px; font-weight: 700; padding: 2px 8px; border-radius: 999px;
  border: 1.5px dashed #f59e0b; color: #b45309; background: color-mix(in srgb, #f59e0b 10%, transparent); width: fit-content; }
.m-ck-vor.an { display: block; } .m-ck-vor.krit { border-color: var(--rot); color: var(--rot);
  background: color-mix(in srgb, var(--rot) 8%, transparent); }
body:not(.hell) .m-ck-vor { color: #fbbf24; }
.m-ck-karte.vorschau { outline: 2px dashed #f59e0b; outline-offset: 1px; }
@media (max-width: 1100px) { .m-ck-kz { grid-template-columns: repeat(2, minmax(0, 1fr)); } .m-ck-haupt { grid-template-columns: 1fr; } }
"""


def _eur(x: float) -> str:
    return f"{round(x):,} €".replace(",", ".")


def _zustand(a, d: dict) -> tuple[set, dict]:
    """Auswahl je Planjahr in der Sitzung: (angehakte Schlüssel, Monat je Schlüssel). Neu, wenn sich die Karten ändern."""
    ks = d["ck_karten"]
    sig = (d["jahr"], tuple(k.schluessel for k in ks))
    if getattr(a, "ck_sig", None) != sig:
        a.ck_sig = sig
        std = ck.standard_auswahl(ks)
        a.ck_an = set(std)
        a.ck_monat = {k.schluessel: (k.zeile.start.month if k.art == "etage" else 0) for k in ks}
        a.ck_offen = set()
    return a.ck_an, a.ck_monat


def auswahl(a, d: dict) -> dict:
    an, monat = _zustand(a, d)
    return {s: monat.get(s, 0) for s in an}


def zeichnen(a) -> None:
    d = a.daten
    ks, bd = d.get("ck_karten") or [], d.get("ck_bedarf")
    if not ks and not bd:
        with a.inhalt:
            leer("Für das Cockpit fehlen Prognose und Renovierungsdaten (Bedarf, Angebote).")
        return
    aw = auswahl(a, d)
    wd = _wenn_dann(a, d, bd)                       # 1.19: angenommener Wert in einem Monat → Bedarf bedingt angepasst
    bd0, bd = bd, (wd.bedarf if wd else bd)
    bw = ck.bewerten(ks, aw, bd, d["budgets"]["bau"], d["andere"].get("bau", 0.0), d["fl"])
    refs: dict = {"bw": bw, "aw": aw, "bd": bd, "wd": wd}
    with a.inhalt, ui.element("div").classes("m-ck"):
        _kacheln(d, bw, bd, refs)
        hinweise = list(bw.hinweise)
        from . import steuerung_kern as sk

        if satz := sk.abgleich_satz(d.get("abgleich") or []):
            hinweise.append(satz)
        if hinweise:
            with ui.element("div").classes("m-ck-hinweise"):
                for h in hinweise[:4]:
                    ui.label("⚠ " + h)
        with ui.element("div").classes("m-ck-haupt"):
            with ui.element("div").classes("m-ck-box"):
                with ui.element("h3"):
                    ui.label(f"Vorhaben & Renovierung {d['jahr']}")
                    ui.label("vorsortiert: A vor B vor C · Haken = im Plan").classes("hint")
                for k in ks:
                    _karte(a, d, k, bw, refs)
                with ui.element("div").classes("m-ck-fuss"):
                    knopf("Übernehmen (vormerken)", lambda: _uebernehmen(a, d), "primaer", "check",
                          "Angehakte Karten vormerken (Etagen im gewählten Monat), abgehakte Vormerkungen entfernen – "
                          "ein Schritt, Rückgängig möglich")
                    knopf("Zurücksetzen", lambda: _zuruecksetzen(a), "leise", "restart_alt",
                          "Auswahl wie vorgemerkt bzw. vorgeschlagen")
                    if aw != ck.standard_auswahl(ks):
                        ui.label("Geändert – erst „Übernehmen“ speichert.").classes("m-zweite m-warn")
            with ui.element("div").classes("m-ck-box"):
                with ui.element("h3"):
                    ui.label("Betten: Decke gegen Bedarf")
                    ui.label("obere Spanne = 8 von 10 Verläufen · Planjahr Jan–Dez").classes("hint")
                if bd:
                    from . import themes

                    dunkel = (themes.AKTIV or {}).get("modus") == "dunkel"
                    t = themes.farben(themes.AKTIV)
                    refs["stil"] = (dunkel, t.get("text", "#334155"))
                    refs["chart"] = ch = ui.echart(ck.diagramm(bd, bw, dunkel, t.get("text", "#334155"), wd=wd)).classes(
                        "m-chart m-dg").style("height:430px")
                    ch.on("m_achse", lambda e: _monat_gewaehlt(a, d, e.args), ["index"])
                    _wenn_dann_zeile(a, d, bd0, bw, wd)
                else:
                    leer("Keine Belegungsprognose – Diagramm nicht möglich.")
                ui.label(_satz(d, ks, aw, bw, bd) + (f" – Achtung: gerechnet mit der Annahme „{rk.MONATE[wd.monat]} "
                                                    f"{round(wd.wert)} belegt“ (Wenn-dann)." if wd else "")).classes(
                    "m-ck-satz").style("margin-top:10px")


def _vor(refs: dict, name: str) -> None:
    refs[name] = ui.label("").classes("m-ck-vor")


def _kacheln(d: dict, bw: ck.Bewertung, bd, refs: dict) -> None:
    with ui.element("div").classes("m-ck-kz"):
        b = bw.budget
        stufe = "krit" if b is not None and bw.verplant > b + 1 else ""
        with ui.element("div").classes(f"m-ck-kachel {stufe}"):
            ui.label(f"Baubudget {d['jahr']} · verfällt").classes("k")
            ui.html(f'<div class="w">{_eur(bw.verplant)} <small>{"von " + _eur(b) if b is not None else "kein Budget gesetzt"}'
                    "</small></div>")
            if b:
                anteil = min(100.0, 100 * bw.verplant / b)
                ui.html(f'<div class="m-ck-balken"><i style="width:{anteil:.1f}%;background:'
                        f'{"var(--rot)" if stufe else "var(--akzent)"}"></i></div>')
            teile = [f"Spanne ± {_eur(bw.bau_spanne)}"]
            if bw.rest is not None:
                teile.append(f"Rest {_eur(bw.rest)}" if bw.rest >= 0 else f"{_eur(-bw.rest)} über Budget")
            if bw.andere_bau:
                teile.append(f"davon andere Vorhaben {_eur(bw.andere_bau)}")
            teile.append("A-Bedarf vollständig drin" if not bw.a_offen else f"{bw.a_offen} A-Zimmer offen")
            ui.label(" · ".join(teile)).classes("s")
            _vor(refs, "budget")
        with ui.element("div").classes("m-ck-kachel"):
            ui.label("Möbel-Antrag").classes("k")
            ui.html(f'<div class="w">{_eur(bw.moebel)} <small>{bw.moebel_zimmer} Zimmer</small></div>')
            ui.label("aus den angehakten Karten (Etage und Zimmer komplett bringen neue Möbel mit)").classes("s")
            _vor(refs, "moebel")
        if bd and bw.knappster is not None:
            r = bw.reserve[bw.knappster]
            st = "krit" if r < 0 else "warn" if r < 10 else "ok"
            with ui.element("div").classes(f"m-ck-kachel {st}"):
                ui.label("Engpass-Radar · knappster Monat").classes("k")
                ui.html(f'<div class="w">{"+" if r >= 0 else "−"}{abs(round(r))} Betten '
                        f"<small>{rk.MONATE[bw.knappster]} {d['jahr']}</small></div>")
                ui.label((f"{len(bw.engpaesse)} Monat(e) mit Engpass" if bw.engpaesse else "kein Monat mit Engpass")
                         + " · gerechnet mit der oberen Spanne").classes("s")
                _vor(refs, "engpass")
        else:
            with ui.element("div").classes("m-ck-kachel"):
                ui.label("Engpass-Radar").classes("k")
                ui.html('<div class="w">–</div>')
                ui.label("keine Prognose für das Planjahr").classes("s")
        with ui.element("div").classes("m-ck-kachel"):
            ui.label("Aufwand").classes("k")
            ui.html(f'<div class="w">{bw.umzuege} <small>Umzüge</small></div>')
            alt = rk.angebote_alt(d["p"], d.get("heute")) if d.get("heute") else []
            ui.label(f"{len(alt)} Angebot(e) älter als 12 Monate" if alt else "Angebote aktuell").classes("s")
            _vor(refs, "umzuege")


def _karte(a, d: dict, k: ck.Karte, bw: ck.Bewertung, refs: dict) -> None:
    an, monat = a.ck_an, a.ck_monat
    ist_an = k.schluessel in an
    m = monat.get(k.schluessel) or k.zeile.start.month
    karte = ui.element("div").classes("m-ck-karte" + ("" if ist_an else " aus"))
    karte.on("mouseenter", lambda k=k, m=m, karte=karte: _vorschau_an(a, d, k, m, refs, karte))
    karte.on("mouseleave", lambda karte=karte: _vorschau_aus(d, refs, karte))
    with karte:
        cb = ui.element("button").classes("m-ck-cb" + (" an" if ist_an else ""))
        with cb:
            if ist_an:
                ui.label("✓")
        attr(cb, title="Im Plan" if ist_an else "Nicht im Plan – anklicken zum Aufnehmen")
        cb.on("click", lambda k=k: _umschalten(a, k))
        with ui.element("div"):
            with ui.element("div").classes("m-ck-titel"):
                ui.label(k.titel)
                if k.klasse:
                    ui.label(f"{k.klasse} · {'Bau' if any(k.klassen_bau) else 'Möbel'}").classes(f"m-ck-pill {k.klasse}")
                ph, lu = d.get("ck_phase") or ("Vorschlag", "")
                t_ = (f"vorgemerkt · {ph}" if k.vorgemerkt else ("Vorschlag" if k.vorschlag else "weitere Etage"))
                attr(ui.label(t_ + (" ⚠" if k.vorgemerkt and lu in ("Freigabe fehlt", "Rechnung fehlt") else "")).classes(
                    "m-ck-phase" + (" vm" if k.vorgemerkt else "")), title=(lu if k.vorgemerkt else "") or "")
        lo, hi = k.kosten.spanne
        hk = rk.HERKUNFT_TEXT.get(k.kosten.herkunft_bau if k.kosten.instandhaltung else k.kosten.herkunft_moebel, "")
        pct = round(100 * (hi - k.kosten.summe) / k.kosten.summe) if k.kosten.summe else 0
        ui.html(f'<div class="m-ck-kosten">{_eur(k.kosten.summe)}<small>± {pct} % · {hk}</small></div>')
        with ui.element("div").classes("m-ck-z2"):
            if k.schiebbar:
                with ui.element("span").classes("m-ck-monat"):
                    z = ui.element("button")
                    with z:
                        ui.label("◄")
                    z.on("click", lambda k=k: _schieben(a, k, -1))
                    ui.label(rk.MONATE[m - 1])
                    w = ui.element("button")
                    with w:
                        ui.label("►")
                    w.on("click", lambda k=k: _schieben(a, k, 1))
                attr(z, title="Früherer möglicher Monat")
                attr(w, title="Späterer möglicher Monat")
            sim = bw
            if not ist_an and k.art == "etage":      # nicht angehakt: Wirkung so, als käme sie zu den angehakten dazu
                sim = ck.bewerten(d["ck_karten"], {**auswahl(a, d), k.schluessel: m}, refs["bd"], None, 0, [])
            text, st = ck.wirkung_text(k, m, sim)
            ui.label(("wenn dazu: " if not ist_an and k.art == "etage" else "") + text).classes(f"m-ck-w {st}")
            if k.art == "etage":
                ui.label(f"{k.umzuege(m)} Umzüge · {k.betten} Betten")
            mehr = ui.element("button").classes("m-ck-mehr")
            with mehr:
                ui.label("Details ▾" if k.schluessel in a.ck_offen else "Details ▸")
            mehr.on("click", lambda k=k: _details(a, k))
        if k.schluessel in a.ck_offen:
            _drawer(k, m, d.get("ck_phase") or ("Vorschlag", ""))


def _drawer(k: ck.Karte, m: int, phase: tuple = ("Vorschlag", "")) -> None:
    with ui.element("div").classes("m-ck-drawer"):
        if k.gruende:
            ui.html("<b>Bedarf</b> " + " · ".join(k.gruende))
        bau, moe = k.klassen_bau, k.klassen_moebel
        ui.html(f"<b>Zimmer</b> {len(k.zimmer_ids)} · Bau A{bau[0]} B{bau[1]} C{bau[2]} · Möbel A{moe[0]} B{moe[1]} C{moe[2]}")
        ui.html(f"<b>Kosten</b> Bau {_eur(k.kosten.instandhaltung)} · Möbel {_eur(k.kosten.investition)} – "
                + ", ".join(f"{t} {_eur(b)}" for t, b in k.kosten.herleitung if b)[:400])
        if k.schiebbar:
            ui.html("<b>Monate</b> (grün = ohne Umzüge, gelb = mit Umzügen, durchgestrichen = nicht möglich)")
            with ui.element("div").classes("m-ck-mt"):
                for i in range(1, 13):
                    x = k.monate.get(i)
                    kl = "nein" if not x or not x.moeglich else ("gut" if not x.umzuege else "eng")
                    s = ui.label(rk.MONATE[i - 1]).classes(kl + (" wahl" if i == m else ""))
                    attr(s, title=("nicht möglich: " + x.grund) if x and not x.moeglich else
                         (f"{x.umzuege} Umzüge" + (f", {x.ohne_ausweich} ohne Ausweich" if x.ohne_ausweich else "")
                          + ("" if x.pruefbar else " · hinter den Buchungen, nicht prüfbar")) if x else "")
        else:
            z = k.zeile
            ui.html(f"<b>Termine</b> Kampagne im Leerstand {z.start:%d.%m.} – {z.ende:%d.%m.%Y}; neu planen unter „Vorhaben“.")
        ui.html("<b>Stand</b>" + ("" if k.vorgemerkt else " – noch nicht vorgemerkt"))
        from .seite_steuerung import phasen_leiste

        phasen_leiste(*(phase if k.vorgemerkt else ("Vorschlag", "")),
                      "Stand des Vorhabens „Renovierung <Jahr>“ – Freigabe, Auftrag und Rechnungen pflegen unter „Vorhaben“")


def _satz(d: dict, ks: list, aw: dict, bw: ck.Bewertung, bd) -> str:
    gew = [k for k in ks if k.schluessel in aw]
    if not gew:
        return "Nichts angehakt – es ist keine Renovierung geplant."
    nb = sum(k.klassen_bau[1] for k in gew if k.art != "moebel")
    na = sum(k.klassen_bau[0] for k in gew if k.art != "moebel")
    s = (f"Vorschlag für die Vorlage: Mit {_eur(bw.verplant)} werden {d['jahr']} {na} Zimmer mit A-Bedarf und {nb} mit "
         f"B-Bedarf erneuert")
    if bd and bw.knappster is not None:
        r = bw.reserve[bw.knappster]
        s += (f"; der knappste Monat ist der {rk.MONATE[bw.knappster]} mit {round(r)} freien Betten" if r >= 0
              else f"; im {rk.MONATE[bw.knappster]} fehlen {abs(round(r))} Betten")
    s += f", nötig sind {bw.umzuege} Umzüge."
    if bw.a_offen:
        s += f" {bw.a_offen} Zimmer mit A-Bedarf bleiben offen."
    return s


def _wenn_dann(a, d: dict, bd) -> ck.WennDann | None:
    w = getattr(a, "ck_wd", None)
    if not w or not bd or w[0] != d["jahr"]:
        return None
    return ck.wenn_dann(bd, w[1], w[2], d.get("ck_rho", ck.BEHARRUNG_STANDARD))


def _kuenftig(bd) -> list[int]:
    return [i for i in range(12) if bd and not bd.ist[i] and bd.erwartet[i] is not None]


def _wenn_dann_zeile(a, d: dict, bd0, bw, wd) -> None:
    """Monat wählen (oder im Diagramm anklicken), Wert eingeben, Enter – Kacheln, Karten und Diagramm rechnen damit."""
    monate = _kuenftig(bd0)
    if not monate:
        return
    sel = getattr(a, "ck_wd_monat", None)
    sel = wd.monat if wd else (sel if sel in monate else monate[0])
    with ui.element("div").classes("m-ck-wd"):
        ui.label("Wenn-dann").classes("m-ck-wd-t")
        auswahl_m = ui.select({i: f"{rk.MONATE[i]} {d['jahr']}" for i in monate}, value=sel).props(
            'dense outlined options-dense popup-content-class="m-popup"').classes("m-ck-wd-m")
        zahl = ui.number(value=round(wd.wert if wd else bd0.erwartet[sel]), min=0, step=1, format="%.0f").props(
            "dense outlined").classes("m-ck-wd-z")
        attr(zahl, title="Angenommene Belegung (Betten) in diesem Monat – Enter rechnet")
        ui.label(f"Planwert {round(bd0.erwartet[sel])}").classes("m-zweite")

        async def rechnen():
            if zahl.value is None:
                return
            a.ck_wd = (d["jahr"], int(auswahl_m.value), float(zahl.value))
            await a.setzen(laden=False)

        async def monat_neu(e):
            a.ck_wd_monat = int(e.value)
            a.ck_wd = None
            await a.setzen(laden=False)

        auswahl_m.on_value_change(monat_neu)
        zahl.on("keydown.enter", rechnen)
        zahl.on("blur", rechnen)
        knopf("Rechnen", rechnen, "leise", "play_arrow", "Mit diesem Wert rechnen")
        if wd:
            knopf("Aus", lambda: _wenn_dann_aus(a), "leise", "close", "Wenn-dann ausschalten")
    if wd:
        bw0 = ck.bewerten(d["ck_karten"], auswahl(a, d), bd0, d["budgets"]["bau"], d["andere"].get("bau", 0.0), d["fl"])
        ui.label(ck.wenn_dann_satz(wd, bw0, bw)).classes("m-ck-wd-satz")


async def _monat_gewaehlt(a, d: dict, args) -> None:
    i = (args or {}).get("index") if isinstance(args, dict) else None
    if i is None or i not in _kuenftig(d.get("ck_bedarf")):
        return
    a.ck_wd_monat = int(i)
    a.ck_wd = None
    await a.setzen(laden=False)


async def _wenn_dann_aus(a) -> None:
    a.ck_wd = None
    await a.setzen(laden=False)


def _vorschau_an(a, d: dict, k: ck.Karte, m: int, refs: dict, karte) -> None:
    """1.18: Was wäre, wenn diese Karte an- bzw. abgehakt würde – Kacheln und Diagramm, ohne die Seite neu aufzubauen."""
    v = ck.vorschau(d["ck_karten"], refs["aw"], k, m, refs["bd"], d["budgets"]["bau"],
                    d["andere"].get("bau", 0.0), d["fl"], refs["bw"])
    texte = ck.vorschau_texte(v, d["jahr"])
    for name in ("budget", "moebel", "engpass", "umzuege"):
        lbl = refs.get(name)
        if lbl is None:
            continue
        t = texte.get(name, "")
        lbl.set_text(("Wenn dazu – " if v.an else "Wenn weg – ") + t.replace("Vorschau: ", "") if t else "")
        krit = (name == "budget" and v.bw.rest is not None and v.bw.rest < 0) or \
               (name == "engpass" and v.knapp_nachher is not None and v.knapp_nachher[1] < 0)
        lbl.classes(remove="an krit")
        if t:
            lbl.classes(add="an krit" if krit else "an")
    karte.classes(add="vorschau")
    if refs.get("chart") is not None and refs.get("bd"):
        _diagramm_setzen(refs, ck.diagramm(refs["bd"], refs["bw"], *refs["stil"], vor=v.bw, wd=refs.get("wd")))


def _vorschau_aus(d: dict, refs: dict, karte) -> None:
    for name in ("budget", "moebel", "engpass", "umzuege"):
        if refs.get(name) is not None:
            refs[name].classes(remove="an krit")
    karte.classes(remove="vorschau")
    if refs.get("chart") is not None and refs.get("bd"):
        _diagramm_setzen(refs, ck.diagramm(refs["bd"], refs["bw"], *refs["stil"], wd=refs.get("wd")))


def _diagramm_setzen(refs: dict, opt: dict) -> None:
    ch = refs["chart"]
    ch.options.clear()
    ch.options.update(opt)
    ch.update()


async def _umschalten(a, k: ck.Karte) -> None:
    (a.ck_an.discard if k.schluessel in a.ck_an else a.ck_an.add)(k.schluessel)
    await a.setzen(laden=False)


async def _schieben(a, k: ck.Karte, schritt: int) -> None:
    m = a.ck_monat.get(k.schluessel) or k.zeile.start.month
    for _ in range(12):
        m = (m - 1 + schritt) % 12 + 1
        x = k.monate.get(m)
        if x and x.moeglich:
            break
    a.ck_monat[k.schluessel] = m
    await a.setzen(laden=False)


async def _details(a, k: ck.Karte) -> None:
    (a.ck_offen.discard if k.schluessel in a.ck_offen else a.ck_offen.add)(k.schluessel)
    await a.setzen(laden=False)


async def _zuruecksetzen(a) -> None:
    a.ck_sig = None
    await a.setzen(laden=False)


async def _uebernehmen(a, d: dict) -> None:
    if await a.aendern(ck.uebernehmen_schritt, d["ck_karten"], auswahl(a, d)):
        a.ck_sig = None
