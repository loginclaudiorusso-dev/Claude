"""1.39: eigene Piktogramme von INNternat (Navigation 2.0) – Duotone auf einem 32er-Raster.

* Kontur 1,75 in Textfarbe (``.s``), ein Akzent (``.sa`` Linie, ``.fa`` Fläche), zarte Tönung (``.f``).
* Rot nur für Schäden und Engpässe (``.sw`` / ``.fw``). ``.k`` stanzt den Hintergrund für Zusatzzeichen frei.
* Rein: liefert SVG-Text; Farben kommen aus CSS-Variablen (``--pk-p``, ``--pk-a``, ``--pk-t``, ``--pk-k``), damit
  Normal, Hover, Aktiv und Dunkel ohne eigenes Symbolset funktionieren.
"""

from __future__ import annotations

SYMBOLE: dict[str, str] = {
    'uebersicht': '<rect class="f" x="4" y="5" width="14" height="12" rx="2.5"/><rect class="s" x="4" y="5" width="14" height="12" rx="2.5"/><path class="sa" d="M7.5 14a3.5 3.5 0 0 1 7 0"/><path class="s" d="M11 14l1.9-2.1"/><rect class="s" x="21" y="5" width="7" height="12" rx="2.5"/><path class="s" d="M23.5 9.5h2M23.5 12.5h2"/><rect class="s" x="4" y="20" width="9" height="7" rx="2.5"/><rect class="s" x="16" y="20" width="12" height="7" rx="2.5"/><path class="sa" d="M19.5 24.3v-1.2M22 24.3v-2.4M24.5 24.3v-.8"/>',
    'anreisen': '<path class="s" d="M3 27h26M18.5 27V5.5h9.5V27"/><path class="f" d="M28 5.5 24.6 7.4V27H28z"/><path class="s" d="M28 5.5 24.6 7.4V27"/><path class="sa w" d="M4 16.5h11.5M12 13l3.5 3.5-3.5 3.5"/>',
    'abreisen': '<path class="s" d="M3 27h26M18.5 27V5.5h9.5V27"/><path class="f" d="M28 5.5 24.6 7.4V27H28z"/><path class="s" d="M28 5.5 24.6 7.4V27"/><path class="sa w" d="M16 16.5H4.5M8 13l-3.5 3.5L8 20"/>',
    'zimmer': '<path class="f" d="M6.5 12.2V27h19V12.2L16 5.6z"/><path class="s" d="M3.5 14 16 4.6 28.5 14M6.5 12.2V27h19V12.2"/><path class="s" d="M9 18v7M9 22.5h8.5V25"/><rect class="s" x="10.3" y="19" width="3.6" height="2.3" rx="1"/><path class="s" d="M20 27v-8.5h3.5V27"/><rect class="fa" x="20" y="14.6" width="3.5" height="2.1" rx=".6"/>',
    'planung': '<path class="f" d="M15 5h11a2 2 0 0 1 2 2v11H15z"/><rect class="s" x="4" y="5" width="24" height="22" rx="2"/><path class="s" d="M4 16h7M15 5v7.5M15 16v11M15 18h5M24 18h4"/><circle class="sa" cx="21.5" cy="9.7" r="1.9"/><path class="sa" d="M18.4 15.4a3.1 3.1 0 0 1 6.2 0"/>',
    'auswertung': '<path class="f" d="M7 4.5h11.5L25 11v16.5H7z"/><path class="s" d="M7 4.5h11.5L25 11v16.5H7z"/><path class="s" d="M18.5 4.5V11H25"/><path class="s" d="M10.5 9h4.5M10.5 12.5h6.5M10.3 24h11.4"/><path class="sa w" d="M12.5 24v-3.6M16 24v-6.6M19.5 24v-4.6"/>',
    'ki': '<path class="f" d="M5 8.5A3.5 3.5 0 0 1 8.5 5h15A3.5 3.5 0 0 1 27 8.5v10a3.5 3.5 0 0 1-3.5 3.5H15l-5.5 4.5V22h-1A3.5 3.5 0 0 1 5 18.5z"/><path class="s" d="M5 8.5A3.5 3.5 0 0 1 8.5 5h15A3.5 3.5 0 0 1 27 8.5v10a3.5 3.5 0 0 1-3.5 3.5H15l-5.5 4.5V22h-1A3.5 3.5 0 0 1 5 18.5z"/><path class="fa" d="M16 7.3Q16.8 12.7 22.2 13.5Q16.8 14.3 16 19.7Q15.2 14.3 9.8 13.5Q15.2 12.7 16 7.3Z"/>',
    'verwaltung': '<rect class="f" x="3.5" y="5" width="15" height="22" rx="2.5"/><rect class="s" x="3.5" y="5" width="15" height="22" rx="2.5"/><path class="s" d="M8 9v14M14 9v14"/><circle class="fa" cx="8" cy="18" r="2.2"/><circle class="fa" cx="14" cy="12" r="2.2"/><path class="f" d="M25 12.5l4.5 1.8v4.5c0 3.3-2 5.7-4.5 6.9-2.5-1.2-4.5-3.6-4.5-6.9v-4.5z"/><path class="s" d="M25 12.5l4.5 1.8v4.5c0 3.3-2 5.7-4.5 6.9-2.5-1.2-4.5-3.6-4.5-6.9v-4.5z"/><path class="sa" d="M23.1 19.2l1.4 1.4 2.5-2.7"/>',
    'datei': '<path class="f" d="M18 4.5v6h6z"/><path class="s" d="M8 4.5h10l6 6v17H8z"/><path class="s" d="M18 4.5v6h6"/><path class="sa" d="M11.5 16h9M11.5 20h9M11.5 24h5"/>',
    'nachrichten': '<path class="f" d="M4.5 5.5h18v13l-5 5h-13z"/><path class="s" d="M4.5 5.5h18v13l-5 5h-13z"/><path class="s" d="M17.5 23.5v-5h5M8.5 10.5h10M8.5 14.5h6"/><circle class="k" cx="25" cy="7.5" r="4.6"/><circle class="fa" cx="25" cy="7.5" r="3"/>',
    'nachricht_neu': '<path class="f" d="M4.5 5.5h18v13l-5 5h-13z"/><path class="s" d="M4.5 5.5h18v13l-5 5h-13z"/><path class="s" d="M17.5 23.5v-5h5M8.5 10.5h10M8.5 14.5h6"/><path class="k" d="M19.6 29.2l1-4.4 7-7 3.4 3.4-7 7z"/><path class="sa" d="M21 28l.8-3.3 6-6 2.5 2.5-6 6z"/>',
    'fm_mail': '<rect class="f" x="3.5" y="7.5" width="21" height="15.5" rx="2.2"/><rect class="s" x="3.5" y="7.5" width="21" height="15.5" rx="2.2"/><path class="s" d="M4.3 8.8 14 16l9.7-7.2"/><circle class="k" cx="25" cy="24" r="6.4"/><path class="sa" d="M28.6 20.6a3 3 0 0 0-4.1 3.8l-3.4 3.4 1.2 1.2 3.4-3.4a3 3 0 0 0 3.8-4.1l-1.7 1.7-1.6-.4-.4-1.6z"/>',
    'aufgaben': '<rect class="f" x="5" y="4.5" width="20" height="23" rx="2.5"/><rect class="s" x="5" y="4.5" width="20" height="23" rx="2.5"/><path class="sa" d="M9 11l1.5 1.5L13 10M9 18l1.5 1.5L13 17"/><path class="s" d="M16 11.5h5M16 18.5h5M9.5 24h11"/>',
    'zuteilen': '<circle class="s" cx="8.5" cy="8.5" r="3.2"/><path class="s" d="M3.5 18.5a5 5 0 0 1 10 0"/><path class="sa" d="M14.5 9h4.3a2.5 2.5 0 0 1 2.5 2.5v4M19.1 13.5l2.2 2.2 2.2-2.2"/><path class="f" d="M13.5 24.5v-4.3h12.3a2 2 0 0 1 2 2v2.3z"/><path class="s" d="M13.5 27v-8M13.5 24.5h14.3V27M27.8 24.5v-2.3a2 2 0 0 0-2-2H13.5"/>',
    'teilnehmer': '<circle class="sa" cx="7.5" cy="8" r="2.4"/><circle class="sa" cx="7.5" cy="16" r="2.4"/><circle class="sa" cx="7.5" cy="24" r="2.4"/><path class="s" d="M12.5 8h15M12.5 16h15M12.5 24h10"/>',
    'datenabgleich': '<rect class="s" x="3.5" y="4.5" width="11" height="14" rx="2"/><path class="s" d="M6.5 9h5M6.5 12.5h5"/><rect class="f" x="17.5" y="13.5" width="11" height="14" rx="2"/><rect class="s" x="17.5" y="13.5" width="11" height="14" rx="2"/><path class="s" d="M20.5 18h5M20.5 21.5h5"/><path class="sa" d="M17.5 7.5h3a3 3 0 0 1 3 3v.6M21.5 9.6l2 2 2-2M14.5 24.5h-3a3 3 0 0 1-3-3v-.6M10.5 22.4l-2-2-2 2"/>',
    'mieter': '<path class="f" d="M5.5 4.5h11l5.5 5.5v17.5H5.5z"/><path class="s" d="M5.5 4.5h11l5.5 5.5v17.5H5.5z"/><path class="s" d="M16.5 4.5V10H22"/><path class="sa" d="M9 17.5l3.5-3 3.5 3V22H9z"/><path class="s" d="M9 10.5h4.5"/><circle class="k" cx="24.5" cy="24" r="7"/><circle class="sa" cx="22.4" cy="21.9" r="2.4"/><path class="sa" d="M24.1 23.6l4.3 4.3M26.8 26.3l1.4-1.4"/>',
    'zimmeruebersicht': '<rect class="s" x="3.5" y="6" width="7.3" height="9" rx="1.5"/><rect class="f" x="12.4" y="6" width="7.3" height="9" rx="1.5"/><rect class="s" x="12.4" y="6" width="7.3" height="9" rx="1.5"/><rect class="s" x="21.3" y="6" width="7.3" height="9" rx="1.5"/><rect class="s" x="3.5" y="17.5" width="7.3" height="9" rx="1.5"/><rect class="s" x="12.4" y="17.5" width="7.3" height="9" rx="1.5"/><rect class="s" x="21.3" y="17.5" width="7.3" height="9" rx="1.5"/><path class="sa" d="M14.6 15v-3.6h2.9V15"/>',
    'zimmerliste': '<rect class="fa" x="4" y="5.5" width="4" height="5.5" rx=".8"/><rect class="s" x="4" y="13.3" width="4" height="5.5" rx=".8"/><rect class="s" x="4" y="21" width="4" height="5.5" rx=".8"/><path class="s" d="M12 8.3h16M12 16h16M12 23.8h11"/>',
    'reinigung': '<path class="s" d="M24 4.5 16.4 14.6"/><path class="f" d="M12.3 13.3l6.4 4.4-3.2 8.8H5z"/><path class="s" d="M12.3 13.3l6.4 4.4-3.2 8.8H5zM9.2 26.5l3.2-6.4M12.6 26.5l2.8-5.2"/><path class="sa" d="M7 4.5v4.6M4.7 6.8h4.6M26.5 13.5v3M25 15h3"/>',
    'defekt': '<path class="f" d="M6 27V5.5h13V27z"/><path class="s" d="M6 27V5.5h13V27M3.5 27h18"/><path class="dot" d="M16 17h.01"/><path class="k" d="M24.5 13.4 32.6 28.6H16.4z"/><path class="fw" d="M24.5 16.6 30 26.8H19z"/><path class="sw" d="M24.5 16.6 30 26.8H19zM24.5 20.6v2.6M24.5 25v.1"/>',
    'qr': '<rect class="s" x="3.5" y="3.5" width="9" height="9" rx="1.6"/><rect class="s" x="3.5" y="16.5" width="9" height="9" rx="1.6"/><rect class="s" x="16.5" y="3.5" width="9" height="9" rx="1.6"/><rect class="fa" x="6.5" y="6.5" width="3" height="3" rx=".5"/><rect class="fa" x="6.5" y="19.5" width="3" height="3" rx=".5"/><rect class="fa" x="19.5" y="6.5" width="3" height="3" rx=".5"/><path class="dot" d="M16.8 16.8h.01M20.3 16.8h.01M16.8 20.3h.01"/><path class="sa" d="M29 19l-7.6 7.6M21.2 21.6v5.2h5.2"/>',
    'facility': '<rect class="f" x="6" y="5.5" width="20" height="22.5" rx="2.5"/><rect class="s" x="6" y="5.5" width="20" height="22.5" rx="2.5"/><rect class="k" x="11" y="3.2" width="10" height="4.6" rx="1.4"/><rect class="s" x="11.8" y="3.6" width="8.4" height="3.9" rx="1.2"/><path class="s" d="M10.5 17.5 16 13l5.5 4.5V24h-11z"/><path class="sa" d="M13.3 19.6l1.8 1.8 3.5-3.6"/>',
    'inventar': '<path class="f" d="M4.5 10 16 5l11.5 5L16 15z"/><path class="s" d="M4.5 10 16 5l11.5 5v13L16 28 4.5 23zM4.5 10 16 15l11.5-5M16 15v13"/><path class="fa" d="M7.5 16.4l4.6 2v3.2l-4.6-2z"/>',
    'belegungsplan': '<path class="s" d="M4 5v22h24"/><rect class="fa" x="7" y="7.5" width="11" height="3.8" rx="1.6"/><rect class="f" x="11.5" y="13.8" width="13" height="3.8" rx="1.6"/><rect class="s" x="11.5" y="13.8" width="13" height="3.8" rx="1.6"/><rect class="fa" x="8.5" y="20.1" width="9" height="3.8" rx="1.6"/><path class="s dash" d="M21 5v19"/>',
    'kalender': '<path class="f" d="M4 9a2.5 2.5 0 0 1 2.5-2.5h19A2.5 2.5 0 0 1 28 9v3.5H4z"/><rect class="s" x="4" y="6.5" width="24" height="21" rx="2.5"/><path class="s" d="M4 12.5h24M10 4.5v4M22 4.5v4"/><path class="dot" d="M9.5 17.5h.01M13.5 17.5h.01M9.5 22.3h.01M13.5 22.3h.01M22.5 17.5h.01"/><rect class="fa" x="17.3" y="19.8" width="5.4" height="4.6" rx="1"/>',
    'reinigungsvorschau': '<path class="f" d="M3.5 9a2.5 2.5 0 0 1 2.5-2.5h15A2.5 2.5 0 0 1 23.5 9v3H3.5z"/><rect class="s" x="3.5" y="6.5" width="20" height="19" rx="2.5"/><path class="s" d="M3.5 12h20M8.5 4.5v4M18.5 4.5v4"/><path class="dot" d="M8 16.5h.01M12 16.5h.01M8 20.8h.01"/><circle class="k" cx="23.5" cy="22" r="8"/><path class="sa" d="M29 14.8l-4.5 5.6"/><path class="f" d="M22.2 19.3l3.8 2.6-1.9 5.4h-5.5z"/><path class="s" d="M22.2 19.3l3.8 2.6-1.9 5.4h-5.5zM20.6 27.3l1.8-3.4M22.8 27.3l1.6-3"/>',
    'renovierung': '<rect class="f" x="4" y="5" width="17" height="6.5" rx="2"/><rect class="s" x="4" y="5" width="17" height="6.5" rx="2"/><path class="s" d="M21 8.2h3v6.3H12.5v3.4"/><rect class="s" x="10.5" y="18" width="4" height="9" rx="1.6"/><circle class="k" cx="24" cy="23.5" r="6.2"/><circle class="sa" cx="24" cy="23.5" r="4.3"/><path class="sa" d="M24 21.2v4.6"/>',
    'kennzahlen': '<rect class="f" x="4" y="6" width="24" height="20" rx="2.5"/><rect class="s" x="4" y="6" width="24" height="20" rx="2.5"/><path class="s" d="M8 11h5M8 21.5h8"/><path class="sa w" d="M8 16.5h9.5"/><path class="sa" d="M19.5 15l2.6-2.8 2 2 1.9-2M23.6 11.7h2.4v2.4"/>',
    'belegung': '<path class="s" d="M7 27V7.5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2V27M4 27h24"/><rect class="s" x="10" y="9" width="3" height="3" rx=".6"/><rect class="s" x="14.5" y="9" width="3" height="3" rx=".6"/><rect class="s" x="19" y="9" width="3" height="3" rx=".6"/><rect class="fa" x="10" y="14" width="3" height="3" rx=".6"/><rect class="fa" x="14.5" y="14" width="3" height="3" rx=".6"/><rect class="s" x="19" y="14" width="3" height="3" rx=".6"/><rect class="fa" x="10" y="19" width="3" height="3" rx=".6"/><rect class="fa" x="14.5" y="19" width="3" height="3" rx=".6"/><rect class="fa" x="19" y="19" width="3" height="3" rx=".6"/>',
    'prognose': '<path class="f" d="M19.5 15 27.5 6v9z"/><path class="s" d="M4 5v22h24M6.5 21.5l4.5-4 4.2 2.5 4.3-5"/><path class="sa dash" d="M19.5 15l8-7.2"/><circle class="fa" cx="19.5" cy="15" r="1.9"/>',
    'massnahmen': '<path class="f" d="M3.5 12 16 6.5 28.5 12 16 17.5z"/><path class="s" d="M3.5 12 16 6.5 28.5 12 16 17.5z"/><path class="s" d="M9 14.8V21c0 1.8 3.1 3.5 7 3.5s7-1.7 7-3.5v-6.2"/><path class="sa" d="M26 13v6.4"/><circle class="fa" cx="26" cy="20.6" r="1.5"/>',
    'engpaesse': '<rect class="fw" x="6" y="6" width="20" height="5" rx="2.5"/><rect class="sw" x="6" y="6" width="20" height="5" rx="2.5"/><path class="sw" d="M26 4v9"/><path class="f" d="M5.5 23.5V19.5h4.5v4z"/><path class="s" d="M4 27v-9.5M4 23.5h24V27M28 23.5v-2.8a2 2 0 0 0-2-2H12v4.8M5.5 22.3v-2.8h4.5"/>',
    'auftraege': '<rect class="f" x="4.5" y="5.5" width="19" height="22.5" rx="2.5"/><rect class="s" x="4.5" y="5.5" width="19" height="22.5" rx="2.5"/><rect class="k" x="9" y="3.2" width="10" height="4.6" rx="1.4"/><rect class="s" x="9.8" y="3.6" width="8.4" height="3.9" rx="1.2"/><path class="s" d="M8.5 13h11M8.5 17h7"/><circle class="k" cx="24.5" cy="23.5" r="7"/><path class="fa" d="M24.5 17.3Q25.2 22.8 30.7 23.5Q25.2 24.2 24.5 29.7Q23.8 24.2 18.3 23.5Q23.8 22.8 24.5 17.3Z"/>',
    'schnellauskunft': '<path class="f" d="M4.5 8A3 3 0 0 1 7.5 5h17a3 3 0 0 1 3 3v9.5a3 3 0 0 1-3 3H13L7.5 25v-4.5A3 3 0 0 1 4.5 17.5z"/><path class="s" d="M4.5 8A3 3 0 0 1 7.5 5h17a3 3 0 0 1 3 3v9.5a3 3 0 0 1-3 3H13L7.5 25v-4.5A3 3 0 0 1 4.5 17.5z"/><path class="sa" d="M13.2 10.4a2.9 2.9 0 1 1 3.9 2.7c-.7.3-1.1.9-1.1 1.6v.5"/><path class="dot a" d="M16 18h.01"/><path class="sa" d="M24.5 23.5v4M22.5 25.5h4"/>',
    'mails_ki': '<rect class="f" x="3.5" y="7.5" width="21" height="15.5" rx="2.2"/><rect class="s" x="3.5" y="7.5" width="21" height="15.5" rx="2.2"/><path class="s" d="M4.3 8.8 14 16l9.7-7.2"/><circle class="k" cx="24.5" cy="23.5" r="7"/><path class="fa" d="M24.5 17.3Q25.2 22.8 30.7 23.5Q25.2 24.2 24.5 29.7Q23.8 24.2 18.3 23.5Q23.8 22.8 24.5 17.3Z"/>',
    'daten_einlesen': '<path class="f" d="M4 19h6.5l1.5 3h8l1.5-3H28v6a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2z"/><path class="s" d="M4 19v6a2 2 0 0 0 2 2h20a2 2 0 0 0 2-2v-6M4 19h6.5l1.5 3h8l1.5-3H28M7 15V7.5a2 2 0 0 1 2-2h3M25 15V7.5a2 2 0 0 0-2-2h-3"/><path class="sa" d="M16 4.5v12M11.6 12.6 16 17l4.4-4.4"/>',
    'stammdaten': '<rect class="f" x="3.5" y="6.5" width="22" height="17" rx="2.5"/><rect class="s" x="3.5" y="6.5" width="22" height="17" rx="2.5"/><path class="sa" d="M7 15.5l3.5-3 3.5 3V20H7z"/><path class="s" d="M16.5 12.5h5.5M16.5 16h5.5M16.5 19.5h3"/><path class="k" d="M19.6 29.2l1-4.4 7-7 3.4 3.4-7 7z"/><path class="sa" d="M21 28l.8-3.3 6-6 2.5 2.5-6 6z"/>',
    'benutzer': '<circle class="f" cx="12" cy="10" r="4.6"/><circle class="s" cx="12" cy="10" r="4.6"/><path class="s" d="M3.5 26.5a8.5 8.5 0 0 1 13.4-6.9"/><path class="k2" d="M24.5 16l5 2v4.6c0 3.4-2.2 5.8-5 7.1-2.8-1.3-5-3.7-5-7.1V18z"/><path class="f" d="M24.5 16l5 2v4.6c0 3.4-2.2 5.8-5 7.1-2.8-1.3-5-3.7-5-7.1V18z"/><path class="s" d="M24.5 16l5 2v4.6c0 3.4-2.2 5.8-5 7.1-2.8-1.3-5-3.7-5-7.1V18z"/><path class="sa" d="M22.4 22.6l1.5 1.5 2.9-3.1"/>',
    'einstellungen': '<path class="f" d="M24.03 13.54 L27.06 14.25 L27.06 17.75 L24.03 18.46 L23.42 19.94 L25.06 22.58 L22.58 25.06 L19.94 23.42 L18.46 24.03 L17.75 27.06 L14.25 27.06 L13.54 24.03 L12.06 23.42 L9.42 25.06 L6.94 22.58 L8.58 19.94 L7.97 18.46 L4.94 17.75 L4.94 14.25 L7.97 13.54 L8.58 12.06 L6.94 9.42 L9.42 6.94 L12.06 8.58 L13.54 7.97 L14.25 4.94 L17.75 4.94 L18.46 7.97 L19.94 8.58 L22.58 6.94 L25.06 9.42 L23.42 12.06Z"/><path class="s" d="M24.03 13.54 L27.06 14.25 L27.06 17.75 L24.03 18.46 L23.42 19.94 L25.06 22.58 L22.58 25.06 L19.94 23.42 L18.46 24.03 L17.75 27.06 L14.25 27.06 L13.54 24.03 L12.06 23.42 L9.42 25.06 L6.94 22.58 L8.58 19.94 L7.97 18.46 L4.94 17.75 L4.94 14.25 L7.97 13.54 L8.58 12.06 L6.94 9.42 L9.42 6.94 L12.06 8.58 L13.54 7.97 L14.25 4.94 L17.75 4.94 L18.46 7.97 L19.94 8.58 L22.58 6.94 L25.06 9.42 L23.42 12.06Z"/><circle class="k" cx="16" cy="16" r="4"/><circle class="sa" cx="16" cy="16" r="3.6"/>',
    'verlauf': '<circle class="f" cx="16" cy="16" r="10.5"/><path class="s" d="M5.5 16A10.5 10.5 0 1 0 8.6 8.6L5.5 11.7"/><path class="s" d="M5.5 6.5v5.2h5.2"/><path class="sa" d="M16 10.5V16l3.8 2.5"/>',
    'automatisierung': '<rect class="s" x="3.5" y="3.5" width="8" height="8" rx="1.5"/><rect class="s" x="3.5" y="16" width="8" height="8" rx="1.5"/><rect class="s" x="16" y="3.5" width="8" height="8" rx="1.5"/><rect class="fa" x="6" y="6" width="3" height="3" rx=".5"/><rect class="fa" x="6" y="18.5" width="3" height="3" rx=".5"/><rect class="fa" x="18.5" y="6" width="3" height="3" rx=".5"/><path class="dot" d="M15.8 15.8h.01M19.2 15.8h.01M15.8 19.2h.01"/><circle class="k" cx="24" cy="24" r="7.6"/><circle class="f" cx="24" cy="24" r="3.9"/><circle class="s" cx="24" cy="24" r="3.9"/><circle class="fa" cx="24" cy="24" r="1.5"/><path class="sa" d="M24 17.8v2M24 28.2v2M17.8 24h2M28.2 24h2M19.6 19.6l1.4 1.4M27 27l1.4 1.4M19.6 28.4l1.4-1.4M27 21l1.4-1.4"/>',
    'drucken': '<path class="s" d="M9 11V4.5h14V11"/><rect class="f" x="4" y="11" width="24" height="11" rx="2.5"/><rect class="s" x="4" y="11" width="24" height="11" rx="2.5"/><rect class="k" x="8.2" y="17.6" width="15.6" height="10.6"/><path class="s" d="M9 18.5h14v9H9z"/><path class="dot a" d="M23.5 14.6h.01"/>',
    'exportieren': '<path class="f" d="M5 4.5h10.5l5 5v18H5z"/><path class="s" d="M20.5 15V9.5l-5-5H5v23h15.5V24M15.5 4.5v5h5"/><path class="sa" d="M13 19.5h15M24 15.5l4 4-4 4"/>',
    'info': '<circle class="f" cx="16" cy="16" r="11.5"/><circle class="s" cx="16" cy="16" r="11.5"/><path class="sa" d="M16 14.6v7"/><path class="dot a" d="M16 10.3h.01"/>',
    'konto': '<circle class="s" cx="16" cy="16" r="11.5"/><circle class="f" cx="16" cy="13" r="4"/><circle class="sa" cx="16" cy="13" r="4"/><path class="sa" d="M8.6 24.4a8.5 8.5 0 0 1 14.8 0"/>',
    'suche': '<circle class="f" cx="14" cy="14" r="8.5"/><circle class="s" cx="14" cy="14" r="8.5"/><path class="sa w" d="M20.3 20.3 27 27"/>',
    'glocke': '<path class="f" d="M9 21v-7a7 7 0 0 1 14 0v7l2 2.5H7z"/><path class="s" d="M9 21v-7a7 7 0 0 1 14 0v7l2 2.5H7zM13.5 26.3a2.5 2.5 0 0 0 5 0"/><circle class="k" cx="23.5" cy="7.5" r="4.4"/><circle class="fa" cx="23.5" cy="7.5" r="2.8"/>',
    'hilfe': '<circle class="f" cx="16" cy="16" r="11.5"/><circle class="s" cx="16" cy="16" r="11.5"/><path class="sa w" d="M12.4 12.6a3.6 3.6 0 1 1 5 3.3c-.9.4-1.4 1.1-1.4 2v.9"/><path class="dot a" d="M16 22.4h.01"/>',
    'standort': '<path class="f" d="M16 28s8.5-8 8.5-14.5a8.5 8.5 0 0 0-17 0C7.5 20 16 28 16 28z"/><path class="s" d="M16 28s8.5-8 8.5-14.5a8.5 8.5 0 0 0-17 0C7.5 20 16 28 16 28z"/><circle class="sa" cx="16" cy="13.5" r="3.2"/>',
    # ---- 1.40: Aktionen und Zustände der Kontext- und Werkzeug-Registerkarten ----
    'a_heute': '<rect class="s" x="4.5" y="6.5" width="23" height="21" rx="2.5"/><path class="s" d="M4.5 11.5h23M10 4.5v4M22 4.5v4"/><rect class="fa" x="12.5" y="15" width="7" height="7" rx="1.4"/>',
    'a_tag': '<rect class="s" x="4.5" y="6.5" width="23" height="21" rx="2.5"/><path class="s" d="M4.5 11.5h23M10 4.5v4M22 4.5v4"/><path class="sa w" d="M14 17.2l2.4-1.7v8"/>',
    'a_woche': '<rect class="s" x="4.5" y="6.5" width="23" height="21" rx="2.5"/><path class="s" d="M4.5 11.5h23M10 4.5v4M22 4.5v4"/><rect class="fa" x="7.5" y="16.5" width="17" height="4" rx="1.2"/><path class="dot" d="M9.5 24h.01M16 24h.01M22.5 24h.01"/>',
    'a_monat': '<rect class="s" x="4.5" y="6.5" width="23" height="21" rx="2.5"/><path class="s" d="M4.5 11.5h23M10 4.5v4M22 4.5v4"/><circle class="fa" cx="9.5" cy="16" r="1.25"/><circle class="fa" cx="14" cy="16" r="1.25"/><circle class="fa" cx="18.5" cy="16" r="1.25"/><circle class="fa" cx="23" cy="16" r="1.25"/><circle class="fa" cx="9.5" cy="20" r="1.25"/><circle class="fa" cx="14" cy="20" r="1.25"/><circle class="fa" cx="18.5" cy="20" r="1.25"/><circle class="fa" cx="23" cy="20" r="1.25"/><circle class="fa" cx="9.5" cy="24" r="1.25"/><circle class="fa" cx="14" cy="24" r="1.25"/><circle class="fa" cx="18.5" cy="24" r="1.25"/><circle class="fa" cx="23" cy="24" r="1.25"/>',
    'a_zeitraum': '<rect class="s" x="4.5" y="6.5" width="23" height="21" rx="2.5"/><path class="s" d="M4.5 11.5h23M10 4.5v4M22 4.5v4"/><path class="sa" d="M8.5 19.5h15M8.5 17v5M23.5 17v5"/>',
    'a_geplant': '<rect class="s" x="3.5" y="5.5" width="20" height="18" rx="2.3"/><path class="s" d="M3.5 10h20M8.5 3.5v3.6M18.5 3.5v3.6"/><circle class="k" cx="24.5" cy="24" r="6.4"/><circle class="sa" cx="24.5" cy="24" r="4.6"/><path class="sa" d="M24.5 21.5V24l1.8 1.2"/>',
    'a_naechste': '<rect class="s" x="3.5" y="5.5" width="20" height="18" rx="2.3"/><path class="s" d="M3.5 10h20M8.5 3.5v3.6M18.5 3.5v3.6"/><circle class="k" cx="24.5" cy="24" r="6.4"/><path class="sa" d="M20.5 24h7.5M25 21l3 3-3 3"/>',
    'a_letzte': '<rect class="s" x="3.5" y="5.5" width="20" height="18" rx="2.3"/><path class="s" d="M3.5 10h20M8.5 3.5v3.6M18.5 3.5v3.6"/><circle class="k" cx="24.5" cy="24" r="6.4"/><path class="sa" d="M28.5 24h-7.5M24 21l-3 3 3 3"/>',
    'a_person': '<circle class="f" cx="16" cy="10.5" r="5"/><circle class="s" cx="16" cy="10.5" r="5"/><path class="s" d="M6.5 27.5a9.5 9.5 0 0 1 19 0"/>',
    'a_personen': '<circle class="s" cx="11" cy="10.5" r="4"/><path class="s" d="M3.5 26a7.5 7.5 0 0 1 15 0"/><circle class="f" cx="21.5" cy="12" r="3.5"/><circle class="s" cx="21.5" cy="12" r="3.5"/><path class="s" d="M19.5 18.6a6.5 6.5 0 0 1 9 6"/>',
    'a_personenliste': '<circle class="sa" cx="9" cy="9.5" r="3.4"/><path class="s" d="M3 22a6 6 0 0 1 12 0"/><path class="s" d="M18.5 9h9.5M18.5 15h9.5M18.5 21h6M3 27h25"/>',
    'a_team': '<circle class="s" cx="8" cy="12" r="3"/><circle class="s" cx="24" cy="12" r="3"/><circle class="f" cx="16" cy="9.5" r="3.6"/><circle class="s" cx="16" cy="9.5" r="3.6"/><path class="s" d="M2.5 24a5.5 5.5 0 0 1 9-4.2M29.5 24a5.5 5.5 0 0 0-9-4.2M9.5 27a6.5 6.5 0 0 1 13 0"/>',
    'a_person_neu': '<circle class="f" cx="13" cy="10" r="4.6"/><circle class="s" cx="13" cy="10" r="4.6"/><path class="s" d="M4 26.5a9 9 0 0 1 15.6-6.1"/><circle class="k" cx="24.5" cy="24" r="6.4"/><path class="sa w" d="M24.5 20.5v7M21 24h7"/>',
    'a_notfall': '<circle class="f" cx="13" cy="10" r="4.6"/><circle class="s" cx="13" cy="10" r="4.6"/><path class="s" d="M4 26.5a9 9 0 0 1 15.6-6.1"/><path class="k" d="M24.5 15.6 32.4 30H16.6z"/><path class="fw" d="M24.5 18.5 30 28H19z"/><path class="sw" d="M24.5 18.5 30 28H19zM24.5 22v2.5M24.5 26.1v.1"/>',
    'a_person_weiter': '<circle class="f" cx="13" cy="10" r="4.6"/><circle class="s" cx="13" cy="10" r="4.6"/><path class="s" d="M4 26.5a9 9 0 0 1 15.6-6.1"/><circle class="k" cx="24.5" cy="24" r="6.4"/><path class="sa" d="M20.5 24h8M25.5 21l3 3-3 3"/>',
    'a_person_frage': '<circle class="f" cx="13" cy="10" r="4.6"/><circle class="s" cx="13" cy="10" r="4.6"/><path class="s" d="M4 26.5a9 9 0 0 1 15.6-6.1"/><circle class="k" cx="24.5" cy="24" r="6.4"/><path class="sa" d="M22.4 21.8a2.2 2.2 0 1 1 3 2c-.6.3-.9.7-.9 1.3v.3"/><path class="dot a" d="M24.5 28h.01"/>',
    'a_haus_ok': '<path class="f" d="M6 14v13h20V14L16 6z"/><path class="s" d="M3.5 15.5 16 5.5l12.5 10M6 13.5V27h20V13.5"/><path class="sa w" d="M11.5 19l3 3 6-6"/>',
    'a_schluessel': '<circle class="f" cx="10" cy="12" r="5.5"/><circle class="s" cx="10" cy="12" r="5.5"/><circle class="fa" cx="10" cy="12" r="1.6"/><path class="s" d="M14.2 15.6 27 28.4M21.5 23l2.8-2.8M24.6 26.1l2.8-2.8"/>',
    'a_sitzplatz': '<path class="f" d="M9 15h14v4H9z"/><path class="s" d="M10 5.5h12a1.5 1.5 0 0 1 1.5 1.5v8H8.5V7A1.5 1.5 0 0 1 10 5.5zM7 15h18v4H7zM9 19v8.5M23 19v8.5"/>',
    'a_frei': '<circle class="f" cx="16" cy="16" r="11.5"/><circle class="s" cx="16" cy="16" r="11.5"/><path class="sa w" d="M10.5 16.3l3.8 3.8 7.4-7.6"/>',
    'a_alle_ok': '<rect class="f" x="4" y="4" width="24" height="24" rx="4"/><rect class="s" x="4" y="4" width="24" height="24" rx="4"/><path class="sa" d="M8 16.5l3 3 6.5-6.8M14.5 19.5l1 1 8-8.3"/>',
    'a_bezugsfertig': '<path class="f" d="M16 3.5l3 2.6 3.9-.6 1.3 3.7 3.7 1.4-.6 3.9 2.6 3-2.6 3 .6 3.9-3.7 1.4-1.3 3.7-3.9-.6-3 2.6-3-2.6-3.9.6-1.3-3.7-3.7-1.4.6-3.9-2.6-3 2.6-3-.6-3.9 3.7-1.4 1.3-3.7 3.9.6z"/><path class="s" d="M16 3.5l3 2.6 3.9-.6 1.3 3.7 3.7 1.4-.6 3.9 2.6 3-2.6 3 .6 3.9-3.7 1.4-1.3 3.7-3.9-.6-3 2.6-3-2.6-3.9.6-1.3-3.7-3.7-1.4.6-3.9-2.6-3 2.6-3-.6-3.9 3.7-1.4 1.3-3.7 3.9.6z"/><path class="sa w" d="M11.3 16.2l3.2 3.2 6.2-6.4"/>',
    'a_sicherheit': '<path class="f" d="M16 3.5l10 4v7.5c0 6.3-4.3 10.6-10 12.5C10.3 25.6 6 21.3 6 15V7.5z"/><path class="s" d="M16 3.5l10 4v7.5c0 6.3-4.3 10.6-10 12.5C10.3 25.6 6 21.3 6 15V7.5z"/><path class="sa" d="M9.5 15.5h13M11 19.5h10"/>',
    'a_gesperrt': '<circle class="s" cx="16" cy="16" r="11.5"/><path class="sa w" d="M7.9 24.1 24.1 7.9"/>',
    'a_warnung': '<path class="f" d="M16 4 29 27H3z"/><path class="sa" d="M16 4 29 27H3z"/><path class="sa w" d="M16 12v7"/><path class="dot a" d="M16 23.3h.01"/>',
    'a_dringend': '<circle class="f" cx="16" cy="16" r="11.5"/><circle class="sa" cx="16" cy="16" r="11.5"/><path class="sa w" d="M16 9.5v8"/><path class="dot a" d="M16 22.3h.01"/>',
    'a_offen': '<circle class="f" cx="16" cy="16" r="11.5"/><circle class="s" cx="16" cy="16" r="11.5"/><path class="sa" d="M16 9v7l4.5 3"/>',
    'a_eilig': '<path class="f" d="M18.5 3.5 6.5 18h8l-2 10.5 13-15h-8.5z"/><path class="sa" d="M18.5 3.5 6.5 18h8l-2 10.5 13-15h-8.5z"/>',
    'a_neu': '<path class="f" d="M4 9.5A2.5 2.5 0 0 1 6.5 7h19A2.5 2.5 0 0 1 28 9.5v13a2.5 2.5 0 0 1-2.5 2.5h-19A2.5 2.5 0 0 1 4 22.5z"/><path class="s" d="M4 9.5A2.5 2.5 0 0 1 6.5 7h19A2.5 2.5 0 0 1 28 9.5v13a2.5 2.5 0 0 1-2.5 2.5h-19A2.5 2.5 0 0 1 4 22.5z"/><path class="sa" d="M9 20v-8l5 8v-8M18.5 12v8h4M18.5 16h3.5"/>',
    'a_schloss': '<path class="s" d="M10.5 14v-3.5a5.5 5.5 0 0 1 11 0V14"/><rect class="f" x="6.5" y="14" width="19" height="13.5" rx="2.5"/><rect class="s" x="6.5" y="14" width="19" height="13.5" rx="2.5"/><path class="sa w" d="M16 19.3v3.4"/>',
    'a_mangel': '<path class="f" d="M24.6 4.6a6.5 6.5 0 0 0-8.9 8l-11 11a2.6 2.6 0 0 0 3.7 3.7l11-11a6.5 6.5 0 0 0 8-8.9l-3.7 3.7-3.7-1-1-3.7z"/><path class="s" d="M24.6 4.6a6.5 6.5 0 0 0-8.9 8l-11 11a2.6 2.6 0 0 0 3.7 3.7l11-11a6.5 6.5 0 0 0 8-8.9l-3.7 3.7-3.7-1-1-3.7z"/>',
    'a_mangelart': '<path class="s" d="M17.6 3.6a5 5 0 0 0-6.8 6.2l-7 7a2.1 2.1 0 0 0 3 3l7-7a5 5 0 0 0 6.2-6.8l-2.8 2.8-2.9-.8-.8-2.9z"/><path class="sa" d="M17 21h11M17 25.5h11M21 16.5h7"/>',
    'a_tuer': '<path class="f" d="M8 27V5h16v22z"/><path class="s" d="M8 27V5h16v22M4.5 27h23"/><path class="dot a" d="M20 16.5h.01"/>',
    'a_gebaeude': '<path class="f" d="M7 27V6.5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2V27z"/><path class="s" d="M7 27V6.5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2V27M4 27h24M11.5 9.5h3M17.5 9.5h3M11.5 14h3M17.5 14h3M11.5 18.5h3M17.5 18.5h3"/><path class="sa" d="M14 27v-4h4v4"/>',
    'a_haus': '<path class="f" d="M7 15v12h18V15L16 7.5z"/><path class="s" d="M4 16.5 16 6.5l12 10M7 14.5V27h18V14.5"/><path class="sa" d="M13.5 27v-6h5v6"/>',
    'a_haeuser': '<path class="s" d="M3.5 27V12.5L10 8l6.5 4.5V27"/><path class="f" d="M15.5 27V9.5L22 5l6.5 4.5V27z"/><path class="s" d="M15.5 27V9.5L22 5l6.5 4.5V27M2 27h28"/><path class="sa" d="M8 16h4M8 20.5h4M20 14h4M20 18.5h4M20 23h4"/>',
    'a_bett': '<path class="f" d="M4 22.5v-5.5h24v5.5z"/><path class="s" d="M4 27V9M4 22.5h24V27M28 22.5v-3.5a2 2 0 0 0-2-2H13v5.5"/><rect class="sa" x="5.8" y="13" width="5.5" height="4" rx="1.5"/>',
    'a_mail': '<rect class="f" x="4" y="7" width="24" height="18" rx="2.5"/><rect class="s" x="4" y="7" width="24" height="18" rx="2.5"/><path class="sa" d="M5 8.5 16 17l11-8.5"/>',
    'a_linie': '<path class="s" d="M4.5 5v22.5H28"/><path class="sa w" d="M8 22l5.5-6 4.5 3.5 7.5-9"/>',
    'a_flaeche': '<path class="s" d="M4.5 5v22.5H28"/><path class="f" d="M5 24 11 16l5.5 4L25 10v17.5H5z"/><path class="sa" d="M5 24 11 16l5.5 4L25 10"/>',
    'a_saeulen': '<path class="s" d="M4.5 5v22.5H28"/><path class="fa" d="M8 27.5V18h4v9.5zM15 27.5V11h4v16.5zM22 27.5V15h4v12.5z"/>',
    'a_anteile': '<path class="f" d="M16 4.5A11.5 11.5 0 1 1 4.5 16H16z"/><circle class="s" cx="16" cy="16" r="11.5"/><path class="fa" d="M14 3.6A11.5 11.5 0 0 0 3.6 14H14z"/><path class="s" d="M16 16V4.5M16 16H4.5"/>',
    'a_trend': '<path class="s" d="M4.5 5v22.5H28"/><path class="s" d="M8 23l5-5 4 3 7.5-8.5"/><path class="sa w" d="M20.5 12.3h4.3v4.3"/>',
    'a_reserve': '<rect class="s" x="3.5" y="9" width="22" height="14" rx="2.5"/><path class="s" d="M28.5 13.5v5"/><rect class="fa" x="6.5" y="12" width="10" height="8" rx="1"/><path class="f" d="M17 12h5.5v8H17z"/>',
    'a_vorjahr': '<path class="s" d="M5 11h20M20.5 6.5 25 11l-4.5 4.5"/><path class="sa" d="M27 21H7M11.5 16.5 7 21l4.5 4.5"/>',
    'a_vergleich': '<rect class="s" x="3.5" y="5" width="7" height="22" rx="1.8"/><rect class="f" x="12.5" y="5" width="7" height="22" rx="1.8"/><rect class="s" x="12.5" y="5" width="7" height="22" rx="1.8"/><rect class="s" x="21.5" y="5" width="7" height="22" rx="1.8"/><path class="sa" d="M5.5 20.5h3M14.5 14.5h3M23.5 18h3"/>',
    'a_ebenen': '<path class="f" d="M16 4.5 28 11l-12 6.5L4 11z"/><path class="s" d="M16 4.5 28 11l-12 6.5L4 11z"/><path class="sa" d="M4 16l12 6.5L28 16M4 21l12 6.5L28 21"/>',
    'a_legende': '<rect class="fa" x="4.5" y="6.5" width="5" height="5" rx="1"/><rect class="s" x="4.5" y="13.5" width="5" height="5" rx="1"/><rect class="f" x="4.5" y="20.5" width="5" height="5" rx="1"/><rect class="s" x="4.5" y="20.5" width="5" height="5" rx="1"/><path class="s" d="M13.5 9h14M13.5 16h11M13.5 23h13"/>',
    'a_tacho': '<path class="f" d="M4.5 21a11.5 11.5 0 0 1 23 0z"/><path class="s" d="M4.5 21a11.5 11.5 0 0 1 23 0M3 25h26"/><path class="sa w" d="M16 21l5-6.5"/><circle class="fa" cx="16" cy="21" r="1.8"/>',
    'a_szenarien': '<path class="s" d="M4 9h24M4 16h24M4 23h24"/><circle class="fa" cx="10" cy="9" r="2.6"/><circle class="fa" cx="21" cy="16" r="2.6"/><circle class="fa" cx="14" cy="23" r="2.6"/>',
    'a_praesentation': '<rect class="f" x="3.5" y="5" width="25" height="16.5" rx="2"/><rect class="s" x="3.5" y="5" width="25" height="16.5" rx="2"/><path class="s" d="M16 21.5V27M11 27.5h10"/><path class="fa" d="M13.5 9.5v7.5l6-3.75z"/>',
    'a_lineal': '<path class="f" d="M4 22 22 4l6 6-18 18z"/><path class="s" d="M4 22 22 4l6 6-18 18zM8.5 17.5l2.5 2.5M12 14l2 2M15.5 10.5l2.5 2.5M19 7l2 2"/>',
    'a_auswahl': '<rect class="s" x="4" y="4" width="24" height="24" rx="3.5"/><path class="sa" d="M8.5 11l1.8 1.8L13.5 9.5M8.5 19l1.8 1.8 3.2-3.3"/><path class="s" d="M16.5 11.5h7M16.5 19.5h7"/>',
    'a_protokoll': '<path class="f" d="M7 4.5h11l6 6v17H7z"/><path class="s" d="M7 4.5h11l6 6v17H7zM18 4.5v6h6"/><path class="s" d="M10.5 13h6M10.5 17h9M10.5 21h9"/><path class="sa" d="M10.5 9h3"/>',
    'a_pruefbericht': '<path class="f" d="M7 4.5h11l6 6v17H7z"/><path class="s" d="M7 4.5h11l6 6v17H7zM18 4.5v6h6"/><path class="s" d="M10.5 13h7M10.5 17h4"/><circle class="k" cx="23" cy="23.5" r="6.2"/><path class="sa w" d="M20 23.5l2 2 3.8-4"/>',
    'a_pdf': '<path class="f" d="M7 4.5h11l6 6v17H7z"/><path class="s" d="M7 4.5h11l6 6v17H7zM18 4.5v6h6"/><rect class="fa" x="9.5" y="16" width="12.5" height="6.5" rx="1.2"/>',
    'a_export': '<rect class="f" x="3.5" y="6" width="17" height="20" rx="2"/><path class="s" d="M20.5 12V8a2 2 0 0 0-2-2h-13a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h13a2 2 0 0 0 2-2v-4M3.5 12.5h17M3.5 19h12M10 6v20"/><path class="sa w" d="M16 16h12.5M24.5 12l4 4-4 4"/>',
    'a_kopieren': '<rect class="f" x="10.5" y="10.5" width="17" height="17" rx="2.5"/><rect class="s" x="10.5" y="10.5" width="17" height="17" rx="2.5"/><path class="s" d="M21.5 10.5V7a2.5 2.5 0 0 0-2.5-2.5H7A2.5 2.5 0 0 0 4.5 7v12A2.5 2.5 0 0 0 7 21.5h3.5"/><path class="sa" d="M14.5 16h9M14.5 21h6"/>',
    'a_bearbeiten': '<path class="f" d="M20.5 5.5l6 6L12 26H6v-6z"/><path class="s" d="M20.5 5.5l6 6L12 26H6v-6zM17 9l6 6"/><path class="sa" d="M16 27h11"/>',
    'a_anzeigen': '<path class="f" d="M2.5 16S7.5 7 16 7s13.5 9 13.5 9-5 9-13.5 9S2.5 16 2.5 16z"/><path class="s" d="M2.5 16S7.5 7 16 7s13.5 9 13.5 9-5 9-13.5 9S2.5 16 2.5 16z"/><circle class="sa" cx="16" cy="16" r="4.3"/><circle class="fa" cx="16" cy="16" r="1.8"/>',
    'a_filter': '<path class="f" d="M4 5.5h24l-9.5 11v8l-5 3v-11z"/><path class="s" d="M4 5.5h24l-9.5 11v8l-5 3v-11z"/><path class="sa" d="M8 9.5h16"/>',
    'a_mehr': '<circle class="fa" cx="7.5" cy="16" r="2.4"/><circle class="fa" cx="16" cy="16" r="2.4"/><circle class="fa" cx="24.5" cy="16" r="2.4"/>',
    'a_neu_plus': '<path class="sa w" d="M16 6v20M6 16h20"/>',
    'a_aufraeumen': '<rect class="f" x="4" y="5" width="24" height="7" rx="1.8"/><rect class="s" x="4" y="5" width="24" height="7" rx="1.8"/><path class="s" d="M6 12v13a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2V12"/><path class="sa" d="M12.5 17h7"/>',
    'a_weiter': '<path class="sa w" d="M5 16h20M18 9l7 7-7 7"/>',
    'a_flure': '<path class="s" d="M5 26V16h11V6h11"/><circle class="fa" cx="5" cy="26" r="2.4"/><circle class="f" cx="16" cy="16" r="2.4"/><circle class="s" cx="16" cy="16" r="2.4"/><path class="sa" d="M23.5 2.5 27 6l-3.5 3.5"/>',
    'a_einlesen': '<path class="sa" d="M26.5 12.5A11 11 0 0 0 6.2 9.5M5.5 19.5a11 11 0 0 0 20.3 3"/><path class="s" d="M5.5 4v5.5H11M26.5 28v-5.5H21"/><circle class="fa" cx="16" cy="16" r="2.6"/>',
    'a_hochladen': '<path class="f" d="M4 20h7l1.5 3h7l1.5-3h7v5a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2z"/><path class="s" d="M4 20v5a2 2 0 0 0 2 2h20a2 2 0 0 0 2-2v-5M4 20h7l1.5 3h7l1.5-3h7"/><path class="sa w" d="M16 16V4.5M11.5 9 16 4.5 20.5 9"/>',
    'a_zurueck': '<path class="s w" d="M20 6 10 16l10 10"/>',
    'a_vor': '<path class="s w" d="M12 6l10 10-10 10"/>',
}

# 1.40: Fluent-Name → eigenes Piktogramm. Gleiche Bedeutung = gleiches Bild (Drucken, QR, Standort, Einstellungen …).
ERSATZ: dict[str, str] = {
    'calendar_today': 'a_heute',
    'calendar_day': 'a_tag',
    'calendar_week_numbers': 'a_woche',
    'calendar_month': 'a_monat',
    'calendar_date': 'a_zeitraum',
    'calendar_clock': 'a_geplant',
    'calendar_arrow_right': 'a_naechste',
    'calendar_arrow_counterclockwise': 'a_letzte',
    'calendar_ltr': 'kalender',
    'calendar': 'kalender',
    'calendar_add': 'kalender',
    'calendar_edit': 'kalender',
    'person': 'a_person',
    'people': 'a_personen',
    'people_list': 'a_personenliste',
    'people_team': 'a_team',
    'person_add': 'a_person_neu',
    'person_alert': 'a_notfall',
    'person_arrow_right': 'a_person_weiter',
    'person_question_mark': 'a_person_frage',
    'home_checkmark': 'a_haus_ok',
    'key': 'a_schluessel',
    'seat': 'a_sitzplatz',
    'hat_graduation': 'massnahmen',
    'checkmark_circle': 'a_frei',
    'checkmark_circle_square': 'a_alle_ok',
    'checkmark_starburst': 'a_bezugsfertig',
    'prohibited': 'a_gesperrt',
    'warning': 'a_warnung',
    'alert_urgent': 'a_dringend',
    'clock': 'a_offen',
    'flash': 'a_eilig',
    'new': 'a_neu',
    'lock_closed': 'a_schloss',
    'wrench': 'a_mangel',
    'wrench_settings': 'a_mangelart',
    'broom': 'reinigung',
    'info': 'info',
    'door': 'a_tuer',
    'building': 'a_gebaeude',
    'building_home': 'a_haus',
    'building_multiple': 'a_haeuser',
    'bed': 'a_bett',
    'mail': 'a_mail',
    'qr_code': 'qr',
    'location': 'standort',
    'settings': 'einstellungen',
    'print': 'drucken',
    'data_line': 'a_linie',
    'data_area': 'a_flaeche',
    'data_bar_vertical': 'a_saeulen',
    'data_pie': 'a_anteile',
    'arrow_trending_lines': 'a_trend',
    'data_trending': 'a_trend',
    'battery_charge': 'a_reserve',
    'arrow_swap': 'a_vorjahr',
    'layout_column_three': 'a_vergleich',
    'layer': 'a_ebenen',
    'tag': 'a_legende',
    'gauge': 'a_tacho',
    'options': 'a_szenarien',
    'slide_play': 'a_praesentation',
    'ruler': 'a_lineal',
    'task_list_square_ltr': 'a_auswahl',
    'clipboard_task_list_ltr': 'a_protokoll',
    'document_checkmark': 'a_pruefbericht',
    'document_pdf': 'a_pdf',
    'table_arrow_up': 'a_export',
    'share': 'exportieren',
    'copy': 'a_kopieren',
    'edit': 'a_bearbeiten',
    'eye': 'a_anzeigen',
    'filter': 'a_filter',
    'more_horizontal': 'a_mehr',
    'add': 'a_neu_plus',
    'archive': 'a_aufraeumen',
    'arrow_right': 'a_weiter',
    'arrow_routing': 'a_flure',
    'arrow_sync': 'a_einlesen',
    'arrow_upload': 'a_hochladen',
    'chevron_left': 'a_zurueck',
    'chevron_right': 'a_vor',
    'history': 'verlauf',
    'search': 'suche',
}


def vorhanden(name: str) -> bool:
    return name in SYMBOLE


def svg(name: str, groesse: int | None = None) -> str:
    """SVG-Text (leer, wenn es das Piktogramm nicht gibt)."""
    inhalt = SYMBOLE.get(name)
    if inhalt is None:
        return ""
    g = f' width="{groesse}" height="{groesse}"' if groesse else ""
    return f'<svg class="m-pk" viewBox="0 0 32 32"{g} aria-hidden="true" focusable="false">{inhalt}</svg>'


CSS = """
:root { --pk-p: #3D5558; --pk-a: #0B6E66; --pk-t: rgba(11,110,102,.16); --pk-w: #B42318; --pk-wt: rgba(180,35,24,.14);
  --pk-k: #F7F8F8; }
body { --pk-k: var(--ob-band, #F7F8F8); }   /* 1.64: erst am body auflösen – dort steht die Bandfarbe (auch dunkel) */
body.mod-dunkel { --pk-p: #B4C7C6; --pk-a: #5ED6C6; --pk-t: rgba(94,214,198,.22); --pk-w: #FF8A80;
  --pk-wt: rgba(255,138,128,.2); }
.m-pk { display: block; width: 100%; height: 100%; overflow: visible; }
.m-pk .s, .m-pk .sa, .m-pk .sw { fill: none; stroke-width: 1.75; stroke-linecap: round; stroke-linejoin: round; }
.m-pk .s { stroke: var(--pk-p); } .m-pk .sa { stroke: var(--pk-a); } .m-pk .sw { stroke: var(--pk-w); }
.m-pk .w { stroke-width: 2.6; } .m-pk .dash { stroke-dasharray: 2.2 2.6; }
.m-pk .f { fill: var(--pk-t); } .m-pk .fa { fill: var(--pk-a); } .m-pk .fw { fill: var(--pk-wt); }
.m-pk .k, .m-pk .k2 { fill: var(--pk-k); }
.m-pk .dot { fill: none; stroke: var(--pk-p); stroke-width: 2.6; stroke-linecap: round; }
.m-pk .dot.a { stroke: var(--pk-a); }
/* 1.64: dezente Bereichsfarbe je Registerkarte (Option „Je Bereich“) – Linien bleiben einheitlich, nur Akzent und
   Tönung tragen die Farbe. Signalfarben (Inline-Stil am Symbol) haben Vorrang; „Nur Signalfarben“ (body.sym-signal)
   schaltet das ab. */
body:not(.sym-signal) .rb-anreisen .m-sym:not([style]),
body:not(.sym-signal).seite-rb-anreisen .m-kz .m-sym:not([style]) { --pk-a: #15803D; --pk-t: rgba(21,128,61,.15); }
body:not(.sym-signal) .rb-zimmer .m-sym:not([style]),
body:not(.sym-signal).seite-rb-zimmer .m-kz .m-sym:not([style]) { --pk-a: #1D5FBF; --pk-t: rgba(29,95,191,.14); }
body:not(.sym-signal) .rb-planung .m-sym:not([style]),
body:not(.sym-signal).seite-rb-planung .m-kz .m-sym:not([style]) { --pk-a: #6D3FC8; --pk-t: rgba(109,63,200,.14); }
body:not(.sym-signal) .rb-auswertung .m-sym:not([style]), body:not(.sym-signal) .rb-prognose .m-sym:not([style]),
body:not(.sym-signal) .rb-diagramm .m-sym:not([style]),
body:not(.sym-signal).seite-rb-auswertung .m-kz .m-sym:not([style]) { --pk-a: #B45309; --pk-t: rgba(180,83,9,.14); }
body:not(.sym-signal) .rb-ki .m-sym:not([style]),
body:not(.sym-signal).seite-rb-ki .m-kz .m-sym:not([style]) { --pk-a: #0E7490; --pk-t: rgba(14,116,144,.15); }
body:not(.sym-signal) .rb-verwaltung .m-sym:not([style]),
body:not(.sym-signal).seite-rb-verwaltung .m-kz .m-sym:not([style]) { --pk-a: #475569; --pk-t: rgba(71,85,105,.15); }
body.mod-dunkel:not(.sym-signal) .rb-anreisen .m-sym:not([style]),
body.mod-dunkel:not(.sym-signal).seite-rb-anreisen .m-kz .m-sym:not([style]) { --pk-a: #6EE7A0; --pk-t: rgba(110,231,160,.2); }
body.mod-dunkel:not(.sym-signal) .rb-zimmer .m-sym:not([style]),
body.mod-dunkel:not(.sym-signal).seite-rb-zimmer .m-kz .m-sym:not([style]) { --pk-a: #8AB8FF; --pk-t: rgba(138,184,255,.2); }
body.mod-dunkel:not(.sym-signal) .rb-planung .m-sym:not([style]),
body.mod-dunkel:not(.sym-signal).seite-rb-planung .m-kz .m-sym:not([style]) { --pk-a: #C4A8FF; --pk-t: rgba(196,168,255,.2); }
body.mod-dunkel:not(.sym-signal) .rb-auswertung .m-sym:not([style]), body.mod-dunkel:not(.sym-signal) .rb-prognose .m-sym:not([style]),
body.mod-dunkel:not(.sym-signal) .rb-diagramm .m-sym:not([style]),
body.mod-dunkel:not(.sym-signal).seite-rb-auswertung .m-kz .m-sym:not([style]) { --pk-a: #FCC56A; --pk-t: rgba(252,197,106,.2); }
body.mod-dunkel:not(.sym-signal) .rb-ki .m-sym:not([style]),
body.mod-dunkel:not(.sym-signal).seite-rb-ki .m-kz .m-sym:not([style]) { --pk-a: #67D8EE; --pk-t: rgba(103,216,238,.2); }
body.mod-dunkel:not(.sym-signal) .rb-verwaltung .m-sym:not([style]),
body.mod-dunkel:not(.sym-signal).seite-rb-verwaltung .m-kz .m-sym:not([style]) { --pk-a: #B6C2D2; --pk-t: rgba(182,194,210,.2); }
"""
