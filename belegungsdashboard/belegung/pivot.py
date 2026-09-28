"""Pivot-Quelle einlesen.

Zwei Wege zur selben Werte-Matrix:

* ``lese_matrix_datei`` – liest die in der .xlsx gespeicherten Pivot-Werte direkt mit
  openpyxl. Braucht weder Excel noch Server/VPN, dauert Sekunden und funktioniert auch,
  wenn die Datei gerade in Excel offen ist. Das ist der Normalfall ("Neu laden").
* ``lese_matrix_excel`` – startet Excel per COM, stößt optional den OLAP-Refresh gegen den
  Server an und liest danach die Werte. Nur für "Pivot vom Server aktualisieren".

``parse_matrix`` macht aus der Matrix die Tagesreihen je Standort und Haus; die Logik ist
für beide Wege identisch und ohne Excel testbar.

Wichtig zur Interpretation: Die Pivot enthält Tage weit nach dem Abrufdatum. Das sind
keine Platzhalter, sondern der **gebuchte Bestand** – Teilnehmende mit geplantem Ende der
Maßnahme (die Werte fallen stufenweise, wenn Kohorten auslaufen, und steigen nie). Bis zum
Abrufdatum sind die Werte Ist-Belegung, danach "gesichert laut Planung" ohne künftige
Neuaufnahmen. ``Pivotdaten.stichtag`` markiert diese Grenze.
"""

from __future__ import annotations

import logging
from dataclasses import asdict, dataclass, field
from datetime import date, datetime, timedelta
from pathlib import Path

import pandas as pd

from . import speicher
from .konfig import STANDORTE, standort_normalisieren

log = logging.getLogger(__name__)

EXCEL_EPOCH = datetime(1899, 12, 30)


@dataclass
class PivotProfil:
    """Beschreibt den Aufbau einer Pivot-/Kreuztabellen-Datei.

    sheet_modus:  "auto" = erstes Sheet mit echter PivotTable, "manuell" = fester Sheet-Name.
    ausrichtung:  "standard" = Standorte/Häuser in Spalten, Tage in Zeilen; "transponiert" umgekehrt.
    hierarchie_ebenen: 2 = Standort + Haus, 1 = nur Standort.
    kopfzeilen_marker: Text in der ersten Spalte der letzten Kopfzeile.
    zwischensummen_suffix: Endung von Zwischensummen, die ignoriert werden.
    datumsformat: strptime-Format der Tagesbeschriftungen.
    """

    name: str = "Standard"
    sheet_modus: str = "auto"
    sheet_name: str | None = None
    ausrichtung: str = "standard"
    hierarchie_ebenen: int = 2
    kopfzeilen_marker: str = "Zeilenbeschriftungen"
    zwischensummen_suffix: str = " Ergebnis"
    datumsformat: str = "%d.%m.%Y"

    def to_dict(self) -> dict:
        return asdict(self)

    @staticmethod
    def from_dict(d: dict) -> "PivotProfil":
        std = PivotProfil()
        werte = {k: d.get(k, getattr(std, k)) for k in std.to_dict()}
        werte["hierarchie_ebenen"] = int(werte["hierarchie_ebenen"])
        return PivotProfil(**werte)


def lade_profile(ordner: Path | None = None) -> tuple[dict[str, PivotProfil], dict[str, str]]:
    roh = speicher.lesen(speicher.PIVOT_PROFILE, {}, ordner)
    profile = {n: PivotProfil.from_dict(p) for n, p in roh.get("profile", {}).items()}
    return profile, dict(roh.get("zuordnung", {}))


def speichere_profile(profile: dict[str, PivotProfil], zuordnung: dict[str, str], ordner: Path | None = None) -> None:
    speicher.schreiben(
        speicher.PIVOT_PROFILE,
        {"profile": {n: p.to_dict() for n, p in profile.items()}, "zuordnung": zuordnung},
        ordner,
    )


def profil_fuer_datei(dateiname: str, ordner: Path | None = None) -> PivotProfil:
    profile, zuordnung = lade_profile(ordner)
    name = zuordnung.get(dateiname.lower())
    return profile.get(name, PivotProfil()) if name else PivotProfil()


# ---------------------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------------------

@dataclass
class Pivotdaten:
    reha: pd.DataFrame                  # Index: Tage, Spalten: STANDORTE
    haeuser: pd.DataFrame               # Index: Tage, Spalten: Hausnamen
    haus_standort: dict[str, str]
    abrufdatum: date | None = None      # letzter Pivot-Refresh laut Datei (falls bekannt)
    warnungen: list[str] = field(default_factory=list)

    @property
    def stichtag(self) -> date:
        """Letzter Tag mit Ist-Werten: Abrufdatum der Pivot, höchstens heute."""
        heute = date.today()
        kandidat = min(self.abrufdatum, heute) if self.abrufdatum else heute
        if len(self.reha.index):
            erster = self.reha.index[0].date()
            letzter = self.reha.index[-1].date()
            kandidat = max(erster, min(kandidat, letzter))
        return kandidat


def zelle_zu_datum(wert, datumsformat: str = "%d.%m.%Y") -> date | None:
    """Tagesbeschriftung -> date. Gruppenzeilen ('Jan 2020', '2020') ergeben None."""
    if isinstance(wert, datetime):
        return wert.date()
    if isinstance(wert, date):
        return wert
    if isinstance(wert, (int, float)) and not isinstance(wert, bool):
        # Excel-Seriennummer (COM liefert Datumszellen so). Jahreszahlen wie 2020 ausschließen.
        if 20000 < float(wert) < 80000:
            return (EXCEL_EPOCH + timedelta(days=float(wert))).date()
        return None
    if isinstance(wert, str):
        try:
            return datetime.strptime(wert.strip(), datumsformat).date()
        except ValueError:
            return None
    return None


def _zahl(wert) -> float:
    if wert in (None, ""):
        return 0.0
    try:
        return float(wert)
    except (TypeError, ValueError):
        return 0.0


def parse_matrix(werte: list[list], profil: PivotProfil) -> Pivotdaten:
    """Werte-Matrix (Zeilen x Spalten) -> Pivotdaten. Wirft ValueError mit Klartext."""
    if not werte or not werte[0]:
        raise ValueError("Der Pivot-Bereich ist leer – Sheet bzw. Profil prüfen.")
    werte = [list(z) for z in werte]
    if profil.ausrichtung == "transponiert":
        werte = [list(z) for z in zip(*werte)]

    marker = profil.kopfzeilen_marker.strip()
    idx_marker = next((i for i, z in enumerate(werte) if str(z[0] or "").strip() == marker), None)
    if idx_marker is None:
        raise ValueError(
            f"Kopfzeilen-Markierung '{marker}' nicht gefunden. Stimmen Marker-Text und Ausrichtung?"
        )
    if profil.hierarchie_ebenen == 2:
        if idx_marker == 0:
            raise ValueError("Über der Haus-Kopfzeile fehlt die Standort-Zeile (Hierarchie-Ebenen prüfen).")
        standort_zeile, haus_zeile = werte[idx_marker - 1], werte[idx_marker]
    else:
        standort_zeile = haus_zeile = werte[idx_marker]

    suffix = profil.zwischensummen_suffix
    spalten: list[tuple[int, str, str]] = []
    aktueller: str | None = None
    for c in range(1, len(standort_zeile)):
        s_text = str(standort_zeile[c]).strip() if standort_zeile[c] not in (None, "") else ""
        if s_text:
            if suffix and s_text.endswith(suffix) or s_text.lower().startswith("gesamtergebnis"):
                aktueller = None
                continue
            aktueller = standort_normalisieren(s_text)
        if aktueller is None:
            continue
        if profil.hierarchie_ebenen == 2:
            h_text = str(haus_zeile[c]).strip() if haus_zeile[c] not in (None, "") else ""
            if h_text and not (suffix and h_text.endswith(suffix)):
                spalten.append((c, aktueller, h_text))
        elif s_text:
            spalten.append((c, aktueller, aktueller))

    fehlend = [s for s in STANDORTE if s not in {st for _, st, _ in spalten}]
    if fehlend:
        raise ValueError(
            "Keine Spalten gefunden für: " + ", ".join(fehlend)
            + ". Passt das Profil (Ausrichtung/Hierarchie) zur Datei?"
        )

    tage: list[date] = []
    zeilen: list[list[float]] = []
    for z in werte[idx_marker + 1:]:
        tag = zelle_zu_datum(z[0], profil.datumsformat)
        if tag is None:
            continue
        tage.append(tag)
        zeilen.append([_zahl(z[c]) if c < len(z) else 0.0 for c, _, _ in spalten])
    if not tage:
        raise ValueError(f"Keine Tageszeilen im Format '{profil.datumsformat}' gefunden.")

    roh = pd.DataFrame(zeilen, index=pd.DatetimeIndex(tage), columns=range(len(spalten)))
    roh = roh.groupby(level=0).sum().sort_index()
    voll = pd.date_range(roh.index[0], roh.index[-1], freq="D")
    warnungen = []
    if len(voll) != len(roh.index):
        warnungen.append(f"{len(voll) - len(roh.index)} Tage fehlen in der Pivot und werden als 0 gewertet.")
    roh = roh.reindex(voll, fill_value=0.0)

    haeuser = pd.DataFrame(index=voll)
    haus_standort: dict[str, str] = {}
    for i, (_, standort, haus) in enumerate(spalten):
        haeuser[haus] = haeuser.get(haus, 0.0) + roh[i]
        haus_standort[haus] = standort
    reha = pd.DataFrame(
        {s: sum((roh[i] for i, (_, st, _) in enumerate(spalten) if st == s), pd.Series(0.0, index=voll))
         for s in STANDORTE}
    )
    return Pivotdaten(reha=reha, haeuser=haeuser, haus_standort=haus_standort, warnungen=warnungen)


def vorschau(werte: list[list], profil: PivotProfil) -> dict:
    """Trockenlauf für den Profil-Dialog."""
    try:
        d = parse_matrix(werte, profil)
    except ValueError as exc:
        return {"erfolg": False, "fehler": str(exc)}
    return {
        "erfolg": True,
        "erster_tag": d.reha.index[0].date(),
        "letzter_tag": d.reha.index[-1].date(),
        "anzahl_tage": len(d.reha.index),
        "haeuser_je_standort": {
            s: sorted(h for h, st in d.haus_standort.items() if st == s) for s in STANDORTE
        },
    }


# ---------------------------------------------------------------------------------------
# Lesen per openpyxl (ohne Excel)
# ---------------------------------------------------------------------------------------

def sheet_namen_datei(pfad: Path) -> list[str]:
    import openpyxl
    wb = openpyxl.load_workbook(pfad, read_only=True)
    try:
        return list(wb.sheetnames)
    finally:
        wb.close()


def lese_matrix_datei(pfad: Path, profil: PivotProfil) -> tuple[list[list], date | None]:
    """(Werte-Matrix, Abrufdatum der Pivot) aus den in der Datei gespeicherten Werten."""
    import openpyxl
    from openpyxl.utils.cell import range_boundaries

    wb = openpyxl.load_workbook(pfad, data_only=True)
    abrufdatum = None
    if profil.sheet_modus == "manuell" and profil.sheet_name:
        if profil.sheet_name not in wb.sheetnames:
            raise ValueError(f"Sheet '{profil.sheet_name}' fehlt. Vorhanden: {', '.join(wb.sheetnames)}")
        ws = wb[profil.sheet_name]
        pivots = getattr(ws, "_pivots", [])
    else:
        ws = next((w for w in wb.worksheets if getattr(w, "_pivots", [])), None)
        if ws is None:
            raise ValueError(
                "Keine Pivot-Tabelle in der Datei gefunden. Bei einer Kreuztabelle im "
                "Pivot-Profil den Sheet-Modus auf 'manuell' stellen."
            )
        pivots = ws._pivots

    if pivots:
        pv = pivots[0]
        min_c, min_r, max_c, max_r = range_boundaries(pv.location.ref)
        matrix = [list(z) for z in ws.iter_rows(min_row=min_r, max_row=max_r, min_col=min_c,
                                                 max_col=max_c, values_only=True)]
        seriell = getattr(pv.cache, "refreshedDate", None)
        if seriell:
            abrufdatum = (EXCEL_EPOCH + timedelta(days=float(seriell))).date()
    else:
        matrix = [list(z) for z in ws.iter_rows(values_only=True)]
    return matrix, abrufdatum


def lese_datei(pfad: Path, profil: PivotProfil | None = None) -> Pivotdaten:
    profil = profil or profil_fuer_datei(pfad.name)
    matrix, abrufdatum = lese_matrix_datei(pfad, profil)
    daten = parse_matrix(matrix, profil)
    daten.abrufdatum = abrufdatum
    return daten


# ---------------------------------------------------------------------------------------
# Lesen per Excel-COM (nur Windows, optional mit OLAP-Refresh)
# ---------------------------------------------------------------------------------------

def datei_gesperrt(pfad: Path) -> bool:
    if (pfad.parent / f"~${pfad.name}").exists():
        return True
    try:
        with open(pfad, "r+b"):
            return False
    except PermissionError:
        return True
    except OSError:
        return False


def lese_excel(pfad: Path, profil: PivotProfil | None = None, refresh: bool = True) -> tuple[Pivotdaten, bool]:
    """Öffnet die Datei in einer unsichtbaren Excel-Instanz (schreibgeschützt), aktualisiert
    optional die OLAP-Pivot und liest die Werte. Gibt (Daten, refresh_erfolgreich) zurück.
    Muss in einem eigenen Thread mit CoInitialize laufen (siehe UI-Worker)."""
    import pywintypes
    import win32com.client as win32

    profil = profil or profil_fuer_datei(pfad.name)
    if datei_gesperrt(pfad):
        raise RuntimeError(f"'{pfad.name}' ist in einem anderen Programm geöffnet. Bitte dort schließen.")

    excel = win32.DispatchEx("Excel.Application")
    excel.Visible = False
    excel.DisplayAlerts = False
    excel.AskToUpdateLinks = False
    wb = None
    try:
        wb = excel.Workbooks.Open(str(pfad), UpdateLinks=0, ReadOnly=True)
        if profil.sheet_modus == "manuell" and profil.sheet_name:
            ws = wb.Worksheets(profil.sheet_name)
        else:
            ws = next((w for w in wb.Worksheets if w.PivotTables().Count > 0), None)
            if ws is None:
                raise ValueError("Keine Pivot-Tabelle in der Datei gefunden.")
        erfolgreich = True
        if ws.PivotTables().Count > 0:
            pt = ws.PivotTables(1)
            if refresh:
                try:
                    pt.PivotCache().Refresh()
                except pywintypes.com_error as exc:
                    log.warning("Pivot-Refresh fehlgeschlagen (%s) – verwende gespeicherten Stand.", exc)
                    erfolgreich = False
            matrix = pt.TableRange1.Value2
        else:
            matrix = ws.UsedRange.Value2
        daten = parse_matrix([list(z) for z in matrix], profil)
        daten.abrufdatum = date.today() if (refresh and erfolgreich) else None
        return daten, erfolgreich
    finally:
        if wb is not None:
            wb.Close(SaveChanges=False)
        excel.Quit()
