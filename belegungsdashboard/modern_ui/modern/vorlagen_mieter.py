"""1.68: Vorlagen für Mietverträge einrichten – „Neuer Mieter“ scheiterte, weil der Ordner ``Vorlagen\\Mieter`` fehlte.

Die Vorlagen sind keine Programmteile (echte Vertragstexte gehören nicht ins Update-Paket). Bisher suchte das Programm
sie im Datenordner des Standorts und im Programmordner – Letzterer wird bei jedem Update ersetzt. Fehlte eine der vier
Dateien, brach „Neuer Mieter“ ab, auch wenn nur ein Vordruck fehlte.

Jetzt:
* ``ordner_suchen`` (eingehängt in ``mieter.vorlagen_ordner``, nur neue Oberfläche): Standort-Datenordner → gemeinsamer
  Datenordner (Goslar, gilt für alle Standorte) → Programmordner; genommen wird der erste mit ``Mietvertrag.vorlage``.
* Pflicht ist nur ``Mietvertrag.vorlage``. Die drei PDF-Vordrucke und das Logo hängt das Programm an, wenn sie da sind.
* ``einrichten``: Datei in den gemeinsamen Datenordner speichern (bleibt bei Updates); eine vorhandene Datei wird vorher
  als Kopie aufbewahrt. ``muster_anlegen``: ein neutraler, deutlich als MUSTER markierter Vertragstext mit allen
  Platzhaltern – zum Ersetzen durch den eigenen, geprüften Wortlaut.
Rein bis auf Lesen und Schreiben der Dateien.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

_ORIG: dict = {}

BESCHREIBUNG = {
    "Mietvertrag.vorlage": ("Vertragstext (Pflicht)", "Text mit Platzhaltern wie {vorname}, {zimmer_kurz}, {miete}"),
    "Wohnungsgeberbestaetigung.pdf": ("Wohnungsgeberbestätigung", "PDF-Formular, wird vorausgefüllt angehängt"),
    "SEPA_Lastschriftmandat.pdf": ("SEPA-Lastschriftmandat", "PDF-Formular, wird vorausgefüllt angehängt"),
    "Mietschuldenfreiheitsbescheinigung.pdf": ("Mietschuldenfreiheitsbescheinigung", "PDF-Formular, wird angehängt"),
    "logo.jpg": ("Logo", "Bild oben rechts im Vertrag (optional)"),
}

MUSTER = """# MUSTER – vom Programm angelegt. Bitte den Wortlaut durch Ihren eigenen, geprüften Vertragstext ersetzen.
# Bearbeiten mit dem Editor (UTF-8). Zeichen am Zeilenanfang:
#   =Titel   ==§ 1 Überschrift (wird durchgezählt)   ^zentriert   >rechtsbündig   1. Absatz mit Nummer   +eingerückt
#   |Links|Rechts (Tabelle)   ---SEITE--- (neue Seite)   @UNTERSCHRIFT (Unterschriftenfeld)   # Kommentar
#   ?kaution Text  nur mit Mietsicherheit      ?!kaution Text  nur ohne Mietsicherheit
#   ?flexibel Text nur im flexiblen Vertrag    ?!flexibel Text nur im üblichen Vertrag
#   [weiblich|männlich] wählt nach Anrede, z. B. [die Mieterin|der Mieter]
# Platzhalter: {nr} {anrede} {vorname} {nachname} {name} {haus} {zimmer} {zimmer_kurz} {flaeche} {schluessel}
#   {von} {bis} {miete} {kaution_bis} {mieter_adresse} {vermieterin_adresse} {ort}
=Mietvertrag Nr. {nr}
^MUSTER – Text bitte durch den eigenen Vertragstext ersetzen

Zwischen
^{vermieterin_adresse}
^– Vermieterin –
und
^{anrede} {vorname} {nachname}
^– [Mieterin|Mieter] –

==§ 1 Mietsache
1. Vermietet wird das möblierte Zimmer {zimmer_kurz} (Haus {haus}, ca. {flaeche} m²) in {mieter_adresse}.
2. [Die Mieterin|Der Mieter] erhält {schluessel} Schlüssel.
==§ 2 Mietzeit
1. Das Mietverhältnis beginnt am {von} und endet am {bis}.
==§ 3 Miete
1. Die monatliche Miete beträgt {miete}. (MUSTER: Fälligkeit, Zahlungsweise und Nebenkosten ergänzen.)
==§ 4 Mietsicherheit
?kaution 1. Eine Mietsicherheit ist bis zum {kaution_bis} zu leisten. (MUSTER: Höhe ergänzen.)
?!kaution 1. Eine Mietsicherheit wird nicht vereinbart.
==§ 5 Rückgabe
1. Bei Ende des Mietverhältnisses ist das Zimmer geräumt und mit allen Schlüsseln zurückzugeben.
==§ 6 Weitere Vereinbarungen
1. (MUSTER: Hausordnung, Kündigung und weitere Vereinbarungen ergänzen.)
@UNTERSCHRIFT
"""


def _mt():
    from belegung import mieter as mt

    return mt


def _orte() -> list[tuple[str, Path]]:
    """(Bezeichnung, Basisordner) in Suchreihenfolge."""
    from belegung import konfig, speicher

    erg = [("Standort", Path(speicher.pfad("")))]
    try:
        from . import netz_kern

        erg.append(("gemeinsam", Path(netz_kern.basis())))
    except Exception:                              # noqa: BLE001 – ohne Netzwerkbetrieb: nur Standort/Programm
        pass
    erg.append(("Programm", Path(konfig.programmordner())))
    gesehen, eindeutig = set(), []
    for wo, p in erg:
        if str(p) not in gesehen:
            gesehen.add(str(p))
            eindeutig.append((wo, p))
    return eindeutig


def ordner_suchen() -> Path | None:
    """Ordner mit ``Mietvertrag.vorlage`` (Standort → gemeinsam → Programm), sonst der erste vorhandene."""
    mt = _mt()
    vorhanden = [b / mt.VORLAGEN_ORDNER for _, b in _orte() if (b / mt.VORLAGEN_ORDNER).is_dir()]
    return next((o for o in vorhanden if (o / mt.VERTRAG).is_file()), vorhanden[0] if vorhanden else None)


def zielordner() -> Path:
    """Wohin neue Vorlagen gespeichert werden: gemeinsamer Datenordner (bleibt bei Updates, gilt für alle Standorte)."""
    mt = _mt()
    orte = dict(_orte())
    return (orte.get("gemeinsam") or orte["Standort"]) / mt.VORLAGEN_ORDNER


@dataclass
class Status:
    datei: str
    titel: str
    text: str
    pfad: Path | None         # gefunden in …
    pflicht: bool

    @property
    def da(self) -> bool:
        return self.pfad is not None


def status() -> list[Status]:
    mt = _mt()
    o = ordner_suchen()
    erg = []
    for datei in [*mt.VORLAGEN, mt.LOGO]:
        titel, text = BESCHREIBUNG.get(datei, (datei, ""))
        p = o / datei if o is not None and (o / datei).is_file() else None
        erg.append(Status(datei, titel, text, p, datei == mt.VERTRAG))
    return erg


def vertrag_fehlt() -> bool:
    return not any(s.da for s in status() if s.pflicht)


def ist_muster() -> bool:
    mt = _mt()
    o = ordner_suchen()
    try:
        return o is not None and (o / mt.VERTRAG).read_text(encoding="utf-8").startswith("# MUSTER")
    except OSError:
        return False


def fehlende_optional() -> list[str]:
    return [s.titel for s in status() if not s.da and not s.pflicht and s.datei != _mt().LOGO]


def _pruefen_name(datei: str) -> None:
    if datei not in BESCHREIBUNG:
        raise ValueError(f"Unbekannte Vorlage: {datei}")


def einrichten(datei: str, inhalt: bytes) -> str:
    """Vorlage speichern (gemeinsamer Datenordner). Vorhandene Datei bleibt als Kopie „….bis-<Zeit>“ erhalten."""
    from belegung import protokoll

    from .benutzer_kern import admin_pruefen

    _pruefen_name(datei)
    admin_pruefen("Vertragsvorlagen ändern")
    if datei.endswith(".vorlage"):
        try:
            text = inhalt.decode("utf-8-sig")
        except UnicodeDecodeError:
            try:
                text = inhalt.decode("cp1252")
            except UnicodeDecodeError as exc:
                raise ValueError("Der Vertragstext muss eine Textdatei sein (z. B. im Editor gespeichert).") from exc
        if "{" not in text:
            raise ValueError("Im Vertragstext steht kein Platzhalter wie {vorname} – ist das die richtige Datei?")
        inhalt = text.encode("utf-8")
    elif datei.endswith(".pdf") and not inhalt.startswith(b"%PDF"):
        raise ValueError(f"{datei} ist keine PDF-Datei.")
    elif datei.endswith(".jpg") and not inhalt.startswith(b"\xff\xd8"):
        raise ValueError("Das Logo muss ein JPG-Bild sein.")
    ziel = zielordner()
    ziel.mkdir(parents=True, exist_ok=True)
    p = ziel / datei
    alt = ""
    if p.exists():
        kopie = p.with_name(f"{p.name}.bis-{datetime.now():%Y%m%d-%H%M%S}")
        p.replace(kopie)
        alt = f" (die bisherige liegt daneben als {kopie.name})"
    p.write_bytes(inhalt)
    protokoll.eintragen([{"aktion": "Vertragsvorlage gespeichert", "name": datei, "person": "", "alt": "",
                          "neu": str(p), "von": "", "quelle": "Mieter · Vorlagen"}])
    return f"{BESCHREIBUNG[datei][0]} gespeichert in {ziel}{alt}"


def muster_anlegen() -> str:
    """Neutralen MUSTER-Vertragstext anlegen – nur, wenn noch keiner da ist (nie überschreiben)."""
    mt = _mt()
    if not vertrag_fehlt():
        raise ValueError("Es gibt schon einen Vertragstext – das Muster wird nicht darübergeschrieben.")
    return einrichten(mt.VERTRAG, MUSTER.encode("utf-8")).replace("Vertragstext (Pflicht)", "Muster-Vertragstext")


# ---- Einhängen ---------------------------------------------------------------------------------------------------------

def installieren() -> None:
    mt = _mt()
    if _ORIG:
        return
    _ORIG["vorlagen_ordner"] = mt.vorlagen_ordner
    _ORIG["fehlende_vorlagen"] = mt.fehlende_vorlagen
    mt.vorlagen_ordner = ordner_suchen
    mt.fehlende_vorlagen = lambda: [] if not vertrag_fehlt() else [mt.VERTRAG]   # nur der Vertragstext ist Pflicht


def zuruecksetzen() -> None:
    mt = _mt()
    for k, f in list(_ORIG.items()):
        setattr(mt, k, f)
    _ORIG.clear()


einrichten.ohne_rueckgaengig = True        # Datei statt Schritt – die alte Fassung bleibt als Kopie daneben
muster_anlegen.ohne_rueckgaengig = True
