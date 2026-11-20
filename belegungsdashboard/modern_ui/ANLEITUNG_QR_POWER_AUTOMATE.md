# QR-Meldungen über Power Automate – Anleitung (ab 1.32)

**Warum:** Die Forms-Excel-Datei auf dem PC wird nur aktualisiert, wenn OneDrive sie synchronisiert, und das passiert
oft nicht. Darum schickt Power Automate jetzt **je Antwort eine Mail mit festem Aufbau**. Eine Outlook-Regel legt
diese Mails in einen eigenen Ordner. INNternat liest **nur diesen Ordner** alle 5 Minuten. Es verschiebt, löscht oder
markiert dabei nichts. Ihr Posteingang bleibt dadurch sauber.

Dauer: etwa 15 Minuten. Sie brauchen das Formular mit den Fragen „Zimmer“, „Code (bitte nicht ändern)“,
„Art des Problems“ und „Beschreibung“.

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
20. Öffnen Sie **Zimmer & Haus → Defekte Zimmer → QR-Meldungen** und klicken Sie auf **„Einrichten & Etiketten“**.
21. Tragen Sie unter **„2 · Eingang auf diesem PC“** bei **„Outlook-Ordner für QR-Mails“** den Ordner ein:
    - für das eigene Postfach: `Posteingang/QR-Meldungen`;
    - für ein Gruppenpostfach: `<Name des Postfachs>/Posteingang/QR-Meldungen`, so wie es links in Outlook steht.
22. Klicken Sie auf **„Ordner speichern“** und dann auf **„Jetzt einlesen“**. Die Testmeldung erscheint in der
    Liste, mit dem Zimmer vom Etikett.
23. Oben zeigt die Prüfanzeige **„Outlook-Ordner“** grün und **„QR-Mails“** mit der Zahl der Mails.

**Wichtig:**
- Outlook muss auf diesem PC geöffnet sein. Ist es zu, wartet INNternat und versucht es in 5 Minuten wieder. Outlook
  wird nie selbst gestartet.
- Es reicht **ein** PC mit eingetragenem Ordner. Die anderen PCs sehen die Meldungen über die gemeinsamen Daten.
- Bitte **nur einen Eingang** nutzen: entweder Outlook oder die Excel-Datei. Sonst kann dieselbe Antwort zweimal
  erscheinen. Den Excel-Pfad leeren und speichern genügt.
- Die QR-Mails können Sie gefahrlos löschen, sobald sie eingelesen sind. INNternat merkt sich die Antwort-ID.
