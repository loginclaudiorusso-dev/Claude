"""1.29: Maßnahmen – Daten einlesen: Maßnahmen-Pivot (mit Archiv), Anreiselisten, Zuordnung zu Gruppen, eigene Plätze.

Baut auf massnahmen_kern auf. Aus massnahmen_kern.py ausgelagert (nur verschoben, keine Funktionsänderung); dort
weiter erreichbar."""

from __future__ import annotations

import re
import statistics as stt
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from belegung import speicher
from .massnahmen_kern import (  # baut auf massnahmen_kern auf
    DATEI, GRUPPEN, _KURS, _TAG, _rle, _roh, _schreiben,
)


# ---- Pivot einlesen -------------------------------------------------------------------------------------

@dataclass
class PivotErgebnis:
    von: date
    bis: date
    kurse: dict                    # Kurs → {"von": ISO, "werte": RLE, "dauer": Median-Tage je Person}
    personen: int
    luecken: list                  # [(von, bis)] überbrückt
    bestand: dict = field(default_factory=dict)   # 0.76: Aufenthalte je Person (nur Nummern) + Prüfwerte fürs Bestandsmodell

    @property
    def text(self) -> str:
        t = f"{len(self.kurse)} Kurse, {self.personen} Teilnahmen, {self.von:%d.%m.%Y} – {self.bis:%d.%m.%Y}"
        if self.luecken:
            t += " · überbrückt: " + ", ".join(f"{a:%d.%m.%y}–{b:%d.%m.%y}" for a, b in self.luecken)
        return t


def pivot_aus_zeilen(zeilen, stichtag: date | None = None) -> PivotErgebnis:
    """Zeilen (Tupel) des Pivots: Kopfzeile mit „Zeilenbeschriftungen“ und Tagesdaten, darunter Personen und ihre
    Maßnahme-Zeilen. Namen werden übersprungen."""
    it = iter(zeilen)
    kopf = None
    for z in it:
        if z and isinstance(z[0], str) and z[0].strip().lower() == "zeilenbeschriftungen":
            kopf = z
            break
    if kopf is None:
        raise ValueError("Kein Maßnahmen-Pivot erkannt (Zeile „Zeilenbeschriftungen“ mit Tagesdaten fehlt).")
    spalten = [(i, datetime.strptime(v.strip(), "%d.%m.%Y").date()) for i, v in enumerate(kopf)
               if isinstance(v, str) and _TAG.match(v.strip())]
    spalten += [(i, v.date() if isinstance(v, datetime) else v) for i, v in enumerate(kopf)
                if isinstance(v, (datetime, date)) and i]
    spalten.sort(key=lambda x: x[1])
    if not spalten:
        raise ValueError("Im Maßnahmen-Pivot fehlen die Tagesspalten.")
    tage = [d for _i, d in spalten]
    von, bis = tage[0], tage[-1]
    n = (bis - von).days + 1
    pos = [(i, (d - von).days) for i, d in spalten]
    # 0.76: Aufenthalte je Person und Kurs fürs Bestandsmodell (Namen werden nicht gespeichert – nur Nummern)
    from . import bestand_kern as bk

    stichtag = stichtag or date.today()
    datum_idx = {i for i, _d in spalten}
    hj_idx = [i for i, v in enumerate(kopf) if i and v not in (None, "") and i not in datum_idx
              and not str(v).strip().lower().startswith("gesamt")]
    sammler = bk.Sammler(von, stichtag)
    summen: dict[str, list[float]] = {}
    dauer: dict[str, list[int]] = {}
    personen = 0
    for z in it:
        if not z or not isinstance(z[0], str):
            continue
        t = z[0].strip()
        if t.lower().startswith("gesamt"):
            break
        sammler.zeile(t, [k for i, k in pos if i < len(z) and z[i]], any(i < len(z) and z[i] for i in hj_idx))
        if not _KURS.match(t):
            continue                                   # Personenzeile – nichts davon wird gelesen
        reihe = summen.setdefault(t, [0.0] * n)
        erste = letzte = None
        for i, k in pos:
            w = z[i] if i < len(z) else None
            if w:
                reihe[k] += float(w)
                erste = k if erste is None else erste
                letzte = k
        if erste is not None:
            personen += 1
            dauer.setdefault(t, []).append(letzte - erste + 1)
    # Lücken (Tage ohne Spalte) je Kurs mit dem letzten bekannten Wert füllen
    bekannt = set(k for _i, k in pos)
    luecken, start = [], None
    for k in range(n):
        if k not in bekannt and start is None:
            start = k
        if k in bekannt and start is not None:
            luecken.append((von + timedelta(days=start), von + timedelta(days=k - 1)))
            start = None
    for reihe in summen.values():
        for k in range(1, n):
            if k not in bekannt:
                reihe[k] = reihe[k - 1]
    kurse = {}
    for kurs, reihe in summen.items():
        nz = [k for k, w in enumerate(reihe) if w]
        if not nz:
            continue
        a, e = nz[0], nz[-1]
        kurse[kurs] = {"von": (von + timedelta(days=a)).isoformat(), "werte": _rle([round(w) for w in reihe[a:e + 1]]),
                       "dauer": int(stt.median(dauer.get(kurs) or [e - a + 1]))}
    sammler.ende()
    bestand = {"aufenthalte": [x.als_liste() for x in sammler.aufenthalte],
               "meta": {"von": von.isoformat(), "bis": bis.isoformat(), "stichtag": stichtag.isoformat(),
                        "halbjahr_spalten": len(hj_idx), "teilsummen": sammler.teilsummen, "langnamen": sammler.langnamen,
                        "nur_halbjahr": sammler.nur_halbjahr, "ohne_person": sammler.ohne_person,
                        "kuenftig_spalten": sum(1 for d in tage if d > stichtag), "kuenftig_tage": sammler.kuenftig_tage,
                        "kuenftig_personen": len(sammler.kuenftig_personen)}}
    return PivotErgebnis(von, bis, kurse, personen, luecken, bestand)


def pivot_lesen(pfad) -> PivotErgebnis:
    import openpyxl

    wb = openpyxl.load_workbook(pfad, read_only=True, data_only=True)
    try:
        return pivot_aus_zeilen(wb.worksheets[0].iter_rows(values_only=True))
    finally:
        wb.close()


def pivot_uebernehmen(erg: PivotErgebnis, datei: str) -> str:
    roh = _roh()
    roh["pivot"] = {"datei": datei, "importiert_am": datetime.now().isoformat(timespec="seconds"),
                    "von": erg.von.isoformat(), "bis": erg.bis.isoformat(), "kurse": erg.kurse, "personen": erg.personen,
                    "luecken": [[a.isoformat(), b.isoformat()] for a, b in erg.luecken]}
    if erg.bestand:
        roh["bestand"] = erg.bestand
        archivieren(roh["pivot"], erg.bestand)
    _schreiben(roh)
    return f"Maßnahmen-Pivot übernommen: {erg.text}"


# 0.86: Jeder eingelesene Stand wird mit Datum abgelegt – nur pseudonyme Aufenthalte (Nummer, Kurs, Daten), keine Namen.
# Erst damit lässt sich später ehrlich prüfen, was die Prognose mit dem damals Bekannten gesagt hätte (Buchungskurve).
ARCHIV_ORDNER = f"{speicher.IMPORT_ORDNER}/massnahmen_archiv"
ARCHIV_MAX = 60


def archivieren(pivot: dict, bestand) -> str | None:
    try:
        tag = datetime.now().date().isoformat()
        name = f"{ARCHIV_ORDNER}/bestand_{tag}.json"
        speicher.schreiben(name, {"pivot": pivot, "bestand": bestand})
        alle = sorted(speicher.pfad(name).parent.glob("bestand_*.json"))
        for alt in alle[:-ARCHIV_MAX]:
            alt.unlink(missing_ok=True)
        return name
    except OSError:                    # Archiv ist Zusatz – das Einlesen selbst darf daran nicht scheitern
        return None


def archiv_staende() -> list[str]:
    """Daten der abgelegten Stände (ISO), älteste zuerst."""
    try:
        return [p.stem.removeprefix("bestand_") for p in sorted(speicher.pfad(f"{ARCHIV_ORDNER}/x").parent.glob("bestand_*.json"))]
    except OSError:
        return []


def pivot_schritt(erg: PivotErgebnis, datei: str) -> str:
    from .kern import _schritt

    out = []
    _schritt("Maßnahmen-Pivot eingelesen", lambda: out.append(pivot_uebernehmen(erg, datei)), [DATEI])
    return out[0]


# ---- Anreiselisten (Word/PDF) → Pendler/Internat je Kurs ----------------------------------------------

def listen_aus_text(text: str) -> dict[str, dict]:
    """Je Kurs: Teilnehmende, Pendler (P), Kostenzusage (K). Nur Zähler – keine Namen."""
    from . import pdf_anreise_kern as pk

    erg: dict[str, dict] = {}
    kurs = None
    for zeile in text.splitlines():
        if m := pk._MASSNAHME.match(zeile):
            kurs = re.sub(r"\s+", " ", m.group(1)).strip()
            continue
        m = pk._PERSON.match(zeile)
        if not m or kurs is None:
            continue
        kz = pk.kennzeichen(m.group(4).split())
        z = erg.setdefault(kurs, {"tn": 0, "pendler": 0, "zusage": 0})
        z["tn"] += 1
        z["pendler"] += "P" in kz
        z["zusage"] += "K" in kz
    return erg


def listen_lesen(pfad) -> dict[str, dict]:
    from . import pdf_anreise_kern as pk

    erg = listen_aus_text(pk.text_lesen(pfad))
    if not erg:
        raise ValueError("Keine Kurse mit Teilnehmenden erkannt – ist das die Liste „Teilnehmer Beginn“ (Word oder PDF)?")
    return erg


def listen_uebernehmen(kurse: dict[str, dict], datei: str) -> str:
    roh = _roh()
    alt = roh.get("listen") or {"kurse": {}, "dateien": []}
    alt["kurse"].update(kurse)                         # gleicher Kurs aus einer neueren Liste ersetzt den alten Stand
    alt["dateien"] = [d for d in alt.get("dateien", []) if d.get("datei") != datei] + [
        {"datei": datei, "kurse": len(kurse), "importiert_am": datetime.now().isoformat(timespec="seconds")}]
    roh["listen"] = alt
    _schreiben(roh)
    tn = sum(k["tn"] for k in kurse.values())
    pe = sum(k["pendler"] for k in kurse.values())
    return f"{len(kurse)} Kurse, {tn} Teilnehmende, davon {pe} Pendler ({round(100 * pe / tn) if tn else 0} %)"


def listen_schritt(kurse: dict[str, dict], datei: str) -> str:
    from .kern import _schritt

    out = []
    _schritt("Anreiselisten für die Maßnahmen-Prognose", lambda: out.append(listen_uebernehmen(kurse, datei)), [DATEI])
    return out[0]


def zuordnung_schritt(fam: str, gruppe: str) -> str:
    from .kern import _schritt

    def aktion():
        roh = _roh()
        roh.setdefault("gruppen", {})[fam] = gruppe
        _schreiben(roh)
    _schritt(f"Maßnahmen-Gruppe: {fam}", aktion, [DATEI])
    return f"{fam} → {GRUPPEN.get(gruppe, gruppe)}"


def plaetze_schritt(fam: str, monat: str, plaetze: int | None) -> str:
    """Geplante Plätze je Art und Startmonat (JJJJ-MM); None = Eintrag entfernen."""
    from .kern import _schritt

    def aktion():
        roh = _roh()
        liste = [p for p in roh.get("plaetze") or [] if not (p["familie"] == fam and p["monat"] == monat)]
        if plaetze:
            liste.append({"familie": fam, "monat": monat, "plaetze": int(plaetze)})
        roh["plaetze"] = sorted(liste, key=lambda p: (p["monat"], p["familie"]))
        _schreiben(roh)
    _schritt(f"Geplante Plätze {fam} {monat}", aktion, [DATEI])
    return f"{fam} {monat}: {plaetze} Plätze" if plaetze else f"{fam} {monat}: Eintrag entfernt"
