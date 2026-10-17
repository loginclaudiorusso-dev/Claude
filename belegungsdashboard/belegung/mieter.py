"""Mieter: Unterlagen beim Einzug (Mietvertrag, Wohnungsgeberbestätigung, SEPA-Mandat, Mietschuldenfreiheits-
bescheinigung) und die Nebenabrede bei einer Verlängerung – aus einer Maske (Name, Zimmer, ab wann).

Die Vorlagen (Vertragswortlaut, PDF-Vordrucke, Logo) liegen im Ordner ``Vorlagen/Mieter`` neben dem Programm (oder im
Datenordner) und werden nur mit dem Update-Paket verteilt. Ausgefüllt wird mit pypdf (Formularfelder bzw. Text an
festen Stellen); den Vertragstext setzt die Oberfläche aus ``vertrag_html`` als PDF. Jeder Mieter steht in
``mieter.json`` und – als Gruppe „Mieter“ – im Zimmerplan. Rein, ohne Qt.
"""

from __future__ import annotations

import html
import io
import re
import zipfile
from dataclasses import asdict, dataclass, field
from datetime import date, datetime, timedelta
from pathlib import Path

from . import protokoll, speicher

DATEI = "mieter.json"
VORLAGEN_ORDNER = Path("Vorlagen") / "Mieter"
VERTRAG = "Mietvertrag.vorlage"
WOHNUNGSGEBER = "Wohnungsgeberbestaetigung.pdf"
SEPA = "SEPA_Lastschriftmandat.pdf"
MIETSCHULDEN = "Mietschuldenfreiheitsbescheinigung.pdf"
LOGO = "logo.jpg"
VORLAGEN = [VERTRAG, WOHNUNGSGEBER, SEPA, MIETSCHULDEN]

VERMIETERIN = "INN-tegrativ gGmbH, Kriegerstraße 1e, 30161 Hannover"
ADRESSE = "Schützenallee 6-9, 38644 Goslar"
VERTRAGSORT = "Hannover"
STANDARD_MIETE = 450.0
STANDARD_FLAECHE = 11
STANDARD_MONATE = 6


@dataclass
class Mietvertrag:
    nr: str                    # „26-011“
    anrede: str                # Frau | Herr
    vorname: str
    nachname: str
    zimmer: str                # Zimmer-ID (GS-6-1005)
    von: date
    bis: date
    miete: float = STANDARD_MIETE
    flaeche: int = STANDARD_FLAECHE
    schluessel: int = 1
    kaution_bis: date | None = None        # Mietsicherheit spätestens bis (Standard: Mietbeginn)
    erstellt: str = ""
    verlaengerungen: list[dict] = field(default_factory=list)   # [{"bis_alt", "bis", "am"}]

    @property
    def weiblich(self) -> bool:
        return self.anrede != "Herr"

    @property
    def name(self) -> str:
        return f"{self.vorname} {self.nachname}".strip()

    @property
    def person(self) -> str:
        """Schlüssel im Zimmerplan."""
        return f"mv:{self.nr}"

    @property
    def zimmer_kurz(self) -> str:
        return self.zimmer.removeprefix("GS-")

    @property
    def haus(self) -> str:
        return self.zimmer_kurz.partition("-")[0]

    @property
    def zimmer_nr(self) -> str:
        return self.zimmer_kurz.partition("-")[2]

    def zu_dict(self) -> dict:
        d = asdict(self)
        d["von"], d["bis"] = self.von.isoformat(), self.bis.isoformat()
        d["kaution_bis"] = self.kaution_bis.isoformat() if self.kaution_bis else None
        return d

    @staticmethod
    def aus_dict(d: dict) -> "Mietvertrag":
        d = dict(d)
        d["von"], d["bis"] = date.fromisoformat(d["von"]), date.fromisoformat(d["bis"])
        d["kaution_bis"] = date.fromisoformat(d["kaution_bis"]) if d.get("kaution_bis") else None
        felder = Mietvertrag.__dataclass_fields__
        return Mietvertrag(**{k: v for k, v in d.items() if k in felder})


# ---------------------------------------------------------------------------------------
# Ablage, Nummern, Zimmerplan
# ---------------------------------------------------------------------------------------

def laden() -> list[Mietvertrag]:
    erg = []
    for d in speicher.lesen(DATEI, {}).get("mieter", []):
        try:
            erg.append(Mietvertrag.aus_dict(d))
        except (KeyError, TypeError, ValueError):
            continue
    return erg


def _speichern(alle: list[Mietvertrag]) -> None:
    speicher.schreiben(DATEI, {"mieter": [m.zu_dict() for m in alle]})


def nach_nummer(nr: str) -> Mietvertrag | None:
    return next((m for m in laden() if m.nr == nr), None)


def naechste_nummer(heute: date | None = None, vorhandene: list[str] | None = None) -> str:
    """„JJ-NNN“ – die nächste freie Nummer im laufenden Jahr (nach den hier erstellten Verträgen)."""
    heute = heute or date.today()
    jj = f"{heute:%y}"
    nummern = vorhandene if vorhandene is not None else [m.nr for m in laden()]
    lfd = [int(m.group(1)) for n in nummern if (m := re.fullmatch(rf"{jj}-(\d+)", n.strip()))]
    return f"{jj}-{max(lfd, default=0) + 1:03d}"


def standard_ende(von: date, monate: int = STANDARD_MONATE) -> date:
    """Ende nach ``monate`` Monaten: Tag vor demselben Tag im Zielmonat (01.09. → 28.02.)."""
    j, m = divmod(von.month - 1 + monate, 12)
    ziel = date(von.year + j, m + 1, 1)
    tag = min(von.day, 28 if ziel.month == 2 else 30 if ziel.month in (4, 6, 9, 11) else 31)
    return ziel.replace(day=tag) - timedelta(days=1)


BALD_TAGE = 42      # „endet bald“: in den nächsten 6 Wochen – Zeit für die Nebenabrede


def status(mv: Mietvertrag, heute: date | None = None) -> tuple[str, str]:
    """(Text, Stufe) – beginnt / läuft / endet bald / beendet."""
    heute = heute or date.today()
    if mv.von > heute:
        return f"beginnt {mv.von:%d.%m.}", "akzent"
    if mv.bis < heute:
        return "beendet", "neutral"
    tage = (mv.bis - heute).days
    if tage <= BALD_TAGE:
        return f"endet in {tage} Tagen" if tage else "endet heute", "knapp"
    return "läuft", "ok"


def weitere_mieter(stand, heute: date | None = None) -> list:
    """Mieter laut Zimmerplan/Gebäudeplan, die nicht hier angelegt sind (aktuell oder künftig)."""
    from . import zimmerplan as zp

    heute = heute or date.today()
    erg = []
    for zid, bs in stand.lage.belegungen.items():
        for b in bs:
            if (b.art in ("belegt", "geplant") and b.bis >= heute and not b.person.startswith("mv:")
                    and zp.gruppe_von(b.massnahme, "") == "Mieter" and b.name and b.name != zp.PIVOT_NAME):
                erg.append(b)
    return sorted(erg, key=lambda b: (b.bis, b.name))


def pruefen(mv: Mietvertrag, andere: list[Mietvertrag] | None = None) -> list[str]:
    """Fehler, die das Erstellen verhindern."""
    fehler = []
    if not mv.vorname.strip() or not mv.nachname.strip():
        fehler.append("Vor- und Nachname fehlen.")
    if not mv.zimmer:
        fehler.append("Kein Zimmer gewählt.")
    if mv.bis <= mv.von:
        fehler.append("Das Ende muss nach dem Beginn liegen.")
    if not re.fullmatch(r"\d{2}-\d{3}", mv.nr.strip()):
        fehler.append("Vertragsnummer bitte als JJ-NNN, z. B. 26-011.")
    elif any(m.nr == mv.nr for m in (andere if andere is not None else laden())):
        fehler.append(f"Die Vertragsnummer {mv.nr} ist schon vergeben.")
    if mv.miete <= 0:
        fehler.append("Der Mietzins fehlt.")
    return fehler


def bedarf_liste():
    """Mieter als Bedarf für den Zimmerplan (Gruppe „Mieter“)."""
    from . import zimmerplan as zp

    return [zp.Bedarf(m.person, f"{m.nachname}, {m.vorname}", f"Miete Goslar MV {m.nr}", "Mieter", m.von, m.bis,
                      "w" if m.weiblich else "m", bemerkung=f"Mietvertrag {m.nr}") for m in laden()]


def _zuweisung_setzen(mv: Mietvertrag) -> None:
    from . import zimmerplan as zp

    alle = [z for z in zp.zuweisungen_laden() if z["person"] != mv.person]
    alle.append({"person": mv.person, "name": f"{mv.nachname}, {mv.vorname}", "massnahme": f"Miete Goslar MV {mv.nr}",
                 "gruppe": "Mieter", "geschlecht": "w" if mv.weiblich else "m", "zimmer": mv.zimmer,
                 "von": mv.von.isoformat(), "bis": mv.bis.isoformat()})
    speicher.schreiben(zp.ZUWEISUNGEN, {"zuweisungen": alle})


def anlegen(mv: Mietvertrag) -> None:
    """Neuen Mieter speichern und im Zimmerplan eintragen (geplant, Gruppe Mieter)."""
    mv.erstellt = mv.erstellt or datetime.now().isoformat(timespec="seconds")
    alle = [m for m in laden() if m.nr != mv.nr] + [mv]
    _speichern(alle)
    _zuweisung_setzen(mv)
    protokoll.eintragen([{"aktion": "Mietvertrag erstellt", "name": f"{mv.nachname}, {mv.vorname}", "person": mv.person,
                          "alt": "", "neu": mv.zimmer, "von": mv.von.isoformat(), "quelle": "Mieter"}])


def verlaengern(nr: str, bis_neu: date) -> Mietvertrag:
    """Ende verschieben (Nebenabrede); der Zimmerplan zieht mit."""
    alle = laden()
    mv = next(m for m in alle if m.nr == nr)
    if bis_neu <= mv.bis:
        raise ValueError(f"Das neue Ende muss nach dem bisherigen ({mv.bis:%d.%m.%Y}) liegen.")
    mv.verlaengerungen.append({"bis_alt": mv.bis.isoformat(), "bis": bis_neu.isoformat(),
                               "am": date.today().isoformat()})
    alt, mv.bis = mv.bis, bis_neu
    _speichern(alle)
    _zuweisung_setzen(mv)
    protokoll.eintragen([{"aktion": "Mietvertrag verlängert", "name": f"{mv.nachname}, {mv.vorname}", "person": mv.person,
                          "alt": alt.isoformat(), "neu": bis_neu.isoformat(), "von": mv.von.isoformat(), "quelle": "Mieter"}])
    return mv


# ---------------------------------------------------------------------------------------
# Vorlagen
# ---------------------------------------------------------------------------------------

def vorlagen_ordner() -> Path | None:
    """Erst der Datenordner (eigene, angepasste Vorlagen), dann der Programmordner."""
    from .konfig import programmordner

    for basis in (speicher.pfad(""), programmordner()):
        ordner = Path(basis) / VORLAGEN_ORDNER
        if ordner.is_dir():
            return ordner
    return None


def fehlende_vorlagen() -> list[str]:
    ordner = vorlagen_ordner()
    return list(VORLAGEN) if ordner is None else [v for v in VORLAGEN if not (ordner / v).is_file()]


_WAHL = re.compile(r"\[([^\[\]|]*)\|([^\[\]|]*)\]")


def ersetzen(text: str, werte: dict[str, str], weiblich: bool) -> str:
    """„[die Mieterin|der Mieter]“ nach Anrede wählen, „{feld}“ ausfüllen (unbekannte Felder bleiben stehen)."""
    text = _WAHL.sub(lambda m: m.group(1) if weiblich else m.group(2), text)
    return re.sub(r"\{(\w+)\}", lambda m: werte.get(m.group(1), m.group(0)), text)


def _euro(betrag: float) -> str:
    return f"{betrag:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def werte(mv: Mietvertrag) -> dict[str, str]:
    return {"nr": mv.nr, "name": mv.name, "vorname": mv.vorname, "nachname": mv.nachname, "anrede": mv.anrede,
            "haus": mv.haus, "zimmer": mv.zimmer_nr, "zimmer_kurz": mv.zimmer_kurz, "flaeche": str(mv.flaeche),
            "schluessel": str(mv.schluessel), "von": f"{mv.von:%d.%m.%Y}", "bis": f"{mv.bis:%d.%m.%Y}",
            "miete": _euro(mv.miete), "kaution_bis": f"{(mv.kaution_bis or mv.von):%d.%m.%Y}",
            "mieter_adresse": ADRESSE, "vermieterin_adresse": VERMIETERIN, "ort": VERTRAGSORT}


def vertrag_html(mv: Mietvertrag, vorlage: str, logo: Path | None = None) -> str:
    """Mietvertrag als HTML (für QTextDocument → PDF) aus dem Wortlaut in ``Mietvertrag.vorlage``."""
    w = werte(mv)
    e = lambda t: html.escape(ersetzen(t, w, mv.weiblich))
    teile = ["<html><body style=\"font-family:'Segoe UI', Arial, sans-serif; font-size:10.5pt; color:#111;\">"]
    if logo is not None and logo.is_file():
        teile.append(f"<table width='100%'><tr><td></td><td align='right'><img src='{logo.as_posix()}' height='46'>"
                     "</td></tr></table>")
    bank = False
    for zeile in vorlage.splitlines():
        z = zeile.rstrip()
        if z.startswith("#"):
            continue
        if bank and not z.startswith("|"):          # Bank-Tabelle endet mit der ersten anderen Zeile
            teile.append("</table>")
            bank = False
        if not z.strip():
            teile.append("<p style='margin:0;'>&nbsp;</p>")
        elif z == "---SEITE---":
            teile.append("<p style='page-break-before:always; margin:0;'>&nbsp;</p>")
        elif z.startswith("=="):
            teile.append(f"<p align='center' style='margin-top:12px; margin-bottom:6px;'><b>{e(z[2:].strip())}</b></p>")
        elif z.startswith("="):
            teile.append(f"<p align='center' style='font-size:14pt; margin:4px;'><b>{e(z[1:].strip())}</b></p>")
        elif z.startswith(">"):
            teile.append(f"<p align='right'>{e(z[1:].strip())}</p>")
        elif z.startswith("^"):
            teile.append(f"<p align='center'>{e(z[1:].strip())}</p>")
        elif z.startswith("|"):
            a, _, b = z[1:].partition("|")
            if not bank:
                teile.append("<table style='margin-left:40px;' cellspacing='0' cellpadding='1'>")
                bank = True
            teile.append(f"<tr><td width='120'>{e(a)}</td><td>{e(b)}</td></tr>")
        elif z.startswith("+"):
            teile.append(f"<p align='justify' style='margin-left:24px; margin-top:4px;'>{e(z[1:].strip())}</p>")
        elif (m := re.match(r"^(\d+)\.\s+(.*)$", z)):
            teile.append("<table width='100%' cellspacing='0' cellpadding='0' style='margin-top:4px;'><tr>"
                         f"<td width='24' valign='top'>{m.group(1)}.</td>"
                         f"<td align='justify' valign='top'>{e(m.group(2))}</td></tr></table>")
        elif z == "@UNTERSCHRIFT":
            teile.append(_unterschrift_html(mv))
        else:
            teile.append(f"<p align='justify' style='margin-top:4px;'>{e(z.strip())}</p>")
    if bank:
        teile.append("</table>")
    return "".join(teile) + "</body></html>"


def _unterschrift_html(mv: Mietvertrag) -> str:
    rolle = "Mieterin" if mv.weiblich else "Mieter"
    return ("<p>&nbsp;</p>"
            f"<p>{html.escape(VERTRAGSORT)}, ____________________</p><p>&nbsp;</p><p>&nbsp;</p>"
            "<table width='100%' cellspacing='0'><tr>"
            "<td width='48%' style='border-top:1px solid #000;'>" + rolle + "<br>" + html.escape(mv.name) + "</td>"
            "<td width='4%'></td>"
            "<td width='48%' style='border-top:1px solid #000;'>Vermieterin<br>(INN-tegrativ gGmbH)</td>"
            "</tr></table>")


# ---------------------------------------------------------------------------------------
# PDF-Vordrucke ausfüllen (pypdf)
# ---------------------------------------------------------------------------------------

# Text an festen Stellen: (x, y von oben, Text-Schlüssel, Schriftgröße) in Punkt auf Seite 1
WOHNUNGSGEBER_FELDER = [
    (248, 366, "zusatz", 10),          # Zusatzangaben (Stockwerk/Wohnungsnummer)
    (236, 399, "einzug", 10.5),        # „In die oben genannte Wohnung ist/sind am …“
    (447.5, 401, "x", 12),             # Kästchen „eingezogen“
    (118, 466, "nachname", 10.5),      # erste Zeile: Familienname
    (402, 466, "vorname", 10.5),       #              Vorname
]
SEPA_FELDER = [
    (306, 281, "mandat", 10),                 # Mandatsreferenz
    (140, 323, "empfaenger", 10),             # [Name des Zahlungsempfängers]
    (64, 357, "empfaenger", 10),              # [Name des Zahlungsempfängers]
    (64, 418, "kontoinhaber", 10),            # Kontoinhaber (Vorname, Name)
    (64, 439, "strasse", 10),                 # Straße, Hausnummer
    (64, 461, "plz_ort", 10),                 # PLZ, Ort
    (64, 545, "ort", 10),                     # Ort, Datum
]
MIETSCHULDEN_FELDER = {"Name Vorname_2": "name_nv", "Straße Hausnummer_2": "strasse_zimmer", "PLZ Wohnort_2": "plz_ort"}


def formular_werte(mv: Mietvertrag) -> dict[str, str]:
    return {"zusatz": f"Haus {mv.haus}, Zimmer {mv.zimmer_kurz}", "einzug": f"{mv.von:%d.%m.%Y}", "x": "X",
            "nachname": mv.nachname, "vorname": mv.vorname, "mandat": f"MV {mv.nr}", "empfaenger": "INN-tegrativ gGmbH",
            "kontoinhaber": mv.name, "strasse": "Schützenallee 6-9", "plz_ort": "38644 Goslar", "ort": "Goslar,",
            "name_nv": f"{mv.nachname}, {mv.vorname}", "strasse_zimmer": f"Schützenallee 6-9 (Haus {mv.haus}, "
            f"Zimmer {mv.zimmer_kurz})"}


def _pdf_text(t: str) -> str:
    t = t.encode("cp1252", "replace").decode("latin-1")
    return t.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def text_auflegen(seite, eintraege: list[tuple[float, float, str, float]]) -> None:
    """Text (Helvetica) auf eine pypdf-Seite legen; y von oben gemessen."""
    from pypdf import PageObject
    from pypdf.generic import (ArrayObject, DecodedStreamObject, DictionaryObject, NameObject)

    box = seite.mediabox
    breite, hoehe = float(box.width), float(box.height)
    befehle = []
    for x, y, text, groesse in eintraege:
        if text:
            befehle.append(f"BT /FA {groesse} Tf 0 0 0 rg {x:.1f} {hoehe - y:.1f} Td ({_pdf_text(text)}) Tj ET")
    if not befehle:
        return
    ueber = PageObject.create_blank_page(width=breite, height=hoehe)
    schrift = DictionaryObject({NameObject("/Type"): NameObject("/Font"), NameObject("/Subtype"): NameObject("/Type1"),
                                NameObject("/BaseFont"): NameObject("/Helvetica"),
                                NameObject("/Encoding"): NameObject("/WinAnsiEncoding")})
    ueber[NameObject("/Resources")] = DictionaryObject({NameObject("/Font"): DictionaryObject({NameObject("/FA"): schrift}),
                                                        NameObject("/ProcSet"): ArrayObject([NameObject("/PDF"),
                                                                                             NameObject("/Text")])})
    inhalt = DecodedStreamObject()
    inhalt.set_data("\n".join(befehle).encode("latin-1"))
    ueber[NameObject("/Contents")] = inhalt
    seite.merge_page(ueber)


def vordruck_anhaengen(schreiber, pfad: Path, felder: list[tuple], werte_: dict[str, str]) -> None:
    """Vordruck an ``schreiber`` anhängen und auf seine erste Seite Text legen (Seite gehört erst dem Schreiber)."""
    from pypdf import PdfReader

    start = len(schreiber.pages)
    schreiber.append(PdfReader(str(pfad)))
    text_auflegen(schreiber.pages[start], [(x, y, werte_.get(k, ""), g) for x, y, k, g in felder])


def paket_erstellen(mv: Mietvertrag, vertrag_pdf: bytes | None, ziel: Path, ordner: Path | None = None) -> list[str]:
    """Alle Einzugsunterlagen in eine PDF: Mietvertrag, Wohnungsgeberbestätigung, SEPA-Mandat,
    Mietschuldenfreiheitsbescheinigung (vorausgefüllt, ohne Kreuze). Gibt die Namen der enthaltenen Teile zurück."""
    from pypdf import PdfReader, PdfWriter
    from pypdf.generic import NameObject

    ordner = ordner or vorlagen_ordner()
    w = formular_werte(mv)
    schreiber = PdfWriter()
    teile = []
    if vertrag_pdf:
        schreiber.append(PdfReader(io.BytesIO(vertrag_pdf)))
        teile.append("Mietvertrag")
    if ordner and (ordner / WOHNUNGSGEBER).is_file():
        vordruck_anhaengen(schreiber, ordner / WOHNUNGSGEBER, WOHNUNGSGEBER_FELDER, w)
        teile.append("Wohnungsgeberbestätigung")
    if ordner and (ordner / SEPA).is_file():
        vordruck_anhaengen(schreiber, ordner / SEPA, SEPA_FELDER, w)
        teile.append("SEPA-Lastschriftmandat")
    if ordner and (ordner / MIETSCHULDEN).is_file():
        ms = PdfWriter(clone_from=str(ordner / MIETSCHULDEN))
        ms.update_page_form_field_values(ms.pages[0], {feld: w[k] for feld, k in MIETSCHULDEN_FELDER.items()},
                                         auto_regenerate=False)
        ms.set_need_appearances_writer(True)
        puffer = io.BytesIO()
        ms.write(puffer)
        start = len(schreiber.pages)
        schreiber.append(PdfReader(puffer))
        teile.append("Mietschuldenfreiheitsbescheinigung")
        if len(schreiber.pages) > start:
            schreiber.set_need_appearances_writer(True)
    schreiber.add_metadata({NameObject("/Title"): f"Mietunterlagen MV {mv.nr} – {mv.name}"})
    with open(ziel, "wb") as f:
        schreiber.write(f)
    return teile


# ---------------------------------------------------------------------------------------
# Verlängerung: Nebenabrede (Word und PDF)
# ---------------------------------------------------------------------------------------

def nebenabrede_texte(mv: Mietvertrag, bis_neu: date, am: date | None = None) -> dict[str, str]:
    am = am or date.today()
    return {"titel": f"Nebenabrede zum Mietvertrag {mv.nr} / {mv.anrede} {mv.nachname}",
            "text": ("Das Mietverhältnis wird im gegenseitigen Einvernehmen zu den vereinbarten Konditionen bis zum "
                     f"{bis_neu:%d.%m.%Y} verlängert."),
            "ort": f"Goslar, {am:%d.%m.%Y}", "mieter": "Mieterin" if mv.weiblich else "Mieter", "name": mv.name}


def nebenabrede_html(mv: Mietvertrag, bis_neu: date, logo: Path | None = None, am: date | None = None) -> str:
    t = {k: html.escape(v) for k, v in nebenabrede_texte(mv, bis_neu, am).items()}
    kopf = (f"<table width='100%'><tr><td></td><td align='right'><img src='{logo.as_posix()}' height='46'></td></tr></table>"
            if logo is not None and logo.is_file() else "")
    return ("<html><body style=\"font-family:'Segoe UI', Arial, sans-serif; font-size:11pt;\">" + kopf +
            f"<p>&nbsp;</p><p><b>{t['titel']}</b></p><p>&nbsp;</p><p>{t['text']}</p><p>&nbsp;</p><p>&nbsp;</p>"
            f"<p>{t['ort']}</p><p>&nbsp;</p><p>&nbsp;</p>"
            "<table width='100%' cellspacing='0'><tr>"
            f"<td width='45%' style='border-top:1px solid #000;'>{t['mieter']}<br>{t['name']}</td><td width='10%'></td>"
            "<td width='45%' style='border-top:1px solid #000;'>Vermieterin<br>(INN-tegrativ gGmbH)</td>"
            "</tr></table></body></html>")


def _w_absatz(text: str, fett: bool = False, abstand: int = 240, tabs: bool = False) -> str:
    lauf = "<w:rPr><w:b/></w:rPr>" if fett else ""
    if tabs:
        links, _, rechts = text.partition("\t")
        inhalt = (f"<w:r>{lauf}<w:t xml:space=\"preserve\">{html.escape(links)}</w:t></w:r>"
                  f"<w:r><w:tab/></w:r><w:r>{lauf}<w:t xml:space=\"preserve\">{html.escape(rechts)}</w:t></w:r>")
        ppr = f"<w:pPr><w:tabs><w:tab w:val=\"left\" w:pos=\"5400\"/></w:tabs><w:spacing w:after=\"{abstand}\"/></w:pPr>"
    else:
        inhalt = f"<w:r>{lauf}<w:t xml:space=\"preserve\">{html.escape(text)}</w:t></w:r>"
        ppr = f"<w:pPr><w:spacing w:after=\"{abstand}\"/></w:pPr>"
    return f"<w:p>{ppr}{inhalt}</w:p>"


def nebenabrede_docx(mv: Mietvertrag, bis_neu: date, logo: Path | None = None, am: date | None = None) -> bytes:
    """Nebenabrede als Word-Datei (.docx) – zum Bearbeiten und Drucken in Word."""
    t = nebenabrede_texte(mv, bis_neu, am)
    bild = logo is not None and logo.is_file()
    logo_xml = ""
    if bild:
        cx, cy = 1800000, 786000          # ca. 5 × 2,2 cm
        logo_xml = (
            "<w:p><w:pPr><w:jc w:val=\"right\"/></w:pPr><w:r><w:drawing><wp:inline distT=\"0\" distB=\"0\" distL=\"0\" "
            f"distR=\"0\"><wp:extent cx=\"{cx}\" cy=\"{cy}\"/><wp:docPr id=\"1\" name=\"Logo\"/>"
            "<a:graphic><a:graphicData "
            "uri=\"http://schemas.openxmlformats.org/drawingml/2006/picture\"><pic:pic><pic:nvPicPr><pic:cNvPr id=\"1\" "
            "name=\"logo.jpg\"/><pic:cNvPicPr/></pic:nvPicPr><pic:blipFill><a:blip r:embed=\"rIdLogo\"/><a:stretch>"
            "<a:fillRect/></a:stretch></pic:blipFill><pic:spPr><a:xfrm><a:off x=\"0\" y=\"0\"/>"
            f"<a:ext cx=\"{cx}\" cy=\"{cy}\"/></a:xfrm><a:prstGeom prst=\"rect\"><a:avLst/></a:prstGeom></pic:spPr>"
            "</pic:pic></a:graphicData></a:graphic></wp:inline></w:drawing></w:r></w:p>")
    koerper = (logo_xml + _w_absatz("", abstand=480) + _w_absatz(t["titel"], fett=True, abstand=480)
               + _w_absatz(t["text"], abstand=720) + _w_absatz(t["ort"], abstand=1200)
               + _w_absatz("_____________________________\t_____________________________", abstand=0, tabs=True)
               + _w_absatz(f"{t['mieter']}\tVermieterin", abstand=0, tabs=True)
               + _w_absatz(f"{t['name']}\t(INN-tegrativ gGmbH)", abstand=0, tabs=True))
    dokument = ("<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>"
                "<w:document xmlns:w=\"http://schemas.openxmlformats.org/wordprocessingml/2006/main\" "
                "xmlns:r=\"http://schemas.openxmlformats.org/officeDocument/2006/relationships\" "
                "xmlns:wp=\"http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing\" "
                "xmlns:a=\"http://schemas.openxmlformats.org/drawingml/2006/main\" "
                "xmlns:pic=\"http://schemas.openxmlformats.org/drawingml/2006/picture\">"
                f"<w:body>{koerper}<w:sectPr><w:pgSz w:w=\"11906\" w:h=\"16838\"/><w:pgMar w:top=\"1134\" "
                "w:right=\"1134\" w:bottom=\"1134\" w:left=\"1418\" w:header=\"709\" w:footer=\"709\" w:gutter=\"0\"/>"
                "</w:sectPr></w:body></w:document>")
    stile = ("<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>"
             "<w:styles xmlns:w=\"http://schemas.openxmlformats.org/wordprocessingml/2006/main\"><w:docDefaults>"
             "<w:rPrDefault><w:rPr><w:rFonts w:ascii=\"Arial\" w:hAnsi=\"Arial\" w:cs=\"Arial\"/><w:sz w:val=\"22\"/>"
             "<w:lang w:val=\"de-DE\"/></w:rPr></w:rPrDefault></w:docDefaults></w:styles>")
    typen = ("<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>"
             "<Types xmlns=\"http://schemas.openxmlformats.org/package/2006/content-types\">"
             "<Default Extension=\"rels\" ContentType=\"application/vnd.openxmlformats-package.relationships+xml\"/>"
             "<Default Extension=\"xml\" ContentType=\"application/xml\"/>"
             "<Default Extension=\"jpg\" ContentType=\"image/jpeg\"/>"
             "<Override PartName=\"/word/document.xml\" ContentType=\"application/vnd.openxmlformats-officedocument."
             "wordprocessingml.document.main+xml\"/>"
             "<Override PartName=\"/word/styles.xml\" ContentType=\"application/vnd.openxmlformats-officedocument."
             "wordprocessingml.styles+xml\"/></Types>")
    rels = ("<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>"
            "<Relationships xmlns=\"http://schemas.openxmlformats.org/package/2006/relationships\">"
            "<Relationship Id=\"rId1\" Type=\"http://schemas.openxmlformats.org/officeDocument/2006/relationships/"
            "officeDocument\" Target=\"word/document.xml\"/></Relationships>")
    doc_rels = ("<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>"
                "<Relationships xmlns=\"http://schemas.openxmlformats.org/package/2006/relationships\">"
                "<Relationship Id=\"rIdStile\" Type=\"http://schemas.openxmlformats.org/officeDocument/2006/"
                "relationships/styles\" Target=\"styles.xml\"/>"
                + ("<Relationship Id=\"rIdLogo\" Type=\"http://schemas.openxmlformats.org/officeDocument/2006/"
                   "relationships/image\" Target=\"media/logo.jpg\"/>" if bild else "") + "</Relationships>")
    puffer = io.BytesIO()
    with zipfile.ZipFile(puffer, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", typen)
        z.writestr("_rels/.rels", rels)
        z.writestr("word/document.xml", dokument)
        z.writestr("word/styles.xml", stile)
        z.writestr("word/_rels/document.xml.rels", doc_rels)
        if bild:
            z.writestr("word/media/logo.jpg", logo.read_bytes())
    return puffer.getvalue()
