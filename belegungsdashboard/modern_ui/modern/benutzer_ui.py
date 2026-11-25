"""1.33: Anmelden, Konto, Benutzer verwalten. Logik in ``benutzer_kern``."""

from __future__ import annotations

from nicegui import run, ui

from . import benutzer_kern as bk
from .ui_bausteine import attr, knopf

FELD = "dense outlined dark"
STANDORT_NAMEN = {"GS": "Goslar", "BP": "Bad Pyrmont", "WE": "Weser-Ems"}


def _fehler(lbl, text: str) -> None:
    lbl.set_text(text)
    lbl.set_visibility(bool(text))


# ---- Beim Start ----------------------------------------------------------------------------------------------------

async def anmelden(windows_erlaubt: bool = True) -> bk.Konto:
    """Windows-Konto zugeordnet → sofort angemeldet; sonst Dialog (Anmeldename + Passwort), bis es klappt.
    Danach – falls verlangt – neues Passwort festlegen."""
    from . import netz_kern

    k = await run.io_bound(bk.windows_konto) if windows_erlaubt else None
    if k is None:
        win = netz_kern.benutzer()
        with ui.dialog().props("persistent") as dlg, ui.element("div").classes("m-frage m-anmelden"):
            attr(dlg, role="dialog", aria_label="Anmelden")
            ui.label("Anmelden").classes("m-titel")
            ui.label("Bitte mit Ihrem INNternat-Konto anmelden. Ein Konto legt der Administrator an."
                     + (f" Soll die Anmeldung künftig automatisch über das Windows-Konto „{win}“ laufen, kann er es "
                        "Ihrem Konto zuordnen." if win else "")).classes("m-ptext")
            name = ui.input("Anmeldename").classes("m-feld w-full").props(FELD + " autofocus")
            pw = ui.input("Passwort", password=True, password_toggle_button=True).classes("m-feld w-full").props(FELD)
            fehler = ui.label("").classes("m-zweite m-warn").style("white-space:normal")
            fehler.set_visibility(False)

            async def los():
                try:
                    k_ = await run.io_bound(bk.anmelden, name.value or "", pw.value or "")
                except ValueError as exc:
                    _fehler(fehler, str(exc))
                    pw.set_value("")
                    return
                dlg.submit(k_)
            pw.on("keydown.enter", los)
            name.on("keydown.enter", lambda: pw.run_method("focus"))
            with ui.element("div").classes("m-paktionen"):
                knopf("Anmelden", los, "primaer", "login")
        dlg.open()
        k = await dlg
    k = await run.io_bound(bk.angemeldet, k)
    if k.muss_aendern:
        await passwort_dialog(pflicht=True)
    return bk.aktuell() or k


async def passwort_dialog(pflicht: bool = False) -> bool:
    k = bk.aktuell()
    with ui.dialog().props("persistent" if pflicht else "") as dlg, ui.element("div").classes("m-frage"):
        attr(dlg, role="dialog", aria_label="Passwort ändern")
        ui.label("Neues Passwort festlegen" if pflicht else "Passwort ändern").classes("m-titel")
        if pflicht:
            ui.label("Das Passwort hat der Administrator vergeben – bitte jetzt ein eigenes festlegen "
                     f"(mindestens {bk.MIN_LAENGE} Zeichen).").classes("m-ptext")
        alt = None
        if not pflicht and k and k.pw:
            alt = ui.input("Bisheriges Passwort", password=True).classes("m-feld w-full").props(FELD + " autofocus")
        neu = ui.input("Neues Passwort", password=True, password_toggle_button=True).classes("m-feld w-full").props(FELD)
        wdh = ui.input("Neues Passwort wiederholen", password=True).classes("m-feld w-full").props(FELD)
        fehler = ui.label("").classes("m-zweite m-warn").style("white-space:normal")
        fehler.set_visibility(False)

        async def los():
            try:
                await run.io_bound(bk.passwort_aendern, alt.value if alt else "", neu.value or "", wdh.value or "")
            except ValueError as exc:
                _fehler(fehler, str(exc))
                return
            dlg.submit(True)
        wdh.on("keydown.enter", los)
        with ui.element("div").classes("m-paktionen"):
            knopf("Speichern", los, "primaer", "key")
            if not pflicht:
                knopf("Abbrechen", lambda: dlg.submit(False), "leise")
    dlg.open()
    return bool(await dlg)


def _optionen(a) -> None:
    """1.39: Optionen (Darstellung) stehen im Konto – „Datei → Optionen“ gibt es nicht mehr."""
    from . import optionen_ui

    a.panel_zu()
    optionen_ui.oeffnen(a, "farben")


# ---- Konto (Datei → Konto, Statusleiste) -----------------------------------------------------------------------------

def konto_panel(a) -> None:
    k = bk.aktuell()

    async def verwalten():
        a.panel_zu()
        await a.oeffnen("einstellungen", "benutzer")

    def bauen():
        if k is None:
            ui.label("Es gibt noch keine Benutzerkonten – INNternat läuft ohne Anmeldung. Den ersten Administrator legen "
                     "Sie unter Verwaltung → Benutzer & Rechte an.").classes("m-ptext")
            with ui.element("div").classes("m-paktionen"):
                knopf("Benutzer einrichten", verwalten, "primaer", "manage_accounts")
                knopf("Optionen", lambda: _optionen(a), "", "tune", "Darstellung, Farben, Diagramme")
                knopf("Schließen", a.panel_zu, "leise")
            return
        ui.label(k.name).classes("m-titel")
        ui.label(f"Anmeldename: {k.kennung}").classes("m-zweite")
        ui.label(f"Rolle: {bk.ROLLEN.get(k.rolle, k.rolle)}").classes("m-zweite")
        ui.label("Standorte: " + ", ".join(STANDORT_NAMEN[s] for s in k.erlaubt())).classes("m-zweite")
        ui.label(f"Windows-Konto: {k.windows}" if k.windows else "Anmeldung mit Passwort").classes("m-zweite")

        async def pw():
            if await passwort_dialog():
                a.toast("Passwort geändert", rueck=False)
        with ui.element("div").classes("m-paktionen"):
            knopf("Passwort ändern", pw, "", "key")
            knopf("Abmelden", lambda: abmelden(a), "", "logout", "Abmelden – z. B. wenn jemand anderes an diesem PC weiterarbeitet")
            if k.admin:
                knopf("Benutzer verwalten", verwalten, "primaer", "manage_accounts")
            knopf("Optionen", lambda: _optionen(a), "", "tune", "Darstellung, Farben, Diagramme – für Sie persönlich")
            knopf("Schließen", a.panel_zu, "leise")

    a.panel("Konto", bauen)


def abmelden(a) -> None:
    from .oberflaeche import _START

    bk.abmelden()
    _START["manuell"] = True                   # nicht gleich wieder automatisch über Windows anmelden
    ui.navigate.reload()


# ---- Einstellungen → Benutzer --------------------------------------------------------------------------------------

def daten(a) -> None:
    a.daten = {"konten": bk.konten(), "eingerichtet": bk.eingerichtet(), "notfall": bk.notfall()}


async def _tun(a, fn, *args) -> bool:
    try:
        text = await run.io_bound(fn, *args)
    except ValueError as exc:
        a.toast(str(exc), fehler=True)
        return False
    a.toast(text, rueck=False)
    await a.laden()
    return True


def zeichnen(a) -> None:
    d = a.daten or {}
    with a.inhalt:
        if not d.get("eingerichtet") or d.get("notfall"):
            _erster_admin(a, d.get("notfall") and d.get("eingerichtet"))
            return
        if not bk.ist_admin():
            ui.label("Benutzer verwalten darf nur ein Administrator.").classes("m-ptext").style("padding:14px 20px")
            return
        sp = "minmax(140px,1.2fr) minmax(120px,1fr) 130px minmax(150px,1fr) minmax(110px,.8fr) 120px"
        with ui.element("div").classes("m-zeile-flex").style("padding: 14px 20px 4px"):
            ui.label("Jede Person meldet sich mit ihrem Konto an. Mitarbeitende sehen nur ihre Standorte. Klick auf eine "
                     "Zeile zum Ändern, Sperren oder neuen Startpasswort.").classes("m-ptext")
            knopf("Neuer Benutzer …", lambda: _panel(a, None), "primaer", "person_add").style("margin-left:auto")
        with ui.element("div").classes("m-raster m-tkopf").style(f"grid-template-columns:{sp}"):
            for t in ("Name", "Anmeldename", "Rolle", "Standorte", "Windows-Konto", "Zuletzt"):
                ui.label(t)
        for k in sorted(d.get("konten") or [], key=lambda k: (not k.admin, k.name.lower())):
            r = ui.element("div").classes("m-raster m-zeile m-klick" + ("" if k.aktiv else " fertig")).style(
                f"grid-template-columns:{sp}")
            with r:
                ui.label(k.name + ("" if k.aktiv else " (gesperrt)")).classes("m-name")
                ui.label(k.kennung).classes("m-zweite")
                ui.label(bk.ROLLEN.get(k.rolle, k.rolle)).classes("m-zweite")
                ui.label("alle" if k.admin else ", ".join(STANDORT_NAMEN[s] for s in k.erlaubt())).classes("m-zweite")
                ui.label(k.windows or "–").classes("m-zweite")
                ui.label(_zeit(k.zuletzt) + (" · Passwort neu" if k.muss_aendern else "")).classes("m-zweite")
            r.on("click", lambda k=k: _panel(a, k))


def _zeit(t: str) -> str:
    from datetime import datetime

    try:
        return f"{datetime.fromisoformat(t):%d.%m.%y %H:%M}"
    except (TypeError, ValueError):
        return "–"


def _erster_admin(a, notfall: bool) -> None:
    from . import netz_kern

    with ui.element("section").classes("m-block").style("max-width:560px; margin:14px 20px"):
        ui.label("Notfall: neuen Administrator anlegen" if notfall else "Ersten Administrator anlegen").classes("m-btitel")
        ui.label(("Im Datenordner liegt ADMIN_ZURUECKSETZEN.txt – deshalb darf hier ein Administrator angelegt werden. Die "
                  "Datei wird danach entfernt. " if notfall else
                  "Noch gibt es keine Benutzerkonten, INNternat läuft ohne Anmeldung. Sobald hier der erste Administrator "
                  "angelegt ist, meldet sich jede Person an; Mitarbeitende legen Sie danach hier an. ")
                 + "Passwörter werden nur verschlüsselt (als Hash) gespeichert.").classes("m-ptext")
        name = ui.input("Ihr Name (steht im Verlauf)").classes("m-feld w-full").props(FELD)
        kennung = ui.input("Anmeldename (z. B. Vorname.Nachname oder E-Mail)").classes("m-feld w-full").props(FELD)
        pw = ui.input("Passwort", password=True, password_toggle_button=True).classes("m-feld w-full").props(FELD)
        wdh = ui.input("Passwort wiederholen", password=True).classes("m-feld w-full").props(FELD)
        win = netz_kern.benutzer()
        auto = ui.checkbox(f"An diesem PC automatisch über mein Windows-Konto „{win}“ anmelden", value=bool(win))
        auto.set_visibility(bool(win))

        async def los():
            try:
                await run.io_bound(bk.ersten_admin_anlegen, kennung.value or "", name.value or "", pw.value or "",
                                   wdh.value or "", win if auto.value else "")
            except ValueError as exc:
                a.toast(str(exc), fehler=True)
                return
            ui.navigate.reload()               # Name in der Statusleiste, Liste der Benutzer
        knopf("Administrator anlegen", los, "primaer", "admin_panel_settings")


def _panel(a, k: bk.Konto | None) -> None:
    neu = k is None

    def bauen():
        name = ui.input("Name (steht im Verlauf)", value=k.name if k else "").classes("m-feld w-full").props(FELD)
        kennung = ui.input("Anmeldename", value=k.kennung if k else "").classes("m-feld w-full").props(FELD)
        if not neu:
            kennung.props("readonly")
        rolle = ui.select(bk.ROLLEN, value=k.rolle if k else "mitarbeiter", label="Rolle").classes("m-feld w-full")
        ui.label("Standorte (Administratoren sehen immer alle)").classes("m-abschnitt")
        haken = {s: ui.checkbox(n, value=bool(k and s in k.standorte)) for s, n in STANDORT_NAMEN.items()}
        ui.label("Automatisch anmelden über Windows (empfohlen)").classes("m-abschnitt")
        ui.label("Windows-Anmeldename der Person, so wie er beim Anmelden am PC steht (ohne Domäne). Dann braucht sie "
                 "in INNternat kein Passwort. Leer lassen, wenn sich mehrere Personen ein Windows-Konto teilen.") \
            .classes("m-ptext")
        windows = ui.input("Windows-Anmeldename", value=k.windows if k else "").classes("m-feld w-full").props(FELD)
        start = None
        aktiv = None
        if neu:
            ui.label("Startpasswort (muss beim ersten Anmelden geändert werden)").classes("m-abschnitt")
            start = ui.input("Startpasswort", value=bk.start_passwort()).classes("m-feld w-full").props(FELD)
            ui.label("Nur nötig ohne Windows-Konto. Bitte der Person persönlich geben, nicht per Mail.").classes("m-zweite")
        else:
            aktiv = ui.switch("Konto aktiv (aus = gesperrt)", value=k.aktiv).props("dense color=primary")

        def standorte():
            return [s for s, h in haken.items() if h.value]

        async def speichern():
            if neu:
                ok = await _tun(a, bk.anlegen, kennung.value or "", name.value or "", rolle.value, standorte(),
                                windows.value or "", start.value or "")
            else:
                ok = await _tun(a, bk.bearbeiten, k.kennung, name.value or "", rolle.value, standorte(),
                                windows.value or "", aktiv.value)
            if ok:
                a.panel_zu()

        with ui.element("div").classes("m-paktionen"):
            knopf("Anlegen" if neu else "Speichern", speichern, "primaer", "save")
            knopf("Abbrechen", a.panel_zu, "leise")
        if not neu:
            ui.label("Passwort").classes("m-abschnitt")
            pw = ui.input("Neues Startpasswort", value=bk.start_passwort()).classes("m-feld w-full").props(FELD)

            async def zuruecksetzen():
                if await _tun(a, bk.passwort_zuruecksetzen, k.kennung, pw.value or ""):
                    a.panel_zu()

            async def weg():
                if await _tun(a, bk.loeschen, k.kennung):
                    a.panel_zu()
            with ui.element("div").classes("m-paktionen"):
                knopf("Startpasswort setzen", zuruecksetzen, "", "key", "Die Person muss es beim nächsten Anmelden ändern")
                knopf("Benutzer löschen", weg, "leise", "person_remove",
                      "Konto entfernen (im Verlauf bleibt der Name stehen). Sperren geht oben mit „Konto aktiv“.")

    a.panel("Neuer Benutzer" if neu else f"Benutzer · {k.name}", bauen)
