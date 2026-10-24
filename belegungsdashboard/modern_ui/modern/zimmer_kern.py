"""Daten der Seite „Zimmer“ – Liste mit Filtern, Zimmer-/Personenkarte, Mängel, Notizen, Umzug – ohne NiceGUI,
über die Funktionen des Hauptprogramms. Jede Änderung ist ein Schritt mit Rückgängig."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from belegung import maengel as mg
from belegung import termine as tm
from belegung import umzug as um
from belegung import zimmerliste as zl
from belegung import zimmerplan as zp

from .kern import _schritt, kurz

STATUS = {"": "Alle", "frei": "Frei", "belegt": "Belegt", "geplant": "Geplant", "gesperrt": "Gesperrt"}
MERKMALE = {"maengel": "Mängel", "reno": "Renoviert", "tiere": "Tier", "doppel": "Doppelzimmer", "maenner": "Bad über Flur"}


# ---------------------------------------------------------------------------------------
# Liste
# ---------------------------------------------------------------------------------------

@dataclass
class LZeile:
    zimmer: str           # ID
    kurz: str
    lage: str
    merkmale: str
    reno: str
    boden: str
    heute: str
    status: str
    maengel: str
    stufe: int            # höchste Mängelstufe (0 = keine)
    notiz: str


def filter_bauen(haus: str = "", status: str = "", schnell: set[str] | None = None, text: str = "") -> zl.Filter:
    schnell = schnell or set()
    return zl.Filter(haus=haus, status=status, text=text.strip(), renoviert="ja" if "reno" in schnell else "alle",
                     merkmale={m for m in schnell if m in ("tiere", "doppel", "maenner")},
                     maengel={"*"} if "maengel" in schnell else set())


def liste(stand: zp.Planstand, f: zl.Filter, tag: date) -> list[LZeile]:
    erg = []
    for r in sorted(zl.filtern(stand, f, tag), key=lambda r: (zp._haus_sort(r.zimmer.haus), zp._etage_sort(r.zimmer.etage),
                                                              r.zimmer.nummer)):
        z = r.zimmer
        st = mg.stufe(r.maengel)
        erg.append(LZeile(z.id, z.kurz, zp.flur_text(z).split(" · ", 1)[-1], zl.merkmal_kurz(z), zl.reno_text(z) or "",
                          r.boden or "", r.heute, r.status, ", ".join(sorted({mg.NAMEN.get(m.art, m.art) for m in r.maengel})),
                          st, z.notiz))
    return erg


def liste_druck(stand: zp.Planstand, f: zl.Filter, tag: date, namen: bool = True) -> str:
    return zl.liste_html(zl.filtern(stand, f, tag), f, namen)


def fm_bericht() -> str:
    """Mängelbericht für das Facility-Management (HTML zum Drucken)."""
    stand = zp.laden()
    k = {z.id: z.kurz for z in stand.zimmer}
    return mg.fm_html(mg.offen(), lambda zid: k.get(zid, kurz(zid)))


# ---------------------------------------------------------------------------------------
# Zimmer- und Personenkarte
# ---------------------------------------------------------------------------------------

@dataclass
class Person:
    schluessel: str
    name: str
    gruppe: str
    von: date
    bis: date
    art: str                      # belegt | geplant
    quelle: str
    kommt: bool
    zimmer_waehlbar: dict = field(default_factory=dict)   # Zimmer-ID → Text (nur geplant, noch nicht angereist)
    zimmer_jetzt: str = ""
    fest_umschaltbar: bool = False
    fest: bool = False
    umzug: object = None          # bestehender Umzug (um.Umzug) oder None
    umzug_moeglich: bool = False
    notizen: list = field(default_factory=list)


@dataclass
class Karte:
    zimmer: str
    kurz: str
    lage: str
    betten: int
    merkmale: str
    hinweis: str
    unbewohnbar: str
    maengel: list                 # (art, Name, Stufe, unbewohnbar, seit)
    personen: list[Person]
    notizen: list                 # tm.Notiz (zum Zimmer)
    belegungen: list              # (Zeitraum, Text, Art) – kommende und laufende


def _umzug_von(stand: zp.Planstand, bw: zp.Bewohner):
    for u in um.zur_person(stand.lage, bw.schluessel):
        if u.status not in ("erledigt", "hinfaellig") and bw.zimmer in (u.von_zimmer, u.nach_zimmer):
            return u
    return None


def karte(stand: zp.Planstand, zid: str, heute: date) -> Karte:
    z = stand.lage.zimmer.get(zid)
    if z is None:
        raise ValueError(f"Zimmer {kurz(zid)} gibt es nicht.")
    personen = []
    for bw in zp.bewohner_im_zimmer(stand, zid, heute):
        nur_umzug = bw.art == "belegt" or bool(bw.umzug) or bw.von <= heute
        p = Person(bw.schluessel, zp.anzeige_name(bw.name), bw.massnahme or zp.GRUPPE_LABEL.get(bw.gruppe, bw.gruppe),
                   bw.von, bw.bis, bw.art, "im Programm geplant" if bw.eigene_belegung else "Gebäudeplan", bw.von > heute,
                   zimmer_jetzt=zid, notizen=tm.notizen(bw.schluessel))
        if bw.bedarf is not None and not nur_umzug:
            w = zp.zimmer_wahl(stand, bw.schluessel)
            if w is not None and not w.gebucht:
                p.zimmer_waehlbar = {zid: f"{z.kurz} (jetzt)"}
                p.zimmer_waehlbar.update({x.id: x.kurz + (" · DZ" if x.betten > 1 else "") for x in w.alternativen})
                p.zimmer_waehlbar.update({x.id: f"{x.kurz} · {g}" for x, g in w.ausnahmen})
        if bw.bedarf is not None and not bw.umzug and stand.zugewiesen(bw.schluessel):
            p.fest_umschaltbar, p.fest = True, bw.art == "belegt"
        p.umzug = _umzug_von(stand, bw)
        p.umzug_moeglich = nur_umzug and bw.bis >= heute
        personen.append(p)
    maengel = [(m.art, mg.NAMEN.get(m.art, m.art), m.stufe, m.unbewohnbar, m.seit) for m in mg.offen(zid)]
    belegungen = []
    for b in sorted(stand.lage.belegungen.get(zid, []), key=lambda b: b.von):
        if b.bis >= heute and b.art != "freigabe":
            text, art = zp.balken_text(b)
            belegungen.append((f"{b.von:%d.%m.%y} – {b.bis:%d.%m.%y}", text, art))
    return Karte(zid, z.kurz, zp.flur_text(z), z.betten, zl.merkmal_kurz(z), z.notiz,
                 stand.lage.unbewohnbar.get(zid, ""), maengel, personen, tm.notizen(zp.zimmer_schluessel(zid)), belegungen)


# ---- Ändern ---------------------------------------------------------------------------

def mangel_setzen(zid: str, art: str, an: bool, notiz: str = "") -> str:
    _schritt(f"Mangel {'gemeldet' if an else 'behoben'}", lambda: mg.setzen(zid, art, an, notiz=notiz), [mg.DATEI])
    return f"{mg.NAMEN.get(art, art)}: {'gemeldet' if an else 'behoben'} ({kurz(zid)})"


def unbewohnbar_setzen(zid: str, art: str, an: bool) -> str:
    _schritt("Unbewohnbar", lambda: mg.sperren_setzen(zid, art, an), [mg.DATEI])
    return f"{kurz(zid)}: {'unbewohnbar' if an else 'wieder bewohnbar'}"


def hinweis_setzen(zid: str, text: str) -> str:
    def aktion():
        st = zp.laden()
        for z in st.zimmer:
            if z.id == zid:
                z.notiz = text.strip()
        zp.stammdaten_speichern(st.zimmer, st.plan)
    _schritt(f"Hinweis {kurz(zid)}", aktion, [zp.STAMM_DATEI])
    return "Hinweis zum Zimmer gespeichert"


def notiz_hinzu(person: str, name: str, text: str, wiedervorlage: date | None) -> str:
    if not text.strip():
        raise ValueError("Bitte einen Text eingeben.")
    _schritt("Notiz", lambda: tm.notiz_speichern(tm.Notiz(person, name, text.strip(), date.today(), wiedervorlage)),
             [tm.DATEI])
    return "Notiz gespeichert" + (f", Wiedervorlage {wiedervorlage:%d.%m.%Y}" if wiedervorlage else "")


def notiz_loeschen(nid: str) -> str:
    _schritt("Notiz gelöscht", lambda: tm.notiz_loeschen(nid), [tm.DATEI])
    return "Notiz gelöscht"


def zimmer_setzen(person: str, zimmer: str) -> str:
    stand = zp.laden()
    _schritt("Zimmer geändert", lambda: zp.zuweisung_setzen(stand, person, zimmer, "Zimmerkarte"))
    return f"Zimmer {kurz(zimmer)} gespeichert" if zimmer else "Planung entfernt"


def fest_setzen(person: str, fest: bool) -> str:
    _schritt("Planung fest" if fest else "Wieder geplant", lambda: zp.status_setzen(person, fest))
    return "Steht fest (gilt als belegt)" if fest else "Wieder als geplant geführt"


def umzug_ziele(zid: str, person: str, name: str, ab: date) -> dict[str, str]:
    stand = zp.laden()
    b = um.belegung_zu(stand, zid, person, name)
    if b is None:
        return {}
    gut, ausnahmen = um.auswahl(stand, b, ab)
    erg = {z.id: z.kurz + (" · DZ" if z.betten > 1 else "") for z in gut}
    erg.update({z.id: f"{z.kurz} · {g}" for z, g in ausnahmen})
    return erg


def umzug_speichern(zid: str, person: str, name: str, nach: str, ab: date, grund: str = "") -> str:
    stand = zp.laden()
    b = um.belegung_zu(stand, zid, person, name)
    if b is None:
        raise ValueError("Die Belegung gibt es nicht mehr.")
    fehler, _hinweis = um.pruefen(stand, b, nach, ab)
    if fehler:
        raise ValueError(fehler)
    _schritt(f"Umzug {name}", lambda: um.speichern(stand, b, nach, ab, grund, quelle="Neue Oberfläche"))
    return f"Umzug {kurz(zid)} → {kurz(nach)} ab {ab:%d.%m.%Y} gespeichert"


def umzug_entfernen(uid: str) -> str:
    _schritt("Umzug zurückgenommen", lambda: um.entfernen(uid, "Neue Oberfläche"))
    return "Umzug zurückgenommen"


def umzug_fest(uid: str, fest: bool) -> str:
    _schritt("Umzug fest" if fest else "Umzug geplant", lambda: um.status_setzen(uid, fest, "Neue Oberfläche"))
    return "Umzug steht fest" if fest else "Umzug wieder geplant"
