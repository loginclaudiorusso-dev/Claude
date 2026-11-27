"""1.74: Zimmer während einer Unterbrechung gehalten (z. B. Praktikum) – nicht „frei“.

Wer ins Praktikum geht, ist nicht im Haus – das Zimmer bleibt aber seins (Sachen bleiben, er kommt zurück). In den
Daten stehen zwei Aufenthalte derselben Person im selben Zimmer mit einer Lücke; das Programm zeigte die Lücke als frei
und hätte das Zimmer neu vergeben.

Regel: Dieselbe Person (Schlüssel oder gleicher Name) hat im selben Zimmer zwei Aufenthalte, dazwischen 2 Tage bis
``max_tage`` (Einstellung ``zimmer_halten_monate``, Standard 9 Monate; 0 = aus) → für die Lücke wird ein Bett als
belegt eingetragen (Grund „gehalten …“). Im Doppelzimmer ist so nur ihr Bett belegt.
* Notfallliste/„Aktuell im Haus“: die Person steht als abwesend (nicht im Haus).
* Abreisen: das Ende der Lücke ist keine Abreise.
* Nur im Speicher (beim Laden) – Gebäudeplan und Planung bleiben unverändert.
Eingehängt in ``zimmerplan.lage_bauen`` (nur neue Oberfläche).
"""

from __future__ import annotations

import re
from dataclasses import replace
from datetime import date, timedelta

GRUND = "gehalten"
_ORIG: dict = {}


def _woerter(name: str) -> frozenset[str]:
    return frozenset(w for w in re.split(r"[^\wäöüß]+", (name or "").lower()) if len(w) > 1)


def _gleich(a, b) -> bool:
    if a.person and b.person and a.person == b.person:
        return True
    wa, wb = _woerter(a.name), _woerter(b.name)
    return bool(wa) and wa == wb


def max_tage() -> int:
    try:
        from belegung import speicher

        m = speicher.einstellungen().get("zimmer_halten_monate")
        return max(0, int(round(float(9 if m in (None, "") else m) * 30.5)))
    except Exception:                              # noqa: BLE001
        return 275


def luecken(belegungen: list, grenze: int) -> list:
    """Halte-Belegungen für ein Zimmer (Lücken zwischen zwei Aufenthalten derselben Person)."""
    if grenze <= 0:
        return []
    personen = [b for b in belegungen if b.art in ("belegt", "geplant") and b.name and (b.grund or "") != GRUND]
    personen.sort(key=lambda b: b.von)
    erg = []
    for i, a in enumerate(personen):
        naechste = next((b for b in personen[i + 1:] if _gleich(a, b) and b.von > a.bis), None)
        if naechste is None:
            continue
        luecke = (naechste.von - a.bis).days - 1
        if luecke < 2 or luecke > grenze:
            continue
        # dazwischen ein anderer Aufenthalt derselben Person in diesem Zimmer? Dann ist es keine Lücke
        if any(_gleich(a, x) and x is not a and x is not naechste and x.von <= naechste.von and x.bis >= a.bis
               for x in personen):
            continue
        erg.append(replace(a, von=a.bis + timedelta(days=1), bis=naechste.von - timedelta(days=1), art="belegt",
                           grund=f"{GRUND} (Unterbrechung, z. B. Praktikum, bis {naechste.von - timedelta(days=1):%d.%m.%Y})",
                           umzug=""))
    return erg


def anwenden(lage, grenze: int | None = None) -> int:
    grenze = max_tage() if grenze is None else grenze
    n = 0
    for zid, bs in list(lage.belegungen.items()):
        neu = luecken(bs, grenze)
        if neu:
            lage.belegungen[zid] = bs + neu
            n += len(neu)
    return n


def ist_gehalten(b) -> bool:
    return (getattr(b, "grund", "") or "").startswith(GRUND)


def _lage_bauen(*args, **kwargs):
    lage = _ORIG["lage_bauen"](*args, **kwargs)
    try:
        anwenden(lage)
    except Exception:                              # noqa: BLE001 – darf das Laden nie verhindern
        pass
    return lage


def installieren() -> None:
    from belegung import zimmerplan as zp

    if _ORIG:
        return
    _ORIG["lage_bauen"] = zp.lage_bauen
    zp.lage_bauen = _lage_bauen


def heute_gehalten(lage, zid: str, tag: date) -> list:
    return [b for b in lage.belegungen.get(zid, []) if ist_gehalten(b) and b.von <= tag <= b.bis]
