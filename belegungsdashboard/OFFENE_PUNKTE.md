# Offene Punkte und Arbeitsweise (Stand v5.14.0, 09.10.2026)

## Als Nächstes

- **Mehrere Ansichten gleichzeitig** (Wunsch vom 09.10.): z. B. Zeitstrahl und Zuteilen nebeneinander oder zwei
  Anreisen gleichzeitig offen. Idee: Reiter des Zimmerplans (und andere Seiten) per Rechtsklick/Knopf
  „In neuem Fenster öffnen“ als eigenes Fenster abkoppeln; Änderungen in einem Fenster aktualisieren die anderen
  (gemeinsamer Zustand über `Zustand.listen_geaendert`).
- Weitere Punkte sammelt der Nutzer übers Wochenende – zusammen als nächstes Update einspielen.
- Noch offen von früher: UWT-Zimmervorschlags-Maske wie im anderen System (Screenshots folgen vom Nutzer).
- Zu klären (siehe v5.3.0): CUW24 DZ-Nr. 1 mit drei Personen; Einzelzimmer-Wünsche trotz DZ-Liste
  (CUA24, CUK25); Kreuz bei CUK24 Dag/Hofmeier auf der handschriftlichen Liste.

## Arbeitsweise mit dem Nutzer

- Der Nutzer arbeitet **lokal**, nicht mit Git: Lieferung als `INNternat_Update.zip` (Inhalt des Programmordners
  ohne Hülle, ohne `.venv`, `__pycache__`, `.pytest_cache`), entpacken nach
  `C:\Users\claudio.russo\Documents\GitClaude\INNternat`, Start mit `Start.bat`.
- Bei jeder Lieferung die Version in `belegung/__init__.py` erhöhen (der Nutzer prüft „v…“ in der Seitenleiste)
  und die README ergänzen.
- Oberfläche: nichts abschneiden, nichts überladen (lieber Menü/Reiter als viele Knöpfe), bei 125 %/150 % und
  schmalem Fenster (1000 px) prüfen – keine waagerechte Bildlaufleiste.
- Zimmer immer numerisch sortiert, West/Ost nicht anzeigen (Flur nur intern für die Planung).
- Echte Daten (Gebäudeplan, Klassenübersicht, Blockpläne, Anreiselisten) liegen nur beim Nutzer – nie ins
  Repository; Tests nur mit erfundenen Namen und IDs.

## Wichtige Regeln (Kurzfassung)

- EMR nur Haus 2, Etage 1–2; Haus 2 Zimmer 101–110 ausschließlich EMR. UWT nur Haus 3.2, 3.3, 6.
  Gästezimmer Haus 2, 6. OG nie vorschlagen, von Hand als Ausnahme möglich; von Hand geht jedes freie Zimmer.
- UWT: DZ-Partner laut Klassenübersicht zusammen, „-“/ohne Partner allein; kommende Blöcke automatisch zuteilen.
- Reinigung: eine Zeile je Zimmerwechsel, „sauber bis spätestens“ = letzter Werktag vor der nächsten Anreise
  (Sa/So wird nicht gereinigt). Facility-Check (Elektrik, Fenster) nach Auszug ab 6 Monaten Aufenthalt.
- Gebäudeplan-Abgleich nach Namen; Konflikte (geplantes Zimmer inzwischen belegt/gesperrt) melden, „Neu planen“.
