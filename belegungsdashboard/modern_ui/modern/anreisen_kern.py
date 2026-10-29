"""Daten für „Anreisen“ über das Zuteilen hinaus: Abreisen, Liste fürs Firmenprogramm (Eintragen), Drucklisten,
Planung zurücknehmen, Optimieren, UWT automatisch, Personenangaben und Personen von Hand – ohne NiceGUI."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import date, timedelta

from belegung import anreiseliste, cockpit, drucklisten, eintragen, speicher
from belegung import termine as tm
from belegung import umzug as um
from belegung import zimmerplan as zp

from .kern import WT, _schritt, kurz

ZEITRAEUME = {"heute": "Heute", "morgen": "Morgen", "woche": "Diese Woche", "naechste": "Nächste Woche"}


def zeitraum(wahl: str, heute: date) -> tuple[date, date]:
    if wahl == "heute":
        return heute, heute
    if wahl == "morgen":
        return heute + timedelta(days=1), heute + timedelta(days=1)
    montag = heute - timedelta(days=heute.weekday())
    if wahl == "naechste":
        montag += timedelta(days=7)
    return montag, montag + timedelta(days=6)


# ---- Abreisen ---------------------------------------------------------------------------

@dataclass
class AZeile:
    tag: str
    name: str
    massnahme: str
    zimmer: str
    zimmer_id: str
    naechste: str
    art: str


def abreisen(stand: zp.Planstand, von: date, bis: date) -> list[AZeile]:
    return [AZeile(f"{WT[a.tag.weekday()]} {a.tag:%d.%m.}", a.name, a.massnahme, kurz(a.zimmer), a.zimmer,
                   f"{WT[a.naechste.weekday()]} {a.naechste:%d.%m.}" if a.naechste else "–", a.art)
            for a in cockpit.abreiseliste(stand, von, bis)]


def abreisen_druck(stand: zp.Planstand, von: date, bis: date) -> str:
    titel = f"{von:%d.%m.%Y}" if von == bis else f"{von:%d.%m.} – {bis:%d.%m.%Y}"
    return drucklisten.abreiseliste_html(cockpit.abreiseliste(stand, von, bis), titel)


# ---- Eintragen ins Firmenprogramm -------------------------------------------------------

@dataclass
class EZeile:
    schluessel: str
    name: str
    massnahme: str
    zimmer: str
    von: date
    bis: date
    haken: bool


def eintragen_liste(stand: zp.Planstand, heute: date, tage: int = 14) -> list[EZeile]:
    return [EZeile(z.schluessel, z.name, z.massnahme, kurz(z.zimmer), z.von, z.bis, z.haken)
            for z in eintragen.offen(stand.lage, heute, heute + timedelta(days=tage))]


def eintragen_setzen(schluessel: list[str], an: bool, heute: date, tage: int = 14) -> str:
    stand = zp.laden()
    zs = [z for z in eintragen.offen(stand.lage, heute, heute + timedelta(days=tage)) if z.schluessel in set(schluessel)]
    if not zs:
        raise ValueError("Diese Einträge gibt es nicht mehr.")
    _schritt("Eingetragen" if an else "Nicht eingetragen", lambda: eintragen.setzen(zs, an), [eintragen.DATEI])
    return f"{len(zs)} als eingetragen markiert" if an else f"{len(zs)} wieder offen"


def eintragen_text(stand: zp.Planstand, heute: date, tage: int = 14, nur_offen: bool = True) -> str:
    zs = [z for z in eintragen.offen(stand.lage, heute, heute + timedelta(days=tage)) if not (nur_offen and z.haken)]
    return eintragen.kopiertext(zs)


# ---- Drucken und Zurücknehmen je Anreise ------------------------------------------------

def _zuteilungen(stand: zp.Planstand, kennung: str) -> list[zp.Zuteilung]:
    bedarf = sorted((b for b in stand.bedarf if b.von.isoformat() == kennung), key=lambda b: (b.anreise_kennung, b.name))
    fest = {b.schluessel: z["zimmer"] for b in bedarf if (z := stand.zugewiesen(b.schluessel))}
    return [zt for zt in zp.vorschlagen(stand.lage, bedarf, fest) if zt.bedarf.schluessel in fest] if bedarf else []


def anreise_druck(stand: zp.Planstand, kennung: str, art: str, titel: str) -> str:
    """art: anreise | schluessel | schilder – nur gespeicherte Zimmer."""
    zts = _zuteilungen(stand, kennung)
    if not zts:
        raise ValueError("Für diese Anreise ist noch kein Zimmer gespeichert.")
    tag = date.fromisoformat(kennung)
    kopf = f"{WT[tag.weekday()]} {tag:%d.%m.%Y}" + (f" · {titel}" if titel else "")
    if art == "anreise":
        return drucklisten.anreiseliste_html(zts, kopf)
    schilder = drucklisten.schilder(zts)
    return drucklisten.zimmerschilder_html(schilder) if art == "schilder" else drucklisten.schluesselliste_html(schilder, kopf)


def anreise_zuruecknehmen(kennung: str) -> str:
    stand = zp.laden()
    personen = {b.schluessel for b in stand.bedarf if b.von.isoformat() == kennung and stand.zugewiesen(b.schluessel)}
    if not personen:
        raise ValueError("Für diese Anreise ist nichts geplant.")
    _schritt(f"Planung Anreise {kennung} zurückgenommen", lambda: zp.planung_zuruecknehmen(personen))
    return f"Planung von {len(personen)} Personen zurückgenommen"


# ---- UWT automatisch --------------------------------------------------------------------

def uwt_zuteilen(heute: date) -> str:
    erg = _schritt("UWT automatisch zugeteilt", lambda: zp.uwt_automatisch_zuteilen(zp.laden(), heute))
    if not erg:
        raise ValueError("Keine kommenden UWT-Teilnehmenden ohne Zimmer.")
    return f"{len(erg)} UWT-Teilnehmende automatisch zugeteilt"


def uwt_zuruecknehmen(heute: date) -> str:
    stand = zp.laden()
    personen = {b.schluessel for b in stand.bedarf if b.gruppe == "UWT" and b.von >= heute and stand.zugewiesen(b.schluessel)}
    if not personen:
        raise ValueError("Keine kommenden UWT-Planungen.")
    _schritt("UWT-Planungen zurückgenommen", lambda: zp.planung_zuruecknehmen(personen))
    return f"{len(personen)} UWT-Planungen zurückgenommen (werden nicht wieder automatisch zugeteilt)"


# ---- Optimieren -------------------------------------------------------------------------

def optimieren_vorschlaege(heute: date):
    """Vorschläge des Hauptprogramms – ohne die, die einen Allergiker von der Allergiker-Etage holen würden (dort
    gelten für Allergiker die Etagen-Regeln nicht, siehe ``hinweise_kern``)."""
    from belegung import optimierung

    from . import hinweise_kern as hk

    stand = zp.laden()
    allergiker = {b.schluessel for b in stand.bedarf if hk.allergiker(b.bemerkung)}
    z = stand.lage.zimmer

    def holt_weg(v) -> bool:
        return any(p in allergiker and hk.auf_allergie_etage(z.get(von)) and not hk.auf_allergie_etage(z.get(nach))
                   for p, von, nach in zip(v.personen, v.von_zimmer, v.nach_zimmer))

    return [v for v in optimierung.vorschlaege(stand, heute) if not holt_weg(v)]


def optimieren_umsetzen(auswahl: list, heute: date) -> str:
    from belegung import optimierung

    stand = zp.laden()
    erg = _schritt("Optimierung", lambda: optimierung.umsetzen(stand, auswahl, heute), [tm.DATEI, um.DATEI])
    geaendert, aufgaben, tausche = erg
    teile = [f"{geaendert} Planungen geändert"] * bool(geaendert) + [f"{tausche} Tausche"] * bool(tausche) + \
        [f"{aufgaben} Aufgaben fürs Belegungssystem"] * bool(aufgaben)
    return ", ".join(teile) or "Nichts geändert"


# ---- Personen ---------------------------------------------------------------------------

@dataclass
class PersonInfo:
    schluessel: str
    name: str
    massnahme: str
    anreise: date
    abreise: date | None
    geschlecht: str
    geschlecht_geschaetzt: bool
    tier: bool
    bemerkung: str
    aus_liste: bool            # Anreiseliste (änderbar) – sonst UWT/Gebäudeplan
    tn_id: str = ""
    gruppe: str = ""
    erinnerung_tage: int | None = None
    erinnerung_kanal: str = ""


def person(stand: zp.Planstand, schluessel: str) -> PersonInfo:
    b = next((x for x in stand.bedarf if x.schluessel == schluessel), None)
    if b is None:
        raise ValueError("Die Person ist nicht mehr in den Listen.")
    personen, _ = anreiseliste.laden()
    p = next((x for x in personen if x.schluessel == schluessel), None)
    return PersonInfo(schluessel, b.name, b.massnahme, b.liste_anreise or b.von, p.abreise if p else b.abreise_liste,
                      b.geschlecht, b.geschlecht_geschaetzt, b.tier, p.bemerkung if p else b.bemerkung, p is not None,
                      p.tn_id if p else "", b.gruppe, p.erinnerung_tage if p else None, p.erinnerung_kanal if p else "")


def angaben_setzen(schluessel: str, geschlecht: str, tier: bool) -> str:
    _schritt("Angaben geändert", lambda: zp.angabe_setzen(schluessel, geschlecht=geschlecht, tier=tier),
             [zp.PERSONEN_ANGABEN])
    return "Angaben gespeichert – die Vorschläge berücksichtigen sie"


def person_aendern(schluessel: str, abreise: date | None, bemerkung: str) -> str:
    personen, _ = anreiseliste.laden()
    p = next((x for x in personen if x.schluessel == schluessel), None)
    if p is None:
        raise ValueError("Nur Personen aus der Anreiseliste lassen sich hier ändern.")
    if abreise is not None and abreise < p.anreise:
        raise ValueError("Die Abreise liegt vor der Anreise.")
    neu = replace(p, abreise=abreise, bemerkung=bemerkung.strip(),
                  abreise_quelle="hand" if abreise != p.abreise else p.abreise_quelle)

    def aktion():
        anreiseliste.person_speichern(neu, p.schluessel)
        zp.person_umbenannt(p.schluessel, neu.schluessel)
    _schritt(f"{p.name} geändert", aktion, [anreiseliste.DATEI])
    return f"{p.name} gespeichert"


def person_entfernen(schluessel: str) -> str:
    personen, _ = anreiseliste.laden()
    p = next((x for x in personen if x.schluessel == schluessel), None)
    if p is None:
        raise ValueError("Nur Personen aus der Anreiseliste lassen sich hier entfernen.")

    def aktion():
        anreiseliste.person_loeschen(schluessel)
        zp.person_geloescht(schluessel)
    _schritt(f"{p.name} entfernt", aktion, [anreiseliste.DATEI])
    return f"{p.name} entfernt"


def massnahmen() -> list[str]:
    personen, _ = anreiseliste.laden()
    return sorted({p.massnahme for p in personen if p.massnahme})


def person_anlegen(name: str, massnahme: str, anreise: date, abreise: date | None, tn_id: str = "",
                   geschlecht: str = "") -> str:
    name = " ".join(name.split())
    if "," not in name or len(name) < 4:
        raise ValueError("Bitte den Namen als „Nachname, Vorname“ eingeben.")
    if not massnahme.strip():
        raise ValueError("Bitte eine Maßnahme angeben (z. B. „GS RVL“).")
    if abreise is not None and abreise < anreise:
        raise ValueError("Die Abreise liegt vor der Anreise.")
    p = anreiseliste.Person(name, massnahme.strip(), anreise, True, tn_id=tn_id.strip(), abreise=abreise,
                            geschlecht=geschlecht, abreise_quelle="hand" if abreise else "")
    _schritt(f"{name} angelegt", lambda: anreiseliste.person_speichern(p), [anreiseliste.DATEI])
    return f"{name} angelegt – Anreise {anreise:%d.%m.%Y}"


# ---------------------------------------------------------------------------------------
# Alle Personen der kommenden Anreisen – mit „neu“ (erstmals in den Listen) und Zimmer
# ---------------------------------------------------------------------------------------

@dataclass
class PZeile:
    schluessel: str
    name: str
    gruppe: str
    zeitraum: str
    kennung: str          # Anreise (für „Zuteilen“)
    anreise: date
    zimmer: str           # Kurzname oder ""
    neu_seit: date | None
    status: str           # ok | handeln | ohne | maengel


def personen_liste(stand: zp.Planstand, heute: date, neu: dict) -> list[PZeile]:
    from .kern import anreisen, kurz, zeilen

    erg = []
    for an in anreisen(stand, heute):
        for z in zeilen(stand, an.kennung, heute):
            erg.append(PZeile(z.schluessel, z.name, z.gruppe, z.zeitraum, an.kennung, an.tag,
                              kurz(z.gespeichert) if z.gespeichert else "", neu.get(z.schluessel), z.status))
    return erg


def anreise_excel(stand: zp.Planstand, kennung: str, titel: str = ""):
    """Zimmerliste einer Anreise als Excel (Zimmer, Etagen, freie Zimmer) – wie „Als Excel-Liste speichern“."""
    from pathlib import Path

    from belegung import speicher, zimmerexport

    zts = _zuteilungen(stand, kennung)
    if not zts:
        raise ValueError("Für diese Anreise ist noch nichts geplant.")
    tag = zts[0].bedarf.von
    ziel = Path(speicher.einstellungen().get("export_ordner") or speicher.pfad("Export"))
    ziel.mkdir(parents=True, exist_ok=True)
    pfad = ziel / f"Zimmerliste_{tag:%Y-%m-%d}.xlsx"
    zimmerexport.exportieren(pfad, f"Zimmerliste Anreise {tag:%d.%m.%Y}" + (f" – {titel}" if titel else ""), zts, stand.lage, tag)
    return f"Excel gespeichert: {pfad.name}", str(pfad)


# ---------------------------------------------------------------------------------------
# Gruppe und Abreise-Erinnerung einer Person (wie im Personen-Dialog des Hauptprogramms)
# ---------------------------------------------------------------------------------------

# Gruppen in den Personenangaben (Details zur Maßnahme gehören in die Bemerkung). RVL bleibt erkannt und zählt als
# vorbereitende Maßnahme – mit seiner Vorliebe für Haus 3.1 –, steht aber nicht eigens in der Auswahl.
GRUPPEN = {"EMR": "EMR", "ASS": "Assessment", "RVT": "Vorbereitende Maßnahme", "Reha": "Hauptmaßnahme", "UWT": "UWT",
           "Gast": "Gast", "Mieter": "Mieter"}


def gruppe_auswahl(gruppe: str) -> str | None:
    """Welcher Eintrag der Auswahl zur Gruppe einer Person passt (RVL → vorbereitende Maßnahme)."""
    return "RVT" if gruppe == "RVL" else gruppe if gruppe in GRUPPEN else None


def gruppe_setzen(schluessel: str, gruppe: str) -> str:
    if gruppe not in zp.GRUPPEN:
        raise ValueError("Unbekannte Gruppe.")
    _schritt("Gruppe geändert", lambda: zp.angabe_setzen(schluessel, gruppe=gruppe), [zp.PERSONEN_ANGABEN])
    return f"Gruppe: {GRUPPEN.get(gruppe, zp.GRUPPE_LABEL.get(gruppe, gruppe))} – Zeitraum und erlaubte Zimmer richten sich danach"


def kanaele() -> dict[str, str]:
    from belegung import erinnerung

    return {k: t for k, t in erinnerung.KANAELE.items() if k not in ("outlook", "mail") or erinnerung.outlook_moeglich()}


def _erinnerung_abgleichen(alt, neu) -> str:
    """Outlook-Termin/Mail bzw. .ics an den neuen Stand anpassen (wie ``erinnerung_abgleichen`` im Hauptprogramm,
    hier ohne Fenster – Outlook wird im Hintergrund-Thread über COM angesprochen)."""
    from belegung import erinnerung

    com = False
    if (alt.erinnerung_kanal in ("outlook", "mail") or neu.erinnerung_kanal in ("outlook", "mail")):
        try:
            import pythoncom

            pythoncom.CoInitialize()
            com = True
        except ImportError:
            pass
    try:
        if alt.erinnerung_id and alt.erinnerung_kanal in ("outlook", "mail"):
            erinnerung.outlook_entfernen(alt.erinnerung_id)
        neu.erinnerung_id = ""
        if neu.erinnerung_tage is None or neu.abreise is None:
            return "Keine Erinnerung"
        titel = erinnerung.betreff(neu.name, neu.abreise)
        text = (f"{neu.name} ({neu.massnahme or neu.gruppe}) reist am {neu.abreise:%d.%m.%Y} ab "
                f"(Anreise {neu.anreise:%d.%m.%Y}, Internat Goslar).\n\nEingetragen im Belegungsdashboard.")
        am = neu.erinnerung_am
        try:
            if neu.erinnerung_kanal == "outlook":
                neu.erinnerung_id = erinnerung.outlook_termin(titel, neu.abreise, neu.erinnerung_tage, text)
                return f"Outlook-Termin am {neu.abreise:%d.%m.%Y}, Erinnerung am {am:%d.%m.%Y}"
            if neu.erinnerung_kanal == "mail":
                empfaenger = speicher.einstellungen().get("erinnerung", {}).get("empfaenger", "")
                neu.erinnerung_id = erinnerung.outlook_mail(titel, am, text, empfaenger)
                return f"Erinnerungs-Mail wird am {am:%d.%m.%Y} um 8 Uhr verschickt"
            if neu.erinnerung_kanal == "ics":
                pfad = erinnerung.ics_speichern(titel, neu.abreise, neu.erinnerung_tage, text, f"abreise_{neu.schluessel}")
                erinnerung.ics_oeffnen(pfad)
                return f"Kalenderdatei erstellt: {pfad.name}"
        except Exception as exc:              # noqa: BLE001 – Outlook fehlt/blockiert: dann im Dashboard
            neu.erinnerung_kanal, neu.erinnerung_id = "app", ""
            return f"Outlook nicht erreichbar ({exc}) – die Erinnerung erscheint stattdessen unter Termine"
        return f"Erinnerung am {am:%d.%m.%Y} unter Termine"
    finally:
        if com:
            import pythoncom

            pythoncom.CoUninitialize()


def erinnerung_setzen(schluessel: str, an: bool, tage: int, kanal: str) -> str:
    personen, _ = anreiseliste.laden()
    p = next((x for x in personen if x.schluessel == schluessel), None)
    if p is None:
        raise ValueError("Nur Personen aus der Anreiseliste haben eine Abreise-Erinnerung.")
    if an and p.abreise is None:
        raise ValueError("Erst eine Abreise eintragen – dann lässt sich daran erinnern.")
    neu = replace(p, erinnerung_tage=int(tage) if an else None, erinnerung_kanal=kanal if an else "")
    if (neu.erinnerung_tage, neu.erinnerung_kanal) == (p.erinnerung_tage, p.erinnerung_kanal):
        raise ValueError("Die Erinnerung ist schon so eingestellt – nichts geändert.")
    neu.erledigt = False
    meldung = _erinnerung_abgleichen(p, neu)
    _schritt("Abreise-Erinnerung", lambda: anreiseliste.person_speichern(neu, p.schluessel), [anreiseliste.DATEI])
    return meldung

