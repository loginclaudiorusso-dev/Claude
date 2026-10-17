"""Zimmerliste: Zimmer nach Eigenschaften filtern und ausdrucken – Renovierung, Boden, Tier-/Doppel-/Gästezimmer,
Bad über den Flur, heute frei. Dazu das Einlesen einer Renovierungsliste (aus Excel kopiert).

Renovierung und Boden stehen in den Zimmer-Stammdaten (``renoviert``, ``boden``, ``boden_vermutet``). Kennt der
Zimmerplan den Boden nicht, wird der Boden laut ZKL angezeigt (falls importiert). Rein, ohne Qt.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from datetime import date, datetime
from html import escape

from . import speicher
from . import zimmerplan as zp

BOEDEN = ["Vinyl", "PVC", "Teppich", "Laminat", "Linoleum", "Fliesen"]
IMPORT_DATEI = "Renovierungen_Import.tsv"     # liegt sie im Programm- oder Datenordner, wird sie einmal übernommen
_DATUM = re.compile(r"(\d{1,2})\.(\d{1,2})\.(\d{2,4})")


def boden_text(z: zp.Zimmer) -> str:
    return f"{z.boden} (vermutet)" if z.boden and z.boden_vermutet else z.boden


RENOVIERT_OHNE_DATUM = "ja"      # renoviert, Datum unbekannt


def reno_text(z: zp.Zimmer) -> str:
    d = reno_datum(z)
    if d and len(z.renoviert) == 7:                 # nur Monat bekannt (z. B. aus der ZKL „26-08“)
        return f"{d:%m/%Y}"
    return f"{d:%d.%m.%Y}" if d else ("ja (Datum ?)" if z.renoviert else "")


def reno_datum(z: zp.Zimmer) -> date | None:
    """Datum der Renovierung; bei „JJJJ-MM“ (nur Monat bekannt) der Monatserste."""
    try:
        if z.renoviert and len(z.renoviert) == 7:
            return date.fromisoformat(z.renoviert + "-01")
        return date.fromisoformat(z.renoviert) if z.renoviert else None
    except ValueError:
        return None


# ---------------------------------------------------------------------------------------
# Renovierungsliste einlesen
# ---------------------------------------------------------------------------------------

@dataclass
class Renovierung:
    zimmer: str
    datum: date | None          # None = renoviert, Datum unbekannt
    notiz: str = ""
    boden: str = ""             # in der Zeile genannter Boden (gilt als sicher)


def _datum(text: str) -> date | None:
    m = _DATUM.search(text or "")
    if not m:
        return None
    t, mo, j = int(m.group(1)), int(m.group(2)), int(m.group(3))
    try:
        return date(j + 2000 if j < 100 else j, mo, t)
    except ValueError:
        return None


def renovierungen_lesen(text: str, bekannt: set[str]) -> tuple[list[Renovierung], list[str]]:
    """Zeilen wie „3.1  E20  …  27.09.2019“ bzw. „2 402 fertigstellung 07.01.26 07.01.2026“ (Tabulator oder
    Leerzeichen): Haus, Zimmer, optional Notiz, Datum (letztes Datum der Zeile). Statt Datum geht „ja“ (renoviert,
    Datum unbekannt); ein genannter Boden (z. B. „Vinyl“) gilt als sicher. Gibt (Treffer, unbekannte Zeilen)."""
    from .zkl import zimmer_id

    erg, fehler = [], []
    for zeile in (text or "").splitlines():
        teile = [t.strip() for t in re.split(r"\t|\s{2,}", zeile.strip()) if t.strip()]
        if len(teile) < 2:
            teile = zeile.split()
        if len(teile) < 3:
            if zeile.strip():
                fehler.append(zeile.strip())
            continue
        daten = [d for t in teile if (d := _datum(t))]
        ohne_datum = any(t.lower() in ("ja", "renoviert") for t in teile[2:])
        boden = next((b for t in teile[2:] for b in BOEDEN
                      if t.lower() == b.lower() or b == "Vinyl" and t.lower() == "vynil"), "")
        zid = zimmer_id(f"{teile[0]}-{teile[1]}", bekannt)
        if not (daten or ohne_datum) or zid is None or zid not in bekannt:
            fehler.append(zeile.strip())
            continue
        notiz = " ".join(t for t in teile[2:] if not _DATUM.fullmatch(t) and t.lower() not in ("ja", "renoviert")
                         and t != boden)
        erg.append(Renovierung(zid, daten[-1] if daten else None, notiz, boden))
    return erg, fehler


def renovierungen_anwenden(stand: zp.Planstand, eintraege: list[Renovierung], boden: str = "",
                           vermutet: bool = True) -> int:
    """Renovierungsdatum setzen (das neuere gewinnt) und – wenn angegeben – den Boden, sofern noch keiner sicher
    eingetragen ist. Speichert die Stammdaten. Gibt die Zahl geänderter Zimmer zurück."""
    zimmer = {z.id: z for z in stand.zimmer}
    n = 0
    for e in eintraege:
        z = zimmer.get(e.zimmer)
        if z is None:
            continue
        alt = (z.renoviert, z.boden, z.boden_vermutet)
        if e.datum is None:
            z.renoviert = z.renoviert or RENOVIERT_OHNE_DATUM
        elif not reno_datum(z) or z.renoviert < e.datum.isoformat():
            z.renoviert = e.datum.isoformat()
        if e.boden:                            # in der Liste ausdrücklich genannt → sicher
            z.boden, z.boden_vermutet = e.boden, False
        elif boden and (not z.boden or z.boden_vermutet):
            z.boden, z.boden_vermutet = boden, vermutet
        n += alt != (z.renoviert, z.boden, z.boden_vermutet)
    if n:
        zp.stammdaten_speichern(stand.zimmer, stand.plan)
    return n


def auto_import(stand: zp.Planstand) -> tuple[int, list[str]] | None:
    """Einmalig: ``Renovierungen_Import.tsv`` aus Programm- oder Datenordner übernehmen (Boden: Vinyl, vermutet).
    None = keine (neue) Datei."""
    from .konfig import programmordner

    for ordner in dict.fromkeys([speicher.pfad(""), programmordner()]):
        pfad = ordner / IMPORT_DATEI
        if not pfad.is_file():
            continue
        text = pfad.read_text(encoding="utf-8-sig")
        kennung = hashlib.sha1(text.encode()).hexdigest()[:16]
        if kennung in speicher.einstellungen().get("renovierung_importe", []):
            return None
        eintraege, fehler = renovierungen_lesen(text, {z.id for z in stand.zimmer})
        n = renovierungen_anwenden(stand, eintraege, "Vinyl", True)
        speicher.einstellung_setzen("renovierung_importe",
                                    speicher.einstellungen().get("renovierung_importe", []) + [kennung])
        return n, fehler
    return None


# ---------------------------------------------------------------------------------------
# Filtern
# ---------------------------------------------------------------------------------------

STATUS_FILTER = {"frei": "frei", "belegt": "belegt", "geplant": "geplant", "gesperrt": "gesperrt"}

MERKMALE = {"tiere": "Tier-Zimmer", "doppel": "Doppelzimmer", "maenner": "Bad über den Flur (nur Männer)",
            "gaeste": "Gästezimmer"}


@dataclass
class Filter:
    haus: str = ""                    # "" = alle
    renoviert: str = "alle"           # alle | ja | nein | seit:JJJJ
    boden: str = "alle"               # alle | unbekannt | <Belag> (auch vermutet)
    merkmale: set[str] = field(default_factory=set)
    nur_internat: bool = True
    heute_frei: bool = False
    text: str = ""
    status: str = ""                  # "" | frei (auch teilweise) | belegt | geplant | gesperrt – am Stichtag
    boeden: set[str] = field(default_factory=set)      # mehrere Böden (oder-verknüpft), auch „unbekannt“
    gruppen: set[str] = field(default_factory=set)     # Personengruppen …
    gruppen_modus: str = "wohnt"      # … die dort wohnen | die dort wohnen dürfen („darf“)
    maengel: set[str] = field(default_factory=set)     # offene Mängel dieser Arten („*“ = irgendein Mangel)

    @property
    def aktiv(self) -> bool:
        """Ist irgendein Filter gesetzt (außer Haus)?"""
        return (self.renoviert != "alle" or self.boden != "alle" or bool(self.merkmale or self.boeden or self.gruppen)
                or not self.nur_internat or self.heute_frei or bool(self.text) or bool(self.status) or bool(self.maengel))

    def beschreibung(self) -> str:
        teile = [f"Haus {self.haus}" if self.haus else "alle Häuser"]
        if self.status:
            teile.append(STATUS_FILTER.get(self.status, self.status))
        if self.renoviert == "ja":
            teile.append("renoviert")
        elif self.renoviert == "nein":
            teile.append("nicht renoviert / unbekannt")
        elif self.renoviert.startswith("seit:"):
            teile.append(f"renoviert seit {self.renoviert[5:]}")
        if self.boden != "alle":
            teile.append(f"Boden {self.boden}")
        if self.boeden:
            teile.append("Boden " + " oder ".join(sorted(self.boeden)))
        teile += [MERKMALE[m] for m in sorted(self.merkmale)]
        if self.maengel:
            from .maengel import NAMEN

            from .maengel import STUFEN

            stufen = sorted((int(t[6:]) for t in self.maengel if t.startswith("stufe:")), reverse=True)
            arten = sorted(t for t in self.maengel if not t.startswith("stufe:") and t != "*")
            if stufen:
                teile.append("Mängel " + " oder ".join(f"{STUFEN[s][3]} ({STUFEN[s][0]})" for s in stufen if s in STUFEN))
            if "*" in self.maengel and not stufen:
                teile.append("Mängel")
            if arten:
                teile.append("Mangel: " + " oder ".join(NAMEN.get(m, m) for m in arten))
        if self.gruppen:
            teile.append(("wohnt: " if self.gruppen_modus == "wohnt" else "erlaubt für: ")
                         + ", ".join(zp.GRUPPE_LABEL.get(g, g) for g in sorted(self.gruppen)))
        if self.heute_frei:
            teile.append("heute frei")
        if self.text:
            teile.append(f"„{self.text}“")
        return " · ".join(teile)


@dataclass
class Zeile:
    zimmer: zp.Zimmer
    boden: str            # Anzeige (eigener Eintrag, sonst „PVC (ZKL)“)
    heute: str            # frei | Name(n) | gesperrt …
    frei: bool
    status: str = ""      # frei | teilweise | belegt | geplant | gesperrt (am Stichtag)
    belegungen: list = field(default_factory=list)     # Belegungen am Stichtag (für die Kartenansicht)
    maengel: list = field(default_factory=list)        # offene Mängel (maengel.Mangel)


def _boden_anzeige(lage: zp.Lage, z: zp.Zimmer) -> str:
    if z.boden:
        return boden_text(z)
    e = getattr(lage, "zkl", {}).get(z.id)
    if e is None or not e.boden:
        return ""
    belag = {"tep": "Teppich", "tep sw": "Teppich", "pvc": "PVC", "pvc-d": "PVC"}.get(e.boden.lower(), e.boden)
    return f"{belag} (ZKL)"


def filtern(stand: zp.Planstand, f: Filter, heute: date | None = None) -> list[Zeile]:
    from . import maengel as mg

    heute = heute or date.today()
    offen = mg.offen_je_zimmer()
    erg = []
    for z in stand.zimmer:
        if f.nur_internat and not z.aktiv or f.haus and z.haus != f.haus:
            continue
        d = reno_datum(z)
        if f.renoviert == "ja" and not z.renoviert or f.renoviert == "nein" and z.renoviert:
            continue
        if f.renoviert.startswith("seit:") and (d is None or d.year < int(f.renoviert[5:])):
            continue
        boden = _boden_anzeige(stand.lage, z)
        if f.boden == "unbekannt" and boden or f.boden not in ("alle", "unbekannt") and \
                not boden.lower().startswith(f.boden.lower()):
            continue
        if f.boeden and not any((b == "unbekannt" and not boden) or (b != "unbekannt" and boden.lower().startswith(b.lower()))
                                for b in f.boeden):
            continue
        if "tiere" in f.merkmale and not z.tiere or "doppel" in f.merkmale and z.betten < 2 \
                or "maenner" in f.merkmale and not z.nur_maenner or "gaeste" in f.merkmale and not z.gaeste:
            continue
        status, bs = stand.lage.status_am(z.id, heute)
        frei = status == "frei"
        if f.heute_frei and not frei:
            continue
        if f.status and status != f.status and not (f.status == "frei" and status == "teilweise"):
            continue
        if f.gruppen:
            if f.gruppen_modus == "wohnt":
                if not f.gruppen & zp.gruppen_am(stand.lage, z.id, heute):
                    continue
            elif not any(zp.erlaubt(z, g) for g in f.gruppen):
                continue
        if status == "gesperrt":
            jetzt = "gesperrt" + (f" ({bs[0].grund})" if bs and bs[0].grund else "")
        else:
            namen = [b.name for b in bs if b.art in ("belegt", "geplant") and b.name and b.name != zp.PIVOT_NAME]
            jetzt = ", ".join(namen) if namen else ("frei" if frei else "belegt")
        m = offen.get(z.id, [])
        stufen = {int(t[6:]) for t in f.maengel if t.startswith("stufe:")}
        arten = {t for t in f.maengel if not t.startswith("stufe:")}
        if stufen and mg.stufe(m) not in stufen:              # rot / orange / gelb – nach höchster Stufe im Zimmer
            continue
        if arten and not (m and ("*" in arten or any(x.art in arten for x in m))):
            continue
        if f.text and f.text.lower() not in f"{z.kurz} {z.notiz} {boden} {jetzt} {' '.join(x.text for x in m)}".lower():
            continue
        erg.append(Zeile(z, boden, jetzt, frei, status, [b for b in bs if b.art != "freigabe"], m))
    return erg


def merkmal_kurz(z: zp.Zimmer) -> str:
    return " ".join(k for k, an in (("Tier", z.tiere), ("DZ", z.betten > 1), ("M", z.nur_maenner), ("Gast", z.gaeste),
                                    ("außer Betrieb", not z.aktiv)) if an)


def liste_html(zeilen: list[Zeile], f: Filter, namen: bool = True) -> str:
    """Zimmerliste zum Ausdrucken – nach Haus und Zimmer, mit Filter in der Überschrift."""
    from .drucklisten import _STIL

    teile = [_STIL, "<h1>Zimmerliste</h1>",
             f"<div class='klein'>Internat Goslar · {escape(f.beschreibung())} · {len(zeilen)} Zimmer · "
             f"Stand {datetime.now():%d.%m.%Y %H:%M}</div><br>",
             "<table class='liste' width='100%' cellspacing='0'><tr><th width='10%'>Zimmer</th><th width='12%'>Etage</th>"
             "<th width='13%'>Merkmale</th><th width='12%'>Renoviert</th><th width='15%'>Boden</th>"
             + ("<th width='20%'>Heute</th>" if namen else "") + "<th>Notiz</th></tr>"]
    for r in zeilen:
        z = r.zimmer
        reno = escape(reno_text(z)) or "<span class='leer'>–</span>"
        teile.append(f"<tr><td><b>{escape(z.kurz)}</b></td><td>{escape(zp.flur_text(z))}</td>"
                     f"<td>{escape(merkmal_kurz(z))}</td><td>{reno}</td>")
        teile.append(f"<td>{escape(r.boden) or '<span class=leer>–</span>'}</td>"
                     + (f"<td>{escape(r.heute)}</td>" if namen else "") + f"<td>{escape(z.notiz)}</td></tr>")
    teile.append("</table>")
    if not zeilen:
        teile.append("<p class='leer'>Keine Zimmer für diese Auswahl.</p>")
    return "".join(teile)
