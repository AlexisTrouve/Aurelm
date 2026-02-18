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
    get_structured_facts,
    get_choice_history,
    explore_relations,
    filter_timeline,
    entity_activity,
    get_tech_tree,
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

# --------------------------------------------------------------------------- #
# getStructuredFacts
# --------------------------------------------------------------------------- #

class TestGetStructuredFacts:
    def test_all_facts(self, db):
        result = get_structured_facts(db, 1, "Civilisation de la Confluence")
        assert "Civilisation de la Confluence" in result
        assert "Argile Vivante" in result
        assert "Poisson" in result

    def test_filter_by_type(self, db):
        result = get_structured_facts(db, 1, "Civilisation de la Confluence", fact_type="technologies")
        assert "Argile Vivante" in result
        assert "Poisson" not in result

    def test_filter_by_turn(self, db):
        result = get_structured_facts(db, 1, "Civilisation de la Confluence", turn_number=1)
        assert "Poisson" in result
        assert "Argile Vivante" not in result

    def test_no_facts(self, db):
        result = get_structured_facts(db, 1, "Civilisation de la Confluence", fact_type="technologies", turn_number=99)
        assert "No structured facts" in result


# --------------------------------------------------------------------------- #
# getChoiceHistory
# --------------------------------------------------------------------------- #

class TestGetChoiceHistory:
    def test_returns_choices(self, db):
        result = get_choice_history(db, 1, "Civilisation de la Confluence")
        assert "delegation diplomatique" in result
        assert "Explorer les ruines" in result
        assert "Decision" in result

    def test_filter_by_turn(self, db):
        result = get_choice_history(db, 1, "Civilisation de la Confluence", turn_number=2)
        assert "delegation diplomatique" in result
        assert "Explorer les ruines" not in result

    def test_no_choices(self, db):
        # CdS turn 1 has no choices
        result = get_choice_history(db, 2, "Cheveux de Sang")
        assert "No choices recorded" in result


# --------------------------------------------------------------------------- #
# exploreRelations
# --------------------------------------------------------------------------- #

class TestExploreRelations:
    def test_finds_relations(self, db):
        result = explore_relations(db, "Argile Vivante")
        assert "discovered_at" in result
        assert "Ruines Anciennes" in result

    def test_depth_2(self, db):
        result = explore_relations(db, "Caste de l Air", depth=2)
        assert "member_of" in result
        assert "Argile Vivante" in result

    def test_not_found(self, db):
        result = explore_relations(db, "zzzzzzz")
        assert "No entity found" in result


# --------------------------------------------------------------------------- #
# filterTimeline
# --------------------------------------------------------------------------- #

class TestFilterTimeline:
    def test_filter_by_type(self, db):
        result = filter_timeline(db, turn_type="first_contact")
        assert "first_contact" in result
        assert "eclaireurs" in result
        assert "1" in result

    def test_filter_by_range(self, db):
        result = filter_timeline(db, from_turn=2, to_turn=3)
        assert "eclaireurs" in result
        assert "ruines" in result
        # Turn 1 should be excluded
        assert "Fondation" not in result

    def test_filter_by_entity(self, db):
        result = filter_timeline(db, entity_name="Argile")
        assert "Turn" in result
        assert "turn(s) found" in result

    def test_no_match(self, db):
        result = filter_timeline(db, turn_type="crisis")
        assert "No turns match" in result


# --------------------------------------------------------------------------- #
# entityActivity
# --------------------------------------------------------------------------- #

class TestEntityActivity:
    def test_shows_activity(self, db):
        result = entity_activity(db, "Argile Vivante")
        assert "First appearance" in result
        assert "Total mentions" in result
        assert "Turn" in result

    def test_shows_sparkline(self, db):
        result = entity_activity(db, "Caste de l Air")
        assert "Activity by Turn" in result
        assert "```" in result

    def test_not_found(self, db):
        result = entity_activity(db, "zzzzzzz")
        assert "No entity found" in result


# --------------------------------------------------------------------------- #
# getTechTree
# --------------------------------------------------------------------------- #

class TestGetTechTree:
    """Seed: civ 1 has gourdins+pieux (T1), lance (T2), Argile Vivante (T3)."""

    def test_full_tree_has_all_4_techs(self, db):
        result = get_tech_tree(db, 1, "Civilisation de la Confluence")
        assert "**4 technologies**" in result
        for tech in ["gourdins", "pieux", "lance", "Argile Vivante"]:
            assert f"**{tech}**" in result

    def test_correct_categories_assigned(self, db):
        result = get_tech_tree(db, 1, "Civilisation de la Confluence")
        # gourdins, pieux, lance -> Outils de chasse; Argile Vivante -> Materiaux
        assert "## Outils de chasse (3)" in result
        assert "## Materiaux (1)" in result
        # 2 categories + Timeline = 3 h2 sections
        assert result.count("\n## ") == 3

    def test_timeline_order(self, db):
        result = get_tech_tree(db, 1, "Civilisation de la Confluence")
        timeline_start = result.index("## Timeline")
        timeline = result[timeline_start:]
        # Tours must appear in order
        pos_t1 = timeline.index("Tour 1")
        pos_t2 = timeline.index("Tour 2")
        pos_t3 = timeline.index("Tour 3")
        assert pos_t1 < pos_t2 < pos_t3

    def test_filter_returns_only_matching_category(self, db):
        result = get_tech_tree(db, 1, "Civilisation de la Confluence", category="chasse")
        assert "**3 technologies**" in result
        assert "gourdins" in result
        assert "lance" in result
        assert "Argile Vivante" not in result
        assert "Materiaux" not in result

    def test_invalid_category_lists_available(self, db):
        result = get_tech_tree(db, 1, "Civilisation de la Confluence", category="spatial")
        assert "No technologies in category 'spatial'" in result
        assert "Materiaux" in result
        assert "Outils de chasse" in result

    def test_nonexistent_civ_returns_empty(self, db):
        result = get_tech_tree(db, 999, "Unknown Civ")
        assert result == "No technologies found for Unknown Civ."


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

    def test_getStructuredFacts(self, db):
        result = dispatch_tool(db, "getStructuredFacts", {"civName": "Confluence", "factType": "technologies"})
        assert "Argile Vivante" in result

    def test_getChoiceHistory(self, db):
        result = dispatch_tool(db, "getChoiceHistory", {"civName": "Confluence"})
        assert "delegation diplomatique" in result

    def test_exploreRelations(self, db):
        result = dispatch_tool(db, "exploreRelations", {"entityName": "Argile Vivante"})
        assert "discovered_at" in result

    def test_filterTimeline(self, db):
        result = dispatch_tool(db, "filterTimeline", {"turnType": "first_contact"})
        assert "first_contact" in result

    def test_entityActivity(self, db):
        result = dispatch_tool(db, "entityActivity", {"entityName": "Argile"})
        assert "First appearance" in result

    def test_getTechTree(self, db):
        result = dispatch_tool(db, "getTechTree", {"civName": "Confluence"})
        assert "Tech Tree" in result

    def test_unknown_tool(self, db):
        result = dispatch_tool(db, "foobar", {})
        assert "Unknown tool" in result
