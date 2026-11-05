"""Betrieb aus einem gemeinsamen Netzwerkordner (0.54). Rein, ohne NiceGUI.

Aufbau im Netzwerk::

    INNternat\\
        INNternat starten.bat     ← jeder PC startet hierüber
        Programm\\                 ← wird bei einem Update ersetzt
        Daten\\                    ← gemeinsame Daten aller PCs, bleibt bei Updates unangetastet

Jeder PC startet das Programm selbst. Damit sich 7–8 PCs nicht in die Quere kommen:

* **Speichern mit Wiederholung:** Unter Windows schlägt das Ersetzen einer Datei auf einem Netzlaufwerk fehl
  („Zugriff verweigert“), solange ein anderer PC sie gerade liest. Ersetzen und Lesen werden deshalb einige Sekunden
  lang wiederholt. Bleibt eine Datei gesperrt, wird gemeldet statt still mit leeren Daten weitergerechnet.
* **Schreibsperre:** Jede Änderung (ein „Schritt“) läuft unter einer kurzen Sperre im Datenordner (``.innternat_sperre``).
  Zwei PCs schreiben also nie gleichzeitig. Eine Sperre, die älter als ``SPERRE_ALT`` Sekunden ist (PC abgestürzt), gilt
  als verwaist und wird übernommen.
* **Wer hat geändert:** Nach jedem Schritt steht in ``modern_letzte_aenderung.json``, was zuletzt von wem gespeichert
  wurde. Die anderen PCs laden neu und zeigen es kurz an.
* **Persönliches bleibt am PC:** Darstellung, „Später“, Begrüßung und der zuletzt gewählte Standort liegen unter
  ``%LOCALAPPDATA%\\INNternat`` – nicht im gemeinsamen Ordner, wo jeder die Einstellungen der anderen überschreiben würde.
* **Tägliche Sicherung:** Beim ersten Start des Tages sichert genau ein PC die Arbeitsdaten jedes Standorts (unter der
  Sperre, damit nicht acht PCs gleichzeitig sichern und die Sicherungen älterer Tage verdrängen).
* **Daten übernehmen:** Aus dem bisherigen Programmordner werden die Daten einmalig in den neuen Datenordner kopiert.
  Der alte Ordner bleibt unverändert und ist damit zugleich die Sicherung.

Das Hauptprogramm wird nicht geändert; die neue Oberfläche ersetzt zur Laufzeit nur einzelne Funktionen.
"""

from __future__ import annotations

import json
import logging
import os
import shutil
import socket
import tempfile
import threading
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

log = logging.getLogger(__name__)

LOKAL_ENV = "INNTERNAT_LOKAL"            # setzt „INNternat starten.bat“; sonst %LOCALAPPDATA%\INNternat
START_ENV = "INNTERNAT_START"            # Pfad der Startdatei (für „Mit Windows starten“)
LOKAL_DATEI = "einstellungen_lokal.json"
SPERRE = ".innternat_sperre"
SPERRE_WARTEN = 15.0                     # so lange wird auf einen anderen PC gewartet
SPERRE_ALT = 45.0                        # ältere Sperren gelten als verwaist (PC abgestürzt)
SPERRE_PULS = 10.0                       # 0.55: so oft frischt der Halter die Sperre auf – lange Schritte bleiben gültig
LETZTE = "modern_letzte_aenderung.json"
VERSUCHE = 12                            # Wiederholungen beim Ersetzen/Lesen (zusammen etwa 7 s)
_GESPERRT = {5, 32, 33}                  # WinError: Zugriff verweigert, Freigabeverletzung, Sperrverletzung


# ---------------------------------------------------------------------------------------
# Wer bin ich, wo liegt was
# ---------------------------------------------------------------------------------------

def rechner() -> str:
    return os.environ.get("COMPUTERNAME") or socket.gethostname() or "PC"


def benutzer() -> str:
    try:
        import getpass

        return os.environ.get("USERNAME") or getpass.getuser()
    except Exception:                    # noqa: BLE001 – ohne Benutzernamen geht es auch
        return ""


def wer() -> str:
    b = benutzer()
    return f"{b} an {rechner()}" if b else rechner()


def lokal_ordner() -> Path:
    if v := os.environ.get(LOKAL_ENV):
        return Path(v)
    if v := os.environ.get("LOCALAPPDATA"):
        return Path(v) / "INNternat"
    return Path.home() / ".innternat"


def netzbetrieb() -> bool:
    """Gestartet über „INNternat starten.bat“ (eigener Datenordner neben dem Programm)."""
    return bool(os.environ.get(START_ENV))


def basis() -> Path:
    """Gemeinsamer Datenordner (Goslar-Ordner, darunter ``Standorte/…``)."""
    from . import standort_kern

    return standort_kern._BASIS()


# ---------------------------------------------------------------------------------------
# Wiederholen bei gesperrten Dateien
# ---------------------------------------------------------------------------------------

def _gesperrt(exc: OSError) -> bool:
    return isinstance(exc, PermissionError) or getattr(exc, "winerror", None) in _GESPERRT


def _pause(i: int) -> float:
    return min(0.05 * (2 ** i), 1.0)


def ersetzen(quelle, ziel, versuche: int = VERSUCHE) -> None:
    """``os.replace`` mit Wiederholung, solange die Zieldatei von einem anderen PC gelesen wird."""
    for i in range(versuche):
        try:
            os.replace(quelle, ziel)
            return
        except OSError as exc:
            if not _gesperrt(exc) or i == versuche - 1:
                raise
            time.sleep(_pause(i))


def text_lesen(p: Path, versuche: int = VERSUCHE) -> str:
    for i in range(versuche):
        try:
            return p.read_text(encoding="utf-8")
        except OSError as exc:
            if not _gesperrt(exc) or i == versuche - 1:
                raise
            time.sleep(_pause(i))
    raise OSError(p)                     # pragma: no cover


class _OsMitWiederholung:
    """Steht in ``speicher``/``aenderungen`` an Stelle des Moduls ``os``: alles wie gehabt, nur ``replace`` wiederholt."""

    replace = staticmethod(ersetzen)

    def __getattr__(self, name):
        return getattr(os, name)


_ORIG: dict = {}


def installieren() -> None:
    """Einmal beim Start: Speichern und Lesen netzwerkfest machen, Pivot im Datenordner suchen."""
    if _ORIG:
        return
    from belegung import aenderungen, laden, speicher

    _ORIG.update(s_os=speicher.os, a_os=aenderungen.os, lesen=speicher.lesen, schnapp=aenderungen.schnappschuss,
                 laden_prog=laden.programmordner)
    speicher.os = _OsMitWiederholung()
    aenderungen.os = _OsMitWiederholung()

    def lesen(name, standard, ordner=None):
        p = speicher.pfad(name, ordner)
        if not p.exists():
            return standard
        try:
            text = text_lesen(p)
        except OSError as exc:
            if _gesperrt(exc):           # nicht still mit leeren Daten weiterrechnen (und dann überschreiben)
                raise OSError(f"{p.name} ist gerade von einem anderen PC gesperrt – bitte gleich noch einmal.") from exc
            log.warning("%s konnte nicht gelesen werden (%s) – verwende Standardwerte.", p.name, exc)
            return standard
        try:
            return json.loads(text)
        except json.JSONDecodeError as exc:
            log.warning("%s konnte nicht gelesen werden (%s) – verwende Standardwerte.", p.name, exc)
            return standard

    def schnappschuss(namen=None):
        erg = {}
        for name in namen or aenderungen._dateien():
            p = speicher.pfad(name)
            erg[name] = text_lesen(p) if p.exists() else None     # gesperrt → Fehler statt „Datei gab es nicht“
        return erg

    speicher.lesen = lesen
    aenderungen.schnappschuss = schnappschuss
    # Pivot-Datei: im (gemeinsamen) Datenordner suchen, nicht im Programmordner – der wird bei Updates ersetzt.
    laden.programmordner = basis


def zuruecksetzen() -> None:
    if not _ORIG:
        return
    from belegung import aenderungen, laden, speicher

    speicher.os, aenderungen.os = _ORIG["s_os"], _ORIG["a_os"]
    speicher.lesen, aenderungen.schnappschuss = _ORIG["lesen"], _ORIG["schnapp"]
    laden.programmordner = _ORIG["laden_prog"]
    _ORIG.clear()


# ---------------------------------------------------------------------------------------
# Schreibsperre (über alle PCs)
# ---------------------------------------------------------------------------------------

class Besetzt(ValueError):
    """Ein anderer PC speichert gerade (ValueError: wird in der Oberfläche als Hinweis gezeigt)."""


_rlock = threading.RLock()
_tiefe = {"n": 0}


def _sperre_pfad() -> Path:
    return basis() / SPERRE


def sperre_info() -> dict | None:
    try:
        return json.loads(_sperre_pfad().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def _sperren(warten: float, alt: float) -> None:
    p = _sperre_pfad()
    p.parent.mkdir(parents=True, exist_ok=True)
    ende = time.monotonic() + warten
    while True:
        try:
            fd = os.open(p, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            try:
                if time.time() - p.stat().st_mtime > alt:          # verwaist (PC abgestürzt)
                    log.warning("Verwaiste Schreibsperre übernommen: %s", sperre_info())
                    p.unlink(missing_ok=True)
                    continue
            except OSError:
                continue
            if time.monotonic() > ende:
                info = sperre_info() or {}
                von = info.get("wer") or "ein anderer PC"
                raise Besetzt(f"Gerade speichert {von}. Bitte in ein paar Sekunden noch einmal versuchen.") from None
            time.sleep(0.15)
            continue
        except OSError as exc:
            if _gesperrt(exc) and time.monotonic() <= ende:
                time.sleep(0.15)
                continue
            raise
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump({"wer": wer(), "pid": os.getpid(), "seit": datetime.now().isoformat(timespec="seconds")}, f)
        _puls_starten(p)
        return


_puls = {"stop": None}


def _puls_starten(p: Path) -> None:
    """Solange die Sperre gehalten wird, ihre Änderungszeit regelmäßig erneuern (Herzschlag)."""
    stop = threading.Event()
    _puls["stop"] = stop

    def schlagen() -> None:
        while not stop.wait(SPERRE_PULS):
            try:
                os.utime(p, None)
            except OSError:
                pass

    threading.Thread(target=schlagen, name="innternat-sperre", daemon=True).start()


def _freigeben() -> None:
    if _puls["stop"] is not None:
        _puls["stop"].set()
        _puls["stop"] = None
    for i in range(VERSUCHE):
        try:
            _sperre_pfad().unlink(missing_ok=True)
            return
        except OSError as exc:
            if not _gesperrt(exc) or i == VERSUCHE - 1:
                log.warning("Schreibsperre konnte nicht entfernt werden: %s", exc)
                return
            time.sleep(_pause(i))


@contextmanager
def sperre(warten: float | None = None, alt: float | None = None):
    """Exklusiv schreiben – über alle PCs (Datei im Datenordner) und alle Threads dieses Programms. Verschachtelbar."""
    with _rlock:
        if _tiefe["n"] == 0:
            _sperren(SPERRE_WARTEN if warten is None else warten, SPERRE_ALT if alt is None else alt)
        _tiefe["n"] += 1
        try:
            yield
        finally:
            _tiefe["n"] -= 1
            if _tiefe["n"] == 0:
                _freigeben()


# ---------------------------------------------------------------------------------------
# Wer hat zuletzt geändert
# ---------------------------------------------------------------------------------------

def notieren(titel: str) -> None:
    """Nach einem Schritt: was, wer, wann (im Ordner des aktiven Standorts)."""
    from belegung import speicher

    try:
        speicher.schreiben(LETZTE, {"titel": titel, "wer": wer(), "rechner": rechner(), "pid": os.getpid(),
                                    "zeit": datetime.now().isoformat(timespec="seconds")})
    except OSError as exc:
        log.warning("Letzte Änderung nicht notiert: %s", exc)


def letzte_aenderung() -> dict | None:
    from belegung import speicher

    try:
        d = speicher.lesen(LETZTE, None)
    except OSError:
        return None
    return d if isinstance(d, dict) else None


def von_anderem(d: dict | None) -> bool:
    return bool(d) and (d.get("rechner") != rechner() or d.get("pid") != os.getpid())


# ---------------------------------------------------------------------------------------
# Persönliche Einstellungen (je PC)
# ---------------------------------------------------------------------------------------

_lokal_lock = threading.Lock()


def lokal_lesen() -> dict:
    p = lokal_ordner() / LOKAL_DATEI
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return d if isinstance(d, dict) else {}


def lokal_schreiben(d: dict) -> None:
    p = lokal_ordner() / LOKAL_DATEI
    p.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=p.name, suffix=".tmp", dir=p.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(d, f, ensure_ascii=False, indent=2)
        ersetzen(tmp, p)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise


def _schluessel(name: str, je_standort: bool) -> str:
    if not je_standort:
        return name
    from . import standort_kern

    return f"{standort_kern.aktiv().kurz}:{name}"


def persoenlich(name: str, standard=None, je_standort: bool = True, gemeinsam: str = "modern_ui.json"):
    """Persönlicher Wert dieses PCs. Fehlt er noch, wird er einmalig aus der gemeinsamen Datei übernommen
    (so bleibt die bisherige Einstellung nach dem Umzug erhalten)."""
    from belegung import speicher

    k = _schluessel(name, je_standort)
    with _lokal_lock:
        d = lokal_lesen()
        if k in d:
            return d[k]
        try:
            if je_standort:
                alt = speicher.lesen(gemeinsam, {})
            else:
                from .standort_kern import haupt

                with haupt():
                    alt = speicher.lesen(gemeinsam, {})
        except OSError:
            alt = {}
        if isinstance(alt, dict) and name in alt:
            d[k] = alt[name]
            try:
                lokal_schreiben(d)
            except OSError:
                pass
            return alt[name]
    return standard


def persoenlich_setzen(name: str, wert, je_standort: bool = True) -> None:
    k = _schluessel(name, je_standort)
    with _lokal_lock:
        d = lokal_lesen()
        d[k] = wert
        lokal_schreiben(d)


# ---------------------------------------------------------------------------------------
# Tägliche Sicherung
# ---------------------------------------------------------------------------------------

def _standort_ordner() -> list[Path]:
    from . import standort_kern

    return [o for k in standort_kern.STANDORTE if (o := standort_kern.ordner(k)).is_dir()]


def tagessicherung(jetzt: datetime | None = None) -> list[str]:
    """Einmal am Tag (und beim ersten Start einer neuen Version) die Arbeitsdaten jedes Standorts sichern."""
    from belegung import datensicherung

    from . import __version__

    jetzt = jetzt or datetime.now()
    marke = __version__.replace(".", " ")
    erg = []
    with sperre(warten=30):
        for ordner in _standort_ordner():
            try:
                vorhanden = datensicherung.liste(ordner)
                neu = not any(marke in s.anlass for s in vorhanden)
                heute = any(s.zeit.date() == jetzt.date() for s in vorhanden)
                if heute and not neu:
                    continue
                s = datensicherung.sichern(f"vor Update {__version__}" if neu else f"Start {__version__}", ordner, jetzt)
                if s:
                    erg.append(f"{ordner.name}: {s.text}")
            except OSError as exc:
                log.warning("Tagessicherung %s fehlgeschlagen: %s", ordner, exc)
    return erg


# ---------------------------------------------------------------------------------------
# Daten aus dem bisherigen Ordner übernehmen
# ---------------------------------------------------------------------------------------

# Programmteile – werden nicht mitkopiert (alles andere sind Daten: JSON, Listen, Gebäudeplan, Vorlagen, Sicherungen …)
PROGRAMM_ORDNER = {"belegung", "modern_ui", "modern", "tests", ".venv", "venv", ".git", "__pycache__", ".pytest_cache",
                   "build", "dist", "_internal", ".nicegui", "Programm", "assets"}
PROGRAMM_DATEIEN = {"README.md", "ROLLBACK.md", "OFFENE_PUNKTE.md", "UX_KONZEPT.md", "FEATURES.md", "requirements.txt",
                    ".gitignore", SPERRE}
PROGRAMM_ENDUNGEN = {".py", ".pyc", ".pyw", ".bat", ".cmd", ".spec", ".exe", ".dll", ".log", ".tmp"}


def ist_programmteil(rel: Path) -> bool:
    if any(t in PROGRAMM_ORDNER for t in rel.parts[:-1]):
        return True
    return rel.name in PROGRAMM_DATEIEN or rel.suffix.lower() in PROGRAMM_ENDUNGEN or rel.name.startswith("~$")


# Hilfsdateien – zählen nicht als „Daten vorhanden“: Sie entstehen schon beim ersten Start von selbst (Reinigungs-
# Abgleich, Zimmerhistorie, Neu-Markierung …), bevor jemand die Daten übernehmen konnte.
NEBENSACHE = {LETZTE, "modern_ui.json", "modern_ui_neu.json", "modern_standort.json", "reinigung_erledigt.json",
              "modern_zimmerhistorie.json"}


def hat_daten(ordner: Path) -> bool:
    """Liegen in ``ordner`` schon Arbeitsdaten (JSON im Ordner oder in ``importe``)?"""
    try:
        return any(p.is_file() and p.name not in NEBENSACHE for p in ordner.glob("*.json")) or \
            any(p.name not in NEBENSACHE for p in (ordner / "importe").glob("*.json"))
    except OSError:
        return False


@dataclass
class Uebernahme:
    quelle: Path
    dateien: list[Path] = field(default_factory=list)       # relativ zur Quelle
    bytes: int = 0
    probleme: list[str] = field(default_factory=list)
    standorte: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.probleme and bool(self.dateien)

    @property
    def text(self) -> str:
        mb = self.bytes / 1_000_000
        s = f"{len(self.dateien)} Dateien ({mb:.1f} MB)"
        return s + (f" · Standorte: {', '.join(self.standorte)}" if self.standorte else "")


def uebernahme_pruefen(quelle: str | Path, ziel: Path | None = None) -> Uebernahme:
    q = Path(str(quelle).strip().strip('"'))
    ziel = ziel or basis()
    u = Uebernahme(q)
    if not str(quelle).strip():
        u.probleme.append("Bitte den bisherigen Ordner angeben.")
        return u
    if not q.is_dir():
        u.probleme.append(f"Den Ordner „{q}“ gibt es nicht (oder er ist von hier nicht erreichbar).")
        return u
    try:
        if q.resolve() == ziel.resolve() or ziel.resolve() in q.resolve().parents or q.resolve() in ziel.resolve().parents:
            u.probleme.append("Das ist der neue Datenordner selbst (oder liegt darin) – bitte den bisherigen Ordner wählen.")
            return u
    except OSError:
        pass
    if not hat_daten(q):
        u.probleme.append("In diesem Ordner liegen keine INNternat-Daten (keine .json-Dateien). Gemeint ist der Ordner, "
                          "in dem bisher „Start.bat“ bzw. das Programm lag.")
        return u
    for wurzel, ordner, dateien in os.walk(q):
        rel_w = Path(wurzel).relative_to(q)
        ordner[:] = [o for o in ordner if o not in PROGRAMM_ORDNER]
        for n in dateien:
            rel = rel_w / n
            if ist_programmteil(rel):
                continue
            u.dateien.append(rel)
            try:
                u.bytes += (Path(wurzel) / n).stat().st_size
            except OSError:
                pass
    u.dateien.sort()
    u.standorte = ["Goslar"] + [k for k in ("BP", "WE") if hat_daten(q / "Standorte" / k)]
    if hat_daten(ziel):
        u.probleme.append("Im neuen Datenordner liegen schon Daten. Übernehmen geht nur in einen leeren Datenordner – "
                          "sonst würden aktuelle Daten überschrieben.")
    return u


def uebernehmen(quelle: str | Path, ziel: Path | None = None) -> str:
    """Daten kopieren (der alte Ordner bleibt unverändert). Gespeicherte Pfade zur Pivot-Datei werden umgestellt."""
    ziel = ziel or basis()
    with sperre(warten=30):
        u = uebernahme_pruefen(quelle, ziel)
        if not u.ok:
            raise ValueError(" ".join(u.probleme) or "Nichts zu übernehmen.")
        if any(ziel.glob("*.json")) or any((ziel / "importe").glob("*.json")):
            from belegung import datensicherung   # Hilfsdateien des ersten Starts vorher sichern – nichts geht verloren

            datensicherung.sichern("vor Übernahme", ziel)
        for rel in u.dateien:
            (ziel / rel).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(u.quelle / rel, ziel / rel)
        _pfade_umstellen(u.quelle, ziel)
    log.info("Daten übernommen aus %s: %s", u.quelle, u.text)
    return f"Übernommen: {u.text}. Bitte INNternat einmal schließen und neu starten."


def _pfade_umstellen(alt: Path, neu: Path) -> None:
    """``einstellungen.json`` → ``quelle`` (Pivot): zeigt sie in den alten Ordner, auf die Kopie im neuen umstellen."""
    p = neu / "einstellungen.json"
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return
    q = d.get("quelle") if isinstance(d, dict) else None
    if not q:
        return
    try:
        rel = Path(q).resolve().relative_to(alt.resolve())
    except (ValueError, OSError):
        return
    if (neu / rel).exists():
        d["quelle"] = str(neu / rel)
        p.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")


# ---------------------------------------------------------------------------------------
# Neue Version im Netzwerkordner?
# ---------------------------------------------------------------------------------------

def version_auf_platte() -> str:
    """Version, die gerade im Programmordner liegt (nach einem Update ggf. neuer als die laufende)."""
    import re

    p = Path(__file__).resolve().parent / "__init__.py"
    try:
        m = re.search(r'__version__\s*=\s*"([^"]+)"', text_lesen(p, 3))
    except OSError:
        return ""
    return m.group(1) if m else ""
