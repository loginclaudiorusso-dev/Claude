"""1.33: Benutzerkonten – eine gemeinsame Installation, jede Person meldet sich an. Rein, ohne NiceGUI.

* **Konten** liegen im gemeinsamen Datenordner (``importe/modern_benutzer.json`` im Goslar-Ordner = Basis), also für
  alle PCs und alle Standorte dieselben. Passwörter nur als Hash (PBKDF2-SHA256, eigenes Salz je Konto).
* **Anmelden:** automatisch über das Windows-Konto, wenn der Administrator es dem Benutzer zugeordnet hat (kein
  Passwort nötig, Windows hat schon geprüft) – sonst mit Anmeldename und Passwort. Nach vom Administrator gesetztem
  Passwort muss man es beim ersten Anmelden ändern.
* **Rollen:** Administrator (alles, auch Benutzer verwalten, alle Standorte) und Mitarbeiter/in (nur die freigegebenen
  Standorte).
* **Solange es kein Konto gibt,** läuft INNternat wie bisher ohne Anmeldung; der erste Administrator wird unter
  Einstellungen → Benutzer angelegt. Notfall (Administrator-Passwort vergessen): eine leere Datei
  ``ADMIN_ZURUECKSETZEN.txt`` in den Datenordner legen – dann darf beim nächsten Start ein neuer Administrator angelegt
  werden, die Datei wird danach entfernt. Wer Zugriff auf den Datenordner hat, kann ohnehin alle Dateien lesen: die
  Anmeldung schützt das Programm, nicht die Dateien – die schützt die Ordnerfreigabe.
* **Angemeldet ist der Programmprozess** (jeder PC startet INNternat selbst, die Oberfläche hört nur auf diesem PC).
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import re
import secrets
import tempfile
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path

DATEI = "importe/modern_benutzer.json"
NOTFALL = "ADMIN_ZURUECKSETZEN.txt"
ROLLEN = {"admin": "Administrator", "mitarbeiter": "Mitarbeiter/in"}
STANDORTE = ("GS", "BP", "WE")
RUNDEN = 240_000
MIN_LAENGE = 8
FEHL_MAX = 5                       # danach je Anmeldename kurz warten
FEHL_PAUSE = 30.0
_KENNUNG = re.compile(r"^[a-z0-9][a-z0-9._@-]{1,59}$")


@dataclass
class Konto:
    kennung: str                   # Anmeldename (klein), z. B. „m.muster“ oder eine E-Mail-Adresse
    name: str                      # Anzeigename, steht im Verlauf („gespeichert von …“)
    rolle: str = "mitarbeiter"
    standorte: list[str] = field(default_factory=list)
    windows: str = ""              # Windows-Anmeldename für die automatische Anmeldung (leer = nur mit Passwort)
    pw: str = ""                   # pbkdf2$runden$salz$hash
    muss_aendern: bool = False
    aktiv: bool = True
    erstellt: str = ""
    zuletzt: str = ""

    @property
    def admin(self) -> bool:
        return self.rolle == "admin"

    def erlaubt(self) -> list[str]:
        return list(STANDORTE) if self.admin else [s for s in STANDORTE if s in self.standorte]


# ---- Ablage --------------------------------------------------------------------------------------------------------

def _pfad() -> Path:
    from . import netz_kern

    return netz_kern.basis() / DATEI


def _lesen() -> dict:
    from . import netz_kern

    p = _pfad()
    if not p.exists():
        return {"konten": []}
    try:
        d = json.loads(netz_kern.text_lesen(p))
    except ValueError as exc:      # beschädigt: lieber melden als alle aussperren oder leer überschreiben
        raise ValueError(f"Die Benutzerdatei ist beschädigt ({p}). Bitte aus der Sicherung holen.") from exc
    return d if isinstance(d, dict) else {"konten": []}


def _schreiben(d: dict) -> None:
    from . import netz_kern

    p = _pfad()
    p.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=p.name, suffix=".tmp", dir=p.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(d, f, ensure_ascii=False, indent=2)
        netz_kern.ersetzen(tmp, p)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise


def _konto(x: dict) -> Konto:
    return Konto(**{k: x[k] for k in Konto.__dataclass_fields__ if k in x})


def konten() -> list[Konto]:
    return [_konto(x) for x in _lesen().get("konten") or [] if isinstance(x, dict) and x.get("kennung")]


def finden(kennung: str) -> Konto | None:
    k = norm(kennung)
    return next((x for x in konten() if x.kennung == k), None)


def eingerichtet() -> bool:
    """Gibt es mindestens einen aktiven Administrator? Erst dann wird eine Anmeldung verlangt."""
    return any(k.admin and k.aktiv for k in konten())


def _aendern(fn) -> object:
    """Lesen, ändern, schreiben – unter der Schreibsperre (mehrere PCs)."""
    from . import netz_kern

    with netz_kern.sperre():
        d = _lesen()
        ks = [_konto(x) for x in d.get("konten") or [] if isinstance(x, dict) and x.get("kennung")]
        erg = fn(ks)
        d["konten"] = [asdict(k) for k in ks]
        _schreiben(d)
    return erg


# ---- Passwörter ----------------------------------------------------------------------------------------------------

def hash_bilden(pw: str, salz: bytes | None = None, runden: int = RUNDEN) -> str:
    salz = salz or secrets.token_bytes(16)
    h = hashlib.pbkdf2_hmac("sha256", pw.encode("utf-8"), salz, runden)
    return f"pbkdf2${runden}${salz.hex()}${h.hex()}"


def hash_pruefen(pw: str, gespeichert: str) -> bool:
    try:
        art, runden, salz, h = gespeichert.split("$")
        if art != "pbkdf2":
            return False
        neu = hashlib.pbkdf2_hmac("sha256", (pw or "").encode("utf-8"), bytes.fromhex(salz), int(runden))
    except (ValueError, AttributeError):
        return False
    return hmac.compare_digest(neu.hex(), h)


def pw_pruefen(pw: str) -> None:
    if len(pw or "") < MIN_LAENGE:
        raise ValueError(f"Das Passwort braucht mindestens {MIN_LAENGE} Zeichen.")
    if pw.strip() != pw:
        raise ValueError("Das Passwort darf nicht mit Leerzeichen beginnen oder enden.")


def start_passwort() -> str:
    """Vorschlag für ein Startpasswort (gut abzutippen: ohne 0/O, 1/l/I)."""
    zeichen = "abcdefghjkmnpqrstuvwxyz23456789"
    return "-".join("".join(secrets.choice(zeichen) for _ in range(4)) for _ in range(3))


# ---- Prüfen der Eingaben -------------------------------------------------------------------------------------------

def norm(kennung: str) -> str:
    return (kennung or "").strip().lower()


def _kennung_pruefen(k: str) -> str:
    k = norm(k)
    if not _KENNUNG.match(k):
        raise ValueError("Anmeldename: 2–60 Zeichen, nur Buchstaben a–z, Ziffern und . _ @ - (z. B. „m.muster“ oder "
                         "die E-Mail-Adresse).")
    return k


def _standorte_pruefen(rolle: str, standorte) -> list[str]:
    if rolle not in ROLLEN:
        raise ValueError("Unbekannte Rolle.")
    st = [s for s in STANDORTE if s in set(standorte or [])]
    if rolle != "admin" and not st:
        raise ValueError("Bitte mindestens einen Standort freigeben.")
    return st


def _windows_pruefen(ks: list[Konto], windows: str, ausser: str = "") -> str:
    w = (windows or "").strip()
    if "\\" in w:                  # „DOMÄNE\name“ → „name“ (so liefert Windows den Namen auch)
        w = w.rsplit("\\", 1)[1]
    if w and any(k.windows.lower() == w.lower() and k.kennung != ausser for k in ks):
        raise ValueError(f"Das Windows-Konto „{w}“ ist schon einem anderen Benutzer zugeordnet.")
    return w


def _admins_bleiben(ks: list[Konto]) -> None:
    if not any(k.admin and k.aktiv for k in ks):
        raise ValueError("Es muss mindestens ein aktiver Administrator bleiben.")


def _jetzt() -> str:
    return datetime.now().isoformat(timespec="minutes")


# ---- Wer ist angemeldet (dieser Programmprozess) --------------------------------------------------------------------

_AKTUELL: dict = {"konto": None}
_FEHL: dict[str, list[float]] = {}


def aktuell() -> Konto | None:
    return _AKTUELL["konto"]


def setzen(k: Konto | None) -> None:
    _AKTUELL["konto"] = k


def abmelden() -> None:
    _AKTUELL["konto"] = None


def ist_admin() -> bool:
    k = aktuell()
    return k is None or k.admin    # ohne Konten (nicht eingerichtet) wie bisher: alles erlaubt


def erlaubte_standorte() -> list[str]:
    k = aktuell()
    return list(STANDORTE) if k is None else k.erlaubt()


def anzeige() -> str:
    k = aktuell()
    return k.name if k else ""


def admin_pruefen(was: str) -> None:
    """1.61: Heikle Änderungen (Sicherung zurückspielen, Stammdaten, Regeln, Zimmer anlegen, KI-Mail-Erkennung) nur
    für Administratoren – sobald Benutzerkonten eingerichtet sind. Ohne Konten bleibt alles wie bisher erlaubt."""
    if eingerichtet() and not ist_admin():
        raise ValueError(f"{was} darf nur ein Administrator.")


def _admin_noetig() -> None:
    if eingerichtet() and not (aktuell() and aktuell().admin):
        raise ValueError("Nur ein Administrator darf Benutzer verwalten.")


# ---- Anmelden ------------------------------------------------------------------------------------------------------

def windows_konto(windows: str | None = None) -> Konto | None:
    from . import netz_kern

    w = (windows if windows is not None else netz_kern.benutzer() or "").strip().lower()
    if not w:
        return None
    return next((k for k in konten() if k.aktiv and k.windows and k.windows.lower() == w), None)


def anmelden(kennung: str, pw: str, jetzt: float | None = None) -> Konto:
    """Anmeldename + Passwort prüfen. Nach ``FEHL_MAX`` Fehlversuchen kurz sperren. ValueError mit Text."""
    jetzt = time.monotonic() if jetzt is None else jetzt
    k_ = norm(kennung)
    fehl = [t for t in _FEHL.get(k_, []) if jetzt - t < FEHL_PAUSE]
    if len(fehl) >= FEHL_MAX:
        raise ValueError(f"Zu viele Fehlversuche – bitte {int(FEHL_PAUSE - (jetzt - fehl[0])) + 1} Sekunden warten.")
    k = finden(k_)
    if k is None or not k.pw or not hash_pruefen(pw, k.pw):
        _FEHL[k_] = fehl + [jetzt]
        raise ValueError("Anmeldename oder Passwort stimmt nicht.")
    if not k.aktiv:
        raise ValueError("Dieses Konto ist gesperrt – bitte den Administrator fragen.")
    _FEHL.pop(k_, None)
    return k


def angemeldet(k: Konto) -> Konto:
    """Nach erfolgreicher Anmeldung: merken und „zuletzt“ notieren (Fehler beim Notieren stören nicht)."""
    setzen(k)
    try:
        def f(ks):
            for x in ks:
                if x.kennung == k.kennung:
                    x.zuletzt = _jetzt()
        _aendern(f)
    except Exception:              # noqa: BLE001 – „zuletzt“ ist nur Zusatz (z. B. Besetzt, Netz weg)
        pass
    return k


def passwort_aendern(alt: str, neu: str, wiederholung: str) -> str:
    k = aktuell()
    if k is None:
        raise ValueError("Nicht angemeldet.")
    if neu != wiederholung:
        raise ValueError("Die beiden neuen Passwörter sind verschieden.")
    pw_pruefen(neu)
    if k.pw and not k.muss_aendern and not hash_pruefen(alt, k.pw):
        raise ValueError("Das bisherige Passwort stimmt nicht.")
    if k.pw and hash_pruefen(neu, k.pw):
        raise ValueError("Bitte ein anderes Passwort als bisher wählen.")
    h = hash_bilden(neu)

    def f(ks):
        for x in ks:
            if x.kennung == k.kennung:
                x.pw, x.muss_aendern = h, False
                return x
        raise ValueError("Das Konto gibt es nicht mehr.")
    setzen(_aendern(f))
    return "Passwort geändert"


# ---- Verwalten (nur Administrator) ---------------------------------------------------------------------------------

def notfall() -> bool:
    from . import netz_kern

    return (netz_kern.basis() / NOTFALL).exists()


def ersten_admin_anlegen(kennung: str, name: str, pw: str, wiederholung: str, windows: str = "") -> Konto:
    """Nur wenn es noch keinen Administrator gibt – oder im Notfall (Datei ``ADMIN_ZURUECKSETZEN.txt``)."""
    from . import netz_kern

    if eingerichtet() and not notfall():
        raise ValueError("Es gibt schon einen Administrator – bitte anmelden.")
    if pw != wiederholung:
        raise ValueError("Die beiden Passwörter sind verschieden.")
    pw_pruefen(pw)
    k_ = _kennung_pruefen(kennung)
    if not (name or "").strip():
        raise ValueError("Bitte einen Namen eintragen.")

    def f(ks):
        w = _windows_pruefen(ks, windows, ausser=k_)
        neu = Konto(k_, name.strip(), "admin", list(STANDORTE), w, hash_bilden(pw), False, True, _jetzt(), _jetzt())
        ks[:] = [x for x in ks if x.kennung != k_] + [neu]
        return neu
    k = _aendern(f)
    try:
        (netz_kern.basis() / NOTFALL).unlink(missing_ok=True)
    except OSError:
        pass
    setzen(k)
    return k


def anlegen(kennung: str, name: str, rolle: str, standorte, windows: str = "", start_pw: str = "") -> str:
    _admin_noetig()
    k_ = _kennung_pruefen(kennung)
    if not (name or "").strip():
        raise ValueError("Bitte einen Namen eintragen.")
    st = _standorte_pruefen(rolle, standorte)
    if start_pw:
        pw_pruefen(start_pw)

    def f(ks):
        if any(x.kennung == k_ for x in ks):
            raise ValueError(f"Den Anmeldenamen „{k_}“ gibt es schon.")
        w = _windows_pruefen(ks, windows)
        if not w and not start_pw:
            raise ValueError("Bitte ein Startpasswort vergeben oder ein Windows-Konto zuordnen – sonst kann sich "
                             "niemand anmelden.")
        ks.append(Konto(k_, name.strip(), rolle, st, w, hash_bilden(start_pw) if start_pw else "", bool(start_pw),
                        True, _jetzt(), ""))
    _aendern(f)
    return f"Benutzer „{name.strip()}“ angelegt"


def bearbeiten(kennung: str, name: str, rolle: str, standorte, windows: str, aktiv: bool) -> str:
    _admin_noetig()
    k_ = norm(kennung)
    st = _standorte_pruefen(rolle, standorte)
    if not (name or "").strip():
        raise ValueError("Bitte einen Namen eintragen.")
    ich = aktuell()
    if ich and ich.kennung == k_ and (not aktiv or rolle != "admin"):
        raise ValueError("Sie können sich nicht selbst sperren oder die Administrator-Rolle nehmen.")

    def f(ks):
        x = next((x for x in ks if x.kennung == k_), None)
        if x is None:
            raise ValueError("Diesen Benutzer gibt es nicht mehr.")
        w = _windows_pruefen(ks, windows, ausser=k_)
        if not w and not x.pw:
            raise ValueError("Ohne Windows-Konto braucht der Benutzer ein Passwort – bitte zuerst eins vergeben.")
        x.name, x.rolle, x.standorte, x.windows, x.aktiv = name.strip(), rolle, st, w, bool(aktiv)
        _admins_bleiben(ks)
        return x
    x = _aendern(f)
    if ich and ich.kennung == k_:
        setzen(x)
    return "Gespeichert"


def passwort_zuruecksetzen(kennung: str, neu: str) -> str:
    """Administrator vergibt ein neues Startpasswort; der Benutzer muss es beim nächsten Anmelden ändern."""
    _admin_noetig()
    pw_pruefen(neu)
    k_ = norm(kennung)
    h = hash_bilden(neu)

    def f(ks):
        x = next((x for x in ks if x.kennung == k_), None)
        if x is None:
            raise ValueError("Diesen Benutzer gibt es nicht mehr.")
        x.pw, x.muss_aendern = h, True
    _aendern(f)
    _FEHL.pop(k_, None)
    return "Neues Startpasswort gesetzt – beim nächsten Anmelden muss es geändert werden"


def loeschen(kennung: str) -> str:
    _admin_noetig()
    k_ = norm(kennung)
    ich = aktuell()
    if ich and ich.kennung == k_:
        raise ValueError("Sie können Ihr eigenes Konto nicht löschen.")

    def f(ks):
        vorher = len(ks)
        ks[:] = [x for x in ks if x.kennung != k_]
        if len(ks) == vorher:
            raise ValueError("Diesen Benutzer gibt es nicht mehr.")
        _admins_bleiben(ks)
    _aendern(f)
    return "Benutzer gelöscht"
