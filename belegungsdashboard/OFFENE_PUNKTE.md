# Offene Punkte und Arbeitsweise (Stand v6.3.0, 13.10.2026)

## Als Nächstes

- Erledigt in 6.0/6.1: Zimmer-/Personenkarte, mehrere Fenster, Datensicherung, Tabs, Startseite mit Kacheln,
  neuer Kalender, minimiert sparsam, kein Überlauf bei 1000 px. Rückweg: ROLLBACK.md.
- Offen: Nutzer-Satz „außerdem wäre es gut wenn man.“ (12.10.) war unvollständig – nachfragen.
- 6.2: Design wählbar (Klassisch/Modern/Kompakt/Warm), Name änderbar. Nutzer wählt sein Design – ggf. nachjustieren.
- Erledigt in 6.3 (13.10.): Startseiten-Titel, KW mit Daten, Engpässe erklärt/Grenzen einstellbar, Posteingang
  (Gästehaus, Anmeldung, Storno, Abbruch mit Prüfliste, Hinweis; Outlook-Übernahme ungetestet), Optimierung.
- **Datenschutz offen:** Repository auf GitHub ist öffentlich; frühe Commits (8ef10e3, 227827c vom 03.10.) enthalten
  echte Namen/TN-Nr. in Testdaten. Nutzer entscheidet: Repository privat schalten und/oder Historie bereinigen.
- Mail-Erkennung mit weiteren echten Beispielen nachschärfen (Anmeldungen zu Maßnahmen, Verlängerungen).
- Weitere Punkte sammelt der Nutzer übers Wochenende – zusammen als nächstes Update einspielen.
- Noch offen von früher: UWT-Zimmervorschlags-Maske wie im anderen System (Screenshots folgen vom Nutzer).
- Zu klären (siehe v5.3.0): CUW24 DZ-Nr. 1 mit drei Personen; Einzelzimmer-Wünsche trotz DZ-Liste
  (CUA24, CUK25); Kreuz bei CUK24 Dag/Hofmeier auf der handschriftlichen Liste.

## Arbeitsweise mit dem Nutzer

- Der Nutzer arbeitet **lokal**, nicht mit Git: Lieferung als `INNternat_Update.zip` (Inhalt des Programmordners
  ohne Hülle, ohne `.venv`, `__pycache__`, `.pytest_cache`), entpacken nach
  `C:\Users\claudio.russo\Documents\GitClaude\INNternat`, Start mit `Start.bat`.
- Vor größeren Umbauten: Sicherungs-Branch + Zip + ROLLBACK.md; Overhaul auf eigenem Branch.
- Bei jeder Lieferung die Version in `belegung/__init__.py` erhöhen (der Nutzer prüft „v…“ in der Seitenleiste)
  und die README ergänzen.
- Oberfläche: nichts abschneiden, nichts überladen (lieber Menü/Reiter als viele Knöpfe), bei 125 %/150 % und
  schmalem Fenster (1000 px) prüfen – keine waagerechte Bildlaufleiste.
- Zimmer immer numerisch sortiert, West/Ost nicht anzeigen (Flur nur intern für die Planung).
- Echte Daten (Gebäudeplan, Klassenübersicht, Blockpläne, Anreiselisten) liegen nur beim Nutzer – nie ins
  Repository; Tests nur mit erfundenen Namen und IDs.

## Wichtige Regeln (Kurzfassung)

- EMR nur Haus 2, Etage 1–2; Haus 2 Zimmer 101–110 ausschließlich EMR; Haus 2, 1. OG (101–124) nur Kurzmaßnahmen.
- Doppelzimmer nur UWT und Gäste – ohne Ausnahme (auch nicht von Hand). Tiere: zuerst Haus 3.1 UG, dann EG.
- Lange Aufenthalte (Hauptmaßnahmen) bei der Flurwahl auf Flure mit langen Aufenthalten (`flur_mischung`, Gewicht 3 – höher lässt Personen ohne Zimmer). UWT nur Haus 3.2, 3.3, 6.
  Gästezimmer Haus 2, 6. OG nie vorschlagen, von Hand als Ausnahme möglich; von Hand geht jedes freie Zimmer.
- UWT: DZ-Partner laut Klassenübersicht zusammen, „-“/ohne Partner allein; kommende Blöcke automatisch zuteilen.
- Reinigung: eine Zeile je Zimmerwechsel, „sauber bis spätestens“ = letzter Werktag vor der nächsten Anreise
  (Sa/So wird nicht gereinigt). Facility-Check (Elektrik, Fenster) nach Auszug ab 6 Monaten Aufenthalt.
- Gebäudeplan-Abgleich nach Namen; Konflikte (geplantes Zimmer inzwischen belegt/gesperrt) melden, „Neu planen“.
