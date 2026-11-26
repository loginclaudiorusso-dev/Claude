"""1.72: Ladezeiten messen – welche Seite ist auf diesem PC langsam, und woran liegt es?

Langsam ist es oft nur im echten Netz (Netzlaufwerk, große Pivot-Datei, Outlook). Deshalb misst das Programm selbst:
* ``installieren``: hängt sich an die drei Ladestufen der Oberfläche – Daten voll laden, Daten der Seite laden, Seite
  aufbauen – und an das Einlesen der Auswertung (Pivot). Jede Messung: Zeit, Stufe, Seite/Ansicht, Dauer.
* Gemerkt werden die letzten Messungen im Speicher und in ``%LOCALAPPDATA%\\INNternat\\ladezeiten.log`` (nur dieser PC,
  keine Namen oder Inhalte – nur Seitennamen und Sekunden).
* ``bericht``: die langsamsten Schritte und je Seite der Mittelwert – zum Anzeigen und zum Kopieren.
Rein bis auf das Schreiben der Protokolldatei.
"""

from __future__ import annotations

import functools
import logging
import threading
import time
from collections import deque
from dataclasses import dataclass
from datetime import datetime

log = logging.getLogger(__name__)
MAX = 500
LANGSAM = 3.0               # Sekunden – ab hier „langsam“
_MESSUNGEN: deque = deque(maxlen=MAX)
_SPERRE = threading.Lock()
_AN = {"ok": False}
STUFEN = {"_voll_laden": "Daten laden", "_seite_laden": "Seitendaten", "zeichnen": "Aufbau",
          "datenstand": "Pivot/Auswertung einlesen"}


@dataclass
class Messung:
    zeit: str
    stufe: str
    seite: str
    dauer: float


def merken(stufe: str, seite: str, dauer: float) -> None:
    m = Messung(datetime.now().strftime("%d.%m. %H:%M:%S"), STUFEN.get(stufe, stufe), seite, round(dauer, 2))
    with _SPERRE:
        _MESSUNGEN.append(m)
    if dauer >= 0.5:
        _datei(m)


def _datei(m: Messung) -> None:
    try:
        from .netz_kern import lokal_ordner

        p = lokal_ordner() / "ladezeiten.log"
        p.parent.mkdir(parents=True, exist_ok=True)
        if p.exists() and p.stat().st_size > 400_000:            # klein halten
            p.replace(p.with_suffix(".alt.log"))
        with open(p, "a", encoding="utf-8") as f:
            f.write(f"{m.zeit}\t{m.dauer:.2f}\t{m.stufe}\t{m.seite}\n")
    except Exception:                                            # noqa: BLE001 – Messung darf nie stören
        pass


def messungen() -> list[Messung]:
    with _SPERRE:
        return list(_MESSUNGEN)


def seite_von(ansicht) -> str:
    s = getattr(ansicht, "seite", "") or ""
    try:
        a = ansicht.ansicht_von(s, "")
    except Exception:                                            # noqa: BLE001
        a = ""
    return f"{s}/{a}" if a else s


def bericht(ms: list[Messung] | None = None, n: int = 12) -> dict:
    """{"langsamste": [Messung…], "je_seite": [(Seite, Anzahl, Mittel, Max)…], "langsam": Anzahl ≥ LANGSAM}"""
    ms = messungen() if ms is None else ms
    je: dict[str, list[float]] = {}
    for m in ms:
        je.setdefault(m.seite, []).append(m.dauer)
    tab = sorted(((s, len(d), round(sum(d) / len(d), 2), max(d)) for s, d in je.items()), key=lambda x: -x[3])
    return {"langsamste": sorted(ms, key=lambda m: -m.dauer)[:n], "je_seite": tab,
            "langsam": sum(1 for m in ms if m.dauer >= LANGSAM)}


def text(ms: list[Messung] | None = None) -> str:
    """Zum Kopieren (z. B. für eine Rückmeldung) – nur Seiten und Sekunden."""
    from . import __version__

    b = bericht(ms, 20)
    zeilen = [f"INNternat {__version__} – Ladezeiten ({len(ms if ms is not None else messungen())} Messungen)", "",
              "Langsamste Schritte:"]
    zeilen += [f"  {m.dauer:6.2f} s  {m.stufe:<26} {m.seite}  ({m.zeit})" for m in b["langsamste"]]
    zeilen += ["", "Je Seite (Anzahl · Mittel · Max):"]
    zeilen += [f"  {s:<34} {n:3d} · {mi:5.2f} s · {mx:5.2f} s" for s, n, mi, mx in b["je_seite"][:25]]
    return "\n".join(zeilen)


def _huelle(f, stufe: str, seite_fn):
    @functools.wraps(f)
    def gemessen(*args, **kwargs):
        t = time.perf_counter()
        try:
            return f(*args, **kwargs)
        finally:
            try:
                merken(stufe, seite_fn(*args), time.perf_counter() - t)
            except Exception:                                    # noqa: BLE001
                pass
    gemessen._gemessen = True
    return gemessen


def installieren() -> None:
    if _AN["ok"]:
        return
    _AN["ok"] = True
    from . import auswertung_kern, oberflaeche

    for name in ("_voll_laden", "_seite_laden", "zeichnen"):
        f = getattr(oberflaeche.Ansicht, name)
        if not getattr(f, "_gemessen", False):
            setattr(oberflaeche.Ansicht, name, _huelle(f, name, lambda self, *_: seite_von(self)))
    if not getattr(auswertung_kern.datenstand, "_gemessen", False):
        auswertung_kern.datenstand = _huelle(auswertung_kern.datenstand, "datenstand", lambda *_: "auswertung")
