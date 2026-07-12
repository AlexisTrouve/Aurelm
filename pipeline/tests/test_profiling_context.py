"""Regression: sentence-scoped profiling context must not bleed between entities.

The profiler built each entity's context from a ±400-char window centered on its
mention, which pulled in NEIGHBOURING characters' sentences — so one character's
trait (e.g. Front-Levé's "menton") landed in another's description. Novel profiles
now scope the excerpt to the sentence containing the mention.
"""

from __future__ import annotations

from pipeline.entity_profiler import _sentence_around


_TEXT = "Main-de-Pierre taille la pierre au bord. Front-Levé marche, le menton haut, fier."


def test_sentence_scope_excludes_neighbour_traits():
    pos = _TEXT.find("Main-de-Pierre")
    s = _sentence_around(_TEXT, pos, len("Main-de-Pierre"))
    assert "Main-de-Pierre" in s
    assert "menton" not in s          # Front-Levé's trait must NOT bleed in


def test_sentence_scope_keeps_the_owning_sentence():
    pos = _TEXT.find("Front-Levé")
    s = _sentence_around(_TEXT, pos, len("Front-Levé"))
    assert "menton" in s              # Front-Levé's own sentence is returned
    assert "taille la pierre" not in s


def test_sentence_scope_handles_final_sentence_without_terminator():
    text = "Seule phrase sans point final avec Oracle dedans"
    pos = text.find("Oracle")
    s = _sentence_around(text, pos, len("Oracle"))
    assert s == text                 # runs to end of text, no crash
