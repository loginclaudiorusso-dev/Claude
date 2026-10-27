"""Daten für Zeitstrahl, Reinigung, Mieter, Auswertung und Verwalten – ohne NiceGUI, über die Funktionen des
Hauptprogramms. Änderungen laufen wie in ``kern`` als Schritt mit Rückgängig."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta

from belegung import speicher
from belegung import reinigungsliste as rl
from belegung import zimmerplan as zp

from .kern import WT, _schritt, kurz, problemfaelle


def tag_kurz(d: date) -> str:
    return f"{WT[d.weekday()]} {d:%d.%m.}"


# ---------------------------------------------------------------------------------------
# Zeitstrahl
# ---------------------------------------------------------------------------------------

@dataclass
class Balken:
    art: str              # belegt | geplant | gesperrt | konflikt
    text: str
    titel: str            # Tooltip
    start: int            # Tag-Index ab Beginn (0 …)
    tage: int
    offen_links: bool = False
    offen_rechts: bool = False
    person: str = ""      # gesetzt = per Ziehen in ein anderes Zimmer verschiebbar (geplant, noch nicht eingezogen)


@dataclass
class ZsZeile:
    zimmer: str
    kurz: str
    lage: str
    betten: int
    balken: list[Balken] = field(default_factory=list)
    hinweis: str = ""     # Mangel / unbewohnbar


def haeuser(stand: zp.Planstand) -> list[str]:
    return sorted({z.haus for z in stand.zimmer if z.aktiv}, key=zp._haus_sort)


def zeitstrahl(stand: zp.Planstand, haus: str, start: date, tage: int = 28, heute: date | None = None) -> list[ZsZeile]:
    heute = heute or date.today()
    ende = start + timedelta(days=tage - 1)
    probleme = problemfaelle(stand, heute)
    from belegung import maengel as mg

    try:
        maengel = mg.offen_je_zimmer()
    except Exception:                      # noqa: BLE001
        maengel = {}
    erg = []
    zimmer = sorted((z for z in stand.zimmer if z.aktiv and z.haus == haus),
                    key=lambda z: (zp._etage_sort(z.etage), z.nummer, z.nr))
    for z in zimmer:
        hinweis = ""
        if z.id in stand.lage.unbewohnbar:
            hinweis = f"unbewohnbar: {stand.lage.unbewohnbar[z.id]}"
        elif z.id in maengel:
            hinweis = "Mängel: " + ", ".join(sorted({mg.NAMEN.get(m.art, m.art) for m in maengel[z.id]}))
        zeile = ZsZeile(z.id, z.kurz, zp.flur_text(z), z.betten, hinweis=hinweis)
        for b in sorted(stand.lage.belegungen.get(z.id, []), key=lambda b: b.von):
            if b.art == "freigabe" or b.bis < start or b.von > ende:
                continue
            art = "konflikt" if b.person in probleme else b.art
            if b.art == "gesperrt":
                text = b.grund or "gesperrt"
            else:
                text = b.name.split(",")[0] if b.name and b.name != zp.PIVOT_NAME else (b.massnahme or "belegt")
            titel = (f"{b.name or text} · {b.massnahme}" if b.massnahme else (b.name or text)) + \
                f"\n{b.von:%d.%m.%Y} – {b.bis:%d.%m.%Y}" + \
                {"geplant": " · im Programm geplant", "konflikt": f" · {probleme.get(b.person, '')}",
                 "gesperrt": " · gesperrt"}.get(art, "") + (" · Umzug" if b.umzug else "")
            a, e = max(b.von, start), min(b.bis, ende)
            ziehbar = b.art == "geplant" and b.person and not b.umzug and stand.zugewiesen(b.person) is not None
            if ziehbar:
                titel += "\nZiehen: in ein anderes Zimmer verschieben"
            zeile.balken.append(Balken(art, text, titel, (a - start).days, (e - a).days + 1, b.von < start, b.bis > ende,
                                       b.person if ziehbar else ""))
        erg.append(zeile)
    return erg


# ---------------------------------------------------------------------------------------
# Reinigung
# ---------------------------------------------------------------------------------------

ZEITRAUM = {"heute": "Heute", "woche": "Diese Woche", "naechste": "Nächste Woche"}


def zeitraum(wahl: str, heute: date) -> tuple[date, date]:
    if wahl == "heute":
        return heute, heute
    von, bis = rl.woche(heute)
    if wahl == "naechste":
        von, bis = von + timedelta(days=7), bis + timedelta(days=7)
    return von, bis


@dataclass
class RZeile:
    schluessel: str
    zimmer: str
    lage: str
    art: str
    auszug: str
    danach: str
    frist: str
    prio: int
    prio_text: str
    erledigt: bool
    notiz: str = ""
    details: str = ""
    manuell_id: str = ""

    @property
    def stufe(self) -> str:
        return "ok" if self.erledigt else ("krit" if self.prio <= 1 else ("warn" if self.prio <= 3 else "neutral"))


def _reinigungen(stand: zp.Planstand, von: date, bis: date) -> list[zp.Reinigung]:
    zpv = stand.zimmer_pivot
    return zp.reinigungen(stand.lage, von, bis, zpv.zeitraum[1] if zpv else None, zpv.zeitraum[0] if zpv else None,
                          bool(speicher.einstellungen().get("reinigung_anreisetag", False)))


def reinigung(stand: zp.Planstand, von: date, bis: date, heute: date | None = None) -> list[RZeile]:
    heute = heute or date.today()
    fertig = rl.erledigt()
    erg = []
    for r in rl.sortiert(_reinigungen(stand, von, bis), heute, fertig):
        p = rl.prioritaet(r, heute, fertig)
        erg.append(RZeile(rl.schluessel(r), r.zimmer.kurz, zp.flur_text(r.zimmer), r.art, rl.auszug_datum(r),
                          rl.einzug_text(r, True), rl.frist_text(r), p, rl.prio_text(r, heute, fertig), p == 9,
                          rl.notiz(r), rl.details(r, True), r.manuell_id))
    return erg


def reinigung_zaehlen(zs: list[RZeile]) -> dict[str, int]:
    return {"offen": sum(1 for z in zs if not z.erledigt), "eilig": sum(1 for z in zs if not z.erledigt and z.prio <= 1),
            "erledigt": sum(1 for z in zs if z.erledigt)}


def reinigung_setzen(schluessel: list[str], an: bool, von: date, bis: date) -> str:
    stand = zp.laden()
    rs = [r for r in _reinigungen(stand, von, bis) if rl.schluessel(r) in set(schluessel)]
    if not rs:
        raise ValueError("Diese Reinigung gibt es nicht mehr.")
    titel = f"{len(rs)} Reinigung{'en' if len(rs) > 1 else ''} {'erledigt' if an else 'wieder offen'}"
    _schritt(titel, lambda: [rl.erledigt_setzen(r, an) for r in rs], [rl.DATEI])
    if len(rs) == 1:
        return f"Zimmer {rs[0].zimmer.kurz}: {'gereinigt' if an else 'wieder offen'}"
    return titel


def reinigung_hinzu(zimmer_kurz: str, tag: date, grund: str) -> str:
    stand = zp.laden()
    z = next((z for z in stand.zimmer if z.kurz == zimmer_kurz.strip() or z.id == zimmer_kurz.strip()), None)
    if z is None:
        raise ValueError(f"Zimmer „{zimmer_kurz}“ gibt es nicht.")
    _schritt(f"Reinigung {z.kurz} am {tag:%d.%m.}", lambda: zp.reinigung_hinzufuegen(z.id, tag, grund),
             [zp.REINIGUNG_MANUELL])
    return f"Zimmer {z.kurz} für {tag_kurz(tag)} auf die Reinigungsliste gesetzt"


def reinigung_entfernen(manuell_id: str) -> str:
    _schritt("Reinigung entfernt", lambda: zp.reinigung_entfernen(manuell_id), [zp.REINIGUNG_MANUELL])
    return "Von Hand hinzugefügte Reinigung entfernt"


def zimmer_kurzliste(stand: zp.Planstand) -> list[str]:
    return [z.kurz for z in sorted((z for z in stand.zimmer if z.aktiv),
                                   key=lambda z: (zp._haus_sort(z.haus), zp._etage_sort(z.etage), z.nummer))]


def reinigung_druck(von: date, bis: date, heute: date | None = None) -> str:
    """Druckfertiges HTML der Reinigungsliste (gleiche Liste wie im Hauptprogramm)."""
    heute = heute or date.today()
    stand = zp.laden()
    rs = rl.sortiert(_reinigungen(stand, von, bis), heute, rl.erledigt())
    return rl.html_text(rs, von, bis, False, f"Stand {heute:%d.%m.%Y}", heute=heute, fertig=rl.erledigt())


# ---------------------------------------------------------------------------------------
# Mieter
# ---------------------------------------------------------------------------------------

@dataclass
class MZeile:
    nr: str
    name: str
    zimmer: str
    von: date
    bis: date
    status: str
    stufe: str            # ok | warn | neutral | akzent
    mail_offen: bool
    email: str = ""
    mail_am: str = ""


STUFE_MIETER = {"ok": "ok", "knapp": "warn", "neutral": "neutral", "akzent": "akzent"}


def mieter(heute: date | None = None) -> tuple[list[MZeile], list[tuple[str, str, str]]]:
    """(Verträge im Programm, weitere Mieter laut Gebäudeplan ohne Vertrag hier: (Name, Zimmer, Zeitraum))."""
    from belegung import mieter as mt

    heute = heute or date.today()
    erg = []
    for mv in sorted(mt.laden(), key=lambda m: (m.bis < heute, m.bis)):
        text, stufe = mt.status(mv, heute)
        erg.append(MZeile(mv.nr, mv.name, mv.zimmer_kurz, mv.von, mv.bis, text, STUFE_MIETER.get(stufe, "neutral"),
                          mt.mail_offen(mv, heute), mv.email, mv.mail_ende))
    try:
        weitere = [(b.name, kurz(b.zimmer), f"{b.von:%d.%m.%Y} – {b.bis:%d.%m.%Y}")
                   for b in mt.weitere_mieter(zp.laden(), heute)]
    except Exception:                      # noqa: BLE001
        weitere = []
    return erg, weitere


def mieter_mail(nr: str, art: str = "anfrage", heute: date | None = None) -> tuple[str, str, str]:
    """(Empfänger, Betreff, Text) der Mail zum Vertragsende."""
    from belegung import mieter as mt

    mv = mt.nach_nummer(nr)
    if mv is None:
        raise ValueError("Den Vertrag gibt es nicht mehr.")
    betreff, text = mt.ende_mail(mv, art, heute)
    return mv.email, betreff, text


def mieter_mail_vermerken(nr: str, email: str) -> str:
    from belegung import mieter as mt

    _schritt(f"Mail zum Vertragsende {nr}", lambda: mt.mail_vermerken(nr, email), [mt.DATEI])
    return "Mail vorbereitet und am Vertrag vermerkt"


def mail_oeffnen(empfaenger: str, betreff: str, text: str) -> str | None:
    """Outlook-Entwurf öffnen (Windows mit Outlook). Sonst den mailto-Link zurückgeben – die Oberfläche öffnet ihn."""
    from belegung import erinnerung

    if erinnerung.outlook_moeglich():
        try:
            erinnerung.outlook_entwurf(empfaenger, betreff, text)
            return None
        except Exception:                  # noqa: BLE001 – z. B. „neues Outlook“ ohne COM: Standard-Mailprogramm
            pass
    return erinnerung.mailto(empfaenger, betreff, text)


# ---------------------------------------------------------------------------------------
# Auswertung
# ---------------------------------------------------------------------------------------

@dataclass
class WZeile:
    kw: str
    frei_jetzt: int
    frei_nach: int
    emr: int
    doppel: int
    stufe: str            # ok | knapp | kritisch
    stufen: dict = field(default_factory=dict)   # je Art (gesamt, emr, doppel)


@dataclass
class HausZeile:
    haus: str
    zimmer: int
    belegt: int
    frei: int
    gesperrt: int

    @property
    def quote(self) -> int:
        nutzbar = self.zimmer - self.gesperrt
        return round(100 * self.belegt / nutzbar) if nutzbar else 0


@dataclass
class Auswertung:
    wochen: list[WZeile]
    haeuser: list[HausZeile]
    offen: int
    ohne_platz: int


def auswertung(stand: zp.Planstand, heute: date | None = None, wochen: int = 12) -> Auswertung:
    from belegung import eintragen

    heute = heute or date.today()
    np_ = eintragen.nach_planung(stand, heute, wochen)
    ws = [WZeile(j.text, j.gesamt, n.gesamt, n.emr, n.doppel, n.gesamtstufe, {a: n.stufe(a) for a in ("gesamt", "emr", "doppel")})
          for j, n in np_.wochen]
    hs: dict[str, HausZeile] = {}
    for z in stand.zimmer:
        if not z.aktiv or z.gaeste:
            continue
        h = hs.setdefault(z.haus, HausZeile(z.haus, 0, 0, 0, 0))
        h.zimmer += 1
        s = stand.lage.status_am(z.id, heute)[0]
        if s == "gesperrt":
            h.gesperrt += 1
        elif s in ("frei", "teilweise"):
            h.frei += 1
        else:
            h.belegt += 1
    return Auswertung(ws, [hs[k] for k in sorted(hs, key=zp._haus_sort)], np_.offen, np_.ohne_platz)


# ---------------------------------------------------------------------------------------
# Verwalten
# ---------------------------------------------------------------------------------------

def datenstand(stand: zp.Planstand | None = None) -> list[tuple[str, str, str]]:
    """(Bereich, Stand, Hinweis) – was das Programm gerade kennt."""
    from belegung import anreiseliste, gebaeudeplan, konfig, mieter, uwt

    erg = []
    plan, meta = gebaeudeplan.laden()
    if plan is None:
        erg.append(("Gebäudeplan", "noch keiner übernommen", "Word-Datei in den Ordner „Gebaeudeplan“ legen"))
    else:
        am = (meta.get("importiert_am") or "")[:10]
        erg.append(("Gebäudeplan", f"{plan.datei}" + (f" · Stand {plan.stand:%d.%m.%Y}" if plan.stand else ""),
                    f"übernommen am {date.fromisoformat(am):%d.%m.%Y}" if am else ""))
    personen, _ = anreiseliste.laden()
    erg.append(("Anreiselisten", f"{len(personen)} Personen", ""))
    erg.append(("Blockschulplan (UWT)", f"{len(uwt.laden())} Blöcke", ""))
    erg.append(("Mietverträge", f"{len(mieter.laden())} Verträge", ""))
    if stand is not None:
        erg.append(("Zimmer", f"{sum(1 for z in stand.zimmer if z.aktiv)} im Internat",
                    f"{len(stand.zuweisungen)} Planungen im Programm"))
    erg.append(("Datenordner", str(konfig.datenordner()), ""))
    return erg


def neuer_plan():
    """(Plan, Kennung, Unterschiede) für einen neuen Gebäudeplan im Ordner – None, wenn keiner da ist."""
    from belegung import gebaeudeplan
    from belegung import planabgleich as pa

    kandidat = gebaeudeplan.neuer_plan()
    if kandidat is None:
        return None
    plan, kennung = kandidat
    return plan, kennung, pa.vergleichen(plan, zp.laden())


def plan_uebernehmen(plan, unterschiede: list, kennung: dict) -> str:
    from belegung import aenderungen
    from belegung import planabgleich as pa

    n = _schritt("Gebäudeplan übernommen", lambda: pa.anwenden(plan, unterschiede, kennung), aenderungen.dateien_mit_plan())
    belegt = sum(1 for b in plan.belegungen if b.art == "belegt")
    return f"Gebäudeplan übernommen: {len(plan.zimmer)} Zimmer, {belegt} Belegungen" + \
        (f", {n} Entscheidungen umgesetzt" if n else "")


EINSTELLUNGEN = {
    "reinigung_anreisetag": ("Reinigung vor einer Anreise am Anreisetag selbst (statt am letzten Werktag davor)", bool, False),
    "zimmer_puffer": ("Tage zwischen Abreise und nächster Belegung (1 = nicht am Abreisetag)", int, 1),
}


def einstellungen() -> dict:
    roh = speicher.einstellungen()
    return {k: typ(roh.get(k, standard)) for k, (_t, typ, standard) in EINSTELLUNGEN.items()}


def einstellung_setzen(schluessel: str, wert) -> str:
    if schluessel not in EINSTELLUNGEN:
        raise ValueError("Unbekannte Einstellung.")
    text, typ, _s = EINSTELLUNGEN[schluessel]
    wert = typ(wert)
    if typ is int and not 0 <= wert <= 7:
        raise ValueError("Bitte 0 bis 7 Tage.")
    _schritt(f"Einstellung: {text}", lambda: speicher.einstellung_setzen(schluessel, wert), [speicher.EINSTELLUNGEN])
    return "Einstellung gespeichert"


def wochenblatt(montag: date, namen: bool = True) -> str:
    """Wochenblatt zum Aushängen: je Tag Zimmer, Abreise, Anreise, Reinigung (für Hausmeister und Reinigung)."""
    from belegung import drucklisten

    stand = zp.laden()
    sonntag = montag + timedelta(days=6)
    s = f"{stand.plan.stand:%d.%m.%Y}" if stand.plan and stand.plan.stand else ""
    return drucklisten.wochenblatt_html(stand.lage, _reinigungen(stand, montag, sonntag), montag, namen, s)


def wochen(heute: date) -> dict[str, str]:
    """Auswahl „Diese Woche · KW 43 (19.10.–25.10.)“ … für die nächsten vier Wochen (Schlüssel: Montag ISO)."""
    erg = {}
    for i, text in enumerate(["Diese Woche", "Nächste Woche", "In 2 Wochen", "In 3 Wochen"]):
        mo = heute - timedelta(days=heute.weekday()) + timedelta(weeks=i)
        erg[mo.isoformat()] = f"{text} · KW {mo.isocalendar()[1]} ({mo:%d.%m.}–{mo + timedelta(days=6):%d.%m.})"
    return erg

