"""Strg+K: Suchen und Springen – Seiten, Personen (Anreiselisten, UWT, Gebäudeplan, Zimmerplan) und Zimmer."""

from __future__ import annotations

from datetime import date

from nicegui import run, ui

from .kern import kurz
from .ui_bausteine import attr


def treffer(text: str, stand, heute: date) -> list[tuple[str, str, str, dict]]:
    """(Titel, Zusatz, Seite, Zustand) – Seiten zuerst, dann Personen/Zimmer aus der Suche des Hauptprogramms."""
    from belegung import suche

    from .register import NAV

    q = text.strip().lower()
    erg = []
    for key, titel, _icon, _g in NAV:
        if q and q in titel.lower():
            erg.append((titel, "Seite", key, {}))
    if stand is not None and len(q) >= 2:
        from . import kern as k_

        strittig = {x.person: x for x in k_.strittige(stand)}
        for t in suche.suchen(text, stand, heute=heute)[:40]:
            zusatz = " · ".join(x for x in (t.zimmer_text, t.massnahme, f"{t.von:%d.%m.%y}–{t.bis:%d.%m.%y}"
                                             if t.bis else f"ab {t.von:%d.%m.%y}", t.status(heute)) if x)
            if (x := strittig.get(t.person)) is not None and t.zimmer_id == x.geplant:
                zusatz = f"⚠ strittig – Gebäudeplan: {kurz(x.gebucht)} · " + zusatz
            if t.zimmer_id:
                erg.append((t.name, zusatz, "zimmer", {"karte": t.zimmer_id}))
            else:
                erg.append((t.name, zusatz, "anreisen", {"kennung": t.von.isoformat()}))
        from . import historie_kern as hk

        try:
            frueher = hk.suchen(text, heute)
        except Exception:                  # noqa: BLE001 – Historie ist Zusatz
            frueher = []
        schon = {(t[0], t[3].get("karte")) for t in erg}
        for h in frueher:
            if (h.name, h.zimmer) not in schon:
                erg.append((h.name, " · ".join(x for x in (f"früher in {h.kurz}", h.massnahme, h.zeitraum) if x),
                            "zimmer", {"karte": h.zimmer}))
    return erg


def befehle(a, text: str) -> list[tuple[str, str, str, tuple]]:
    """0.71: (Titel, Zusatz, Symbol, Ziel) – Befehle aus dem Menüband und Aktionen, Zimmer + Stichwort, Frage, Auftrag."""
    from . import befehle_kern as bk
    from .menueband_ui import _ansichten

    kat = getattr(a, "_befehle", None)
    if kat is None:
        kat = a._befehle = bk.katalog(_ansichten(), a.design.get("leitung", True))
    q = text.strip()
    if not q:
        return [(b.titel, b.bereich, b.icon, b.ziel) for b in bk.vorschlaege(kat)]
    erg = []
    if (zb := bk.zimmer_befehl(q)) is not None and a.stand is not None:
        code, was = zb
        z = next((z for z in a.stand.zimmer if z.kurz.upper() == code.upper()), None)
        if z is not None:
            erg.append((f"Zimmer {z.kurz}: {was}", "Zimmerkarte öffnen – dort Mangel, Sperre, Verlauf, Bewohner",
                        "meeting_room", ("seite", "zimmer", None, {"karte": z.id})))
    if bk.ist_frage(q):
        erg.append((f"Fragen: „{q}“", "Antwort aus den Daten (Start → Assistenz → Fragen & Zahlen)", "help_center",
                    ("frage", q)))
    erg += [(b.titel, b.bereich, b.icon, b.ziel) for b in bk.suchen(q, kat)]
    return erg


async def ausfuehren(a, ziel: tuple) -> None:
    from . import menueband_ui

    art = ziel[0]
    if art in ("seite", "aktion"):
        if art == "seite" and ziel[1] == "zimmer" and ziel[3].get("karte"):
            await a.oeffnen("zimmer", karte=ziel[3]["karte"])
            return
        await menueband_ui.ausfuehren(a, ziel)
    elif art == "panel":
        _p, seite, ansicht, name = ziel
        await a.oeffnen(seite, ansicht)
        if name == "termin_neu":
            from .seite_termine import termin_panel

            termin_panel(a, None, a.heute)
        elif name == "mieter_neu":
            from .seiten import mieter_neu_panel

            mieter_neu_panel(a)
        elif name == "notfall":
            from .seite_zimmer import notfall_drucken

            await notfall_drucken(a)
        elif name == "wochenblatt":
            from .seiten import _wochenblatt_panel

            _wochenblatt_panel(a)
    elif art == "frage":
        await a.oeffnen("assistenz", "fragen", as_frage_neu=ziel[1])
    elif art == "auftrag":
        await a.oeffnen("assistenz", "auftraege", as_text=ziel[1])


def oeffnen(a) -> None:
    """Strg+K: eine Eingabe für alles – Befehle (wie „Was möchten Sie tun?“ in Office), Personen, Zimmer, Fragen."""
    ablage = getattr(a, "dialog_ablage", None)
    ctx = ablage if ablage is not None else ui.element("div")
    with ctx, ui.dialog().props("position=top") as dlg, ui.element("div").classes("m-palette"):
        eingabe = ui.input(placeholder="Suchen oder Befehl: Name, 2-408, „drucken“, „neuer Termin“, eine Frage …").classes(
            "m-palette-ein").props("dense borderless dark autofocus")
        liste = ui.element("div").classes("m-palette-liste")
        auswahl = {"i": 0, "erg": [], "text": ""}

        def zeichnen():
            liste.clear()
            with liste:
                if not auswahl["text"]:
                    ui.label("Vorschläge – oder tippen: Personen, Zimmer, Befehle, Fragen").classes("m-palette-gruppe")
                for i, e in enumerate(auswahl["erg"]):
                    if e[0] == "befehl" and i == 0 and auswahl["text"]:
                        ui.label("Befehle").classes("m-palette-gruppe")
                    if e[0] == "treffer" and (i == 0 or auswahl["erg"][i - 1][0] != "treffer"):
                        ui.label("Personen und Zimmer").classes("m-palette-gruppe")
                    if e[0] == "auftrag":
                        ui.label("Assistenz").classes("m-palette-gruppe")
                    _art, titel, zusatz, icon, _ziel = e
                    b = ui.element("button").classes("m-palette-z mit-symbol" + (" an" if i == auswahl["i"] else ""))
                    with b:
                        ui.icon(icon).classes("m-palette-sym")
                        with ui.element("div").classes("m-palette-text"):
                            attr(ui.label(titel).classes("m-name"), title=titel)
                            ui.label(zusatz).classes("m-zweite")
                    b.on("click", lambda i=i: los(i))
                if auswahl["text"] and not auswahl["erg"]:
                    ui.label("Nichts gefunden.").classes("m-zweite").style("padding:10px 12px")
                ui.label("Enter öffnet · ↑ ↓ wählt · Esc schließt").classes("m-palette-fuss")

        async def suchen():
            text = eingabe.value or ""
            auswahl["text"] = text.strip()
            erg = [("befehl", t, z, i, ziel) for t, z, i, ziel in befehle(a, text)]
            leute = await run.io_bound(treffer, text, a.stand, a.heute) if len(text.strip()) >= 2 else []
            erg += [("treffer", t, z, "person", ("seite", s, None, st))
                    for t, z, s, st in leute if z != "Seite"][:12]            # Seiten stehen schon als Befehle oben
            mehrwortig = len(auswahl["text"].split()) >= 2
            if (auswahl["text"] and len(auswahl["text"]) >= 6 and not any(e[4][0] == "frage" for e in erg)
                    and (mehrwortig or not erg)):            # nur, wenn es nach einem Auftrag aussieht
                erg.append(("auftrag", f"Als Auftrag an die Assistenz: „{auswahl['text']}“",
                            "z. B. „2-408 Heizung defekt“ – die Assistenz schlägt die passenden Schritte vor",
                            "assignment", ("auftrag", auswahl["text"])))
            auswahl["erg"], auswahl["i"] = erg, 0
            zeichnen()

        async def los(i: int | None = None):
            i = auswahl["i"] if i is None else i
            if 0 <= i < len(auswahl["erg"]):
                ziel = auswahl["erg"][i][4]
                dlg.close()
                await ausfuehren(a, ziel)

        def taste(e):
            k = e.args.get("key")
            if k == "ArrowDown":
                auswahl["i"] = min(auswahl["i"] + 1, len(auswahl["erg"]) - 1)
                zeichnen()
            elif k == "ArrowUp":
                auswahl["i"] = max(auswahl["i"] - 1, 0)
                zeichnen()
            elif k == "Enter":
                return los()

        eingabe.on("update:model-value", suchen, throttle=0.25, leading_events=False)
        eingabe.on("keydown", taste, args=["key"])
    dlg.on("hide", lambda: dlg.delete() if not dlg.is_deleted else None)
    dlg.open()
    ui.timer(0.01, suchen, once=True)                 # Vorschläge sofort zeigen


CSS = r"""
.m-palette-gruppe { font-size: 11px; font-weight: 700; letter-spacing: .06em; text-transform: uppercase; color: var(--text3);
  padding: 10px 12px 4px; }
.m-palette-z.mit-symbol { display: flex !important; align-items: center; gap: 10px; }
.m-palette-sym { font-size: 20px; color: var(--akzent); flex: none; }
.m-palette-text { display: flex; flex-direction: column; min-width: 0; }
.m-palette-text > * { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.m-palette-fuss { font-size: 11.5px; color: var(--text3); padding: 8px 12px 6px; border-top: 1px solid var(--rand); margin-top: 6px; }
"""
