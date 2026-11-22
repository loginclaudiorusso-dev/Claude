"""1.36: Schneller – zur Laufzeit, das Hauptprogramm bleibt unverändert.

Gemessen (Startseite): ~90 % der Rechenzeit stecken in ``eintragen.nach_planung`` („freie Zimmer nach Planung“). Es
teilt alle offenen Anreisen probeweise zu und wurde je Laden zweimal gerechnet (Aufgaben und Startseite). Darin
vergleicht ``zimmerplan.vorschlagen`` Zimmer millionenfach über das von ``@dataclass`` erzeugte ``__eq__`` – Feld für
Feld, obwohl sich zwei Zimmer fast immer schon in der Kennung unterscheiden.

* ``Zimmer.__eq__``: gleiches Objekt → gleich; verschiedene Kennung → ungleich; sonst wie bisher alle Felder. Das
  Ergebnis ist in jedem Fall dasselbe wie vorher (gleiche Zimmer haben dieselbe Kennung), nur schneller.
* ``vorschlagen``: „Ausnahmen“ (von Hand wählbare Zimmer) prüften je Zimmer ``z not in zt.alternativen`` – eine
  Liste, also Raum × Raum Vergleiche je Person. Jetzt einmal je Person eine Menge der Kennungen (gleiches Ergebnis:
  gleiche Zimmer haben dieselbe Kennung). Der Quelltext des Hauptprogramms wird dafür nur im Speicher geändert;
  findet sich die Stelle nicht (anderes Hauptprogramm), bleibt alles wie es war.
* ``nach_planung``: Ergebnis je Planstand, Tag und Wochenzahl merken – derselbe Stand wird nicht zweimal gerechnet.
  Jedes Laden erzeugt einen neuen Planstand, also nie ein veralteter Wert.
"""

from __future__ import annotations

import logging
import weakref

log = logging.getLogger(__name__)
_STAND: dict = {"ok": False}


def installieren() -> None:
    if _STAND["ok"]:
        return
    from belegung import eintragen
    from belegung import zimmerplan as zp

    alt_eq = zp.Zimmer.__eq__

    def _eq(self, other):
        if self is other:
            return True
        if other.__class__ is self.__class__ and self.id != other.id:
            return False
        return alt_eq(self, other)
    zp.Zimmer.__eq__ = _eq
    zp.Zimmer._eq_original = alt_eq

    _vorschlagen_schneller(zp)

    alt_np = eintragen.nach_planung
    merk: dict = {}

    def nach_planung(stand, heute=None, wochen: int = 12):
        schluessel = (heute, wochen)
        ref, wert = merk.get(schluessel, (None, None))
        if ref is not None and ref() is stand:
            return wert
        wert = alt_np(stand, heute, wochen)
        try:
            for k in [k for k, (r, _w) in merk.items() if r() is not stand]:
                del merk[k]                                # nur den jüngsten Stand behalten
            merk[schluessel] = (weakref.ref(stand), wert)
        except TypeError:                                  # Stand ohne weakref (Test-Attrappe): nicht merken
            pass
        return wert
    nach_planung.__wrapped__ = alt_np
    eintragen.nach_planung = nach_planung
    _STAND["ok"] = True
    log.debug("Leistung: Zimmer-Vergleich und nach_planung beschleunigt")


ALT_AUSNAHMEN = "zt.ausnahmen = sorted((z for z in zimmer_liste if z not in zt.alternativen and "
NEU_AUSNAHMEN = ("_alt_ids = {x.id for x in zt.alternativen}\n        "
                 "zt.ausnahmen = sorted((z for z in zimmer_liste if z.id not in _alt_ids and ")


def _vorschlagen_schneller(zp) -> bool:
    """Code-Objekt der Originalfunktion tauschen – so profitieren auch alle, die sie schon festhalten (z. B. die
    Mieter-Regel in ``regeln_kern``)."""
    import inspect
    import textwrap

    from . import regeln_kern

    f = regeln_kern._MIETER.get("vorschlagen") or zp.vorschlagen
    try:
        quelle = textwrap.dedent(inspect.getsource(f))
        if quelle.count(ALT_AUSNAHMEN) != 1 or f.__code__.co_freevars:
            log.info("Leistung: Stelle in vorschlagen nicht gefunden – unverändert")
            return False
        ns: dict = {}
        vorne = "\n" * (f.__code__.co_firstlineno - 1)       # Zeilennummern wie im Hauptprogramm (Fehlermeldungen)
        exec(compile(vorne + quelle.replace(ALT_AUSNAHMEN, NEU_AUSNAHMEN), inspect.getsourcefile(f) or "<vorschlagen>",
                     "exec"), f.__globals__, ns)
        f.__code__ = ns[f.__name__].__code__
        return True
    except Exception as exc:                               # noqa: BLE001 – im Zweifel das Original
        log.warning("Leistung: vorschlagen nicht beschleunigt: %s", exc)
        return False
