# Tests der neuen Oberfläche – nach Themen

Dateinamen: `test_<thema>_v<version>_<inhalt>.py` – das Thema gruppiert, die Version zeigt, mit welcher Lieferung
der Test kam (bis 1.28 hießen die Dateien nur `test_v<version>.py`). Alle Tests nutzen nur erfundene Daten.

```bash
cd modern_ui
PYTHONPATH=.. python3 -m pytest -q tests                      # alle
PYTHONPATH=.. python3 -m pytest -q tests/test_netz_*.py         # ein Thema
```

## assistenz – Assistenz, Mails, Outlook, Tagesbriefing, Heute

- `test_assistenz_v015_heute_tempo.py` – 0.15: Heute als Newsfeed mit Briefing, schnellere Prognose (gleiche Werte, Zwischenspeicher) – erfundene Daten.
- `test_assistenz_v024_briefing.py` – 0.24: Tagesbriefing per Outlook-Termin oder E-Mail – ohne Personennamen. Erfundene Daten.
- `test_assistenz_v091_seitenleiste_mail.py` – 0.91 – Seitenleiste im Windows-Look (Menüband wählbar), Heute als eine Seite, „Diese Mail übernehmen“,
- `test_assistenz_v102_postfach.py` – 1.02 – Postfach auf „Aufgaben“ mit Öffnen in Outlook, Standorte im Menüband in einer Reihe. Nur erfundene Daten.
- `test_assistenz_v104_mail_erkennung.py` – 1.04 – Mail-Erkennung nachgeschärft, Outlook-Erkennung robuster, Maßnahmen-Auswahl im Menüband.
- `test_assistenz_v109_gaestehaus.py` – 1.09 – mehrere Gästehaus-Vormerkungen in einer Mail. Nur erfundene Namen, Orte und Anschriften.
- `test_assistenz_v136_nachrichten.py` – 1.36 – Nachrichten im Programm, Mail an FM, „Was ist zu tun?“
- `test_assistenz_v141_kurzmeldung.py` – 1.41 – Kurzmeldungen der Pforte (Schlüssel, Anreise heute), KI-Einschätzung, Kennzahlen → Belegung
- `test_assistenz_v143_chat.py` – 1.43 – Chat im Programm: Kanäle, gelesen je Person, Hinweis bei Neuem
- `test_maengel_v144_pa_mail.py` – 1.44 – QR-Mail aus der Mail-Benachrichtigung (Auswahl-Liste, UTC-Zeit)
- `test_maengel_v144_onedrive_ordner.py` – 1.44/1.45 – QR-Meldungen aus einem OneDrive-Ordner (Textdatei je Antwort, ohne Kennzeile, Platzhalter)
- `test_maengel_v146_fm_archiv.py` – 1.46 – QR-Meldungen an FM weiterleiten (Vorlage, Vermerk) und archivieren
- `test_start_v147_alte_version.py` – 1.47 – Start erkennt und beendet eine ältere Version im Hintergrund
- `test_postfach_v147_zimmer_fm_absender.py` – 1.47 – Postfach nur mit Zimmerbezug; FM-Mail aus dem gemeinsamen Postfach
- `test_mieter_v148_vertrag_gilt.py` – 1.48 – Mietvertrag gilt vor dem Gebäudeplan; Verlängern-Optionen, automatische Verlängerung
- `test_gaeste_v149_doppelzimmer.py` – 1.49 – Gäste & Mieter: Gast im Doppelzimmer, allein oder mit Begleitperson
- `test_gaeste_v150_bearbeiten_symbol.py` – 1.50 – Gast bearbeiten/entfernen, Programmsymbol aus dem Logo, Ersteller sichtbar
- `test_hausordnung_v151.py` – 1.51/1.52 – Hausordnung per QR bestätigen (je Aufenthalt) bzw. als Aushang mit QR-Code
- `test_zimmer_v153_emr_sperre.py` – 1.53 – EMR-Reservierung ist keine Sperre, echte Sperren bleiben (rot)
- `test_postfach_v154_filter_antworten.py` – 1.54 – Filter mit Zimmer-/Namenskontext, Absender-Regeln, Antworten/Weiterleiten
- `test_fm_v155_mangel_auftrag.py` – 1.55 – FM-Auftrag zu einem Mangel (alle Angaben, keine Bewohnernamen), Sammelmail, abgesicherter Klick
- `test_belegungsplan_v156_frei.py` – 1.56 – Heatmap „Frei“ (Stufen, frei ab, Mindestdauer, Sortieren/Filtern), Datum wählen, Legende
- `test_postfach_v157_erkennen_antwort.py` – 1.57 – Bereitstellung als Anmeldung, Zeitraum mit Wörtern, Antwort mit Zimmer, Mailfenster

## austausch – Austauschdatei altes ⇄ neues Programm

- `test_austausch_v120_1_exportordner.py` – 1.20.1 – Austauschdatei landet im Export-Ordner (im Programmfenster sind Browser-Downloads gesperrt).
- `test_austausch_v121_1_zimmerplanung.py` – 1.21.1 – Austausch: Zimmerplanung kommt an. Eintrag hier unverändert seit dem letzten Austausch → die Datei gilt

## befehle – Befehlssuche (Strg+K)

- `test_befehle_v071_suche.py` – 0.71: Befehlssuche in Strg+K – wie „Was möchten Sie tun?“ in Office.

## darstellung – Themes, Farben, Menüband, Symbole, Diagrammstil, Leitstand

- `test_darstellung_v008_themes.py` – 0.8: Designs – „original“ bleibt unberührt, alles Neue ist an body.pro / body.th-… gebunden.
- `test_darstellung_v065_menueband.py` – 0.65: Menüband wie in Office, sachliche Überschriften, Leitstand ohne Fachjargon. Ohne echte Daten.
- `test_darstellung_v066_optionen.py` – 0.66: Darstellungs-Optionen wie in Office – Farben, eigene Akzentfarbe, Zoom, Schrift, Diagrammtyp. Erfundene Werte.
- `test_darstellung_v067_menueband_aufgeraeumt.py` – 0.67: Menüband aufgeräumt – jeder Befehl an einer Stelle, Split-Buttons, Kontext-Registerkarte „Diagramm“.
- `test_darstellung_v068_glocke_hilfe.py` – 0.68: Glocke und Hilfe in der Titelleiste, Drucken und Hilfe unter Datei, F1-Hilfe je Seite.
- `test_darstellung_v069_registerkarten.py` – 0.69: Menüband nach zwei Reviews – Arbeitsbereiche als Registerkarten, sichtbare Ansichten, Statusleiste mit
- `test_darstellung_v072_farbdesigns.py` – 0.72: komplette Farbdesigns – Ton-Paletten aus einer Farbe, Helligkeit hell/gedämpft/dunkel, Färbung Akzent/ganz.
- `test_darstellung_v074_arbeitsflaeche.py` – 0.74 – Arbeitsfläche: eine Kontextzeile, feste Skalen, Dichte 28/36/44, Detailpanel angedockt, Menüband einklappbar.
- `test_darstellung_v075_diagramme_gross.py` – 0.75 – Diagramme groß und ziehbar, Diagramm ⇄ Tabelle, Klick → Detailpanel, ƒx Berechnung (Kennzahlen-Katalog),
- `test_darstellung_v089_diagramm_modus.py` – 0.89 – Darstellung der Diagramme wählbar (Karte | Klassisch | Einfach), Leitungsaussage „Einfach“.
- `test_darstellung_v096_baender_anteile.py` – 0.96 – deutliche Bänder, Schrift ohne Kontur, Bildschirmfoto, Diagrammentwurf im Menüband, Anteils-Diagramme.
- `test_darstellung_v099_gruppenfarben.py` – 0.99 – ein Gruppen-Farbschema überall, zweifarbige Menüband-Symbole (Microsoft 365), Werkzeuge der Seite im
- `test_darstellung_v100_waechter.py` – 1.00 – Wächter gegen „lokaler Import verdeckt Modulnamen“: In 0.97–0.99 brach das Belegungs-Diagramm ab, weil
- `test_darstellung_v101_symbole_knoepfe.py` – 1.01 – Knöpfe ohne eigenes Symbol bekommen im Menüband ein passendes Fluent-Symbol; „RIOS-Daten“ statt
- `test_darstellung_v112_gantt_diagrammtyp.py` – 1.12 – Gantt lesbar, Diagrammtyp gilt für alle Diagramme (auch Säulen), Zurück nach einem Sprung.
- `test_darstellung_v113_symbole.py` – 1.13 – Symbole aus einem Guss: jedes verwendete Fluent-Symbol liegt vollständig vor (groß/klein, Kontur/Fläche),
- `test_darstellung_v123_optionen.py` – 1.23 – Optionen im Menüband nur dort, wo sie wirken; Anteile getrennt wählbar; Datenbeschriftung auch bei
- `test_darstellung_v129_ein_modell.py` – 1.29 – Ein Einstellungsmodell für die Darstellung (vorher themes.py + darstellung_kern.py getrennt).
- `test_darstellung_v134_eine_oberflaeche.py` – 1.34 – nur noch das Menüband; Symbole klar oder farbig
- `test_darstellung_v138_start.py` – 1.38 – Start aufgeräumt, Mail an FM direkt senden
- `test_darstellung_v139_navigation.py` – 1.39 – Navigation 2.0: sieben Bereiche, Cockpit, Piktogramme, Kontextkarten, alte Namen in der Suche
- `test_darstellung_v140_kontext_symbole.py` – 1.40 – Kontextkarten mit eigenen Piktogrammen, Bedeutungsfarben, ruhigeres Cockpit, sicherer Python-Start

## export – Exporte (Excel, Änderungen, FM-Liste)

- `test_export_v037_aenderungen_fm.py` – 0.37: Änderungen je Zeitraum (Excel), Schloss/Schlüssel → FM-Auftrag statt Umplanen. Erfundene Daten.
- `test_export_v073_dateien.py` – 0.73: Datei → Exportieren – Tabellen der Ansicht als Excel/Zwischenablage, fertige Exporte. Erfundene Werte.

## maengel – Mängel und Meldungen per QR-Code

- `test_maengel_v128_qr_code.py` – 1.28 – QR-Codes: jeder erzeugte Code wird mit einem UNABHÄNGIGEN Decoder zurückgelesen (eigene GF-Rechnung,
- `test_maengel_v131_pruefanzeige.py` – 1.31 – Prüfanzeige „Verbindung prüfen“: warum kommt eine QR-Meldung nicht an?
- `test_maengel_v132_power_automate.py` – 1.32 – QR-Meldungen per Power-Automate-Mail aus einem Outlook-Ordner
- `test_maengel_v130_pruefcode.py` – 1.30 – Prüfcode auf dem QR-Etikett: zeigt, ob ein Gast die vorausgefüllte Zimmernummer geändert hat.
- `test_maengel_v128_qr_meldungen.py` – 1.28 – Meldungen per QR-Code (Forms, anonym): einlesen, Zimmer erkennen, übernehmen, verwerfen. Erfundene Daten.

## mieter – Mieter und Mietverträge

- `test_mieter_v025_vertragsnummern.py` – 0.25: Vertragsnummern der Mieter mit bisherigen Verträgen abgleichen – erfundene Daten.
- `test_mieter_v060_bearbeiten.py` – 0.60: Erstellten Mietvertrag bearbeiten (z. B. falsches Zimmer). Erfundene Namen und Beträge.
- `test_mieter_v087_schrift_karte.py` – 0.87 – Mietverträge mit einheitlicher Schrift; „Auf einen Blick“ (reine Satzvorlagen); Diagramm-Karte und

## netz – Netzwerkordner, Schreibsperre, Start, Installationspaket

- `test_netz_v054_netzwerkordner.py` – 0.54: Netzwerkordner – Speichern mit Wiederholung, Schreibsperre, persönliche Einstellungen je PC, Tagessicherung,
- `test_netz_v083_installation.py` – 0.83 – Komplettes Installationspaket: Pakete ohne Internet, eigene Instanz (INSTANZ.txt), kein Briefing von selbst.
- `test_netz_v084_portables_python.py` – 0.84 – Installationspaket mit portablem Python: der PC braucht kein installiertes Python.
- `test_netz_v085_edge_fehlersuche.py` – 0.85 – Installationspaket: Edge-Fenster statt eigenem Fenster (Netzlaufwerk), Fehlersuche.bat mit sichtbarer Konsole.
- `test_netz_v090_haertung.py` – 0.90 – Review-Härtung: Prüfen und Speichern unter derselben Sperre, Sperre mit Besitzer und Server-Uhr,
- `test_netz_v126_fencing.py` – 1.26 – Schreibsperre: lebende Sperre nie löschen, Fencing beim Speichern. Simulierte Sperrdateien.
- `test_netz_v126_sperre.py` – 1.26 – Lesen, Prüfen und Speichern unter EINER Schreibsperre (Mehrplatz). Erfundene Daten.
- `test_netz_v129_1_fensterprozess.py` – 1.29.1 – Fensterprozess (pywebview) hält sich nicht für einen Doppelstart.
- `test_netz_v127_start.py` – 1.27 – Start absichern: Lebenszeichen, Doppelstart, Python-Version, Fehleranzeige.
- `test_netz_v133_benutzer.py` – 1.33 – Benutzerkonten: Anmelden, Rollen, Standorte, Schutz vor Aussperren
- `test_netz_v135_umzug.py` – 1.35 – Umzug in den einen Netzwerkordner: ersetzen mit Sicherung, Konten bleiben, Ordner finden
- `test_netz_v136_leistung.py` – 1.36 – schneller: Zimmer-Vergleich, nach Planung einmal je Stand, Seitenwechsel ohne Neuladen
- `test_netz_v137_je_person.py` – 1.37 – persönliche Einstellungen je Person (angemeldet) statt je PC

## prognose – Belegungsprognose, Analytik, Rechenweg

- `test_prognose_v011_analytik.py` – 0.11: Executive-Analytics – KPIs, Erkenntnisse, Szenario, Vorjahr, Summary, Diagramm-Optionen (erfundene Zahlen).
- `test_prognose_v039_kennzahlen.py` – 0.39: Ehrliche Prognose-Kennzahlen, flurweise Renovierungsplanung (Haus 2/6). Erfundene Daten.
- `test_prognose_v086_challenge.py` – 0.86 – Prognose nach der Challenge: Verbleibskurve nur mit beobachteten Tagen und nur vorzeitigen Abgängen,
- `test_prognose_v095_laien.py` – 0.95 – Diagramme für Laien (Karte): drei Fragen, Probe statt Backtest-Linie, lesbare Prognose (Achse ab 0, Voll,
- `test_prognose_v122_vorjahr_tag.py` – 1.22 – Vorjahresvergleich je Tag: Prognose beginnt am Stichtag (beim Ist-Wert), Tooltip mit Tageswerten,
- `test_prognose_v123_rechenweg.py` – 1.23 – Rechenweg der Prognose: dieselben Zahlen wie das Hauptprogramm, mit Statistik. Erfundener Pivot.
- `test_prognose_v126_monatsende.py` – 1.26 – Prognose am Monatsletzten: kein doppelter Monat, keine Verschiebung um zwei Monate (Laufzeit-Korrektur,

## pruefbericht – Kleinigkeiten aus dem Prüfbericht 1.22

- `test_pruefbericht_v126_klein.py` – 1.26 – Kleinigkeiten aus dem Prüfbericht. Erfundene Daten.

## reinigung – Reinigungsliste und Facility-Checks

- `test_reinigung_v080_offen.py` – 0.80 – halb belegte Doppelzimmer eindeutig (nicht mehr gestrichelt wie „geplant“), Reinigungsliste „Offen – auch
- `test_reinigung_v081_druck.py` – 0.81 – Reinigungsliste drucken in der Reihenfolge, die auf dem Bildschirm eingestellt ist (z. B. nach Zimmer).
- `test_reinigung_v082_facility.py` – 0.82 – Facility-Checks: Zeitraum wählbar (auch ältere offene und eigener Zeitraum), Filter, Druck in der

## seiten – Seiten allgemein (Zeitstrahl, Archiv, Flur-Raster, UX)

- `test_seiten_v003_bereiche.py` – Neue Oberfläche ab 0.3: Anreisen-Zusätze, Zimmerkarte, Termine, Inventar, Einstellungen, Daten – nur erfundene Namen.
- `test_seiten_v026_flur_raster.py` – 0.26: Flur-Raster (Abreisewellen je Flur und Woche) – erfundene Daten.
- `test_seiten_v034_ux.py` – 0.34: Ergebnisse der UX-Prüfung – Änderungsbericht nach dem Einlesen, Kontrast, Sortieren per Tastatur. Erfundene Daten.
- `test_seiten_v049_archiv.py` – 0.49: Archiv früherer Anreisen über jeden Zeitraum – mit Zimmer aus Planung, Gebäudeplan oder Historie, Drucken und
- `test_seiten_v093_belegung.py` – 0.93 – Belegung: Mieter aus Mietverträgen, Zeitraum-Knöpfe vom heutigen Tag aus („Heute“), eigene Einfach-Ansicht;
- `test_seiten_zeitstrahl_reinigung.py` – Neue Oberfläche: Zeitstrahl, Reinigung, Mieter, Auswertung, Verwalten – nur erfundene Namen.

## standorte – Standorte (Datenordner, Gebäudepläne, PDF-Listen)

- `test_standorte_v035_datenordner.py` – 0.35: Standorte – getrennte Datenordner, Gebäudeplan-Formate Bad Pyrmont/Weser-Ems, neutrale Regeln. Erfundene Daten.
- `test_standorte_v036_pdf_listen.py` – 0.36: Anreiselisten als PDF („Teilnehmer Beginn“) für Bad Pyrmont/Weser-Ems, Showcase-Dock. Erfundene Daten.

## steuerung – Steuerung: Renovierung, Budget, Cockpit

- `test_steuerung_v041_kosten.py` – 0.41: Steuerung – Kostenmodell, Ausweichprüfung, Zimmerziel, Szenarien, Angebot einlesen, Prognosegüte,
- `test_steuerung_v042_budget.py` – 0.42: Planen nach Budget (Bau und Möbel getrennt), Monate mit möglichst wenig Engpässen. Erfundene Daten.
- `test_steuerung_v043_varianten.py` – 0.43: Einzelzimmer (komplett / nur Möbel), Varianten mit Empfehlung, Kostenherleitung, Szenarien über 5 Jahre,
- `test_steuerung_v044_klassen.py` – 0.44: Klassen A/B/C (Bau/Möbel getrennt), Baubudget fest + Möbelantrag, beste Kombination, Herkunft und Spanne,
- `test_steuerung_v046_fragen.py` – 0.46: Steuerung nach Fragen gegliedert, Tabellenvorlage, Festpreis solange ein Angebot gilt, nie nur zum Ausschöpfen,
- `test_steuerung_v047_vorhaben.py` – 0.47: Vorhaben → Maßnahmen → Kostenpositionen, Haupttreiber mit Nachweis, drei Statusachsen, Renovierung als
- `test_steuerung_v048_toepfe.py` – 0.48: Budget je Topf und Haushaltsjahr – verbraucht beim Auftrag (einstellbar), Ablauf über zwei Jahre, Budget je
- `test_steuerung_v114_rechenkern.py` – 1.14 – Rechenkern Steuerung: Kostenspanne mit gemeinsamem Preisfaktor, Rangfolge A vor B vor C, Szenario auch auf
- `test_steuerung_v116_cockpit.py` – 1.16 – Cockpit (neu): Karten an/ab, Monat schieben, Bewertung (Budget, Möbel, Reserve, Umzüge), Übernehmen.
- `test_steuerung_v117_stand.py` – 1.17 – Stand in einer Zeile: aus Entscheidung, Umsetzung und Finanzen abgeleitet (nichts wird anders gespeichert).
- `test_steuerung_v118_vorschau.py` – 1.18 – Cockpit: Vorschau beim Überfahren (Kacheln und Diagramm), ohne die Seite neu aufzubauen.
- `test_steuerung_v119_wenn_dann.py` – 1.19 – Wenn-dann im Cockpit: angenommener Wert in einem Monat, Abweichung klingt mit gemessener Beharrung ab.

## teilnehmer – Teilnehmer-/Maßnahmen-Prognose (Pivot, Neuanmeldungen, Simulation)

- `test_teilnehmer_v050_pivot.py` – 0.50: Maßnahmen-Prognose – Pivot einlesen (nur Zählwerte), Lücke überbrücken, Gruppen, erwartete Kurse, Rückwärts-
- `test_teilnehmer_v053_vergleich.py` – 0.53: Zimmer hinzufügen und entfernen; Maßnahmen-Vergleich je Maßnahme. Erfundene Daten.
- `test_teilnehmer_v055_verbleib.py` – 0.55: Maßnahmen-Prognose ehrlicher – Verbleibskurve, Nachbuchung (Buchungsloch), Kurzkurs-Sockel, Rückwärtstest
- `test_teilnehmer_v056_halbjahr.py` – 0.56: Neuanmeldungen je Halbjahr (alle Teilnehmenden), Verfahren per Rückwärtstest, Kleinst-/eingestellte Maßnahmen
- `test_teilnehmer_v057_spanne.py` – 0.57: 80-%- und 95-%-Spanne der Neuanmeldungen (aus dem Rückwärtstest). Nur erfundene Zahlen.
- `test_teilnehmer_v058_welle.py` – 0.58: Rückwärtstest je Welle mit damaliger Spanne (Treffer im 80-/95-%-Band), UWT ausgeblendet. Erfundene Zahlen.
- `test_teilnehmer_v063_spannen.py` – 0.63: realistische Spannen (Wurzel-Einheiten), Obergrenze je Maßnahme, Holt-Winters und Anteil am Gesamttrend.
- `test_teilnehmer_v076_bestand.py` – 0.76 – Bestandsmodell Schritt 1: Aufenthalte je Person (nur Nummern), Kursnamen lesen, Zuordnungstabelle,
- `test_teilnehmer_v077_solldauer.py` – 0.77 – Solldauer aus der Zimmerbelegung je Kursfamilie, Gruppe „Ignoriert“, Obergrenze nur VW.
- `test_teilnehmer_v079_simulation.py` – 0.79 – Bestandsprognose: Kaplan-Meier, Übergänge, Simulation (wiederholbar), Kappe VW, Szenarien, Wenn-dann,
- `test_teilnehmer_v094_kbm.py` – 0.94 – Teilnehmer-Prognose: keine Kursfamilie verschwindet (KBM), Treffsicherheit je Maßnahme, Lücke statt 0,
- `test_teilnehmer_v105_monat_austausch.py` – 1.05 – Neuanmeldungen je Monat; Austauschdatei zwischen altem und neuem Programm. Nur erfundene Daten.
- `test_teilnehmer_v106_zugaenge.py` – 1.06 – Zu- und Abgänge in der Teilnehmer-Prognose, veraltete Maßnahmen entfernen, Kurznamen. Erfundene Daten.
- `test_teilnehmer_v108_auswahl.py` – 1.08 – Maßnahmen-Auswahl wird übernommen (asynchrones setzen), eigene Skala als Standard.
- `test_teilnehmer_v120_startwelle.py` – 1.20 – Teilnehmer-Prognose: Zugänge in Hauptmaßnahmen kommen zum Starttermin (Januar/Juli), nicht verteilt übers Jahr;
- `test_teilnehmer_v124_rvl_rvt.py` – 1.24 – RVL und RVT getrennt; künftige Zahlen zeigen „angemeldet + erwartet = gesamt“. Erfundene Kurse.
- `test_teilnehmer_v125_rechenweg.py` – 1.25 – Rechenweg der Teilnehmer-Prognose: alle Zutaten der Simulation mit den gemessenen Werten. Erfundene Fälle.

## zimmer – Zimmer: Karte, Zustände, Filter, Druck, Suche, Historie

- `test_zimmer_v007_karten_personen.py` – 0.7: Kartenansicht, Filter, Person direkt ins Zimmer, „neu“-Erkennung, Erinnerung, Wochenblatt – erfundene Namen.
- `test_zimmer_v018_druck.py` – 0.18: Zimmer drucken / als Excel je Filter – mit „frei ab“, „frei bis“ und freien Tagen (erfundene Namen).
- `test_zimmer_v029_historie.py` – 0.29: Zimmerhistorie, kontrastreichere Zimmerfarben, flexible Mietverträge – erfundene Daten.
- `test_zimmer_v070_zustaende.py` – 0.70: Zimmerzustände – vier Zustände (frei, geplant, belegt, nicht nutzbar), die sich ausschließen und zusammen
- `test_zimmer_v097_suche_kontrast.py` – 0.97 – Suche zeigt nach Umzug das Zimmer heute, Diagrammschrift mit hohem Kontrast, deutlich verschiedene
- `test_zimmer_v111_filter.py` – 1.11 – Zimmerfilter in der Übersicht (Einzel-/Doppelzimmer, Tier …), Einzelzimmer als neuer Filter.
- `test_zimmer_v123_suche_umzug.py` – 1.23 – Suche nach Zimmerwechsel: nur das neue Zimmer (altes als Hinweis). Erfundene Namen.
- `test_zimmer_v142_kontrast_protokoll.py` – 1.42 – Zimmerkacheln mit hohem Kontrast und Legende, Protokoll „Heute geändert“ im Cockpit

## zuteilung – Zuteilung bei Anreisen: Regeln, Zimmerwahl, strittige Planung, Doppelzimmer

- `test_zuteilung_kern.py` – Neue Oberfläche: Zeilen, Filter, 1-Klick-Lösungen und Rückgängig – nur erfundene Namen.
- `test_zuteilung_v020_import_ziehen.py` – 0.20: Ordner-Import beim Start, Klassenstärken, Ziehen im Zeitstrahl, Kalender-Klick – erfundene Daten.
- `test_zuteilung_v027_gruppen.py` – 0.27: Gruppen beim Anlegen und in den Personenangaben (ohne Feld „Maßnahme“) – erfundene Namen.
- `test_zuteilung_v031_zimmer_pruefen.py` – 0.31: Bestimmtes Zimmer prüfen – warum es nicht wählbar ist, und von Hand zuweisen, wenn es geht. Erfundene Namen.
- `test_zuteilung_v032_strittig.py` – 0.32: Eigene Planung widerspricht dem Gebäudeplan – nie wieder still „frei“. Erfundene Namen.
- `test_zuteilung_v033_auszug.py` – 0.33: Abbruch / vorzeitiger Auszug in der Zimmerkarte – das Zimmer wird wirklich frei. Erfundene Namen.
- `test_zuteilung_v040_haus6_bad.py` – 0.40: Haus 6 – Bad über den Flur (x01, x02, x08, x09), schaltbare Aufteilung je Etage. Erfundene Daten.
- `test_zuteilung_v059_mieter_regel.py` – 0.59: Mieter sind von der Männer-Regel (Haus 6, Bad über den Flur) ausgenommen. Erfundene Daten.
- `test_zuteilung_v061_sperre.py` – 0.61: Sperre früher beenden, Zimmer trotzdem nehmen, Jahr der Vertragsnummer, Nummer nachträglich ändern.
- `test_zuteilung_v064_zimmer_2_517.py` – 0.64: Zimmer 2-517 fest im Programm; Heute entschlackt. Erfundene Daten.
- `test_zuteilung_v121_dz_einzeln.py` – 1.21 – Doppelzimmer einzeln vergeben (je Anreise per Knopfdruck), wenn die DZ-Liste nicht stimmt. Erfundene Daten.
- `test_zuteilung_v129_geschlecht.py` – 1.29 – Geschlecht einer Belegung an EINER Stelle lesen (Feld „grund“ des Hauptprogramms). Erfundene Namen.
- `test_zuteilung_v136_allergie_wohnt.py` – 1.36 – Allergiker: Zimmer laut Gebäudeplan zählt, „Passt so“ für alle
