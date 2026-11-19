"""1.28 – QR-Codes: jeder erzeugte Code wird mit einem UNABHÄNGIGEN Decoder zurückgelesen (eigene GF-Rechnung,
eigene Funktionsflächen, eigenes Zickzack-Lesen) und gegen veröffentlichte Referenzwerte geprüft."""

import pytest

from modern import qr_kern as q

# Referenzwerte (ISO 18004 / verbreitete Tabellen): Formatbits Stufe M, Masken 0–7, höchstes Bit zuerst
FORMAT_M = ["101010000010010", "101000100100101", "101111001111100", "101101101001011",
            "100010111111001", "100000011001110", "100111110010111", "100101010100000"]


def _gf_mal(a, b):                       # Bitweise (ohne Tabellen) – unabhängig vom Erzeuger
    r = 0
    while b:
        if b & 1:
            r ^= a
        a <<= 1
        if a & 0x100:
            a ^= 0x11D
        b >>= 1
    return r


def _gf_pot(e):
    r = 1
    for _ in range(e):
        r = _gf_mal(r, 2)
    return r


def _funktion(n, v):
    f = [[False] * n for _ in range(n)]
    for y in range(n):
        for x in range(n):
            if (x < 9 and y < 9) or (x >= n - 8 and y < 9) or (x < 9 and y >= n - 8) or x == 6 or y == 6:
                f[y][x] = True
            if v >= 7 and ((n - 11 <= x <= n - 9 and y < 6) or (n - 11 <= y <= n - 9 and x < 6)):
                f[y][x] = True
    pos = q.AUSRICHTUNG[v]
    for a in pos:
        for b in pos:
            if (a < 9 and b < 9) or (a > n - 9 and b < 9) or (a < 9 and b > n - 9):   # Ecke mit Suchmuster
                continue
            for dy in range(-2, 3):
                for dx in range(-2, 3):
                    f[b + dy][a + dx] = True
    return f


def decodieren(m):
    n = len(m)
    v = (n - 17) // 4
    assert n == 17 + 4 * v and 1 <= v <= 20
    # Format, beide Kopien
    a = [m[i][8] for i in range(6)] + [m[7][8], m[8][8], m[8][7]] + [m[8][14 - i] for i in range(9, 15)]
    b = [m[8][n - 1 - i] for i in range(8)] + [m[n - 15 + i][8] for i in range(8, 15)]
    assert a == b, "Formatkopien verschieden"
    text = "".join("1" if a[i] else "0" for i in range(14, -1, -1))
    assert text in FORMAT_M, f"ungültige Formatbits {text}"
    maske = FORMAT_M.index(text)
    assert m[n - 8][8] is True                               # dunkles Modul
    f = _funktion(n, v)
    bits = []
    spalte, hoch = n - 1, True
    while spalte > 0:
        if spalte == 6:
            spalte -= 1
        zeilen = range(n - 1, -1, -1) if hoch else range(n)
        for i in zeilen:
            for j in (spalte, spalte - 1):
                if not f[i][j]:
                    regel = [(i + j) % 2 == 0, i % 2 == 0, j % 3 == 0, (i + j) % 3 == 0,
                             (i // 2 + j // 3) % 2 == 0, (i * j) % 2 + (i * j) % 3 == 0,
                             ((i * j) % 2 + (i * j) % 3) % 2 == 0, ((i + j) % 2 + (i * j) % 3) % 2 == 0][maske]
                    bits.append(m[i][j] ^ regel)
        spalte -= 2
        hoch = not hoch
    n_ecc, gruppen = q.BLOECKE_M[v]
    laengen = [d for anz, d in gruppen for _ in range(anz)]
    gesamt = sum(laengen) + n_ecc * len(laengen)
    assert len(bits) // 8 == gesamt, f"Tabelle passt nicht zur Version {v}: {len(bits) // 8} ≠ {gesamt}"
    cw = [int("".join("1" if x else "0" for x in bits[k * 8:k * 8 + 8]), 2) for k in range(gesamt)]
    bloecke = [[] for _ in laengen]
    k = 0
    for i in range(max(laengen)):
        for bl, ln in zip(bloecke, laengen):
            if i < ln:
                bl.append(cw[k])
                k += 1
    pruef = [[] for _ in laengen]
    for _ in range(n_ecc):
        for p in pruef:
            p.append(cw[k])
            k += 1
    for d, p in zip(bloecke, pruef):                          # Syndrome müssen 0 sein
        poly = d + p
        for i in range(n_ecc):
            x, s = _gf_pot(i), 0
            for c in poly:
                s = _gf_mal(s, x) ^ c
            assert s == 0, "Reed-Solomon-Prüfsumme falsch"
    daten = [c for bl in bloecke for c in bl]
    strom = "".join(f"{c:08b}" for c in daten)
    assert strom[:4] == "0100"
    zb = 8 if v <= 9 else 16
    laenge = int(strom[4:4 + zb], 2)
    roh = bytes(int(strom[4 + zb + 8 * i:12 + zb + 8 * i], 2) for i in range(laenge))
    return roh.decode("utf-8")


def test_reed_solomon_referenz():
    daten = [32, 91, 11, 120, 209, 114, 220, 77, 67, 64, 236, 17, 236, 17, 236, 17]      # „HELLO WORLD“ 1-M
    assert q.rs_pruefbytes(daten, 10) == [196, 35, 39, 119, 235, 215, 231, 226, 93, 23]


def test_format_und_versionsbits_referenz():
    assert [f"{q.format_bits(k):015b}" for k in range(8)] == FORMAT_M
    assert q.version_bits(7) == 0x07C94 and q.version_bits(10) == 0x0A4D3


def test_bloecke_passen_zur_modulzahl():
    for v in range(1, 21):
        n = 17 + 4 * v
        f = _funktion(n, v)
        frei = sum(not x for z in f for x in z) // 8
        n_ecc, gruppen = q.BLOECKE_M[v]
        assert frei == sum(a * (d + n_ecc) for a, d in gruppen), v


@pytest.mark.parametrize("text", [
    "A", "2-408", "https://forms.office.com/Pages/ResponsePage.aspx?id=AbCdEf123&r1a2b3c=%222-408%22",
    "Zimmer 3.2-111 – Heizung, Öl & Ümlaute ✓", "x" * 150, "https://example.invalid/" + "q" * 400,
])
def test_rueckwaerts_lesen(text):
    assert decodieren(q.matrix(text)) == text


@pytest.mark.parametrize("maske", range(8))
def test_jede_maske_lesbar(maske):
    t = "https://forms.office.com/r/Beispiel?zimmer=2-408"
    assert decodieren(q.matrix(t, maske=maske)) == t


def test_alle_versionen_1_bis_20():
    for v in range(1, 21):
        t = "z" * q.kapazitaet(v)
        m = q.matrix(t)
        assert len(m) == 17 + 4 * v and decodieren(m) == t


def test_zu_lang_und_svg():
    with pytest.raises(ValueError, match="zu lang"):
        q.matrix("x" * 700)
    s = q.svg("2-408")
    assert s.startswith("<svg") and "crispEdges" in s and 'viewBox="0 0 29 29"' in s
