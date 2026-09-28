"""Chat-Assistent.

Zweistufig:
1. ``verstehen`` + ``antworten``: deterministisches Sprachverständnis und exakte Antworten
   direkt aus den Daten – keine Halluzination möglich, sofort, offline.
2. Optional ``llm``: ein Sprachmodell (Claude oder ein lokales Modell) für freie Fragen. Es
   bekommt keine Rohdaten, sondern ruft dieselben Abfragefunktionen als Werkzeuge auf
   (``werkzeuge``) und formuliert nur die Antwort.
"""

from .antworten import Antwort, Assistent

__all__ = ["Antwort", "Assistent"]
