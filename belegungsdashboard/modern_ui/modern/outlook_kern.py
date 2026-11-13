"""Outlook-Vorschau auf „Heute“: die neuesten Mails eines Ordners (z. B. des Postfachs „Internatsdienst“) – nur lesen.

Zugriff wie bei Erinnerungen und Tagesbriefing: lokal über das klassische Outlook (Windows, pywin32/COM). Es wird
nichts gesendet, verschoben, gelöscht oder als gelesen markiert; Outlook wird nicht gestartet, wenn es nicht läuft.
1.02: Eine Mail (oder den ganzen Ordner) per Klick **in Outlook öffnen** – Outlook zeigt sie in seinem eigenen
Fenster; ob sie dann als gelesen gilt, regelt Outlook wie bei jedem Öffnen dort.
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
    eintrag: str = ""            # 1.02: Outlook-EntryID – zum Öffnen in Outlook
    ablage: str = ""             # StoreID des Postfachs (freigegebene Postfächer)

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


def _outlook(text: str = "Outlook ist nicht geöffnet – die Vorschau erscheint, sobald Outlook läuft."):
    """(pythoncom, laufendes Outlook) – nie starten. Aufrufer meldet COM an und ab."""
    try:
        import pythoncom
        import win32com.client
    except ImportError as exc:
        raise ValueError("Die Outlook-Vorschau gibt es nur unter Windows mit dem klassischen Outlook.") from exc
    pythoncom.CoInitialize()
    try:
        return pythoncom, win32com.client.GetActiveObject("Outlook.Application")
    except Exception as exc:                          # noqa: BLE001
        pythoncom.CoUninitialize()
        raise ValueError(text) from exc


def lesen(pfad: str, anzahl: int = ANZAHL) -> list[Mail]:
    """Die neuesten Mails des Ordners – nur lesen. ValueError mit verständlichem Text, wenn es nicht geht."""
    pythoncom, ol = _outlook()
    try:
        ns = ol.GetNamespace("MAPI")
        f = _ordner_finden(ns, pfad)
        try:
            ablage = str(f.StoreID or "")
        except Exception:                             # noqa: BLE001
            ablage = ""
        items = f.Items
        items.Sort("[ReceivedTime]", True)
        erg: list[Mail] = []
        m = items.GetFirst()
        while m is not None and len(erg) < anzahl:
            if getattr(m, "Class", 0) == 43:          # olMail
                rt = m.ReceivedTime
                erg.append(Mail(datetime(rt.year, rt.month, rt.day, rt.hour, rt.minute), str(m.Subject or "(ohne Betreff)"),
                                str(m.SenderName or ""), bool(m.UnRead), str(getattr(m, "EntryID", "") or ""), ablage))
            m = items.GetNext()
        return erg
    finally:
        pythoncom.CoUninitialize()


def oeffnen(eintrag: str, ablage: str = "") -> str:
    """1.02: Die Mail in Outlook im eigenen Fenster zeigen (nur ein laufendes Outlook). Rückgabe: Fehlertext oder ""."""
    if not eintrag:
        return "Diese Mail lässt sich nicht öffnen."
    try:
        pythoncom, ol = _outlook("Outlook ist nicht geöffnet – bitte Outlook starten, dann noch einmal klicken.")
    except ValueError as exc:
        return str(exc)
    try:
        ns = ol.GetNamespace("MAPI")
        m = ns.GetItemFromID(eintrag, ablage) if ablage else ns.GetItemFromID(eintrag)
        m.Display()
        return ""
    except Exception:                                 # noqa: BLE001
        return "Die Mail wurde in Outlook nicht gefunden (verschoben oder gelöscht?) – bitte neu laden."
    finally:
        pythoncom.CoUninitialize()


def ordner_oeffnen(pfad: str | None = None) -> str:
    """1.02: Den eingestellten Ordner (z. B. das Postfach „Internatsdienst“) in einem Outlook-Fenster zeigen."""
    pfad = ordner() if pfad is None else pfad
    if not pfad:
        return "Kein Outlook-Ordner eingestellt."
    try:
        pythoncom, ol = _outlook("Outlook ist nicht geöffnet – bitte Outlook starten, dann noch einmal klicken.")
    except ValueError as exc:
        return str(exc)
    try:
        _ordner_finden(ol.GetNamespace("MAPI"), pfad).Display()
        return ""
    except ValueError as exc:
        return str(exc)
    except Exception as exc:                          # noqa: BLE001
        return f"Outlook konnte den Ordner nicht zeigen: {exc}"
    finally:
        pythoncom.CoUninitialize()


def vorschau(neu: bool = False, anzahl: int = ANZAHL) -> tuple[list[Mail], str]:
    """(Mails, Fehlertext) – höchstens alle ``NEU_LADEN_S`` Sekunden frisch aus Outlook."""
    pfad = ordner()
    if not pfad:
        return [], ""
    if (not neu and _ZWISCHEN["pfad"] == (pfad, anzahl)
            and time.monotonic() - _ZWISCHEN["zeit"] < NEU_LADEN_S):
        return _ZWISCHEN["erg"]
    try:
        erg = (lesen(pfad, anzahl), "")
    except ValueError as exc:
        erg = ([], str(exc))
    except Exception as exc:                          # noqa: BLE001 – Outlook-Fehler nie bis zur Oberfläche durchreichen
        erg = ([], f"Outlook konnte nicht gelesen werden: {exc}")
    _ZWISCHEN.update(zeit=time.monotonic(), pfad=(pfad, anzahl), erg=erg)
    return erg


# ---- Oberfläche (Block auf „Heute“) ------------------------------------------------------

def _als_mail(x):
    """Ein Outlook-Element → Mail (oder None). Auch Unterhaltungen (Unterhaltungsansicht) und Elemente ohne
    Empfangszeit (Entwürfe, Berichte) – Hauptsache Betreff und Text."""
    if x is None:
        return None
    try:
        klasse = int(getattr(x, "Class", 0) or 0)
    except Exception:                              # noqa: BLE001
        klasse = 0
    if klasse == 43:                               # olMail
        return x
    try:                                           # Unterhaltungs-Kopf: die neueste Mail daraus
        teile = x.GetItems()
        beste = None
        for i in range(1, teile.Count + 1):
            m = teile.Item(i)
            if int(getattr(m, "Class", 0) or 0) == 43:
                beste = m
        if beste is not None:
            return beste
    except Exception:                              # noqa: BLE001
        pass
    try:
        if getattr(x, "Subject", None) is not None and getattr(x, "Body", None) is not None:
            return x                               # z. B. Besprechungsanfrage, Bericht – Text reicht zum Erkennen
    except Exception:                              # noqa: BLE001
        pass
    return None


def _zeit(m) -> datetime:
    for feld in ("ReceivedTime", "SentOn", "CreationTime"):
        try:
            rt = getattr(m, feld)
            return datetime(rt.year, rt.month, rt.day, rt.hour, rt.minute)
        except Exception:                          # noqa: BLE001
            continue
    return datetime.now().replace(second=0, microsecond=0)


def kandidaten(ol) -> list:
    """Reihenfolge: aktives Mail-Fenster, alle offenen Mail-Fenster (neuestes zuerst), Auswahl im aktiven Explorer,
    Auswahl in allen Explorern."""
    erg: list = []

    def dazu(f):
        try:
            x = f()
        except Exception:                          # noqa: BLE001
            return
        if x is not None:
            erg.append(x)
    dazu(lambda: ol.ActiveInspector().CurrentItem if ol.ActiveInspector() else None)
    try:
        insp = ol.Inspectors
        for i in range(insp.Count, 0, -1):
            dazu(lambda i=i: insp.Item(i).CurrentItem)
    except Exception:                              # noqa: BLE001
        pass

    def auswahl(ex):
        sel = ex.Selection if ex else None
        if sel is not None and sel.Count:
            for i in range(1, sel.Count + 1):
                dazu(lambda i=i: sel.Item(i))
    try:
        auswahl(ol.ActiveExplorer())
    except Exception:                              # noqa: BLE001
        pass
    try:
        exs = ol.Explorers
        for i in range(1, exs.Count + 1):
            try:
                auswahl(exs.Item(i))
            except Exception:                      # noqa: BLE001
                continue
    except Exception:                              # noqa: BLE001
        pass
    return erg


def offene_mail() -> dict | None:
    """0.91/1.04: Die Mail, an der gerade gearbeitet wird – zuerst ein geöffnetes Mail-Fenster, sonst die in Outlook
    markierte (auch in der Unterhaltungsansicht und in freigegebenen Postfächern). Nur ein laufendes klassisches
    Outlook (nie starten), nur lesen. None = keine Mail offen/markiert. ValueError mit verständlichem Text, wenn
    Outlook nicht erreichbar ist (z. B. „neues Outlook“)."""
    try:
        pythoncom, ol = _outlook("Outlook ist nicht geöffnet (oder es ist das „neue Outlook“) – bitte den Text "
                                 "einfügen.")
    except ValueError as exc:
        if "nur unter Windows" in str(exc):
            raise ValueError("Outlook ist nur unter Windows mit dem klassischen Outlook erreichbar – bitte den Text "
                             "einfügen.") from exc
        raise
    try:
        for x in kandidaten(ol):
            m = _als_mail(x)
            if m is None:
                continue
            try:
                betreff, absender, text = str(m.Subject or ""), str(getattr(m, "SenderName", "") or ""), str(m.Body or "")
            except Exception:                      # noqa: BLE001
                continue
            if not (betreff or text):
                continue
            return {"betreff": betreff, "absender": absender, "text": text, "zeit": _zeit(m)}
        return None
    finally:
        pythoncom.CoUninitialize()


def block(a, anzahl: int = ANZAHL, postfach: bool = False) -> None:
    """Mail-Block. ``postfach`` (1.02, Seite „Aufgaben“): mehr Mails, Kopf „Postfach“, Platz unter der Aufgabe.
    Klick auf eine Mail öffnet sie in Outlook; „In Outlook“ zeigt den ganzen Ordner."""
    from nicegui import run, ui

    from .ui_bausteine import attr, knopf

    pfad = ordner()

    async def _oeffnen(m: Mail) -> None:
        fehler = await run.io_bound(oeffnen, m.eintrag, m.ablage)
        if fehler:
            a.toast(fehler, fehler=True)

    async def _ordner() -> None:
        fehler = await run.io_bound(ordner_oeffnen)
        if fehler:
            a.toast(fehler, fehler=True)

    with ui.element("section").classes("m-tz-block m-tz-outlook" + (" m-pf-post" if postfach else "")):
        with ui.element("div").classes("m-tz-ab"):
            ui.label(("Postfach" if postfach else "Outlook") + (f" · {pfad}" if pfad else ""))
            if pfad:
                with ui.element("div").classes("m-tz-abk"):
                    knopf("In Outlook", _ordner, "leise", "open_in_new", "Den Ordner in Outlook öffnen")
                    knopf("", lambda: _laden(True), "leise", "refresh", "Neu laden")
        inhalt = ui.element("div").classes("m-tz-mails")
        if not pfad:
            with inhalt:
                ui.label("Die Vorschau ist aus. In den Einstellungen den Outlook-Ordner eintragen (z. B. „Internatsdienst“) – "
                         "dann stehen hier Betreff, Zeit und ungelesen; ein Klick öffnet die Mail in Outlook.").classes(
                    "m-zweite").style("white-space:normal")
                knopf("Einstellen", lambda: a.oeffnen("einstellungen"), "leise", "settings")
            return
        with inhalt:
            ui.label("Lädt …").classes("m-zweite")

    async def _laden(neu: bool = False) -> None:
        mails, fehler = await run.io_bound(vorschau, neu, anzahl)
        inhalt.clear()
        with inhalt:
            if fehler:
                ui.label(fehler).classes("m-zweite").style("white-space:normal")
                return
            if not mails:
                ui.label("Keine Mails in diesem Ordner.").classes("m-zweite")
                return
            for m in mails:
                z = ui.element("button").classes("m-tz-mail" + (" neu" if m.ungelesen else ""))
                attr(z, title=f"{m.betreff} – in Outlook öffnen", type="button")
                with z:
                    ui.label(m.wann).classes("m-tz-mzeit")
                    with ui.element("div").classes("m-tz-mtext"):
                        ui.label(m.betreff).classes("m-tz-mbetreff")
                        ui.label(m.absender).classes("m-zweite")
                    if m.ungelesen:
                        ui.label("ungelesen").classes("m-pille akzent")
                z.on("click", lambda m=m: _oeffnen(m))
            ungelesen = sum(1 for m in mails if m.ungelesen)
            ui.label(f"Klick öffnet die Mail in Outlook · {ungelesen} ungelesen unter den neuesten {len(mails)} · "
                     f"Stand {datetime.now():%H:%M}").classes("m-tz-meta")

    ui.timer(0.05, _laden, once=True)
