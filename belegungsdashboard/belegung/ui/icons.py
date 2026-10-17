"""Linien-Icons als SVG (24er Raster, 1,75 px Strich), zur Laufzeit eingefärbt.

Selbst gezeichnet statt Icon-Theme/Schrift: sieht auf jedem Windows-Rechner, jeder
DPI-Stufe und in jedem Farbmodus gleich aus.
"""

from __future__ import annotations

from functools import lru_cache

from PySide6.QtCore import QByteArray, QRectF, Qt
from PySide6.QtGui import QIcon, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer

_PFADE = {
    "mail": '<rect x="3" y="5" width="18" height="14" rx="2"/><path d="M3 7l9 6 9-6"/>',
    "start": '<path d="M12 3l2.6 5.6 6.1.7-4.5 4.2 1.2 6L12 16.6 6.6 19.5l1.2-6L3.3 9.3l6.1-.7z"/>',
    "uebersicht": '<rect x="3" y="3" width="7" height="9" rx="1.5"/><rect x="14" y="3" width="7" height="5" rx="1.5"/><rect x="14" y="12" width="7" height="9" rx="1.5"/><rect x="3" y="16" width="7" height="5" rx="1.5"/>',
    "belegung": '<path d="M3 3v18h18"/><path d="M7 15l4-4 3 3 5-6"/>',
    "prognose": '<path d="M3 17l6-6 4 4 8-8"/><path d="M14 7h7v7"/>',
    "daten": '<ellipse cx="12" cy="5" rx="8" ry="3"/><path d="M4 5v6c0 1.7 3.6 3 8 3s8-1.3 8-3V5"/><path d="M4 11v6c0 1.7 3.6 3 8 3s8-1.3 8-3v-6"/>',
    "assistent": '<path d="M21 12a8 8 0 0 1-11.6 7.1L4 20l1-4.6A8 8 0 1 1 21 12z"/><path d="M8.5 11h.01M12 11h.01M15.5 11h.01" stroke-width="2.4"/>',
    "einstellungen": '<circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.7 1.7 0 0 0 .3 1.8l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1.7 1.7 0 0 0-1.8-.3 1.7 1.7 0 0 0-1 1.5V21a2 2 0 1 1-4 0v-.1a1.7 1.7 0 0 0-1.1-1.5 1.7 1.7 0 0 0-1.8.3l-.1.1a2 2 0 1 1-2.8-2.8l.1-.1a1.7 1.7 0 0 0 .3-1.8 1.7 1.7 0 0 0-1.5-1H3a2 2 0 1 1 0-4h.1a1.7 1.7 0 0 0 1.5-1.1 1.7 1.7 0 0 0-.3-1.8l-.1-.1a2 2 0 1 1 2.8-2.8l.1.1a1.7 1.7 0 0 0 1.8.3H9a1.7 1.7 0 0 0 1-1.5V3a2 2 0 1 1 4 0v.1a1.7 1.7 0 0 0 1 1.5 1.7 1.7 0 0 0 1.8-.3l.1-.1a2 2 0 1 1 2.8 2.8l-.1.1a1.7 1.7 0 0 0-.3 1.8V9a1.7 1.7 0 0 0 1.5 1H21a2 2 0 1 1 0 4h-.1a1.7 1.7 0 0 0-1.5 1z"/>',
    "aktualisieren": '<path d="M21 12a9 9 0 0 1-15.5 6.2L3 16"/><path d="M3 12a9 9 0 0 1 15.5-6.2L21 8"/><path d="M21 3v5h-5"/><path d="M3 21v-5h5"/>',
    "server": '<rect x="3" y="4" width="18" height="7" rx="1.5"/><rect x="3" y="13" width="18" height="7" rx="1.5"/><path d="M7 7.5h.01M7 16.5h.01" stroke-width="2.4"/>',
    "hochladen": '<path d="M12 15V3"/><path d="M7 8l5-5 5 5"/><path d="M4 15v4a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-4"/>',
    "datei": '<path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z"/><path d="M14 3v5h5"/>',
    "kalender": '<rect x="3" y="5" width="18" height="16" rx="2"/><path d="M16 3v4M8 3v4M3 10h18"/>',
    "links": '<path d="M15 18l-6-6 6-6"/>',
    "rechts": '<path d="M9 18l6-6-6-6"/>',
    "runter": '<path d="M6 9l6 6 6-6"/>',
    "plus": '<path d="M12 5v14M5 12h14"/>',
    "loeschen": '<path d="M3 6h18"/><path d="M8 6V4h8v2"/><path d="M6 6l1 14a2 2 0 0 0 2 2h6a2 2 0 0 0 2-2l1-14"/>',
    "schliessen": '<path d="M18 6L6 18M6 6l12 12"/>',
    "senden": '<path d="M22 2L11 13"/><path d="M22 2l-7 20-4-9-9-4z"/>',
    "funke": '<path d="M12 3l1.8 5.2L19 10l-5.2 1.8L12 17l-1.8-5.2L5 10l5.2-1.8z"/><path d="M19 15l.8 2.2L22 18l-2.2.8L19 21l-.8-2.2L16 18l2.2-.8z"/>',
    "warnung": '<path d="M10.3 3.9L1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0z"/><path d="M12 9v4M12 17h.01"/>',
    "ausrufe": '<circle cx="12" cy="12" r="9.5"/><path d="M12 6.8v6.6" stroke-width="2.6"/><path d="M12 17.2h.01" stroke-width="3"/>',
    "info": '<circle cx="12" cy="12" r="9"/><path d="M12 16v-4M12 8h.01"/>',
    "haken": '<path d="M20 6L9 17l-5-5"/>',
    "kopieren": '<rect x="9" y="9" width="12" height="12" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/>',
    "neu": '<path d="M12 20h9"/><path d="M16.5 3.5a2.1 2.1 0 0 1 3 3L7 19l-4 1 1-4z"/>',
    "inventar": '<path d="M21 8l-9-5-9 5v8l9 5 9-5z"/><path d="M3 8l9 5 9-5M12 13v8"/>',
    "haus": '<path d="M3 10l9-7 9 7v10a1 1 0 0 1-1 1h-5v-6H9v6H4a1 1 0 0 1-1-1z"/>',
    "personen": '<path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.9M16 3.1a4 4 0 0 1 0 7.8"/>',
    "mond": '<path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z"/>',
    "sonne": '<circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/>',
    "tabelle": '<rect x="3" y="3" width="18" height="18" rx="2"/><path d="M3 9h18M3 15h18M9 3v18"/>',
    "glocke": '<path d="M18 8a6 6 0 0 0-12 0c0 7-3 9-3 9h18s-3-2-3-9"/><path d="M13.7 21a2 2 0 0 1-3.4 0"/>',
    "fenster": '<rect x="3" y="4" width="18" height="16" rx="2"/><path d="M3 9h18"/><path d="M7 6.5h.01"/>',
    "schloss": '<rect x="4" y="11" width="16" height="10" rx="2"/><path d="M8 11V7a4 4 0 0 1 8 0v4"/>',
    # 6.15 – Zimmer finden
    "suche": '<circle cx="11" cy="11" r="7"/><path d="M21 21l-4.6-4.6"/>',
    "boden": '<rect x="3" y="4" width="18" height="16" rx="1.5"/><path d="M3 9.3h18M3 14.6h18M10 4v5.3M15 9.3v5.3M8 14.6V20M17 14.6V20"/>',
    "teppich": '<rect x="4" y="3" width="16" height="18" rx="1.5"/><path d="M7 8c2-1.5 3 1.5 5 0s3 1.5 5 0M7 12c2-1.5 3 1.5 5 0s3 1.5 5 0M7 16c2-1.5 3 1.5 5 0s3 1.5 5 0"/>',
    "pfote": '<ellipse cx="12" cy="16" rx="4.2" ry="3.6"/><circle cx="6" cy="10.5" r="1.8"/><circle cx="9.5" cy="6.5" r="1.8"/><circle cx="14.5" cy="6.5" r="1.8"/><circle cx="18" cy="10.5" r="1.8"/>',
    "bett": '<path d="M3 19V6M3 15h18v4M21 15v-3a3 3 0 0 0-3-3h-7v6"/><circle cx="7" cy="11" r="2"/>',
    "dusche": '<path d="M5 21V6a3 3 0 0 1 6 0"/><path d="M8 9h7l-1.5 3h-4z"/><path d="M10 15v1M13 15v2M16 15v1M11.5 19v1M14.5 19v1"/>',
    "filter": '<path d="M3 5h18l-7 8.5V20l-4-2v-4.5z"/>',
    "raster": '<rect x="3" y="3" width="5" height="5" rx="1"/><rect x="10" y="3" width="5" height="5" rx="1"/><rect x="17" y="3" width="4" height="5" rx="1"/><rect x="3" y="10" width="5" height="5" rx="1"/><rect x="10" y="10" width="5" height="5" rx="1"/><rect x="17" y="10" width="4" height="5" rx="1"/><rect x="3" y="17" width="5" height="4" rx="1"/><rect x="10" y="17" width="5" height="4" rx="1"/>',
    "karten": '<rect x="3" y="3" width="8" height="18" rx="1.5"/><rect x="13" y="3" width="8" height="8" rx="1.5"/><rect x="13" y="13" width="8" height="8" rx="1.5"/>',
    "liste": '<path d="M9 6h12M9 12h12M9 18h12"/><path d="M4 6h.01M4 12h.01M4 18h.01" stroke-width="2.6"/>',
    "drucker": '<path d="M6 9V3h12v6"/><rect x="3" y="9" width="18" height="8" rx="2"/><rect x="7" y="14" width="10" height="7" rx="1"/>',
    "farbrolle": '<rect x="3" y="3" width="15" height="6" rx="1.5"/><path d="M18 6h2.5v5.5H11V15"/><rect x="9.5" y="15" width="3" height="6" rx="1"/>',
    "werkzeug": '<path d="M14.7 6.3a4 4 0 0 0 5 5L21 13l-2 2-1.3-1.3a4 4 0 0 0-5-5z" fill="none"/><path d="M13 8l-9.3 9.3a1.8 1.8 0 0 0 2.5 2.5L15.5 10.5"/><path d="M15 4a4.5 4.5 0 0 1 5 5l-3-1-1.5-1.5z"/>',
    "person": '<circle cx="12" cy="8" r="4"/><path d="M4 21v-1a6 6 0 0 1 6-6h4a6 6 0 0 1 6 6v1"/>',
}


@lru_cache(maxsize=512)
def pixmap(name: str, farbe: str, groesse: int = 18, dpr: float = 2.0) -> QPixmap:
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="{farbe}" '
           f'stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round">{_PFADE[name]}</svg>')
    renderer = QSvgRenderer(QByteArray(svg.encode()))
    px = QPixmap(int(groesse * dpr), int(groesse * dpr))
    px.fill(Qt.transparent)
    p = QPainter(px)
    p.setRenderHint(QPainter.Antialiasing)
    renderer.render(p, QRectF(0, 0, groesse * dpr, groesse * dpr))
    p.end()
    px.setDevicePixelRatio(dpr)
    return px


def icon(name: str, farbe: str, groesse: int = 18, farbe_aktiv: str | None = None) -> QIcon:
    ic = QIcon()
    ic.addPixmap(pixmap(name, farbe, groesse), QIcon.Normal, QIcon.Off)
    if farbe_aktiv:
        ic.addPixmap(pixmap(name, farbe_aktiv, groesse), QIcon.Normal, QIcon.On)
        ic.addPixmap(pixmap(name, farbe_aktiv, groesse), QIcon.Active, QIcon.Off)
    return ic
