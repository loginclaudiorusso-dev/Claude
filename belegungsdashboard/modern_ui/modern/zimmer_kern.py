"""Daten der Seite „Zimmer“ – Liste mit Filtern, Zimmer-/Personenkarte, Mängel, Notizen, Umzug – ohne NiceGUI,
über die Funktionen des Hauptprogramms. Jede Änderung ist ein Schritt mit Rückgängig."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta

from belegung import maengel as mg
from belegung import termine as tm
from belegung import umzug as um
from belegung import zimmerliste as zl
from belegung import zimmerplan as zp

from .kern import _schritt, kurz

STATUS = {"": "Alle", "frei": "Frei", "belegt": "Belegt", "geplant": "Geplant", "gesperrt": "Gesperrt"}
MERKMALE = {"maengel": "Mängel", "reno": "Renoviert", "Vinyl": "Vinyl", "Teppich": "Teppich", "tiere": "Tier",
            "doppel": "Doppelzimmer", "maenner": "Bad über Flur"}
# Seltenere Filter (wie „Filter ▾“ im bisherigen Programm)
MEHR_LEER = {"boeden": [], "merkmale": [], "renoviert": "alle", "gruppen": [], "modus": "wohnt", "alle": False, "maengel": []}


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


def filter_bauen(haus: str = "", status: str = "", schnell: set[str] | None = None, text: str = "",
                 mehr: dict | None = None) -> zl.Filter:
    schnell = schnell or set()
    m = {**MEHR_LEER, **(mehr or {})}
    return zl.Filter(haus=haus, status=status, text=text.strip(),
                     renoviert="ja" if "reno" in schnell else m["renoviert"],
                     boeden=set(m["boeden"]) | ({"Vinyl", "Teppich"} & schnell),
                     merkmale=set(m["merkmale"]) | {x for x in schnell if x in ("tiere", "doppel", "maenner")},
                     nur_internat=not m["alle"], gruppen=set(m["gruppen"]), gruppen_modus=m["modus"],
                     maengel=set(m["maengel"]) | ({"*"} if "maengel" in schnell else set()))


def mehr_aktiv(mehr: dict | None) -> int:
    """Wie viele der selteneren Filter gesetzt sind (für die Zahl am Knopf „Filter“)."""
    m = {**MEHR_LEER, **(mehr or {})}
    return (len(m["boeden"]) + len(m["merkmale"]) + len(m["gruppen"]) + len(m["maengel"])
            + (m["renoviert"] != "alle") + bool(m["alle"]))


def filter_optionen(heute: date) -> dict:
    """Auswahl für „Filter“: Boden, Mangel (Stufe/Art), Renovierung, Merkmale, Personengruppe."""
    return {
        "boeden": {b: ("Boden unbekannt" if b == "unbekannt" else b)
                   for b in [x for x in zl.BOEDEN if x not in ("Vinyl", "Teppich")] + ["unbekannt"]},
        "maengel": {**{f"stufe:{st}": f"{mg.STUFEN[st][3].capitalize()} – {mg.STUFEN[st][0]}" for st in (3, 2, 1)},
                    **dict(mg.KATALOG)},
        "renoviert": {"alle": "egal", "nein": "nicht renoviert / unbekannt",
                      **{f"seit:{j}": f"renoviert seit {j}" for j in range(heute.year - 1, heute.year - 6, -1)}},
        "merkmale": {"maenner": "Bad über den Flur (nur Männer)", "gaeste": "Gästezimmer"},
        "gruppen": {g: zp.GRUPPE_LABEL.get(g, g) for g in zp.GRUPPEN},
        "modus": {"wohnt": "… wohnt dort", "darf": "… darf dort wohnen (Regeln)"},
    }


def zaehler(stand: zp.Planstand, haus: str, tag: date, alle: bool = False) -> dict[str, int]:
    """Zahlen an den Status-Knöpfen (für das gewählte Haus)."""
    zs = zl.filtern(stand, zl.Filter(nur_internat=not alle, haus=haus), tag)
    n = {s: sum(1 for r in zs if r.status == s or (s == "frei" and r.status == "teilweise"))
         for s in ("frei", "belegt", "geplant", "gesperrt")}
    n[""] = len(zs)
    return n


def kennzahl_text(zs: list) -> str:
    """„335 Zimmer · 120 belegt/geplant · 215 frei · Auslastung 36 %“ – wie im Gebäudeplan."""
    bel = sum(1 for r in zs if r.status in ("belegt", "geplant"))
    frei = sum(1 for r in zs if r.status in ("frei", "teilweise"))
    nutzbar = sum(1 for r in zs if r.status != "gesperrt")
    return (f"{len(zs)} Zimmer · {bel} belegt/geplant · {frei} frei"
            + (f" · Auslastung {bel / nutzbar:.0%}".replace("%", " %") if nutzbar else ""))


def _sortiert(stand: zp.Planstand, f: zl.Filter, tag: date) -> list:
    return sorted(zl.filtern(stand, f, tag), key=lambda r: (zp._haus_sort(r.zimmer.haus), zp._etage_sort(r.zimmer.etage),
                                                            r.zimmer.nummer))


def liste(stand: zp.Planstand, f: zl.Filter, tag: date) -> list[LZeile]:
    erg = []
    for r in _sortiert(stand, f, tag):
        z = r.zimmer
        st = mg.stufe(r.maengel)
        erg.append(LZeile(z.id, z.kurz, zp.flur_text(z).split(" · ", 1)[-1], zl.merkmal_kurz(z), zl.reno_text(z) or "",
                          r.boden or "", r.heute, r.status, ", ".join(sorted({mg.NAMEN.get(m.art, m.art) for m in r.maengel})),
                          st, z.notiz))
    return erg


def liste_druck(stand: zp.Planstand, f: zl.Filter, tag: date, namen: bool = True) -> str:
    return zl.liste_html(zl.filtern(stand, f, tag), f, namen)


def liste_tsv(stand: zp.Planstand, f: zl.Filter, tag: date) -> tuple[str, int]:
    """Die angezeigten Zimmer als Tabulator-Text – in Excel einfügen (Strg+V)."""
    zeilen = ["Zimmer\tEtage\tMerkmale\tRenoviert\tBoden\tAm Tag\tNotiz"]
    for r in _sortiert(stand, f, tag):
        z = r.zimmer
        zeilen.append("\t".join([z.kurz, zp.flur_text(z), zl.merkmal_kurz(z), zl.reno_text(z), r.boden, r.heute, z.notiz]))
    return "\n".join(zeilen), len(zeilen) - 1


def belegung_excel(stand: zp.Planstand, tag: date):
    """Excel-Liste (Zimmer, Etagen, freie Zimmer) am Stichtag – wie „Belegung am Tag als Excel“."""
    from pathlib import Path

    from belegung import speicher, zimmerexport

    ziel = Path(speicher.einstellungen().get("export_ordner") or speicher.pfad("Export"))
    ziel.mkdir(parents=True, exist_ok=True)
    pfad = ziel / f"Freie_Zimmer_{tag:%Y-%m-%d}.xlsx"
    zimmerexport.exportieren(pfad, f"Belegung am {tag:%d.%m.%Y}", [], stand.lage, tag)
    return f"Excel gespeichert: {pfad.name}", pfad


# ---------------------------------------------------------------------------------------
# Karten: je Haus und Etage, je Zimmer Status, Merkmale, Mängel, Bewohner mit Zeitraum (wie der Gebäudeplan)
# ---------------------------------------------------------------------------------------

KARTEN_MAX = 120          # mehr Karten auf einmal werden träge – dann hausweise


@dataclass
class KBelegung:
    art: str              # belegt | geplant | gesperrt
    titel: str
    zeit: str


@dataclass
class KKarte:
    zimmer: str
    kurz: str
    betten: int
    status: str
    merkmale: str
    stufe: int            # höchste Mängelstufe
    maengel: str
    unbewohnbar: bool
    belegungen: list[KBelegung] = field(default_factory=list)
    frei_bis: str = ""


@dataclass
class KEtage:
    titel: str
    unter: str
    karten: list[KKarte]


@dataclass
class KHaus:
    haus: str
    unter: str
    etagen: list[KEtage]


def karten(stand: zp.Planstand, f: zl.Filter, tag: date) -> tuple[list[KHaus], str]:
    zs = _sortiert(stand, f, tag)
    haeuser: dict[str, list] = {}
    for r in zs:
        haeuser.setdefault(r.zimmer.haus, []).append(r)
    hinweis = ""
    if not f.haus and len(zs) > KARTEN_MAX and len(haeuser) > 1:
        erstes = next(iter(haeuser))
        hinweis = (f"Bei vielen Zimmern zeigen die Karten ein Haus auf einmal – hier Haus {erstes}. "
                   "Oben ein Haus wählen oder mit Filtern eingrenzen.")
        haeuser = {erstes: haeuser[erstes]}
    erg = []
    for haus, zeilen in haeuser.items():
        bel = sum(1 for r in zeilen if r.status in ("belegt", "geplant"))
        nutzbar = sum(1 for r in zeilen if r.status != "gesperrt")
        unter = f"{len(zeilen)} Zimmer · {bel} belegt · " + (f"{bel / nutzbar:.0%}".replace("%", " %") if nutzbar else "–") \
            + " Auslastung"
        etagen = []
        for e in sorted({r.zimmer.etage for r in zeilen}, key=zp._etage_sort):
            ez = [r for r in zeilen if r.zimmer.etage == e]
            e_bel = sum(1 for r in ez if r.status in ("belegt", "geplant"))
            etagen.append(KEtage(zp.etage_text(e), f"{len(ez)} Zimmer · {e_bel} belegt", [_kkarte(stand, r, tag) for r in ez]))
        erg.append(KHaus(haus, unter, etagen))
    return erg, hinweis


def _kkarte(stand: zp.Planstand, r, tag: date) -> KKarte:
    z = r.zimmer
    merkmale = [x for x in (f"renoviert {zl.reno_text(z)}" if z.renoviert else "", r.boden, "Tier" if z.tiere else "",
                            "Bad über den Flur" if z.nur_maenner else "", "Gäste" if z.gaeste else "") if x]
    st = mg.stufe(r.maengel)
    k = KKarte(z.id, z.kurz, z.betten, r.status, " · ".join(merkmale), st,
               " · ".join(m.text for m in sorted(r.maengel, key=lambda m: -m.stufe)),
               any(getattr(m, "unbewohnbar", False) for m in r.maengel))
    for b in r.belegungen:
        if b.art == "gesperrt":
            titel = b.grund or "gesperrt"
        else:
            titel = (zp.anzeige_name(b.name) if b.name != zp.PIVOT_NAME else "gebucht (Zimmer-Pivot)") \
                + (f" ({b.massnahme})" if b.massnahme else "")
        k.belegungen.append(KBelegung(b.art, titel, f"{b.von:%d.%m.%Y} – {b.bis:%d.%m.%Y}"))
    if r.status in ("frei", "teilweise"):
        bis = stand.lage.frei_bis(z.id, tag)
        k.frei_bis = f"frei bis {bis:%d.%m.%Y}" if bis else "frei ohne Folgebelegung"
    return k


# ---------------------------------------------------------------------------------------
# Eigenschaften mehrerer Zimmer, Renovierungsliste
# ---------------------------------------------------------------------------------------

def boeden() -> list[str]:
    return list(zl.BOEDEN)


def eigenschaften_setzen(zimmer: list[str], reno: str, reno_datum: date | None, boden: str | None,
                         vermutet: bool) -> str:
    """reno: „gleich“ | „datum“ | „entfernen“ · boden: None = nicht ändern, "" = entfernen, sonst Belag."""
    if not zimmer:
        raise ValueError("Bitte zuerst Zimmer markieren.")
    if reno == "gleich" and boden is None:
        raise ValueError("Es ist nichts zum Ändern gewählt.")

    def aktion():
        st = zp.laden()
        gewaehlt = set(zimmer)
        for z in st.zimmer:
            if z.id not in gewaehlt:
                continue
            if reno == "datum" and reno_datum:
                z.renoviert = reno_datum.isoformat()
            elif reno == "entfernen":
                z.renoviert = ""
            if boden is not None:
                z.boden, z.boden_vermutet = boden, bool(boden) and vermutet
        zp.stammdaten_speichern(st.zimmer, st.plan)
    _schritt(f"Eigenschaften für {len(zimmer)} Zimmer", aktion, [zp.STAMM_DATEI])
    return f"Eigenschaften für {len(zimmer)} Zimmer gespeichert"


def renovierungen_pruefen(stand: zp.Planstand, text: str) -> tuple[int, list[str]]:
    eintraege, fehler = zl.renovierungen_lesen(text, {z.id for z in stand.zimmer})
    return len(eintraege), fehler


def renovierungen_uebernehmen(text: str, boden: str, vermutet: bool) -> str:
    def aktion():
        st = zp.laden()
        eintraege, _f = zl.renovierungen_lesen(text, {z.id for z in st.zimmer})
        if not eintraege:
            raise ValueError("Keine Zimmer erkannt – Spalten Haus, Zimmer, (Notiz,) Datum einfügen.")
        return zl.renovierungen_anwenden(st, eintraege, boden, vermutet)
    n = _schritt("Renovierungsliste übernommen", aktion, [zp.STAMM_DATEI])
    return f"Renovierungen übernommen: {n} Zimmer geändert"


# ---------------------------------------------------------------------------------------
# Person direkt in ein Zimmer: neu anlegen oder aus den Anreisen ohne Zimmer
# ---------------------------------------------------------------------------------------

@dataclass
class Kandidat:
    schluessel: str
    name: str
    zweite: str
    zeit: str
    vorschlag: bool       # dieses Zimmer ist der grüne Vorschlag


def kandidaten(stand: zp.Planstand, zid: str, heute: date, wochen: int = 8) -> list[Kandidat]:
    """Personen der nächsten Wochen ohne Zimmer, denen dieses Zimmer angeboten wird (frei, passt zu den Regeln)."""
    from . import kern

    erg = []
    for an in kern.anreisen(stand, heute):
        if an.tag > heute + timedelta(weeks=wochen):
            continue
        for z in kern.zeilen(stand, an.kennung, heute):
            if z.gespeichert or zid not in {o.zimmer for o in z.optionen}:
                continue
            erg.append(Kandidat(z.schluessel, z.name, z.gruppe, z.zeitraum, z.vorschlag == zid))
    return erg


def person_ins_zimmer(zid: str, name: str, massnahme: str, gruppe: str, anreise: date, abreise: date,
                      geschlecht: str = "", tier: bool = False, bemerkung: str = "", tn_id: str = "") -> str:
    """Neue Person anlegen und gleich in dieses Zimmer setzen – ein Schritt (Rückgängig nimmt beides zurück)."""
    from belegung import anreiseliste

    from . import kern

    name = " ".join(name.split())
    if "," not in name or len(name) < 4:
        raise ValueError("Bitte den Namen als „Nachname, Vorname“ eingeben.")
    if not massnahme.strip():
        raise ValueError("Bitte eine Maßnahme angeben (z. B. „GS RVL“).")
    if abreise is None or abreise <= anreise:
        raise ValueError("Bitte eine Abreise nach der Anreise angeben – sonst lässt sich nicht prüfen, ob das Zimmer frei ist.")
    p = anreiseliste.Person(name, massnahme.strip(), anreise, True, tn_id=tn_id.strip(), abreise=abreise,
                            geschlecht=geschlecht, tier=tier, bemerkung=bemerkung.strip(), abreise_quelle="hand")

    def aktion():
        anreiseliste.person_speichern(p)
        if gruppe:
            zp.angabe_setzen(p.schluessel, gruppe=gruppe)
        werte = {k: v for k, v in (("geschlecht", geschlecht), ("tier", tier)) if v}
        if werte:
            zp.angabe_setzen(p.schluessel, **werte)
        st = zp.laden()
        zt = kern._zuteilung(st, p.schluessel, zid)
        zp.zuweisungen_speichern([zt], "Neue Oberfläche")
    _schritt(f"{name} → {kurz(zid)}", aktion, [anreiseliste.DATEI, zp.PERSONEN_ANGABEN])
    return f"{name} angelegt und in {kurz(zid)} eingeplant ({anreise:%d.%m.} – {abreise:%d.%m.%Y})"


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


# ---------------------------------------------------------------------------------------
# Defekte Zimmer (Mängel) und FM
# ---------------------------------------------------------------------------------------

STUFEN = {3: "Nicht bewohnbar", 2: "Dringend", 1: "Leicht"}


@dataclass
class MZeile:
    zimmer: str
    kurz: str
    lage: str
    stufe: int                    # höchste Stufe der offenen Mängel
    maengel: list                 # (art, Name, Stufe, unbewohnbar, seit, notiz)
    heute: str                    # frei | belegt | …
    naechste: date | None         # nächste Anreise ins Zimmer (ab heute)


def _status_heute(stand: zp.Planstand, heute: date) -> dict[str, str]:
    return {z.id: stand.lage.status_am(z.id, heute)[0] for z in stand.zimmer if z.aktiv}


def maengel_liste(stand: zp.Planstand, heute: date) -> list[MZeile]:
    status = _status_heute(stand, heute)
    erg = []
    for zid, ms in mg.offen_je_zimmer().items():
        z = stand.lage.zimmer.get(zid)
        if z is None or not z.aktiv:
            continue
        naechste = min((b.von for b in stand.lage.belegungen.get(zid, []) if b.art in ("belegt", "geplant") and b.von >= heute),
                       default=None)
        erg.append(MZeile(zid, z.kurz, zp.flur_text(z), mg.stufe(ms),
                          [(m.art, mg.NAMEN.get(m.art, m.art), m.stufe, m.unbewohnbar, m.seit, m.notiz)
                           for m in sorted(ms, key=lambda m: -m.stufe)],
                          mg.ZIMMER_HEUTE.get(status.get(zid, ""), status.get(zid, "")), naechste))
    return sorted(erg, key=lambda r: (-r.stufe, r.naechste or date.max, zp._haus_sort(r.kurz.split("-")[0]), r.kurz))


def _kurz_map(stand: zp.Planstand) -> dict[str, str]:
    return {z.id: z.kurz for z in stand.zimmer}


def fm_bericht_html(stand: zp.Planstand, heute: date) -> str:
    k = _kurz_map(stand)
    return mg.fm_html(mg.offen(), lambda zid: k.get(zid, kurz(zid)), _status_heute(stand, heute), heute)


def fm_mailtext(stand: zp.Planstand) -> str:
    k = _kurz_map(stand)
    return mg.fm_text(mg.offen(), lambda zid: k.get(zid, kurz(zid)))


def fm_excel(stand: zp.Planstand, heute: date):
    from pathlib import Path

    from belegung import speicher

    k = _kurz_map(stand)
    ziel = Path(speicher.einstellungen().get("export_ordner") or speicher.pfad("FM"))
    ziel.mkdir(parents=True, exist_ok=True)
    pfad = ziel / f"Maengel_FM_{heute:%Y-%m-%d}.xlsx"
    n = mg.fm_excel(pfad, mg.offen(), lambda zid: k.get(zid, kurz(zid)), _status_heute(stand, heute), heute)
    return f"FM-Liste mit {n} Mängeln gespeichert", pfad


def fm_erledigte_lesen(pfad):
    eintraege, fehler = mg.fm_erledigte_lesen(pfad)
    offen = {(m.zimmer, m.art) for m in mg.offen()}
    return [e for e in eintraege if (e[0], e[1]) in offen], fehler


def fm_erledigte_uebernehmen(eintraege: list) -> str:
    n = _schritt("FM-Liste übernommen", lambda: mg.erledigte_uebernehmen(eintraege), [mg.DATEI])
    return f"{n} Mängel als behoben übernommen"


# ---------------------------------------------------------------------------------------
# Übersicht: alle Zimmer als Kacheln je Haus und Etage
# ---------------------------------------------------------------------------------------

@dataclass
class Kachel:
    zimmer: str
    kurz: str
    nr: str
    status: str                   # frei | teilweise | belegt | geplant | gesperrt
    stufe: int                    # Mängelstufe (0 = keine)
    unbewohnbar: bool
    titel: str
    arten: frozenset = frozenset()   # Arten der offenen Mängel (für den Mangelart-Filter)


def uebersicht(stand: zp.Planstand, tag: date) -> dict[str, dict[str, list[Kachel]]]:
    """Haus → Etage-Text → Kacheln (am Tag ``tag``)."""
    offen = mg.offen_je_zimmer()
    erg: dict[str, dict[str, list[Kachel]]] = {}
    for z in sorted((z for z in stand.zimmer if z.aktiv), key=lambda z: (zp._haus_sort(z.haus), zp._etage_sort(z.etage), z.nummer)):
        status, bs = stand.lage.status_am(z.id, tag)
        ms = offen.get(z.id, [])
        namen = ", ".join(zp.anzeige_name(b.name) for b in bs if b.art in ("belegt", "geplant") and b.name != zp.PIVOT_NAME)
        titel = f"{z.kurz} · {status}" + (f" · {namen}" if namen else "") + \
            ("\nMängel: " + ", ".join(mg.NAMEN.get(m.art, m.art) for m in ms) if ms else "")
        erg.setdefault(z.haus, {}).setdefault(zp.etage_text(z.etage), []).append(
            Kachel(z.id, z.kurz, z.nr, status, mg.stufe(ms), z.id in stand.lage.unbewohnbar, titel,
                   frozenset(m.art for m in ms)))
    return erg


# Kachel-Auswahl der Übersicht: mehrere Kacheln gleichzeitig. Status-Kacheln schließen sich gegenseitig aus und werden
# deshalb mit „oder“ verknüpft (frei oder geplant), Mängel/unbewohnbar sind Eigenschaften und schränken zusätzlich ein
# (frei + mit Mängeln = freie Zimmer mit Mängeln). Der Mangelart-Filter (Stufe/Art) gilt immer zusätzlich.
KACHEL_STATUS = ("frei", "belegt", "geplant", "gesperrt")
KACHEL_EIGENSCHAFT = ("maengel", "unbewohnbar")


def kacheln(wert) -> frozenset:
    """Kachel-Auswahl vereinheitlichen – andere Seiten springen noch mit einem einzelnen Schlüssel („frei“) hierher."""
    if not wert:
        return frozenset()
    return frozenset({wert} if isinstance(wert, str) else wert)


def mangel_passt(stufe: int, arten, filt) -> bool:
    """Mangelart-Filter wie in der Liste: Stufen (rot/orange/gelb) und Arten, beides gesetzt = beides muss passen."""
    if not filt:
        return True
    stufen = {int(t[6:]) for t in filt if t.startswith("stufe:")}
    gesucht = {t for t in filt if not t.startswith("stufe:")}
    if stufen and stufe not in stufen:
        return False
    return not gesucht or bool(("*" in gesucht and stufe) or set(arten) & gesucht)


def kachel_passt(status: str, stufe: int, unbewohnbar: bool, arten, auswahl, filt=None) -> bool:
    st = auswahl & set(KACHEL_STATUS)
    ei = auswahl & set(KACHEL_EIGENSCHAFT)
    if st and not (status in st or ("frei" in st and status == "teilweise")):
        return False
    if ei and not (("maengel" in ei and stufe) or ("unbewohnbar" in ei and unbewohnbar)):
        return False
    return mangel_passt(stufe, arten, filt)


def kachel_text(auswahl, filt=None) -> str:
    """„frei oder geplant · mit Mängeln · Mangel: Heizung defekt“ – für Überschrift, Menü und Dateiname."""
    teile = []
    st = [KACHEL_TEXT[k] for k in KACHEL_STATUS if k in auswahl]
    if st:
        teile.append(" oder ".join(st))
    ei = [KACHEL_TEXT[k] for k in KACHEL_EIGENSCHAFT if k in auswahl]
    if ei:
        teile.append(" oder ".join(ei))
    if filt:
        teile.append(zl.Filter(maengel=set(filt)).beschreibung().split(" · ", 1)[1])
    return " · ".join(teile)


# ---------------------------------------------------------------------------------------
# Drucken & Excel: Zimmer nach Filter (Liste/Karten) bzw. Kachel (Übersicht) – mit „frei ab“ / „frei bis“
# ---------------------------------------------------------------------------------------

KACHEL_TEXT = {"frei": "frei", "belegt": "belegt", "geplant": "geplant", "gesperrt": "gesperrt",
               "maengel": "mit Mängeln", "unbewohnbar": "unbewohnbar"}
STATUS_TEXT = {"frei": "frei", "teilweise": "1 Bett frei", "belegt": "belegt", "geplant": "geplant", "gesperrt": "gesperrt"}


@dataclass
class DZeile:
    haus: str
    etage: str
    zimmer: str
    betten: int
    status: str                   # frei | teilweise | belegt | geplant | gesperrt (am Stichtag)
    bewohner: str                 # Namen am Stichtag ("" ohne Namen)
    belegt_bis: date | None       # Ende der aktuellen Belegung
    frei_ab: date | None          # ab wann (wieder) frei – Stichtag, wenn schon frei
    frei_bis: date | None         # letzter freier Tag vor der nächsten Belegung (None = offen)
    frei_tage: int | None         # Länge der freien Zeit (None = offen bzw. nicht frei)
    merkmale: str
    boden: str
    renoviert: str
    maengel: str
    notiz: str


def druck_zeilen(stand: zp.Planstand, tag: date, f: zl.Filter | None = None, kachel=None,
                 namen: bool = True, maengel=None) -> list[DZeile]:
    """Die Zimmer der aktuellen Auswahl mit Status am Stichtag und der freien Zeit (frei ab … bis …).
    ``kachel`` = Kachel-Auswahl der Übersicht (ein Schlüssel oder mehrere), ``maengel`` = Mangelart-Filter."""
    lage = stand.lage
    auswahl = kacheln(kachel)
    erg = []
    for r in _sortiert(stand, f or zl.Filter(nur_internat=True), tag):
        z = r.zimmer
        if (auswahl or maengel) and not kachel_passt(r.status, mg.stufe(r.maengel), z.id in lage.unbewohnbar,
                                                     {m.art for m in r.maengel}, auswahl, maengel):
            continue
        personen = [b for b in r.belegungen if b.art in ("belegt", "geplant")]
        belegt_bis = max((b.bis for b in personen), default=None)
        if r.status in ("frei", "teilweise"):
            frei_ab = tag
        elif r.status in ("belegt", "geplant") and belegt_bis:
            frei_ab = belegt_bis + timedelta(days=max(lage.puffer, 1))
        else:
            frei_ab = None
        frei_bis = lage.frei_bis(z.id, frei_ab - timedelta(days=1)) if frei_ab else None
        if frei_ab and frei_bis and frei_bis < frei_ab:          # Folgebelegung schließt direkt an
            frei_bis = frei_ab - timedelta(days=1)
        tage = (frei_bis - frei_ab).days + 1 if frei_ab and frei_bis else None
        bewohner = ", ".join(zp.anzeige_name(b.name) for b in personen if b.name and b.name != zp.PIVOT_NAME) if namen else ""
        if r.status == "gesperrt":
            bewohner = r.heute
        erg.append(DZeile(z.haus, zp.flur_text(z).removeprefix(f"Haus {z.haus} · "), z.kurz, z.betten, r.status, bewohner, belegt_bis, frei_ab, frei_bis,
                          tage if tage is None or tage > 0 else 0, zl.merkmal_kurz(z), r.boden or "", zl.reno_text(z) or "",
                          ", ".join(sorted({mg.NAMEN.get(m.art, m.art) for m in r.maengel})), z.notiz))
    return erg


def _auswahl_text(f: zl.Filter | None, kachel, maengel=None) -> str:
    if f is None and (kachel or maengel):
        return f"alle Häuser · {kachel_text(kacheln(kachel), maengel)}"
    return f.beschreibung() if f else "alle Häuser"


def _frei_bis_text(z: DZeile) -> str:
    if z.frei_ab is None:
        return ""
    return f"{z.frei_bis:%d.%m.%Y}" if z.frei_bis else "offen"


def druck_html(zeilen: list[DZeile], tag: date, f: zl.Filter | None = None, kachel=None,
               namen: bool = True, maengel=None) -> str:
    """Zimmerliste zum Drucken: je Haus, mit Status am Stichtag und „frei ab / frei bis“."""
    from html import escape

    from belegung.drucklisten import _STIL

    n = {s: sum(1 for z in zeilen if z.status == s) for s in STATUS_TEXT}
    teile = [_STIL, "<style>th,td{padding:2px 7px;text-align:left;white-space:nowrap} td:last-child{white-space:normal}"
             " td.r{text-align:right} td.frei{color:#0a7a3e;font-weight:600} td.fb{font-weight:600}"
             " tr.gesperrt td{color:#888} h2{font-size:11.5pt;margin:12px 0 4px}</style>",
             "<h1>Zimmer</h1>",
             f"<div class='klein'>Internat Goslar · {escape(_auswahl_text(f, kachel, maengel))} · Stand {tag:%d.%m.%Y} · "
             f"{len(zeilen)} Zimmer · {n['frei'] + n['teilweise']} frei · {n['belegt']} belegt · {n['geplant']} geplant · "
             f"{n['gesperrt']} gesperrt</div>"]
    kopf = ["Zimmer", "Etage", "Status"] + (["Bewohner"] if namen else []) + ["belegt bis", "frei ab", "frei bis",
                                                                               "freie Tage", "Merkmale", "Mängel"]
    haus = None
    for z in zeilen:
        if z.haus != haus:
            if haus is not None:
                teile.append("</table>")
            haus = z.haus
            teile.append(f"<h2>Haus {escape(haus)}</h2><table><tr>" + "".join(f"<th>{k}</th>" for k in kopf) + "</tr>")
        frei = z.status in ("frei", "teilweise")
        zellen = [escape(z.zimmer), escape(z.etage), escape(STATUS_TEXT.get(z.status, z.status))] + \
            ([escape(z.bewohner)] if namen else []) + \
            [f"{z.belegt_bis:%d.%m.%Y}" if z.belegt_bis else "", f"{z.frei_ab:%d.%m.%Y}" if z.frei_ab else "",
             _frei_bis_text(z), "" if z.frei_tage is None else str(z.frei_tage), escape(z.merkmale), escape(z.maengel)]
        teile.append(f"<tr class='{z.status}'>" + "".join(
            f"<td class='{'frei' if frei and i == 2 else ''}{' r' if i == len(zellen) - 3 else ''}{' fb' if i == len(zellen) - 4 else ''}'>{c}</td>"
            for i, c in enumerate(zellen)) + "</tr>")
    if haus is not None:
        teile.append("</table>")
    teile.append("<div class='klein' style='margin-top:10px'>„frei bis“ = letzter freier Tag vor der nächsten bekannten "
                 "Belegung (offen = keine Folgebelegung bekannt). Bei belegten Zimmern: frei ab dem Tag nach dem Auszug.</div>")
    return "".join(teile)


def druck_excel(zeilen: list[DZeile], tag: date, f: zl.Filter | None = None, kachel=None,
                namen: bool = True, maengel=None):
    """Dieselbe Auswahl als Excel-Tabelle (sortier- und filterbar), mit den Spalten „frei ab“, „frei bis“, „freie Tage“."""
    from pathlib import Path

    from openpyxl import Workbook

    from belegung import speicher, zimmerexport

    kopf = ["Haus", "Etage", "Zimmer", "Betten", "Status"] + (["Bewohner"] if namen else []) + \
        ["belegt bis", "frei ab", "frei bis", "freie Tage", "Merkmale", "Boden", "Renoviert", "Mängel", "Notiz"]
    breiten = [7, 22, 10, 7, 12] + ([30] if namen else []) + [12, 12, 12, 10, 14, 14, 14, 26, 30]
    daten, markierung = [], {}
    for i, z in enumerate(zeilen):
        frei_bis = z.frei_bis if z.frei_bis else ("offen" if z.frei_ab else None)
        daten.append([z.haus, z.etage, z.zimmer, z.betten, STATUS_TEXT.get(z.status, z.status)] + ([z.bewohner] if namen else [])
                     + [z.belegt_bis, z.frei_ab, frei_bis, z.frei_tage, z.merkmale, z.boden, z.renoviert, z.maengel, z.notiz])
        if z.status in ("frei", "teilweise"):
            markierung[i] = "E6F4EA"
    wb = Workbook()
    ws = wb.active
    ws.title = "Zimmer"
    n_frei = sum(1 for z in zeilen if z.status in ("frei", "teilweise"))
    zimmerexport._tabelle(ws, f"Zimmer am {tag:%d.%m.%Y}",
                          f"{_auswahl_text(f, kachel, maengel)} · {len(zeilen)} Zimmer · {n_frei} frei · „frei bis“ = letzter freier "
                          "Tag vor der nächsten bekannten Belegung (offen = keine bekannt)", kopf, daten, breiten, markierung)
    ziel = Path(speicher.einstellungen().get("export_ordner") or speicher.pfad("Export"))
    ziel.mkdir(parents=True, exist_ok=True)
    teil = "_".join(k for k in KACHEL_STATUS + KACHEL_EIGENSCHAFT if k in kacheln(kachel)) or "Auswahl"
    pfad = ziel / f"Zimmer_{teil}{'_Maengelart' if maengel else ''}_{tag:%Y-%m-%d}{'' if namen else '_ohne_Namen'}.xlsx"
    wb.save(pfad)
    return f"Excel gespeichert: {pfad.name} ({len(zeilen)} Zimmer)", pfad
