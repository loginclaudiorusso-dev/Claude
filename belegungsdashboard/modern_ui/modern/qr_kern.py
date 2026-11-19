"""1.28: QR-Codes erzeugen – rein, ohne Zusatzpaket (nur Standardbibliothek).

Modell 2 nach ISO/IEC 18004, Byte-Modus (UTF-8), Fehlerkorrektur M (15 % – ein verschmiertes oder leicht
beschädigtes Etikett bleibt lesbar), Versionen 1–20 (bis 666 Byte, reicht für lange Forms-Links). Die Maske wird wie
vorgeschrieben nach dem kleinsten Strafwert gewählt. Ausgabe: Matrix (True = dunkel) oder fertiges SVG.

Aufbau nach dem bekannten Verfahren (Funktionsmuster → Format/Version → Datenbits im Zickzack → Maske); die Tests
lesen jeden Code mit einem unabhängigen Decoder zurück und prüfen die Reed-Solomon-Prüfsummen.
"""

from __future__ import annotations

# Fehlerkorrektur M je Version: (Prüfbytes je Block, [(Anzahl Blöcke, Datenbytes je Block), ...])
BLOECKE_M: dict[int, tuple[int, list[tuple[int, int]]]] = {
    1: (10, [(1, 16)]), 2: (16, [(1, 28)]), 3: (26, [(1, 44)]), 4: (18, [(2, 32)]), 5: (24, [(2, 43)]),
    6: (16, [(4, 27)]), 7: (18, [(4, 31)]), 8: (22, [(2, 38), (2, 39)]), 9: (22, [(3, 36), (2, 37)]),
    10: (26, [(4, 43), (1, 44)]), 11: (30, [(1, 50), (4, 51)]), 12: (22, [(6, 36), (2, 37)]),
    13: (22, [(8, 37), (1, 38)]), 14: (24, [(4, 40), (5, 41)]), 15: (24, [(5, 41), (5, 42)]),
    16: (28, [(7, 45), (3, 46)]), 17: (28, [(10, 46), (1, 47)]), 18: (26, [(9, 43), (4, 44)]),
    19: (26, [(3, 44), (11, 45)]), 20: (26, [(3, 41), (13, 42)]),
}
AUSRICHTUNG = {1: [], 2: [6, 18], 3: [6, 22], 4: [6, 26], 5: [6, 30], 6: [6, 34], 7: [6, 22, 38], 8: [6, 24, 42],
               9: [6, 26, 46], 10: [6, 28, 50], 11: [6, 30, 54], 12: [6, 32, 58], 13: [6, 34, 62],
               14: [6, 26, 46, 66], 15: [6, 26, 48, 70], 16: [6, 26, 50, 74], 17: [6, 30, 54, 78],
               18: [6, 30, 56, 82], 19: [6, 30, 58, 86], 20: [6, 34, 62, 90]}
STUFE_M = 0                     # Formatbits der Stufe M (L = 1, M = 0, Q = 3, H = 2)
MAX_VERSION = 20

# ---- Galois-Feld GF(256), Polynom x⁸ + x⁴ + x³ + x² + 1 --------------------------------------------------------
_EXP = [0] * 512
_LOG = [0] * 256
_x = 1
for _i in range(255):
    _EXP[_i] = _x
    _LOG[_x] = _i
    _x <<= 1
    if _x & 0x100:
        _x ^= 0x11D
for _i in range(255, 512):
    _EXP[_i] = _EXP[_i - 255]


def _mal(a: int, b: int) -> int:
    return 0 if a == 0 or b == 0 else _EXP[_LOG[a] + _LOG[b]]


def _generator(n: int) -> list[int]:
    g = [1]
    for i in range(n):
        neu = [0] * (len(g) + 1)
        for j, k in enumerate(g):
            neu[j] ^= k
            neu[j + 1] ^= _mal(k, _EXP[i])
        g = neu
    return g


def rs_pruefbytes(daten: list[int], n: int) -> list[int]:
    """Reed-Solomon: ``n`` Prüfbytes zu ``daten`` (Polynomdivision durch das Generatorpolynom)."""
    g = _generator(n)
    rest = list(daten) + [0] * n
    for i in range(len(daten)):
        f = rest[i]
        if f:
            for j in range(1, len(g)):
                rest[i + j] ^= _mal(g[j], f)
    return rest[len(daten):]


# ---- Kapazität und Daten ---------------------------------------------------------------------------------------

def datenbytes(version: int) -> int:
    return sum(a * d for a, d in BLOECKE_M[version][1])


def _zaehlbits(version: int) -> int:
    return 8 if version <= 9 else 16


def kapazitaet(version: int) -> int:
    """So viele Bytes Text passen in diese Version (Stufe M)."""
    return (datenbytes(version) * 8 - 4 - _zaehlbits(version)) // 8


def version_fuer(n: int) -> int:
    for v in range(1, MAX_VERSION + 1):
        if kapazitaet(v) >= n:
            return v
    raise ValueError(f"Der Text ist zu lang für einen QR-Code ({n} Byte, höchstens {kapazitaet(MAX_VERSION)}).")


def _codewoerter(text: str, version: int) -> list[int]:
    roh = text.encode("utf-8")
    bits: list[int] = []

    def anhaengen(wert: int, laenge: int) -> None:
        bits.extend((wert >> (laenge - 1 - i)) & 1 for i in range(laenge))
    anhaengen(0b0100, 4)                                    # Byte-Modus
    anhaengen(len(roh), _zaehlbits(version))
    for b in roh:
        anhaengen(b, 8)
    voll = datenbytes(version) * 8
    anhaengen(0, min(4, voll - len(bits)))                  # Endmarke
    bits.extend([0] * (-len(bits) % 8))
    daten = [int("".join(map(str, bits[i:i + 8])), 2) for i in range(0, len(bits), 8)]
    fuell = (0xEC, 0x11)                                    # Füllbytes abwechselnd
    i = 0
    while len(daten) < datenbytes(version):
        daten.append(fuell[i % 2])
        i += 1
    # Blöcke bilden, Prüfbytes anhängen, verschränken
    n_ecc, gruppen = BLOECKE_M[version]
    bloecke, pos = [], 0
    for anzahl, laenge in gruppen:
        for _ in range(anzahl):
            bloecke.append(daten[pos:pos + laenge])
            pos += laenge
    pruef = [rs_pruefbytes(b, n_ecc) for b in bloecke]
    erg = [b[i] for i in range(max(len(b) for b in bloecke)) for b in bloecke if i < len(b)]
    erg += [p[i] for i in range(n_ecc) for p in pruef]
    return erg


# ---- Matrix --------------------------------------------------------------------------------------------------

def format_bits(maske: int) -> int:
    """15 Formatbits (Stufe M, Maske) mit BCH-Prüfteil und der festen Maske 0x5412."""
    d = (STUFE_M << 3) | maske
    rest = d
    for _ in range(10):
        rest = (rest << 1) ^ ((rest >> 9) * 0x537)
    return ((d << 10) | rest) ^ 0x5412


def version_bits(version: int) -> int:
    rest = version
    for _ in range(12):
        rest = (rest << 1) ^ ((rest >> 11) * 0x1F25)
    return (version << 12) | rest


MASKEN = [
    lambda x, y: (x + y) % 2 == 0,
    lambda x, y: y % 2 == 0,
    lambda x, y: x % 3 == 0,
    lambda x, y: (x + y) % 3 == 0,
    lambda x, y: (x // 3 + y // 2) % 2 == 0,
    lambda x, y: x * y % 2 + x * y % 3 == 0,
    lambda x, y: (x * y % 2 + x * y % 3) % 2 == 0,
    lambda x, y: ((x + y) % 2 + x * y % 3) % 2 == 0,
]


class _Matrix:
    def __init__(self, version: int):
        self.v = version
        self.n = 17 + 4 * version
        self.m = [[False] * self.n for _ in range(self.n)]       # m[y][x]
        self.fest = [[False] * self.n for _ in range(self.n)]

    def modul(self, x: int, y: int, dunkel: bool) -> None:
        self.m[y][x] = dunkel
        self.fest[y][x] = True

    def funktionsmuster(self) -> None:
        n = self.n
        for i in range(n):                                       # Taktlinien
            self.modul(6, i, i % 2 == 0)
            self.modul(i, 6, i % 2 == 0)
        for cx, cy in ((3, 3), (n - 4, 3), (3, n - 4)):          # Suchmuster mit hellem Rand
            for dy in range(-4, 5):
                for dx in range(-4, 5):
                    x, y = cx + dx, cy + dy
                    if 0 <= x < n and 0 <= y < n:
                        d = max(abs(dx), abs(dy))
                        self.modul(x, y, d not in (2, 4))
        pos = AUSRICHTUNG[self.v]                                # Ausrichtungsmuster
        for i, a in enumerate(pos):
            for j, b in enumerate(pos):
                if (i == 0 and j == 0) or (i == 0 and j == len(pos) - 1) or (i == len(pos) - 1 and j == 0):
                    continue
                for dy in range(-2, 3):
                    for dx in range(-2, 3):
                        self.modul(a + dx, b + dy, max(abs(dx), abs(dy)) != 1)
        self.format_setzen(0)                                    # Platz reservieren (wird später richtig gesetzt)
        if self.v >= 7:
            bits = version_bits(self.v)
            for i in range(18):
                b = (bits >> i) & 1 == 1
                a, c = n - 11 + i % 3, i // 3
                self.modul(a, c, b)
                self.modul(c, a, b)

    def format_setzen(self, maske: int) -> None:
        n, bits = self.n, format_bits(maske)

        def bit(i: int) -> bool:
            return (bits >> i) & 1 == 1
        for i in range(6):
            self.modul(8, i, bit(i))
        self.modul(8, 7, bit(6))
        self.modul(8, 8, bit(7))
        self.modul(7, 8, bit(8))
        for i in range(9, 15):
            self.modul(14 - i, 8, bit(i))
        for i in range(8):
            self.modul(n - 1 - i, 8, bit(i))
        for i in range(8, 15):
            self.modul(8, n - 15 + i, bit(i))
        self.modul(8, n - 8, True)                              # immer dunkles Modul

    def daten(self, codewoerter: list[int]) -> None:
        n, i, gesamt = self.n, 0, len(codewoerter) * 8
        rechts = n - 1
        while rechts >= 1:
            if rechts == 6:
                rechts = 5
            for vert in range(n):
                for j in range(2):
                    x = rechts - j
                    hoch = ((rechts + 1) & 2) == 0
                    y = n - 1 - vert if hoch else vert
                    if not self.fest[y][x]:
                        if i < gesamt:
                            self.m[y][x] = (codewoerter[i >> 3] >> (7 - (i & 7))) & 1 == 1
                        i += 1                                   # Restbits bleiben hell
            rechts -= 2

    def maskieren(self, maske: int) -> None:
        f = MASKEN[maske]
        for y in range(self.n):
            for x in range(self.n):
                if not self.fest[y][x] and f(x, y):
                    self.m[y][x] = not self.m[y][x]


def _strafe(m: list[list[bool]]) -> int:
    n, s = len(m), 0
    zeilen = m + [[m[y][x] for y in range(n)] for x in range(n)]
    muster = ([True, False, True, True, True, False, True, False, False, False, False],
              [False, False, False, False, True, False, True, True, True, False, True])
    for z in zeilen:
        lauf = 1
        for i in range(1, n + 1):
            if i < n and z[i] == z[i - 1]:
                lauf += 1
            else:
                if lauf >= 5:
                    s += 3 + lauf - 5
                lauf = 1
        for i in range(n - 10):
            if z[i:i + 11] in muster:
                s += 40
    for y in range(n - 1):
        for x in range(n - 1):
            if m[y][x] == m[y][x + 1] == m[y + 1][x] == m[y + 1][x + 1]:
                s += 3
    dunkel = sum(map(sum, m))
    k = (abs(dunkel * 20 - n * n * 10) + n * n - 1) // (n * n) - 1
    return s + 10 * max(0, k)


def matrix(text: str, maske: int | None = None) -> list[list[bool]]:
    """QR-Code für ``text`` als Matrix [Zeile][Spalte], True = dunkel (ohne Ruhezone)."""
    version = version_fuer(len(text.encode("utf-8")))
    cw = _codewoerter(text, version)
    beste = None
    for mk in ([maske] if maske is not None else range(8)):
        q = _Matrix(version)
        q.funktionsmuster()
        q.daten(cw)
        q.maskieren(mk)
        q.format_setzen(mk)
        wert = _strafe(q.m)
        if beste is None or wert < beste[0]:
            beste = (wert, q.m)
    return beste[1]


def svg(text: str, modul: float = 4.0, rand: int = 4, farbe: str = "#000") -> str:
    """Fertiges SVG (eine Pfadfläche, gestochen scharf beim Drucken), Ruhezone ``rand`` Module (Norm: 4)."""
    m = matrix(text)
    n = len(m)
    groesse = (n + 2 * rand) * modul
    pfad = "".join(f"M{x + rand},{y + rand}h1v1h-1z" for y in range(n) for x in range(n) if m[y][x])
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{groesse:g}" height="{groesse:g}" '
            f'viewBox="0 0 {n + 2 * rand} {n + 2 * rand}" shape-rendering="crispEdges" role="img">'
            f'<rect width="100%" height="100%" fill="#fff"/><path fill="{farbe}" d="{pfad}"/></svg>')
