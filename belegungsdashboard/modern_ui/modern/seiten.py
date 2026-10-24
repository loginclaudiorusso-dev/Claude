"""Seiten Zeitstrahl, Reinigung, Mieter, Auswertung und Verwalten. Jede Seite hat ``daten`` (läuft im Hintergrund,
ohne Oberfläche) und ``zeichnen`` (baut Kopf-Werkzeuge, Leiste und Inhalt). Formulare öffnen sich im Panel rechts."""

from __future__ import annotations

import html
import os
import sys
import tempfile
from datetime import date, timedelta
from pathlib import Path

from nicegui import run, ui

from . import seiten_kern as sk
from .kern import kurz
from .ui_bausteine import attr, knopf, leer, segmente

E = html.escape


def _datei_oeffnen(ziel: str) -> bool:
    """Datei/Link mit dem Standardprogramm öffnen (Windows). False = bitte über den Browser."""
    if sys.platform == "win32":
        try:
            os.startfile(ziel)          # noqa: S606 – nur eigene Dateien bzw. mailto
            return True
        except OSError:
            return False
    return False


# =======================================================================================
# Zeitstrahl
# =======================================================================================

def zs_daten(a) -> None:
    hs = sk.haeuser(a.stand)
    if a.zs_haus not in hs:
        a.zs_haus = hs[0] if hs else ""
    a.daten = sk.zeitstrahl(a.stand, a.zs_haus, a.zs_start, a.zs_tage, a.heute) if a.zs_haus else []
    a.zs_haeuser = hs


def zs_zeichnen(a) -> None:
    with a.werkzeuge:
        segmente({h: f"Haus {h}" for h in a.zs_haeuser}, a.zs_haus, lambda h: a.setzen(zs_haus=h))
        knopf("", lambda: a.setzen(zs_start=a.zs_start - timedelta(days=7)), "leise", "chevron_left", "Eine Woche zurück")
        knopf("Heute", lambda: a.setzen(zs_start=a.heute - timedelta(days=a.heute.weekday())), "leise")
        knopf("", lambda: a.setzen(zs_start=a.zs_start + timedelta(days=7)), "leise", "chevron_right", "Eine Woche weiter")
    ende = a.zs_start + timedelta(days=a.zs_tage - 1)
    with a.leiste:
        n_bel = sum(1 for z in a.daten for b in z.balken if b.art in ("belegt", "geplant", "konflikt"))
        ui.html(f'<span class="m-kpi"><b>{len(a.daten)}</b> Zimmer<span class="m-punktt">·</span>'
                f'{a.zs_start:%d.%m.} – {ende:%d.%m.%Y}<span class="m-punktt">·</span><b>{n_bel}</b> Belegungen</span>',
                sanitize=False)
        ui.html('<span class="m-legende"><i class="belegt"></i>belegt<i class="geplant"></i>im Programm geplant'
                '<i class="gesperrt"></i>gesperrt<i class="konflikt"></i>Konflikt</span>', sanitize=False).style(
            "margin-left: auto")
        segmente({14: "2 Wochen", 28: "4 Wochen", 56: "8 Wochen"}, a.zs_tage, lambda t: a.setzen(zs_tage=t))
    with a.inhalt:
        if not a.daten:
            leer("Keine Zimmer in diesem Haus.")
            return
        ui.html(_zs_html(a), sanitize=False).classes("m-zs-wrap")


def _zs_html(a) -> str:
    t = a.zs_tage
    tage = [a.zs_start + timedelta(days=i) for i in range(t)]
    teile = ['<div class="m-zs" style="--tage:%d">' % t, '<div class="m-zs-kopf"><div class="m-zs-lab"></div><div class="m-zs-spur">']
    for i, d in enumerate(tage):
        kl = "we" if d.weekday() >= 5 else ""
        kl += " heute" if d == a.heute else ""
        text = f"{sk.WT[d.weekday()][0]}<br>{d.day}" if t <= 28 else (f"{d:%d.%m.}" if d.weekday() == 0 else "")
        teile.append(f'<div class="m-zs-tag {kl}" style="left:calc({i} * 100% / var(--tage))">{text}</div>')
    teile.append("</div></div>")
    hintergrund = "".join(f'<div class="m-zs-we" style="left:calc({i} * 100% / var(--tage))"></div>'
                          for i, d in enumerate(tage) if d.weekday() >= 5)
    if a.zs_start <= a.heute < a.zs_start + timedelta(days=t):
        hintergrund += f'<div class="m-zs-jetzt" style="left:calc({(a.heute - a.zs_start).days + .5} * 100% / var(--tage))"></div>'
    for z in a.daten:
        hinweis = f'<span class="m-zs-h" title="{E(z.hinweis)}">●</span>' if z.hinweis else ""
        teile.append(f'<div class="m-zs-zeile"><div class="m-zs-lab" title="{E(z.lage)}">'
                     f'<b>{E(z.kurz)}</b>{" · DZ" if z.betten > 1 else ""}{hinweis}</div><div class="m-zs-spur">{hintergrund}')
        for b in z.balken:
            kl = f"m-zs-b {b.art}" + (" ol" if b.offen_links else "") + (" or" if b.offen_rechts else "")
            teile.append(f'<div class="{kl}" title="{E(b.titel)}" style="left:calc({b.start} * 100% / var(--tage));'
                         f'width:calc({b.tage} * 100% / var(--tage) - 2px)"><span>{E(b.text)}</span></div>')
        teile.append("</div></div>")
    teile.append("</div>")
    return "".join(teile)


# =======================================================================================
# Reinigung
# =======================================================================================

def rg_daten(a) -> None:
    von, bis = sk.zeitraum(a.rg_zeitraum, a.heute)
    a.daten = sk.reinigung(a.stand, von, bis, a.heute)
    a.rg_von, a.rg_bis = von, bis


RG_SPALTEN = "36px 70px minmax(80px, .8fr) minmax(90px, 1fr) minmax(100px, .9fr) minmax(120px, 1.5fr) minmax(100px, 1.2fr) 140px 36px"


def rg_zeichnen(a) -> None:
    with a.werkzeuge:
        segmente(sk.ZEITRAUM, a.rg_zeitraum, lambda w: a.setzen(rg_zeitraum=w))
        knopf("Zimmer hinzufügen", lambda: _rg_hinzu_panel(a), "", "add")
        knopf("Drucken", lambda: _rg_drucken(a), "", "print")
    n = sk.reinigung_zaehlen(a.daten)
    eilig = [z for z in a.daten if not z.erledigt and z.prio <= 1]
    with a.leiste:
        ui.html(f'<span class="m-kpi"><b>{n["offen"]}</b> offen<span class="m-punktt">·</span>'
                f'<b style="color:var(--rot)">{n["eilig"]}</b> eilig<span class="m-punktt">·</span>'
                f'<b>{n["erledigt"]}</b> erledigt<span class="m-punktt">·</span>{a.rg_von:%d.%m.} – {a.rg_bis:%d.%m.}</span>',
                sanitize=False)
        if eilig:
            knopf(f"Alle {len(eilig)} eiligen als gereinigt markieren" if len(eilig) > 1 else "Eilige als gereinigt markieren",
                  lambda: a.aendern(sk.reinigung_setzen, [z.schluessel for z in eilig], True, a.rg_von, a.rg_bis),
                  "gruen", "done_all")
        segmente({"offen": f"Offen {n['offen']}", "alle": f"Alle {len(a.daten)}"}, a.rg_filter,
                 lambda f: a.setzen(rg_filter=f, laden=False))
    with a.inhalt:
        zs = [z for z in a.daten if a.rg_filter == "alle" or not z.erledigt]
        if not zs:
            leer("Keine offenen Reinigungen in diesem Zeitraum." if a.daten else "Keine Reinigungen in diesem Zeitraum.")
            return
        with ui.element("div").classes("m-raster m-tkopf").style(f"grid-template-columns:{RG_SPALTEN}"):
            for t in ("", "Zimmer", "Lage", "Art", "Auszug", "Danach", "Sauber bis", "Priorität", ""):
                ui.label(t)
        for z in zs:
            with ui.element("div").classes("m-raster m-zeile" + (" fertig" if z.erledigt else "")).style(
                    f"grid-template-columns:{RG_SPALTEN}"):
                with ui.element("div"):
                    b = ui.element("button").classes("m-haken" + (" an" if z.erledigt else ""))
                    attr(b, title="Als gereinigt markieren" if not z.erledigt else "Wieder offen", aria_pressed=str(z.erledigt).lower())
                    with b:
                        ui.icon("check")
                    b.on("click", lambda z=z: a.aendern(sk.reinigung_setzen, [z.schluessel], not z.erledigt, a.rg_von, a.rg_bis))
                attr(ui.label(z.zimmer).classes("m-name"), title=z.details)
                ui.label(z.lage).classes("m-zweite")
                attr(ui.label(z.art + (f" · {z.notiz}" if z.notiz and z.notiz != z.art else "")).classes("m-zweite"),
                     title=z.notiz or z.art)
                ui.label(z.auszug).classes("m-mono")
                attr(ui.label(z.danach).classes("m-zweite"), title=z.details)
                ui.label(z.frist).classes("m-mono")
                with ui.element("div"):
                    ui.label(z.prio_text).classes(f"m-pille {z.stufe}")
                with ui.element("div"):
                    if z.manuell_id:
                        knopf("", lambda z=z: a.aendern(sk.reinigung_entfernen, z.manuell_id), "leise", "close",
                              "Von Hand hinzugefügte Reinigung entfernen")


def _rg_hinzu_panel(a) -> None:
    def bauen():
        ui.label("Ein Zimmer zusätzlich auf die Reinigungsliste setzen, z. B. Zwischen- oder Grundreinigung.").classes("m-ptext")
        zimmer = ui.select(sk.zimmer_kurzliste(a.stand), label="Zimmer", with_input=True).classes("m-feld").props(
            'dense outlined dark options-dense popup-content-class="m-popup"')
        tag = ui.input("Tag", value=a.heute.isoformat()).classes("m-feld").props("dense outlined dark type=date")
        from belegung import zimmerplan as zp

        grund = ui.select(zp.REINIGUNG_GRUENDE, value=zp.REINIGUNG_GRUENDE[0], label="Grund", new_value_mode="add-unique",
                          with_input=True).classes("m-feld").props('dense outlined dark options-dense popup-content-class="m-popup"')

        async def speichern():
            if not zimmer.value:
                a.toast("Bitte ein Zimmer wählen.", fehler=True)
                return
            try:
                d = date.fromisoformat(tag.value)
            except (TypeError, ValueError):
                a.toast("Bitte einen Tag wählen.", fehler=True)
                return
            if await a.aendern(sk.reinigung_hinzu, zimmer.value, d, grund.value or ""):
                a.panel_zu()

        with ui.element("div").classes("m-paktionen"):
            knopf("Hinzufügen", speichern, "primaer", "add")
            knopf("Abbrechen", a.panel_zu, "leise")

    a.panel("Zimmer zur Reinigung hinzufügen", bauen)


async def _rg_drucken(a) -> None:
    text = await run.io_bound(sk.reinigung_druck, a.rg_von, a.rg_bis, a.heute)
    pfad = Path(tempfile.gettempdir()) / f"Reinigungsliste_{a.rg_von:%Y-%m-%d}.html"
    pfad.write_text(text.replace("</body>", "<script>window.print()</script></body>"), encoding="utf-8")
    if not _datei_oeffnen(str(pfad)):
        a.toast(f"Druckansicht gespeichert: {pfad}", rueck=False)
    else:
        a.toast("Druckansicht geöffnet", rueck=False)


# =======================================================================================
# Mieter
# =======================================================================================

def mt_daten(a) -> None:
    a.daten = sk.mieter(a.heute)


MT_SPALTEN = "28px 70px minmax(160px, 1.3fr) 90px 190px minmax(130px, 1fr) minmax(170px, 1fr)"


def mt_zeichnen(a) -> None:
    vertraege, weitere = a.daten
    offen = [m for m in vertraege if m.mail_offen]
    with a.leiste:
        laufend = sum(1 for m in vertraege if m.bis >= a.heute)
        ui.html(f'<span class="m-kpi"><b>{laufend}</b> laufende Verträge<span class="m-punktt">·</span>'
                f'<b>{len(offen)}</b> Mail zum Vertragsende offen<span class="m-punktt">·</span>'
                f'<b>{len(weitere)}</b> weitere laut Gebäudeplan</span>', sanitize=False)
        ui.label("Verträge anlegen, verlängern und Unterlagen: im Hauptprogramm").classes("m-zweite").style("margin-left:auto")
    with a.inhalt:
        if not vertraege and not weitere:
            leer("Keine Mieter.")
            return
        if vertraege:
            with ui.element("div").classes("m-raster m-tkopf").style(f"grid-template-columns:{MT_SPALTEN}"):
                for t in ("", "Nr.", "Name", "Zimmer", "Zeitraum", "Status", "Mail zum Vertragsende"):
                    ui.label(t)
            for m in vertraege:
                with ui.element("div").classes("m-raster m-zeile" + (" fertig" if m.bis < a.heute else "")).style(
                        f"grid-template-columns:{MT_SPALTEN}"):
                    with ui.element("div"):
                        ui.element("div").classes(f"m-ampel {m.stufe}")
                    ui.label(m.nr).classes("m-mono")
                    with ui.element("div"):
                        ui.label(m.name).classes("m-name")
                        if m.email:
                            ui.label(m.email).classes("m-zweite")
                    ui.label(m.zimmer).classes("m-mono")
                    ui.label(f"{m.von:%d.%m.%Y} – {m.bis:%d.%m.%Y}").classes("m-mono")
                    ui.label(m.status).classes("m-zweite")
                    with ui.element("div").classes("m-hinweis"):
                        if m.mail_offen:
                            knopf("Mail vorbereiten", lambda m=m: _mail_panel(a, m), "gruen", "mail")
                        elif m.mail_am:
                            ui.label(f"vorbereitet am {date.fromisoformat(m.mail_am):%d.%m.%Y}").classes("t")
                            knopf("", lambda m=m: _mail_panel(a, m), "leise", "mail", "Noch einmal vorbereiten")
                        elif m.bis >= a.heute:
                            knopf("Mail", lambda m=m: _mail_panel(a, m), "leise", "mail", "Mail zum Vertragsende vorbereiten")
        if weitere:
            ui.label("Weitere Mieter laut Gebäudeplan (ohne Vertrag in diesem Programm)").classes("m-abschnitt")
            for name, zimmer, zeit in weitere:
                with ui.element("div").classes("m-raster m-zeile").style(f"grid-template-columns:{MT_SPALTEN}"):
                    ui.label("")
                    ui.label("–").classes("m-mono")
                    ui.label(name).classes("m-name")
                    ui.label(zimmer).classes("m-mono")
                    ui.label(zeit).classes("m-mono")
                    ui.label("")
                    ui.label("")


def _mail_panel(a, m) -> None:
    from belegung import mieter as mt

    def bauen():
        ui.label(f"{m.name} · Zimmer {m.zimmer} · Vertrag bis {m.bis:%d.%m.%Y}. Die Mail öffnet sich als Entwurf in "
                 "Outlook – geprüft und abgeschickt wird von Ihnen.").classes("m-ptext")
        art = ui.select(mt.MAIL_ARTEN, value="anfrage", label="Art").classes("m-feld").props(
            'dense outlined dark options-dense popup-content-class="m-popup"')
        an = ui.input("An (E-Mail)", value=m.email).classes("m-feld").props("dense outlined dark")
        betreff = ui.input("Betreff").classes("m-feld").props("dense outlined dark")
        text = ui.textarea("Text").classes("m-feld").props("outlined dark autogrow")

        def fuellen():
            try:
                _e, b, t = sk.mieter_mail(m.nr, art.value, a.heute)
            except ValueError as exc:
                a.toast(str(exc), fehler=True)
                return
            betreff.value, text.value = b, t

        art.on_value_change(lambda _e: fuellen())
        fuellen()

        async def oeffnen():
            if not (an.value or "").strip() or "@" not in an.value:
                a.toast("Bitte eine E-Mail-Adresse eintragen.", fehler=True)
                return
            link = await run.io_bound(sk.mail_oeffnen, an.value.strip(), betreff.value, text.value)
            if link and not _datei_oeffnen(link):
                ui.navigate.to(link)
            if await a.aendern(sk.mieter_mail_vermerken, m.nr, an.value.strip()):
                a.panel_zu()

        with ui.element("div").classes("m-paktionen"):
            knopf("In Outlook öffnen", oeffnen, "primaer", "open_in_new")
            knopf("Abbrechen", a.panel_zu, "leise")

    a.panel("Mail zum Vertragsende", bauen)


# =======================================================================================
# Auswertung
# =======================================================================================

def aw_daten(a) -> None:
    a.daten = sk.auswertung(a.stand, a.heute, 12)


STUFE_AW = {"ok": "ok", "knapp": "warn", "kritisch": "krit"}


def aw_zeichnen(a) -> None:
    aw: sk.Auswertung = a.daten
    with a.leiste:
        tief = min(aw.wochen, key=lambda w: w.frei_nach, default=None)
        ui.html(f'<span class="m-kpi"><b>{aw.offen}</b> Anreisen ohne Zimmer in 12 Wochen<span class="m-punktt">·</span>'
                f'<b>{aw.ohne_platz}</b> fänden keins<span class="m-punktt">·</span>knappste Woche: '
                f'<b>{E(tief.kw) if tief else "–"}</b> ({tief.frei_nach if tief else 0} frei)</span>', sanitize=False)
    with a.inhalt:
        with ui.element("div").classes("m-zwei"):
            with ui.element("section").classes("m-block"):
                ui.label("Freie Zimmer je Woche").classes("m-btitel")
                ui.label("Ganz freie Zimmer (ohne Gästezimmer). „Nach Planung“: wenn alle bekannten Anreisen nach den "
                         "Regeln ein Zimmer bekommen.").classes("m-ptext")
                hoechst = max([w.frei_jetzt for w in aw.wochen] + [1])
                with ui.element("div").classes("m-aw-tab"):
                    for t in ("Woche", "jetzt", "nach Planung", "EMR", "Doppel"):
                        ui.label(t).classes("k")
                    for w in aw.wochen:
                        with ui.element("div").classes("m-aw-kw"):
                            ui.element("div").classes(f"m-ampel {STUFE_AW[w.stufe]}").style("margin:0 8px 0 0")
                            ui.label(w.kw)
                        ui.label(str(w.frei_jetzt)).classes("m-mono")
                        with ui.element("div").classes("m-aw-balken"):
                            with ui.element("div").classes("m-spur"):
                                ui.element("div").classes(f"m-bar {STUFE_AW[w.stufe]}").style(
                                    f"width:{max(2, round(100 * w.frei_nach / hoechst))}%")
                            ui.label(str(w.frei_nach)).classes("m-mono")
                        ui.label(str(w.emr)).classes("m-mono")
                        ui.label(str(w.doppel)).classes("m-mono")
            with ui.element("section").classes("m-block"):
                ui.label(f"Belegung heute je Haus").classes("m-btitel")
                ui.label("Anteil belegter Zimmer an den nutzbaren (ohne gesperrte, ohne Gästezimmer).").classes("m-ptext")
                for h in aw.haeuser:
                    with ui.element("div").classes("m-aw-haus"):
                        ui.label(f"Haus {h.haus}").classes("m-name")
                        with ui.element("div").classes("m-aw-balken"):
                            with ui.element("div").classes("m-spur"):
                                ui.element("div").classes("m-bar akzent").style(f"width:{max(1, h.quote)}%")
                            ui.label(f"{h.quote} %").classes("m-mono")
                        ui.label(f"{h.belegt} belegt · {h.frei} frei · {h.gesperrt} gesperrt").classes("m-zweite")


# =======================================================================================
# Verwalten
# =======================================================================================

def vw_daten(a) -> None:
    a.daten = {"stand": sk.datenstand(a.stand), "plan": sk.neuer_plan(), "einst": sk.einstellungen()}


def vw_zeichnen(a) -> None:
    d = a.daten
    with a.inhalt:
        with ui.element("div").classes("m-zwei"):
            with ui.element("section").classes("m-block"):
                ui.label("Datenstand").classes("m-btitel")
                for bereich, wert, hinweis in d["stand"]:
                    with ui.element("div").classes("m-dl"):
                        ui.label(bereich).classes("k")
                        with ui.element("div"):
                            attr(ui.label(wert).classes("v"), title=wert)
                            if hinweis:
                                ui.label(hinweis).classes("m-zweite")
                from belegung import konfig

                with ui.element("div").classes("m-paktionen"):
                    knopf("Datenordner öffnen", lambda: _datei_oeffnen(str(konfig.datenordner())) or a.toast(
                        str(konfig.datenordner()), rueck=False), "", "folder_open")
                    knopf("Neu laden", a.laden, "leise", "refresh")
            with ui.element("section").classes("m-block"):
                ui.label("Gebäudeplan").classes("m-btitel")
                if d["plan"] is None:
                    ui.label("Kein neuer Gebäudeplan im Ordner „Gebaeudeplan“. Neue Word-Datei dort ablegen – sie wird "
                             "hier geprüft, bevor sie gilt.").classes("m-ptext")
                else:
                    plan, kennung, unterschiede = d["plan"]
                    from belegung import planabgleich as pa

                    ui.label(f"Neu im Ordner: {plan.datei}" + (f" (Stand {plan.stand:%d.%m.%Y})" if plan.stand else "")
                             ).classes("m-name")
                    ui.label(pa.zusammenfassung(unterschiede) if unterschiede else
                             "Keine Unterschiede zum Zimmerplan.").classes("m-ptext")
                    with ui.element("div").classes("m-paktionen"):
                        if unterschiede:
                            knopf("Prüfen und übernehmen …", lambda: _plan_panel(a, plan, kennung, unterschiede), "primaer")
                        else:
                            knopf("Übernehmen", lambda: a.aendern(sk.plan_uebernehmen, plan, [], kennung), "primaer")
                ui.label("Einstellungen").classes("m-btitel").style("margin-top:18px")
                for k, (text, typ, _s) in sk.EINSTELLUNGEN.items():
                    with ui.element("div").classes("m-einst"):
                        ui.label(text).classes("m-ptext")
                        if typ is bool:
                            ui.switch(value=d["einst"][k], on_change=lambda e, k=k: a.aendern(
                                sk.einstellung_setzen, k, e.value)).props("dense color=indigo-4")
                        else:
                            n = ui.number(value=d["einst"][k], min=0, max=7, step=1, format="%d").classes("m-feld klein").props(
                                "dense outlined dark")
                            n.on("blur", lambda _e, k=k, n=n: a.aendern(sk.einstellung_setzen, k, int(n.value or 0))
                                 if int(n.value or 0) != a.daten["einst"][k] else None)


def _plan_panel(a, plan, kennung, unterschiede) -> None:
    def bauen():
        ui.label("Was im neuen Gebäudeplan anders ist als jetzt im Zimmerplan. Bei eigenen Einträgen wählen Sie, was "
                 "gelten soll. Alles andere kommt aus dem neuen Gebäudeplan. Rückgängig ist möglich.").classes("m-ptext")
        boxen = []
        with ui.element("div").classes("m-paktionen"):
            def alle(vorrang):
                for u, box in boxen:
                    ziel = vorrang if vorrang in u.optionen else ("entfernen" if vorrang == "plan" else "planung")
                    if ziel in u.optionen:
                        box.value = ziel
            knopf("Alles aus dem neuen Plan", lambda: alle("plan"), "")
            knopf("Alle eigenen behalten", lambda: alle("planung"), "")
        with ui.element("div").classes("m-plan-liste"):
            for u in unterschiede:
                with ui.element("div").classes("m-plan-u"):
                    ui.label(f"{u.name}").classes("m-name")
                    ui.label(u.art_text).classes("m-zweite")
                    if u.system:
                        ui.label(f"Jetzt: {u.system}").classes("m-zweite")
                    if u.plan:
                        ui.label(f"Neuer Plan: {u.plan}").classes("m-zweite")
                    if u.entscheidbar:
                        box = ui.select(u.optionen, value=u.wahl).classes("m-feld").props(
                            'dense outlined dark options-dense popup-content-class="m-popup"')
                        box.on_value_change(lambda e, u=u: setattr(u, "wahl", e.value))
                        boxen.append((u, box))
                    else:
                        ui.label(u.info or "wird übernommen").classes("m-zweite").style("color: var(--text3)")

        async def los():
            if await a.aendern(sk.plan_uebernehmen, plan, unterschiede, kennung):
                a.panel_zu()

        with ui.element("div").classes("m-paktionen"):
            knopf("Übernehmen", los, "primaer", "check")
            knopf("Abbrechen", a.panel_zu, "leise")

    a.panel(f"Gebäudeplan prüfen · {len(unterschiede)} Unterschiede", bauen)


SEITEN = {
    "zeitstrahl": ("Zeitstrahl", "view_timeline", zs_daten, zs_zeichnen),
    "reinigung": ("Reinigung", "cleaning_services", rg_daten, rg_zeichnen),
    "mieter": ("Mieter", "key", mt_daten, mt_zeichnen),
    "auswertung": ("Auswertung", "insights", aw_daten, aw_zeichnen),
    "verwalten": ("Verwalten", "settings", vw_daten, vw_zeichnen),
}
