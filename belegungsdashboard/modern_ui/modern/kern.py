"""Brücke zwischen der neuen Oberfläche und der bestehenden Logik in ``belegung`` – ohne NiceGUI, damit testbar.

Gelesen und geschrieben wird ausschließlich über die Funktionen des Hauptprogramms (``zimmerplan``, ``vorgaenge``,
``reinigungsliste``, ``termine``, ``aenderungen``). Jede Änderung ist ein Schritt mit Schnappschuss, den
``rueckgaengig`` zurücknimmt – wie Strg+Z im Hauptprogramm.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import logging
import re
from datetime import date, timedelta
from typing import Callable

from belegung import aenderungen, speicher
from belegung import reinigungsliste as rl
from belegung import termine as tm
from belegung import zimmerplan as zp

WT = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]
FILTER = {"alle": "Alle", "handeln": "Handlungsbedarf", "maengel": "Mängel", "ohne": "Ohne Zimmer"}
ZUSTAND = "modern_ui.json"           # eigene Ablage der neuen Oberfläche (z. B. „Später“), getrennt von den alten Dateien


def kurz(zid: str) -> str:
    return zid.removeprefix("GS-")


# ---------------------------------------------------------------------------------------
# Anreisen und Tabellenzeilen
# ---------------------------------------------------------------------------------------

@dataclass
class Anreise:
    kennung: str          # ISO-Datum
    tag: date
    titel: str
    personen: int
    zugeteilt: int

    @property
    def text(self) -> str:
        stand = "zugeteilt" if self.zugeteilt == self.personen else f"{self.zugeteilt}/{self.personen} zugeteilt"
        return f"{WT[self.tag.weekday()]} {self.tag:%d.%m.%Y} · {self.titel} · {stand}"


def anreisen(stand: zp.Planstand, heute: date, vergangene: bool = False) -> list[Anreise]:
    ab = heute - timedelta(days=365 if vergangene else 3)
    return [Anreise(k, tag, titel, len(bs), sum(1 for b in bs if stand.zugewiesen(b.schluessel)))
            for k, tag, titel, bs in stand.anreisen(ab)]


def erste_offene(liste: list[Anreise]) -> str | None:
    """Wie im Hauptprogramm: die nächste Anreise, die noch nicht vollständig zugeteilt ist."""
    offen = [a.kennung for a in liste if a.zugeteilt < a.personen]
    return (offen or [a.kennung for a in liste] or [None])[0]


@dataclass
class Option:
    zimmer: str           # Zimmer-ID
    text: str
    art: str = "frei"     # frei | vorschlag | aktuell | ausnahme


# Spalte „Gruppe“: kurz und in den Begriffen des Internatsdienstes
GRUPPE_KURZ = {"Reha": "Haupt", "RVT": "Vorb.", "RVL": "Vorb.", "ASS": "ASS", "EMR": "EMR", "UWT": "UWT", "Gast": "Gast",
               "Mieter": "Mieter"}


@dataclass
class Zeile:
    schluessel: str
    name: str
    zweite: str
    gruppe: str
    von: date
    bis: date
    gespeichert: str | None           # Zimmer-ID, die schon gespeichert ist
    status: str                       # ok | handeln | maengel | ohne
    stufe: str                        # ok | warn | krit  (Ampelpunkt)
    grund: str = ""
    vorschlag: str | None = None      # grüne Ausweich-/Vorschlags-Option (Zimmer-ID)
    optionen: list[Option] = field(default_factory=list)
    maengel: str = ""
    hinweise: list = field(default_factory=list)   # erkannte Hinweise aus der Bemerkung (hinweise_kern.Hinweis)
    bemerkung: str = ""

    @property
    def zeitraum(self) -> str:
        return f"{self.von:%d.%m.}–{self.bis:%d.%m.%y}"

    def filter(self, f: str, neu: dict | None = None) -> bool:
        if f == "alle":
            return True
        if f == "neu":
            return self.schluessel in (neu or {})
        if f == "maengel":
            return bool(self.maengel)
        return self.status == f


def _maengel_text() -> dict[str, str]:
    from belegung import maengel as mg

    try:
        return {zid: ", ".join(sorted({mg.NAMEN.get(m.art, m.art) for m in ms})) for zid, ms in mg.offen_je_zimmer().items()}
    except Exception:                      # noqa: BLE001 – ohne Mängelliste geht die Tabelle trotzdem
        return {}


def _bezeichnung(z: zp.Zimmer) -> str:
    return z.kurz + (" · DZ" if z.betten > 1 else "")


def zeilen(stand: zp.Planstand, kennung: str | None, heute: date | None = None) -> list[Zeile]:
    """Alle Personen einer Anreise mit gespeichertem Zimmer, Status und Vorschlag (Logik des Hauptprogramms)."""
    if not kennung:
        return []
    heute = heute or date.today()
    bedarf = sorted((b for b in stand.bedarf if b.von.isoformat() == kennung), key=lambda b: (b.anreise_kennung, b.name))
    if not bedarf:
        return []
    fest = {b.schluessel: z["zimmer"] for b in bedarf if (z := stand.zugewiesen(b.schluessel))}
    konflikte = {k.person: k.grund for k in zp.konflikte(stand.lage, heute)}
    maengel = _maengel_text()
    from . import hinweise_kern as hk

    zuteilungen = list(zp.vorschlagen(stand.lage, bedarf, fest))
    reserviert = strittige(stand)
    from belegung import maengel as mg

    fuer_allergiker_nicht = hk.meiden(mg.offen_je_zimmer())
    vergeben = set(fest.values()) | {zt.zimmer.id for zt in zuteilungen if zt.zimmer}
    erg = []
    for zt in zuteilungen:
        b = zt.bedarf
        gespeichert = fest.get(b.schluessel)
        neu = zt.zimmer.id if zt.zimmer else None
        hinweise = [h for h in hk.erkennen(b.bemerkung) if not (h.art == "vortag" and b.gruppe == "EMR")]  # EMR: Vortag ist Standard
        allergie = any(h.art == "allergie" for h in hinweise)
        if allergie and not gespeichert and (alt := hk.allergie_vorschlag(zt, vergeben, fuer_allergiker_nicht, stand.lage)) is not None:
            vergeben.discard(neu)
            vergeben.add(alt.id)
            neu = alt.id                      # Allergiker: freies, zulässiges Zimmer auf der Allergiker-Etage bevorzugen
        vorschlag, grund = None, ""
        hart = (konflikte.get(b.schluessel) or (f"unbewohnbar: {stand.lage.unbewohnbar[gespeichert]}"
                                                 if gespeichert in stand.lage.unbewohnbar else "")) if gespeichert else ""
        if gespeichert and (hart or neu != gespeichert):
            status, stufe = "handeln", "krit"
            grund = hart or "Zimmer passt nicht mehr"
            vorschlag = neu if neu and neu != gespeichert else next(
                (z.id for z in zt.alternativen if z.id != gespeichert and z.id not in stand.lage.unbewohnbar), None)
        elif not gespeichert:
            status, stufe = "ohne", "krit"
            vorschlag = neu
            grund = "noch kein Zimmer" + (f" – {zt.grund}" if neu is None and zt.grund else "")
        elif warnungen := [w for w in zt.warnungen if not (allergie and hk.auf_allergie_etage(zt.zimmer)
                                                          and hk._etagenregel(w.removeprefix("Regel verletzt: "), zt.zimmer))]:
            status, stufe, grund = "handeln", "warn", "; ".join(warnungen)    # Allergiker: Etagen-Regeln gelten nicht
        else:
            status, stufe = "ok", "ok"
        zimmer_jetzt = gespeichert or vorschlag
        if allergie and zimmer_jetzt in fuer_allergiker_nicht:
            if gespeichert and not vorschlag and (alt := hk.allergie_vorschlag(zt, vergeben, fuer_allergiker_nicht, stand.lage)) is not None:
                vorschlag = alt.id
                vergeben.add(alt.id)
            text = "Allergiker – im Zimmer ist Schimmel, Ungeziefer, Geruch oder Schmutz gemeldet"
            grund = f"{grund}; {text}" if grund else text
            if status == "ok":
                status, stufe = "handeln", "krit"
        elif allergie and zimmer_jetzt and not hk.auf_allergie_etage(stand.lage.zimmer.get(zimmer_jetzt)):
            frei = any(hk.auf_allergie_etage(z) for z in zt.alternativen)
            if gespeichert and not vorschlag and (alt := hk.allergie_vorschlag(zt, vergeben, fuer_allergiker_nicht, stand.lage)) is not None:
                vorschlag = alt.id
                vergeben.add(alt.id)
            text = f"Allergiker – nicht auf der {hk.ALLERGIE_TEXT}" + ("" if frei else ", dort ist für diese Person kein Zimmer frei bzw. zulässig")
            grund = f"{grund}; {text}" if grund else text
            if status == "ok":
                status, stufe = "handeln", "warn"
        m = maengel.get(zimmer_jetzt or "", "")
        if status == "ok" and m:
            status, stufe = "maengel", "warn"
        opts: list[Option] = []
        gesehen: set[str] = set()

        def dazu(zid: str, art: str, text: str | None = None) -> None:
            if zid in gesehen or zid not in stand.lage.zimmer:
                return
            gesehen.add(zid)
            z = stand.lage.zimmer[zid]
            zusatz = {"vorschlag": " · passt", "aktuell": (" · " + grund) if status == "handeln" and stufe == "krit" else ""}
            opts.append(Option(zid, text or (_bezeichnung(z) + zusatz.get(art, "")), art))

        if vorschlag:
            dazu(vorschlag, "vorschlag")
        if gespeichert:
            dazu(gespeichert, "aktuell")
        for z in zt.alternativen:
            dazu(z.id, "frei")
        if allergie:
            for z in hk.allergie_zimmer(stand.lage, b, set(), fuer_allergiker_nicht)[:8]:
                dazu(z.id, "frei", f"{_bezeichnung(z)} · Allergiker-Etage")
        for z in zt.ausnahmen:
            dazu(z.id, "ausnahme", f"{_bezeichnung(z)} · {zp.ausnahme_grund(stand.lage, z, b)}")
        if reserviert:
            opts = [o for o in opts if not any(r.geplant == o.zimmer and r.person != b.schluessel and r.von <= b.bis
                                               and b.von <= r.bis for r in reserviert)]
            if vorschlag and vorschlag not in {o.zimmer for o in opts}:
                vorschlag = None
        if (eigen := next((r for r in reserviert if r.person == b.schluessel), None)) is not None:
            status, stufe = "handeln", "krit"
            grund = (f"Gebäudeplan: {kurz(eigen.gebucht)} · eigene Planung: {kurz(eigen.geplant)} – widerspricht sich, "
                     "bitte klären (Heute)")
        zweite = b.massnahme.removeprefix("UWT ") if b.gruppe == "UWT" else b.massnahme
        erg.append(Zeile(b.schluessel, b.name, zweite, GRUPPE_KURZ.get(b.gruppe, b.gruppe), b.von, b.bis, gespeichert, status,
                         stufe, grund,
                         vorschlag, opts, m, hinweise, b.bemerkung))
    return erg


@dataclass
class Bereitschaft:
    """Sind die Zimmer einer Anreise bezugsfertig? ``punkte``: (art, Name, Text) – art = blocker | vorbereiten."""
    n: int
    bereit: int
    punkte: list[tuple[str, str, str]] = field(default_factory=list)

    @property
    def stufe(self) -> str:
        return "ok" if self.bereit == self.n else ("krit" if self.bereit < self.n / 2 else "warn")


def bereitschaft(stand: zp.Planstand, zs: list[Zeile], tag: date) -> Bereitschaft:
    """Je Person: Zimmer gespeichert, kein Konflikt, Reinigung vor genau dieser Anreise erledigt, Allergiker auf der
    Allergiker-Etage → bereit. Hilfsmittel, Begleitung und offene (nicht sperrende) Mängel sind „vorbereiten“."""
    from .seiten_kern import _reinigungen

    fertig = rl.erledigt()
    offen = {r.zimmer.id: r for r in _reinigungen(stand, tag - timedelta(days=28), tag)
             if r.naechste_anreise == tag and rl.schluessel(r) not in fertig}
    erg = Bereitschaft(len(zs), 0)
    for z in zs:
        blocker = []
        if not z.gespeichert:
            blocker.append("noch kein Zimmer")
        elif z.status == "handeln":
            blocker.append(z.grund)
        elif z.gespeichert in offen:
            r = offen[z.gespeichert]
            blocker.append(f"{kurz(z.gespeichert)}: {r.art} vom {r.tag:%d.%m.} noch nicht erledigt")
        erg.punkte += [("blocker", z.name, t) for t in blocker]
        if not blocker:
            erg.bereit += 1
        wo = f" ({kurz(z.gespeichert)})" if z.gespeichert else ""
        for h in z.hinweise:
            if h.art == "hilfsmittel":
                erg.punkte.append(("vorbereiten", z.name, f"{h.text} bereitstellen{wo}"))
            elif h.art == "begleitung":
                erg.punkte.append(("vorbereiten", z.name, f"Begleitung angekündigt{wo} – {z.bemerkung}"))
        if z.maengel and z.gespeichert and not blocker:
            erg.punkte.append(("vorbereiten", z.name, f"Mangel{wo}: {z.maengel}"))
    return erg


def zaehlen(zs: list[Zeile]) -> dict[str, int]:
    return {f: sum(1 for z in zs if z.filter(f)) for f in FILTER}


def kennzahlen(stand: zp.Planstand, tag: date) -> dict[str, int]:
    """Internatszimmer (ohne Gästezimmer) am Tag: frei | belegt | gesperrt."""
    erg = {"frei": 0, "belegt": 0, "gesperrt": 0}
    for z in stand.zimmer:
        if not z.aktiv or z.gaeste:
            continue
        s = stand.lage.status_am(z.id, tag)[0]
        erg["frei" if s in ("frei", "teilweise") else ("gesperrt" if s == "gesperrt" else "belegt")] += 1
    return erg


# ---------------------------------------------------------------------------------------
# Ändern – jeder Aufruf ist ein Schritt, den „Rückgängig“ zurücknimmt
# ---------------------------------------------------------------------------------------

def _schritt(titel: str, aktion: Callable[[], object], dateien: list[str] | None = None) -> object:
    """Alles oder nichts: bei einem Fehler wird der Stand davor zurückgeschrieben und der Fehler weitergereicht."""
    namen = aenderungen._dateien() + [n for n in (dateien or []) if n not in aenderungen._dateien()]
    vorher = aenderungen.schnappschuss(namen)
    try:
        erg = aktion()
    except Exception:
        for name, inhalt in vorher.items():
            if aenderungen.schnappschuss([name])[name] != inhalt:
                aenderungen._roh_schreiben(name, inhalt)
        raise
    aenderungen.merken(titel, vorher)
    return erg


# ---- Eigene Planung widerspricht dem Gebäudeplan („strittig“) ------------------------------------------
# Das Hauptprogramm lässt bei einem Widerspruch stillschweigend den Gebäudeplan gelten: steht die Person dort in einem
# anderen Zimmer, entfällt unsere Zuweisung – das geplante Zimmer erscheint FREI, obwohl Zuteilen und Suche es weiter
# zeigen. Ist der Gebäudeplan veraltet, droht eine Doppelbelegung. Deshalb: sichtbar machen, das Zimmer bis zur Klärung
# für niemand anderen anbieten und per Klick klären (Gebäudeplan stimmt / Planung stimmt).

@dataclass
class Strittig:
    person: str
    name: str
    geplant: str              # Zimmer-ID laut eigener Planung (gilt bisher NICHT)
    gebucht: str              # Zimmer-ID laut Gebäudeplan (gilt bisher)
    von: date
    bis: date


def strittige(stand: zp.Planstand) -> list[Strittig]:
    zw = {z["person"]: z for z in stand.zuweisungen}
    erg = []
    for a in getattr(stand.lage, "abgleich", []) or []:
        z = zw.get(a.person)
        if a.art != "anders" or z is None or z.get("vorrang") == "plan":
            continue
        erg.append(Strittig(a.person, zp.anzeige_name(a.name), a.geplant, a.gebucht,
                            date.fromisoformat(z["von"]), date.fromisoformat(z["bis"])))
    return sorted(erg, key=lambda s: (s.von, s.name))


def strittig_im_weg(stand: zp.Planstand, zimmer: str, von: date, bis: date, ausser: str = "") -> Strittig | None:
    """Ist ``zimmer`` im Zeitraum laut eigener Planung (strittig) für jemand anderen vorgesehen?"""
    return next((s for s in strittige(stand) if s.geplant == zimmer and s.person != ausser
                 and s.von <= bis and von <= s.bis), None)


def strittig_text(s: Strittig) -> str:
    return (f"{kurz(s.geplant)} ist laut eigener Planung für {s.name} ({s.von:%d.%m.} – {s.bis:%d.%m.%Y}) vorgesehen, "
            f"im Gebäudeplan steht {s.name} aber in {kurz(s.gebucht)} – bitte erst klären (Heute → „Planung widerspricht "
            "dem Gebäudeplan“).")


def strittig_klaeren(person: str, wahl: str) -> str:
    """``wahl``: „plan“ = Gebäudeplan stimmt (eigene Zuweisung auf dessen Zimmer setzen) | „planung“ = unsere Planung
    stimmt (gilt dann auch gegen den Gebäudeplan; das Zimmer im Gebäudeplan wird frei). Ein Rückgängig-Schritt."""
    stand = zp.laden()
    s = next((x for x in strittige(stand) if x.person == person), None)
    if s is None:
        raise ValueError("Das ist schon geklärt.")
    if wahl not in ("plan", "planung"):
        raise ValueError("Unbekannte Auswahl.")

    def aendern():
        alle = zp.zuweisungen_laden()
        for z in alle:
            if z["person"] == person:
                z["vorrang"] = wahl
                if wahl == "plan":
                    z["zimmer"] = s.gebucht
        speicher.schreiben(zp.ZUWEISUNGEN, {"zuweisungen": alle})
        from belegung import protokoll

        protokoll.eintragen([{"aktion": "gilt: " + ("Gebäudeplan" if wahl == "plan" else "eigene Planung"), "name": s.name,
                              "person": person, "alt": s.geplant if wahl == "plan" else s.gebucht,
                              "neu": s.gebucht if wahl == "plan" else s.geplant, "von": s.von.isoformat(),
                              "quelle": "Neue Oberfläche – Klären"}])
    _schritt(f"{s.name}: " + ("Gebäudeplan gilt" if wahl == "plan" else "Planung gilt"), aendern, [zp.ZUWEISUNGEN])
    if wahl == "plan":
        return f"{s.name}: Gebäudeplan gilt – {kurz(s.gebucht)}; {kurz(s.geplant)} ist frei"
    return (f"{s.name}: Planung gilt – {kurz(s.geplant)}; {kurz(s.gebucht)} ist frei. Bitte auch im Belegungssystem "
            "umbuchen.")


def _zuteilung(stand: zp.Planstand, schluessel: str, zimmer: str) -> zp.Zuteilung:
    b = next((x for x in stand.bedarf if x.schluessel == schluessel), None)
    if b is None:
        raise ValueError("Die Person ist nicht mehr in den Listen.")
    if (st_ := strittig_im_weg(stand, zimmer, b.von, b.bis, schluessel)) is not None:
        raise ValueError(strittig_text(st_))
    zeile = next((z for z in zeilen(stand, b.von.isoformat()) if z.schluessel == schluessel), None)
    if zeile is None or zimmer not in {o.zimmer for o in zeile.optionen}:
        raise ValueError(f"Zimmer {kurz(zimmer)} ist für {b.name} nicht (mehr) frei.")
    return zp.Zuteilung(b, stand.lage.zimmer[zimmer])


def zuweisen(schluessel: str, zimmer: str) -> str:
    """Ein Zimmer für eine Person speichern – nur Zimmer, die die Auswahl auch anbietet (frei bzw. Ausnahme)."""
    stand = zp.laden()
    zt = _zuteilung(stand, schluessel, zimmer)
    _schritt(f"{zt.bedarf.name} → {kurz(zimmer)}", lambda: zp.zuweisungen_speichern([zt], "Neue Oberfläche"))
    return f"{zt.bedarf.name} → {kurz(zimmer)}"


def vorschlaege_uebernehmen(kennung: str, nur: str = "ohne") -> str:
    """Alle grünen Vorschläge einer Anreise speichern. ``nur``: ohne | handeln | alle (ohne + Konflikte)."""
    stand = zp.laden()
    zs = [z for z in zeilen(stand, kennung) if z.vorschlag and (nur == "alle" or z.status == nur)]
    if not zs:
        raise ValueError("Keine Vorschläge offen.")
    zts = [_zuteilung(stand, z.schluessel, z.vorschlag) for z in zs]
    tag = date.fromisoformat(kennung)
    _schritt(f"Anreise {tag:%d.%m.}: {len(zts)} Vorschläge", lambda: zp.zuweisungen_speichern(zts, "Neue Oberfläche"))
    return f"Anreise {tag:%d.%m.}: {len(zts)} Zimmer zugewiesen"


def problemfaelle(stand: zp.Planstand, heute: date) -> dict[str, str]:
    """Person → Grund: Planungen mit Konflikt (belegt/gesperrt) oder in einem inzwischen unbewohnbaren Zimmer."""
    erg = {k.person: k.grund for k in zp.konflikte(stand.lage, heute)}
    for z in stand.zuweisungen:
        if z["zimmer"] in stand.lage.unbewohnbar and z.get("bis", "") >= heute.isoformat() and z["person"] not in erg:
            erg[z["person"]] = f"unbewohnbar: {stand.lage.unbewohnbar[z['zimmer']]}"
    return erg


@dataclass
class ZimmerPruefung:
    zimmer: str | None        # Zimmer-ID, wenn erkannt
    art: str                  # passt | ausnahme | nein
    text: str
    gruende: list[str] = field(default_factory=list)   # wer/was im Zeitraum im Weg ist


def _zimmer_aus_text(stand: zp.Planstand, text: str) -> str | None:
    """„3.2 111“, „3.2-111“, „GS-3.2-111“, „2-104“ → Zimmer-ID."""
    t = re.sub(r"\s+", " ", (text or "").strip().upper()).removeprefix("GS-").removeprefix("GS ")
    m = re.match(r"^(\d(?:\.\d)?)\s*[- /]?\s*([A-Z]?\d{2,4}[A-Z]?)$", t)
    if not m:
        return None
    kurz_ = f"{m.group(1)}-{m.group(2)}"
    return next((z.id for z in stand.zimmer if z.kurz.upper() == kurz_), None)


def zimmer_pruefen(stand: zp.Planstand, schluessel: str, eingabe: str) -> ZimmerPruefung:
    """Warum ist ein bestimmtes Zimmer für diese Person (nicht) wählbar? Mit allem, was im Zeitraum im Weg ist."""
    b = next((x for x in stand.bedarf if x.schluessel == schluessel), None)
    if b is None:
        return ZimmerPruefung(None, "nein", "Die Person steht nicht (mehr) in den Listen.")
    zid = _zimmer_aus_text(stand, eingabe)
    if zid is None:
        return ZimmerPruefung(None, "nein", f"Zimmer „{eingabe}“ nicht gefunden – bitte z. B. „3.2-111“ eingeben.")
    lage, z, ohne = stand.lage, stand.lage.zimmer[zid], frozenset({schluessel})
    if (stand.zugewiesen(schluessel) or {}).get("zimmer") == zid:
        return ZimmerPruefung(zid, "nein", f"{z.kurz} ist schon für diese Person gespeichert.")
    if not z.aktiv:
        return ZimmerPruefung(zid, "nein", f"{z.kurz} gehört nicht (mehr) zum Internat (außer Betrieb).")
    if zid in lage.unbewohnbar:
        return ZimmerPruefung(zid, "nein", f"{z.kurz} ist unbewohnbar: {lage.unbewohnbar[zid]} – erst den Mangel beheben.")
    if (st_ := strittig_im_weg(stand, zid, b.von, b.bis, schluessel)) is not None:
        return ZimmerPruefung(zid, "nein", strittig_text(st_))
    if zp.nur_doppel(z, b.gruppe):
        return ZimmerPruefung(zid, "nein", f"{z.kurz} ist ein Doppelzimmer ({z.betten} Betten) – {zp.DOPPEL_GRUND}. "
                              "Das ist eine feste Regel des Hauptprogramms (auch nicht von Hand). Ist das Zimmer in "
                              "Wirklichkeit ein Einzelzimmer: unter Einstellungen → Zimmer-Stammdaten die Betten ändern.")
    puffer = timedelta(days=max(lage.puffer - 1, 0))
    im_weg = sorted((x for x in lage.belegungen.get(zid, []) if x.art in ("belegt", "geplant", "gesperrt")
                     and x.person != schluessel and x.von <= b.bis + puffer and b.von <= x.bis + puffer), key=lambda x: x.von)
    gruende = [f"{(zp.anzeige_name(x.name) if x.name else x.grund or 'gesperrt')} · {x.von:%d.%m.%Y} – {x.bis:%d.%m.%Y} · "
               + {"belegt": "laut Gebäudeplan", "geplant": "im Programm geplant", "gesperrt": "gesperrt"}[x.art]
               for x in im_weg]
    if lage.freie_betten(zid, b.von, b.bis, ohne) <= 0:
        extra = f" (mit {lage.puffer} Tag{'en' if lage.puffer != 1 else ''} Abstand für die Reinigung)" if lage.puffer else ""
        return ZimmerPruefung(zid, "nein", f"{z.kurz} ist vom {b.von:%d.%m.} bis {b.bis:%d.%m.%Y}{extra} belegt oder gesperrt.",
                              gruende)
    grund = zp.passt(lage, z, b, ohne)
    if grund and lage.mitbewohner(zid, b.von, b.bis, ohne):
        return ZimmerPruefung(zid, "nein", f"In {z.kurz} wohnt im Zeitraum schon jemand – dorthin geht es nicht ({grund}).",
                              gruende)
    if grund:
        return ZimmerPruefung(zid, "ausnahme", f"{z.kurz} ist frei, verletzt aber eine Regel: {grund}. "
                              "Von Hand trotzdem möglich.", gruende)
    return ZimmerPruefung(zid, "passt", f"{z.kurz} ist frei und passt.", gruende)


@dataclass
class Fall:
    """Eine Planung mit Konflikt bzw. in einem unbewohnbaren Zimmer – zum Prüfen vor dem Umplanen."""
    schluessel: str
    name: str
    zimmer: str               # Zimmer-ID der Planung
    grund: str
    von: date
    bis: date
    wohnt: bool               # schon eingezogen → kein Ausweichzimmer hier, sondern Umzug (Zimmerkarte)
    vorschlag: str | None     # freies Ausweichzimmer (Zimmer-ID) oder None


def faelle(stand: zp.Planstand, heute: date, nur_unbewohnbar: bool = False) -> list[Fall]:
    """Alle Problemfälle mit Ausweichvorschlag – ändert nichts (Entscheidung im Panel „Prüfen und zuweisen“)."""
    pf = {p: g for p, g in problemfaelle(stand, heute).items() if not nur_unbewohnbar or g.startswith("unbewohnbar")}
    bedarf = {b.schluessel: b for b in stand.bedarf if b.schluessel in pf}
    kandidaten: dict[str, list[str]] = {}            # je Person: Vorschlag, dann die übrigen freien Zimmer
    for tag in sorted({b.von.isoformat() for b in bedarf.values()}):
        for z in zeilen(stand, tag, heute):
            if z.schluessel in pf:
                liste = ([z.vorschlag] if z.vorschlag else []) + [o.zimmer for o in z.optionen if o.art == "frei"]
                kandidaten[z.schluessel] = [x for i, x in enumerate(liste) if x and x != z.gespeichert
                                            and x not in stand.lage.unbewohnbar and x not in liste[:i]]
    namen = {z["person"]: z for z in stand.zuweisungen}
    erg = []
    for p, grund in pf.items():
        b, zw = bedarf.get(p), namen.get(p, {})
        if b is None and not zw:
            continue
        von = b.von if b else date.fromisoformat(zw.get("von", heute.isoformat()))
        bis = b.bis if b else date.fromisoformat(zw.get("bis", heute.isoformat()))
        zimmer = (stand.zugewiesen(p) or {}).get("zimmer", "") or zw.get("zimmer", "")
        erg.append(Fall(p, zp.anzeige_name(b.name if b else zw.get("name", "")), zimmer,
                        grund.split(": ", 1)[-1] if grund.startswith("unbewohnbar") else grund, von, bis, von < heute,
                        None))
    erg.sort(key=lambda f: (f.wohnt, f.von, f.zimmer))
    # gemeinsam verteilen: kein Ausweichzimmer zweimal für überlappende Zeiträume (jeder Fall einzeln hätte oft dasselbe)
    vergeben: list[tuple[str, date, date]] = []
    for f in erg:
        if f.wohnt:
            continue
        f.vorschlag = next((x for x in kandidaten.get(f.schluessel, [])
                            if not any(x == z and f.von <= b and v <= f.bis for z, v, b in vergeben)), None)
        if f.vorschlag:
            vergeben.append((f.vorschlag, f.von, f.bis))
    return erg


def ausweich_uebernehmen(personen: list[str], heute: date | None = None) -> str:
    """Nur die ausgewählten Planungen bekommen ihr Ausweichzimmer – ein Schritt, ein Rückgängig."""
    heute = heute or date.today()
    stand = zp.laden()
    gewaehlt = {f.schluessel: f for f in faelle(stand, heute) if f.schluessel in set(personen) and f.vorschlag}
    if not gewaehlt:
        raise ValueError("Nichts ausgewählt, das ein freies Ausweichzimmer hat.")
    zts = [_zuteilung(stand, p, f.vorschlag) for p, f in gewaehlt.items()]
    _schritt(f"{len(zts)} Ausweichzimmer", lambda: zp.zuweisungen_speichern(zts, "Neue Oberfläche"))
    rest = len(set(personen)) - len(zts)
    return f"{len(zts)} Ausweichzimmer zugewiesen" + (f", {rest} ohne freies Zimmer" if rest else "")


def konflikte_loesen(heute: date | None = None) -> str:
    """Jede Planung mit Konflikt bekommt ihr (gemeinsam verteiltes) Ausweichzimmer – Bewohner und Fälle ohne freies
    Zimmer bleiben. In der Oberfläche läuft das über „Prüfen und zuweisen“ (nur das Angehakte)."""
    heute = heute or date.today()
    fs = [f.schluessel for f in faelle(zp.laden(), heute) if f.vorschlag]
    if not fs:
        raise ValueError("Für die Konflikte gibt es gerade kein freies Ausweichzimmer – bitte im Hauptprogramm lösen.")
    return ausweich_uebernehmen(fs, heute)


def reinigung_erledigt(dringend: bool, heute: date | None = None) -> str:
    from belegung import cockpit

    heute = heute or date.today()
    kon, offen = cockpit.reinigung_heute(zp.laden(), heute)
    rs = kon if dringend else offen
    if not rs:
        raise ValueError("Keine offenen Reinigungen.")
    _schritt(f"{len(rs)} Reinigungen erledigt", lambda: [rl.erledigt_setzen(r) for r in rs], [rl.DATEI])
    return f"{len(rs)} Zimmer als gereinigt markiert"


def termin_erledigt(tid: str) -> str:
    from belegung import anreiseliste

    t = next((x for x in tm.alle() if x.id == tid), None)
    if t is None:
        raise ValueError("Den Termin gibt es nicht mehr.")
    _schritt(f"Erledigt: {t.titel}", lambda: tm.erledigt_setzen(t), [tm.DATEI, anreiseliste.DATEI])
    return f"Erledigt: {t.titel}"


def rueckgaengig() -> tuple[bool, str]:
    return aenderungen.rueckgaengig("Neue Oberfläche")


# ---------------------------------------------------------------------------------------
# Aufgaben-Center: Karten mit 1-Klick-Lösung
# ---------------------------------------------------------------------------------------

@dataclass
class Aktion:
    schluessel: str       # z. B. „vorschlaege:2026-10-26“, „konflikte“, „reinigung:dringend“, „termin:<id>“
    text: str
    zeigen: str = ""      # Anreise, die die Tabelle danach zeigen soll


@dataclass
class Karte:
    id: str
    stufe: str            # dringend | bald | info
    titel: str
    detail: str
    aktion: Aktion | None = None
    zweite: Aktion | None = None
    hinweis: str = ""     # wenn es hier keine 1-Klick-Lösung gibt


HAUPTPROGRAMM = "Im Hauptprogramm erledigen"
# Vorgang-Ziel → Seite der neuen Oberfläche („Seite/Ansicht“), für den zweiten Knopf einer Karte
ZIELE = {"konflikte": "anreisen", "eintragen": "anreisen/eintragen", "reinigung": "reinigung", "abreisen": "anreisen/abreisen",
         "facility": "reinigung/facility", "maengel": "zimmer/liste", "engpaesse": "auswertung/zimmer", "gebaeudeplan": "daten",
         "termin": "termine", "posteingang": "assistenz", "mail": "assistenz", "mieterende": "mieter", "umzug": "zimmer"}


def _karte(v, stand: zp.Planstand | None) -> Karte:
    k = Karte(v.id, v.stufe, v.titel, v.detail)
    art = v.id.split(":")[0]
    if art == "anreise" and stand is not None:
        kennung = v.id.split(":", 1)[1]
        alle = zeilen(stand, kennung)
        try:
            b = bereitschaft(stand, alle, date.fromisoformat(kennung))
            k.detail += f" · {b.bereit} von {b.n} Zimmern bezugsfertig"
        except Exception:                      # noqa: BLE001 – Zusatzinfo, die Karte bleibt
            pass
        zs = [z for z in alle if z.status == "ohne"]
        mit = sum(1 for z in zs if z.vorschlag)
        if mit:
            k.aktion = Aktion(f"vorschlaege:{kennung}", f"{mit} Vorschläge übernehmen", kennung)
        k.zweite = Aktion(f"zeigen:{kennung}", "Anzeigen", kennung)
    elif art == "konflikte":
        k.aktion = Aktion("konflikte", "Prüfen und zuweisen")
    elif v.id == "reinigung_dringend":
        k.aktion = Aktion("reinigung:dringend", "Alle als gereinigt markieren")
    elif v.id == "reinigung":
        k.aktion = Aktion("reinigung:heute", "Alle als gereinigt markieren")
    elif v.erledigen:
        k.aktion = Aktion(f"termin:{v.erledigen}", "Erledigt")
    if k.zweite is None:
        ziel = ZIELE.get(v.ziel.split(":")[0])
        if ziel:
            k.zweite = Aktion(f"zeigen:{v.ziel}", v.aktion.rstrip(" …") if k.aktion is None else "Ansehen", ziel)
    if k.aktion is None and k.zweite is None:
        k.hinweis = f"{HAUPTPROGRAMM}: {v.aktion.rstrip(' …')}"
    return k


def karten(stand: zp.Planstand | None, heute: date | None = None, vorgaenge_: list | None = None) -> list[Karte]:
    """Offene Vorgänge (wie „Heute“ im Hauptprogramm) als Karten – ohne die heute auf „Später“ gesetzten."""
    from belegung import vorgaenge

    heute = heute or date.today()
    if vorgaenge_ is None:
        try:
            termine = tm.alle()
        except Exception:                  # noqa: BLE001 – Termine sind optional
            termine = []
        try:
            from belegung import gebaeudeplan

            neuer_plan = gebaeudeplan.neuer_plan_da()
        except Exception:                  # noqa: BLE001 – Ordner fehlt o. Ä.
            neuer_plan = False
        vorgaenge_ = vorgaenge.sammeln(stand, heute, termine, neuer_plan=neuer_plan)
    weg = spaeter(heute)
    erg = [_karte(v, stand) for v in vorgaenge_ if v.id not in weg]
    if stand is not None and not any(k.id == "konflikte" for k in erg):
        # Planungen in inzwischen unbewohnbaren Zimmern meldet „Heute“ nicht – hier schon, mit 1-Klick-Lösung
        unb = {p: g for p, g in problemfaelle(stand, heute).items() if g.startswith("unbewohnbar")}
        if unb and "unbewohnbar" not in weg:
            namen = {z["person"]: z.get("name", "") for z in stand.zuweisungen}
            erg.insert(0, Karte("unbewohnbar", "dringend",
                                f"{len(unb)} Planung{'en' if len(unb) > 1 else ''} in unbewohnbarem Zimmer",
                                "; ".join(f"{namen.get(p, '')} ({g.split(': ', 1)[1]})" for p, g in list(unb.items())[:2])
                                + (" …" if len(unb) > 2 else ""), Aktion("konflikte", "Prüfen und zuweisen")))
    if stand is not None and "strittig" not in weg and (sts := strittige(stand)):
        erg.insert(0, Karte("strittig", "dringend",
                            f"{len(sts)} Planung{'en widersprechen' if len(sts) > 1 else ' widerspricht'} dem Gebäudeplan",
                            "; ".join(f"{x.name}: Planung {kurz(x.geplant)}, Gebäudeplan {kurz(x.gebucht)}" for x in sts[:2])
                            + (" …" if len(sts) > 2 else "") + " – bis zur Klärung wird das geplante Zimmer niemandem angeboten",
                            Aktion("strittig", "Klären")))
    if stand is not None and "allergie" not in weg:
        k = allergie_karte(stand, heute)
        if k is not None:
            erg.insert(0 if k.stufe == "dringend" else len([x for x in erg if x.stufe == "dringend"]), k)
    return erg


def allergie_karte(stand: zp.Planstand, heute: date) -> Karte | None:
    """Eigene Meldung für Allergiker (Hinweis in der Anreiseliste): gehören auf die Allergiker-Etage (Haus 2, 1. OG).
    Dringend, wenn jemand in den nächsten 7 Tagen anreist und dort (noch) kein Zimmer hat."""
    from . import hinweise_kern as hk

    faelle = hk.allergie_faelle(stand, heute)
    falsch = [f for f in faelle if not f.auf_etage]
    if not faelle:
        return None
    if not falsch:
        return Karte("allergie", "info", f"{len(faelle)} Allergiker – alle auf der {hk.ALLERGIE_TEXT}",
                     ", ".join(f"{f.name} ({f.anreise:%d.%m.}, {kurz(f.zimmer)})" for f in faelle[:3])
                     + (" …" if len(faelle) > 3 else ""),
                     zweite=Aktion(f"zeigen:{faelle[0].anreise.isoformat()}", "Ansehen", faelle[0].anreise.isoformat()))
    bald = any(f.anreise <= heute + timedelta(days=7) for f in falsch)
    return Karte("allergie", "dringend" if bald else "bald",
                 f"{len(falsch)} Allergiker nicht auf der {hk.ALLERGIE_TEXT}",
                 "; ".join(f"{f.name}: Anreise {f.anreise:%d.%m.}, " + (f"geplant {kurz(f.zimmer)}" if f.zimmer else "noch ohne Zimmer")
                           for f in falsch[:3]) + (" …" if len(falsch) > 3 else ""),
                 zweite=Aktion(f"zeigen:{falsch[0].anreise.isoformat()}", "Zur Anreise", falsch[0].anreise.isoformat()))


def ausfuehren(schluessel: str, heute: date | None = None) -> str:
    """Hauptknopf einer Karte. Gibt die Meldung für den Toast zurück; ValueError = fachlich nicht möglich."""
    art, _, wert = schluessel.partition(":")
    if art == "vorschlaege":
        return vorschlaege_uebernehmen(wert)
    if art == "konflikte":
        return konflikte_loesen(heute)
    if art == "reinigung":
        return reinigung_erledigt(wert == "dringend", heute)
    if art == "termin":
        return termin_erledigt(wert)
    raise ValueError(f"Unbekannte Aktion: {schluessel}")


def spaeter(heute: date | None = None) -> set[str]:
    heute = heute or date.today()
    roh = speicher.lesen(ZUSTAND, {}).get("spaeter", {})
    return {k for k, bis in roh.items() if bis > heute.isoformat()}


def spaeter_setzen(kid: str, an: bool = True, heute: date | None = None) -> None:
    """„Später“: Karte bis morgen ausblenden (an=False holt sie zurück)."""
    heute = heute or date.today()
    roh = speicher.lesen(ZUSTAND, {})
    s = {k: v for k, v in roh.get("spaeter", {}).items() if v > heute.isoformat()}
    if an:
        s[kid] = (heute + timedelta(days=1)).isoformat()
    else:
        s.pop(kid, None)
    roh["spaeter"] = s
    speicher.schreiben(ZUSTAND, roh)


def automatisch_oeffnen(ks: list[Karte], heute: date | None = None) -> bool:
    """Das Center öffnet sich von selbst, wenn Dringendes da ist, das heute noch nicht gezeigt wurde."""
    heute = heute or date.today()
    roh = speicher.lesen(ZUSTAND, {})
    gezeigt = set(roh.get("gezeigt", {}).get(heute.isoformat(), []))
    neu = {k.id for k in ks if k.stufe == "dringend"} - gezeigt
    if neu:
        roh["gezeigt"] = {heute.isoformat(): sorted(gezeigt | neu)}
        speicher.schreiben(ZUSTAND, roh)
    return bool(neu)


# ---------------------------------------------------------------------------------------
# Frei nach Planung
# ---------------------------------------------------------------------------------------

@dataclass
class NachPlanung:
    wochen: list          # (Woche-Text, frei jetzt, frei nach Planung, EMR, Doppel, Stufe gesamt, Stufen je Art)
    tiefst: tuple | None  # (Woche-Text, frei nach Planung, Stufe)
    offen: int
    ohne_platz: int


def nach_planung(stand: zp.Planstand, heute: date | None = None, wochen: int = 12) -> NachPlanung:
    """Freie Zimmer je Woche, wenn alle bekannten Anreisen (auch die ohne Zimmer) nach den Regeln ein Zimmer hätten."""
    from belegung import eintragen

    heute = heute or date.today()
    np_ = eintragen.nach_planung(stand, heute, wochen)
    zeilen = [(n.text, j.gesamt, n.gesamt, n.emr, n.doppel, n.gesamtstufe,
               {a: n.stufe(a) for a in ("gesamt", "emr", "doppel")}) for j, n in np_.wochen]
    t = np_.tiefst
    return NachPlanung(zeilen, (t.text, t.gesamt, t.stufe("gesamt")) if t else None, np_.offen, np_.ohne_platz)


SYMBOL = {"anreise": "flight_land", "konflikte": "warning", "unbewohnbar": "report", "strittig": "sync_problem", "eintragen": "edit_note",
          "reinigung": "cleaning_services", "abreisen": "flight_takeoff", "facility": "electrical_services",
          "maengel": "build", "engpass": "trending_down", "termin": "event", "mail": "mail", "posteingang": "mail",
          "mieterende": "key", "gebaeudeplan": "description", "umzug": "swap_horiz", "n": "campaign"}


def symbol(kid: str) -> str:
    """Kleines Symbol je Aufgabentyp (aus der Kennung, z. B. „anreise:2026-10-26“, „reinigung_dringend“)."""
    art = kid.split(":")[0].split("_")[0]
    return SYMBOL.get(art, "task_alt")


def willkommen_zeigen() -> bool:
    return not speicher.lesen(ZUSTAND, {}).get("willkommen_gesehen")


def willkommen_weg() -> None:
    roh = speicher.lesen(ZUSTAND, {})
    roh["willkommen_gesehen"] = True
    speicher.schreiben(ZUSTAND, roh)


# ---------------------------------------------------------------------------------------
# Neue Personen: Das Hauptprogramm speichert kein Anlagedatum – die neue Oberfläche merkt sich daher selbst, wann
# eine Person zum ersten Mal in den Listen stand (eigene Datei, die alten Dateien bleiben unberührt).
# ---------------------------------------------------------------------------------------

NEU_DATEI = "modern_ui_neu.json"
NEU_TAGE = 7


def neue_personen(stand: zp.Planstand, heute: date | None = None, tage: int = NEU_TAGE) -> dict[str, date]:
    """Schlüssel → Tag, an dem die Person zuerst auftauchte – nur die der letzten ``tage`` Tage.

    Beim allerersten Aufruf gilt für Personen aus einer Anreiseliste deren Importdatum (sonst „schon länger da“),
    danach zählt der Tag, an dem die neue Oberfläche die Person zum ersten Mal sieht."""
    from belegung import anreiseliste

    heute = heute or date.today()
    roh = speicher.lesen(NEU_DATEI, {})
    gesehen: dict[str, str] = roh.get("gesehen", {})
    schluessel = {b.schluessel for b in stand.bedarf}
    neu = schluessel - set(gesehen)
    if neu:
        if not gesehen:                      # erster Start: Importdatum der Liste, sonst „alt“
            personen, listen = anreiseliste.laden()
            liste_von = {p.schluessel: p.liste for p in personen}
            for k in neu:
                am = (listen.get(liste_von.get(k, ""), {}) or {}).get("importiert_am", "")
                gesehen[k] = am[:10] if am else "2000-01-01"
        else:
            for k in neu:
                gesehen[k] = heute.isoformat()
        speicher.schreiben(NEU_DATEI, {"gesehen": gesehen})
    grenze = heute - timedelta(days=tage - 1)
    erg = {}
    for k in schluessel:
        try:
            tag = date.fromisoformat(gesehen.get(k, "2000-01-01"))
        except ValueError:
            continue
        if tag >= grenze:
            erg[k] = tag
    return erg



# ---------------------------------------------------------------------------------------
# Design (Theme) und Navigation – gespeichert in der eigenen Datei, wirkt nach dem Neustart weiter
# ---------------------------------------------------------------------------------------

def design_lesen() -> dict:
    """Layout, Theme, Hell/Dunkel, Dichte, schmale Leiste, Vollbild, Notiz – geprüft (Unbekanntes → Original)."""
    from .themes import bereinigen

    return bereinigen(speicher.lesen(ZUSTAND, {}).get("design", {}))


def design_setzen(d: dict) -> dict:
    from .themes import bereinigen

    roh = speicher.lesen(ZUSTAND, {})
    roh["design"] = bereinigen(d)
    speicher.schreiben(ZUSTAND, roh)
    return roh["design"]


def kontingent_lesen(standort: str) -> dict | None:
    """Geplante Aufteilung der Kapazität in % ({"UWT": 20, "Mieter": 10}) – Planungsannahme, keine Belegungsdaten."""
    k = speicher.lesen(ZUSTAND, {}).get("kontingente", {}).get(standort)
    return {"UWT": float(k.get("UWT", 0)), "Mieter": float(k.get("Mieter", 0))} if isinstance(k, dict) else None


def kontingent_setzen(standort: str, werte: dict | None) -> None:
    roh = speicher.lesen(ZUSTAND, {})
    alle = roh.setdefault("kontingente", {})
    if werte is None:
        alle.pop(standort, None)
    else:
        alle[standort] = {"UWT": float(werte["UWT"]), "Mieter": float(werte["Mieter"])}
    speicher.schreiben(ZUSTAND, roh)


# ---------------------------------------------------------------------------------------
# Zähler an den Menüpunkten und Glocke (ungelesene Neuigkeiten) – wie in der Seitenleiste des Hauptprogramms
# ---------------------------------------------------------------------------------------

@dataclass
class NavZahl:
    n: int
    tipp: str
    rot: bool = False


def nav_zahlen(stand: zp.Planstand | None, heute: date | None = None) -> dict[str, NavZahl]:
    """Seite → Zähler: fällige Termine, bald endende Mietverträge, offene Mails, offene Reinigungen vor einer Anreise,
    geplante Zimmer, die laut Gebäudeplan inzwischen belegt/gesperrt sind. Jede Quelle für sich – ein Fehler in einer
    lässt die anderen stehen."""
    from belegung import mails
    from belegung import mieter as mt

    log = logging.getLogger(__name__)
    heute = heute or date.today()
    erg: dict[str, NavZahl] = {}

    def setzen(seite, fn):
        try:
            z = fn()
        except Exception:                      # noqa: BLE001
            log.exception("Zähler %s", seite)
            return
        if z and z.n:
            erg[seite] = z

    setzen("termine", lambda: NavZahl(n := sum(1 for t in tm.alle() if t.faellig(heute)),
                                      f"{n} Erinnerung{'en' if n != 1 else ''} fällig"))
    setzen("mieter", lambda: NavZahl(n := sum(1 for m in mt.laden() if mt.status(m, heute)[1] == "knapp"),
                                     f"{n} Mietvertr{'äge enden' if n != 1 else 'ag endet'} in den nächsten "
                                     f"{mt.BALD_TAGE // 7} Wochen"))
    setzen("assistenz", lambda: NavZahl(n := mails.offen_anzahl(), f"{n} Mail{'s' if n != 1 else ''} offen oder zu prüfen"))
    if stand is not None:
        def reinigung():
            zpv = stand.zimmer_pivot
            rs = zp.reinigungen(stand.lage, heute - timedelta(days=14), heute + timedelta(days=1),
                                zpv.zeitraum[1] if zpv else None, zpv.zeitraum[0] if zpv else None,
                                bool(speicher.einstellungen().get("reinigung_anreisetag", False)))
            n = len(rl.konflikte(rs, heute, rl.erledigt()))
            return NavZahl(n, f"{n} Reinigung{'en' if n != 1 else ''} offen, obwohl jemand einzieht", True)

        setzen("reinigung", reinigung)
        setzen("anreisen", lambda: NavZahl(n := len(zp.konflikte(stand.lage, heute)),
                                           f"{n} geplante{'s' if n == 1 else ''} Zimmer laut Gebäudeplan inzwischen "
                                           "belegt/gesperrt", True))
    return erg


@dataclass
class Neu:
    id: str
    zeit: str
    text: str
    art: str
    gelesen: bool
    seite: str            # wohin ein Klick führt ("" = nirgends)
    ansicht: str = ""


# Ziele des Hauptprogramms („zimmerplan:Reinigung“ …) → Seiten der neuen Oberfläche
_NEU_ZIELE = {"zimmerplan:reinigung": ("reinigung", ""), "zimmerplan:aufgaben": ("reinigung", "facility"),
              "zimmerplan": ("zimmer", ""), "posteingang": ("assistenz", ""), "start": ("heute", ""),
              "belegung": ("auswertung", ""), "prognose": ("auswertung", "prognose")}


def neu_ziel(ziel: str) -> tuple[str, str]:
    z = (ziel or "").strip().lower()
    if z in _NEU_ZIELE:
        return _NEU_ZIELE[z]
    kopf = z.split(":")[0]
    if kopf in _NEU_ZIELE:
        return _NEU_ZIELE[kopf]
    from .register import TITEL

    return (kopf, "") if kopf in TITEL else ("", "")


def neuigkeiten(anzahl: int = 40) -> tuple[list[Neu], int]:
    """Die letzten Neuigkeiten (gemeinsam mit dem Hauptprogramm) und wie viele davon ungelesen sind."""
    from belegung import neuigkeiten as nk

    alle = nk.laden()
    erg = [Neu(n.id, f"{n.zeit:%d.%m. %H:%M}", n.text, n.art, n.gelesen, *neu_ziel(n.ziel)) for n in alle[:anzahl]]
    return erg, sum(1 for n in alle if not n.gelesen)


def neu_gelesen(nid: str | None = None) -> None:
    from belegung import neuigkeiten as nk

    nk.gelesen_setzen(nid)
