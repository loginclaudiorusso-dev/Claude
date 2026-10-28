"""Tagesbriefing als Outlook-Termin oder E-Mail an mich – die wichtigsten Punkte des Tages auf einen Blick.

Inhalt wie auf „Heute“: dringende Aufgaben zuerst, dann Anreisen (mit „bezugsfertig“), Abreisen, Reinigung, Allergiker,
fällige Termine. **Ohne Personennamen** – die Mail liegt im Postfach, Details stehen im Programm. Einmal am Tag, ab der
eingestellten Uhrzeit (beim Start bzw. im 15-Minuten-Takt der Meldungen). Outlook über COM (pywin32), nur unter Windows.
"""

from __future__ import annotations

import logging
import sys
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta

from belegung import speicher

log = logging.getLogger(__name__)

KANAELE = {"aus": "aus", "termin": "Outlook-Termin (mit Erinnerung)", "mail": "E-Mail an mich"}
EINSTELLUNG_KANAL = "modern_briefing_kanal"
EINSTELLUNG_UHRZEIT = "modern_briefing_uhrzeit"
STANDARD_UHRZEIT = "07:30"
STATUS = f"{speicher.IMPORT_ORDNER}/modern_briefing.json"
# Karten, deren Titel nur Anzahlen/Tage nennt – alle anderen (Termine, Mails …) kommen nur gezählt ins Briefing
OHNE_NAMEN = {"konflikte", "unbewohnbar", "allergie", "anreise", "eintragen", "reinigung_dringend", "reinigung", "abreisen",
              "facility", "maengel", "mieterende", "gebaeudeplan"}
WOCHENTAGE = ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"]


@dataclass
class Briefing:
    betreff: str
    text: str
    dringend: int


def kanal() -> str:
    k = speicher.einstellungen().get(EINSTELLUNG_KANAL, "aus")
    return k if k in KANAELE else "aus"


def uhrzeit() -> time:
    try:
        h, m = str(speicher.einstellungen().get(EINSTELLUNG_UHRZEIT, STANDARD_UHRZEIT)).split(":")
        return time(int(h), int(m))
    except (ValueError, TypeError):
        return time(7, 30)


def einstellen(kanal_: str, uhrzeit_: str) -> str:
    if kanal_ not in KANAELE:
        raise ValueError("Unbekannter Weg für das Briefing.")
    h, m = (uhrzeit_ or STANDARD_UHRZEIT).split(":")
    t = time(int(h), int(m))
    speicher.einstellung_setzen(EINSTELLUNG_KANAL, kanal_)
    speicher.einstellung_setzen(EINSTELLUNG_UHRZEIT, f"{t:%H:%M}")
    return "Tagesbriefing aus" if kanal_ == "aus" else f"Tagesbriefing täglich ab {t:%H:%M} als {KANAELE[kanal_]}"


def status() -> dict:
    return speicher.lesen(STATUS, {})


# ---- Inhalt ----------------------------------------------------------------------------------------------

def erstellen(stand, heute: date) -> Briefing:
    """Text ohne Personennamen: Karten-Titel nennen nur Anzahlen; Termine und Mails (Titel mit Namen) nur gezählt."""
    from belegung import cockpit

    from . import hinweise_kern as hk
    from . import kern

    karten = kern.karten(stand, heute)

    def titel(k) -> str | None:
        art = k.id.split(":")[0]
        if art == "umzug":
            return "Umzug mit Konflikt"
        return k.titel if art in OHNE_NAMEN or art.startswith("engpass_") else None

    dringend = [t for k in karten if k.stufe == "dringend" and (t := titel(k))]
    bald = [t for k in karten if k.stufe == "bald" and (t := titel(k))]
    n_termine = sum(1 for k in karten if k.id.startswith("termin:"))
    n_mails = sum(1 for k in karten if k.id.startswith("mail:"))
    z = []
    z.append(f"Tagesbriefing – {WOCHENTAGE[heute.weekday()]}, {heute:%d.%m.%Y}")
    z.append("")
    if dringend:
        z.append("ZUERST (dringend)")
        z += [f"• {t}" for t in dringend]
        z.append("")
    if bald:
        z.append("ALS NÄCHSTES")
        z += [f"• {t}" for t in bald[:6]] + ([f"• … und {len(bald) - 6} weitere"] if len(bald) > 6 else [])
        z.append("")
    z.append("ANREISEN")
    anreisen = [a for a in cockpit.anreisen(stand, heute, 1)]
    if not anreisen:
        z.append("• heute und morgen keine")
    for a in anreisen:
        wann = "heute" if a.tag == heute else "morgen"
        teil = f"• {wann}: {a.personen} Person{'en' if a.personen != 1 else ''}"
        try:
            b = kern.bereitschaft(stand, kern.zeilen(stand, a.tag.isoformat(), heute), a.tag)
            teil += f" – {b.bereit} von {b.n} Zimmern bezugsfertig"
            vorbereiten = sum(1 for p in b.punkte if p[0] == "vorbereiten")
            if vorbereiten:
                teil += f", {vorbereiten} × vorbereiten (z. B. Hilfsmittel)"
        except Exception:                      # noqa: BLE001 – Zusatz
            teil += f" – {a.mit_zimmer} mit Zimmer"
        z.append(teil)
    ab = cockpit.abreisen(stand, heute, 1)
    n_heute = sum(1 for x in ab if x.tag == heute)
    z.append(f"ABREISEN: heute {n_heute}, morgen {len(ab) - n_heute}")
    eilig, offen = cockpit.reinigung_heute(stand, heute)
    z.append(f"REINIGUNG: {len(eilig)} eilig (Anreise bald), {len(offen)} heute offen")
    zimmer = cockpit.zimmer_heute(stand, heute)
    z.append(f"ZIMMER: {zimmer['frei']} heute frei")
    faelle = hk.allergie_faelle(stand, heute)
    if faelle:
        falsch = sum(1 for f in faelle if not f.auf_etage)
        z.append(f"ALLERGIKER: {len(faelle)} in den nächsten 3 Wochen" +
                 (f" – {falsch} nicht auf der {hk.ALLERGIE_TEXT}" if falsch else f" – alle auf der {hk.ALLERGIE_TEXT}"))
    if n_termine or n_mails:
        z.append(f"TERMINE/MAILS: {n_termine} Erinnerung{'en' if n_termine != 1 else ''} fällig, {n_mails} Mail{'s' if n_mails != 1 else ''} offen")
    z.append("")
    z.append("Ohne Namen – Details im Programm (INNternat → Heute).")
    betreff = (f"INNternat: {len(dringend)} dringend · " if dringend else "INNternat: ") + \
        f"Briefing {WOCHENTAGE[heute.weekday()][:2]} {heute:%d.%m.}"
    return Briefing(betreff, "\n".join(z), len(dringend))


# ---- Versand ---------------------------------------------------------------------------------------------

def faellig(jetzt: datetime) -> bool:
    """Heute noch nicht geschickt (auch kein Fehlversuch heute) und die Uhrzeit ist erreicht."""
    if kanal() == "aus" or jetzt.time() < uhrzeit():
        return False
    return status().get("datum") != jetzt.date().isoformat()


def pruefen(jetzt: datetime | None = None) -> str | None:
    """Aus dem Melde-Takt: schickt das Briefing, wenn es heute fällig ist (sonst nichts)."""
    from belegung import zimmerplan as zp

    jetzt = jetzt or datetime.now()
    return senden(zp.laden(), jetzt) if faellig(jetzt) else None


def _outlook_senden(art: str, b: Briefing, jetzt: datetime) -> None:
    if sys.platform != "win32":
        raise OSError("Das Briefing per Outlook geht nur unter Windows mit installiertem Outlook (klassisch).")
    import pythoncom

    from belegung import erinnerung

    pythoncom.CoInitialize()
    try:
        ol = erinnerung._outlook()
        if art == "termin":
            t = ol.CreateItem(1)                     # olAppointmentItem
            t.Subject = b.betreff
            t.Body = b.text
            start = max(datetime.combine(jetzt.date(), uhrzeit()), jetzt + timedelta(minutes=2))
            t.Start = erinnerung._outlook_zeit(start)
            t.Duration = 15
            t.BusyStatus = 0                        # frei – blockiert den Kalender nicht
            t.ReminderSet = True
            t.ReminderMinutesBeforeStart = 0
            t.Categories = erinnerung.KATEGORIE
            t.Save()
        else:
            nutzer = ol.Session.CurrentUser.AddressEntry
            try:
                an = nutzer.GetExchangeUser().PrimarySmtpAddress
            except Exception:                        # noqa: BLE001 – kein Exchange: Adresse direkt
                an = nutzer.Address
            m = ol.CreateItem(0)                     # olMailItem
            m.To = an
            m.Subject = b.betreff
            m.Body = b.text
            m.Categories = erinnerung.KATEGORIE
            m.Send()
    finally:
        pythoncom.CoUninitialize()


def senden(stand, jetzt: datetime | None = None, art: str | None = None, test: bool = False, sender=None) -> str:
    """Briefing erstellen und über Outlook schicken. Merkt sich den Tag (auch einen Fehlversuch – kein Wiederholen im
    15-Minuten-Takt). ``test``: sofort, ohne den Tag zu verbrauchen. ``sender`` nur für Tests."""
    jetzt = jetzt or datetime.now()
    art = art or kanal()
    if art == "aus":
        raise ValueError("Das Tagesbriefing ist ausgeschaltet.")
    b = erstellen(stand, jetzt.date())
    try:
        (sender or _outlook_senden)(art, b, jetzt)
    except Exception as exc:                    # noqa: BLE001
        if not test:
            speicher.schreiben(STATUS, {"datum": jetzt.date().isoformat(), "zeit": f"{jetzt:%H:%M}", "kanal": art,
                                        "ok": False, "fehler": str(exc)})
        log.exception("Tagesbriefing nicht gesendet")
        raise OSError(f"Briefing nicht gesendet: {exc}") from exc
    if not test:
        speicher.schreiben(STATUS, {"datum": jetzt.date().isoformat(), "zeit": f"{jetzt:%H:%M}", "kanal": art, "ok": True})
    return f"Briefing als {KANAELE[art]} geschickt" + (" (Test)" if test else "")
