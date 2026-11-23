# QR-Meldungen über Power Automate – Anleitung (Stand 1.46)

**Warum:** Die Forms-Excel-Datei auf dem PC wird nur aktualisiert, wenn OneDrive sie synchronisiert, und das passiert
oft nicht. Darum schickt Power Automate jetzt **je Antwort eine Mail mit festem Aufbau**. Eine Outlook-Regel legt
diese Mails in einen eigenen Ordner. INNternat liest **nur diesen Ordner** alle 5 Minuten. Es verschiebt, löscht oder
markiert dabei nichts. Ihr Posteingang bleibt dadurch sauber.

Dauer: etwa 15 Minuten. Sie brauchen das Formular mit den Fragen „Zimmer“, „Code (bitte nicht ändern)“,
„Art des Problems“ und „Beschreibung“.

**Voraussetzung:** auf dem PC, der einliest, das **klassische Outlook** (nicht „Neues Outlook“ – dort fehlt die
Schnittstelle). In INNternat öffnen Sie alles Nötige unter **Verwaltung → Automatisierung** (gleiches Fenster wie
**Zimmer & Haus → QR-Meldungen → „Einrichten & Etiketten“**).

## Teil 0 – Formular-Link in INNternat (falls noch nicht geschehen)
1. In Forms: Formular öffnen → **„…“ → „Vorausgefüllte URL abrufen“**. Bei „Zimmer“ `ZIMMER` und bei „Code (bitte
   nicht ändern)“ `CODE` eintragen → **„Vorausgefüllten Link abrufen“** → **Kopieren**.
2. In INNternat **Verwaltung → Automatisierung** öffnen, unter **„1 · Formular-Link“** einfügen und speichern. Danach
   lassen sich dort die Etiketten mit QR-Code je Zimmer drucken.

---

## Teil 1 – Flow anlegen (einmalig)

1. Öffnen Sie **make.powerautomate.com** und melden Sie sich mit Ihrem Dienstkonto an.
2. Klicken Sie links auf **„+ Erstellen“** und dann auf **„Automatisierter Cloud-Flow“**.
3. Füllen Sie die Felder aus:
   - **Flowname:** `INNternat QR-Meldung`
   - **Trigger:** suchen Sie „Forms“ und wählen Sie **„Wenn eine neue Antwort übermittelt wird“** (Microsoft Forms).
   - Klicken Sie auf **„Erstellen“**.
4. Wählen Sie im Trigger bei **„Formular-ID“** Ihr Mängel-Formular aus der Liste.

### Schritt 2 – Antwort holen
5. Klicken Sie auf **„+ Neuer Schritt“** und suchen Sie „Forms“. Wählen Sie **„Antwortdetails abrufen“**.
6. Füllen Sie die Felder aus:
   - **Formular-ID:** dasselbe Formular wie im Trigger.
   - **Antwort-ID:** Klicken Sie ins Feld, dann im Blitz-Menü (dynamische Inhalte) auf **„Antwort-ID“**.
   - Falls Power Automate dabei selbst ein „Auf alle anwenden“ um den Schritt legt: Das ist in Ordnung, alles Weitere
     kommt dann innerhalb dieses Rahmens.

### Schritt 3 – Mail schicken
7. Klicken Sie auf **„+ Neuer Schritt“** und suchen Sie „Outlook“. Wählen Sie **„E-Mail senden (V2)“**
   (Office 365 Outlook).
8. **An:** die Adresse des Postfachs, in dem INNternat lesen soll. Meist ist das Ihre eigene Adresse oder die des
   Internatsdienstes.
9. **Betreff:** Tippen Sie `INNternat-QR | `. Fügen Sie dann aus dem Blitz-Menü die Antwort auf **„Zimmer“** ein,
   tippen Sie ` | ` und fügen Sie die Antwort auf **„Code (bitte nicht ändern)“** ein.
   Ergebnis: `INNternat-QR | [Zimmer] | [Code (bitte nicht ändern)]`
10. **Text:** Schreiben Sie genau diese Zeilen, jede in eine eigene Zeile. Die Teile in eckigen Klammern sind
    dynamische Inhalte aus dem Blitz-Menü:

```
INNTERNAT-QR
ID: [Antwort-ID]
Zeit: [Übermittlungszeit]
Zimmer: [Zimmer]
Code: [Code (bitte nicht ändern)]
Art: [Art des Problems]
Beschreibung: [Beschreibung]
ENDE
```

    - Die Wörter vor dem Doppelpunkt müssen genau so heißen. Groß- und Kleinschreibung ist egal.
    - Heißen Ihre Fragen etwas anders, nehmen Sie trotzdem die passenden Antworten. Nur die linken Wörter bleiben
      fest.
    - Hat das Formular keine Frage „Art des Problems“, lassen Sie die Zeile `Art:` leer stehen.
11. Klicken Sie oben rechts auf **„Speichern“**.

### Schritt 3 ohne Office-365-Outlook-Verbindung (Variante B)
Wenn Power Automate für „E-Mail senden (V2)“ eine **Office 365 Outlook-Verbindung** verlangt, die es bei Ihnen nicht
gibt, nehmen Sie stattdessen den Baustein **„Mail“** von Microsoft. Er braucht **keine Anmeldung und kein Postfach** –
die Mail kommt vom Absender *Microsoft Power Automate* (flow-noreply@microsoft.com).

7b. Klicken Sie auf **„+ Neuer Schritt“** und suchen Sie **„E-Mail-Benachrichtigung“** (englisch: „Send an email
    notification“). Wählen Sie **„E-Mail-Benachrichtigung senden (V3)“** mit dem Symbol **„Mail“** (blauer Umschlag) –
    **nicht** „Office 365 Outlook“.
8b. **An**, **Betreff** und **Text** füllen Sie genau wie oben in 8–10 (Betreff `INNternat-QR | …`, Text mit den
    Zeilen `INNTERNAT-QR` … `ENDE`). Jede Zeile mit Enter beenden.
9b. Speichern, testen wie in Teil 2. In der Outlook-Regel (Teil 3) bleibt die Bedingung **Betreff enthält
    „INNternat-QR“** – der Absender spielt keine Rolle.

Gut zu wissen: Diese Benachrichtigungen schickt Microsoft – höchstens etwa 100 am Tag, für QR-Meldungen genug. Landet
die erste im Junk-Ordner: Rechtsklick → **Junk-E-Mail → Absender nie sperren**. Ist auch dieser Baustein gesperrt
(Hinweis „durch Richtlinie zur Verhinderung von Datenverlust blockiert“ oder Fehler **401 „The Mail connector is
currently restricted for new tenants“**), nehmen Sie Variante C.

### Schritt 3 ganz ohne Mail: Datei in OneDrive (Variante C, ab 1.44)
Für Firmenkonten, in denen **weder Office 365 Outlook noch der Mail-Baustein** freigegeben ist. Power Automate legt je
Antwort eine kleine Textdatei in einen OneDrive-Ordner. OneDrive holt sie auf den PC, INNternat liest den Ordner.
**Outlook wird dafür nicht gebraucht, Teil 3 entfällt.**

C1. Einmalig: Öffnen Sie im Explorer Ihren **OneDrive-Ordner** (links „OneDrive – <Firma>“) und legen Sie einen
    neuen Ordner **`INNternat-QR`** an. Rechtsklick auf den Ordner → **„Immer auf diesem Gerät beibehalten“**.
C2. Im Flow: Löschen Sie den Mail-Schritt (die drei Punkte „…“ am Schritt → **„Löschen“**).
C3. **„+ Neuer Schritt“**, suchen Sie **„OneDrive for Business“** und wählen Sie **„Datei erstellen“**. Melden Sie
    sich bei der Nachfrage mit Ihrem Dienstkonto an.
C4. Füllen Sie die Felder aus:
    - **Ordnerpfad:** auf das Ordnersymbol klicken und **`/INNternat-QR`** wählen.
    - **Dateiname:** tippen Sie `qr-`, fügen Sie aus dem Blitz-Menü **„Antwort-ID“** ein und tippen Sie `.txt`.
      Ergebnis: `qr-[Antwort-ID].txt`
    - **Dateiinhalt:** dieselben Zeilen wie oben in Schritt 10 (`ID:` … `ENDE`; die erste Zeile `INNTERNAT-QR`
      darf hier fehlen). Beenden Sie jede
      Zeile mit Enter. Die Teile in eckigen Klammern kommen aus dem Blitz-Menü.
C5. **„Speichern“** und testen wie in Teil 2. Nach ein bis zwei Minuten liegt im Ordner `INNternat-QR` eine Datei
    `qr-….txt`. Mit dem Editor geöffnet sieht man die Zeilen.
C6. In INNternat öffnen Sie **Verwaltung → Automatisierung → „2 · Eingang auf diesem PC“**. Tragen Sie bei
    **„Weg A – QR-Ordner in OneDrive“** den Ordner ein:
    - Ordner im Explorer öffnen, oben in die Adresszeile klicken, kopieren und einfügen
      (z. B. `C:\Users\<Name>\OneDrive - <Firma>\INNternat-QR`).
    - **„QR-Ordner speichern“**, dann **„Jetzt einlesen“**.
    - Die Prüfanzeige zeigt **„QR-Ordner“** grün und **„QR-Dateien“** mit der Zahl der Dateien.

INNternat liest die Dateien nur. Es verschiebt und löscht nichts. Eingelesene Dateien dürfen Sie gefahrlos löschen,
denn INNternat merkt sich die Antwort-ID. Wechseln Sie später doch auf Mail, erscheint keine Meldung doppelt.

## Teil 2 – Testen
12. Scannen Sie ein Probe-Etikett mit dem Handy und schicken Sie eine Testantwort ab.
13. Öffnen Sie in Power Automate **„Meine Flows“ → „INNternat QR-Meldung“ → „Ausführungsverlauf“**. Nach ein bis
    zwei Minuten sollte dort „Erfolgreich“ stehen. Bei „Fehler“: Anklicken zeigt den roten Schritt. Meist ist eine
    Formular-ID oder ein leeres Pflichtfeld schuld.
14. Die Mail sollte jetzt in Outlook ankommen.

## Teil 3 – Outlook-Regel gegen das Durcheinander (einmalig, klassisches Outlook)
15. Klicken Sie in Outlook mit der rechten Maustaste auf **Posteingang**, wählen Sie **„Neuer Ordner“** und nennen
    Sie ihn `QR-Meldungen`.
16. Öffnen Sie **Datei → Regeln und Benachrichtigungen verwalten → Neue Regel → „Regel ohne Vorlage erstellen:
    Regel auf von mir empfangene Nachrichten anwenden“**.
17. Bedingung: **„mit bestimmten Wörtern im Betreff“**, Wort `INNternat-QR`.
18. Aktion: **„diese in den Ordner Zielordner verschieben“** und dann **QR-Meldungen** wählen.
19. Klicken Sie auf **„Fertig stellen“**. Die Testmail aus Teil 2 können Sie mit „Regel jetzt ausführen“ gleich
    verschieben.

## Teil 4 – In INNternat eintragen (auf einem PC mit Outlook)
20. Öffnen Sie **Verwaltung → Automatisierung** (oder **Zimmer & Haus → QR-Meldungen → „Einrichten & Etiketten“**).
21. Tragen Sie unter **„2 · Eingang auf diesem PC“** bei **„Outlook-Ordner für QR-Mails“** den Ordner ein:
    - für das eigene Postfach: `Posteingang/QR-Meldungen`;
    - für ein Gruppenpostfach: `<Name des Postfachs>/Posteingang/QR-Meldungen`, so wie es links in Outlook steht.
22. Klicken Sie auf **„Ordner speichern“** und dann auf **„Jetzt einlesen“**. Die Testmeldung erscheint in der
    Liste, mit dem Zimmer vom Etikett.
23. Oben zeigt die Prüfanzeige **„Outlook-Ordner“** grün und **„QR-Mails“** mit der Zahl der Mails.
24. Eine Meldung wird erst zum Mangel, wenn Sie sie unter **Zimmer & Haus → QR-Meldungen** prüfen und
    **„Übernehmen“** klicken. Danach steht sie unter **Defekte Zimmer** (und im Cockpit unter „Heute geändert“).

## Teil 5 – Meldungen bearbeiten (alle PCs)
- **Zimmer & Haus → QR-Meldungen**: Die Meldungen liegen in den gemeinsamen Daten. Alle Kolleginnen und Kollegen
  sehen sie, auch wenn der Ordner nur auf einem PC eingetragen ist.
- Meldung anklicken → **„Übernehmen & an FM“**: Der Mangel wird angelegt, und die Mail an FM öffnet sich fertig
  ausgefüllt. Klicken Sie **„Senden“** (über Ihr Outlook) oder **„In Outlook öffnen“**. Die FM-Adresse wird beim ersten
  Mal gemerkt.
- **„Erledigte archivieren“** räumt übernommene und verworfene Meldungen in den Filter **„Archiv“**. Von dort holen
  Sie eine Meldung mit **„Zurückholen“** wieder.
- Tipp: Damit auch eingelesen wird, wenn Ihr PC aus ist, können Sie den OneDrive-Ordner für eine Kollegin oder einen
  Kollegen freigeben („Freigeben“ → „Verknüpfung zu Meine Dateien hinzufügen“). Tragen Sie ihn dort ebenfalls ein.
  Doppelte Meldungen entstehen dabei nicht.

## Wenn etwas nicht klappt
| Was Sie sehen | Was zu tun ist |
|---|---|
| Ausführungsverlauf „Fehler“ bei „Antwortdetails abrufen“ | Formular-ID im Schritt prüfen (dasselbe Formular wie im Trigger). |
| Mail kommt nicht an | „An“-Adresse prüfen; Junk-E-Mail-Ordner ansehen. |
| Mail kommt an, INNternat zeigt nichts | Ordnerpfad genau wie links in Outlook schreiben; Outlook muss offen sein; „Jetzt einlesen“. |
| Zimmer falsch oder leer | Etikett neu drucken (Teil 0); im Formular darf „Zimmer“ nicht verändert werden – der Code zeigt es an. |
| Mail-Schritt rot mit 401 „Mail connector is currently restricted“ | Microsoft sperrt den Mail-Baustein für neue Firmenkonten. Nehmen Sie Variante C (OneDrive-Datei). |
| Variante C: Datei nur in OneDrive im Browser, nicht auf dem PC | Prüfen Sie, ob OneDrive auf dem PC angemeldet ist (Wolke in der Taskleiste). Stellen Sie den Ordner auf „Immer auf diesem Gerät beibehalten“. |
| Variante C: Datei liegt im Ordner, INNternat zeigt nichts | Verwaltung → Automatisierung: Steht „Unlesbare Dateien“ in der Prüfanzeige, den Dateiinhalt im Flow prüfen (jede Angabe in eine eigene Zeile, links „ID:“, „Zimmer:“ …). Danach „Jetzt einlesen“. |
| Beim Scannen bleibt „Code“ im Formular leer | Der gespeicherte Formular-Link enthält keinen Platzhalter CODE. Vorausgefüllten Link neu holen (Teil 0), bei der Code-Frage `CODE` eintragen, in INNternat speichern, Etiketten neu drucken. Alte Etiketten haben keinen Code. |
| Variante C: „QR-Ordner nicht gefunden“ | Kopieren Sie den Pfad aus der Explorer-Adresszeile, ohne Anführungszeichen. Er gilt je PC. |
| Meldung doppelt | Nur einen Eingang nutzen (Outlook **oder** Excel), Excel-Pfad leeren. |

**Wichtig:**
- Outlook muss auf diesem PC geöffnet sein. Ist es zu, wartet INNternat und versucht es in 5 Minuten wieder. Outlook
  wird nie selbst gestartet.
- Es reicht **ein** PC mit eingetragenem Ordner. Die anderen PCs sehen die Meldungen über die gemeinsamen Daten.
- Bitte **nur einen Eingang** nutzen: OneDrive-Ordner, Outlook oder die Excel-Datei. Sonst kann dieselbe Antwort zweimal
  erscheinen. Den Excel-Pfad leeren und speichern genügt.
- Die QR-Mails können Sie gefahrlos löschen, sobald sie eingelesen sind. INNternat merkt sich die Antwort-ID.
