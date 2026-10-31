"""Seite „Assistenz“: Aufträge in normalen Sätzen (verstehen → prüfen → ausführen), Mails (erkennen → zuordnen →
umsetzen, Posteingang) und Fragen an die Zahlen (offline aus den Daten, optional mit KI)."""

from __future__ import annotations

from datetime import date, datetime

from nicegui import run, ui

from belegung import anreiseliste, assistenz, mails
from belegung import termine as tm
from belegung import zimmerplan as zp

from .kern import _schritt
from .ui_bausteine import attr, knopf, leer, segmente
from .standort_kern import kurz as zkurz

ANSICHTEN = {"auftraege": "Aufträge", "mails": "Mails", "fragen": "Fragen & Zahlen"}
BEISPIEL = ("z. B.  6-403 Fliegen beseitigen bis 1.11.26\n        Nachname, Vorname vom 26.06.2025 bis 24.06.2027 in 2-408\n"
            "        2-115 Heizung erledigt\n        Freitag 10 Uhr Teambesprechung")


def daten(a) -> None:
    ansicht = a.ansicht_von("assistenz", "auftraege")
    if ansicht == "auftraege":
        a.daten = {"verlauf": assistenz.verlauf()[:20]}
    elif ansicht == "mails":
        a.daten = {"eingaenge": mails.eingaenge()}
    else:
        from belegung.assistent.antworten import BEISPIELE

        a.daten = {"beispiele": BEISPIELE[:6]}


def zeichnen(a) -> None:
    ansicht = a.ansicht_von("assistenz", "auftraege")
    with a.werkzeuge:
        segmente(ANSICHTEN, ansicht, lambda v: a.oeffnen("assistenz", ansicht=v))
    {"auftraege": _auftraege, "mails": _mails, "fragen": _fragen}[ansicht](a)


# =======================================================================================
# Aufträge
# =======================================================================================

def _auftraege(a) -> None:
    with a.inhalt:
        with ui.element("div").classes("m-zwei"):
            with ui.element("section").classes("m-block"):
                ui.label("Was ist zu tun?").classes("m-btitel")
                ui.label("Ganz normal eintippen – eine Zeile je Auftrag. Zimmer, Datum, Mangel und Personen werden "
                         "erkannt; vor dem Ausführen sehen Sie alles und können abwählen. „bis …“ = Frist, „am …“ = "
                         "Termin, „erledigt“ hakt ab, „Name, Vorname vom … bis … in 2-408“ pflegt ein.").classes("m-ptext")
                eingabe = ui.textarea(placeholder=BEISPIEL, value=a.as_text).classes("m-feld").props("outlined dark autogrow")
                vorschau = ui.element("div").classes("m-plan-liste")

                async def verstehen():
                    a.as_text = eingabe.value or ""
                    zeilen = [z.strip() for z in a.as_text.splitlines() if z.strip()]
                    if not zeilen:
                        return
                    bekannt = {z.id for z in a.stand.zimmer}
                    vs = await run.io_bound(assistenz.verstehen_alle, "\n".join(zeilen), bekannt)
                    fragen = [v.eingabe for v in vs if assistenz.ist_frage(v.eingabe) and not (v.name or v.reservierung or v.kopf)]
                    a.as_verstanden = [v for v in vs if v.eingabe not in fragen]
                    _vorschau(a, vorschau, eingabe)
                    if fragen:
                        a.toast(f"{len(fragen)} Frage(n) – bitte unter „Fragen & Zahlen“ stellen.", rueck=False)

                eingabe.on("keydown.ctrl.enter", verstehen)
                with ui.element("div").classes("m-paktionen"):
                    knopf("Verstehen", verstehen, "primaer", "auto_awesome")
                    ui.label("Strg+Enter").classes("m-taste")
                if a.as_verstanden:
                    _vorschau(a, vorschau, eingabe)
            with ui.element("section").classes("m-block"):
                ui.label("Zuletzt erledigt").classes("m-btitel")
                ui.label("Was die Assistenz eingetragen hat – „Rückgängig“ nimmt einen Auftrag ganz zurück.").classes("m-ptext")
                if not a.daten["verlauf"]:
                    ui.label("Noch nichts.").classes("m-ptext")
                for e in a.daten["verlauf"]:
                    with ui.element("div").classes("m-notiz"):
                        attr(ui.label(" / ".join(e["eingaben"])).classes("m-ptext").style("color:var(--text)"),
                             title=" · ".join(e["erledigt"]))
                        ui.label(f"{datetime.fromisoformat(e['zeit']):%d.%m. %H:%M} · " + (" · ".join(e["erledigt"]) or "–")
                                 ).classes("m-zweite")
                        if e.get("zurueck"):
                            ui.label("zurückgenommen").classes("m-zweite")
                        else:
                            knopf("", lambda i=e["id"]: _rueck(a, i), "leise", "undo", "Diesen Auftrag zurücknehmen")


def _vorschau(a, box, eingabe) -> None:
    box.clear()
    with box:
        if not a.as_verstanden:
            return
        ui.label("Verstanden – Häkchen entfernen, was nicht passieren soll").classes("m-ktitel")
        for v in a.as_verstanden:
            with ui.element("div").classes("m-plan-u"):
                teile = [v.eingabe]
                if v.zimmer:
                    teile.append("Zimmer " + ", ".join(zkurz(z) for z in v.zimmer))
                if v.datum:
                    teile.append(("Frist " if v.frist else "Termin ") + f"{v.datum:%d.%m.%Y}" + (f" {v.uhrzeit} Uhr" if v.uhrzeit else ""))
                ui.label(" · ".join(teile)).classes("m-name").style("white-space:normal")
                for h in v.hinweise:
                    ui.label(h).classes("m-zweite").style("color:var(--orange); white-space:normal")
                for akt in v.aktionen:
                    cb = ui.checkbox(akt.text, value=akt.an).props("dense dark color=indigo-4")
                    cb.on_value_change(lambda e, akt=akt: setattr(akt, "an", e.value))

        async def ausfuehren():
            liste = a.as_verstanden
            if not any(akt.an for v in liste for akt in v.aktionen):
                a.toast("Nichts angehakt.", fehler=True)
                return
            try:
                e = await run.io_bound(assistenz.ausfuehren, liste)
            except Exception as exc:          # noqa: BLE001
                a.toast(f"Nicht ausgeführt: {exc}", fehler=True)
                return
            a.as_verstanden, a.as_text = [], ""
            await a.laden()
            a.toast(f"{len(e['erledigt'])} Schritte eingetragen – Rückgängig unter „Zuletzt erledigt“", rueck=False)

        def verwerfen():
            a.as_verstanden = []
            box.clear()

        with ui.element("div").classes("m-paktionen"):
            knopf("Ausführen", ausfuehren, "primaer", "check")
            knopf("Verwerfen", verwerfen, "leise")


async def _rueck(a, eid: str) -> None:
    n = await run.io_bound(assistenz.rueckgaengig, eid)
    await a.laden()
    a.toast(f"Zurückgenommen ({n} Schritte)", rueck=False)


# =======================================================================================
# Mails
# =======================================================================================

def _mail_umsetzen(e, schritte, betreff, text, absender, treffer) -> str:
    stand = zp.laden()
    x = _schritt(f"Mail umgesetzt: {e.name or mails.ARTEN.get(e.art, e.art)}",
                 lambda: mails.umsetzen(e, schritte, stand, betreff, text, absender, treffer),
                 [mails.DATEI, anreiseliste.DATEI, tm.DATEI, zp.PERSONEN_ANGABEN])
    return f"{mails.ARTEN.get(x.art, x.art)} umgesetzt: {x.name or 'ohne Person'}" + (" – Prüfliste offen" if x.status == "zu prüfen" else "")


def _mails(a) -> None:
    with a.inhalt:
        with ui.element("div").classes("m-zwei"):
            with ui.element("section").classes("m-block"):
                ui.label("Mail einfügen").classes("m-btitel")
                ui.label("Betreff und Text aus Outlook kopieren (oder unten „Aus Outlook“). Erkannt werden Anmeldung, "
                         "Gästehaus, Storno, Abbruch – mit Person, Zeitraum und Vorschlag.").classes("m-ptext")
                betreff = ui.input("Betreff").classes("m-feld").props("dense outlined dark")
                absender = ui.input("Absender (optional)").classes("m-feld").props("dense outlined dark")
                text = ui.textarea("Text").classes("m-feld").props("outlined dark autogrow")
                erg = ui.element("div").classes("m-plan-liste")

                async def erkennen():
                    if not (text.value or betreff.value):
                        return
                    e = await run.io_bound(mails.erkennen, betreff.value or "", text.value or "")
                    personen, _ = await run.io_bound(anreiseliste.laden)
                    treffer = await run.io_bound(mails.zuordnen, e, zp.laden(), personen)
                    _mail_ergebnis(a, erg, e, treffer, betreff, absender, text)

                async def outlook():
                    try:
                        auswahl = await run.io_bound(mails.outlook_auswahl)
                    except Exception:                  # noqa: BLE001 – kein Outlook (z. B. „neues Outlook“)
                        a.toast("Outlook ist nicht erreichbar – bitte Betreff und Text hineinkopieren.", fehler=True)
                        return
                    if not auswahl:
                        a.toast("In Outlook ist keine Mail markiert.", fehler=True)
                        return
                    betreff.value, absender.value, text.value = auswahl[0]
                    await erkennen()

                with ui.element("div").classes("m-paktionen"):
                    knopf("Erkennen", erkennen, "primaer", "auto_awesome")
                    knopf("Aus Outlook", outlook, "", "mail")
            with ui.element("section").classes("m-block"):
                ui.label("Posteingang").classes("m-btitel")
                offen = [x for x in a.daten["eingaenge"] if x.status in ("offen", "zu prüfen")]
                ui.label(f"{len(offen)} offen · {len(a.daten['eingaenge'])} insgesamt").classes("m-ptext")
                for x in a.daten["eingaenge"][:30]:
                    with ui.element("div").classes("m-notiz"):
                        ui.label(f"{mails.ARTEN.get(x.art, x.art)}: {x.name or '–'}").classes("m-name")
                        ui.label(f"{datetime.fromisoformat(x.eingang):%d.%m. %H:%M} · {x.status}" +
                                 (f" · offen: {', '.join(x.offen_zu_pruefen)}" if x.offen_zu_pruefen else "")).classes("m-zweite")
                        if x.status in ("offen", "zu prüfen"):
                            knopf("", lambda x=x: _eingang_erledigt(a, x), "leise", "check", "Als erledigt markieren")


async def _eingang_erledigt(a, x) -> None:
    from dataclasses import replace

    def aktion():
        mails.eingang_speichern(replace(x, status="erledigt"))
    await a.aendern(lambda: (_schritt("Mail erledigt", aktion, [mails.DATEI]), "Mail als erledigt markiert")[1])


def _mail_ergebnis(a, box, e, treffer, betreff, absender, text) -> None:
    box.clear()
    zustand = {"treffer": treffer[0] if treffer else None, "schritte": []}
    with box:
        ui.label(f"Erkannt: {mails.ARTEN.get(e.art, e.art)}" + (f" · {e.name}" if e.name else "") +
                 (f" · {e.von:%d.%m.%Y}" if e.von else "") + (f" – {e.bis:%d.%m.%Y}" if e.bis else "")).classes("m-name")
        for u in e.unsicher:
            ui.label(u).classes("m-zweite").style("color:var(--orange)")
        if treffer:
            ui.select({i: t.text for i, t in enumerate(treffer)} | {-1: "Keine dieser Personen"}, value=0,
                      label="Person", on_change=lambda ev: neu_vorschlag(treffer[ev.value] if ev.value >= 0 else None)).classes(
                "m-feld").props('dense outlined dark options-dense popup-content-class="m-popup"')
        schritte_box = ui.element("div").classes("m-plan-liste")

        def neu_vorschlag(t):
            zustand["treffer"] = t
            zustand["schritte"] = mails.vorschlag(e, t, zp.laden())
            schritte_box.clear()
            with schritte_box:
                for s in zustand["schritte"]:
                    cb = ui.checkbox(s.text, value=s.an).props("dense dark color=indigo-4")
                    cb.on_value_change(lambda ev, s=s: setattr(s, "an", ev.value))

        neu_vorschlag(zustand["treffer"])

        async def umsetzen():
            if await a.aendern(_mail_umsetzen, e, zustand["schritte"], betreff.value or "", text.value or "",
                               absender.value or "", zustand["treffer"]):
                betreff.value = absender.value = text.value = ""
                box.clear()

        async def ablegen(status: str):
            await run.io_bound(mails.ablegen, e, betreff.value or "", text.value or "", absender.value or "", status)
            betreff.value = absender.value = text.value = ""
            box.clear()
            await a.laden()
            a.toast("Mail abgelegt" if status == "offen" else "Mail verworfen", rueck=False)

        with ui.element("div").classes("m-paktionen"):
            knopf("Umsetzen", umsetzen, "primaer", "check")
            knopf("Nur ablegen", lambda: ablegen("offen"), "leise")
            knopf("Verwerfen", lambda: ablegen("verworfen"), "leise")


# =======================================================================================
# Fragen & Zahlen
# =======================================================================================

def _antwort(frage: str, verlauf: list) -> tuple[str, str, list, list]:
    """(Text, Quelle, Tabelle, Vorschläge) – erst aus den Daten, sonst KI (wenn eingeschaltet)."""
    from belegung import speicher
    from belegung.assistent import Assistent
    from belegung.assistent.llm import Einstellungen, backend_erstellen

    from . import auswertung_kern as ak

    ds, fehler = ak.datenstand()
    if ds is None:
        return fehler or "Es sind noch keine Daten geladen.", "hinweis", [], []
    ass = Assistent(ds)
    try:
        antwort = ass.beantworte(frage)
    except Exception as exc:                  # noqa: BLE001
        return f"Bei der Berechnung ist ein Fehler aufgetreten: {exc}", "hinweis", [], []
    if antwort is not None:
        tab = [antwort.tabelle[0]] + antwort.tabelle[1] if antwort.tabelle else []
        return antwort.text, "aus den Daten berechnet", tab, antwort.vorschlaege
    e = Einstellungen.aus_dict(speicher.einstellungen().get("ki", {}))
    try:
        backend = backend_erstellen(e)
    except Exception as exc:                  # noqa: BLE001
        return f"KI nicht verfügbar: {exc}", "hinweis", [], []
    if backend is None:
        return ("Das habe ich nicht sicher verstanden. Ich beantworte Fragen zu **Belegung, freien Plätzen, Auslastung, "
                "Kapazität, Prognose, Anreisen, Mietern und Häusern** – am besten mit Standort und Zeitraum. Für freie "
                "Fragen lässt sich unter Einstellungen eine KI zuschalten."), "hinweis", [], []
    try:
        return backend.antworte(frage, verlauf, ds, date.today()), "KI", [], []
    except Exception as exc:                  # noqa: BLE001
        return f"Die KI ist gerade nicht erreichbar: {exc}", "hinweis", [], []


def _md(text: str) -> str:
    import html
    import re

    t = html.escape(text)
    t = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", t)
    return t.replace("\n", "<br>")


def _fragen(a) -> None:
    with a.inhalt:
        with ui.element("div").classes("m-chat"):
            verlauf_box = ui.element("div").classes("m-chat-verlauf")

            def zeichnen_verlauf():
                verlauf_box.clear()
                with verlauf_box:
                    if not a.as_chat:
                        ui.label("Fragen Sie nach Belegung, freien Plätzen, Auslastung, Prognose, Anreisen oder Mietern – "
                                 "die Zahlen kommen direkt aus den Daten.").classes("m-ptext")
                    for rolle, text, quelle, tab in a.as_chat:
                        with ui.element("div").classes(f"m-blase {rolle}"):
                            ui.html(_md(text), sanitize=False)
                            if tab:
                                import html as h_

                                kopf, *zeilen = tab
                                ui.html("<table class='m-chat-tab'><tr>" + "".join(f"<th>{h_.escape(str(k))}</th>" for k in kopf)
                                        + "</tr>" + "".join("<tr>" + "".join(f"<td>{h_.escape(str(c))}</td>" for c in z)
                                                            + "</tr>" for z in zeilen) + "</table>", sanitize=False)
                            if quelle:
                                ui.label(quelle).classes("m-zweite")

            zeichnen_verlauf()
            with ui.element("div").classes("m-paktionen"):
                for b in a.daten["beispiele"]:
                    knopf(b, lambda b=b: senden(b), "leise")
            with ui.element("div").classes("m-chat-ein"):
                feld = ui.input(placeholder="Frage stellen … z. B. „Wie viele Plätze sind im November in Goslar frei?“").classes(
                    "m-feld").props("dense outlined dark")

                async def senden(frage: str | None = None):
                    frage = (frage or feld.value or "").strip()
                    if not frage:
                        return
                    feld.value = ""
                    a.as_chat.append(("nutzer", frage, "", []))
                    zeichnen_verlauf()
                    verlauf = [("user" if r == "nutzer" else "assistant", t) for r, t, _q, _t in a.as_chat[:-1]]
                    text, quelle, tab, _v = await run.io_bound(_antwort, frage, verlauf)
                    a.as_chat.append(("assistent", text, quelle, tab))
                    zeichnen_verlauf()

                feld.on("keydown.enter", lambda: senden())
                knopf("Senden", lambda: senden(), "primaer", "send")
                knopf("Neues Gespräch", lambda: (a.as_chat.clear(), zeichnen_verlauf()), "leise")
