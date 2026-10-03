"""Belegungsdashboard – Export in Belegungsdashboard.html (Konsole, ohne GUI).

    python belegungsdashboard_export.py [--ohne-server] [Pivot-Datei] [HTML-Datei]

Liest die Pivot (unter Windows standardmäßig mit OLAP-Refresh über Excel, sonst die in der
Datei gespeicherten Werte), berechnet die Prognose und ersetzt nur den JSON-Datenblock
<script id="__data__" type="application/json"> in der HTML-Datei. Vorher wird eine .bak
angelegt. In die Excel-Datei wird nie geschrieben.
"""

from __future__ import annotations

import sys
import traceback
from datetime import datetime
from pathlib import Path

from belegung import export, laden
from belegung.konfig import programmordner

HTML_DATEINAME = "Belegungsdashboard.html"


def log(text: str) -> None:
    print(f"[{datetime.now():%H:%M:%S}] {text}", flush=True)


def main() -> int:
    argumente = [a for a in sys.argv[1:] if not a.startswith("--")]
    ohne_server = "--ohne-server" in sys.argv
    interaktiv = sys.stdin is not None and sys.stdin.isatty()
    try:
        excel = Path(argumente[0]) if argumente else laden.excel_suchen()
        html = Path(argumente[1]) if len(argumente) > 1 else programmordner() / HTML_DATEINAME
        if excel is None or not excel.exists():
            raise FileNotFoundError("Keine Pivot-Datei gefunden (pivot_neu.xlsx im Programmordner erwartet).")
        if not html.exists():
            raise FileNotFoundError(f"'{html}' nicht gefunden.")
        refresh = laden.refresh_moeglich() and not ohne_server
        log(f"Pivot: {excel}")
        log(f"HTML:  {html}")
        ds = laden.lade(excel, refresh=refresh, fortschritt=log)
        if refresh and not ds.pivot_aktualisiert:
            log("HINWEIS: Server-Abruf fehlgeschlagen – exportiert wird der gespeicherte Pivot-Stand.")
        for s, m in ds.prognose.modelle.items():
            log(f"  {s}: {m.name}" + (f" (Backtest-Fehler ± {m.mae:.1f})" if m.mae else ""))
        zeichen = export.html_aktualisieren(html, export.baue_json(ds))
        log(f"'{html.name}' aktualisiert ({zeichen:_} Zeichen), Sicherung: {html.name}.bak".replace("_", "."))
        return 0
    except Exception as exc:
        print("\nFEHLER – Export abgebrochen:", exc)
        traceback.print_exc()
        return 1
    finally:
        if interaktiv and getattr(sys, "frozen", False):
            input("\nEnter zum Beenden …")


if __name__ == "__main__":
    sys.exit(main())
