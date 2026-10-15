# Offene Punkte und Arbeitsweise (Stand v6.14.0, 15.10.2026)

## Als Nächstes

- Erledigt in 6.0/6.1: Zimmer-/Personenkarte, mehrere Fenster, Datensicherung, Tabs, Startseite mit Kacheln,
  neuer Kalender, minimiert sparsam, kein Überlauf bei 1000 px. Rückweg: ROLLBACK.md.
- Offen: Nutzer-Satz „außerdem wäre es gut wenn man.“ (12.10.) war unvollständig – nachfragen.
- 6.2: Design wählbar (Klassisch/Modern/Kompakt/Warm), Name änderbar. Nutzer wählt sein Design – ggf. nachjustieren.
- Erledigt in 6.3 (13.10.): Startseiten-Titel, KW mit Daten, Engpässe erklärt/Grenzen einstellbar, Posteingang
  (Gästehaus, Anmeldung, Storno, Abbruch mit Prüfliste, Hinweis; Outlook-Übernahme ungetestet), Optimierung.
- Erledigt in 6.4 (13.10.): Umzug für Eingezogene (Zeitstrahl ziehen, Rechtsklick, Personenkarte).
- Erledigt in 6.5: Haus 3.1 UG nur mit Tier; Optimierung führt dieselbe Anreise auf einem Flur zusammen.
  Offen/zu entscheiden: Bewohner für Gruppen-Flure aktiv umziehen lassen? Flure für große Anreisen freihalten?
  (Messung 13.10.: RVL 21.10. mit 11 Personen auf 6 Fluren – mehr war nicht frei.)
- Erledigt in 6.6: ZKL-Import mit Abgleich (Nutzer wollte ausdrücklich nur Abgleich, keinen Umbau).
  Mit ZKL_26_V1 (Stand ~01.10.): 3 Zimmer laut ZKL bewohnt/im Plan frei, 2 nicht belegbar (Musterzimmer,
  Appartment 2-614), 21 SGH-Abweichungen (2.5 OG), 13 Tier-Pool-Abweichungen (3.1 E13–E26) – Nutzer entscheidet.
- 6.7: ZKL ist ab jetzt statisch (einmaliger Abgleich, Punkte bewohnt/nicht belegbar/Tier-Pool übernehmen, SGH nicht).
  Zimmerplan wird Hauptwerkzeug: geplant ↔ belegt umschaltbar (Personen und Umzüge), Gebäudeplan-Import optional.
- 6.8: Tabellen sortierbar. Frage „wie lange bis eine Maßnahme auf einem Flur“ simuliert (14.10.): heutiges
  Verfahren ~50 % auf Haupt-Flur bis 2030; je Kurs gruppieren ~60 % bis 06/2028; mit Tauschen (~86 Umzüge sofort)
  ~75–80 %. 6.9: beides umgesetzt (je Kurs ein Flur; Bewohner-Tausche als Umzugspaare, Datenkopie 34 % → 69 %).
- 6.10: Abreiseliste (Reiter „Abreisen“), Zimmer-Sortierung Haus → Etage → Nummer. Nutzer meldete, dass Zuteilen →
  Zimmer nicht sortiert – im Test (auch echter Mausklick) sortiert es; Version beim Nutzer prüfen lassen.
  Hinweis: gemerkte Reiter-Nummern (offene Tabs) verschieben sich durch den neuen Reiter um eins.
- 6.11: Renovierung/Boden je Zimmer, Zimmerliste. 2 Zeilen der Renovierungsliste nicht im Zimmerplan (6-205
  Jugendhilfe, 3.1-220); „3.3-110/301/305/313“ als 3.2 zugeordnet – bestätigt (6.14): laut Gebäudeplan 03.10. hat Haus 3.2 die Nummern
  101–113/201–213/301–313, Haus 3.3 114–127/214–227/314–327; die vier gibt es nur in 3.2.
- 6.12: „Frei nach Planung“ (Kopf, Engpässe, Startseite); Haus 6/4. OG renoviert + Vinyl (Datum unbekannt außer 405/408).
- 6.13 (Master-Prompt UX/Sicherheit): Vorschau vor folgenreichen Zimmer-Änderungen, Rückgängig, keine
  Doppelbelegung von Hand, kein halber Stand, Reiter gruppiert. Analyse und nächste Schritte: `UX_KONZEPT.md` (B.3).
  Vom Nutzer zu entscheiden: „Quellen“ umbenennen/zusammenlegen; Personenkarte als einziger Einstieg für Zimmerwechsel.
- **Datenschutz (15.10.):** Historie bereinigt – echte Namen/TN-Nr. (14 Namen, 7 Nummern in frühen Testdaten vom 03.10.)
  in allen Commits durch erfundene ersetzt, alle 19 Branches neu geschrieben (Inhalt der Spitzen unverändert). Alte
  Historie als Bundle beim Nutzer. **Noch offen beim Nutzer:** Repository auf privat stellen (über die Arbeitsumgebung
  nicht erlaubt). Alte Commits bleiben auf GitHub über ihre Nummer noch abrufbar, bis GitHub aufräumt – wer sicher
  gehen will: GitHub-Support um Entfernen der „cached views“ bitten (Liste alter Nummern: commit-map). Die beiden
  Branches des anderen Projekts (health-analytics, sharp-newton) haben dabei neue Commit-Nummern bekommen (Inhalt
  gleich); zurücksetzen wurde von der Arbeitsumgebung blockiert – Nutzer entscheidet.
- 6.14: Start „Heute“ (Vorgangsliste), Importe gebündelt (Quellen → Daten & Import), Verlauf, Seitenleiste nach
  Aufgaben, Zuteilen „Mehr“, ein Ablauf „Zimmer wechseln“. 3.3 → 3.2 (110/301/305/313) mit Gebäudeplan bestätigt.
  Zuteilen-Sortierung vom Nutzer bestätigt (nur noch Regressionstest).
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
