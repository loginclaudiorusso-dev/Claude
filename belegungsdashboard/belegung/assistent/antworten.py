"""Exakte Antworten aus den Daten. Jede Zahl wird berechnet, nichts wird generiert."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta

import pandas as pd

from ..datenstand import Datenstand
from ..konfig import GESAMT, STANDORT_LABEL, STANDORTE, ampel_stufe
from .verstehen import MONATSNAMEN, Anfrage, Versteher, Zeitraum, monat_zeitraum, standorte_fuer


@dataclass
class Antwort:
    text: str                                   # Mini-Markup: **fett**, Zeilenumbrüche
    tabelle: tuple[list[str], list[list[str]]] | None = None
    quelle: str = "daten"                       # daten | ki | hinweis
    vorschlaege: list[str] = field(default_factory=list)
    hinweis: str | None = None                  # kleine Fußnote (z. B. "Prognose")


def zahl(x: float | None, nachkomma: int = 0) -> str:
    if x is None:
        return "–"
    s = f"{x:,.{nachkomma}f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".")


def prozent(anteil: float | None) -> str:
    return "–" if anteil is None else f"{zahl(anteil * 100)} %"


def monat_text(d: date) -> str:
    return f"{MONATSNAMEN[d.month - 1]} {d.year}"


def name(standort: str) -> str:
    return STANDORT_LABEL.get(standort, standort)


BEISPIELE = [
    "Wie ist die Belegung heute?",
    "Wie viele Plätze sind in Goslar frei?",
    "Prognose für März",
    "Vergleich der Standorte",
    "Wie hat sich Weser-Ems in den letzten 6 Monaten entwickelt?",
    "Anreisen nächste 4 Wochen",
    "Wann war die höchste Belegung 2025?",
    "Wie gut ist die Prognose?",
]


class Assistent:
    """Beantwortet Fragen zum geladenen Datenstand. Hält den Gesprächskontext für Folgefragen."""

    def __init__(self, ds: Datenstand, heute: date | None = None):
        self.ds = ds
        self.heute = heute or date.today()
        self.versteher = Versteher(self.heute)
        self.vorher: Anfrage | None = None
        self.brutto_standard = False

    def daten_setzen(self, ds: Datenstand) -> None:
        self.ds = ds

    def zuruecksetzen(self) -> None:
        self.vorher = None

    # ------------------------------------------------------------------------------------

    def verstehe(self, frage: str) -> Anfrage:
        return self.versteher.verstehe(frage, self.vorher)

    def beantworte(self, frage: str) -> Antwort | None:
        """None = nicht sicher verstanden (dann ggf. an das Sprachmodell weitergeben)."""
        anfrage = self.verstehe(frage)
        if not anfrage.erkannt:
            return None
        antwort = self.beantworte_anfrage(anfrage)
        if antwort is not None:
            self.vorher = anfrage
        return antwort

    def beantworte_anfrage(self, a: Anfrage) -> Antwort | None:
        methode = getattr(self, f"_{a.absicht}", None)
        if methode is None:
            return None
        return methode(a)

    def _brutto(self, a: Anfrage) -> bool:
        return self.brutto_standard if a.brutto is None else a.brutto

    def _stichtag_oder(self, z: Zeitraum | None) -> Zeitraum:
        return z or Zeitraum(self.ds.stichtag, self.ds.stichtag, "tag", "heute")

    # ---- Absichten -----------------------------------------------------------------------

    def _hilfe(self, a: Anfrage) -> Antwort:
        return Antwort(
            "Ich beantworte Fragen zu **Belegung, Auslastung, freien Plätzen, Kapazitäten, Prognosen, "
            "Anreisen und Mietern** – für Bad Pyrmont, Goslar, Weser-Ems oder alle zusammen, für einen "
            "Tag, einen Monat oder einen beliebigen Zeitraum. Folgefragen wie „und Goslar?“ oder "
            "„und im November?“ verstehe ich auch.",
            vorschlaege=BEISPIELE[:6],
        )

    def _abseits(self, a: Anfrage) -> Antwort:
        return Antwort("Dabei kann ich nicht helfen – ich beantworte nur Fragen zur Belegung, Kapazität, "
                       "Prognose, zu Anreisen und Mietern der drei Standorte.", quelle="hinweis",
                       vorschlaege=BEISPIELE[:3])

    def _ueberblick(self, a: Anfrage) -> Antwort:
        tag = self.ds.stichtag
        brutto = self._brutto(a)
        zeilen = []
        for s in STANDORTE + [GESAMT]:
            auf = self.ds.aufschluesselung(s, tag, brutto)
            vor = self.ds.belegung(s, tag - timedelta(days=7), tag - timedelta(days=7), brutto)
            delta = auf.belegt - float(vor.iloc[0]) if len(vor) else None
            zeilen.append([name(s), zahl(auf.belegt), zahl(auf.kapazitaet) if auf.kapazitaet else "–",
                           prozent(auf.anteil), ("+" if (delta or 0) > 0 else "") + zahl(delta) if delta is not None else "–"])
        text = f"**Lage am {tag:%d.%m.%Y}** ({'Brutto' if brutto else 'Netto'}):"
        naechster = date(tag.year + (tag.month == 12), tag.month % 12 + 1, 1)
        mp = self.ds.monatsprognose(GESAMT, naechster, brutto)
        if mp:
            text += (f"\nFür {monat_text(naechster)} werden insgesamt **{zahl(mp['erwartet'])}** erwartet "
                     f"(80 %-Spanne {zahl(mp['lo80'])}–{zahl(mp['hi80'])}).")
        risiken = self._kapazitaetsrisiken(brutto)
        if risiken:
            text += "\n⚠ " + "; ".join(risiken)
        return Antwort(text, (["Standort", "Belegt", "Kapazität", "Auslastung", "ggü. Vorwoche"], zeilen),
                       vorschlaege=["Prognose für die nächsten 6 Monate", "Freie Plätze je Standort"])

    def _belegung(self, a: Anfrage, modus: str = "belegung") -> Antwort:
        z = self._stichtag_oder(a.zeit)
        brutto = self._brutto(a)
        standorte = standorte_fuer(a)
        if z.ist_tag:
            return self._tag(standorte, z, brutto, modus)
        return self._zeitraum(standorte, z, brutto, modus, a.aggregat)

    def _auslastung(self, a: Anfrage) -> Antwort:
        return self._belegung(a, "auslastung")

    def _frei(self, a: Anfrage) -> Antwort:
        return self._belegung(a, "frei")

    def _tag(self, standorte: list[str], z: Zeitraum, brutto: bool, modus: str) -> Antwort:
        tag = z.von
        if tag < self.ds.erster_tag:
            return Antwort(f"Für den {tag:%d.%m.%Y} liegen keine Daten vor (Daten ab {self.ds.erster_tag:%d.%m.%Y}).",
                           quelle="hinweis")
        zukunft = tag > self.ds.stichtag
        werte = []
        for s in standorte:
            df = self.ds.verlauf(s, tag, tag, brutto)
            wert = float(df["wert"].iloc[0])
            kap = self.ds.kapazitaet(s, brutto)
            werte.append((s, wert, kap, float(df["lo80"].iloc[0]), float(df["hi80"].iloc[0]), float(df["gesichert"].iloc[0])))
        zeit = z.text if z.text in ("heute", "gestern", "morgen", "vorgestern", "übermorgen") else f"am {tag:%d.%m.%Y}"
        if zeit == "heute" and tag == self.ds.stichtag and self.ds.stichtag != date.today():
            zeit = f"am {tag:%d.%m.%Y} (letzter Datenstand)"
        bezug = "Brutto" if brutto else "Netto"

        if len(werte) == 1:
            s, wert, kap, lo, hi, gesichert = werte[0]
            ort = "insgesamt" if s == GESAMT else f"in {name(s)}"
            if modus == "frei":
                if not kap:
                    return self._ohne_kapazitaet(s)
                text = f"{zeit.capitalize() if zeit[0].islower() else zeit} sind {ort} **{zahl(max(kap - wert, 0))} Plätze frei** " \
                       f"({zahl(wert)} von {zahl(kap)} belegt, {bezug})."
            elif modus == "auslastung":
                if not kap:
                    return self._ohne_kapazitaet(s)
                stufe = ampel_stufe(wert / kap)[1]
                text = f"Auslastung {ort} {zeit}: **{prozent(wert / kap)}** ({zahl(wert)} von {zahl(kap)}, {bezug}) – {stufe}."
            else:
                text = f"Belegung {ort} {zeit}: **{zahl(wert)}**"
                text += f" von {zahl(kap)} Plätzen ({prozent(wert / kap)})." if kap else "."
            if zukunft:
                text += (f"\nDas ist eine **Prognose** (80 %-Spanne {zahl(lo)}–{zahl(hi)}); "
                         f"bereits gesichert laut Planung: {zahl(gesichert)}.")
            return Antwort(text, hinweis="Prognose" if zukunft else None,
                           vorschlaege=self._folge_vorschlaege(s, modus))

        kopf = ["Standort", "Belegt", "Kapazität", "Frei", "Auslastung"]
        zeilen = [[name(s), zahl(w), zahl(k) if k else "–", zahl(max(k - w, 0)) if k else "–",
                   prozent(w / k) if k else "–"] for s, w, k, *_ in werte]
        titel = {"frei": "Freie Plätze", "auslastung": "Auslastung"}.get(modus, "Belegung")
        text = f"**{titel} {zeit}** ({bezug}{', Prognose' if zukunft else ''}):"
        return Antwort(text, (kopf, zeilen), hinweis="Prognose" if zukunft else None)

    def _zeitraum(self, standorte: list[str], z: Zeitraum, brutto: bool, modus: str, aggregat: str | None) -> Antwort:
        von, bis = max(z.von, self.ds.erster_tag), z.bis
        if bis < von:
            return Antwort(f"Für {z.text} liegen keine Daten vor.", quelle="hinweis")
        zeilen, texte = [], []
        anteil_zukunft = 0.0
        for s in standorte:
            df = self.ds.verlauf(s, von, bis, brutto)
            anteil_zukunft = float((~df["ist"]).mean())
            w = df["wert"]
            kap = self.ds.kapazitaet(s, brutto)
            mittel, maxi, mini = float(w.mean()), float(w.max()), float(w.min())
            tag_max, tag_min = w.idxmax().date(), w.idxmin().date()
            zeilen.append([name(s), zahl(mittel), f"{zahl(maxi)} ({tag_max:%d.%m.})", f"{zahl(mini)} ({tag_min:%d.%m.})",
                           prozent(mittel / kap) if kap else "–", zahl(max(kap - mittel, 0)) if kap else "–"])
            texte.append((s, mittel, maxi, mini, tag_max, tag_min, kap, float(w.sum())))
        prognose_hinweis = ""
        if anteil_zukunft >= 1:
            prognose_hinweis = " – Prognose"
        elif anteil_zukunft > 0:
            prognose_hinweis = f" – Ist-Werte bis {self.ds.stichtag:%d.%m.%Y}, danach Prognose"
        zeitraum = f"{z.text}" + (f" ({von:%d.%m.%Y} – {bis:%d.%m.%Y})" if z.art in ("bereich", "woche") and z.text[0].isalpha() else "")

        if len(texte) == 1:
            s, mittel, maxi, mini, tmax, tmin, kap, summe = texte[0]
            ort = "insgesamt" if s == GESAMT else f"in {name(s)}"
            if anteil_zukunft >= 1:
                df = self.ds.verlauf(s, von, bis, brutto)
                text = (f"Prognose {ort} für {zeitraum}: **Ø {zahl(mittel)}** belegt "
                        f"(80 %-Spanne {zahl(float(df['lo80'].mean()))}–{zahl(float(df['hi80'].mean()))}"
                        + (f", {prozent(mittel / kap)} der Kapazität" if kap else "")
                        + f"); bereits gesichert laut Planung: {zahl(float(df['gesichert'].mean()))}.")
                return Antwort(text, hinweis="Prognose", vorschlaege=self._folge_vorschlaege(s, modus))
            if aggregat == "max":
                text = f"Höchste Belegung {ort} im Zeitraum {zeitraum}: **{zahl(maxi)}** am {tmax:%d.%m.%Y}."
            elif aggregat == "min":
                text = f"Niedrigste Belegung {ort} im Zeitraum {zeitraum}: **{zahl(mini)}** am {tmin:%d.%m.%Y}."
            elif modus == "frei" and kap:
                text = f"Im Zeitraum {zeitraum} waren {ort} im Schnitt **{zahl(max(kap - mittel, 0))} Plätze frei** " \
                       f"(Ø {zahl(mittel)} von {zahl(kap)} belegt; am vollsten am {tmax:%d.%m.%Y} mit {zahl(maxi)})."
            elif modus == "auslastung" and kap:
                text = f"Ø Auslastung {ort} im Zeitraum {zeitraum}: **{prozent(mittel / kap)}** " \
                       f"(Ø {zahl(mittel)} von {zahl(kap)}; Spitze {prozent(maxi / kap)} am {tmax:%d.%m.%Y})."
            else:
                text = (f"Belegung {ort} im Zeitraum {zeitraum}: **Ø {zahl(mittel)}**"
                        + (f" von {zahl(kap)} Plätzen ({prozent(mittel / kap)})" if kap else "")
                        + f".\nHöchstwert {zahl(maxi)} am {tmax:%d.%m.%Y}, Tiefstwert {zahl(mini)} am {tmin:%d.%m.%Y}; "
                        f"{zahl(summe)} Personentage.")
            if prognose_hinweis:
                text += f"\n({prognose_hinweis.strip(' –')})"
            return Antwort(text, hinweis="Prognose" if anteil_zukunft else None,
                           vorschlaege=self._folge_vorschlaege(s, modus))
        kopf = ["Standort", "Ø Belegt", "Höchstwert", "Tiefstwert", "Ø Auslastung", "Ø frei"]
        return Antwort(f"**Belegung {zeitraum}**{prognose_hinweis}:", (kopf, zeilen),
                       hinweis="Prognose" if anteil_zukunft else None)

    def _extrem(self, a: Anfrage) -> Antwort:
        if a.aggregat is None:
            a.aggregat = "max"
        if a.zeit is None:
            a.zeitraeume = [Zeitraum(self.ds.stichtag - timedelta(days=364), self.ds.stichtag, "bereich", "letzte 12 Monate")]
        standorte = standorte_fuer(a)
        return self._zeitraum(standorte, a.zeit, self._brutto(a), "belegung", a.aggregat)

    def _kapazitaet(self, a: Anfrage) -> Antwort:
        standorte = standorte_fuer(a, STANDORTE + [GESAMT])
        zeilen = [[name(s), zahl(self.ds.kapazitaet(s)) if self.ds.kapazitaet(s) else "–",
                   zahl(self.ds.kapazitaet(s, True)) if self.ds.kapazitaet(s, True) else "–"] for s in standorte]
        fehlend = [name(s) for s in standorte if s != GESAMT and not self.ds.hat_kapazitaet(s)]
        text = "**Hinterlegte Kapazitäten** (Netto = Reha & Verträge, Brutto = inkl. FRAI/Jugendhilfe/andere Bereiche):"
        if len(standorte) == 1:
            s = standorte[0]
            if not self.ds.kapazitaet(s):
                return self._ohne_kapazitaet(s)
            return Antwort(f"Kapazität {name(s)}: **{zahl(self.ds.kapazitaet(s))} Plätze netto**, "
                           f"{zahl(self.ds.kapazitaet(s, True))} brutto.")
        if fehlend:
            text += f"\nFür {', '.join(fehlend)} ist noch nichts hinterlegt (Daten → Kapazitäten)."
        return Antwort(text, (["Standort", "Netto", "Brutto"], zeilen))

    def _prognose(self, a: Anfrage) -> Antwort:
        if self.ds.prognose is None:
            return Antwort("Die Prognose wird noch berechnet – bitte gleich noch einmal fragen.", quelle="hinweis")
        brutto = self._brutto(a)
        standorte = standorte_fuer(a)
        z = a.zeit
        if z is None:
            start = date(self.ds.stichtag.year, self.ds.stichtag.month, 1)
            monate = [pd.Timestamp(start) + pd.DateOffset(months=i) for i in range(1, 7)]
        elif z.ist_tag:
            return self._tag(standorte, z, brutto, "belegung")
        else:
            monate = list(pd.date_range(date(z.von.year, z.von.month, 1), z.bis, freq="MS"))
        monate = [m.date() for m in monate][:24]
        if len(standorte) == 1:
            s = standorte[0]
            zeilen = []
            for m in monate:
                mp = self.ds.monatsprognose(s, m, brutto)
                if mp is None:
                    continue
                stufe = ampel_stufe(mp["anteil_hi80"])[1] if mp["kapazitaet"] else "–"
                zeilen.append([monat_text(m), zahl(mp["erwartet"]), f"{zahl(mp['lo80'])}–{zahl(mp['hi80'])}",
                               zahl(mp["gesichert"]) if mp["gesichert"] is not None else "–",
                               prozent(mp["anteil"]), stufe])
            if not zeilen:
                return Antwort(f"Für {z.text if z else 'diesen Zeitraum'} gibt es keine Prognose (Horizont: 3 Jahre).",
                               quelle="hinweis")
            ort = "insgesamt" if s == GESAMT else name(s)
            if len(zeilen) == 1:
                mp = self.ds.monatsprognose(s, monate[0], brutto)
                art = "Hochrechnung (laufender Monat)" if mp["art"] == "laufend" else "Prognose"
                if mp["art"] == "ist":
                    return Antwort(f"{monat_text(monate[0])} ist abgeschlossen: Ø **{zahl(mp['erwartet'])}** belegt "
                                   f"{'insgesamt' if s == GESAMT else 'in ' + name(s)}.")
                text = (f"{art} {ort} für {monat_text(monate[0])}: **Ø {zahl(mp['erwartet'])}** belegt "
                        f"(80 %-Spanne {zahl(mp['lo80'])}–{zahl(mp['hi80'])}, 95 %: {zahl(mp['lo95'])}–{zahl(mp['hi95'])}).")
                if mp["gesichert"] is not None:
                    text += f"\nBereits gesichert laut Planung: {zahl(mp['gesichert'])}."
                if mp["kapazitaet"]:
                    text += (f"\nBei {zahl(mp['kapazitaet'])} Plätzen entspricht das {prozent(mp['anteil'])} – "
                             f"im ungünstigen Fall {prozent(mp['anteil_hi80'])} ({ampel_stufe(mp['anteil_hi80'])[1]}).")
                return Antwort(text, hinweis="Prognose", vorschlaege=[f"Wie gut ist die Prognose für {ort}?"])
            return Antwort(f"**Prognose {ort}** ({'Brutto' if brutto else 'Netto'}, Ø belegte Plätze je Monat):",
                           (["Monat", "Erwartet", "80 %-Spanne", "Gesichert", "Auslastung", "Einschätzung"], zeilen),
                           hinweis="Prognose")
        # mehrere Standorte: ein Monat -> Tabelle je Standort; mehrere Monate -> nur erwartet
        kopf = ["Monat"] + [name(s) for s in standorte]
        zeilen = []
        for m in monate:
            zeile = [monat_text(m)]
            for s in standorte:
                mp = self.ds.monatsprognose(s, m, brutto)
                zeile.append(zahl(mp["erwartet"]) if mp else "–")
            zeilen.append(zeile)
        return Antwort("**Prognose je Standort** (Ø belegte Plätze):", (kopf, zeilen), hinweis="Prognose")

    def _bestand(self, a: Anfrage) -> Antwort:
        if a.zeit is None or a.zeit.ist_tag and a.zeit.von <= self.ds.stichtag:
            n = date(self.ds.stichtag.year, self.ds.stichtag.month, 1)
            a.zeitraeume = [monat_zeitraum((n + timedelta(days=40)).year, (n + timedelta(days=40)).month)]
        z = a.zeit
        standorte = standorte_fuer(a, STANDORTE + [GESAMT])
        zeilen = []
        for s in standorte:
            df = self.ds.verlauf(s, max(z.von, self.ds.stichtag + timedelta(days=1)), max(z.bis, self.ds.stichtag + timedelta(days=1)))
            zeilen.append([name(s), zahl(float(df["gesichert"].mean())), zahl(float(df["wert"].mean()))])
        return Antwort(f"**Gesicherter Bestand {z.text}** – Teilnehmende mit geplantem Verbleib plus Verträge, "
                       "ohne künftige Neuaufnahmen; daneben die Prognose inkl. erwarteter Neuaufnahmen:",
                       (["Standort", "Ø gesichert", "Ø Prognose"], zeilen))

    def _personentage(self, a: Anfrage) -> Antwort:
        z = a.zeit or monat_zeitraum(self.ds.stichtag.year, self.ds.stichtag.month)
        if z.ist_tag:
            z = monat_zeitraum(z.von.year, z.von.month)
        standorte = standorte_fuer(a)
        zeilen = []
        for s in standorte:
            df = self.ds.verlauf(s, max(z.von, self.ds.erster_tag), z.bis, self._brutto(a))
            zeilen.append([name(s), zahl(float(df["wert"].sum())), zahl(float(df["wert"].mean()))])
        if len(zeilen) == 1:
            return Antwort(f"Personentage {'insgesamt' if standorte[0] == GESAMT else name(standorte[0])} im Zeitraum "
                           f"{z.text}: **{zeilen[0][1]}** (Ø {zeilen[0][2]} pro Tag).")
        return Antwort(f"**Personentage {z.text}:**", (["Standort", "Personentage", "Ø pro Tag"], zeilen))

    def _trend(self, a: Anfrage) -> Antwort:
        standorte = standorte_fuer(a, STANDORTE + [GESAMT])
        st = self.ds.stichtag
        if a.zeit and not a.zeit.ist_tag:
            von, bis = a.zeit.von, min(a.zeit.bis, st)
        else:
            von, bis = st - timedelta(days=89), st
        laenge = (bis - von).days + 1
        vj_von, vj_bis = von - timedelta(days=364), bis - timedelta(days=364)
        vor_von, vor_bis = von - timedelta(days=laenge), von - timedelta(days=1)
        zeilen, saetze = [], []
        for s in standorte:
            jetzt = float(self.ds.belegung(s, von, bis).mean())
            vorher = float(self.ds.belegung(s, max(vor_von, self.ds.erster_tag), vor_bis).mean()) if vor_bis >= self.ds.erster_tag else None
            vorjahr = float(self.ds.belegung(s, max(vj_von, self.ds.erster_tag), vj_bis).mean()) if vj_bis >= self.ds.erster_tag else None
            d_vor = jetzt - vorher if vorher else None
            d_vj = jetzt - vorjahr if vorjahr else None
            zeilen.append([name(s), zahl(jetzt), _delta(d_vor, vorher), _delta(d_vj, vorjahr)])
            if d_vj is not None:
                richtung = "mehr" if d_vj > 0 else "weniger"
                saetze.append(f"{name(s)}: {zahl(abs(d_vj))} {richtung} als im Vorjahreszeitraum")
        text = (f"**Entwicklung {von:%d.%m.%Y} – {bis:%d.%m.%Y}** (Ø Belegung) im Vergleich zum Zeitraum davor "
                f"und zum gleichen Zeitraum im Vorjahr:")
        if len(standorte) == 1 and saetze:
            text += "\n" + saetze[0] + "."
        return Antwort(text, (["Standort", "Ø Belegung", "ggü. davor", "ggü. Vorjahr"], zeilen))

    def _vergleich(self, a: Anfrage) -> Antwort:
        if len(a.zeitraeume) >= 2:
            standorte = standorte_fuer(a)
            kopf = ["Zeitraum"] + [name(s) for s in standorte]
            zeilen = []
            for z in a.zeitraeume[:4]:
                zeile = [z.text]
                for s in standorte:
                    df = self.ds.verlauf(s, max(z.von, self.ds.erster_tag), max(z.bis, self.ds.erster_tag), self._brutto(a))
                    zeile.append(zahl(float(df["wert"].mean())))
                zeilen.append(zeile)
            return Antwort("**Vergleich** (Ø Belegung):", (kopf, zeilen))
        a.alle_standorte = a.alle_standorte or len(a.standorte) < 2
        if a.standorte and len(a.standorte) >= 2:
            a.alle_standorte = False
        return self._belegung(a)

    def _anreisen(self, a: Anfrage) -> Antwort:
        if not self.ds.importe.get("anreisen") and not self.ds.eintraege_von(kategorie="Anreise"):
            return Antwort("Es sind noch keine Anreisen importiert. Unter **Daten → Anreisen** lässt sich die "
                           "Excel-Liste hochladen.", quelle="hinweis")
        z = a.zeit or Zeitraum(self.heute, self.heute + timedelta(days=27), "bereich", "nächste 4 Wochen")
        standort = (a.standorte or [GESAMT])[0] if not a.alle_standorte else GESAMT
        liste = self.ds.anreisen(standort, z.von, z.bis)
        je = {s: sum(e.anzahl for e in liste if e.standort == s) for s in STANDORTE}
        gesamt = sum(je.values())
        ort = "" if standort == GESAMT else f" in {name(standort)}"
        if not liste:
            return Antwort(f"Keine geplanten Anreisen{ort} im Zeitraum {z.text}.")
        text = f"**{zahl(gesamt)} geplante Anreisen**{ort} im Zeitraum {z.text}"
        if standort == GESAMT:
            text += " (" + ", ".join(f"{name(s)} {je[s]}" for s in STANDORTE if je[s]) + ")"
        zeilen = [[e.von.strftime("%d.%m.%Y"), name(e.standort), str(e.anzahl), e.bezeichnung or "–",
                   e.bis.strftime("%d.%m.%Y") if not e.nur_termin else "–"] for e in liste[:25]]
        if len(liste) > 25:
            text += f". Die ersten 25 von {len(liste)}:"
        else:
            text += ":"
        return Antwort(text, (["Anreise", "Standort", "Anzahl", "Bezeichnung", "Abreise"], zeilen))

    def _mieter(self, a: Anfrage, kategorie: str = "Mieter") -> Antwort:
        tag = a.zeit.von if a.zeit else self.ds.stichtag
        standort = GESAMT if a.alle_standorte or not a.standorte else a.standorte[0]
        aktiv = self.ds.aktive(kategorie, standort, tag)
        wort = "Mieter" if kategorie == "Mieter" else "Gäste"
        ort = "" if standort == GESAMT else f" in {name(standort)}"
        if not aktiv:
            return Antwort(f"Am {tag:%d.%m.%Y} sind keine {wort}{ort} erfasst.")
        summe = sum(e.anzahl for e in aktiv)
        zeilen = [[e.bezeichnung or "–", name(e.standort), str(e.anzahl), e.von.strftime("%d.%m.%Y"),
                   "offen" if e.bis.year >= 2099 else e.bis.strftime("%d.%m.%Y")] for e in aktiv[:30]]
        return Antwort(f"Am {tag:%d.%m.%Y} belegen {wort}{ort} **{zahl(summe)} Plätze** ({len(aktiv)} Einträge):",
                       (["Bezeichnung", "Standort", "Plätze", "Von", "Bis"], zeilen))

    def _gaeste(self, a: Anfrage) -> Antwort:
        return self._mieter(a, "Gäste")

    def _haeuser(self, a: Anfrage) -> Antwort:
        tag = a.zeit.von if a.zeit else self.ds.stichtag
        if tag > self.ds.letzter_tag or tag < self.ds.erster_tag:
            return Antwort(f"Für den {tag:%d.%m.%Y} gibt es keine Hausdaten.", quelle="hinweis")
        standort = GESAMT if a.alle_standorte or not a.standorte else a.standorte[0]
        haeuser = self.ds.haeuser_am(standort, tag)
        zukunft = " (gesichert laut Planung)" if tag > self.ds.stichtag else ""
        zeilen = [[h, name(self.ds.pivot.haus_standort[h]), zahl(w)] for h, w in haeuser]
        return Antwort(f"**Belegung je Haus am {tag:%d.%m.%Y}**{zukunft}:", (["Haus", "Standort", "Belegt"], zeilen))

    def _modell(self, a: Anfrage) -> Antwort:
        if self.ds.prognose is None:
            return Antwort("Die Prognose wird noch berechnet.", quelle="hinweis")
        standorte = standorte_fuer(a, STANDORTE + [GESAMT])
        zeilen = []
        for s in standorte:
            m = self.ds.prognose.modelle.get(s)
            if not m:
                continue
            zeilen.append([name(s), m.name, zahl(m.mae_1m, 1) if m.mae_1m is not None else "–",
                           zahl(m.mae, 1) if m.mae is not None else "–", prozent(m.abdeckung80)])
        return Antwort(
            "**So gut hat die Prognose in der Vergangenheit getroffen** – gemessen im Backtest: Das Modell wurde "
            "für jeden der letzten 18 Monate nur mit den Daten gerechnet, die damals vorlagen, und dann mit dem "
            "tatsächlichen Wert verglichen. Fehler = Ø Abweichung in Personen (Monatsmittel).",
            (["Standort", "Gewähltes Modell", "Fehler 1 Monat", "Fehler bis 12 Monate", "Treffer 80 %-Band"], zeilen),
        )

    # ---- Hilfen ------------------------------------------------------------------------

    def _ohne_kapazitaet(self, s: str) -> Antwort:
        return Antwort(f"Für {name(s)} ist keine Kapazität hinterlegt – deshalb kann ich Auslastung und freie "
                       "Plätze nicht berechnen. Unter **Daten → Kapazitäten** lässt sie sich eintragen.",
                       quelle="hinweis")

    def _kapazitaetsrisiken(self, brutto: bool) -> list[str]:
        if self.ds.prognose is None:
            return []
        risiken = []
        start = date(self.ds.stichtag.year, self.ds.stichtag.month, 1)
        for s in STANDORTE:
            if not self.ds.hat_kapazitaet(s):
                continue
            for i in range(1, 13):
                m = (pd.Timestamp(start) + pd.DateOffset(months=i)).date()
                mp = self.ds.monatsprognose(s, m, brutto)
                if mp and mp["anteil_hi80"] and mp["anteil_hi80"] > 1:
                    risiken.append(f"{name(s)} könnte ab {monat_text(m)} über die Kapazität kommen")
                    break
        return risiken

    def _folge_vorschlaege(self, s: str, modus: str) -> list[str]:
        andere = [name(x) for x in STANDORTE if x != s][:2]
        v = [f"und {andere[0]}?"] if andere else []
        if modus != "frei":
            v.append("Wie viele Plätze sind frei?")
        v.append("Prognose für die nächsten 6 Monate")
        return v


def _delta(d: float | None, basis: float | None) -> str:
    if d is None or not basis:
        return "–"
    vz = "+" if d > 0 else ("−" if d < 0 else "±")
    return f"{vz}{zahl(abs(d))} ({vz}{zahl(abs(d) / basis * 100)} %)"
