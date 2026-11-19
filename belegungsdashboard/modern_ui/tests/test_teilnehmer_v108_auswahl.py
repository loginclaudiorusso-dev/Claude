"""1.08 – Maßnahmen-Auswahl wird übernommen (asynchrones setzen), eigene Skala als Standard."""

import ast
import pathlib

import modern

ASYNC = {"setzen", "laden", "aendern"}       # Methoden der Oberfläche, die man abwarten muss


def test_keine_asynchrone_methode_ohne_await():
    """Ein nacktes ``a.setzen(...)`` als Anweisung erzeugt nur eine Coroutine, die nie läuft – die Änderung bleibt aus.
    (In Lambdas ist es in Ordnung: NiceGUI wartet den Rückgabewert ab.)"""
    funde = []
    for p in pathlib.Path(modern.__file__).parent.glob("*.py"):
        for knoten in ast.walk(ast.parse(p.read_text(encoding="utf-8"))):
            if isinstance(knoten, ast.Expr) and isinstance(knoten.value, ast.Call) \
                    and isinstance(knoten.value.func, ast.Attribute) and knoten.value.func.attr in ASYNC \
                    and isinstance(knoten.value.func.value, ast.Name) and knoten.value.func.value.id in ("a", "self"):
                funde.append(f"{p.name}:{knoten.lineno}")
    assert not funde, funde


def test_eigene_skala_ist_standard_und_steht_oben():
    import inspect

    from modern import seite_massnahmen as sm

    q = inspect.getsource(sm)
    assert 'getattr(a, "mn_skala", "eigen")' in q
    assert q.index('"eigen": "eigene Skala"') < q.index('"gleich": "gleiche Skala"')
