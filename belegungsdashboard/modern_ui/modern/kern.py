"""Brücke zwischen der neuen Oberfläche und der bestehenden Logik in ``belegung`` – ohne NiceGUI, damit testbar.

Gelesen und geschrieben wird ausschließlich über die Funktionen des Hauptprogramms (``zimmerplan``, ``vorgaenge``,
``reinigungsliste``, ``termine``, ``aenderungen``). Jede Änderung ist ein Schritt mit Schnappschuss, den
``rueckgaengig`` zurücknimmt – wie Strg+Z im Hauptprogramm.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Callable

from belegung import aenderungen, speicher
from belegung import reinigungsliste as rl
from belegung import termine as tm
from belegung import zimmerplan as zp

WT = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]
FILTER = {"alle": "Alle", "handeln": "Handlungsbedarf", "maengel": "Mängel", "ohne": "Ohne Zimmer"}
ZUSTAND = "modern_ui.json"           # eigene Ablage der neuen Oberfläche (z. B. „Später“), getrennt von den alten Dateien


def kurz(zid: str) -> str:
    return zid.removeprefix("GS-")


# ---------------------------------------------------------------------------------------
# Anreisen und Tabellenzeilen
# ---------------------------------------------------------------------------------------

@dataclass
class Anreise:
    kennung: str          # ISO-Datum
    tag: date
    titel: str
    personen: int
    zugeteilt: int

    @property
    def text(self) -> str:
        stand = "zugeteilt" if self.zugeteilt == self.personen else f"{self.zugeteilt}/{self.personen} zugeteilt"
        return f"{WT[self.tag.weekday()]} {self.tag:%d.%m.%Y} · {self.titel} · {stand}"


def anreisen(stand: zp.Planstand, heute: date, vergangene: bool = False) -> list[Anreise]:
    ab = heute - timedelta(days=365 if vergangene else 3)
    return [Anreise(k, tag, titel, len(bs), sum(1 for b in bs if stand.zugewiesen(b.schluessel)))
            for k, tag, titel, bs in stand.anreisen(ab)]


def erste_offene(liste: list[Anreise]) -> str | None:
    """Wie im Hauptprogramm: die nächste Anreise, die noch nicht vollständig zugeteilt ist."""
    offen = [a.kennung for a in liste if a.zugeteilt < a.personen]
    return (offen or [a.kennung for a in liste] or [None])[0]


@dataclass
class Option:
    zimmer: str           # Zimmer-ID
    text: str
    art: str = "frei"     # frei | vorschlag | aktuell | ausnahme


@dataclass
class Zeile:
    schluessel: str
    name: str
    zweite: str
    gruppe: str
    von: date
    bis: date
    gespeichert: str | None           # Zimmer-ID, die schon gespeichert ist
    status: str                       # ok | handeln | maengel | ohne
    stufe: str                        # ok | warn | krit  (Ampelpunkt)
    grund: str = ""
    vorschlag: str | None = None      # grüne Ausweich-/Vorschlags-Option (Zimmer-ID)
    optionen: list[Option] = field(default_factory=list)
    maengel: str = ""

    @property
    def zeitraum(self) -> str:
        return f"{self.von:%d.%m.}–{self.bis:%d.%m.%y}"

    def filter(self, f: str, neu: dict | None = None) -> bool:
        if f == "alle":
            return True
        if f == "neu":
            return self.schluessel in (neu or {})
        if f == "maengel":
            return bool(self.maengel)
        return self.status == f


def _maengel_text() -> dict[str, str]:
    from belegung import maengel as mg

    try:
        return {zid: ", ".join(sorted({mg.NAMEN.get(m.art, m.art) for m in ms})) for zid, ms in mg.offen_je_zimmer().items()}
    except Exception:                      # noqa: BLE001 – ohne Mängelliste geht die Tabelle trotzdem
        return {}


def _bezeichnung(z: zp.Zimmer) -> str:
    return z.kurz + (" · DZ" if z.betten > 1 else "")


def zeilen(stand: zp.Planstand, kennung: str | None, heute: date | None = None) -> list[Zeile]:
    """Alle Personen einer Anreise mit gespeichertem Zimmer, Status und Vorschlag (Logik des Hauptprogramms)."""
    if not kennung:
        return []
    heute = heute or date.today()
    bedarf = sorted((b for b in stand.bedarf if b.von.isoformat() == kennung), key=lambda b: (b.anreise_kennung, b.name))
    if not bedarf:
        return []
    fest = {b.schluessel: z["zimmer"] for b in bedarf if (z := stand.zugewiesen(b.schluessel))}
    konflikte = {k.person: k.grund for k in zp.konflikte(stand.lage, heute)}
    maengel = _maengel_text()
    erg = []
    for zt in zp.vorschlagen(stand.lage, bedarf, fest):
        b = zt.bedarf
        gespeichert = fest.get(b.schluessel)
        neu = zt.zimmer.id if zt.zimmer else None
        vorschlag, grund = None, ""
        hart = (konflikte.get(b.schluessel) or (f"unbewohnbar: {stand.lage.unbewohnbar[gespeichert]}"
                                                 if gespeichert in stand.lage.unbewohnbar else "")) if gespeichert else ""
        if gespeichert and (hart or neu != gespeichert):
            status, stufe = "handeln", "krit"
            grund = hart or "Zimmer passt nicht mehr"
            vorschlag = neu if neu and neu != gespeichert else next(
                (z.id for z in zt.alternativen if z.id != gespeichert and z.id not in stand.lage.unbewohnbar), None)
        elif not gespeichert:
            status, stufe = "ohne", "krit"
            vorschlag = neu
            grund = "noch kein Zimmer" + (f" – {zt.grund}" if neu is None and zt.grund else "")
        elif zt.warnungen:
            status, stufe, grund = "handeln", "warn", "; ".join(zt.warnungen)
        else:
            status, stufe = "ok", "ok"
        zimmer_jetzt = gespeichert or vorschlag
        m = maengel.get(zimmer_jetzt or "", "")
        if status == "ok" and m:
            status, stufe = "maengel", "warn"
        opts: list[Option] = []
        gesehen: set[str] = set()

        def dazu(zid: str, art: str, text: str | None = None) -> None:
            if zid in gesehen or zid not in stand.lage.zimmer:
                return
            gesehen.add(zid)
            z = stand.lage.zimmer[zid]
            zusatz = {"vorschlag": " · passt", "aktuell": (" · " + grund) if status == "handeln" and stufe == "krit" else ""}
            opts.append(Option(zid, text or (_bezeichnung(z) + zusatz.get(art, "")), art))

        if vorschlag:
            dazu(vorschlag, "vorschlag")
        if gespeichert:
            dazu(gespeichert, "aktuell")
        for z in zt.alternativen:
            dazu(z.id, "frei")
        for z in zt.ausnahmen:
            dazu(z.id, "ausnahme", f"{_bezeichnung(z)} · {zp.ausnahme_grund(stand.lage, z, b)}")
        zweite = b.massnahme.removeprefix("UWT ") if b.gruppe == "UWT" else b.massnahme
        erg.append(Zeile(b.schluessel, b.name, zweite, b.gruppe, b.von, b.bis, gespeichert, status, stufe, grund,
                         vorschlag, opts, m))
    return erg


def zaehlen(zs: list[Zeile]) -> dict[str, int]:
    return {f: sum(1 for z in zs if z.filter(f)) for f in FILTER}


def kennzahlen(stand: zp.Planstand, tag: date) -> dict[str, int]:
    """Internatszimmer (ohne Gästezimmer) am Tag: frei | belegt | gesperrt."""
    erg = {"frei": 0, "belegt": 0, "gesperrt": 0}
    for z in stand.zimmer:
        if not z.aktiv or z.gaeste:
            continue
        s = stand.lage.status_am(z.id, tag)[0]
        erg["frei" if s in ("frei", "teilweise") else ("gesperrt" if s == "gesperrt" else "belegt")] += 1
    return erg


# ---------------------------------------------------------------------------------------
# Ändern – jeder Aufruf ist ein Schritt, den „Rückgängig“ zurücknimmt
# ---------------------------------------------------------------------------------------

def _schritt(titel: str, aktion: Callable[[], object], dateien: list[str] | None = None) -> object:
    """Alles oder nichts: bei einem Fehler wird der Stand davor zurückgeschrieben und der Fehler weitergereicht."""
    namen = aenderungen._dateien() + [n for n in (dateien or []) if n not in aenderungen._dateien()]
    vorher = aenderungen.schnappschuss(namen)
    try:
        erg = aktion()
    except Exception:
        for name, inhalt in vorher.items():
            if aenderungen.schnappschuss([name])[name] != inhalt:
                aenderungen._roh_schreiben(name, inhalt)
        raise
    aenderungen.merken(titel, vorher)
    return erg


def _zuteilung(stand: zp.Planstand, schluessel: str, zimmer: str) -> zp.Zuteilung:
    b = next((x for x in stand.bedarf if x.schluessel == schluessel), None)
    if b is None:
        raise ValueError("Die Person ist nicht mehr in den Listen.")
    zeile = next((z for z in zeilen(stand, b.von.isoformat()) if z.schluessel == schluessel), None)
    if zeile is None or zimmer not in {o.zimmer for o in zeile.optionen}:
        raise ValueError(f"Zimmer {kurz(zimmer)} ist für {b.name} nicht (mehr) frei.")
    return zp.Zuteilung(b, stand.lage.zimmer[zimmer])


def zuweisen(schluessel: str, zimmer: str) -> str:
    """Ein Zimmer für eine Person speichern – nur Zimmer, die die Auswahl auch anbietet (frei bzw. Ausnahme)."""
    stand = zp.laden()
    zt = _zuteilung(stand, schluessel, zimmer)
    _schritt(f"{zt.bedarf.name} → {kurz(zimmer)}", lambda: zp.zuweisungen_speichern([zt], "Neue Oberfläche"))
    return f"{zt.bedarf.name} → {kurz(zimmer)}"


def vorschlaege_uebernehmen(kennung: str, nur: str = "ohne") -> str:
    """Alle grünen Vorschläge einer Anreise speichern. ``nur``: ohne | handeln | alle (ohne + Konflikte)."""
    stand = zp.laden()
    zs = [z for z in zeilen(stand, kennung) if z.vorschlag and (nur == "alle" or z.status == nur)]
    if not zs:
        raise ValueError("Keine Vorschläge offen.")
    zts = [_zuteilung(stand, z.schluessel, z.vorschlag) for z in zs]
    tag = date.fromisoformat(kennung)
    _schritt(f"Anreise {tag:%d.%m.}: {len(zts)} Vorschläge", lambda: zp.zuweisungen_speichern(zts, "Neue Oberfläche"))
    return f"Anreise {tag:%d.%m.}: {len(zts)} Zimmer zugewiesen"


def problemfaelle(stand: zp.Planstand, heute: date) -> dict[str, str]:
    """Person → Grund: Planungen mit Konflikt (belegt/gesperrt) oder in einem inzwischen unbewohnbaren Zimmer."""
    erg = {k.person: k.grund for k in zp.konflikte(stand.lage, heute)}
    for z in stand.zuweisungen:
        if z["zimmer"] in stand.lage.unbewohnbar and z.get("bis", "") >= heute.isoformat() and z["person"] not in erg:
            erg[z["person"]] = f"unbewohnbar: {stand.lage.unbewohnbar[z['zimmer']]}"
    return erg


def konflikte_loesen(heute: date | None = None) -> str:
    """Jede Planung mit Konflikt bekommt das vorgeschlagene Ausweichzimmer (Personen ohne Vorschlag bleiben)."""
    heute = heute or date.today()
    stand = zp.laden()
    kon = set(problemfaelle(stand, heute))
    tage = {b.von.isoformat() for b in stand.bedarf if b.schluessel in kon}
    zts = []
    for k in sorted(tage):
        for z in zeilen(stand, k, heute):
            if z.schluessel in kon and z.vorschlag:
                zts.append(_zuteilung(stand, z.schluessel, z.vorschlag))
    if not zts:
        raise ValueError("Für die Konflikte gibt es gerade kein freies Ausweichzimmer – bitte im Hauptprogramm lösen.")
    _schritt(f"{len(zts)} Konflikte gelöst", lambda: zp.zuweisungen_speichern(zts, "Neue Oberfläche"))
    rest = len(kon) - len(zts)
    return f"{len(zts)} Ausweichzimmer zugewiesen" + (f", {rest} ohne freies Zimmer" if rest else "")


def reinigung_erledigt(dringend: bool, heute: date | None = None) -> str:
    from belegung import cockpit

    heute = heute or date.today()
    kon, offen = cockpit.reinigung_heute(zp.laden(), heute)
    rs = kon if dringend else offen
    if not rs:
        raise ValueError("Keine offenen Reinigungen.")
    _schritt(f"{len(rs)} Reinigungen erledigt", lambda: [rl.erledigt_setzen(r) for r in rs], [rl.DATEI])
    return f"{len(rs)} Zimmer als gereinigt markiert"


def termin_erledigt(tid: str) -> str:
    from belegung import anreiseliste

    t = next((x for x in tm.alle() if x.id == tid), None)
    if t is None:
        raise ValueError("Den Termin gibt es nicht mehr.")
    _schritt(f"Erledigt: {t.titel}", lambda: tm.erledigt_setzen(t), [tm.DATEI, anreiseliste.DATEI])
    return f"Erledigt: {t.titel}"


def rueckgaengig() -> tuple[bool, str]:
    return aenderungen.rueckgaengig("Neue Oberfläche")


# ---------------------------------------------------------------------------------------
# Aufgaben-Center: Karten mit 1-Klick-Lösung
# ---------------------------------------------------------------------------------------

@dataclass
class Aktion:
    schluessel: str       # z. B. „vorschlaege:2026-10-26“, „konflikte“, „reinigung:dringend“, „termin:<id>“
    text: str
    zeigen: str = ""      # Anreise, die die Tabelle danach zeigen soll


@dataclass
class Karte:
    id: str
    stufe: str            # dringend | bald | info
    titel: str
    detail: str
    aktion: Aktion | None = None
    zweite: Aktion | None = None
    hinweis: str = ""     # wenn es hier keine 1-Klick-Lösung gibt


HAUPTPROGRAMM = "Im Hauptprogramm erledigen"
# Vorgang-Ziel → Seite der neuen Oberfläche („Seite/Ansicht“), für den zweiten Knopf einer Karte
ZIELE = {"konflikte": "anreisen", "eintragen": "anreisen/eintragen", "reinigung": "reinigung", "abreisen": "anreisen/abreisen",
         "facility": "reinigung/facility", "maengel": "zimmer/liste", "engpaesse": "auswertung/zimmer", "gebaeudeplan": "daten",
         "termin": "termine", "posteingang": "assistenz", "mail": "assistenz", "mieterende": "mieter", "umzug": "zimmer"}


def _karte(v, stand: zp.Planstand | None) -> Karte:
    k = Karte(v.id, v.stufe, v.titel, v.detail)
    art = v.id.split(":")[0]
    if art == "anreise" and stand is not None:
        kennung = v.id.split(":", 1)[1]
        zs = [z for z in zeilen(stand, kennung) if z.status == "ohne"]
        mit = sum(1 for z in zs if z.vorschlag)
        if mit:
            k.aktion = Aktion(f"vorschlaege:{kennung}", f"{mit} Vorschläge übernehmen", kennung)
        k.zweite = Aktion(f"zeigen:{kennung}", "Anzeigen", kennung)
    elif art == "konflikte":
        k.aktion = Aktion("konflikte", "Ausweichzimmer zuweisen")
    elif v.id == "reinigung_dringend":
        k.aktion = Aktion("reinigung:dringend", "Alle als gereinigt markieren")
    elif v.id == "reinigung":
        k.aktion = Aktion("reinigung:heute", "Alle als gereinigt markieren")
    elif v.erledigen:
        k.aktion = Aktion(f"termin:{v.erledigen}", "Erledigt")
    if k.zweite is None:
        ziel = ZIELE.get(v.ziel.split(":")[0])
        if ziel:
            k.zweite = Aktion(f"zeigen:{v.ziel}", v.aktion.rstrip(" …") if k.aktion is None else "Ansehen", ziel)
    if k.aktion is None and k.zweite is None:
        k.hinweis = f"{HAUPTPROGRAMM}: {v.aktion.rstrip(' …')}"
    return k


def karten(stand: zp.Planstand | None, heute: date | None = None, vorgaenge_: list | None = None) -> list[Karte]:
    """Offene Vorgänge (wie „Heute“ im Hauptprogramm) als Karten – ohne die heute auf „Später“ gesetzten."""
    from belegung import vorgaenge

    heute = heute or date.today()
    if vorgaenge_ is None:
        try:
            termine = tm.alle()
        except Exception:                  # noqa: BLE001 – Termine sind optional
            termine = []
        vorgaenge_ = vorgaenge.sammeln(stand, heute, termine)
    weg = spaeter(heute)
    erg = [_karte(v, stand) for v in vorgaenge_ if v.id not in weg]
    if stand is not None and not any(k.id == "konflikte" for k in erg):
        # Planungen in inzwischen unbewohnbaren Zimmern meldet „Heute“ nicht – hier schon, mit 1-Klick-Lösung
        unb = {p: g for p, g in problemfaelle(stand, heute).items() if g.startswith("unbewohnbar")}
        if unb and "unbewohnbar" not in weg:
            namen = {z["person"]: z.get("name", "") for z in stand.zuweisungen}
            erg.insert(0, Karte("unbewohnbar", "dringend",
                                f"{len(unb)} Planung{'en' if len(unb) > 1 else ''} in unbewohnbarem Zimmer",
                                "; ".join(f"{namen.get(p, '')} ({g.split(': ', 1)[1]})" for p, g in list(unb.items())[:2])
                                + (" …" if len(unb) > 2 else ""), Aktion("konflikte", "Ausweichzimmer zuweisen")))
    return erg


def ausfuehren(schluessel: str, heute: date | None = None) -> str:
    """Hauptknopf einer Karte. Gibt die Meldung für den Toast zurück; ValueError = fachlich nicht möglich."""
    art, _, wert = schluessel.partition(":")
    if art == "vorschlaege":
        return vorschlaege_uebernehmen(wert)
    if art == "konflikte":
        return konflikte_loesen(heute)
    if art == "reinigung":
        return reinigung_erledigt(wert == "dringend", heute)
    if art == "termin":
        return termin_erledigt(wert)
    raise ValueError(f"Unbekannte Aktion: {schluessel}")


def spaeter(heute: date | None = None) -> set[str]:
    heute = heute or date.today()
    roh = speicher.lesen(ZUSTAND, {}).get("spaeter", {})
    return {k for k, bis in roh.items() if bis > heute.isoformat()}


def spaeter_setzen(kid: str, an: bool = True, heute: date | None = None) -> None:
    """„Später“: Karte bis morgen ausblenden (an=False holt sie zurück)."""
    heute = heute or date.today()
    roh = speicher.lesen(ZUSTAND, {})
    s = {k: v for k, v in roh.get("spaeter", {}).items() if v > heute.isoformat()}
    if an:
        s[kid] = (heute + timedelta(days=1)).isoformat()
    else:
        s.pop(kid, None)
    roh["spaeter"] = s
    speicher.schreiben(ZUSTAND, roh)


def automatisch_oeffnen(ks: list[Karte], heute: date | None = None) -> bool:
    """Das Center öffnet sich von selbst, wenn Dringendes da ist, das heute noch nicht gezeigt wurde."""
    heute = heute or date.today()
    roh = speicher.lesen(ZUSTAND, {})
    gezeigt = set(roh.get("gezeigt", {}).get(heute.isoformat(), []))
    neu = {k.id for k in ks if k.stufe == "dringend"} - gezeigt
    if neu:
        roh["gezeigt"] = {heute.isoformat(): sorted(gezeigt | neu)}
        speicher.schreiben(ZUSTAND, roh)
    return bool(neu)


# ---------------------------------------------------------------------------------------
# Frei nach Planung
# ---------------------------------------------------------------------------------------

@dataclass
class NachPlanung:
    wochen: list          # (Woche-Text, frei jetzt, frei nach Planung, EMR, Doppel, Stufe gesamt, Stufen je Art)
    tiefst: tuple | None  # (Woche-Text, frei nach Planung, Stufe)
    offen: int
    ohne_platz: int


def nach_planung(stand: zp.Planstand, heute: date | None = None, wochen: int = 12) -> NachPlanung:
    """Freie Zimmer je Woche, wenn alle bekannten Anreisen (auch die ohne Zimmer) nach den Regeln ein Zimmer hätten."""
    from belegung import eintragen

    heute = heute or date.today()
    np_ = eintragen.nach_planung(stand, heute, wochen)
    zeilen = [(n.text, j.gesamt, n.gesamt, n.emr, n.doppel, n.gesamtstufe,
               {a: n.stufe(a) for a in ("gesamt", "emr", "doppel")}) for j, n in np_.wochen]
    t = np_.tiefst
    return NachPlanung(zeilen, (t.text, t.gesamt, t.stufe("gesamt")) if t else None, np_.offen, np_.ohne_platz)


SYMBOL = {"anreise": "flight_land", "konflikte": "warning", "unbewohnbar": "report", "eintragen": "edit_note",
          "reinigung": "cleaning_services", "abreisen": "flight_takeoff", "facility": "electrical_services",
          "maengel": "build", "engpass": "trending_down", "termin": "event", "mail": "mail", "posteingang": "mail",
          "mieterende": "key", "gebaeudeplan": "description", "umzug": "swap_horiz", "n": "campaign"}


def symbol(kid: str) -> str:
    """Kleines Symbol je Aufgabentyp (aus der Kennung, z. B. „anreise:2026-10-26“, „reinigung_dringend“)."""
    art = kid.split(":")[0].split("_")[0]
    return SYMBOL.get(art, "task_alt")


def willkommen_zeigen() -> bool:
    return not speicher.lesen(ZUSTAND, {}).get("willkommen_gesehen")


def willkommen_weg() -> None:
    roh = speicher.lesen(ZUSTAND, {})
    roh["willkommen_gesehen"] = True
    speicher.schreiben(ZUSTAND, roh)


# ---------------------------------------------------------------------------------------
# Neue Personen: Das Hauptprogramm speichert kein Anlagedatum – die neue Oberfläche merkt sich daher selbst, wann
# eine Person zum ersten Mal in den Listen stand (eigene Datei, die alten Dateien bleiben unberührt).
# ---------------------------------------------------------------------------------------

NEU_DATEI = "modern_ui_neu.json"
NEU_TAGE = 7


def neue_personen(stand: zp.Planstand, heute: date | None = None, tage: int = NEU_TAGE) -> dict[str, date]:
    """Schlüssel → Tag, an dem die Person zuerst auftauchte – nur die der letzten ``tage`` Tage.

    Beim allerersten Aufruf gilt für Personen aus einer Anreiseliste deren Importdatum (sonst „schon länger da“),
    danach zählt der Tag, an dem die neue Oberfläche die Person zum ersten Mal sieht."""
    from belegung import anreiseliste

    heute = heute or date.today()
    roh = speicher.lesen(NEU_DATEI, {})
    gesehen: dict[str, str] = roh.get("gesehen", {})
    schluessel = {b.schluessel for b in stand.bedarf}
    neu = schluessel - set(gesehen)
    if neu:
        if not gesehen:                      # erster Start: Importdatum der Liste, sonst „alt“
            personen, listen = anreiseliste.laden()
            liste_von = {p.schluessel: p.liste for p in personen}
            for k in neu:
                am = (listen.get(liste_von.get(k, ""), {}) or {}).get("importiert_am", "")
                gesehen[k] = am[:10] if am else "2000-01-01"
        else:
            for k in neu:
                gesehen[k] = heute.isoformat()
        speicher.schreiben(NEU_DATEI, {"gesehen": gesehen})
    grenze = heute - timedelta(days=tage - 1)
    erg = {}
    for k in schluessel:
        try:
            tag = date.fromisoformat(gesehen.get(k, "2000-01-01"))
        except ValueError:
            continue
        if tag >= grenze:
            erg[k] = tag
    return erg

