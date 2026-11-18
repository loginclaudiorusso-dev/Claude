"""1.26: Prognose am Monatsletzten richtig – zur Laufzeit, das Hauptprogramm bleibt unverändert.

Fehler im Hauptprogramm (``belegung/prognose.py``): Fällt der Stichtag auf einen Monatsletzten, ist dieser Monat schon
vollständig Ist – ``berechne`` nahm ihn trotzdem als ersten Prognosemonat. Folge: der Monat stand doppelt in der Liste
(Ist und Prognose) und alle Prognosewerte waren um zwei Monate verschoben (z. B. November mit dem Januarwert).
``_gesamt`` zählte den Abstand für das Band der Summe ebenfalls ab dem Stichtagsmonat.

Korrektur: Der erste Prognosemonat ist der Monat des Tages NACH dem Stichtag. Ersetzt wird genau diese eine Zeile je
Funktion (Quelltext des Hauptprogramms, Zeile getauscht, in dessen Namensraum neu übersetzt). Findet sich die Zeile
nicht (anderes Hauptprogramm), bleibt alles wie es war – mit Hinweis im Protokoll.
"""

from __future__ import annotations

import inspect
import logging
import textwrap

log = logging.getLogger(__name__)

ERSATZ = {
    "berechne": ('erster_prognosemonat = pd.Timestamp(stichtag).to_period("M").start_time',
                 'erster_prognosemonat = (pd.Timestamp(stichtag) + pd.Timedelta(days=1)).to_period("M").start_time'),
    "_gesamt": ("erster = date(stichtag.year, stichtag.month, 1)",
                "erster = (pd.Timestamp(stichtag) + pd.Timedelta(days=1)).to_period(\"M\").start_time.date()"),
}
_ORIG: dict = {}


def _neu(modul, name: str, alt: str, neu: str):
    f = getattr(modul, name)
    quelle = textwrap.dedent(inspect.getsource(f))
    if quelle.count(alt) != 1:
        return None
    ns: dict = {}
    exec(compile(quelle.replace(alt, neu), inspect.getsourcefile(f) or "<prognose>", "exec"), modul.__dict__, ns)
    g = ns[name]
    g.__doc__ = (f.__doc__ or "") + "\n\n(1.26: erster Prognosemonat = Monat nach dem Stichtag – modern_ui.prognose_fix_kern)"
    return g


def installieren() -> bool:
    """True, wenn beide Stellen ersetzt sind."""
    from belegung import prognose as P

    if _ORIG:
        return True
    neu = {}
    for name, (alt, ersatz) in ERSATZ.items():
        try:
            g = _neu(P, name, alt, ersatz)
        except Exception as exc:                          # noqa: BLE001
            log.warning("Prognose-Korrektur %s nicht möglich: %s", name, exc)
            g = None
        if g is None:
            log.warning("Prognose-Korrektur: Stelle in %s nicht gefunden – Hauptprogramm unverändert gelassen", name)
            return False
        neu[name] = g
    for name, g in neu.items():
        _ORIG[name] = getattr(P, name)
        setattr(P, name, g)
    return True


def entfernen() -> None:
    from belegung import prognose as P

    for name, f in _ORIG.items():
        setattr(P, name, f)
    _ORIG.clear()
