"""Tests for the deterministic novel cast seed (P2b)."""

from __future__ import annotations

from pipeline.db import init_db, run_migrations, get_connection
from pipeline.novel_seed import parse_noms, apply_seed


_NOMS = """# Registre des noms — CANONIQUE, multilingue

## Personnages (enforced — clé = slug de etat/personnages/)

| slug | FR | EN | ZH |
|------|----|----|----|
| oracle | Oracle | (tbd) | 神谕者 |
| pluie-menue | Pluie-Menue | Fine-Rain | 细雨 |
| front-leve | Front-Levé | (tbd) | 昂首 |

## Peuples, lieux, choses (advisory — pas de fichier perso)

| clé | FR | EN | ZH |
|-----|----|----|----|
| peuple-de-l-eau | peuple de l'eau | (tbd) | 水上人家 |
"""


def _write_noms(tmp_path) -> str:
    p = tmp_path / "noms.md"
    p.write_text(_NOMS, encoding="utf-8")
    return str(p)


def test_parse_noms_persons_only(tmp_path):
    cast = parse_noms(_write_noms(tmp_path))
    names = [p.canonical_name for p in cast.persons]
    # 3 persons from the enforced table; the advisory "peuple de l'eau" is excluded
    assert names == ["Oracle", "Pluie-Menue", "Front-Levé"]
    assert all(p.entity_type == "person" for p in cast.persons)


def test_parse_noms_aliases_and_tbd(tmp_path):
    cast = parse_noms(_write_noms(tmp_path))
    by_name = {p.canonical_name: p for p in cast.persons}
    assert by_name["Oracle"].aliases == ["神谕者"]                 # (tbd) EN skipped
    assert by_name["Pluie-Menue"].aliases == ["Fine-Rain", "细雨"]  # both kept
    assert by_name["Front-Levé"].aliases == ["昂首"]


def _seed_db(tmp_path) -> tuple[str, int]:
    db = str(tmp_path / "seed.db")
    init_db(db); run_migrations(db)
    conn = get_connection(db)
    conn.execute("INSERT INTO civ_civilizations (id, name) VALUES (1, 'Roman')")
    conn.commit(); conn.close()
    return db, 1


def test_apply_seed_inserts_entities_and_aliases(tmp_path):
    cast = parse_noms(_write_noms(tmp_path))
    db, civ_id = _seed_db(tmp_path)
    stats = apply_seed(db, civ_id, cast)
    assert stats["entities_added"] == 3
    assert stats["aliases_added"] == 4          # 1 + 2 + 1
    conn = get_connection(db)
    persons = {r["canonical_name"] for r in conn.execute(
        "SELECT canonical_name FROM entity_entities WHERE entity_type='person'")}
    assert persons == {"Oracle", "Pluie-Menue", "Front-Levé"}
    # the Chinese alias is queryable -> entity_lookup will canonicalize it
    zh = conn.execute(
        "SELECT e.canonical_name FROM entity_aliases a JOIN entity_entities e ON e.id=a.entity_id "
        "WHERE a.alias = ?", ("细雨",)).fetchone()
    assert zh["canonical_name"] == "Pluie-Menue"


def test_apply_seed_is_idempotent(tmp_path):
    cast = parse_noms(_write_noms(tmp_path))
    db, civ_id = _seed_db(tmp_path)
    apply_seed(db, civ_id, cast)
    stats2 = apply_seed(db, civ_id, cast)          # second run: nothing new
    assert stats2["entities_added"] == 0
    assert stats2["aliases_added"] == 0
