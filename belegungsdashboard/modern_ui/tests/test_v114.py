"""1.14 – Rechenkern Steuerung: Kostenspanne mit gemeinsamem Preisfaktor, Rangfolge A vor B vor C, Szenario auch auf
die Pipeline, defekte Betten in der Engpassprüfung, Abgleich Betten- gegen Teilnehmerprognose."""

import inspect
from datetime import date
from types import SimpleNamespace as NS

import pytest

from modern import renovierung_kern as rk
from modern import steuerung_kern as sk


def _k(u):
    k = rk.Kosten(1, 2027, bau=u * 10, herkunft_bau="angebot", herkunft_moebel="angebot")
    return k._unsicherheit()


def test_spanne_einzeln_unveraendert_zusammen_zwischen_quadratisch_und_linear():
    a = _k(1000)
    assert a.spanne[1] - a.summe == pytest.approx(a.u_bau)            # eine Position: genau ihre Spanne
    s = a.plus(_k(1000)).plus(_k(1000)).plus(_k(1000))
    lin, quad = 4 * a.u_bau, 2 * a.u_bau
    assert quad < s.spanne[1] - s.summe < lin
    r = rk.KOSTEN_GEMEINSAM                                            # Formel: (Σρu)² + Σ(1−ρ²)u²
    assert s.spanne[1] - s.summe == pytest.approx(((4 * r * a.u_bau) ** 2 + 4 * (1 - r * r) * a.u_bau ** 2) ** .5)


def test_rangfolge_a_vor_b_vor_c():
    def fz(bau, n, moebel=None, frisch=False):
        f = NS(bedarfe={})
        zs = []
        for i in range(n):
            z = NS(id=f"{bau}{moebel}{i}")
            f.bedarfe[z.id] = rk.ZBedarf(bau=bau, moebel=moebel, frisch=frisch)
            zs.append((f, z, "zimmer"))
        return zs
    ein_a, elf_b = fz("A", 1), fz("B", 11)
    assert rk.klassen_zahl(ein_a) > rk.klassen_zahl(elf_b)            # 1 × A schlägt 11 × B (vorher 100 < 110)
    assert rk.klassen_zahl(fz("A", 2, frisch=True)) == (0, 0, 0)       # frisch renoviert: kein Bau-Bedarf
    m = [(f, z, "moebel") for f, z, _a in fz("B", 2, "A")]
    assert rk.klassen_zahl(m, "bau") == (0, 0, 0) and rk.klassen_zahl(m, "moebel") == (2, 0, 0)
    assert rk.klassen_zahl(fz("B", 1, "A"), "moebel") == (1, 0, 0)     # „Zimmer komplett“ bringt auch Möbel mit


def test_kandidaten_erst_klasse_dann_preis():
    q = inspect.getsource(rk._zimmer_kandidaten)
    assert "_rang(b, art)" in q and "-x[0][0]" in q


def test_szenario_wirkt_auf_pipeline():
    from modern import bestand_prognose as bp

    q = inspect.getsource(bp.simulieren)
    assert "u.quote * faktor" in q
    assert q.index("faktor = max(0.0, 1 + faktor_prozent / 100)") < q.index("def folgen(")


def test_defekte_betten_senken_die_engpassgrenze():
    fe = NS(prognose=(90, 85, 95), start=date(2027, 3, 1), engpass=False)
    f = NS(betten=10)
    rk.engpass_markieren([fe], f, 112, [], defekt=0)
    assert not fe.engpass                                              # 95 < (112 − 10) · 0,95
    rk.engpass_markieren([fe], f, 112, [], defekt=5)
    assert fe.engpass                                                  # 95 ≥ (112 − 15) · 0,95
    st = NS(zimmer=[NS(id="a", aktiv=True, betten=2), NS(id="b", aktiv=True, betten=1), NS(id="c", aktiv=False, betten=3)],
            lage=NS(unbewohnbar={"a", "b", "c"}))
    assert rk.defekte_betten(st) == 3 and rk.defekte_betten(st, {"a"}) == 1


def test_abgleich_der_prognosen():
    B = lambda m, w, lo, hi, art="prognose": NS(monat=date(2027, m, 1), art=art, erwartet=w, lo80=lo, hi80=hi)  # noqa: E731
    M = lambda m, s, art="prognose": NS(monat=date(2027, m, 1), art=art, summe=s)                             # noqa: E731
    z = sk.prognosen_abgleich([B(1, 60, 50, 70, "ist"), B(2, 60, 50, 70), B(3, 60, 59, 61), B(4, 60, 50, 70)],
                              [M(2, 64), M(3, 75), M(4, 59)])
    assert [x.monat.month for x in z] == [2, 3, 4]                       # Ist-Monate zählen nicht
    assert [x.auffaellig for x in z] == [False, True, False]            # März: 15 > max(1, 6, 2)
    assert sk.abgleich_schwelle(60, 59, 61) == 6.0                       # schmale Spanne: mindestens 10 %
    assert "Mär 2027" in sk.abgleich_satz(z) and "15 Plätze mehr" in sk.abgleich_satz(z)
    assert sk.abgleich_satz(z[:1]) == ""
