"""Outlook-Vorschau auf „Heute“: die neuesten Mails eines Ordners (z. B. des Postfachs „Internatsdienst“) – nur lesen.

Zugriff wie bei Erinnerungen und Tagesbriefing: lokal über das klassische Outlook (Windows, pywin32/COM). Es wird
nichts gesendet, verschoben, gelöscht oder als gelesen markiert; Outlook wird nicht gestartet, wenn es nicht läuft.
Keine Cloud, kein Server, kein OAuth. Ohne eingestellten Ordner ist die Vorschau aus und zeigt keine Inhalte.

Ordner-Angabe (Einstellungen): ``Internatsdienst`` = Posteingang des Postfachs „Internatsdienst“,
``Internatsdienst/Posteingang/Anreisen`` = Unterordner, leer = aus. Das neue Outlook (ohne COM) wird nicht unterstützt.
"""

from __future__ import annotations

import re
import time
from dataclasses import dataclass
from datetime import date, datetime

from belegung import speicher

EINSTELLUNG = "modern_outlook_vorschau"
ANZAHL = 6
NEU_LADEN_S = 120
_ZWISCHEN: dict = {"zeit": 0.0, "pfad": None, "erg": ([], "")}


@dataclass
class Mail:
    zeit: datetime
    betreff: str
    absender: str
    ungelesen: bool

    @property
    def wann(self) -> str:
        return f"{self.zeit:%H:%M}" if self.zeit.date() == date.today() else f"{self.zeit:%d.%m.}"


def ordner() -> str:
    return str(speicher.einstellungen().get(EINSTELLUNG, "") or "").strip()


def einstellen(pfad: str) -> str:
    speicher.einstellung_setzen(EINSTELLUNG, (pfad or "").strip())
    _ZWISCHEN["zeit"] = 0.0
    return f"Outlook-Vorschau: {pfad.strip()}" if pfad.strip() else "Outlook-Vorschau ausgeschaltet"


def _teile(pfad: str) -> list[str]:
    return [t.strip() for t in re.split(r"[\\/]", pfad or "") if t.strip()]


def _unterordner(f, name: str):
    for i in range(1, f.Folders.Count + 1):
        x = f.Folders.Item(i)
        if str(x.Name).lower() == name.lower():
            return x
    raise ValueError(f"Ordner „{name}“ nicht gefunden (in „{f.Name}“).")


def _ordner_finden(ns, pfad: str):
    teile = _teile(pfad)
    wurzel, rest = None, teile
    for i in range(1, ns.Folders.Count + 1):          # Postfächer (eigenes und freigegebene) nach Anzeigename
        f = ns.Folders.Item(i)
        if teile and str(f.Name).lower() == teile[0].lower():
            wurzel, rest = f, teile[1:]
            break
    if wurzel is None:                                # sonst: Unterordner des eigenen Posteingangs
        wurzel = ns.GetDefaultFolder(6)
        rest = [t for t in teile if t.lower() not in ("posteingang", "inbox")]
    elif not rest:                                    # nur das Postfach angegeben → dessen Posteingang
        for name in ("Posteingang", "Inbox"):
            try:
                return _unterordner(wurzel, name)
            except ValueError:
                continue
        return wurzel
    f = wurzel
    for name in rest:
        f = _unterordner(f, name)
    return f


def lesen(pfad: str, anzahl: int = ANZAHL) -> list[Mail]:
    """Die neuesten Mails des Ordners – nur lesen. ValueError mit verständlichem Text, wenn es nicht geht."""
    try:
        import pythoncom
        import win32com.client
    except ImportError as exc:
        raise ValueError("Die Outlook-Vorschau gibt es nur unter Windows mit dem klassischen Outlook.") from exc
    pythoncom.CoInitialize()
    try:
        try:
            ol = win32com.client.GetActiveObject("Outlook.Application")     # nicht starten, nur ein laufendes nutzen
        except Exception as exc:                      # noqa: BLE001
            raise ValueError("Outlook ist nicht geöffnet – die Vorschau erscheint, sobald Outlook läuft.") from exc
        ns = ol.GetNamespace("MAPI")
        items = _ordner_finden(ns, pfad).Items
        items.Sort("[ReceivedTime]", True)
        erg: list[Mail] = []
        m = items.GetFirst()
        while m is not None and len(erg) < anzahl:
            if getattr(m, "Class", 0) == 43:          # olMail
                rt = m.ReceivedTime
                erg.append(Mail(datetime(rt.year, rt.month, rt.day, rt.hour, rt.minute), str(m.Subject or "(ohne Betreff)"),
                                str(m.SenderName or ""), bool(m.UnRead)))
            m = items.GetNext()
        return erg
    finally:
        pythoncom.CoUninitialize()


def vorschau(neu: bool = False) -> tuple[list[Mail], str]:
    """(Mails, Fehlertext) – höchstens alle ``NEU_LADEN_S`` Sekunden frisch aus Outlook."""
    pfad = ordner()
    if not pfad:
        return [], ""
    if not neu and _ZWISCHEN["pfad"] == pfad and time.monotonic() - _ZWISCHEN["zeit"] < NEU_LADEN_S:
        return _ZWISCHEN["erg"]
    try:
        erg = (lesen(pfad), "")
    except ValueError as exc:
        erg = ([], str(exc))
    except Exception as exc:                          # noqa: BLE001 – Outlook-Fehler nie bis zur Oberfläche durchreichen
        erg = ([], f"Outlook konnte nicht gelesen werden: {exc}")
    _ZWISCHEN.update(zeit=time.monotonic(), pfad=pfad, erg=erg)
    return erg


# ---- Oberfläche (Block auf „Heute“) ------------------------------------------------------

def block(a) -> None:
    from nicegui import run, ui

    from .ui_bausteine import attr, knopf

    pfad = ordner()
    with ui.element("section").classes("m-tz-block m-tz-outlook"):
        with ui.element("div").classes("m-tz-ab"):
            ui.label("Outlook" + (f" · {pfad}" if pfad else ""))
            if pfad:
                knopf("", lambda: _laden(True), "leise", "refresh", "Neu laden")
        inhalt = ui.element("div").classes("m-tz-mails")
        if not pfad:
            with inhalt:
                ui.label("Die Vorschau ist aus. In den Einstellungen den Outlook-Ordner eintragen (z. B. „Internatsdienst“) – "
                         "dann stehen hier Betreff, Zeit und ungelesen. Nur lesen, nichts wird verändert.").classes(
                    "m-zweite").style("white-space:normal")
                knopf("Einstellen", lambda: a.oeffnen("einstellungen"), "leise", "settings")
            return
        with inhalt:
            ui.label("Lädt …").classes("m-zweite")

    async def _laden(neu: bool = False) -> None:
        mails, fehler = await run.io_bound(vorschau, neu)
        inhalt.clear()
        with inhalt:
            if fehler:
                ui.label(fehler).classes("m-zweite").style("white-space:normal")
                return
            if not mails:
                ui.label("Keine Mails in diesem Ordner.").classes("m-zweite")
                return
            for m in mails:
                with ui.element("div").classes("m-tz-mail" + (" neu" if m.ungelesen else "")):
                    ui.label(m.wann).classes("m-tz-mzeit")
                    with ui.element("div").classes("m-tz-mtext"):
                        attr(ui.label(m.betreff).classes("m-tz-mbetreff"), title=m.betreff)
                        ui.label(m.absender).classes("m-zweite")
                    if m.ungelesen:
                        ui.label("ungelesen").classes("m-pille akzent")
            ungelesen = sum(1 for m in mails if m.ungelesen)
            ui.label(f"nur lesen · {ungelesen} ungelesen unter den neuesten {len(mails)} · "
                     f"Stand {datetime.now():%H:%M}").classes("m-tz-meta")

    ui.timer(0.05, _laden, once=True)
