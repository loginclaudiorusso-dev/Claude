"""Mieter: neuer Vertrag mit allen Unterlagen (eine PDF) und Verlängerung per Nebenabrede (Word + PDF) – mit der
Logik aus ``belegung.mieter``. Das Hauptprogramm setzt HTML mit Qt in PDF um; hier übernimmt das Microsoft Edge
(auf jedem Windows 10/11 vorhanden, ohne Fenster). Ohne Edge wird die HTML-Fassung gespeichert und zum Drucken geöffnet."""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import tempfile
from datetime import date
from pathlib import Path

from belegung import mieter as mt
from belegung import speicher
from belegung import zimmerplan as zp

from .kern import _schritt

ANREDEN = ["Frau", "Herr"]
EINSTELLUNG_ORDNER = "modern_mietvertraege_ordner"    # Ordner mit den bisherigen Verträgen (auch aus Word/von Hand)
EINSTELLUNG_LETZTE = "modern_mietvertraege_letzte"    # zuletzt vergebene Nummer außerhalb des Programms („26-047“)
_NR = re.compile(r"(?<!\d)(\d{2})[-._ ]?(\d{3})(?!\d)")
MAX_DATEIEN = 5000                                     # Netzlaufwerk: nicht endlos suchen


def _nummern_in(ordner: Path, jj: str, nur_mv: bool) -> dict[int, str]:
    """Laufende Nummern des Jahres ``jj`` in Dateinamen (auch Unterordner): „MV26-011“, „Mietvertrag 26.011“ …
    ``nur_mv``: nur Dateien, die nach Mietvertrag aussehen (im allgemeinen Ablageordner)."""
    erg: dict[int, str] = {}
    n = 0
    for wurzel, _ordner, dateien in os.walk(ordner):
        for d in dateien:
            n += 1
            if n > MAX_DATEIEN:
                return erg
            if nur_mv and not re.search(r"(?i)miet|nebenabrede|(?<![a-z])mv", d):
                continue
            for m in _NR.finditer(Path(d).stem):
                if m.group(1) == jj:
                    erg.setdefault(int(m.group(2)), str(Path(wurzel) / d))
    return erg


def nummern_abgleich(heute: date | None = None) -> tuple[str, str]:
    """(nächste Nummer, woher die höchste bisherige stammt). Berücksichtigt die Verträge dieses Programms, die Dateien im
    Ablageordner und im Ordner mit den bisherigen Verträgen sowie die von Hand festgelegte letzte Nummer."""
    heute = heute or date.today()
    jj = f"{heute:%y}"
    gefunden: dict[int, str] = {}
    for nr in (m.nr for m in mt.laden()):
        if (m := _NR.fullmatch(nr.strip())) and m.group(1) == jj:
            gefunden[int(m.group(2))] = "Mieterliste"
    e = speicher.einstellungen()
    if (m := _NR.fullmatch(str(e.get(EINSTELLUNG_LETZTE, "")).strip())) and m.group(1) == jj:
        gefunden.setdefault(int(m.group(2)), "von Hand festgelegt")
    ordner = [(Path(e[EINSTELLUNG_ORDNER]), False)] if e.get(EINSTELLUNG_ORDNER) else []
    for o, nur_mv in ordner + [(ablage(), True)]:
        try:
            if o.is_dir():
                for lfd, datei in _nummern_in(o, jj, nur_mv).items():
                    gefunden.setdefault(lfd, f"Datei {Path(datei).name}")
        except OSError:
            continue
    if not gefunden:
        return f"{jj}-001", f"noch keine Nummer aus 20{jj} gefunden"
    hoechste = max(gefunden)
    return f"{jj}-{hoechste + 1:03d}", f"zuletzt {jj}-{hoechste:03d} ({gefunden[hoechste]})"


def vergeben(nr: str, heute: date | None = None) -> str | None:
    """Ist die Nummer schon außerhalb der Mieterliste vergeben (Datei, festgelegt)? → Quelle, sonst None."""
    m = _NR.fullmatch(nr.strip())
    if not m:
        return None
    lfd = int(m.group(2))
    e = speicher.einstellungen()
    if (x := _NR.fullmatch(str(e.get(EINSTELLUNG_LETZTE, "")).strip())) and x.group(1) == m.group(1) and lfd <= int(x.group(2)):
        return f"bis {x.group(1)}-{int(x.group(2)):03d} als vergeben festgelegt"
    ordner = [(Path(e[EINSTELLUNG_ORDNER]), False)] if e.get(EINSTELLUNG_ORDNER) else []
    for o, nur_mv in ordner + [(ablage(), True)]:
        try:
            if o.is_dir() and (d := _nummern_in(o, m.group(1), nur_mv).get(lfd)):
                return f"Datei {Path(d).name}"
        except OSError:
            continue
    return None


def abgleich_einstellen(ordner: str, letzte: str) -> str:
    ordner, letzte = (ordner or "").strip().strip('"'), (letzte or "").strip()
    if ordner and not Path(ordner).is_dir():
        raise ValueError(f"Ordner nicht gefunden: {ordner}")
    if letzte and not _NR.fullmatch(letzte):
        raise ValueError("Letzte Nummer bitte als JJ-NNN, z. B. 26-047.")
    if letzte:
        m = _NR.fullmatch(letzte)
        letzte = f"{m.group(1)}-{m.group(2)}"
    speicher.einstellung_setzen(EINSTELLUNG_ORDNER, ordner)
    speicher.einstellung_setzen(EINSTELLUNG_LETZTE, letzte)
    nr, woher = nummern_abgleich()
    return f"Nächste Vertragsnummer {nr} – {woher}"


def ablage() -> Path:
    """Ordner für erstellte Unterlagen (wie im Hauptprogramm gemerkt, sonst „Mietunterlagen“ im Datenordner)."""
    ordner = Path(speicher.einstellungen().get("export_ordner") or speicher.pfad("Mietunterlagen"))
    ordner.mkdir(parents=True, exist_ok=True)
    return ordner


def _edge() -> str | None:
    for p in (shutil.which("msedge"), r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
              r"C:\Program Files\Microsoft\Edge\Application\msedge.exe", shutil.which("chromium"), shutil.which("google-chrome")):
        if p and Path(p).exists():
            return p
    return None


def html_als_pdf(html: str) -> bytes | None:
    """HTML → PDF mit Edge/Chromium ohne Fenster. None, wenn kein Browser dafür da ist."""
    exe = _edge()
    if exe is None:
        return None
    with tempfile.TemporaryDirectory() as tmp:
        quelle, ziel = Path(tmp) / "dokument.html", Path(tmp) / "dokument.pdf"
        quelle.write_text(html if "<html" in html.lower() else f"<!doctype html><meta charset='utf-8'>{html}", encoding="utf-8")
        try:
            subprocess.run([exe, "--headless", "--disable-gpu", "--no-pdf-header-footer", f"--print-to-pdf={ziel}"]
                           + ([] if os.name == "nt" else ["--no-sandbox"]) + [quelle.as_uri()], timeout=60, capture_output=True, creationflags=0x08000000 if os.name == "nt" else 0)
        except (OSError, subprocess.TimeoutExpired):
            return None
        return ziel.read_bytes() if ziel.exists() else None


def zimmer_auswahl(von: date, bis: date, anrede: str, alle: bool = False) -> dict[str, str]:
    """Zimmer für einen Mieter im Zeitraum – passende zuerst; mit ``alle`` auch andere (mit Grund)."""
    stand = zp.laden()
    b = zp.Bedarf("mv:neu", "Neu", "Miete Goslar", "Mieter", von, bis, "w" if anrede == "Frau" else "m")
    erg = {}
    for z in sorted((z for z in stand.zimmer if z.aktiv), key=lambda z: (zp._haus_sort(z.haus), z.nummer)):
        grund = zp.passt(stand.lage, z, b)
        if grund is None or alle:
            erg[z.id] = z.kurz + ("" if grund is None else f" ({grund})")
    return erg


def neuer_vertrag(werte: dict) -> tuple[str, Path]:
    """Vertrag anlegen, Unterlagen erstellen. (Meldung, Pfad der PDF/HTML)."""
    mv = mt.Mietvertrag(werte["nr"].strip(), werte["anrede"], werte["vorname"].strip(), werte["nachname"].strip(),
                        werte["zimmer"] or "", werte["von"], werte["bis"], round(float(werte["miete"]), 2),
                        int(werte["flaeche"]), int(werte["schluessel"]), werte["kaution_bis"] if werte["kaution"] else None,
                        kaution=bool(werte["kaution"]), email=werte.get("email", "").strip())
    fehler = mt.pruefen(mv) + [f"Vorlage fehlt: {v}" for v in mt.fehlende_vorlagen()]
    if not any("Vertragsnummer" in f for f in fehler) and (wo := vergeben(mv.nr)):
        fehler.append(f"Die Vertragsnummer {mv.nr} ist schon vergeben ({wo}) – nächste freie: {nummern_abgleich()[0]}.")
    if fehler:
        raise ValueError("Bitte prüfen: " + " ".join(fehler))
    ordner = mt.vorlagen_ordner()
    html = mt.vertrag_html(mv, (ordner / mt.VERTRAG).read_text(encoding="utf-8"), ordner / mt.LOGO)
    ziel = ablage() / f"Mietunterlagen_MV{mv.nr}_{mv.nachname.replace(' ', '_')}.pdf"
    pdf = html_als_pdf(html)
    teile = mt.paket_erstellen(mv, pdf, ziel, ordner)
    extra = ""
    if pdf is None:                           # Vertrag als HTML daneben – im Browser drucken/als PDF speichern
        h = ziel.with_name(ziel.stem.replace("Mietunterlagen", "Mietvertrag") + ".html")
        h.write_text(html, encoding="utf-8")
        extra = f" Mietvertrag als {h.name} (im Browser drucken)."
    _schritt(f"Mietvertrag {mv.nr}", lambda: mt.anlegen(mv), [mt.DATEI])
    return (f"Mietvertrag {mv.nr} für {mv.name} ({mv.zimmer_kurz}) erstellt: " + ", ".join(teile) + "." + extra), ziel


def verlaengern(nr: str, bis_neu: date) -> tuple[str, Path]:
    mv = mt.nach_nummer(nr)
    if mv is None:
        raise ValueError("Den Vertrag gibt es nicht mehr.")
    if bis_neu <= mv.bis:
        raise ValueError(f"Das neue Ende muss nach dem {mv.bis:%d.%m.%Y} liegen.")
    ordner = mt.vorlagen_ordner()
    logo = ordner / mt.LOGO if ordner else None
    ziel = ablage() / f"Nebenabrede_MV{mv.nr}_{mv.nachname.replace(' ', '_')}.docx"
    ziel.write_bytes(mt.nebenabrede_docx(mv, bis_neu, logo))
    pdf = html_als_pdf(mt.nebenabrede_html(mv, bis_neu, logo))
    if pdf:
        ziel.with_suffix(".pdf").write_bytes(pdf)
    _schritt(f"Verlängerung {mv.nr}", lambda: mt.verlaengern(mv.nr, bis_neu), [mt.DATEI])
    return f"Nebenabrede für MV {mv.nr} bis {bis_neu:%d.%m.%Y} gespeichert ({'Word + PDF' if pdf else 'Word'}) – Zimmerplan verlängert", ziel


def unterlagen_neu(nr: str) -> tuple[str, Path]:
    mv = mt.nach_nummer(nr)
    if mv is None:
        raise ValueError("Den Vertrag gibt es nicht mehr.")
    ordner = mt.vorlagen_ordner()
    if ordner is None:
        raise ValueError("Vorlagen fehlen im Ordner „Vorlagen/Mieter“.")
    html = mt.vertrag_html(mv, (ordner / mt.VERTRAG).read_text(encoding="utf-8"), ordner / mt.LOGO)
    ziel = ablage() / f"Mietunterlagen_MV{mv.nr}_{mv.nachname.replace(' ', '_')}.pdf"
    teile = mt.paket_erstellen(mv, html_als_pdf(html), ziel, ordner)
    return f"Unterlagen neu erstellt: {', '.join(teile)}", ziel
