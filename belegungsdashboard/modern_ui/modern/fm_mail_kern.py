"""1.36: Mail an FM (Facility-Management) – als Outlook-Entwurf zum Prüfen und Absenden; 1.38 auch direkt senden.

* Die FM-Adresse wird je Standort gespeichert (Programm-Einstellung ``fm_mail``, für alle PCs gleich).
* ``entwurf`` legt im laufenden klassischen Outlook eine neue Mail an und zeigt sie an – gesendet wird erst, wenn man
  in Outlook auf „Senden“ klickt. Outlook wird nie selbst gestartet; läuft es nicht, gibt es einen ``mailto:``-Link
  (öffnet das Standard-Mailprogramm).
* Rein bis auf den Outlook-Aufruf (pywin32, nur unter Windows).
"""

from __future__ import annotations

import re
from urllib.parse import quote

SCHLUESSEL = "fm_mail"
_MAIL = re.compile(r"^[^@\s;,]+@[^@\s;,]+\.[^@\s;,]+$")


def adresse() -> str:
    from belegung import speicher

    return str(speicher.einstellungen().get(SCHLUESSEL, "") or "")


def adresse_setzen(wert: str) -> str:
    from belegung import speicher

    from .kern import _schritt

    teile = [t.strip() for t in re.split(r"[;,]", wert or "") if t.strip()]
    for t in teile:
        if not _MAIL.match(t):
            raise ValueError(f"„{t}“ ist keine gültige Mail-Adresse.")
    neu = "; ".join(teile)
    _schritt("FM-Adresse", lambda: speicher.einstellung_setzen(SCHLUESSEL, neu), [speicher.EINSTELLUNGEN])
    return f"FM-Adresse gespeichert: {neu}" if neu else "FM-Adresse entfernt"


def mailto(an: str, betreff: str, text: str) -> str:
    return f"mailto:{quote(an, safe='@;,')}?subject={quote(betreff)}&body={quote(text)}"


def entwurf(an: str, betreff: str, text: str) -> str:
    """Outlook-Entwurf anzeigen. Rückgabe "" = geklappt, sonst Grund (dann den mailto-Link anbieten)."""
    from . import outlook_kern as ok

    if not (an or "").strip():
        return "Bitte zuerst die FM-Adresse eintragen."
    try:
        pythoncom, ol = ok._outlook("Outlook ist nicht geöffnet – die Mail kann stattdessen im Standard-Mailprogramm "
                                    "geöffnet werden.")
    except ValueError as exc:
        return str(exc)
    try:
        m = ol.CreateItem(0)                       # olMailItem
        m.To = an
        m.Subject = betreff
        m.Body = text
        m.Display(False)
        return ""
    except Exception as exc:                       # noqa: BLE001
        return f"Outlook konnte die Mail nicht anlegen: {exc}"
    finally:
        pythoncom.CoUninitialize()


def vorlage(zimmer: str = "", art: str = "", notiz: str = "", absender: str = "") -> tuple[str, str]:
    """Betreff und Text einer FM-Mail (Zimmer, Mangel, Notiz), freundlich und knapp."""
    wo = f"Zimmer {zimmer}" if zimmer else "Internat"
    betreff = f"FM-Auftrag: {wo}" + (f" – {art}" if art else "")
    zeilen = ["Hallo,", "", f"bitte um Erledigung: {wo}" + (f", {art}" if art else "") + "."]
    if notiz:
        zeilen += ["", notiz]
    zeilen += ["", "Vielen Dank!", absender or ""]
    return betreff, "\n".join(zeilen).rstrip() + "\n"


def senden(an: str, betreff: str, text: str) -> str:
    """1.38: Mail direkt über das laufende Outlook senden (Absender = eigenes Konto, Kopie in „Gesendete Elemente“).
    Rückgabe "" = gesendet, sonst Grund. Outlook wird nie selbst gestartet."""
    from . import outlook_kern as ok

    if not (an or "").strip():
        return "Bitte zuerst die FM-Adresse eintragen."
    if not (betreff or "").strip() or not (text or "").strip():
        return "Bitte Betreff und Text ausfüllen."
    try:
        pythoncom, ol = ok._outlook("Outlook ist nicht geöffnet – bitte Outlook starten und noch einmal senden.")
    except ValueError as exc:
        return str(exc)
    try:
        m = ol.CreateItem(0)
        m.To = an
        m.Subject = betreff
        m.Body = text
        m.Send()
        return ""
    except Exception as exc:                       # noqa: BLE001
        return f"Outlook konnte die Mail nicht senden: {exc}"
    finally:
        pythoncom.CoUninitialize()
