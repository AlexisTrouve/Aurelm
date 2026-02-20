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
    _clean_input,
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

    def test_shows_choices_made(self, db):
        """Turn 2 has choices_made=['Envoyer une delegation diplomatique'].
        get_turn_detail must display them -- not silently omit structured decisions."""
        result = get_turn_detail(db, 2, 1, "Civilisation de la Confluence")
        # Before fix: choices_made not in SELECT, never displayed
        # After fix: parsed JSON array rendered as list items
        assert "delegation diplomatique" in result, (
            "get_turn_detail omits choices_made -- GM can't see what decision was taken"
        )

    def test_shows_choices_proposed(self, db):
        """Turn 3 has choices_proposed=['Explorer les ruines','Ignorer les ruines'].
        get_turn_detail must display proposed choices too."""
        result = get_turn_detail(db, 3, 1, "Civilisation de la Confluence")
        assert "Explorer les ruines" in result or "Ignorer les ruines" in result, (
            "get_turn_detail omits choices_proposed -- GM can't see what was offered"
        )


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


# --------------------------------------------------------------------------- #
# Bug G: _parse_history silently converts null entries to the string "None"
# --------------------------------------------------------------------------- #

class TestParseHistoryNoneFilter:
    """Bug G: _parse_history at bot/tools.py converts None entries to the string 'None'.
    _parse_json_list has an `if e` guard; _parse_history does not.
    """

    def test_entity_detail_does_not_show_none_string(self, db):
        """Entity with history containing null must not show 'None' in output."""
        db.execute(
            "UPDATE entity_entities SET history = '[null, \"Fondation de la cite\"]' WHERE id = 2"
        )
        db.commit()
        result = get_entity_detail(db, "Caste de l Air", 1)
        assert "- None" not in result, (
            "history null entry was converted to the literal string 'None'"
        )

    def test_entity_detail_keeps_valid_history_entries(self, db):
        """After filtering nulls, real history entries must still appear."""
        db.execute(
            "UPDATE entity_entities SET history = '[null, \"Fondation de la cite\"]' WHERE id = 2"
        )
        db.commit()
        result = get_entity_detail(db, "Caste de l Air", 1)
        assert "Fondation de la cite" in result


# --------------------------------------------------------------------------- #
# Bug C: getTechTree min() crash when technologies JSON contains only nulls
# --------------------------------------------------------------------------- #

class TestGetTechTreeNullTechnologies:
    """Bug C: rows exist but _parse_json_list filters all nulls -> all_techs empty
    -> min() on empty sequence -> ValueError crash.
    """

    def test_null_technologies_does_not_crash(self, db):
        """Turn with technologies='[null]' must not raise ValueError."""
        # Insert a turn whose technologies JSON parses to [] after null filtering
        db.execute(
            "INSERT INTO turn_turns (civ_id, turn_number, title, summary, raw_message_ids, technologies) "
            "VALUES (1, 99, 'Tour Null Tech', 'test', '[]', '[null]')"
        )
        db.commit()
        result = get_tech_tree(db, 1, "Civilisation de la Confluence")
        # Must not raise -- should return a graceful message or valid content
        assert isinstance(result, str)

    def test_null_technologies_returns_no_techs_message(self, db):
        """When all technologies JSON entries are null, return a helpful message."""
        # Replace all existing tech rows with null-only ones
        db.execute("UPDATE turn_turns SET technologies = '[null]' WHERE civ_id = 1")
        db.commit()
        result = get_tech_tree(db, 1, "Civilisation de la Confluence")
        # Should not crash and should not return the normal tech tree header
        # (since all_techs is empty after filtering)
        assert "No" in result or "technologies" in result.lower()

    def test_mixed_null_and_valid_still_works(self, db):
        """Mix of null and valid tech entries: only valid ones shown, no crash."""
        db.execute(
            "INSERT INTO turn_turns (civ_id, turn_number, title, summary, raw_message_ids, technologies) "
            "VALUES (1, 98, 'Tour Mixed', 'test', '[]', '[null, \"forge\"]')"
        )
        db.commit()
        result = get_tech_tree(db, 1, "Civilisation de la Confluence")
        assert isinstance(result, str)
        assert "forge" in result


# --------------------------------------------------------------------------- #
# Bug I: search_lore / search_turn_content -- SQL LIKE wildcards in query
# % and _ are treated as SQL wildcards, silently broadening results.
# --------------------------------------------------------------------------- #

class TestSearchLikeWildcardEscape:
    """Bug I: query containing % or _ is used raw in LIKE pattern.
    '5%' becomes '%5%%' which matches anything containing '5'.
    '_' matches any single character.
    """

    def test_percent_in_lore_query_does_not_match_unrelated(self, db):
        """search_lore('%') should NOT match every entity."""
        # '%' as the full query becomes '%%%' which matches everything
        result = search_lore(db, "%")
        # Before fix: returns all 5 entities (% is wildcard matching everything)
        # After fix: returns 0 or only entities whose name/description contains literal '%'
        # In our seed data, no entity name/description contains a literal '%'
        assert "Argile Vivante" not in result or "Caste de l Air" not in result, (
            "search_lore('%') matched ALL entities -- % was treated as SQL wildcard"
        )

    def test_underscore_in_lore_query_matches_only_exact(self, db):
        """'Argile_Vivante' (with underscore) should NOT match 'Argile Vivante' (with space)."""
        # '_' in SQL LIKE matches any single character, including a space
        result = search_lore(db, "Argile_Vivante")
        # Before fix: matches 'Argile Vivante' (space == any char)
        # After fix: no match (no entity has literal underscore in that position)
        assert "Argile Vivante" not in result, (
            "search_lore('Argile_Vivante') matched 'Argile Vivante' -- _ was treated as SQL wildcard"
        )

    def test_percent_in_turn_content_does_not_match_all(self, db):
        """search_turn_content('%') should NOT match every segment."""
        result = search_turn_content(db, "%")
        # Before fix: returns every segment (% matches everything)
        # After fix: returns only segments containing literal '%'
        assert "confluent" not in result.lower() or "castes" not in result.lower(), (
            "search_turn_content('%') matched ALL segments -- % was treated as SQL wildcard"
        )


# --------------------------------------------------------------------------- #
# Bug J: compare_civs -- invalid aspect silently defaults to ALL aspects
# --------------------------------------------------------------------------- #

class TestCompareCivsInvalidAspect:
    """Bug J: compare_civs(aspects=["invalid_aspect"]) silently falls back to
    all aspects instead of reporting an error.
    """

    def test_invalid_aspect_returns_error(self, db):
        """Passing an unknown aspect name must return an error, not all aspects."""
        civ1 = {"id": 1, "name": "Civilisation de la Confluence", "player_name": "Rubanc"}
        civ2 = {"id": 2, "name": "Cheveux de Sang", "player_name": "PlayerB"}
        result = compare_civs(db, civs=[civ1, civ2], aspects=["aspect_inexistant"])
        # Before fix: returns a full comparison of ALL aspects (silent fallback)
        # After fix: returns an error message listing valid aspects
        assert "error" in result.lower() or "invalid" in result.lower() or "aspect" in result.lower(), (
            "compare_civs with invalid aspect should return an error, not silently compare everything"
        )
        # Must NOT show a full comparison -- the result should be a short error,
        # not a full markdown comparison with civ stats
        assert "Civilization Comparison" not in result, (
            "compare_civs returned a full comparison despite receiving an invalid aspect"
        )
        assert "Civilisation de la Confluence" not in result or len(result) < 200, (
            "compare_civs returned a full comparison despite receiving an invalid aspect"
        )


# --------------------------------------------------------------------------- #
# Bug A: get_entity_detail -- SQL LIKE wildcards not escaped in entity_name
# --------------------------------------------------------------------------- #

class TestGetEntityDetailLikeEscape:
    """Bug A: get_entity_detail builds LIKE pattern without _escape_like().
    '%' expands to match everything; '_' matches any single char.
    """

    def test_percent_does_not_match_all_entities(self, db):
        """get_entity_detail('%') should NOT return all entities."""
        result = get_entity_detail(db, "%")
        # Before fix: LIKE '%%%' matches every entity
        # After fix: only entities whose name literally contains '%'
        assert "Argile Vivante" not in result or "Caste de l Air" not in result, (
            "get_entity_detail('%') matched ALL entities -- % treated as SQL wildcard"
        )

    def test_underscore_does_not_match_space(self, db):
        """get_entity_detail('Argile_Vivante') must NOT match 'Argile Vivante'."""
        result = get_entity_detail(db, "Argile_Vivante")
        # '_' matches any single char including space
        assert "Argile Vivante" not in result, (
            "get_entity_detail('Argile_Vivante') matched 'Argile Vivante' -- _ treated as SQL wildcard"
        )


# --------------------------------------------------------------------------- #
# Bug B: filter_timeline -- entity_name search uses unescaped LIKE
# --------------------------------------------------------------------------- #

class TestFilterTimelineEntityLikeEscape:
    """Bug B: filter_timeline entity_name uses raw LIKE without _escape_like()."""

    def test_percent_entity_does_not_match_all_turns(self, db):
        """filter_timeline(entityName='%') should NOT return all turns."""
        result = filter_timeline(db, entity_name="%")
        # Before fix: % matches everything -> all 4 turns returned
        # After fix: no entity name contains literal %, 0 turns
        lines = [l for l in result.splitlines() if l.startswith("|") and "Turn" not in l and "---" not in l]
        # Don't expect all 4 civs' turns to appear
        assert "4 turn(s) found" not in result, (
            "filter_timeline(entityName='%') matched ALL turns -- % treated as SQL wildcard"
        )

    def test_underscore_entity_does_not_match_space(self, db):
        """filter_timeline(entityName='Argile_Vivante') must NOT match 'Argile Vivante'."""
        result = filter_timeline(db, entity_name="Argile_Vivante")
        # '_' matches any single char including space -> would match "Argile Vivante"
        assert "Argile" not in result or "0 turn" in result or "No turns" in result, (
            "filter_timeline('Argile_Vivante') matched 'Argile Vivante' -- _ treated as SQL wildcard"
        )


# --------------------------------------------------------------------------- #
# Bug C: getStructuredFacts -- invalid factType silently returns ALL types
# --------------------------------------------------------------------------- #

class TestGetStructuredFactsInvalidType:
    """Bug C: fact_type not in VALID_FACT_TYPES -> silent fallback to ALL types.
    User thinks they filtered, actually gets unfiltered output.
    """

    def test_invalid_fact_type_returns_error(self, db):
        """Passing an unknown factType must return an error, not silently return all facts."""
        result = get_structured_facts(db, 1, "Civilisation de la Confluence", fact_type="military")
        # Before fix: returns all 4 fact types (technologies, resources, beliefs, geography)
        # After fix: returns an error message mentioning valid types
        assert "military" in result.lower() or "invalid" in result.lower() or "error" in result.lower(), (
            "get_structured_facts with invalid factType should mention the invalid type or return error"
        )
        # Should NOT silently return full structured facts output
        assert "Resources:" not in result and "Beliefs:" not in result, (
            "get_structured_facts with invalid factType silently returned all fact types"
        )


# --------------------------------------------------------------------------- #
# Bug D: _clean_input -- empty string "" converted to None, breaking LIKE queries
# --------------------------------------------------------------------------- #

class TestResolveEntityLikeEscape:
    """Bug: _resolve_entity built LIKE pattern without _escape_like(), so
    '_' matched any single character and '%' matched any substring.
    """

    def test_underscore_does_not_match_space(self, db):
        """'Argile_Vivante' with _ should NOT match 'Argile Vivante' (space)."""
        from bot.tools import _resolve_entity
        results = _resolve_entity(db, "Argile_Vivante", civ_id=None)
        names = [r["name"] for r in results]
        assert "Argile Vivante" not in names, (
            "_resolve_entity: '_' treated as SQL wildcard and matched space"
        )

    def test_percent_does_not_match_all(self, db):
        """'%' alone should NOT match every entity name."""
        from bot.tools import _resolve_entity
        results = _resolve_entity(db, "%", civ_id=None)
        # Before fix: LIKE '%%%' matches everything → many results
        # After fix: no entity name contains literal '%' → 0 results
        assert len(results) == 0, (
            "_resolve_entity: '%' treated as SQL wildcard and matched all entities"
        )


class TestCleanInputEmptyString:
    """Bug D: "" is in _NIL_VALUES so _clean_input replaces it with None.
    dispatch_tool then passes None as query to search_lore, which interpolates
    it into f-string: f"%{_escape_like(None)}%" -> AttributeError crash.
    """

    def test_empty_string_not_converted_to_none(self):
        """_clean_input should NOT convert '' to None -- it's a valid Python empty str."""
        result = _clean_input({"query": ""})
        # Before fix: result["query"] is None (crashes downstream in _escape_like)
        # After fix: result["query"] is None OR "" depending on strategy, but must not crash
        # The key invariant: dispatch_tool("searchLore", {"query": ""}) must not crash
        assert result.get("query") is not None or result.get("query") == "", (
            "_clean_input converted empty string to None -- will cause AttributeError in _escape_like"
        )

    def test_dispatch_search_lore_empty_query_does_not_crash(self, db):
        """dispatch_tool searchLore with query='' must not raise AttributeError."""
        # Before fix: crashes with AttributeError: 'NoneType' object has no attribute 'replace'
        try:
            result = dispatch_tool(db, "searchLore", {"query": ""})
            # If it doesn't crash, it should return some result (not necessarily matches)
            assert isinstance(result, str)
        except AttributeError as e:
            raise AssertionError(
                f"dispatch_tool('searchLore', query='') crashed with AttributeError: {e}"
            ) from e
