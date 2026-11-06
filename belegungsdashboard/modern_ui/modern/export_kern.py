"""Exportieren (0.73) wie „Datei → Exportieren“ in Office. Rein bis auf das Schreiben der Datei.

* **Tabellen dieser Ansicht → Excel:** Die Oberfläche liest die gerade angezeigten Tabellen (so wie gefiltert) aus und
  gibt sie als Liste von {titel, kopf, zeilen} herein – damit hat JEDE Seite mit Tabelle einen Excel-Export.
* **Zwischenablage:** dieselben Tabellen tabulatorgetrennt (in Excel mit Strg+V einfügen).
* **Fertige Exporte der Seite** (gestaltete Excel-Listen, die es schon gibt) – Katalog ``FERTIG``.
* **PDF:** über den Druckdialog („Als PDF speichern“) – siehe Drucken.
"""

from __future__ import annotations

import re
from datetime import date
from pathlib import Path

# (Seite, Ansicht) → [(Text, Schlüssel)] – die Oberfläche ruft dazu die vorhandenen Funktionen auf
FERTIG = {
    ("anreisen", "zuteilen"): [("Anreise als Excel (gestaltet)", "anreise_excel")],
    ("zimmer", "uebersicht"): [("Zimmer mit „frei bis“", "kachel_excel"), ("Zimmer ohne Namen", "kachel_excel_ohne"),
                               ("Belegung am Tag", "belegung_excel")],
    ("zimmer", "liste"): [("Auswahl mit „frei bis“", "auswahl_excel"), ("Auswahl ohne Namen", "auswahl_excel_ohne"),
                          ("Belegung am Tag", "belegung_excel")],
    ("zimmer", "karten"): [("Auswahl mit „frei bis“", "auswahl_excel"), ("Belegung am Tag", "belegung_excel")],
    ("zimmer", "maengel"): [("Mängelliste für den FM", "fm_excel")],
    ("zimmer", "aenderungen"): [("Änderungen im Zeitraum", "aenderungen_excel")],
    ("inventar", "gegenstaende"): [("Inventarliste", "inventar_excel")],
    ("inventar", "zimmer"): [("Inventarliste", "inventar_excel")],
    ("inventar", "haeuser"): [("Inventarliste", "inventar_excel")],
}


def fertige(seite: str, ansicht: str | None) -> list[tuple[str, str]]:
    return FERTIG.get((seite, ansicht or ""), [])


_ZAHL = re.compile(r"^-?\d{1,3}(\.\d{3})*(,\d+)?$|^-?\d+(,\d+)?$")


def wert(text: str):
    """Zahlen wie in Excel (1.234,5 → 1234.5), sonst Text. Datumsangaben bleiben Text (wie angezeigt)."""
    t = (text or "").strip()
    if _ZAHL.match(t):
        z = t.replace(".", "").replace(",", ".")
        return float(z) if "." in z else int(z)
    return t


def bereinigen(roh: list[dict]) -> list[dict]:
    """Leere Tabellen weg, Zellen säubern (Zeilenumbrüche → „ · “), Zeilen auf Kopfbreite bringen."""
    erg = []
    for t in roh or []:
        kopf = [" ".join(str(k).split()) for k in (t.get("kopf") or [])]
        zeilen = [[" · ".join(x.strip() for x in str(z).splitlines() if x.strip()) for z in zeile]
                  for zeile in (t.get("zeilen") or []) if any(str(z).strip() for z in zeile)]
        if not zeilen:
            continue
        breite = max([len(kopf)] + [len(z) for z in zeilen])
        kopf = (kopf + [""] * breite)[:breite]
        if not any(kopf):
            kopf = [f"Spalte {i + 1}" for i in range(breite)]
        zeilen = [(z + [""] * breite)[:breite] for z in zeilen]
        # Spalten, die überall leer sind (Ampel-Punkte, Symbole), entfallen
        voll = [i for i in range(breite) if kopf[i] or any(z[i] for z in zeilen)]
        erg.append({"titel": " ".join(str(t.get("titel") or "").split()) or "Tabelle",
                    "kopf": [kopf[i] for i in voll], "zeilen": [[z[i] for i in voll] for z in zeilen]})
    return erg


def tsv(tabellen: list[dict]) -> str:
    teile = []
    for t in tabellen:
        zeilen = [t["kopf"]] + t["zeilen"]
        teile.append("\n".join("\t".join(str(c).replace("\t", " ") for c in z) for z in zeilen))
    return "\n\n".join(teile)


def dateiname(titel: str, tag: date) -> str:
    sauber = re.sub(r"[^\w\-]+", "_", titel.replace("·", "-").replace("&", "und"), flags=re.UNICODE).strip("_")
    return f"{sauber or 'Export'}_{tag:%Y-%m-%d}.xlsx"


def blattname(titel: str, schon: set) -> str:
    n = re.sub(r"[\[\]\*\?/\\:]", "", titel)[:28] or "Tabelle"
    k, i = n, 2
    while k in schon:
        k, i = f"{n[:25]} {i}", i + 1
    schon.add(k)
    return k


def excel_schreiben(tabellen: list[dict], titel: str, pfad: Path) -> int:
    """Je Tabelle ein Blatt: fette Kopfzeile, Filter, fixierte Kopfzeile, passende Spaltenbreiten. → Anzahl Zeilen."""
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill

    wb = Workbook()
    wb.remove(wb.active)
    namen: set = set()
    n = 0
    for t in tabellen:
        ws = wb.create_sheet(blattname(t["titel"] if len(tabellen) > 1 else titel, namen))
        ws.append(t["kopf"])
        for z in t["zeilen"]:
            ws.append([wert(c) for c in z])
            n += 1
        for c in ws[1]:
            c.font = Font(bold=True)
            c.fill = PatternFill("solid", fgColor="E6EEEE")
        ws.freeze_panes = "A2"
        ws.auto_filter.ref = ws.dimensions
        for i, spalte in enumerate(zip(*([t["kopf"]] + t["zeilen"])), 1):
            ws.column_dimensions[ws.cell(1, i).column_letter].width = min(60, max(8, max(len(str(x)) for x in spalte) + 2))
    pfad.parent.mkdir(parents=True, exist_ok=True)
    wb.save(pfad)
    return n


def speichern(tabellen: list[dict], titel: str, tag: date) -> tuple[str, Path]:
    """In den Export-Ordner (wie die übrigen Excel-Listen) – Text für die Meldung und Pfad."""
    from belegung import speicher

    ziel = Path(speicher.einstellungen().get("export_ordner") or speicher.pfad("Export"))
    pfad = ziel / dateiname(titel, tag)
    n = excel_schreiben(tabellen, titel, pfad)
    return f"Excel gespeichert: {pfad.name} ({n} Zeilen)", pfad


# JavaScript, das die angezeigten Tabellen der Arbeitsfläche ausliest (HTML-Tabellen und die Zeilen-Raster der
# Seiten). Entfernt werden vorher: Aktionsknöpfe (Knöpfe mit Symbol – z. B. ein noch NICHT übernommener Zimmervorschlag
# darf nicht als Zimmer exportiert werden), Symbole (sonst stünde „check_circle“ in der Zelle) und Häkchen-Felder.
# Gemessen wird an einer versteckten Kopie IM Dokument – nur dort liefert innerText die Zeilenumbrüche.
LESEN_JS = r"""
(() => {
  const orig = document.querySelector('.m-inhalt'); if (!orig) return [];
  const titel = (document.querySelector('.m-kopf .m-titel')?.innerText || 'Tabelle').trim();
  // EINE Kopie der Arbeitsfläche, einmal gesäubert, außerhalb des Bildschirms (innerText braucht ein Layout)
  const ber = orig.cloneNode(true);
  ber.style.cssText = `position:fixed;left:-20000px;top:0;width:${orig.clientWidth}px;opacity:0;pointer-events:none`;
  ber.querySelectorAll('button.m-knopf').forEach(x => { if (x.querySelector('.q-icon')) x.remove(); });
  ber.querySelectorAll('i.q-icon, .material-icons, .q-icon').forEach(x => x.remove());
  ber.querySelectorAll('input[type=checkbox], input[type=radio], .q-checkbox, .q-toggle').forEach(x => x.remove());
  ber.querySelectorAll('input, select, textarea').forEach(x => x.replaceWith(document.createTextNode(x.value || '')));
  document.body.appendChild(ber);
  const text = (el) => (el.innerText || '').trim();
  const sichtbar = (el) => !!(el.offsetWidth || el.offsetHeight || el.getClientRects().length);
  const out = [];
  try {
    ber.querySelectorAll('table').forEach(tb => { if (!sichtbar(tb)) return;
      const reihen = [...tb.querySelectorAll('tr')].filter(sichtbar);
      if (reihen.length < 2) return;
      out.push({ titel: tb.closest('section')?.querySelector('.m-btitel')?.innerText || titel,
                 kopf: [...reihen[0].children].map(text), zeilen: reihen.slice(1).map(r => [...r.children].map(text)) }); });
    ber.querySelectorAll('.m-tkopf').forEach(k => { if (!sichtbar(k)) return;
      const zeilen = []; let s = k.nextElementSibling;
      while (s) { if (s.classList.contains('m-zeile') && sichtbar(s)) zeilen.push([...s.children].map(text));
                  else if (s.classList.contains('m-tkopf')) break; s = s.nextElementSibling; }
      if (zeilen.length) out.push({ titel: k.closest('section')?.querySelector('.m-btitel')?.innerText || titel,
                                    kopf: [...k.children].map(text), zeilen }); });
  } finally { ber.remove(); }
  return out;
})()
"""
