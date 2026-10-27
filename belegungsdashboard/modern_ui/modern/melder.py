"""Windows-Meldungen und „Mit Windows starten“ – wie im Hauptprogramm, für die neue Oberfläche.

Gemeldet wird dasselbe wie im Hauptprogramm: fällige Erinnerungen (Termine), offene Reinigungen vor einer Anreise und
Facility-Checks nach langem Aufenthalt. Was gemeldet wurde, merken sich die gemeinsamen Daten (``gemeldet``) – laufen
beide Programme, kommt jede Meldung trotzdem nur einmal. Ohne Qt/NiceGUI, damit es testbar bleibt.
"""

from __future__ import annotations

import logging
import os
import subprocess
import sys
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path
from xml.sax.saxutils import escape

from belegung import speicher

log = logging.getLogger(__name__)

EINSTELLUNG = "modern_windows_meldungen"         # Standard: an
TAKT_MINUTEN = 15                                # wie im Hauptprogramm
AUTOSTART_DATEI = "INNternat_neue_Oberflaeche.cmd"
MINIMIERT = "--minimiert"
# Windows kennt PowerShell als absendende App – so braucht es keine eigene Registrierung und kein Zusatzpaket.
_APP_ID = r"{1AC14E77-02E7-4E5D-B744-2EB1AE5198B7}\WindowsPowerShell\v1.0\powershell.exe"


@dataclass
class Meldung:
    titel: str
    text: str
    ziel: str           # wie im Hauptprogramm (Neuigkeiten): termine | zimmerplan:Reinigung | zimmerplan:Aufgaben


def an() -> bool:
    return bool(speicher.einstellungen().get(EINSTELLUNG, True))


def setzen(wert: bool) -> None:
    speicher.einstellung_setzen(EINSTELLUNG, bool(wert))


def sammeln(heute: date | None = None) -> list[Meldung]:
    """Was jetzt neu zu melden ist – und gleich als gemeldet merken (einmal am Tag je Termin/Zimmer)."""
    from belegung import termine as tm

    heute = heute or date.today()
    erg: list[Meldung] = []
    try:
        neu = tm.zu_melden(tm.alle(), heute)
        if neu:
            erg.append(Meldung(*tm.meldetext(neu), "termine"))
            tm.gemeldet_setzen(neu, heute)
    except Exception:                          # noqa: BLE001 – eine Quelle darf die anderen nicht verhindern
        log.exception("Termine konnten nicht geprüft werden")
    try:
        erg += _reinigung_und_facility(heute)
    except Exception:                          # noqa: BLE001
        log.exception("Reinigung/Facility konnten nicht geprüft werden")
    for m in erg:
        _als_neuigkeit(m)
    return erg


def _reinigung_und_facility(heute: date) -> list[Meldung]:
    from belegung import eintragen
    from belegung import reinigungsliste as rl
    from belegung import zimmerplan as zp

    erg = []
    st = zp.laden()
    zpv = st.zimmer_pivot
    rs = zp.reinigungen(st.lage, heute - timedelta(days=14), heute + timedelta(days=1),
                        zpv.zeitraum[1] if zpv else None, zpv.zeitraum[0] if zpv else None,
                        bool(speicher.einstellungen().get("reinigung_anreisetag", False)))
    neu = rl.zu_melden(rs, heute)
    if neu:
        titel = "Reinigung offen – Anreise steht an" if len(neu) == 1 else f"{len(neu)} Reinigungen offen – Anreisen stehen an"
        erg.append(Meldung(titel, "\n".join(rl.konflikt_text(r) for r in neu[:4]), "zimmerplan:Reinigung"))
        rl.gemeldet_setzen(neu, heute)
    fac = eintragen.facility_zu_melden(st.lage, heute)
    if fac:
        erg.append(Meldung("Facility-Check nach langem Aufenthalt" if len(fac) == 1 else
                           f"{len(fac)} Facility-Checks nach langem Aufenthalt",
                           "\n".join(c.text for c in fac[:4]), "zimmerplan:Aufgaben"))
        eintragen.facility_gemeldet(fac)
    return erg


def _als_neuigkeit(m: Meldung) -> None:
    from belegung import neuigkeiten

    try:
        neuigkeiten.hinzufuegen(f"{m.titel}: {m.text.splitlines()[0]}" if m.text else m.titel, "info", m.ziel)
    except OSError:
        log.exception("Neuigkeit konnte nicht gespeichert werden")


def toast_xml(titel: str, text: str) -> str:
    zeilen = "".join(f"<text>{escape(z)}</text>" for z in text.splitlines()[:3])
    return (f'<toast><visual><binding template="ToastGeneric"><text>{escape(titel)}</text>{zeilen}</binding></visual>'
            '<audio src="ms-winsoundevent:Notification.Default"/></toast>')


def ps_kodiert(skript: str) -> str:
    """PowerShell -EncodedCommand (UTF-16LE, Base64): keine Probleme mit Anführungszeichen und Umlauten."""
    import base64

    return base64.b64encode(skript.encode("utf-16-le")).decode("ascii")


def windows_zeigen(titel: str, text: str) -> bool:
    """Meldung unten rechts (Windows 10/11). False, wenn das hier nicht geht (anderes System, PowerShell fehlt)."""
    if sys.platform != "win32":
        return False
    xml = toast_xml(titel, text).replace("'", "''")
    skript = ("[Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] > $null;"
              "[Windows.Data.Xml.Dom.XmlDocument, Windows.Data.Xml.Dom.XmlDocument, ContentType = WindowsRuntime] > $null;"
              f"$x = New-Object Windows.Data.Xml.Dom.XmlDocument; $x.LoadXml('{xml}');"
              f"[Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier('{_APP_ID}')"
              ".Show([Windows.UI.Notifications.ToastNotification]::new($x))")
    try:
        subprocess.Popen(["powershell", "-NoProfile", "-NonInteractive", "-WindowStyle", "Hidden", "-EncodedCommand",
                          ps_kodiert(skript)], creationflags=0x08000000)          # CREATE_NO_WINDOW
        return True
    except OSError:
        log.exception("Windows-Meldung nicht möglich")
        return False


# ---- Mit Windows starten ---------------------------------------------------------------------------------

def startordner() -> Path | None:
    appdata = os.environ.get("APPDATA")
    return Path(appdata) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup" if appdata else None


def autostart_moeglich() -> bool:
    return sys.platform == "win32" and startordner() is not None


def autostart_aktiv() -> bool:
    ordner = startordner()
    return bool(ordner and (ordner / AUTOSTART_DATEI).exists())


def autostart_befehl(ordner: Path) -> str:
    """Inhalt der .cmd: startet die neue Oberfläche minimiert (pythonw aus der eigenen .venv, sonst Start.bat)."""
    pythonw = ordner / ".venv" / "Scripts" / "pythonw.exe"
    kopf = f'@echo off\r\nchcp 65001 >nul\r\ncd /d "{ordner}"\r\n'
    if pythonw.exists():
        return kopf + f'start "" "{pythonw}" app.py {MINIMIERT}\r\n'
    return kopf + f"call Start.bat {MINIMIERT}\r\n"


def autostart_setzen(an_: bool, programm: Path) -> str:
    ordner = startordner()
    if ordner is None or sys.platform != "win32":
        raise OSError("„Mit Windows starten“ gibt es nur unter Windows.")
    datei = ordner / AUTOSTART_DATEI
    if an_:
        ordner.mkdir(parents=True, exist_ok=True)
        datei.write_text(autostart_befehl(programm), encoding="utf-8", newline="")
        return "Startet ab jetzt mit Windows (minimiert) und meldet Fälliges"
    datei.unlink(missing_ok=True)
    return "Startet nicht mehr mit Windows"
