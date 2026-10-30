"""Daten & Import: alle Listen und Dateien, aus denen das Programm rechnet – lesen (Vorschau) und übernehmen, mit
den Funktionen des Hauptprogramms. Hochgeladene Dateien liegen nur vorübergehend im Temp-Ordner; ein Gebäudeplan
wird nach dem Übernehmen wie im Hauptprogramm in den Ordner „Gebaeudeplan“ kopiert."""

from __future__ import annotations

import shutil
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

from belegung import anreiseliste, einheitsliste, importe, laden, speicher, uwt
from belegung import zimmerplan as zp

from .kern import _schritt


# ---------------------------------------------------------------------------------------
# Übersicht
# ---------------------------------------------------------------------------------------

def _wann(iso: str | None) -> str:
    if not iso:
        return ""
    try:
        return f"{date.fromisoformat(str(iso)[:10]):%d.%m.%Y}"
    except ValueError:
        return ""


@dataclass
class Quelle:
    schluessel: str
    titel: str
    stand: str
    hinweis: str = ""


def uebersicht() -> list[Quelle]:
    from belegung import gebaeudeplan, zimmerpivot, zkl

    erg = []
    personen, listen = anreiseliste.laden()
    letzte = max(listen.values(), key=lambda l: l.get("importiert_am", ""), default={})
    erg.append(Quelle("anreisen", "Anreiselisten Goslar", f"{len(personen)} Personen aus {len(listen)} Listen",
                      f"zuletzt {letzte.get('datei', '')} am {_wann(letzte.get('importiert_am'))}" if letzte else "noch keine"))
    bloecke = uwt.laden()
    klassen = uwt.klassen_laden()
    erg.append(Quelle("uwt", "UWT (Blockschulplan, Klassen)", f"{len(bloecke)} Blöcke · {len(klassen)} Klassen mit Teilnehmenden",
                      f"zuletzt {bloecke[-1].get('datei', '')}" if bloecke else "noch keine"))
    plan, meta = gebaeudeplan.laden()
    erg.append(Quelle("gebaeudeplan", "Gebäudeplan", f"{plan.datei}" + (f" · Stand {plan.stand:%d.%m.%Y}" if plan and plan.stand else "")
                      if plan else "noch keiner", f"übernommen am {_wann(meta.get('importiert_am'))}" if plan else ""))
    z = zkl.laden()
    erg.append(Quelle("zkl", "Zimmerkontrollliste (ZKL)", f"{len(z.zimmer)} Zimmer · Blatt „{z.blatt}“" if z else "noch keine"))
    zpv = zimmerpivot.laden()
    erg.append(Quelle("zimmerpivot", "Zimmer-Pivot", f"{zpv.zimmer} Zimmer · {zpv.zeitraum[0]:%d.%m.%Y} – {zpv.zeitraum[1]:%d.%m.%Y}"
                      if zpv else "noch keine"))
    q = laden.excel_suchen()
    erg.append(Quelle("pivot", "Belegungs-Pivot (Statistik, Prognose)", q.name if q else "keine Datei gefunden",
                      str(q.parent) if q else ""))
    for art, name in importe.ARTEN.items():
        d = importe.datensatz_laden(art)
        erg.append(Quelle(f"import:{art}", f"{name} (Statistik)", f"{len(d['eintraege'])} Einträge aus {d.get('quelle', '')}"
                          if d else "noch keine", f"importiert am {_wann(d.get('importiert_am'))}" if d else ""))
    erg.append(Quelle("manuell", "Manuelle Einträge (Statistik)", f"{len(laden.manuelle_laden())} Einträge"))
    return erg


# ---------------------------------------------------------------------------------------
# Anreiselisten und Einheitslisten
# ---------------------------------------------------------------------------------------

@dataclass
class ListenVorschau:
    listen: list = field(default_factory=list)          # anreiseliste.Anreiseliste
    einheit: list = field(default_factory=list)         # einheitsliste.Ergebnis
    zeilen: list = field(default_factory=list)          # (Datei, Anreisetag, Gruppe, Personen, Internat)
    hinweise: list = field(default_factory=list)
    fehler: list = field(default_factory=list)


def anreisen_lesen(pfade: list[Path], namen: list[str]) -> ListenVorschau:
    v = ListenVorschau()
    for p, name in zip(pfade, namen):
        try:
            if einheitsliste.ist_einheitsliste(p):
                erg = einheitsliste.lesen(p)
                v.listen += erg.anreisen
                v.einheit.append(erg)
                v.hinweise += [f"{name}: {h}" for h in erg.hinweise]
                if erg.uwt is not None:
                    v.hinweise.append(f"{name}: UWT – {len(erg.uwt.bloecke)} Blöcke mit {len(erg.uwt.personen)} Personen "
                                      "werden mit übernommen")
            else:
                v.listen.append(anreiseliste.liste_lesen(p))
        except Exception as exc:              # noqa: BLE001 – je Datei melden, die anderen trotzdem
            v.fehler.append(f"{name}: {exc}")
    for l in v.listen:
        v.zeilen.append((l.datei, l.datum, l.gruppe, len(l.personen), sum(1 for p in l.personen if p.internat)))
        v.hinweise += [f"{l.datei}: {h}" for h in l.hinweise]
    return v


@dataclass
class ListenAenderung:
    art: str              # neu | geaendert | entfernt
    name: str
    text: str             # z. B. „Abreise 20.11. → 27.11.“
    zimmer: str = ""      # gespeicherte Zimmerplanung (kurz), die davon betroffen ist


def anreisen_aenderungen(v: ListenVorschau) -> list[ListenAenderung]:
    """Was der Import gegenüber dem jetzigen Stand ändern würde – als Trockenlauf mit derselben Logik wie beim
    Übernehmen (Personen werden über die TN-ID wiedererkannt). Betroffene Zimmerplanungen werden genannt."""
    import copy

    from . import hinweise_kern as hk
    from .kern import kurz

    bestand, _ = anreiseliste.laden()
    vorher = {p.schluessel: copy.deepcopy(p) for p in bestand}
    neu_bestand = copy.deepcopy(bestand)
    entfernt = []
    for liste in v.listen:
        neu_bestand, bericht = anreiseliste.uebernehmen(neu_bestand, liste)
        entfernt += bericht.entfernt
    geplant = {z["person"]: z["zimmer"] for z in zp.laden().zuweisungen}

    def d(x):
        return f"{x:%d.%m.}" if x else "offen"

    erg = []
    for p in neu_bestand:
        alt = vorher.get(p.schluessel)
        if alt is None:
            extra = [h.text for h in hk.erkennen(p.bemerkung) if h.art != "vortag"]
            erg.append(ListenAenderung("neu", p.name, f"Anreise {d(p.anreise)}" + (f" · {', '.join(extra)}" if extra else "")))
            continue
        teile = []
        if alt.anreise != p.anreise:
            teile.append(f"Anreise {d(alt.anreise)} → {d(p.anreise)}")
        if alt.abreise != p.abreise:
            teile.append(f"Abreise {d(alt.abreise)} → {d(p.abreise)}")
        if bool(alt.internat) != bool(p.internat):
            teile.append("Internat " + ("ja → nein" if alt.internat else "nein → ja"))
        neu_hinweise = {h.text for h in hk.erkennen(p.bemerkung)} - {h.text for h in hk.erkennen(alt.bemerkung)} - {"evtl. Vortag"}
        if neu_hinweise:
            teile.append("neu: " + ", ".join(sorted(neu_hinweise)))
        if teile:
            erg.append(ListenAenderung("geaendert", p.name, " · ".join(teile), kurz(geplant[p.schluessel])
                                       if p.schluessel in geplant else ""))
    for p in entfernt:
        erg.append(ListenAenderung("entfernt", p.name, f"nicht mehr auf der Liste (Anreise {d(p.anreise)})",
                                   kurz(geplant[p.schluessel]) if p.schluessel in geplant else ""))
    reihe = {"geaendert": 0, "entfernt": 1, "neu": 2}
    return sorted(erg, key=lambda x: (reihe[x.art], not x.zimmer, x.name))


def anreisen_uebernehmen(v: ListenVorschau) -> str:
    def aktion():
        b = anreiseliste.Bericht()
        for l in v.listen:
            x = anreiseliste.importieren(l)
            b.neu += x.neu
            b.aktualisiert += x.aktualisiert
            b.entfernt += x.entfernt
        for e in v.einheit:
            if e.uwt is not None:
                einheitsliste.importieren(einheitsliste.Ergebnis(uwt=e.uwt, klassen=e.klassen))
        return b

    b = _schritt("Anreiselisten importiert", aktion, [anreiseliste.DATEI] + _uwt_dateien())
    teile = [f"{b.neu} neu", f"{b.aktualisiert} aktualisiert"] + ([f"{len(b.entfernt)} nicht mehr auf der Liste"] if b.entfernt else [])
    return "Anreisen importiert: " + ", ".join(teile)


# ---------------------------------------------------------------------------------------
# UWT
# ---------------------------------------------------------------------------------------

def uwt_lesen(pfad: Path):
    """('klassen', (klassen, hinweise)) oder ('bloecke', UwtListe)."""
    if uwt.ist_klassenliste(pfad):
        return "klassen", uwt.klassen_lesen(pfad)
    return "bloecke", uwt.lesen(pfad)


def klassen_der_liste(liste) -> dict[str, int]:
    """Klassen eines Blockplans mit der Anzahl, die importiert würde (aus den gespeicherten Klassenstärken)."""
    erg: dict[str, int] = {}
    for b in liste.bloecke:
        erg.setdefault(b.klasse, b.anzahl)
    return dict(sorted(erg.items()))


def klassen_anwenden(liste, staerken: dict[str, int]) -> None:
    """Anzahl je Block nach den eingestellten Klassenstärken (0 = Klasse wohnt nicht im Internat, zählt nicht)."""
    for b in liste.bloecke:
        if b.klasse in staerken:
            b.anzahl = max(int(staerken[b.klasse]), 0)


def klassenstaerken() -> dict[str, int]:
    return dict(sorted(uwt.klassenstaerken().items()))


def klassenstaerken_setzen(werte: dict[str, int]) -> str:
    """Gespeicherte Klassenstärken ändern – gelten für den nächsten Import eines Blockplans."""
    werte = {k: max(int(v), 0) for k, v in werte.items()}
    _schritt("Klassenstärken", lambda: uwt.klassenstaerken_speichern({**uwt.klassenstaerken(), **werte}),
             [speicher.EINSTELLUNGEN])
    return f"Klassenstärken gespeichert ({len(werte)} Klassen)"


def uwt_uebernehmen(art: str, daten, datei: str, staerken: dict[str, int] | None = None) -> str:
    if art == "bloecke" and staerken:
        klassen_anwenden(daten, staerken)

        def mit_staerken():
            uwt.klassenstaerken_speichern({**uwt.klassenstaerken(), **{k: max(int(v), 0) for k, v in staerken.items()}})
            return uwt.importieren(daten)

        neu, ersetzt = _schritt("UWT importiert", mit_staerken, _uwt_dateien() + [speicher.EINSTELLUNGEN])
        return f"UWT importiert: {neu} Blöcke neu, {ersetzt} ersetzt"
    if art == "klassen":
        klassen, hinweise = daten
        if not klassen:
            raise ValueError("Keine Klassenblätter mit Teilnehmenden gefunden.")
        _schritt("UWT-Klassen", lambda: uwt.klassen_importieren(klassen, datei, hinweise), _uwt_dateien())
        return f"{len(klassen)} Klassen mit {sum(len(x) for x in klassen.values())} Teilnehmenden übernommen"
    neu, ersetzt = _schritt("UWT importiert", lambda: uwt.importieren(daten), _uwt_dateien())
    return f"UWT importiert: {neu} Blöcke neu, {ersetzt} ersetzt"


def ordner_importieren() -> list[str]:
    """Neue Dateien aus den Ordnern „UWT“ (Blockpläne, Kalender, Klassenübersicht) und „Listen“ (Einheitslisten)
    übernehmen – wie das Hauptprogramm beim Start. Schon eingelesene Dateien (gleicher Name und Zeitstempel, auch
    wenn das Hauptprogramm sie gelesen hat) werden übersprungen. Rückgängig gibt es nur, wenn wirklich etwas kam."""
    from belegung import aenderungen

    namen = list(dict.fromkeys(aenderungen._dateien() + [anreiseliste.DATEI] + _uwt_dateien()))
    vorher = aenderungen.schnappschuss(namen)
    meldungen = []
    for art, fn in (("UWT", uwt.automatisch_importieren), ("Liste", einheitsliste.automatisch_importieren)):
        try:
            meldungen += [f"{art}: {m}" for m in fn()]
        except Exception:                  # noqa: BLE001 – ein kaputter Ordner darf den Start nicht verhindern
            continue
    if meldungen:
        aenderungen.merken("Automatisch eingelesen (Ordner UWT/Listen)", vorher)
    return meldungen


def _neues_im_ordner() -> bool:
    """Liegt in „UWT“/„Listen“ eine Datei, die noch nicht eingelesen wurde? (Nur dann lohnt der Vorher-Stand.)"""
    for mod, endungen in ((uwt, (".pdf", ".xlsx", ".xlsm")), (einheitsliste, (".xlsx", ".xlsm", ".csv"))):
        ordner = mod.eingangsordner()
        if not ordner.is_dir():
            continue
        bekannt = speicher.lesen(mod._KENNUNGEN, {})
        if any(p.suffix.lower() in endungen and not p.name.startswith("~$") and bekannt.get(p.name) != int(p.stat().st_mtime)
               for p in ordner.iterdir()):
            return True
    return False


def bedarf_aenderungen(vorher: zp.Planstand, nachher: zp.Planstand, heute: date | None = None) -> list[ListenAenderung]:
    """Was sich an den Personen geändert hat (neu, andere An-/Abreise, weggefallen) – mit betroffener Zimmerplanung."""
    from .kern import kurz

    heute = heute or date.today()
    geplant = {z["person"]: z["zimmer"] for z in vorher.zuweisungen + nachher.zuweisungen if z.get("zimmer")}
    alt = {b.schluessel: b for b in vorher.bedarf}
    neu = {b.schluessel: b for b in nachher.bedarf}

    def zimmer(s):
        return kurz(geplant[s]) if s in geplant else ""

    erg = []
    for s, b in neu.items():
        a = alt.get(s)
        if a is None:
            erg.append(ListenAenderung("neu", b.name, f"Anreise {b.von:%d.%m.}" + (f" · {b.gruppe}" if b.gruppe else "")))
            continue
        teile = []
        if a.von != b.von:
            teile.append(f"Anreise {a.von:%d.%m.} → {b.von:%d.%m.}")
        if a.bis != b.bis:
            teile.append(f"Abreise {a.bis:%d.%m.} → {b.bis:%d.%m.}")
        if teile:
            erg.append(ListenAenderung("geaendert", b.name, " · ".join(teile), zimmer(s)))
    for s, a in alt.items():
        if s not in neu and a.bis >= heute:
            erg.append(ListenAenderung("entfernt", a.name, f"nicht mehr auf der Liste (Anreise {a.von:%d.%m.})", zimmer(s)))
    reihe = {"geaendert": 0, "entfernt": 1, "neu": 2}
    return sorted(erg, key=lambda x: (reihe[x.art], not x.zimmer, x.name))


def ordner_importieren_bericht() -> tuple[list[str], list[ListenAenderung]]:
    """Wie ``ordner_importieren``, dazu der Änderungsbericht: was sich an Personen und Zimmerplanungen geändert hat."""
    if not _neues_im_ordner():
        return [], []
    vorher = zp.laden()
    meldungen = ordner_importieren()
    if not meldungen:
        return [], []
    try:
        return meldungen, bedarf_aenderungen(vorher, zp.laden())
    except Exception:                      # noqa: BLE001 – der Bericht ist Zusatz, eingelesen ist schon
        return meldungen, []


def eingangsordner() -> dict[str, Path]:
    return {"UWT": uwt.eingangsordner(), "Listen": einheitsliste.eingangsordner()}


def _uwt_dateien() -> list[str]:
    import re

    from belegung import uwt as u

    return sorted({v for k, v in vars(u).items() if re.fullmatch(r"[A-Z_]*DATEI[A-Z_]*", k) and isinstance(v, str)})


def uwt_bloecke() -> list[dict]:
    return sorted(uwt.laden(), key=lambda b: (b.get("anreise", ""), b.get("klasse", "")))


def uwt_block_loeschen(klasse: str, anreise: str) -> str:
    _schritt("UWT-Block entfernt", lambda: uwt.block_loeschen(klasse, anreise), _uwt_dateien())
    return f"UWT {klasse} ab {date.fromisoformat(anreise):%d.%m.%Y} entfernt"


# ---------------------------------------------------------------------------------------
# Gebäudeplan, ZKL, Zimmer-Pivot
# ---------------------------------------------------------------------------------------

def gebaeudeplan_lesen(pfad: Path):
    from belegung import gebaeudeplan
    from belegung import planabgleich as pa

    plan = gebaeudeplan.lesen(pfad)
    return plan, pa.vergleichen(plan, zp.laden())


def gebaeudeplan_aus_zwischenablage(text: str, html: str):
    """Kopierte Gebäudeansicht aus dem Belegungssystem (Strg+A, Strg+C) – (Plan, Unterschiede, Kennung).
    Die Rohdaten bleiben zur Nachkontrolle im Datenordner liegen (wie im Hauptprogramm)."""
    from belegung import gebaeudeplan
    from belegung import planabgleich as pa

    plan = gebaeudeplan.aus_zwischenablage(text or "", html or "")
    speicher.schreiben(f"{speicher.IMPORT_ORDNER}/gebaeudeplan_eingefuegt.json", {"text": text, "html": (html or "")[:2_000_000]})
    return plan, pa.vergleichen(plan, zp.laden()), {"pfad": "Zwischenablage", "geaendert": 0}


def gebaeudeplan_ablegen(pfad: Path, name: str) -> dict:
    """Wie im Hauptprogramm: die Datei in den Ordner „Gebaeudeplan“ legen (Kennung für „schon übernommen“)."""
    from belegung import gebaeudeplan

    ziel = gebaeudeplan.eingangsordner() / name
    ziel.parent.mkdir(parents=True, exist_ok=True)
    if ziel.resolve() != pfad.resolve():
        shutil.copy2(pfad, ziel)
    return {"pfad": ziel.name, "geaendert": int(ziel.stat().st_mtime)}


def zkl_importieren(pfad: Path) -> str:
    from belegung import zkl

    bekannt = {z.id for z in zp.laden().zimmer}
    erg = zkl.lesen(pfad, bekannt)
    _schritt("ZKL importiert", lambda: zkl.speichern(erg), [zkl.DATEI])
    return f"ZKL importiert: {len(erg.zimmer)} Zimmer aus Blatt „{erg.blatt}“"


def zkl_abgleich(alle: bool = False):
    from belegung import zkl

    stand, daten = zp.laden(), zkl.laden()
    return zkl.abgleich(stand, daten, alle=alle) if daten else []


def zkl_umsetzen(gewaehlt_schluessel: set[str], alle: bool = False) -> str:
    from belegung import zkl

    stand, daten = zp.laden(), zkl.laden()
    punkte = zkl.abgleich(stand, daten, alle=alle)
    gewaehlt = [p for p in punkte if p.schluessel in gewaehlt_schluessel]
    rest = [p for p in punkte if p not in gewaehlt]
    n = _schritt("ZKL-Abgleich", lambda: zkl.umsetzen(stand, daten, gewaehlt, rest), [zkl.DATEI, zp.STAMM_DATEI])
    teile = [f"{k} × {zkl.ARTEN[a].split(' (')[0]}" for a, k in n.items()]
    return "ZKL-Abgleich: " + ("; ".join(teile) if teile else "alles als geprüft abgelegt")


def zimmerpivot_importieren(pfad: Path) -> str:
    from belegung import zimmerpivot

    erg = zimmerpivot.lesen(pfad)
    _schritt("Zimmer-Pivot importiert", lambda: zimmerpivot.speichern(erg), [zimmerpivot.DATEI])
    return f"Zimmer-Pivot importiert: {erg.zimmer} Zimmer, {erg.zeitraum[0]:%d.%m.%Y} – {erg.zeitraum[1]:%d.%m.%Y}"


# ---------------------------------------------------------------------------------------
# Belegungs-Pivot und Kapazitäten
# ---------------------------------------------------------------------------------------

def pivot_setzen(pfad: Path, name: str) -> str:
    """Neue Pivot-Datei: in den Programmordner legen und als Quelle merken."""
    from belegung import konfig

    ziel = konfig.programmordner() / name
    if ziel.resolve() != pfad.resolve():
        shutil.copy2(pfad, ziel)
    laden.lade(ziel)                          # prüft, ob sie sich lesen lässt (Fehler → ValueError o. ä.)
    _schritt("Pivot-Datei", lambda: speicher.einstellung_setzen("quelle", str(ziel)), [speicher.EINSTELLUNGEN])
    return f"Pivot-Datei „{name}“ eingelesen"


# ---- Pivot-Struktur (nur nötig, wenn eine Datei anders aufgebaut ist als üblich) -------------------------

PIVOT_MODUS = {"auto": "Automatisch (erste echte Pivot-Tabelle)", "manuell": "Festes Tabellenblatt (Kreuztabelle)"}
PIVOT_AUSRICHTUNG = {"standard": "Standorte/Häuser in Spalten, Tage in Zeilen",
                     "transponiert": "Gespiegelt: Standorte/Häuser in Zeilen, Tage in Spalten"}
PIVOT_EBENEN = {2: "Standort und Haus", 1: "Nur Standort"}
_MATRIX: dict = {}


def pivot_struktur() -> dict:
    """Aktuelle Pivot-Datei, ihr Profil (Felder) und die Tabellenblätter für das Formular."""
    from belegung import pivot

    quelle = laden.excel_suchen()
    if quelle is None or not quelle.exists():
        raise ValueError("Keine Pivot-Datei gewählt – erst unter „Pivot“ eine Datei einlesen.")
    try:
        blaetter = pivot.sheet_namen_datei(quelle)
    except Exception:                      # noqa: BLE001 – z. B. .xls: dann nur „automatisch“
        blaetter = []
    return {"pfad": quelle, "profil": pivot.profil_fuer_datei(quelle.name).to_dict(), "blaetter": blaetter}


def _profil(felder: dict):
    from belegung import pivot

    return pivot.PivotProfil(
        name=(felder.get("name") or "").strip() or "Profil", sheet_modus=felder.get("sheet_modus") or "auto",
        sheet_name=felder.get("sheet_name") or None, ausrichtung=felder.get("ausrichtung") or "standard",
        hierarchie_ebenen=int(felder.get("hierarchie_ebenen") or 2),
        kopfzeilen_marker=felder.get("kopfzeilen_marker") or "Zeilenbeschriftungen",
        zwischensummen_suffix=felder.get("zwischensummen_suffix") or "", datumsformat=felder.get("datumsformat") or "%d.%m.%Y")


def pivot_vorschau(pfad: Path, felder: dict) -> tuple[bool, str]:
    """Trockenlauf: (passt, Text) – zeigt sofort, ob die Einstellungen zur Datei passen."""
    from belegung import konfig, pivot

    p = _profil(felder)
    schluessel = (str(pfad), pfad.stat().st_mtime, p.sheet_modus, p.sheet_name)
    try:
        if schluessel not in _MATRIX:                 # Datei nur neu lesen, wenn sich Blatt/Modus ändert
            _MATRIX.clear()
            _MATRIX[schluessel] = pivot.lese_matrix_datei(pfad, p)[0]
        r = pivot.vorschau(_MATRIX[schluessel], p)
    except Exception as exc:                   # noqa: BLE001
        return False, f"Die Datei konnte so nicht gelesen werden: {exc}"
    if not r["erfolg"]:
        return False, f"Passt nicht: {r['fehler']}"
    haeuser = " · ".join(f"{konfig.STANDORT_LABEL.get(s, s)}: {', '.join(h) or '—'}" for s, h in r["haeuser_je_standort"].items())
    return True, f"✓ {r['anzahl_tage']} Tage vom {r['erster_tag']:%d.%m.%Y} bis {r['letzter_tag']:%d.%m.%Y} · {haeuser}"


def pivot_struktur_speichern(pfad: Path, felder: dict) -> str:
    from belegung import pivot

    ok, text = pivot_vorschau(pfad, felder)
    if not ok:
        raise ValueError(text)
    p = _profil(felder)

    def aktion():
        profile, zuordnung = pivot.lade_profile()
        profile[p.name] = p
        zuordnung[pfad.name.lower()] = p.name
        pivot.speichere_profile(profile, zuordnung)

    _schritt("Pivot-Struktur", aktion, [speicher.PIVOT_PROFILE])
    return f"Pivot-Struktur „{p.name}“ für {pfad.name} gespeichert"


def pivot_vom_server() -> str:
    q = laden.excel_suchen()
    if q is None:
        raise ValueError("Keine Pivot-Datei gefunden.")
    if not laden.refresh_moeglich():
        raise ValueError("Der Server-Abruf braucht Windows mit Excel.")
    ds = laden.lade(q, refresh=True)
    if ds.pivot_aktualisiert is False:
        raise ValueError("Der Server-Abruf ist fehlgeschlagen (Netz/VPN/Berechtigung) – es gilt der gespeicherte Stand.")
    return f"Pivot vom Server aktualisiert (Stand {ds.stichtag:%d.%m.%Y})"


def kapazitaeten() -> dict[str, dict[str, int]]:
    from belegung import konfig

    k = laden.kapazitaeten_laden()
    return {s: {"netto": int(k.get(s, {}).get("netto", 0) or 0), "brutto": int(k.get(s, {}).get("brutto", 0) or 0)}
            for s in konfig.STANDORTE}


def kapazitaeten_speichern(werte: dict[str, dict[str, int]]) -> str:
    _schritt("Kapazitäten", lambda: laden.kapazitaeten_speichern(werte), [speicher.KAPAZITAETEN])
    return "Kapazitäten gespeichert"


# ---------------------------------------------------------------------------------------
# Mieten/Anreisen (Statistik) und manuelle Einträge
# ---------------------------------------------------------------------------------------

def statistik_lesen(pfad: Path, name: str, art: str):
    tab = importe.tabelle_lesen(pfad)
    zu = importe.gemerkte_zuordnung(art, name) or importe.zuordnung_erraten(tab)
    if zu.sheet and zu.sheet != tab.sheet:
        tab = importe.tabelle_lesen(pfad, zu.sheet)
    eintraege, hinweise = importe.umwandeln(tab, zu, art)
    return zu, eintraege, hinweise, importe.standorte_in(eintraege)


def statistik_uebernehmen(art: str, pfad: Path, name: str, zu, eintraege: list[dict]) -> str:
    if not eintraege:
        raise ValueError("Keine Einträge erkannt – bitte die Datei im Hauptprogramm mit Spaltenzuordnung importieren.")
    ziel = Path(pfad).with_name(name)
    if ziel != pfad:
        shutil.copy2(pfad, ziel)
    _schritt(f"{importe.ARTEN[art]} importiert", lambda: importe.datensatz_speichern(art, ziel, zu, eintraege),
             [f"{speicher.IMPORT_ORDNER}/{art}.json", f"{speicher.IMPORT_ORDNER}/zuordnungen.json"])
    return f"{len(eintraege)} {importe.ARTEN[art]} importiert"


def statistik_loeschen(art: str) -> str:
    _schritt(f"{importe.ARTEN[art]} entfernt", lambda: importe.datensatz_loeschen(art), [f"{speicher.IMPORT_ORDNER}/{art}.json"])
    return f"Alle importierten {importe.ARTEN[art]} entfernt"


def manuelle() -> list[dict]:
    return laden.manuelle_laden()


def manuell_hinzu(typ: str, standort: str, von: date, bis: date, anzahl: int, bezeichnung: str) -> str:
    if bis < von:
        raise ValueError("„Bis“ liegt vor „Von“.")
    roh = laden.manuelle_laden()
    roh.append({"typ": typ, "standort": standort, "von": von.isoformat(), "bis": bis.isoformat(), "anzahl": int(anzahl),
                "bezeichnung": bezeichnung.strip()})
    _schritt("Manueller Eintrag", lambda: laden.manuelle_speichern(roh), [speicher.MANUELLE_EINTRAEGE])
    return "Eintrag gespeichert"


def manuell_loeschen(index: int) -> str:
    roh = laden.manuelle_laden()
    if not 0 <= index < len(roh):
        raise ValueError("Den Eintrag gibt es nicht mehr.")
    del roh[index]
    _schritt("Manueller Eintrag gelöscht", lambda: laden.manuelle_speichern(roh), [speicher.MANUELLE_EINTRAEGE])
    return "Eintrag gelöscht"
