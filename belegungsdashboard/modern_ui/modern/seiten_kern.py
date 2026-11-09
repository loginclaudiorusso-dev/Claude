"""Daten für Zeitstrahl, Reinigung, Mieter, Auswertung und Verwalten – ohne NiceGUI, über die Funktionen des
Hauptprogramms. Änderungen laufen wie in ``kern`` als Schritt mit Rückgängig."""

from __future__ import annotations

import html
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


def zeitstrahl(stand: zp.Planstand, haus: str, start: date, tage: int = 28, heute: date | None = None,
               flur: str = "") -> list[ZsZeile]:
    heute = heute or date.today()
    ende = start + timedelta(days=tage - 1)
    probleme = problemfaelle(stand, heute)
    from belegung import maengel as mg

    try:
        maengel = mg.offen_je_zimmer()
    except Exception:                      # noqa: BLE001
        maengel = {}
    erg = []
    zimmer = sorted((z for z in stand.zimmer if z.aktiv and z.haus == haus
                     and (not flur or "|".join(z.flur_schluessel) == flur)),      # „Flure“: nur dieser Flur
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

ZEITRAUM = {"heute": "Heute", "woche": "Diese Woche", "naechste": "Nächste Woche", "offen": "Offen – auch ältere"}
# 0.80: So weit zurück zählt eine nicht abgehakte Reinigung als „nicht bezugsfertig“ (Besen an der Kachel) – dieselbe
# Spanne zeigt „Offen – auch ältere“ in der Reinigungsliste, damit jeder Besen dort auch zu finden ist.
OFFEN_ZURUECK = 14
ZUSTAND_HEUTE = {"frei": "frei", "teilweise": "1 Bett frei", "belegt": "belegt", "geplant": "zugeteilt",
                 "gesperrt": "gesperrt"}


def zeitraum(wahl: str, heute: date) -> tuple[date, date]:
    if wahl == "heute":
        return heute, heute
    if wahl == "offen":
        return heute - timedelta(days=OFFEN_ZURUECK), heute + timedelta(days=7)
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
    heute: str = ""          # 0.80: Zustand des Zimmers heute – frei | teilweise | belegt | geplant | gesperrt

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
                          rl.notiz(r), rl.details(r, True), r.manuell_id, _zustand_heute(stand, r.zimmer.id, heute)))
    return erg


def _zustand_heute(stand: zp.Planstand, zid: str, heute: date) -> str:
    try:
        return stand.lage.status_am(zid, heute)[0]
    except (KeyError, AttributeError):
        return ""


@dataclass
class LastTag:
    tag: date
    je_haus: dict[str, int]
    spitze: bool = False

    @property
    def n(self) -> int:
        return sum(self.je_haus.values())


def reinigung_last(stand: zp.Planstand, heute: date, wochen: int = 6) -> tuple[list[LastTag], dict[str, int], float]:
    """Reinigungen (Auszug, Vorbereiten, von Hand) je Tag und Haus für die nächsten Wochen – ab Montag dieser Woche.
    Spitzentag = deutlich mehr als an einem üblichen Werktag (≥ 1,5 × Ø der Werktage mit Reinigung, mindestens 5).
    Gezählt werden Zimmer, nicht Arbeitszeit – die Dauer je Zimmer kennt das Programm nicht."""
    start = heute - timedelta(days=heute.weekday())
    ende = start + timedelta(days=7 * wochen - 1)
    tage = {start + timedelta(days=i): {} for i in range(7 * wochen)}
    for r in _reinigungen(stand, start, ende):
        if r.tag in tage:
            tage[r.tag][r.zimmer.haus] = tage[r.tag].get(r.zimmer.haus, 0) + 1
    erg = [LastTag(t, dict(sorted(h.items(), key=lambda x: zp._haus_sort(x[0])))) for t, h in sorted(tage.items())]
    werktage = [t.n for t in erg if t.tag.weekday() < 5 and t.n]
    schnitt = sum(werktage) / len(werktage) if werktage else 0.0
    for t in erg:
        t.spitze = t.n >= max(5, 1.5 * schnitt)
    je_haus: dict[str, int] = {}
    for t in erg:
        for h, n in t.je_haus.items():
            je_haus[h] = je_haus.get(h, 0) + n
    return erg, dict(sorted(je_haus.items(), key=lambda x: zp._haus_sort(x[0]))), schnitt


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


def reinigung_druck(von: date, bis: date, heute: date | None = None, reihenfolge: list[str] | None = None,
                    sortiert_nach: str = "") -> str:
    """Druckfertiges HTML der Reinigungsliste – im Aufbau wie im Hauptprogramm, aber (0.81) in der Reihenfolge, die
    auf dem Bildschirm eingestellt ist (reihenfolge = Schlüssel der Zeilen von oben nach unten). Ohne eigene
    Sortierung gilt die übliche Reihenfolge nach Frist."""
    heute = heute or date.today()
    stand = zp.laden()
    fertig = rl.erledigt()
    rs = in_reihenfolge(rl.sortiert(_reinigungen(stand, von, bis), heute, fertig), reihenfolge or [])
    return druck_html(rs, von, bis, f"Stand {heute:%d.%m.%Y}", heute, fertig, sortiert_nach)


def in_reihenfolge(rs: list, reihenfolge: list[str], schluessel=rl.schluessel) -> list:
    """Zeilen in die Bildschirm-Reihenfolge bringen; was dort nicht steht (z. B. weggefiltert), folgt danach in
    der bisherigen Reihenfolge."""
    platz = {k: i for i, k in enumerate(reihenfolge)}
    return sorted(rs, key=lambda r: platz.get(schluessel(r), len(platz)))          # sorted ist stabil


# ---------------------------------------------------------------------------------------
# Facility-Checks (0.82): Zeitraum wählbar, Druck in der Bildschirm-Reihenfolge
# ---------------------------------------------------------------------------------------

FC_ZEITRAUM = {"offen": "Offen – auch ältere", "woche": "Diese Woche", "naechste": "Nächste Woche",
               "sechs": "Nächste 6 Wochen", "eigen": "Eigener Zeitraum"}
FC_ZURUECK = 90          # „Offen – auch ältere“: so weit zurück (abgehakte Checks merkt sich das Programm 180 Tage)


def fc_zeitraum(wahl: str, heute: date, von: date | None = None, bis: date | None = None) -> tuple[date, date]:
    if wahl == "offen":
        return heute - timedelta(days=FC_ZURUECK), heute + timedelta(days=45)
    if wahl in ("woche", "naechste"):
        return zeitraum(wahl, heute)
    if wahl == "eigen" and von and bis:
        return (von, bis) if von <= bis else (bis, von)
    return heute - timedelta(days=14), heute + timedelta(days=45)


def fc_schluessel(c) -> str:
    return c.schluessel


def facility_druck(von: date, bis: date, heute: date | None = None, reihenfolge: list[str] | None = None,
                   sortiert_nach: str = "", nur: str = "alle") -> str:
    """Druckfertiges HTML der Facility-Checks im Zeitraum – in der Reihenfolge vom Bildschirm. nur: offen |
    erledigt | alle (wie der Filter auf dem Bildschirm)."""
    from belegung import eintragen

    heute = heute or date.today()
    cs = eintragen.facility_checks(zp.laden().lage, von, bis)
    cs = [c for c in cs if nur == "alle" or (nur == "offen") != c.haken]
    return facility_html(in_reihenfolge(cs, reihenfolge or [], fc_schluessel), von, bis, heute, sortiert_nach)


def facility_html(cs: list, von: date, bis: date, heute: date, sortiert_nach: str = "") -> str:
    from belegung import eintragen
    from .standort_kern import kurz as zkurz

    e = html.escape
    breiten = (5, 13, 10, 24, 22, 10, 16)
    kopf = ("", "Auszug", "Zimmer", "Bewohner", "Maßnahme", "Aufenthalt", "Notiz")
    offen = sum(1 for c in cs if not c.haken)
    teile = [
        "<html><head><meta charset='utf-8'><style>",
        "body { font-family: 'Segoe UI', Arial, sans-serif; font-size: 10pt; color: #111; }",
        "h1 { font-size: 14pt; margin: 0; } .sub { color: #555; }",
        "th { text-align: left; font-size: 8.5pt; color: #333; background-color: #e9ecf0; }",
        "</style></head><body>",
        f"<h1>Facility-Checks · {von:%d.%m.} – {bis:%d.%m.%Y}</h1>",
        f"<div class='sub'>{len(cs)} Zimmer, davon {offen} offen · Aufgabe: {e(eintragen.FACILITY_AUFGABE)}"
        + f" · Stand {heute:%d.%m.%Y}" + (f" · sortiert nach {e(sortiert_nach)}" if sortiert_nach else "")
        + " · ☐ nach der Prüfung abhaken</div><br>",
    ]
    if not cs:
        teile.append("<p>In diesem Zeitraum gibt es keine Facility-Checks.</p>")
    else:
        teile.append("<table width='100%' cellspacing='0' cellpadding='5' border='1' "
                     "style='border-collapse: collapse; border-color: #b8bec6;'><tr>"
                     + "".join(f"<th width='{b}%'>{k}</th>" for b, k in zip(breiten, kopf)) + "</tr>")
        for c in cs:
            zellen = (f"{c.bis:%d.%m.%Y}", zkurz(c.zimmer), c.name, c.massnahme, f"{c.monate} Monate", "")
            grau = " style='color: #888;'" if c.haken else ""
            teile.append(f"<tr{grau}><td align='center' style='font-size: 12pt;'>"
                         f"{'☑' if c.haken else '☐'}</td>" + "".join(f"<td>{e(str(x))}</td>" for x in zellen) + "</tr>")
        teile.append("</table>")
    teile.append("</body></html>")
    return "\n".join(teile)


def druck_html(rs: list, von: date, bis: date, stand: str, heute: date, fertig, sortiert_nach: str = "") -> str:
    """Wie reinigungsliste.html_text des bisherigen Programms (gleiches Druckbild), nur ohne erneutes Sortieren."""
    e = html.escape
    breiten = (5, 10, 18, 7, 18, 20, 22)
    kopf = ("", "Zimmer", "Lage", "Betten", "Auszug", "Sauber bis spätestens", "Notiz")
    teile = [
        "<html><head><meta charset='utf-8'><style>",
        "body { font-family: 'Segoe UI', Arial, sans-serif; font-size: 10pt; color: #111; }",
        "h1 { font-size: 14pt; margin: 0; } .sub { color: #555; }",
        "th { text-align: left; font-size: 8.5pt; color: #333; background-color: #e9ecf0; }",
        ".eilig { font-weight: bold; }",
        "</style></head><body>",
        f"<h1>{e(rl.titel(von, bis))}</h1>",
        f"<div class='sub'>{rl.zaehlung(rs)}" + (f" · Gebäudeplan-Stand {e(stand)}" if stand else "")
        + (f" · sortiert nach {e(sortiert_nach)}" if sortiert_nach else "")
        + " · sauber bis spätestens = letzter Werktag vor der nächsten Anreise (Sa/So wird nicht gereinigt)"
        " · ☐ nach der Reinigung abhaken</div><br>",
    ]
    if not rs:
        teile.append("<p>In dieser Woche zieht niemand aus und kein leeres Zimmer muss vorbereitet werden.</p>")
    else:
        teile.append("<table width='100%' cellspacing='0' cellpadding='5' border='1' "
                     "style='border-collapse: collapse; border-color: #b8bec6;'><tr>"
                     + "".join(f"<th width='{b}%'>{k}</th>" for b, k in zip(breiten, kopf)) + "</tr>")
        for r, z in zip(rs, rl.zeilen(rs)):
            p = rl.prioritaet(r, heute, fertig)
            klasse = " class='eilig'" if p <= 1 or r.knapp else " style='color: #888;'" if p == 9 else ""
            teile.append(f"<tr{klasse}><td align='center' style='font-size: 12pt;'>{'☑' if p == 9 else '☐'}</td>"
                         + "".join(f"<td>{e(x)}</td>" for x in z) + f"<td>{e(rl.notiz(r))}</td></tr>")
        teile.append("</table>")
    teile.append("</body></html>")
    return "\n".join(teile)


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
    montag: date | None = None


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
    lage: object = None           # Lage nach Planung (probeweise zugeteilt) – für die Einzelheiten je Woche


def auswertung(stand: zp.Planstand, heute: date | None = None, wochen: int = 12) -> Auswertung:
    from belegung import eintragen

    heute = heute or date.today()
    np_ = eintragen.nach_planung(stand, heute, wochen)
    ws = [WZeile(j.text, j.gesamt, n.gesamt, n.emr, n.doppel, n.gesamtstufe, {a: n.stufe(a) for a in ("gesamt", "emr", "doppel")},
                 j.montag) for j, n in np_.wochen]
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
    return Auswertung(ws, [hs[k] for k in sorted(hs, key=zp._haus_sort)], np_.offen, np_.ohne_platz, np_.lage)


@dataclass
class EngpassZimmer:
    kurz: str
    haus: str
    etage: str
    frei_tage: int                # von den gezählten Tagen der Woche
    tage: int
    wer: list                     # (Name, von, bis, probeweise?) – wer die Woche über drin ist


def engpass_detail(stand: zp.Planstand, lage, montag: date, art: str, heute: date | None = None) -> dict:
    """Wo genau ist es in der Woche knapp? Je Tag die freien Zimmer der Art, je Zimmer frei/teilweise/belegt mit
    Bewohnern – nach Planung (probeweise zugeteilte Anreisen sind markiert)."""
    heute = heute or date.today()
    lage = lage or stand.lage
    tage = [montag + timedelta(days=i) for i in range(7) if montag + timedelta(days=i) >= heute]
    zimmer = [z for z in lage.zimmer.values() if z.aktiv and not z.gaeste]
    if art == "emr":
        zimmer = [z for z in zimmer if zp.erlaubt(z, "EMR")]
    elif art == "doppel":
        zimmer = [z for z in zimmer if z.betten > 1 and zp.erlaubt(z, "UWT")]
    echt = {id(b) for v in stand.lage.belegungen.values() for b in v}
    je_tag = [(t, sum(1 for z in zimmer if lage.status_am(z.id, t)[0] == "frei")) for t in tage]
    liste = []
    for z in zimmer:
        frei = sum(1 for t in tage if lage.status_am(z.id, t)[0] == "frei")
        wer = []
        if tage:
            for b in lage.belegungen.get(z.id, []):
                if b.bis >= tage[0] and b.von <= tage[-1] and b.art in ("belegt", "geplant", "gesperrt"):
                    name = zp.anzeige_name(b.name) if b.name else ("gesperrt" + (f" ({b.grund})" if b.grund else ""))
                    wer.append((name, b.von, b.bis, id(b) not in echt))
        liste.append(EngpassZimmer(z.kurz, z.haus, z.etage, frei, len(tage), wer))
    liste.sort(key=lambda x: (-x.frei_tage, zp._haus_sort(x.haus), zp._etage_sort(x.etage), x.kurz))
    return {"tage": je_tag, "zimmer": liste, "art": art}


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

