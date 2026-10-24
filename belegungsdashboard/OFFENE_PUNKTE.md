# Offene Punkte und Arbeitsweise (Stand v6.27.1, 24.10.2026)

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
- 6.15: Zimmer finden (Reiter „Zimmer“: Chips, Übersicht/Karten/Liste), Reiter angeheftet, Drucken neben Übernehmen,
  Renovierungsliste +23 (Vinyl vermutet – Nutzer schaut die Zimmer noch an). Nicht im Gebäudeplan: 6-101, 6-204,
  6-205, 6-208, 3.1-214, 3.1-220.
- 6.16: Glocke + Leiste „Neuigkeiten“ (Nutzer: A ausblendbar + B; Hintergrund-Meldungen nur noch dort), Mängel je
  Zimmer (Vorschläge in der Zimmerkarte, Filter, FM-Liste), Symbole Farbrolle/Werkzeug. Mängel-Katalog ggf. mit dem
  Nutzer/FM abstimmen.
- 6.17: UI/UX-Gesamtüberarbeitung (Zeitstrahl-Kopf, Termine nach Dringlichkeit, Übersicht, Datenstand, Kontrast/Fokus).
  Zu prüfen beim Nutzer:
  * „unknown1“: Die Ursache steckt vermutlich im neueren Gebäudeplan-Export. In den hier vorliegenden Daten kommt der
    Name nicht vor. Daten & Import → Gebäudeplan nennt jetzt Anzahl und Zimmer.
  * Windows-Darstellung (Schrift, 125/150 %) live ansehen.
- 6.17.1: Aus der Inventur-Datei „Inventur_Abgleich_System.xlsx“ wurden nur die gewünschten Spalten übernommen:
  Nachttischlampe (32 Zimmer) und Bett1 (15 Zimmer). Noch nicht übernommen, Nutzer entscheidet:
  * „Matratze getauscht“ (mit Maß/Härte/Datum) und „Rauchmelder neu“.
  * Blatt „Sonstige“: nicht eindeutig zugeordnet.
  * Blatt „Fehlende Zimmer“ (siehe auch 6.18): 39 Zimmer laut Raumplan, die es im System nicht gibt (z. B. 2-113, Gästezimmer 2-601 ff.).
- 6.18: Zimmerzustand aus ZKL_26_V1 übernommen (Reno als Monat, Boden PVC/Teppich, 71 Mängel, Katalog
  „Renovierung nötig“). Zu klären mit dem Nutzer:
  * Was bedeuten Art „A“/„B“ und Reno „R“/„RZ“/„K0“?
  * Ist „PVC“ in der ZKL dasselbe wie „Vinyl“? Haus 6/4. OG ist sicher als Vinyl eingetragen, die ZKL sagt PVC.
    Dort wurde nichts geändert.
  * Haben sich ältere ZKL-Notizen ohne Erledigt-Vermerk erledigt? Nicht übernommen wurden 2-218, 3.3-204, 3.3-224
    und 3.3-301. Übernommen wurden u. a. 2-106, 3.1-114 und 3.3-323; sie lassen sich in der Zimmerkarte antippen,
    wenn sie behoben sind.
  * 28 Zimmer aus der ZKL gibt es im Zimmerplan nicht (JWG 3.1-2xx/3xx, Jugendhilfe Haus 6, 2-124, 2-413, 2-513,
    2-514, 2-517, 3.3-123, 3.3-319, 6-1009).
- 6.19: „!“-Filter, FM-Bericht (Druck, Excel zum Abarbeiten und Wiedereinlesen), unbewohnbare Zimmer werden nicht
  zugeteilt. Von selbst sperren nur Schimmel und Ungeziefer, den Rest entscheidet der Nutzer je Mangel. Aus der ZKL
  ist bisher nichts als unbewohnbar markiert. Kandidaten für den Nutzer: 2-204 (Matratze fehlt), 3.3-205 (Reno – alle
  Möbel raus), 3.1-U04 (Feuermelder fehlt).
- 6.20: Mieter-Unterlagen per Maske (Mietvertrag, Wohnungsgeberbestätigung, SEPA, Mietschuldenfreiheit),
  Eintrag im Zimmerplan, Verlängerung als Nebenabrede (.docx + PDF). Vom Nutzer zu prüfen:
  * Wortlaut in `Vorlagen/Mieter/Mietvertrag.vorlage`. Gegenüber MV26-010 sind offensichtliche Fehler geglättet:
    * „Einzelzimmern“ → „Einzelzimmer“.
    * „Britten“ → „ein dem Dritten“ (§ 7.4).
    * „Zustimmung des Vermieters“ → „der Vermieterin“ (§ 10.5).
    * § 12.1: „Der Vermieterin oder ihren Beauftragten steht … frei“ und „darf die Vermieterin“.
    * § 8.2: „die Vermieterin … zu benachrichtigen“.
    * „seinem Beauftragten“ → „ihrem“.
    * Pronomen durchgehend passend zur Anrede (das Original mischte „sie/er“).
    * § 4: „XX.XX.20XX“ ist jetzt das Kaution-bis-Datum aus der Maske.
  * Layout: Der Vertrag ist neu gesetzt (Wortlaut gleich, Seiten kompakter als das Word-Original). Das Logo steht
    auf Seite 1.
  * Die Word-Datei der Nebenabrede ist ohne Word erzeugt. Bitte einmal in Word öffnen und ansehen.
  * Die alte Vorlage `.doc` (Nebenabrede) wird nicht mehr gebraucht. Ihr Text steckt im Programm.
- 6.21: Seite „Mieter“ in der Seitenleiste; Mängel in Warnsignalfarben rot / orange / gelb. Zuordnung der Mängelarten zu „dringend“
  (Heizung, Bad, Abfluss, Wasser, Elektrik, Tür, Rauchmelder, Matratze, Geruch) bzw. „leicht“ (Rest) ist ein
  Vorschlag; „nicht bewohnbar“ setzt der Nutzer je Mangel. Bei Bedarf Zuordnung mit dem Nutzer/FM abstimmen.
- 6.22: „Posteingang“ → „Assistenz“ (Eingabe in normaler Sprache → Kalender, Mängel, Notizen; Mails im zweiten
  Reiter); Kaution im Mietvertrag optional. Offen/zu entscheiden:
  * Erledigt in 6.23: Assistent und Assistenz zusammengelegt (Reiter „Fragen & Zahlen“).
  * Stichwörter für Mängel ggf. mit dem Nutzer ergänzen.
  * Die Erkennung arbeitet mit Regeln. Mit KI-Anbindung (Claude) ließen sich auch freiere Sätze verstehen.
- 6.23: Assistenz pflegt Personen ein („Nachname, Vorname vom … bis … in 2-408“ → Zimmerplan, belegt/geplant).
  Beispiel des Nutzers geprüft mit Datenkopie: Die Person stand im Gebäudeplan in 2-408 nur bis 30.09.2026 (danach
  Zimmerfreigabe 01.10.2026–31.03.2027). Der Befehl verlängert auf 24.06.2027.
  * Offen/zu entscheiden: Eingepflegt wird durchgehend, auch über eine Zimmerfreigabe hinweg; die Assistenz weist
    darauf hin. Soll das Zimmer in der Freigabe frei bleiben, zwei Zeilen eingeben (vor und nach der Freigabe).
    Beim Nutzer nachfragen, was die Freigabe bei dieser Person bedeutet.
  * Namen werden nur in der Form „Nachname, Vorname“ erkannt (wie in allen Listen).
- 6.24: Zimmer von Hand zur Reinigung hinzufügen (Reiter „Reinigung“, Zimmerkarte, Assistenz).
  * Offen/zu entscheiden: Auswahl der Gründe (Zwischen-, Grund-, Sonderreinigung, nach Reparatur, vorbereiten, nach
    Ungeziefer/Schimmel) ggf. mit dem Nutzer bzw. der Reinigung abstimmen.
  * Wiederkehrende Reinigungen: vom Nutzer nicht gewünscht (19.10.).
- 6.24.1: „Zimmer hinzufügen …“ ging nicht (Nutzer-Meldung). Ursache: `clicked(bool)` landete im Parameter
  `zimmer`. Lehre: Knöpfe in Prüfskripten immer echt anklicken (QTest.mouseClick), nicht die Methode aufrufen.
- 6.25: Nutzer-Meldung 21.10.: Gäste und Reservierungen über die Assistenz wurden nur Termine/Notizen. Ursachen:
  Kopfzeile mit Zeitraum galt nicht für die Zeilen darunter, „Vorname Nachname“ und „Gast reserviert“ ohne Namen
  wurden nicht erkannt, „25.01. – 30.01.2027“ wurde als ein Datum gelesen. Behoben.
  * Offen: Die bisher falsch angelegten Termine/Notizen muss der Nutzer per „Rückgängig“ entfernen und die Zeilen
    neu eingeben.
  * Reservierungen heißen „Bezeichnung (Zimmer)“. Die Bezeichnung ist beim Nutzer nur ein Platzhalter für Reservierungen
    über das Kundenmanagement – passt so (21.10.).
- 6.25.1: Nutzer-Meldung 21.10.: noch immer nicht im Zeitstrahl. Ursachen: Zeilen nur mit Zimmernummer unter der
  Kopfzeile und klein geschriebene Namen wurden nicht gebucht. Behoben; im Zeitstrahl Januar 2027 mit echten Klicks
  geprüft. Falls es beim Nutzer weiter hakt: genaue Eingabe (Text aus „Zuletzt erledigt“) erfragen.
- **Datenschutz (24.10.):** Ein echter Name aus einer Nutzer-Nachricht stand in einem Code-Kommentar (6.25.1). Er war
  nie im Update-Paket, aber auf GitHub. Auf Wunsch des Nutzers wurde die Historie bereinigt (2 Commits neu, Inhalt
  gleich). Über die alte Commit-Nummer ist er bei GitHub noch abrufbar, bis GitHub aufräumt. **Weiter offen beim
  Nutzer:** Repository auf privat stellen (es ist öffentlich). Lehre: Der Namens-Scan bricht jetzt den Commit ab und
  enthält auch Namen aus Nutzer-Nachrichten und Screenshots.
- 6.26: Gebäudeplan wird vor dem Übernehmen mit Belegung und Planung verglichen; Vorrang je Person wählbar; Ordner
  „Gebaeudeplan“ übernimmt nur noch ohne Unterschiede automatisch.
  * Mit Datenkopie geprüft: Der Plan vom 03.10. gegen sich selbst ergibt keine Unterschiede, gezielte Änderungen werden
    alle gefunden.
  * Erledigt in 6.27: Sperrungen und Zimmerfreigaben werden gemeldet (Nutzer wollte es).
- 6.27: Nutzer fand die Auswahl „in der Planung behalten“ irreführend. Jetzt heißt es „eigener Eintrag“, und die
  Optionen nennen Zimmer und Zeitraum. Mail zum Vertragsende für Mieter (Outlook öffnet, Nutzer sendet).
  * Offen/zu entscheiden: Mailtexte (Frist 4 Wochen vor Ende, Absender „Ihr Team des Internats Goslar“) vom Nutzer
    prüfen lassen. Eigene Fassung geht über die Vorlagen-Dateien.
  * Outlook-Anbindung („In Outlook öffnen“) nur unter Windows mit pywin32 – hier nicht testbar, mailto-Weg geprüft.
- 6.27.1: Nutzer fragte, was „neuer Plan“ und „System“ sind – das Programm wird auch von anderen genutzt. Jetzt:
  „Neuer Gebäudeplan“ (Datei, Stand) vs. „Zimmerplan jetzt“ (bisheriger Gebäudeplan + eigene Einträge), beides mit
  Dateiname/Stand erklärt. Blockschulplan 2026/27 (Nutzer-Upload 24.10.) war schon importiert und geprüft – alle Blöcke
  stimmen; keine Änderung nötig.
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
