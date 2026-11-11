"""Notfallliste (0.89) – wer ist laut Plan JETZT im Haus? Je Haus und Etage, zum Ausdrucken (Evakuierung, Feuerwehr,
Sammelplatz). Rein (ohne Oberfläche), damit testbar.

Grundlage ist dieselbe Belegung wie in „Zimmer & Haus“ (Gebäudeplan + Zimmerplan) am Stichtag:

* belegt laut Gebäudeplan → Person im Haus,
* nur geplant (Zimmerplan) → mit „geplant“ markiert – Anreise heute ist möglich, aber nicht sicher,
* Sperrung wegen Mieter → „Mieter“ (Name steht im Mietvertrag, nicht im Gebäudeplan),
* „belegt laut Zimmer-Pivot“ ohne Namen → „belegt, Name unbekannt“ (zählt trotzdem als Person).

Gäste, Besucher, Personal und Abreisen/Anreisen im Laufe des Tages kennt das Programm nicht – das steht auf dem Blatt.
Die Liste wird nur erzeugt und gedruckt, nicht gespeichert (Datenschutz: Namen bleiben im Plan)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from html import escape

from belegung import zimmerliste as zl
from belegung import zimmerplan as zp


@dataclass
class NZeile:
    haus: str
    etage: str
    zimmer: str           # Kurzbezeichnung, z. B. „2-114“
    name: str
    gruppe: str           # Maßnahme / Gruppe
    bis: date | None      # Abreise laut Plan
    art: str              # im_haus | geplant | mieter | unbekannt
    hinweis: str          # Hinweis zum Zimmer (Notiz) und Merkmale


ART_TEXT = {"im_haus": "", "geplant": "geplant – Anreise prüfen", "mieter": "Mieter", "unbekannt": "Name unbekannt"}


def zeilen(stand: zp.Planstand, tag: date, haus: str = "") -> list[NZeile]:
    """Alle Personen im Haus am Tag, sortiert nach Haus, Etage, Zimmer."""
    f = zl.Filter(nur_internat=True, haus=haus) if haus else zl.Filter(nur_internat=True)
    erg: list[NZeile] = []
    for r in sorted(zl.filtern(stand, f, tag), key=lambda r: (zp._haus_sort(r.zimmer.haus), zp._etage_sort(r.zimmer.etage),
                                                               r.zimmer.nummer, r.zimmer.nr)):
        z = r.zimmer
        etage = zp.etage_text(z.etage) + (f" {z.flur}" if z.flur else "")
        hinweis = " · ".join(t for t in (z.notiz.strip(), zl.merkmal_kurz(z)) if t)
        for b in r.belegungen:
            if b.art == "gesperrt" and "mieter" in (b.grund or "").lower():
                erg.append(NZeile(z.haus, etage, z.kurz, "Mieter (Name im Mietvertrag)", "Mieter", b.bis, "mieter", hinweis))
            elif b.art in ("belegt", "geplant"):
                unbekannt = not b.name or b.name == zp.PIVOT_NAME or zp.name_fehlt(b.name)
                art = "unbekannt" if unbekannt else ("geplant" if b.art == "geplant" else "im_haus")
                if (b.massnahme or "").lower().startswith("mieter") and art == "im_haus":
                    art = "mieter"
                erg.append(NZeile(z.haus, etage, z.kurz, "belegt, Name unbekannt" if unbekannt else zp.anzeige_name(b.name),
                                  zp.GRUPPE_LABEL.get(b.massnahme, b.massnahme or ""), b.bis, art, hinweis))
    return erg


def zaehlen(zs: list[NZeile]) -> dict[str, dict[str, int]]:
    """Je Haus: Personen sicher im Haus, geplant (unsicher), Zimmer mit Personen."""
    erg: dict[str, dict[str, int]] = {}
    for z in zs:
        h = erg.setdefault(z.haus, {"personen": 0, "geplant": 0, "zimmer": 0})
        h["geplant" if z.art == "geplant" else "personen"] += 1
    for haus, h in erg.items():
        h["zimmer"] = len({z.zimmer for z in zs if z.haus == haus})
    return erg


def druck_html(zs: list[NZeile], jetzt: datetime, standort: str = "", haus: str = "") -> str:
    """Druckblatt: je Haus eine Tabelle (neue Seite je Haus), mit Abhak-Spalte für den Sammelplatz."""
    n = zaehlen(zs)
    sicher = sum(h["personen"] for h in n.values())
    geplant = sum(h["geplant"] for h in n.values())
    ort = f"{standort} · " if standort else ""
    teile = ["<!doctype html><meta charset='utf-8'><title>Notfallliste</title><style>"
             "body{font-family:Segoe UI,Arial,sans-serif;font-size:10.5pt;color:#111;margin:14mm}"
             "h1{font-size:17pt;margin:0 0 2px} h2{font-size:13pt;margin:14px 0 4px;border-bottom:2px solid #111}"
             ".klein{font-size:9pt;color:#333} .stand{font-size:12pt;font-weight:700;margin:4px 0 8px}"
             "table{border-collapse:collapse;width:100%} th,td{border:1px solid #999;padding:3px 6px;text-align:left;vertical-align:top}"
             "th{background:#eee} td.ok{width:16mm} tr.geplant td{color:#555;font-style:italic} td.et{white-space:nowrap}"
             "h3{font-size:11pt;margin:10px 0 3px} h3.warn{border:2px solid #111;padding:3px 6px;display:inline-block}"
             "thead{display:table-header-group} .fuss{margin-top:6px}"
             ".haus{break-before:page} .haus:first-of-type{break-before:auto} @page{margin:12mm}</style>",
             "<h1>Notfallliste – wer ist im Haus?</h1>",
             f"<div class='stand'>{escape(ort)}Stand {jetzt:%d.%m.%Y, %H:%M} Uhr · {sicher} Person{'en' if sicher != 1 else ''} "
             f"im Haus{f' · {geplant} geplant (Anreise prüfen)' if geplant else ''}</div>",
             "<div class='klein'>Grundlage: Belegung laut Gebäude- und Zimmerplan. <b>Nicht enthalten:</b> Gäste, Besucher, "
             "Personal und Änderungen seit dem Ausdruck. Spalte ✓ am Sammelplatz abhaken. Blatt nach Gebrauch vernichten "
             "(personenbezogene Daten).</div>"]
    if not zs:
        teile.append("<p><b>Laut Plan ist niemand im Haus.</b></p>")
    kopf = ("<thead><tr><th>✓</th><th>Etage</th><th>Zimmer</th><th>Name</th><th>Gruppe</th><th>bis</th>"
            "<th>Hinweis</th></tr></thead>")
    seitenfuss = (f"<div class='klein fuss'>Planstand {jetzt:%d.%m.%Y, %H:%M} Uhr – ohne Gäste, Besucher, Personal. "
                  "Nicht bestätigte Personen können fehlen oder schon abgereist sein.</div>")

    def zeile(z: NZeile) -> str:
        hinweis = " · ".join(t for t in (ART_TEXT.get(z.art, ""), z.hinweis) if t)
        return (f"<tr class='{z.art}'><td class='ok'></td><td class='et'>{escape(z.etage)}</td><td>{escape(z.zimmer)}</td>"
                f"<td>{escape(z.name)}</td><td>{escape(z.gruppe)}</td><td>{f'{z.bis:%d.%m.}' if z.bis else ''}</td>"
                f"<td>{escape(hinweis)}</td></tr>")

    for haus in dict.fromkeys(z.haus for z in zs):          # Reihenfolge wie sortiert
        h = n[haus]
        sicher_ = [z for z in zs if z.haus == haus and z.art != "geplant"]
        offen = [z for z in zs if z.haus == haus and z.art == "geplant"]
        plus = f" (+{h['geplant']} geplant)" if h["geplant"] else ""
        teile.append(f"<section class='haus'><h2>Haus {escape(haus)} – {h['personen']} Person"
                     f"{'en' if h['personen'] != 1 else ''} in {h['zimmer']} Zimmer{'n' if h['zimmer'] != 1 else ''}"
                     f"{plus}</h2>")
        if sicher_:
            teile.append("<h3>Im Haus laut Belegung</h3><table>" + kopf + "".join(zeile(z) for z in sicher_) + "</table>")
        if offen:
            # 0.90: hart getrennt – nur laut Planung erwartet, Anreise nicht bestätigt (nicht nach ihnen suchen lassen,
            # ohne vorher zu klären)
            teile.append("<h3 class='warn'>⚠ Nur geplant – Anreise NICHT bestätigt</h3><table>" + kopf
                         + "".join(zeile(z) for z in offen) + "</table>")
        teile.append(seitenfuss + "</section>")
    return "".join(teile)


# ---- Übergabeprotokoll (0.89) -----------------------------------------------------------------------------------------

def uebergabe_html(zimmer: str, lage: str, name: str, gruppe: str, von: date | None, bis: date | None, art: str,
                   inventar: list[tuple[str, int]], maengel: list[str], standort: str = "") -> str:
    """Übergabeprotokoll für Einzug („einzug“) oder Auszug („auszug“): Zimmer, Person, Inventar zum Abhaken, bekannte
    Mängel, Schlüssel, Bemerkungen, zwei Unterschriften. Ein Blatt, zum Ausdrucken."""
    titel = "Einzug" if art == "einzug" else "Auszug"
    zeit = " – ".join(f"{d:%d.%m.%Y}" for d in (von, bis) if d)
    teile = ["<!doctype html><meta charset='utf-8'><title>Übergabeprotokoll</title><style>"
             "body{font-family:Segoe UI,Arial,sans-serif;font-size:10.5pt;color:#111;margin:14mm}"
             "h1{font-size:16pt;margin:0 0 6px} h2{font-size:11.5pt;margin:14px 0 4px}"
             "table{border-collapse:collapse;width:100%} th,td{border:1px solid #999;padding:4px 6px;text-align:left}"
             "th{background:#eee} td.k{width:18mm;text-align:center} .feld{border-bottom:1px solid #333;height:22px}"
             ".zwei{display:grid;grid-template-columns:1fr 1fr;gap:18mm;margin-top:16mm} .klein{font-size:9pt;color:#333}"
             "@page{margin:12mm}</style>",
             f"<h1>Übergabeprotokoll – {titel}</h1>",
             "<table>"
             f"<tr><th style='width:34mm'>Zimmer</th><td>{escape(zimmer)}{f' · {escape(lage)}' if lage else ''}</td></tr>"
             f"<tr><th>Name</th><td>{escape(name)}</td></tr>"
             f"<tr><th>Gruppe</th><td>{escape(gruppe)}</td></tr>"
             f"<tr><th>Aufenthalt</th><td>{escape(zeit)}</td></tr>"
             f"<tr><th>{titel} am</th><td></td></tr></table>",
             "<h2>Ausstattung</h2><table><tr><th>Gegenstand</th><th>Soll</th><th>Ist</th><th class='k'>in Ordnung</th>"
             "<th>Bemerkung</th></tr>"]
    for g, n in inventar:
        teile.append(f"<tr><td>{escape(g)}</td><td>{n}</td><td></td><td class='k'>☐</td><td></td></tr>")
    for _ in range(3 if inventar else 6):
        teile.append("<tr><td>&nbsp;</td><td></td><td></td><td class='k'>☐</td><td></td></tr>")
    teile.append("</table><h2>Zustand</h2><table>")
    for punkt in ("Wände / Decke", "Boden", "Fenster / Vorhänge", "Bad / Waschbecken", "Bett / Matratze",
                  "Sauberkeit"):
        teile.append(f"<tr><td style='width:45mm'>{punkt}</td><td class='k'>☐ in Ordnung</td><td></td></tr>")
    teile.append("</table>")
    if maengel:
        teile.append("<h2>Bereits bekannte Mängel</h2><ul>" + "".join(f"<li>{escape(m)}</li>" for m in maengel) + "</ul>")
    teile.append("<h2>Schlüssel</h2><table><tr><td style='width:45mm'>Zimmerschlüssel</td><td>Anzahl:</td>"
                 f"<td class='k'>☐ {'übergeben' if art == 'einzug' else 'zurück'}</td></tr>"
                 f"<tr><td>Weitere (Schrank, Haus)</td><td>Anzahl:</td><td class='k'>☐ {'übergeben' if art == 'einzug' else 'zurück'}</td>"
                 "</tr></table>"
                 "<h2>Bemerkungen</h2><div class='feld'></div><div class='feld'></div>"
                 "<div class='zwei'><div><div class='feld'></div>Datum, Unterschrift Bewohner/in</div>"
                 "<div><div class='feld'></div>Datum, Unterschrift Internat</div></div>"
                 f"<p class='klein'>{escape(standort + ' · ' if standort else '')}Neu gefundene Mängel bitte in der Zimmerkarte melden.</p>")
    return "".join(teile)
