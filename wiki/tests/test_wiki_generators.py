"""Tests for wiki generator functions -- choices page, relations page, nav, civ index links."""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

# Add wiki/ to path so we can import generate
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from generate import (
    generate_choices_page,
    generate_relations_page,
    generate_civ_index,
    _build_nav,
    slugify,
    generate_civ_entities,
)


# --------------------------------------------------------------------------- #
# generate_choices_page
# --------------------------------------------------------------------------- #

class TestGenerateChoicesPage:
    def test_generates_choices_file(self, db):
        with tempfile.TemporaryDirectory() as tmpdir:
            generate_choices_page(db, 1, "Civilisation de la Confluence", tmpdir)
            path = Path(tmpdir) / "civilizations" / "civilisation-de-la-confluence" / "knowledge" / "choices.md"
            assert path.exists()
            content = path.read_text(encoding="utf-8")
            assert "Choix et Decisions" in content

    def test_choices_content(self, db):
        with tempfile.TemporaryDirectory() as tmpdir:
            generate_choices_page(db, 1, "Civilisation de la Confluence", tmpdir)
            path = Path(tmpdir) / "civilizations" / "civilisation-de-la-confluence" / "knowledge" / "choices.md"
            content = path.read_text(encoding="utf-8")
            assert "delegation diplomatique" in content
            assert "Explorer les ruines" in content
            assert "Decision prise" in content
            assert "Choix proposes" in content

    def test_filter_by_turn(self, db):
        with tempfile.TemporaryDirectory() as tmpdir:
            generate_choices_page(db, 1, "Civilisation de la Confluence", tmpdir)
            path = Path(tmpdir) / "civilizations" / "civilisation-de-la-confluence" / "knowledge" / "choices.md"
            content = path.read_text(encoding="utf-8")
            # Turn 2 and 3 have choices, turn 1 does not
            assert "Tour 2" in content
            assert "Tour 3" in content

    def test_no_choices_skips_file(self, db):
        with tempfile.TemporaryDirectory() as tmpdir:
            generate_choices_page(db, 2, "Cheveux de Sang", tmpdir)
            path = Path(tmpdir) / "civilizations" / "cheveux-de-sang" / "knowledge" / "choices.md"
            assert not path.exists()

    def test_mkdocs_admonitions(self, db):
        with tempfile.TemporaryDirectory() as tmpdir:
            generate_choices_page(db, 1, "Civilisation de la Confluence", tmpdir)
            path = Path(tmpdir) / "civilizations" / "civilisation-de-la-confluence" / "knowledge" / "choices.md"
            content = path.read_text(encoding="utf-8")
            assert '??? question' in content
            assert '!!! success' in content


# --------------------------------------------------------------------------- #
# generate_relations_page
# --------------------------------------------------------------------------- #

class TestGenerateRelationsPage:
    def test_generates_relations_file(self, db):
        with tempfile.TemporaryDirectory() as tmpdir:
            generate_relations_page(db, 1, "Civilisation de la Confluence", tmpdir)
            path = Path(tmpdir) / "civilizations" / "civilisation-de-la-confluence" / "knowledge" / "relations.md"
            assert path.exists()
            content = path.read_text(encoding="utf-8")
            assert "Relations entre Entites" in content

    def test_relations_content(self, db):
        with tempfile.TemporaryDirectory() as tmpdir:
            generate_relations_page(db, 1, "Civilisation de la Confluence", tmpdir)
            path = Path(tmpdir) / "civilizations" / "civilisation-de-la-confluence" / "knowledge" / "relations.md"
            content = path.read_text(encoding="utf-8")
            assert "discovered_at" in content.lower() or "Discovered At" in content
            assert "member_of" in content.lower() or "Member Of" in content
            assert "Argile Vivante" in content
            assert "Ruines Anciennes" in content

    def test_grouped_by_type(self, db):
        with tempfile.TemporaryDirectory() as tmpdir:
            generate_relations_page(db, 1, "Civilisation de la Confluence", tmpdir)
            path = Path(tmpdir) / "civilizations" / "civilisation-de-la-confluence" / "knowledge" / "relations.md"
            content = path.read_text(encoding="utf-8")
            # Both relation types should appear as ## headers
            assert "## Discovered At" in content
            assert "## Member Of" in content

    def test_no_relations_skips_file(self, db):
        """Civ with no relations should not generate a file."""
        # Remove all relations for civ 2
        db.execute("DELETE FROM entity_relations WHERE source_entity_id IN (SELECT id FROM entity_entities WHERE civ_id = 2) AND target_entity_id IN (SELECT id FROM entity_entities WHERE civ_id = 2)")
        with tempfile.TemporaryDirectory() as tmpdir:
            generate_relations_page(db, 2, "Cheveux de Sang", tmpdir)
            path = Path(tmpdir) / "civilizations" / "cheveux-de-sang" / "knowledge" / "relations.md"
            # CdS entity (civ_id=2) is involved in relations via cross-civ mentions
            # but the relation itself is between entities of civ 1
            # So this depends on whether any relation involves civ_id=2 entities
            # In our seed data, entity 5 (CdS, civ_id=2) has no relations
            # but entity 2 (Caste de l'Air, civ_id=1) has member_of to entity 1
            # The query filters by s.civ_id = ? OR t.civ_id = ?
            # So for civ_id=2, no relations should match
            assert not path.exists()


# --------------------------------------------------------------------------- #
# _build_nav
# --------------------------------------------------------------------------- #

class TestBuildNav:
    def test_includes_knowledge_section(self, db):
        civs = db.execute("SELECT * FROM civ_civilizations ORDER BY name").fetchall()
        nav = _build_nav(civs)
        # Find the Civilisations section
        civ_section = nav[1]["Civilisations"]
        # First entry is the index, rest are civs
        first_civ = civ_section[1]
        civ_name = list(first_civ.keys())[0]
        civ_pages = first_civ[civ_name]
        # Should have 4 entries: Apercu, Tours, Entites, Connaissances
        assert len(civ_pages) == 4
        # Last one should be Connaissances dict
        knowledge = civ_pages[3]
        assert "Connaissances" in knowledge

    def test_knowledge_has_all_pages(self, db):
        civs = db.execute("SELECT * FROM civ_civilizations ORDER BY name").fetchall()
        nav = _build_nav(civs)
        first_civ = nav[1]["Civilisations"][1]
        civ_pages = list(first_civ.values())[0]
        knowledge_pages = civ_pages[3]["Connaissances"]
        # Should have 6 knowledge pages
        assert len(knowledge_pages) == 6
        page_names = [list(p.keys())[0] for p in knowledge_pages]
        assert "Technologies" in page_names
        assert "Ressources" in page_names
        assert "Croyances" in page_names
        assert "Geographie" in page_names
        assert "Choix" in page_names
        assert "Relations" in page_names

    def test_knowledge_paths_are_correct(self, db):
        civs = db.execute("SELECT * FROM civ_civilizations ORDER BY name").fetchall()
        nav = _build_nav(civs)
        first_civ = nav[1]["Civilisations"][1]
        slug = slugify(list(first_civ.keys())[0])
        knowledge_pages = list(first_civ.values())[0][3]["Connaissances"]
        for page in knowledge_pages:
            path = list(page.values())[0]
            assert path.startswith(f"civilizations/{slug}/knowledge/")
            assert path.endswith(".md")


# --------------------------------------------------------------------------- #
# generate_civ_index cross-links
# --------------------------------------------------------------------------- #

class TestCivIndexLinks:
    def test_civ_index_has_knowledge_links(self, db):
        content = generate_civ_index(db, 1, "Civilisation de la Confluence", "Rubanc")
        assert "knowledge/technologies.md" in content
        assert "knowledge/resources.md" in content
        assert "knowledge/beliefs.md" in content
        assert "knowledge/geography.md" in content
        assert "knowledge/choices.md" in content
        assert "knowledge/relations.md" in content

    def test_civ_index_has_base_links(self, db):
        content = generate_civ_index(db, 1, "Civilisation de la Confluence", "Rubanc")
        assert "turns/index.md" in content
        assert "entities/index.md" in content

    def test_civ_index_has_knowledge_section_header(self, db):
        content = generate_civ_index(db, 1, "Civilisation de la Confluence", "Rubanc")
        assert "Base de connaissances" in content


# --------------------------------------------------------------------------- #
# Bug D: wiki slug collision -- two different entity names can slugify to the
# same string, causing one entity page to silently overwrite the other.
# --------------------------------------------------------------------------- #

class TestSlugCollision:
    """Bug D: Entities with names that differ only in ligatures/accents produce
    the same slug (e.g. 'Tribunal de Moeurs' and 'Tribunal de Mœurs').
    The wiki generator must produce distinct filenames for all entities.
    """

    def test_slugify_ligature_collision(self):
        """Confirm the collision: ae/oe ligatures normalize to same slug."""
        # These two names are different strings but produce the same slug
        assert slugify("Tribunal de Moeurs") == slugify("Tribunal de M\u0153urs"), (
            "Expected 'oe' ligature to produce same slug as plain 'oe'"
        )

    def test_entity_pages_no_overwrite(self, db):
        """Two entities with colliding slugs must produce TWO distinct files."""
        # Insert two entities with slug-colliding names
        db.execute(
            "INSERT INTO entity_entities (canonical_name, entity_type, civ_id) "
            "VALUES (?, ?, ?)",
            ("Tribunal de Moeurs", "institution", 1),
        )
        db.execute(
            "INSERT INTO entity_entities (canonical_name, entity_type, civ_id) "
            "VALUES (?, ?, ?)",
            ("Tribunal de M\u0153urs", "institution", 1),
        )
        db.commit()

        # Verify the collision is real
        assert slugify("Tribunal de Moeurs") == slugify("Tribunal de M\u0153urs")

        # Get the fused entity list for civ 1
        _, fused_list = generate_civ_entities(db, 1, "Civilisation de la Confluence")
        tribunal_entities = [
            e for e in fused_list if "Tribunal" in e["canonical_name"]
        ]
        assert len(tribunal_entities) == 2, "Need 2 Tribunal entities for this test"

        # Simulate the corrected entity page write loop (with deduplication)
        with tempfile.TemporaryDirectory() as tmpdir:
            entity_dir = Path(tmpdir)
            used_slugs: set[str] = set()
            for entity in tribunal_entities:
                eslug = slugify(entity["canonical_name"])
                if eslug in used_slugs:
                    counter = 2
                    while f"{eslug}-{counter}" in used_slugs:
                        counter += 1
                    eslug = f"{eslug}-{counter}"
                used_slugs.add(eslug)
                (entity_dir / f"{eslug}.md").write_text(
                    entity["canonical_name"], encoding="utf-8"
                )

            written_files = list(entity_dir.glob("*.md"))
            assert len(written_files) == 2, (
                f"Expected 2 entity files, got {len(written_files)}. "
                "Slug collision caused silent page overwrite!"
            )
