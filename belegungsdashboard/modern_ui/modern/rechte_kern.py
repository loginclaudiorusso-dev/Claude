"""1.75: Rechte je Benutzer – der Administrator legt per Häkchen fest, was jemand tun darf. Rein, ohne NiceGUI.

* **Katalog** (``RECHTE``): Was man im Programm ändern (oder bei „sehen“-Rechten öffnen) kann, in Gruppen.
* **Vorlagen** (``VORLAGEN``): Mitarbeiter/in (alles außer Verwaltung – wie bis 1.74), Leitung, Empfang/Pforte,
  Haustechnik, Nur lesen. Eine Vorlage belegt nur die Häkchen vor, danach lässt sich jedes Häkchen einzeln ändern.
* **Gespeichert** im Konto (``rechte``). Fehlt es (Konten bis 1.74), gilt die Vorlage „Mitarbeiter/in“ – also genau wie
  bisher. Administratoren dürfen immer alles. Ohne eingerichtete Konten ist alles erlaubt (wie bisher).
* **Wirkung:** beim Speichern (``pruefen`` – jede Änderung über ``Ansicht.aendern`` wird über ``recht_fuer`` einem Recht
  zugeordnet) und beim Öffnen von Seiten mit „sehen“-Recht (``seite_erlaubt``; Menüband blendet sie aus).
* Die Rechte schützen das Programm, nicht die Dateien im Netzwerkordner – das tut die Ordnerfreigabe.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Recht:
    key: str
    text: str
    gruppe: str
    hilfe: str = ""


RECHTE: list[Recht] = [
    Recht("zuteilen", "Zimmer zuteilen, umziehen, Belegung ändern", "Belegung",
          "Zuteilen, Zimmerwechsel, Umzüge, Vorschläge übernehmen, gleiche Person verbinden"),
    Recht("anreisen", "Anreisen und Abreisen bearbeiten", "Belegung",
          "Personen anlegen/ändern, Nichtanreise, Gruppen, UWT zuteilen, Erinnerungen"),
    Recht("blocken", "Zimmer für Gruppen blockieren", "Belegung", "Kontingente ohne Namen anlegen und auflösen"),
    Recht("haus", "Aktuell im Haus: Abwesenheiten und Schlüssel", "Belegung",
          "Abwesenheiten (auch für ganze Kurse), Schlüssel ausgeben und zurücknehmen"),
    Recht("mieter", "Mietverträge anlegen, ändern, kündigen", "Mieter",
          "Neuer Vertrag, Verlängern, Ändern, Unterlagen, Kündigung, Checkliste"),
    Recht("mieter_akte", "Mieter-Akte öffnen und Dateien ablegen", "Mieter", "Unterlagen je Mietvertrag"),
    Recht("reinigung", "Reinigung abhaken und planen", "Haus & Technik", "Reinigungsliste, einzelne Reinigungen"),
    Recht("maengel", "Mängel, defekte Zimmer, FM-Aufträge, QR-Meldungen", "Haus & Technik",
          "Mangel setzen/beheben, FM-Mail, QR-Meldungen übernehmen, Aushänge"),
    Recht("inventar", "Inventar und Gästezimmer pflegen", "Haus & Technik", "Gegenstände, Gästezimmer, Termine"),
    Recht("nachrichten", "Nachrichten und Mails schreiben", "Kommunikation", "Standort-Nachrichten, Mails übernehmen"),
    Recht("auswertung", "Auswertung und Prognose sehen", "Steuerung", "Belegungs- und Teilnehmer-Prognose, Auswertung"),
    Recht("planung", "Maßnahmen, Renovierung, Szenarien ändern", "Steuerung",
          "Maßnahmen-Prognose, Renovierung & Budget, Vorhaben, Szenarien, Kennzahlen"),
    Recht("daten", "Daten einlesen und abgleichen", "Verwaltung",
          "Pivot, Klassenstärken, UWT, Anreiselisten übernehmen, Austauschdatei"),
    Recht("einstellungen", "Einstellungen ändern", "Verwaltung",
          "Zahlen, Grenzen, Termine, Feiertage, Ampel – heikle Stammdaten bleiben beim Administrator"),
]
KEYS = [r.key for r in RECHTE]
NAMEN = {r.key: r.text for r in RECHTE}

VORLAGEN: dict[str, tuple[str, list[str]]] = {
    "mitarbeiter": ("Mitarbeiter/in (alles außer Verwaltung)", [k for k in KEYS]),
    "leitung": ("Leitung (sehen und planen, keine Tagesarbeit)", ["auswertung", "planung", "mieter_akte", "nachrichten",
                                                                  "blocken"]),
    "empfang": ("Empfang / Pforte (Tagesbetrieb)", ["anreisen", "haus", "reinigung", "maengel", "nachrichten"]),
    "haustechnik": ("Haustechnik (Reinigung, Mängel, Inventar)", ["reinigung", "maengel", "inventar"]),
    "lesen": ("Nur lesen", []),
}
STANDARD = "mitarbeiter"

# Welche Änderung braucht welches Recht – nach Modul der Aktion (ohne Eintrag: keine Prüfung)
MODUL_RECHT = {
    "kern": "zuteilen", "zimmer_kern": "zuteilen", "gleiche_person": "zuteilen", "mietbindung": "zuteilen",
    "gleiche_person_ui": "zuteilen", "dz_einzeln_kern": "zuteilen", "cockpit_kern": "zuteilen",
    "anreisen_kern": "anreisen", "abreise_kern": "anreisen", "seite_assistenz": "anreisen",
    "kontingent_kern": "blocken",
    "haus_kern": "haus", "haus_ui": "haus", "schluessel_kern": "haus", "kurs_abwesenheit": "haus",
    "mieter_kern": "mieter", "mieter_checkliste": "mieter", "kuendigung_kern": "mieter", "mieter_akte": "mieter_akte",
    "qr_meldungen_kern": "maengel", "hausordnung_kern": "maengel",
    "seite_inventar": "inventar", "gaeste_kern": "inventar", "seite_termine": "inventar",
    "nachrichten_kern": "nachrichten",
    "massnahmen_kern": "planung", "renovierung_kern": "planung", "vorhaben_kern": "planung", "bestand_kern": "planung",
    "bestand_prognose": "planung", "steuerung_kern": "planung", "zimmer_zusatz_kern": "planung",
    "daten_kern": "daten", "austausch_dienst": "daten", "seite_daten": "daten",
    "seite_einstellungen": "einstellungen", "feiertage_kern": "einstellungen", "regeln_kern": "einstellungen",
}
NAME_RECHT = (("reinigung", "reinigung"), ("renovierung", "planung"), ("mangel", "maengel"), ("fm_", "maengel"), ("facility", "maengel"),
              ("mieter_mail", "mieter"), ("einstellung_setzen", "einstellungen"))

# Seiten, die man nur mit einem „sehen“-Recht öffnet: (Seite, Ansicht oder None für alle) → Recht
SEITEN_RECHT = {("auswertung", None): "auswertung", ("steuerung", None): "auswertung"}


def vorlage(name: str) -> list[str]:
    return list(VORLAGEN.get(name, VORLAGEN[STANDARD])[1])


def bereinigt(rechte) -> list[str]:
    s = set(rechte or [])
    return [k for k in KEYS if k in s]


def von_konto(k) -> set[str]:
    """Rechte eines Kontos (Administrator: alle; ohne gespeicherte Rechte: Vorlage „Mitarbeiter/in“)."""
    if k is None or getattr(k, "admin", False):
        return set(KEYS)
    r = getattr(k, "rechte", None)
    return set(vorlage(STANDARD) if r is None else bereinigt(r))


def passende_vorlage(rechte) -> str:
    s = set(bereinigt(rechte))
    return next((n for n, (_t, ks) in VORLAGEN.items() if set(ks) == s), "")


def _aktuell():
    """Angemeldetes Konto – ohne Konten ist niemand angemeldet (dann alles erlaubt). Liest keine Datei (schnell)."""
    from . import benutzer_kern as bk

    return bk.aktuell()


def darf(recht: str | None, konto=None) -> bool:
    if not recht:
        return True
    k = konto if konto is not None else _aktuell()
    if k is None:
        return True                    # ohne Konten (oder noch nicht angemeldet) wie bisher
    return recht in von_konto(k)


def pruefen(recht: str | None, konto=None) -> None:
    if not darf(recht, konto):
        raise ValueError(f"Dafür fehlt Ihnen das Recht „{NAMEN.get(recht, recht)}“ – bitte den Administrator fragen.")


def recht_fuer(aktion) -> str | None:
    """Welches Recht braucht diese Änderung? (Attribut ``recht`` an der Funktion › Name › Modul.)"""
    r = getattr(aktion, "recht", None)
    if r:
        return r
    f = getattr(aktion, "func", aktion)                 # functools.partial
    name = getattr(f, "__name__", "") or ""
    for teil, recht in NAME_RECHT:
        if teil in name:
            return recht
    modul = (getattr(f, "__module__", "") or "").rsplit(".", 1)[-1]
    return MODUL_RECHT.get(modul)


def seite_erlaubt(seite: str, ansicht: str | None = None, konto=None) -> bool:
    r = SEITEN_RECHT.get((seite, ansicht)) or SEITEN_RECHT.get((seite, None))
    return darf(r, konto)
