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
    for o, nur_mv in ordner + [(x, True) for x in ablage_lesen()]:
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
    for o, nur_mv in ordner + [(x, True) for x in ablage_lesen()]:
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


def ablage_kandidaten() -> list[Path]:
    """1.67: Reihenfolge der Ablage – eingestellter Ordner, „Mietunterlagen“ im Datenordner, persönlicher Ordner."""
    from . import export_ziel

    e = speicher.einstellungen().get("export_ordner")
    erg = [Path(e)] if e else []
    erg.append(Path(speicher.pfad("Mietunterlagen")))
    erg.append(export_ziel.privat().parent / "INNternat Mietunterlagen")
    return list(dict.fromkeys(erg))


def ablage() -> Path:
    """Ordner für erstellte Unterlagen (wie im Hauptprogramm gemerkt, sonst „Mietunterlagen“ im Datenordner).

    1.67: Darf dieser PC/diese Person dort nicht schreiben (z. B. Mitarbeiter ohne Rechte auf den Export-Ordner der
    Leitung), wird der nächste Ordner genommen – vorher scheiterte schon das Formular „Neuer Mieter“ daran."""
    from .export_ziel import _ordner_beschreibbar

    kand = ablage_kandidaten()
    for o in kand:
        try:
            o.mkdir(parents=True, exist_ok=True)
        except OSError:
            continue
        if _ordner_beschreibbar(o):
            return o
    raise PermissionError("Kein Ordner für die Mietunterlagen beschreibbar: " + ", ".join(str(o) for o in kand))


def _vorlagen_hinweis() -> str:
    """1.68: fehlende Vordrucke bzw. Muster-Vertragstext in der Meldung nennen."""
    from . import vorlagen_mieter as vm

    try:
        t = " Achtung: Der Vertrag nutzt noch den MUSTER-Text." if vm.ist_muster() else ""
        if fehlt := vm.fehlende_optional():
            t += f" Nicht angehängt (Vorlage fehlt): {', '.join(fehlt)}."
        return t
    except Exception:                          # noqa: BLE001 – nur ein Hinweis
        return ""


def ablage_hinweis(ordner: Path) -> str:
    """Zusatz zur Meldung, wenn die Unterlagen nicht im üblichen Ordner liegen."""
    erster = ablage_kandidaten()[0]
    return "" if Path(ordner) == erster else (f" Gespeichert in {ordner}, weil dieser PC nicht in {erster} schreiben "
                                              "darf – bitte bei Bedarf dorthin verschieben.")


def ablage_lesen() -> list[Path]:
    """Alle Ablageorte, die es gibt (für die Suche nach vergebenen Vertragsnummern – ohne anzulegen)."""
    erg = []
    for o in ablage_kandidaten():
        try:
            if o.is_dir():
                erg.append(o)
        except OSError:
            continue
    return erg


def _edge() -> str | None:
    for p in (shutil.which("msedge"), r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
              r"C:\Program Files\Microsoft\Edge\Application\msedge.exe", shutil.which("chromium"), shutil.which("google-chrome")):
        if p and Path(p).exists():
            return p
    return None


# 0.87: Einheitliche Schrift. Das HTML des Hauptprogramms hat kein <!doctype> (für Qt gedacht) – Edge rechnet es dann
# im Kompatibilitätsmodus, und darin erben Tabellen die Schriftgröße nicht: nummerierte Absätze, Bankdaten und
# Unterschriftenblock standen in 12 pt statt 10,5 pt. Mit doctype und dieser Regel erbt alles die Schrift des Textes.
EINHEITLICH_CSS = ("<style>table, tr, td, th { font-family: inherit; font-size: inherit; color: inherit; "
                   "line-height: inherit; } p { line-height: 1.3; }</style>")


def einheitlich(html: str) -> str:
    """doctype davor und Schrift-Vererbung für Tabellen – Wortlaut und Aufbau bleiben unverändert."""
    if "<!doctype" in html[:200].lower():
        return html
    t = html if "<html" in html.lower() else f"<html><body>{html}</body></html>"
    i = t.lower().index("<html")
    j = t.index(">", i) + 1
    return "<!doctype html>" + t[:j] + f"<head><meta charset='utf-8'>{EINHEITLICH_CSS}</head>" + t[j:]


def html_als_pdf(html: str) -> bytes | None:
    """HTML → PDF mit Edge/Chromium ohne Fenster. None, wenn kein Browser dafür da ist."""
    exe = _edge()
    if exe is None:
        return None
    html = einheitlich(html)
    with tempfile.TemporaryDirectory() as tmp:
        quelle, ziel = Path(tmp) / "dokument.html", Path(tmp) / "dokument.pdf"
        quelle.write_text(html if "<html" in html.lower() else f"<!doctype html><meta charset='utf-8'>{html}", encoding="utf-8")
        try:
            subprocess.run([exe, "--headless", "--disable-gpu", "--no-pdf-header-footer", f"--print-to-pdf={ziel}"]
                           + ([] if os.name == "nt" else ["--no-sandbox"]) + [quelle.as_uri()], timeout=60, capture_output=True, creationflags=0x08000000 if os.name == "nt" else 0)
        except (OSError, subprocess.TimeoutExpired):
            return None
        return ziel.read_bytes() if ziel.exists() else None


def zimmer_auswahl(von: date, bis: date, anrede: str, alle: bool = False, person: str = "") -> dict[str, str]:
    """Zimmer für einen Mieter im Zeitraum – passende zuerst; mit ``alle`` auch andere (mit Grund). ``person``: beim
    Bearbeiten der eigene Eintrag („mv:26-011“) – er blockiert sein eigenes Zimmer nicht."""
    stand = zp.laden()
    b = zp.Bedarf(person or "mv:neu", "Neu", "Miete Goslar", "Mieter", von, bis, "w" if anrede == "Frau" else "m")
    ohne = {person} if person else set()
    erg = {}
    for z in sorted((z for z in stand.zimmer if z.aktiv), key=lambda z: (zp._haus_sort(z.haus), z.nummer)):
        grund = zp.passt(stand.lage, z, b, ohne)
        if grund is None or alle:
            erg[z.id] = z.kurz + ("" if grund is None else f" ({grund})")
    return erg


# ---- Flexible Mietverträge ---------------------------------------------------------------------------
# In „Vorlagen/Mieter/Mietvertrag.vorlage“ stehen die abweichenden Textstellen als eigene Zeilen:
#   ?flexibel  <Text>   – nur im flexiblen Vertrag
#   ?!flexibel <Text>   – nur im üblichen Vertrag (dort wie bisher)
# Das Hauptprogramm kennt die Markierung nicht und erstellt immer den üblichen Vertrag (gleiche Schreibweise wie
# „?kaution“). Welche Verträge flexibel sind, merkt sich die neue Oberfläche (für „Unterlagen neu erstellen“).

FLEX_DATEI = f"{speicher.IMPORT_ORDNER}/modern_mieter_flexibel.json"
_FLEX = re.compile(r"^\?(!?)flexibel\s+(.*)$")


def flexible() -> set[str]:
    return set(speicher.lesen(FLEX_DATEI, {}).get("vertraege", []))


def _flex_setzen(nr: str, an: bool) -> None:
    alle = flexible() - {nr} | ({nr} if an else set())
    speicher.schreiben(FLEX_DATEI, {"vertraege": sorted(alle)})


def vorlage_hat_flexibel(text: str | None = None) -> bool:
    if text is None:
        ordner = mt.vorlagen_ordner()
        if ordner is None or not (ordner / mt.VERTRAG).exists():
            return False
        text = (ordner / mt.VERTRAG).read_text(encoding="utf-8")
    return any(_FLEX.match(z.rstrip()) and not z.startswith("?!") for z in text.splitlines())


def vorlage_fuer(text: str, flexibel: bool) -> str:
    """Wortlaut für den Vertrag: beim flexiblen die „?flexibel“-Zeilen statt der „?!flexibel“-Zeilen."""
    if not flexibel:
        return text
    if not vorlage_hat_flexibel(text):
        raise ValueError("Die Vorlage „Mietvertrag.vorlage“ enthält noch keine Textstellen für flexible Verträge – "
                         "dort Zeilen mit „?flexibel “ beginnen lassen (und die üblichen mit „?!flexibel “).")
    erg = []
    for z in text.splitlines():
        m = _FLEX.match(z.rstrip())
        if m is None:
            erg.append(z)
        elif not m.group(1):
            erg.append(m.group(2))                 # nur flexibel → immer zeigen
    return "\n".join(erg)


# ---- 0.61: Jahr der Vertragsnummer, Zimmer trotzdem nehmen ----------------------------------------------------

def vertragsjahr(von: date, heute: date | None = None) -> int:
    """Jahr am Anfang der Vertragsnummer: das Jahr, in dem der Vertrag erstellt wird – oder, wenn er erst später
    beginnt, das Jahr des Mietbeginns (im Dezember 2026 für Januar 2027 erstellt → „27-…“)."""
    return max((heute or date.today()).year, von.year)


def nummer_vorschlag(von: date, heute: date | None = None) -> tuple[str, str]:
    return nummern_abgleich(date(vertragsjahr(von, heute), 1, 1))


def _jahr_pruefen(nr: str, von: date, heute: date | None = None) -> str | None:
    jj = f"{vertragsjahr(von, heute) % 100:02d}"
    m = _NR.fullmatch(nr.strip())
    if m and m.group(1) != jj:
        return (f"Die Vertragsnummer muss mit {jj} beginnen (Vertrag für 20{jj}) – Vorschlag: "
                f"{nummer_vorschlag(von, heute)[0]}.")
    return None


TROTZDEM_HINWEIS = ("Wenn es trotzdem passt (z. B. bis dahin fertig renoviert): Haken „Zimmer trotzdem nehmen“ setzen "
                    "– oder im Zimmer „Früher frei (fertig renoviert)“ eintragen.")


def zimmer_grund(person: str, mv: mt.Mietvertrag) -> str | None:
    """Warum das Zimmer im Zeitraum nicht passt (None = passt). Der eigene Eintrag blockiert nicht."""
    stand = zp.laden()
    z = next((x for x in stand.zimmer if x.id == mv.zimmer), None)
    if z is None:
        return "Zimmer nicht gefunden"
    b = zp.Bedarf(person, f"{mv.nachname}, {mv.vorname}", "Miete Goslar", "Mieter", mv.von, mv.bis,
                  "w" if mv.weiblich else "m")
    return zp.passt(stand.lage, z, b, {person})


# ---- 1.69: Anschrift vor Einzug, Auswahl der Vordrucke, Nummer automatisch -------------------------------------

ANSCHRIFT_DATEI = f"{speicher.IMPORT_ORDNER}/modern_mieter_anschrift.json"
DOKUMENTE = {mt.WOHNUNGSGEBER: "Wohnungsgeberbestätigung", mt.SEPA: "SEPA-Lastschriftmandat",
             mt.MIETSCHULDEN: "Mietschuldenfreiheitsbescheinigung"}
DOKU_EINSTELLUNG = "mieter_dokumente"
DOKU_STANDARD = [mt.WOHNUNGSGEBER, mt.SEPA]          # Mietschuldenfreiheit nur bei Bedarf


def _in_akte(mv, pfade) -> None:
    """1.72: erstellte Unterlagen zusätzlich in die Mieter-Akte."""
    from . import mieter_akte

    for p in pfade:
        mieter_akte.kopie_ablegen(mv.nr, mv.nachname, p)


def anschrift(nr: str) -> str:
    return str((speicher.lesen(ANSCHRIFT_DATEI, {}) or {}).get(nr, ""))


def _anschrift_setzen(nr: str, text: str) -> None:
    d = dict(speicher.lesen(ANSCHRIFT_DATEI, {}) or {})
    if text.strip():
        d[nr] = text.strip()
    else:
        d.pop(nr, None)
    speicher.schreiben(ANSCHRIFT_DATEI, d)


def text_vorbereiten(text: str, mv, anschrift_: str = "") -> str:
    """Platzhalter, die das Hauptprogramm nicht kennt: {anschrift}, {name_anschrift} (Vorname Nachname, Anschrift)."""
    a = (anschrift_ or "").strip()
    return (text.replace("{name_anschrift}", f"{mv.vorname} {mv.nachname}" + (f", {a}" if a else ""))
            .replace("{anschrift}", a))


def dokumente_vorhanden() -> list[str]:
    o = mt.vorlagen_ordner()
    return [d for d in DOKUMENTE if o is not None and (o / d).is_file()]


def dokumente_standard() -> list[str]:
    gemerkt = speicher.einstellungen().get(DOKU_EINSTELLUNG)
    return [d for d in (gemerkt if isinstance(gemerkt, list) else DOKU_STANDARD) if d in DOKUMENTE]


def _paket(mv, pdf, ziel: Path, ordner: Path | None, auswahl: list[str] | None) -> list[str]:
    """Unterlagen-PDF; ``auswahl`` = Dateinamen der Vordrucke, die angehängt werden (None = alle vorhandenen)."""
    if auswahl is None or ordner is None:
        return mt.paket_erstellen(mv, pdf, ziel, ordner)
    with tempfile.TemporaryDirectory() as tmp:
        for d in auswahl:
            if d in DOKUMENTE and (ordner / d).is_file():
                shutil.copy2(ordner / d, Path(tmp) / d)
        return mt.paket_erstellen(mv, pdf, ziel, Path(tmp))


def neuer_vertrag(werte: dict) -> tuple[str, Path]:
    """1.69: unter der Schreibsperre – die automatische Nummer kann so kein zweiter PC gleichzeitig vergeben."""
    from . import netz_kern

    with netz_kern.sperre():
        return _neuer_vertrag(werte)


def _neuer_vertrag(werte: dict) -> tuple[str, Path]:
    """Vertrag anlegen, Unterlagen erstellen. (Meldung, Pfad der PDF/HTML)."""
    if werte.get("nr_auto", False) or not str(werte.get("nr", "")).strip():
        werte = {**werte, "nr": nummer_vorschlag(werte["von"])[0]}    # 1.69: immer die nächste freie Nummer
    mv = mt.Mietvertrag(werte["nr"].strip(), werte["anrede"], werte["vorname"].strip(), werte["nachname"].strip(),
                        werte["zimmer"] or "", werte["von"], werte["bis"], round(float(werte["miete"]), 2),
                        int(werte["flaeche"]), int(werte["schluessel"]), werte["kaution_bis"] if werte["kaution"] else None,
                        kaution=bool(werte["kaution"]), email=werte.get("email", "").strip())
    fehler = mt.pruefen(mv) + (["Der Vertragstext (Mietvertrag.vorlage) ist noch nicht eingerichtet – Mieter → "
                                 "„Vorlagen“ (eigene Datei hochladen oder Muster anlegen)."]
                                if mt.fehlende_vorlagen() else [])
    if not any("Vertragsnummer" in f for f in fehler) and (j := _jahr_pruefen(mv.nr, mv.von)):
        fehler.append(j)
    elif not any("Vertragsnummer" in f for f in fehler) and (wo := vergeben(mv.nr)):
        fehler.append(f"Die Vertragsnummer {mv.nr} ist schon vergeben ({wo}) – nächste freie: "
                      f"{nummer_vorschlag(mv.von)[0]}.")
    trotz = ""
    if mv.zimmer and not fehler and (grund := zimmer_grund("mv:neu", mv)):
        if not werte.get("trotzdem"):
            fehler.append(f"Zimmer {mv.zimmer_kurz}: {grund}. {TROTZDEM_HINWEIS}")
        trotz = grund
    if fehler:
        raise ValueError("Bitte prüfen: " + " ".join(fehler))
    ordner = mt.vorlagen_ordner()
    flex = bool(werte.get("flexibel"))
    adr = str(werte.get("anschrift", "") or "")
    html = mt.vertrag_html(mv, text_vorbereiten(vorlage_fuer((ordner / mt.VERTRAG).read_text(encoding="utf-8"), flex),
                                                mv, adr), ordner / mt.LOGO)
    ziel = ablage() / f"Mietunterlagen_MV{mv.nr}_{mv.nachname.replace(' ', '_')}.pdf"
    pdf = html_als_pdf(html)
    auswahl = werte.get("dokumente")
    teile = _paket(mv, pdf, ziel, ordner, list(auswahl) if auswahl is not None else None)
    extra = ""
    if pdf is None:                           # Vertrag als HTML daneben – im Browser drucken/als PDF speichern
        h = ziel.with_name(ziel.stem.replace("Mietunterlagen", "Mietvertrag") + ".html")
        h.write_text(einheitlich(html), encoding="utf-8")
        extra = f" Mietvertrag als {h.name} (im Browser drucken)."
    def anlegen():
        mt.anlegen(mv)
        _flex_setzen(mv.nr, flex)
        if adr.strip():
            _anschrift_setzen(mv.nr, adr)
        if auswahl is not None:
            speicher.einstellung_setzen(DOKU_EINSTELLUNG, [d for d in auswahl if d in DOKUMENTE])
        if trotz:
            from belegung import protokoll

            protokoll.eintragen([{"aktion": "Zimmer trotz Hinweis gewählt", "name": f"{mv.nachname}, {mv.vorname}",
                                  "person": mv.person, "alt": "", "neu": mv.zimmer, "von": mv.von.isoformat(),
                                  "quelle": f"Mieter · {trotz}"}])
    _schritt(f"Mietvertrag {mv.nr}", anlegen, [mt.DATEI, FLEX_DATEI, ANSCHRIFT_DATEI])
    _in_akte(mv, [ziel, ziel.with_name(ziel.stem.replace("Mietunterlagen", "Mietvertrag") + ".html")])
    return (f"{'Flexibler ' if flex else ''}Mietvertrag {mv.nr} für {mv.name} ({mv.zimmer_kurz}) erstellt"
            + (": " + ", ".join(teile) if teile else "") + "." + extra + ablage_hinweis(ziel.parent)
            + _vorlagen_hinweis()), ziel


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
    _in_akte(mv, [ziel, ziel.with_suffix(".pdf")])
    return f"Nebenabrede für MV {mv.nr} bis {bis_neu:%d.%m.%Y} gespeichert ({'Word + PDF' if pdf else 'Word'}) – Zimmerplan verlängert", ziel


# ---- 0.60: bestehenden Vertrag bearbeiten (z. B. falsches Zimmer) ----------------------------------------------

AENDERBAR = {"nr": "Vertragsnummer", "anrede": "Anrede", "vorname": "Vorname", "nachname": "Nachname", "zimmer": "Zimmer", "von": "Mietbeginn",
             "bis": "Mietende", "miete": "Miete", "flaeche": "Fläche", "schluessel": "Schlüssel", "kaution": "Kaution",
             "kaution_bis": "Kaution bis", "email": "E-Mail"}


def _wert_text(k: str, v) -> str:
    if isinstance(v, date):
        return f"{v:%d.%m.%Y}"
    if k == "zimmer":
        return str(v).removeprefix("GS-")
    if isinstance(v, bool):
        return "ja" if v else "nein"
    return str(v)


def vertrag_aendern(nr: str, werte: dict, unterlagen: bool = True) -> tuple[str, Path | None]:
    """Einen erstellten Vertrag korrigieren: Name, Zimmer, Zeitraum, Miete … (die Vertragsnummer bleibt). Der
    Zimmerplan zieht mit; im Verlauf steht, was sich geändert hat. ``unterlagen``: Vertrags-PDF gleich neu erstellen.
    Ein Zimmer, das im Zeitraum nicht passt (belegt, falsche Gruppe …), wird abgelehnt."""
    from dataclasses import replace

    from belegung import protokoll

    alt = mt.nach_nummer(nr)
    if alt is None:
        raise ValueError("Den Vertrag gibt es nicht mehr.")
    neu = replace(alt, nr=(werte.get("nr") or nr).strip(), anrede=werte["anrede"], vorname=werte["vorname"].strip(), nachname=werte["nachname"].strip(),
                  zimmer=werte["zimmer"] or "", von=werte["von"], bis=werte["bis"], miete=round(float(werte["miete"]), 2),
                  flaeche=int(werte["flaeche"]), schluessel=int(werte["schluessel"]), kaution=bool(werte["kaution"]),
                  kaution_bis=(werte.get("kaution_bis") or werte["von"]) if werte["kaution"] else None,
                  email=(werte.get("email") or "").strip(), verlaengerungen=list(alt.verlaengerungen))
    if neu.bis != alt.bis:
        neu.mail_ende = ""                         # neues Ende → Mail zum Vertragsende wieder offen
    fehler = mt.pruefen(neu, [m for m in mt.laden() if m.nr != nr])
    if neu.nr != nr and not fehler:
        erstellt = date.fromisoformat(alt.erstellt[:10]) if alt.erstellt[:10].count("-") == 2 else None
        if (j := _jahr_pruefen(neu.nr, neu.von, erstellt)):
            fehler.append(j)
        elif (wo := vergeben(neu.nr)):
            fehler.append(f"Die Vertragsnummer {neu.nr} ist schon vergeben ({wo}).")
    trotz = ""
    if (neu.zimmer, neu.von, neu.bis, neu.anrede) != (alt.zimmer, alt.von, alt.bis, alt.anrede) and neu.zimmer:
        if (grund := zimmer_grund(alt.person, neu)):
            if not werte.get("trotzdem"):
                fehler.append(f"Zimmer {neu.zimmer_kurz}: {grund}. {TROTZDEM_HINWEIS}")
            trotz = grund
    if fehler:
        raise ValueError("Bitte prüfen: " + " ".join(fehler))
    geaendert = [(k, getattr(alt, k), getattr(neu, k)) for k in AENDERBAR if getattr(alt, k) != getattr(neu, k)]
    flex_alt, flex_neu = nr in flexible(), bool(werte.get("flexibel", nr in flexible()))
    if not geaendert and flex_alt == flex_neu:
        raise ValueError("Es wurde nichts geändert.")

    def tun():
        alle = [neu if m.nr == nr else m for m in mt.laden()]
        mt._speichern(alle)
        if neu.nr != nr:                       # neue Nummer → neuer Schlüssel im Zimmerplan, alter Eintrag weg
            speicher.schreiben(zp.ZUWEISUNGEN, {"zuweisungen": [z for z in zp.zuweisungen_laden()
                                                                 if z["person"] != alt.person]})
            _flex_setzen(nr, False)
        mt._zuweisung_setzen(neu)
        _flex_setzen(neu.nr, flex_neu)
        if trotz:
            protokoll.eintragen([{"aktion": "Zimmer trotz Hinweis gewählt", "name": f"{neu.nachname}, {neu.vorname}",
                                  "person": neu.person, "alt": alt.zimmer, "neu": neu.zimmer, "von": neu.von.isoformat(),
                                  "quelle": f"Mieter · {trotz}"}])
        protokoll.eintragen([{"aktion": "Mietvertrag geändert", "name": f"{neu.nachname}, {neu.vorname}",
                              "person": alt.person, "alt": _wert_text(k, a_), "neu": _wert_text(k, n_),
                              "von": neu.von.isoformat(), "quelle": f"Mieter · {AENDERBAR[k]}"}
                             for k, a_, n_ in geaendert] or
                            [{"aktion": "Mietvertrag geändert", "name": f"{neu.nachname}, {neu.vorname}",
                              "person": alt.person, "alt": "üblich" if not flex_alt else "flexibel",
                              "neu": "flexibel" if flex_neu else "üblich", "von": neu.von.isoformat(),
                              "quelle": "Mieter · Vertragsart"}])
    _schritt(f"Mietvertrag {nr} geändert", tun, [mt.DATEI, FLEX_DATEI])
    was = ", ".join(f"{AENDERBAR[k]} {_wert_text(k, a_)} → {_wert_text(k, n_)}" for k, a_, n_ in geaendert) or "Vertragsart"
    text = f"MV {neu.nr} geändert: {was}"
    if not unterlagen:
        return text + " – Unterlagen bitte bei Bedarf neu erstellen.", None
    try:
        t2, pfad = unterlagen_neu(neu.nr)
    except ValueError as exc:
        return f"{text} – Unterlagen nicht neu erstellt: {exc}", None
    return f"{text} · {t2}", pfad


def unterlagen_neu(nr: str, dokumente: list[str] | None = None) -> tuple[str, Path]:
    mv = mt.nach_nummer(nr)
    if mv is None:
        raise ValueError("Den Vertrag gibt es nicht mehr.")
    ordner = mt.vorlagen_ordner()
    if ordner is None:
        raise ValueError("Vorlagen fehlen im Ordner „Vorlagen/Mieter“.")
    html = mt.vertrag_html(mv, text_vorbereiten(vorlage_fuer((ordner / mt.VERTRAG).read_text(encoding="utf-8"),
                                                           nr in flexible()), mv, anschrift(nr)), ordner / mt.LOGO)
    ziel = ablage() / f"Mietunterlagen_MV{mv.nr}_{mv.nachname.replace(' ', '_')}.pdf"
    teile = _paket(mv, html_als_pdf(html), ziel, ordner, dokumente if dokumente is not None else dokumente_standard())
    _in_akte(mv, [ziel])
    return f"Unterlagen neu erstellt: {', '.join(teile)}", ziel
