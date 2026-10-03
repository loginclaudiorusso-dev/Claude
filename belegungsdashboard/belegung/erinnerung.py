"""Erinnerungen an Abreisen.

Kanäle:
* ``outlook`` – Termin im eigenen Outlook-Kalender am Abreisetag mit Erinnerung X Tage vorher.
  Erinnert auch, wenn das Dashboard geschlossen ist.
* ``mail``    – E-Mail an sich selbst, die Outlook zeitversetzt am Erinnerungstag verschickt.
* ``ics``     – Kalenderdatei (.ics) zum Öffnen/Importieren in einen beliebigen Kalender.
* ``app``     – nur im Dashboard (Hinweis beim Start und auf der Übersicht).

Outlook wird über COM angesprochen (pywin32) und muss im GUI-Thread laufen.
"""

from __future__ import annotations

import sys
import uuid
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path

from .konfig import datenordner

KANAELE = {"outlook": "Outlook-Termin mit Erinnerung", "mail": "E-Mail an mich (zeitversetzt)",
           "ics": "Kalenderdatei (.ics)", "app": "Nur im Dashboard"}
KANAL_KURZ = {"outlook": "Outlook", "mail": "E-Mail", "ics": "Kalenderdatei", "app": "Dashboard"}
KATEGORIE = "Belegungsdashboard"
UHRZEIT = time(8, 0)


def outlook_moeglich() -> bool:
    import importlib.util

    return sys.platform == "win32" and importlib.util.find_spec("win32com") is not None


def standard_kanal() -> str:
    return "outlook" if outlook_moeglich() else "app"


def betreff(name: str, abreise: date) -> str:
    return f"Abreise {name} – {abreise:%d.%m.%Y}"


# ---------------------------------------------------------------------------------------
# Outlook
# ---------------------------------------------------------------------------------------

def _outlook():
    import win32com.client

    return win32com.client.Dispatch("Outlook.Application")


def _outlook_zeit(d: datetime) -> str:
    # Als Text übergeben: pywin32 würde ein naives datetime je nach Version als UTC deuten.
    return d.strftime("%Y-%m-%d %H:%M")


def outlook_termin(titel: str, abreise: date, tage_vorher: int, text: str) -> str:
    """Termin am Abreisetag um 8 Uhr, Erinnerung ``tage_vorher`` Tage davor. Gibt die EntryID zurück."""
    ol = _outlook()
    t = ol.CreateItem(1)  # olAppointmentItem
    t.Subject = titel
    t.Body = text
    t.Start = _outlook_zeit(datetime.combine(abreise, UHRZEIT))
    t.Duration = 15
    t.BusyStatus = 0  # frei – blockiert den Kalender nicht
    t.ReminderSet = True
    t.ReminderMinutesBeforeStart = max(int(tage_vorher), 0) * 24 * 60
    t.Categories = KATEGORIE
    t.Save()
    return str(t.EntryID)


def outlook_mail(titel: str, erinnern_am: date, text: str, empfaenger: str = "") -> str:
    """E-Mail an sich selbst, die Outlook erst am Erinnerungstag verschickt (bleibt bis dahin im Postausgang)."""
    ol = _outlook()
    if not empfaenger:
        nutzer = ol.Session.CurrentUser.AddressEntry
        try:
            empfaenger = nutzer.GetExchangeUser().PrimarySmtpAddress
        except Exception:
            empfaenger = nutzer.Address
    marke = f"BD-{uuid.uuid4().hex[:10]}"
    m = ol.CreateItem(0)  # olMailItem
    m.To = empfaenger
    m.Subject = titel
    m.Body = f"{text}\n\n[{marke}]"
    m.DeferredDeliveryTime = _outlook_zeit(datetime.combine(erinnern_am, UHRZEIT))
    m.Categories = KATEGORIE
    m.Send()
    # Beim Senden wandert die Mail in den Postausgang und bekommt eine neue EntryID –
    # deshalb über die Marke im Text wiederfinden.
    return f"mail:{marke}"


def outlook_entfernen(kennung: str) -> bool:
    """Termin bzw. noch nicht verschickte Mail löschen. False, wenn nichts (mehr) zu finden ist."""
    if not kennung:
        return False
    try:
        ol = _outlook()
        if kennung.startswith("mail:"):
            marke = kennung[5:]
            for item in list(ol.Session.GetDefaultFolder(4).Items):  # olFolderOutbox
                if marke in (item.Body or ""):
                    item.Delete()
                    return True
            return False
        ol.Session.GetItemFromID(kennung).Delete()
        return True
    except Exception:
        return False  # schon gelöscht, verschickt oder anderes Postfach


# ---------------------------------------------------------------------------------------
# .ics
# ---------------------------------------------------------------------------------------

def _esc(text: str) -> str:
    return text.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")


def ics_text(titel: str, abreise: date, tage_vorher: int, text: str, uid: str | None = None) -> str:
    start = datetime.combine(abreise, UHRZEIT)
    trigger = f"-P{tage_vorher}D" if tage_vorher > 0 else "-PT0M"
    zeilen = [
        "BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//INN-tegrativ//Belegungsdashboard//DE", "METHOD:PUBLISH",
        "BEGIN:VEVENT",
        f"UID:{uid or uuid.uuid4()}@belegungsdashboard",
        f"DTSTAMP:{datetime.now(timezone.utc):%Y%m%dT%H%M%SZ}",
        f"DTSTART:{start:%Y%m%dT%H%M%S}",
        f"DTEND:{start + timedelta(minutes=15):%Y%m%dT%H%M%S}",
        f"SUMMARY:{_esc(titel)}",
        f"DESCRIPTION:{_esc(text)}",
        f"CATEGORIES:{KATEGORIE}",
        "TRANSP:TRANSPARENT",
        "BEGIN:VALARM", "ACTION:DISPLAY", f"DESCRIPTION:{_esc(titel)}", f"TRIGGER:{trigger}", "END:VALARM",
        "END:VEVENT", "END:VCALENDAR",
    ]
    return "\r\n".join(zeilen) + "\r\n"


def ics_speichern(titel: str, abreise: date, tage_vorher: int, text: str, dateiname: str) -> Path:
    ordner = datenordner() / "erinnerungen"
    ordner.mkdir(parents=True, exist_ok=True)
    sicher = "".join(c if c.isalnum() or c in "-_" else "_" for c in dateiname)[:80]
    pfad = ordner / f"{sicher}.ics"
    pfad.write_text(ics_text(titel, abreise, tage_vorher, text, sicher), encoding="utf-8", newline="")
    return pfad


def ics_oeffnen(pfad: Path) -> None:
    import os

    if sys.platform == "win32":
        os.startfile(str(pfad))  # öffnet den Import im Standard-Kalender (Outlook)
