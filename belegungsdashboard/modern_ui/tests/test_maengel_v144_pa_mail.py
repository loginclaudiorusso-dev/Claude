"""1.44 – Mail aus „E-Mail-Benachrichtigung senden (V3)“: HTML-Absätze, Auswahl als Liste, US-Zeit in UTC.
Werte erfunden (nachgebaut nach dem Aufbau einer Testmail)."""

import os
import time

from modern import qr_meldungen_kern as q

TEXT = ('<p class="editor-paragraph"><br>ID: 3<br>Zeit: 11/23/2026 1:41:54 PM<br>Zimmer: 2-101<br>Code: AB2CD<br>'
        'Art: ["Heizung"]<br>Beschreibung: Laut</p><p class="editor-paragraph">ENDE</p><p>Fußzeile von Power Automate</p>')


def test_benachrichtigung_v3_wird_gelesen(monkeypatch):
    monkeypatch.setenv("TZ", "Europe/Berlin")
    time.tzset() if hasattr(time, "tzset") else None
    r = q.mail_parsen("INNternat-QR", TEXT)
    assert (r.id, r.zimmer_text, r.code, r.art_text, r.text) == ("pa|3", "2-101", "AB2CD", "Heizung", "Laut")
    assert r.zeit == "2026-11-23T14:41"                    # 13:41 UTC = 14:41 in Deutschland (Winterzeit)
    os.environ.pop("TZ", None)
    time.tzset() if hasattr(time, "tzset") else None


def test_mehrfachauswahl_und_klartext():
    assert q._auswahl('["Heizung","Fenster"]') == "Heizung, Fenster"
    assert q._auswahl("Heizung") == "Heizung" and q._auswahl("") == ""
