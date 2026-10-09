"""Reinigungsliste je Woche: je Zimmer das Auszugsdatum und „sauber bis spätestens“ (ein Tag vor der nächsten
Anreise), sortiert nach dieser Frist – zum Drucken (HTML/PDF) oder als Excel. „Vorbereiten“ nur für Zimmer,
die vorher leer standen. Rein, ohne Qt; die Daten kommen aus ``zimmerplan.reinigungen``."""

from __future__ import annotations

import html
from datetime import date, timedelta
from pathlib import Path

from . import speicher
from . import zimmerplan as zp

DATEI = "reinigung_erledigt.json"

WOCHENTAGE = ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"]
WT_KURZ = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]


def woche(d: date) -> tuple[date, date]:
    start = d - timedelta(days=d.weekday())
    return start, start + timedelta(days=6)


def titel(von: date, bis: date) -> str:
    return f"Reinigungsliste KW {von.isocalendar()[1]} · {von:%d.%m.} – {bis:%d.%m.%Y}"


def wer_text(belegungen: list, namen: bool) -> str:
    teile = []
    for b in belegungen:
        if b.name == zp.PIVOT_NAME:
            teile.append("belegt laut Zimmer-Pivot")
        elif namen:
            teile.append(b.name + (f" ({b.massnahme})" if b.massnahme else ""))
        else:
            g = zp.belegung_gruppe(b)
            teile.append(b.massnahme or zp.GRUPPE_LABEL.get(g, g or ""))
    # gleiche Einträge zusammenfassen (Doppelzimmer derselben Klasse): „2× GS UWT CUK25“
    gezaehlt: dict[str, int] = {}
    for t in teile:
        if t:
            gezaehlt[t] = gezaehlt.get(t, 0) + 1
    return ", ".join(f"{n}× {t}" if n > 1 else t for t, n in gezaehlt.items()) or "–"


def auszug_text(r: zp.Reinigung, namen: bool) -> str:
    if r.auszug:
        return wer_text(r.auszug, namen)
    return f"– leer seit {r.leer_seit:%d.%m.}" if r.leer_seit else "– stand leer"


def _tag_kurz(d: date) -> str:
    return f"{WT_KURZ[d.weekday()]} {d:%d.%m.}"


def einzug_text(r: zp.Reinigung, namen: bool) -> str:
    """Bis wann das Zimmer fertig sein muss und für wen – sonst „danach frei“."""
    if not r.einzug:
        return "danach frei"
    text = f"{_tag_kurz(r.anreise)}: {wer_text(r.einzug, namen)}"
    if r.anreise == r.tag:
        text += " – gleicher Tag!"
    elif r.eilig:
        text += " – eilig"
    return text


def auszug_datum(r: zp.Reinigung) -> str:
    """„Mi 21.10.“ (Doppelzimmer: „Mi 21.10. (1 Bett)“) – ohne Auszug: seit wann das Zimmer leer ist."""
    if r.auszug:
        return _tag_kurz(r.tag) + (" (1 Bett)" if r.bleibt else "")
    return f"– leer seit {r.leer_seit:%d.%m.}" if r.leer_seit else "– stand leer"


def frist_text(r: zp.Reinigung) -> str:
    """„Fr 23.10.“ – sauber bis spätestens (letzter Werktag vor der nächsten Anreise)."""
    f = r.frist
    if f is None:
        return "– (keine Anreise geplant)"
    if not zp.werktag(f):
        return f"{_tag_kurz(f)} – Wochenende! Sonderreinigung vor Anreise {_tag_kurz(r.naechste_anreise)}"
    if r.auszug and f <= r.tag:
        if r.naechste_anreise <= r.tag + timedelta(days=1):
            return f"{_tag_kurz(f)} – sofort nach Auszug"
        return f"{_tag_kurz(f)} – noch am Auszugstag (Wochenende)"
    if f >= r.naechste_anreise:
        return f"{_tag_kurz(f)} – am Anreisetag vor der Anreise"
    return _tag_kurz(f)


def facility(r: zp.Reinigung, tage: int | None = None) -> bool:
    """Auszug nach langem Aufenthalt → Facility-Check (Elektrik prüfen, Fensterwartung)."""
    from . import eintragen

    if not r.auszug:
        return False
    tage = tage or eintragen.facility_tage()
    # Pivot-Fortsetzungen sind schon herausgefiltert (kein echter Auszug) – daher ohne Nachbarn prüfen
    return any(eintragen.lange_belegung(b, [], tage) for b in r.auszug)


def details(r: zp.Reinigung, namen: bool = True) -> str:
    """Für den Tooltip: wer auszieht, wer danach kommt."""
    teile = []
    if r.auszug:
        teile.append(f"Auszug {_tag_kurz(r.tag)}: {wer_text(r.auszug, namen)}" + (" – Mitbewohner bleibt" if r.bleibt else ""))
    if r.einzug:
        teile.append(f"Nächste Anreise {_tag_kurz(r.anreise)}: {wer_text(r.einzug, namen)}")
    return "\n".join(teile) or "danach frei"


def zeilen(rs: list[zp.Reinigung], namen: bool = False) -> list[list[str]]:
    """Tabellenzeilen: Zimmer, Lage, Betten, Auszug, Sauber bis spätestens."""
    return [[r.zimmer.kurz, zp.flur_text(r.zimmer), str(r.zimmer.betten), auszug_datum(r), frist_text(r)] for r in rs]


def zaehlung(rs: list[zp.Reinigung]) -> str:
    mit = sum(1 for r in rs if r.frist is not None)
    vor = sum(1 for r in rs if not r.auszug)
    teile = [f"{len(rs)} Zimmer", f"{mit} mit Frist (Anreise danach)"]
    if vor:
        teile.append(f"{vor} davon standen leer")
    return " · ".join(teile)


def nach_tagen(rs: list[zp.Reinigung]) -> list[tuple[date, list[zp.Reinigung]]]:
    tage: dict[date, list[zp.Reinigung]] = {}
    for r in rs:
        tage.setdefault(r.tag, []).append(r)
    return sorted(tage.items())


# ---------------------------------------------------------------------------------------
# Erledigt abhaken, Priorität, Konflikte mit Anreisen
# ---------------------------------------------------------------------------------------

def schluessel(r: zp.Reinigung) -> str:
    return f"{r.zimmer.id}|{r.tag.isoformat()}"


def _roh() -> dict:
    roh = speicher.lesen(DATEI, {})
    roh.setdefault("erledigt", {})
    roh.setdefault("gemeldet", {})
    roh.setdefault("offen", [])        # vor dem Start liegende Reinigungen, die bewusst wieder offen sind
    if "seit" not in roh:
        # Beim ersten Mal: alles davor gilt als erledigt – sonst meldet die Liste Wochen alter Reinigungen
        roh["seit"] = date.today().isoformat()
        speicher.schreiben(DATEI, roh)
    return roh


def erledigt() -> dict[str, str]:
    """Schlüssel -> Zeitpunkt, wann abgehakt wurde (plus ``__seit__``: ab wann abgehakt wird)."""
    roh = _roh()
    return {**roh["erledigt"], "__seit__": roh["seit"], **{"!" + k: "offen" for k in roh["offen"]}}


def erledigt_setzen(r: zp.Reinigung, an: bool = True) -> None:
    from datetime import datetime

    roh = _roh()
    k = schluessel(r)
    if an:
        roh["erledigt"][k] = datetime.now().isoformat(timespec="minutes")
        roh["offen"] = [x for x in roh["offen"] if x != k]
    else:
        roh["erledigt"].pop(k, None)
        if r.tag.isoformat() < roh["seit"] and k not in roh["offen"]:
            roh["offen"].append(k)     # automatisches Häkchen (vor dem Start) bewusst zurückgenommen
    # alte Häkchen (älter als 120 Tage) aufräumen
    grenze = (date.today() - timedelta(days=120)).isoformat()
    roh["erledigt"] = {k: v for k, v in roh["erledigt"].items() if "|" in k and k.split("|")[1] >= grenze}
    roh["offen"] = [k for k in roh["offen"] if k.split("|")[1] >= grenze]
    speicher.schreiben(DATEI, roh)


# Priorität: 0 = Anreise heute und nicht gereinigt … 9 = erledigt
PRIO_TEXT = {0: "SOFORT – Anreise heute", 1: "heute fertig machen", 2: "überfällig", 3: "bald",
             4: "nicht abgehakt", 5: "normal", 9: "erledigt"}


def prioritaet(r: zp.Reinigung, heute: date, fertig: dict | set) -> int:
    if schluessel(r) in fertig:
        return 9
    seit = fertig.get("__seit__") if isinstance(fertig, dict) else None
    if seit and r.tag.isoformat() < seit and ("!" + schluessel(r)) not in fertig:
        return 9                       # vor dem ersten Abhaken – gilt als erledigt (lässt sich zurücknehmen)
    anreise, frist = r.naechste_anreise, r.frist
    if anreise is not None and anreise < heute and r.tag < heute:
        return 4                       # Anreise schon vorbei – nur noch nicht abgehakt
    if anreise is not None and anreise == heute:
        return 0
    if frist is not None and frist <= heute:
        return 1                       # heute ist der letzte Reinigungstag vor der Anreise (Fr für Mo-Anreise)
    if r.tag < heute and frist is None:
        return 2                       # Auszug vorbei, keine Anreise danach – liegt noch an
    if frist is not None and (frist - heute).days <= 3:
        return 3
    return 5


def prio_text(r: zp.Reinigung, heute: date, fertig: dict | set) -> str:
    p = prioritaet(r, heute, fertig)
    if p == 3 and r.frist:
        tage = (r.frist - heute).days
        return "bis morgen" if tage == 1 else f"noch {tage} Tage"
    if p == 2:
        return f"überfällig seit {r.tag:%d.%m.}"
    if p == 4 and r.naechste_anreise:
        return f"nicht abgehakt (Anreise war {r.naechste_anreise:%d.%m.})"
    return PRIO_TEXT[p]


def konflikte(rs: list[zp.Reinigung], heute: date, fertig: dict | set) -> list[zp.Reinigung]:
    """Nicht erledigte Reinigungen, obwohl heute oder morgen jemand ins Zimmer kommt (bzw. schon da ist)."""
    return sorted((r for r in rs if prioritaet(r, heute, fertig) <= 1 and r.tag <= heute + timedelta(days=1)),
                  key=lambda r: (prioritaet(r, heute, fertig), r.naechste_anreise, r.zimmer.id))


def konflikt_text(r: zp.Reinigung) -> str:
    d = r.naechste_anreise
    return (f"Zimmer {r.zimmer.haus}-{r.zimmer.nr}: {r.art} vom {r.tag:%d.%m.} noch nicht erledigt – "
            f"Anreise {_tag_kurz(d)}")


def sortiert(rs: list[zp.Reinigung], heute: date, fertig: dict | set) -> list[zp.Reinigung]:
    """Nach Frist (sauber bis spätestens) – ohne Frist ans Ende –, dann nach Haus und Zimmernummer."""
    return sorted(rs, key=lambda r: (prioritaet(r, heute, fertig) == 9, r.frist is None, r.frist or r.tag,
                                     zp._haus_sort(r.zimmer.haus), r.zimmer.nummer))


def zu_melden(rs: list[zp.Reinigung], heute: date) -> list[zp.Reinigung]:
    """Konflikte, die heute noch nicht gemeldet wurden (Windows-Benachrichtigung einmal am Tag je Zimmer)."""
    roh = _roh()
    return [r for r in konflikte(rs, heute, roh["erledigt"]) if roh["gemeldet"].get(schluessel(r)) != heute.isoformat()]


def gemeldet_setzen(rs: list[zp.Reinigung], heute: date) -> None:
    roh = _roh()
    for r in rs:
        roh["gemeldet"][schluessel(r)] = heute.isoformat()
    grenze = (heute - timedelta(days=30)).isoformat()
    roh["gemeldet"] = {k: v for k, v in roh["gemeldet"].items() if v >= grenze}
    speicher.schreiben(DATEI, roh)


def html_text(rs: list[zp.Reinigung], von: date, bis: date, namen: bool = False, stand: str = "",
              ohne_zimmer: int = 0, heute: date | None = None, fertig: dict | set | None = None) -> str:
    """Druckfertiges HTML: eine Tabelle nach Frist – Zimmer, Auszug, sauber bis spätestens, Abhakkästchen."""
    e = html.escape
    # Hinweis: Qt druckt HTML mit eingeschränktem CSS – Breiten und Abstände deshalb als Tabellen-Attribute
    heute = heute or date.today()
    fertig = fertig or {}
    breiten = (5, 10, 18, 7, 18, 20, 22)      # %: ☐, Zimmer, Lage, Betten, Auszug, Sauber bis, Notiz
    kopf = ("", "Zimmer", "Lage", "Betten", "Auszug", "Sauber bis spätestens", "Notiz")
    teile = [
        "<html><head><meta charset='utf-8'><style>",
        "body { font-family: 'Segoe UI', Arial, sans-serif; font-size: 10pt; color: #111; }",
        "h1 { font-size: 14pt; margin: 0; } .sub { color: #555; }",
        "th { text-align: left; font-size: 8.5pt; color: #333; background-color: #e9ecf0; }",
        ".eilig { font-weight: bold; }",
        "</style></head><body>",
        f"<h1>{e(titel(von, bis))}</h1>",
        f"<div class='sub'>{zaehlung(rs)}" + (f" · Gebäudeplan-Stand {e(stand)}" if stand else "")
        + " · sauber bis spätestens = letzter Werktag vor der nächsten Anreise (Sa/So wird nicht gereinigt)"
        " · ☐ nach der Reinigung abhaken</div><br>",
    ]
    if ohne_zimmer:
        teile.append(f"<p><b>Achtung:</b> {ohne_zimmer} Anreise(n) haben noch kein Zimmer – sie fehlen auf "
                     "dieser Liste.</p>")
    if not rs:
        teile.append("<p>In dieser Woche zieht niemand aus und kein leeres Zimmer muss vorbereitet werden.</p>")
    else:
        teile.append("<table width='100%' cellspacing='0' cellpadding='5' border='1' "
                     "style='border-collapse: collapse; border-color: #b8bec6;'><tr>"
                     + "".join(f"<th width='{b}%'>{k}</th>" for b, k in zip(breiten, kopf)) + "</tr>")
        for r, z in zip(sortiert(rs, heute, fertig), zeilen(sortiert(rs, heute, fertig))):
            p = prioritaet(r, heute, fertig)
            klasse = " class='eilig'" if p <= 1 or r.knapp else \
                " style='color: #888;'" if p == 9 else ""
            haken = "☑" if p == 9 else "☐"
            notiz = "Facility: Elektrik, Fenster" if facility(r) else ""
            teile.append(f"<tr{klasse}><td align='center' style='font-size: 12pt;'>{haken}</td>"
                         + "".join(f"<td>{e(x)}</td>" for x in z) + f"<td>{e(notiz)}</td></tr>")
        teile.append("</table>")
    teile.append("</body></html>")
    return "\n".join(teile)


def excel_speichern(pfad: Path, rs: list[zp.Reinigung], von: date, bis: date, namen: bool = False) -> Path:
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font, PatternFill

    wb = Workbook()
    ws = wb.active
    ws.title = f"KW {von.isocalendar()[1]}"
    ws.append([titel(von, bis)])
    ws["A1"].font = Font(bold=True, size=14)
    ws.append([])
    kopf = ["Erledigt", "Zimmer", "Lage", "Betten", "Auszug", "Sauber bis spätestens", "Notiz"]
    ws.append(kopf)
    for c in ws[3]:
        c.font = Font(bold=True)
        c.fill = PatternFill("solid", fgColor="E6EAF0")
    rs = sortiert(rs, date.today(), {})
    for r, z in zip(rs, zeilen(rs)):
        ws.append(["☐"] + z[:2] + [int(z[2])] + z[3:] + [""])
        if r.knapp:
            for c in ws[ws.max_row]:
                c.font = Font(bold=True)
    for spalte, breite in zip("ABCDEFG", (9, 10, 20, 7, 18, 30, 30)):
        ws.column_dimensions[spalte].width = breite
    for zeile in ws.iter_rows(min_row=4):
        for c in zeile:
            c.alignment = Alignment(vertical="top", wrap_text=True)
    ws.freeze_panes = "A4"
    ws.print_title_rows = "3:3"
    ws.page_setup.orientation = "landscape"
    ws.page_setup.fitToWidth = 1
    ws.page_setup.fitToHeight = 0
    ws.sheet_properties.pageSetUpPr.fitToPage = True
    pfad = Path(pfad)
    wb.save(pfad)
    return pfad
