"""Tests for bot.tools — mirrors mcp-server/src/__tests__/tools.test.ts."""

from __future__ import annotations

from bot.tools import (
    resolve_civ_name,
    list_civs,
    get_civ_state,
    get_turn_detail,
    search_lore,
    get_entity_detail,
    sanity_check,
    timeline,
    compare_civs,
    search_turn_content,
    dispatch_tool,
)


# --------------------------------------------------------------------------- #
# resolve_civ_name
# --------------------------------------------------------------------------- #

class TestResolveCivName:
    def test_exact_match(self, db):
        result = resolve_civ_name(db, "Civilisation de la Confluence")
        assert "civ" in result
        assert result["civ"]["name"] == "Civilisation de la Confluence"

    def test_fuzzy_match(self, db):
        result = resolve_civ_name(db, "Confluence")
        assert "civ" in result
        assert result["civ"]["name"] == "Civilisation de la Confluence"

    def test_unknown(self, db):
        result = resolve_civ_name(db, "Nope")
        assert "error" in result
        assert "not found" in result["error"]
        assert "Civilisation de la Confluence" in result["error"]


# --------------------------------------------------------------------------- #
# listCivs
# --------------------------------------------------------------------------- #

class TestListCivs:
    def test_lists_all(self, db):
        result = list_civs(db)
        assert "Civilisation de la Confluence" in result
        assert "Cheveux de Sang" in result
        assert "Rubanc" in result


# --------------------------------------------------------------------------- #
# getCivState
# --------------------------------------------------------------------------- #

class TestGetCivState:
    def test_returns_state(self, db):
        result = get_civ_state(db, 1, "Civilisation de la Confluence")
        assert "Civilisation de la Confluence" in result
        assert "technology" in result
        assert "institution" in result
        assert "Argile Vivante" in result


# --------------------------------------------------------------------------- #
# searchLore
# --------------------------------------------------------------------------- #

class TestSearchLore:
    def test_by_canonical_name(self, db):
        result = search_lore(db, "Argile")
        assert "Argile Vivante" in result
        assert "technology" in result

    def test_by_alias(self, db):
        result = search_lore(db, "living clay")
        assert "Argile Vivante" in result

    def test_filter_by_civ(self, db):
        result = search_lore(db, "Caste", civ_id=1)
        assert "Caste de l Air" in result

    def test_no_match(self, db):
        result = search_lore(db, "zzzzzzzzz")
        assert "No entities found" in result


# --------------------------------------------------------------------------- #
# sanityCheck
# --------------------------------------------------------------------------- #

class TestSanityCheck:
    def test_matches_entities(self, db):
        result = sanity_check(
            db,
            "Les Confluents maitrisent l'argile vivante",
            civ_id=1,
            civ_name="Civilisation de la Confluence",
        )
        assert "Argile Vivante" in result
        assert "Matched Entities" in result

    def test_no_match_shows_inventory(self, db):
        result = sanity_check(
            db,
            "Le bronze est forge",
            civ_id=1,
            civ_name="Civilisation de la Confluence",
        )
        assert "bronze" in result
        assert "Entity Inventory" in result

    def test_includes_inventory(self, db):
        result = sanity_check(
            db,
            "test",
            civ_id=1,
            civ_name="Civilisation de la Confluence",
        )
        assert "Entity Inventory" in result
        assert "technology" in result


# --------------------------------------------------------------------------- #
# timeline
# --------------------------------------------------------------------------- #

class TestTimeline:
    def test_global_timeline(self, db):
        result = timeline(db)
        assert "Civilisation de la Confluence" in result
        assert "Cheveux de Sang" in result

    def test_filter_by_civ(self, db):
        result = timeline(db, civ_id=1)
        assert "Civilisation de la Confluence" in result
        assert "Depart Maritime" not in result


# --------------------------------------------------------------------------- #
# compareCivs
# --------------------------------------------------------------------------- #

class TestCompareCivs:
    def test_compare_two(self, db):
        civs = [
            {"id": 1, "name": "Civilisation de la Confluence", "player_name": "Rubanc"},
            {"id": 2, "name": "Cheveux de Sang", "player_name": "PlayerB"},
        ]
        result = compare_civs(db, civs)
        assert "Civilisation de la Confluence" in result
        assert "Cheveux de Sang" in result
        assert "Comparison" in result

    def test_aspect_filter(self, db):
        civs = [
            {"id": 1, "name": "Civilisation de la Confluence", "player_name": "Rubanc"},
            {"id": 2, "name": "Cheveux de Sang", "player_name": "PlayerB"},
        ]
        result = compare_civs(db, civs, aspects=["technology"])
        assert "technology" in result


# --------------------------------------------------------------------------- #
# getEntityDetail
# --------------------------------------------------------------------------- #

class TestGetEntityDetail:
    def test_returns_details(self, db):
        result = get_entity_detail(db, "Argile")
        assert "Argile Vivante" in result
        assert "living clay" in result
        assert "argile" in result
        assert "Mentions" in result

    def test_shows_relations(self, db):
        result = get_entity_detail(db, "Argile Vivante")
        assert "Relations" in result
        assert "discovered_at" in result

    def test_not_found(self, db):
        result = get_entity_detail(db, "zzzzzzz")
        assert "No entity found" in result


# --------------------------------------------------------------------------- #
# getTurnDetail
# --------------------------------------------------------------------------- #

class TestGetTurnDetail:
    def test_returns_detail(self, db):
        result = get_turn_detail(db, 1, 1, "Civilisation de la Confluence")
        assert "Fondation" in result
        assert "narrative" in result
        assert "description" in result
        assert "cinq castes" in result

    def test_not_found(self, db):
        result = get_turn_detail(db, 99, 1, "Civilisation de la Confluence")
        assert "not found" in result
        assert "1, 2, 3" in result


# --------------------------------------------------------------------------- #
# searchTurnContent
# --------------------------------------------------------------------------- #

class TestSearchTurnContent:
    def test_finds_content(self, db):
        result = search_turn_content(db, "argile")
        assert "argile vivante" in result

    def test_filter_by_segment_type(self, db):
        result = search_turn_content(db, "castes", segment_type="narrative")
        assert "narrative" in result

    def test_no_match(self, db):
        result = search_turn_content(db, "zzzzzzz")
        assert "No matching content" in result


# --------------------------------------------------------------------------- #
# dispatch_tool
# --------------------------------------------------------------------------- #

class TestDispatchTool:
    def test_listCivs(self, db):
        result = dispatch_tool(db, "listCivs", {})
        assert "Civilisation de la Confluence" in result

    def test_getCivState(self, db):
        result = dispatch_tool(db, "getCivState", {"civName": "Confluence"})
        assert "Civilisation de la Confluence" in result

    def test_searchLore(self, db):
        result = dispatch_tool(db, "searchLore", {"query": "Argile"})
        assert "Argile Vivante" in result

    def test_unknown_tool(self, db):
        result = dispatch_tool(db, "foobar", {})
        assert "Unknown tool" in result
