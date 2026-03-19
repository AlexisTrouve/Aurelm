"""Tests for map system bot tools (migration 031)."""

from __future__ import annotations

import pytest

from bot.tools import (
    resolve_map_name,
    get_maps,
    get_map_overview,
    get_cell,
    get_cell_history,
    get_territory,
    find_entity_on_map,
)


# ---------------------------------------------------------------------------
# resolve_map_name
# ---------------------------------------------------------------------------

def test_resolve_map_name_exact(db):
    result = resolve_map_name(db, "Monde")
    assert result is not None
    assert result["name"] == "Monde"
    assert isinstance(result["id"], int)


def test_resolve_map_name_fuzzy(db):
    result = resolve_map_name(db, "confluent")
    assert result is not None
    assert "Confluent" in result["name"]


def test_resolve_map_name_not_found(db):
    result = resolve_map_name(db, "Inexistant")
    assert result is None


# ---------------------------------------------------------------------------
# get_maps
# ---------------------------------------------------------------------------

def test_get_maps_lists_all(db):
    result = get_maps(db)
    assert "Monde" in result
    assert "Region Confluent" in result


def test_get_maps_shows_hierarchy(db):
    result = get_maps(db)
    # Child map indented under parent
    lines = result.splitlines()
    monde_line = next(l for l in lines if "Monde" in l)
    confluent_line = next(l for l in lines if "Confluent" in l and "Region" in l)
    # Region Confluent should appear after Monde and be indented
    assert result.index("Monde") < result.index("Region Confluent")
    assert confluent_line.startswith("  ")  # indented


def test_get_maps_empty(db):
    db.execute("DELETE FROM map_cells")
    db.execute("DELETE FROM map_cell_events")
    db.execute("DELETE FROM map_maps")
    result = get_maps(db)
    assert "Aucune" in result


# ---------------------------------------------------------------------------
# get_map_overview
# ---------------------------------------------------------------------------

def test_get_map_overview_shows_cells(db):
    m = resolve_map_name(db, "Monde")
    result = get_map_overview(db, m["id"], m["name"])
    assert "Confluent" in result
    assert "plain" in result


def test_get_map_overview_shows_events(db):
    m = resolve_map_name(db, "Monde")
    result = get_map_overview(db, m["id"], m["name"])
    assert "Fondation" in result
    assert "Premier contact" in result


def test_get_map_overview_empty_map(db):
    db.execute("INSERT INTO map_maps (name) VALUES ('Vide')")
    map_id = db.execute("SELECT id FROM map_maps WHERE name='Vide'").fetchone()[0]
    result = get_map_overview(db, map_id, "Vide")
    assert "aucune cellule" in result


# ---------------------------------------------------------------------------
# get_cell
# ---------------------------------------------------------------------------

def test_get_cell_found(db):
    m = resolve_map_name(db, "Monde")
    result = get_cell(db, m["id"], 0, 0)
    assert "Confluent" in result
    assert "plain" in result
    # Civ name should appear
    assert "Confluence" in result


def test_get_cell_with_events(db):
    m = resolve_map_name(db, "Monde")
    result = get_cell(db, m["id"], 0, 0)
    assert "Fondation" in result or "Premier contact" in result


def test_get_cell_not_found(db):
    m = resolve_map_name(db, "Monde")
    result = get_cell(db, m["id"], 99, 99)
    assert "introuvable" in result.lower() or "non trouvée" in result.lower()


# ---------------------------------------------------------------------------
# get_cell_history
# ---------------------------------------------------------------------------

def test_get_cell_history_returns_events(db):
    m = resolve_map_name(db, "Monde")
    result = get_cell_history(db, m["id"], 0, 0)
    assert "Fondation" in result or "Premier contact" in result


def test_get_cell_history_empty(db):
    m = resolve_map_name(db, "Monde")
    result = get_cell_history(db, m["id"], 99, 99)
    assert "Aucun" in result


def test_get_cell_history_limit(db):
    m = resolve_map_name(db, "Monde")
    # Insert 5 events at (1,0)
    for i in range(5):
        db.execute(
            "INSERT INTO map_cell_events (map_id, q, r, description, event_type) VALUES (?,1,0,?,?)",
            (m["id"], f"Evenement {i}", "note"),
        )
    result = get_cell_history(db, m["id"], 1, 0, limit=3)
    # Only 3 events shown
    assert result.count("- [") <= 3


# ---------------------------------------------------------------------------
# get_territory
# ---------------------------------------------------------------------------

def test_get_territory_returns_cells(db):
    result = get_territory(db, 1, "Civilisation de la Confluence")
    assert "Confluent" in result or "(0,0)" in result
    # Both maps have cells controlled by civ 1
    assert "Monde" in result


def test_get_territory_no_cells(db):
    result = get_territory(db, 999, "CivInconnue")
    assert "ne contrôle aucune" in result


# ---------------------------------------------------------------------------
# find_entity_on_map
# ---------------------------------------------------------------------------

def test_find_entity_on_map_found(db):
    # entity_id=4 (Ruines Anciennes) is placed at (3,0) on map 1
    result = find_entity_on_map(db, "Ruines Anciennes")
    assert "(3,0)" in result or "Ruines" in result


def test_find_entity_on_map_alias(db):
    # entity 1 has alias 'argile' — not placed on map, should say not placed
    result = find_entity_on_map(db, "argile")
    assert "introuvable" in result.lower() or "non placée" in result.lower() or "Argile" in result


def test_find_entity_on_map_not_found(db):
    result = find_entity_on_map(db, "EntiteInexistante")
    assert "introuvable" in result.lower()
