"""1.29: Lesezugriff auf Felder des Hauptprogramms, deren Bedeutung nicht im Namen steckt.

Das Hauptprogramm (``belegung/zimmerplan.py``, ``_als_belegung``) führt bei EIGENEN Planungen das Geschlecht im Feld
``Belegung.grund`` mit – sonst steht dort der Sperrgrund („Mieter“, „Renovierung“ …). Das Hauptprogramm darf nicht
geändert werden; deshalb liest die neue Oberfläche diese Doppelbelegung des Feldes NUR hier, an einer benannten
Stelle. Ändert das Hauptprogramm das später (eigenes Feld ``geschlecht``), wird es hier zuerst genommen.
"""

from __future__ import annotations

from belegung import zimmerplan as zp

GESCHLECHTER = ("m", "w")


def geschlecht(b) -> str:
    """Geschlecht einer Belegung: eigenes Feld (falls das Hauptprogramm es einmal hat), sonst bei eigener Planung
    (``person`` gesetzt) das Feld ``grund``, sonst aus dem Vornamen geraten. Nur „m“/„w“ oder „“."""
    eigen = getattr(b, "geschlecht", None)
    if eigen in GESCHLECHTER:
        return eigen
    if getattr(b, "person", "") and getattr(b, "grund", "") in GESCHLECHTER:
        return b.grund
    return zp.geschlecht_raten(getattr(b, "name", "") or "")
