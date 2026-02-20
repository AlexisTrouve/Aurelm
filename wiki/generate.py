"""Wiki generator -- produces MkDocs Material markdown pages from the Aurelm database.

Usage:
    python generate.py --db ../pipeline/test_e2e.db --out docs
"""

from __future__ import annotations

import argparse
import json
import re
import sqlite3
from datetime import datetime
from pathlib import Path

# Import turn page generators (Phase 2)
from turn_page_generator import generate_turn_index, generate_turn_page


def get_connection(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = sqlite3.Row
    return conn


def slugify(name: str) -> str:
    """Convert a name to a URL-safe slug."""
    s = name.lower().strip()
    s = re.sub(r"[àâä]", "a", s)
    s = re.sub(r"[éèêë]", "e", s)
    s = re.sub(r"[îï]", "i", s)
    s = re.sub(r"[ôö]", "o", s)
    s = re.sub(r"[ùûü]", "u", s)
    s = re.sub(r"[ç]", "c", s)
    s = re.sub(r"[œ]", "oe", s)
    s = re.sub(r"[^a-z0-9]+", "-", s)
    return s.strip("-")


# -- Entity filtering ---------------------------------------------------------
# spaCy's general NER picks up noise (YouTube metadata, markdown artifacts).
# We filter entities to keep only those that look like real game content.

NOISE_PATTERNS = re.compile(
    r"^("
    r"https?://|www\.|youtube|spotify"
    r"|.{1,2}$"           # 1-2 char strings
    r"|.*\n.*"            # multiline
    r"|.*[{}\[\]<>].*"   # markdown/code artifacts
    r"|__(.*?)__"         # underline markers
    r"|\*\*(.*?)\*\*$"   # bold-only strings
    r"|\d+$"             # pure numbers
    r")",
    re.IGNORECASE,
)

# Known noise entities from spaCy general model
NOISE_NAMES = {
    "Geiita", "Bartosz Pokrywka", "Carolina Romero", "Rithelgo",
    "Bartosz Pokrywka - Topic", "YouTube",
    "Blanc", "Hier", "Rare", "But", "Observer", "Transporter",
    "Organisation", "Formes", "Halls", "Hall", "Cercle", "Antre",
    "Biens", "Autre", "Autres", "Chef du", "Gardiens de",
    "Jimmys G", "Deadfire", "MIENNE", "TOUTES", "Message",
    "Ravitaillé", "Touché", "Planche", "Libre", "Lootbox", "Farouche",
    # Common French words that spaCy misidentifies as entities
    "Village", "Méthode", "Couche", "Premiers", "Échanges", "Esprits",
    "Lances", "Sculptures", "Tribunal", "Shamans", "Façonneurs",
    "Amélioration", "Conseil", "Acquisitions", "Montés",
    "Posséder", "Ramassez", "médier",
    "Faucon", "Cercles", "Échos", "Équipes", "Cliques",
    "Rubanc", "Sanciel",  # player name, ambiguous short form
}

# Noise patterns in entity names that indicate NER mis-extraction
NOISE_CONTENT = {
    "Choix", "Option", "option libre", "Option libre",
    "Pillar", "Soundtrack", "DETECTIVE", "Topic",
    "Tu es ", "Tu t'", "Et maintenant", "Puis tu",
    "Everybody wants", "The end of",
}


def is_noise_entity(name: str) -> bool:
    """Check if an entity name is likely noise rather than real game content."""
    if name in NOISE_NAMES:
        return True
    if NOISE_PATTERNS.match(name):
        return True
    if name.endswith("**") or name.startswith("**"):
        return True
    if "\n" in name:
        return True
    if any(noise in name for noise in NOISE_CONTENT):
        return True
    # Very long entity names are almost certainly NER noise
    if len(name) > 50:
        return True
    # Names with __ are NER artifacts (e.g. "Autre__")
    if "__" in name:
        return True
    # Names ending/starting with ) or ( are parsing artifacts (e.g. "Capture)")
    if name.endswith(")") or name.startswith("("):
        return True
    # Names that are just punctuation or whitespace fragments
    if not any(c.isalpha() for c in name):
        return True
    # Names starting with common French articles alone (e.g. "Le ", "La ", "Les ")
    # that are too short to be real entities
    if re.match(r"^(Le|La|Les|Un|Une|Des|Du|De)\s*$", name, re.IGNORECASE):
        return True
    # Markdown bold anywhere in the name
    if "**" in name:
        return True
    # Truncated entities ending with a preposition (e.g. "Chef de la", "Les Gardiens de")
    if re.search(r"\b(de|du|des|de la|de l')\s*$", name, re.IGNORECASE):
        return True
    # Entity names that look like sentence fragments (contain verb-like patterns)
    if re.search(r"\b(est|sont|fut|sera|était)\b", name, re.IGNORECASE):
        return True
    # Names starting with indefinite articles/determinants = NER noise
    # (but NOT "Le/La/Les" which are common in proper names like "La Confluence")
    if re.match(r"^(Que|Ces|Cet|Cette|Un|Une|Des)\s", name):
        return True
    # Names containing colon (truncated headers like "Deuxième Révélation : La")
    if ":" in name:
        return True
    # Names starting with "Chef de" (truncated titles)
    if re.match(r"^Chef de\b", name):
        return True
    return False


# -- Analysis functions --------------------------------------------------------

def get_cooccurrences(conn: sqlite3.Connection, civ_id: int | None = None, min_turns: int = 2) -> list[tuple]:
    """Retourne les co-occurrences d'entités (entités mentionnées ensemble dans les mêmes tours).

    Args:
        conn: Database connection
        civ_id: Optional civilization ID to filter by
        min_turns: Minimum number of turns entities must co-occur (default 2)

    Returns:
        List of tuples: (entity1_name, entity1_type, entity2_name, entity2_type, nb_tours)
    """
    # Build query with optional civ filter
    civ_filter = ""
    params: list = []
    if civ_id is not None:
        civ_filter = "AND e1.civ_id = ?"
        params.append(civ_id)

    query = f"""
        SELECT
            e1.canonical_name as entity1_name,
            e1.entity_type as entity1_type,
            e2.canonical_name as entity2_name,
            e2.entity_type as entity2_type,
            COUNT(DISTINCT m1.turn_id) as nb_turns
        FROM entity_mentions m1
        JOIN entity_mentions m2 ON m1.turn_id = m2.turn_id AND m1.entity_id < m2.entity_id
        JOIN entity_entities e1 ON m1.entity_id = e1.id
        JOIN entity_entities e2 ON m2.entity_id = e2.id
        WHERE 1=1 {civ_filter}
        GROUP BY e1.id, e2.id
        HAVING COUNT(DISTINCT m1.turn_id) >= ?
        ORDER BY nb_turns DESC, e1.canonical_name, e2.canonical_name
    """
    params.append(min_turns)

    rows = conn.execute(query, params).fetchall()
    return [(r["entity1_name"], r["entity1_type"], r["entity2_name"], r["entity2_type"], r["nb_turns"])
            for r in rows]


def get_entity_timeline(conn: sqlite3.Connection, entity_id: int) -> dict[int, int]:
    """Timeline des mentions d'une entité (par numéro de tour).

    Args:
        conn: Database connection
        entity_id: Entity ID

    Returns:
        Dictionary mapping turn_number -> nb_mentions
    """
    rows = conn.execute(
        """SELECT t.turn_number, COUNT(*) as nb_mentions
           FROM entity_mentions m
           JOIN turn_turns t ON m.turn_id = t.id
           WHERE m.entity_id = ?
           GROUP BY t.turn_number
           ORDER BY t.turn_number""",
        (entity_id,)
    ).fetchall()

    return {r["turn_number"]: r["nb_mentions"] for r in rows}


def get_tech_tree(conn: sqlite3.Connection, civ_id: int) -> list[tuple[int, list[str]]]:
    """Arbre technologique chronologique pour une civilisation.

    Args:
        conn: Database connection
        civ_id: Civilization ID

    Returns:
        List of tuples: (turn_number, [technologies])
    """
    rows = conn.execute(
        """SELECT turn_number, technologies
           FROM turn_turns
           WHERE civ_id = ? AND technologies IS NOT NULL AND technologies != '[]'
           ORDER BY turn_number""",
        (civ_id,)
    ).fetchall()

    result = []
    for r in rows:
        techs = _parse_json_list(r["technologies"])
        if techs:
            result.append((r["turn_number"], techs))

    return result


def get_turn_detailed_stats(conn: sqlite3.Connection, turn_id: int) -> dict:
    """Stats détaillées d'un tour.

    Args:
        conn: Database connection
        turn_id: Turn ID

    Returns:
        Dictionary with detailed stats:
        - segments_by_type: {type: count}
        - entities_count: int
        - new_entities: [entity_names]
        - mentions_count: int
        - has_media: bool
        - tech_count: int
        - resource_count: int
    """
    # Segments by type
    seg_rows = conn.execute(
        """SELECT segment_type, COUNT(*) as count
           FROM turn_segments
           WHERE turn_id = ?
           GROUP BY segment_type""",
        (turn_id,)
    ).fetchall()
    segments_by_type = {r["segment_type"]: r["count"] for r in seg_rows}

    # Entity stats
    entities_count = conn.execute(
        "SELECT COUNT(DISTINCT entity_id) FROM entity_mentions WHERE turn_id = ?",
        (turn_id,)
    ).fetchone()[0]

    # New entities (first_seen_turn = this turn)
    new_entity_rows = conn.execute(
        """SELECT e.canonical_name
           FROM entity_entities e
           WHERE e.first_seen_turn = ?
           ORDER BY e.canonical_name""",
        (turn_id,)
    ).fetchall()
    new_entities = [r["canonical_name"] for r in new_entity_rows if not is_noise_entity(r["canonical_name"])]

    # Mentions count
    mentions_count = conn.execute(
        "SELECT COUNT(*) FROM entity_mentions WHERE turn_id = ?",
        (turn_id,)
    ).fetchone()[0]

    # Media links
    turn_row = conn.execute(
        "SELECT media_links, technologies, resources FROM turn_turns WHERE id = ?",
        (turn_id,)
    ).fetchone()

    has_media = False
    tech_count = 0
    resource_count = 0

    if turn_row:
        media = _parse_json_data(turn_row["media_links"])
        has_media = len(media) > 0

        techs = _parse_json_list(turn_row["technologies"])
        tech_count = len(techs)

        resources = _parse_json_list(turn_row["resources"])
        resource_count = len(resources)

    return {
        "segments_by_type": segments_by_type,
        "entities_count": entities_count,
        "new_entities": new_entities,
        "mentions_count": mentions_count,
        "has_media": has_media,
        "tech_count": tech_count,
        "resource_count": resource_count,
    }


def get_entity_context_samples(conn: sqlite3.Connection, entity_id: int, limit: int = 5) -> list[tuple[int, str, str]]:
    """Extraits de mentions avec contexte pour une entité.

    Args:
        conn: Database connection
        entity_id: Entity ID
        limit: Maximum number of samples to return

    Returns:
        List of tuples: (turn_number, mention_text, context)
    """
    rows = conn.execute(
        """SELECT m.mention_text, m.context, t.turn_number
           FROM entity_mentions m
           JOIN turn_turns t ON m.turn_id = t.id
           WHERE m.entity_id = ?
           ORDER BY t.turn_number
           LIMIT ?""",
        (entity_id, limit)
    ).fetchall()

    return [(r["turn_number"], r["mention_text"], r["context"] or "") for r in rows]


def get_activity_by_month(conn: sqlite3.Connection, civ_id: int | None = None) -> list[tuple[str, int]]:
    """Activité mensuelle (nombre de tours par mois).

    Args:
        conn: Database connection
        civ_id: Optional civilization ID to filter by

    Returns:
        List of tuples: (year_month, turn_count)
        year_month format: "YYYY-MM"
    """
    civ_filter = ""
    params: list = []

    if civ_id is not None:
        civ_filter = "WHERE t.civ_id = ?"
        params.append(civ_id)

    # Extract year-month from Discord timestamp in raw messages
    query = f"""
        SELECT
            strftime('%Y-%m', m.timestamp) as year_month,
            COUNT(DISTINCT t.id) as turn_count
        FROM turn_turns t
        JOIN json_each(t.raw_message_ids) AS msg_id
        JOIN turn_raw_messages m ON CAST(msg_id.value AS INTEGER) = m.id
        {civ_filter}
        GROUP BY year_month
        ORDER BY year_month
    """

    rows = conn.execute(query, params).fetchall()
    return [(r["year_month"] or "Unknown", r["turn_count"]) for r in rows]


def get_turn_messages_grouped(conn: sqlite3.Connection, turn_id: int) -> list[dict]:
    """Messages Discord groupés par auteur (GM vs Player).

    Args:
        conn: Database connection
        turn_id: Turn ID

    Returns:
        List of dicts with keys: author, is_gm, timestamp, content
    """
    # Get raw message IDs
    turn_row = conn.execute(
        "SELECT raw_message_ids FROM turn_turns WHERE id = ?",
        (turn_id,)
    ).fetchone()

    if not turn_row or not turn_row["raw_message_ids"]:
        return []

    raw_ids = _parse_json_list(turn_row["raw_message_ids"])
    if not raw_ids:
        return []

    # Detect GM authors
    gm_authors = _detect_gm_authors(conn)

    # Fetch messages
    result = []
    for msg_id_str in raw_ids:
        msg_row = conn.execute(
            "SELECT author_name, timestamp, content FROM turn_raw_messages WHERE id = ?",
            (int(msg_id_str),)
        ).fetchone()

        if not msg_row:
            continue

        author = _clean_author_name(msg_row["author_name"])
        is_gm = msg_row["author_name"] in gm_authors

        result.append({
            "author": author,
            "is_gm": is_gm,
            "timestamp": msg_row["timestamp"] or "",
            "content": msg_row["content"] or "",
        })

    return result


# -- Knowledge base generators (Phase 5) ---------------------------------------

STOP_WORDS_MATCH = {"de", "du", "des", "la", "le", "les", "l", "en", "et", "a", "au", "aux", "un", "une", "pour", "dans", "sur", "par"}


def _fuzzy_name_score(name_a: str, name_b: str) -> float:
    """Score how well two names match. Higher = better. 0 = no match.

    Uses significant word overlap (ignoring French stop words).
    Returns ratio of common significant words to total significant words.
    """
    words_a = set(name_a.lower().split()) - STOP_WORDS_MATCH
    words_b = set(name_b.lower().split()) - STOP_WORDS_MATCH
    if not words_a or not words_b:
        return 0.0
    common = words_a & words_b
    if not common:
        return 0.0
    # Score = common / max(len_a, len_b) -- penalizes partial matches
    return len(common) / max(len(words_a), len(words_b))


def _find_best_tech_match(entity: dict, tech_names: set[str]) -> str | None:
    """Find the best matching tech for an entity, or None.

    Tries: exact match, substring, then best fuzzy score (>= 0.5).
    Also checks entity aliases.
    """
    names_to_check = [entity["canonical_name"]]
    if entity.get("aliases"):
        names_to_check.extend(entity["aliases"])

    best_match = None
    best_score = 0.0

    for name in names_to_check:
        name_lower = name.lower()
        for tn in tech_names:
            tn_lower = tn.lower()
            # Exact
            if tn_lower == name_lower:
                return tn
            # Substring
            if tn_lower in name_lower or name_lower in tn_lower:
                return tn
            # Fuzzy score
            score = _fuzzy_name_score(name, tn)
            if score > best_score:
                best_score = score
                best_match = tn

    return best_match if best_score >= 0.5 else None


def _find_best_entity_match(tech_name: str, entity_lookup: dict[str, dict]) -> dict | None:
    """Find the best matching entity for a tech name, or None.

    Tries: exact match, substring, then best fuzzy score (>= 0.5).
    """
    tech_lower = tech_name.lower()

    # Exact
    if tech_lower in entity_lookup:
        return entity_lookup[tech_lower]

    best_match = None
    best_score = 0.0

    for ename, edata in entity_lookup.items():
        # Substring
        if tech_lower in ename or ename in tech_lower:
            return edata
        # Fuzzy score
        score = _fuzzy_name_score(tech_name, ename)
        if score > best_score:
            best_score = score
            best_match = edata

    return best_match if best_score >= 0.5 else None


def _build_entity_lookup(conn: sqlite3.Connection, civ_id: int) -> dict[str, dict]:
    """Build a lowercase name -> entity dict for matching techs to entities.

    Matches on canonical_name and aliases.
    """
    lookup: dict[str, dict] = {}
    entities = conn.execute(
        "SELECT id, canonical_name, entity_type, description FROM entity_entities WHERE civ_id = ? AND is_active = 1",
        (civ_id,),
    ).fetchall()
    for e in entities:
        lookup[e["canonical_name"].lower()] = dict(e)

    aliases = conn.execute(
        """SELECT a.alias, e.id, e.canonical_name, e.entity_type, e.description
           FROM entity_aliases a
           JOIN entity_entities e ON a.entity_id = e.id
           WHERE e.civ_id = ? AND e.is_active = 1""",
        (civ_id,),
    ).fetchall()
    for a in aliases:
        lookup[a["alias"].lower()] = {
            "id": a["id"], "canonical_name": a["canonical_name"],
            "entity_type": a["entity_type"], "description": a["description"],
        }

    return lookup


def _wikify_item(text: str, entity_lookup: dict[str, dict]) -> str:
    """Linkify text if it matches or contains a known entity name.

    Uses relative path ../entities/{slug}.md (from knowledge/ pages).
    """
    text_stripped = text.strip()

    # Exact match (case-insensitive)
    if text_stripped.lower() in entity_lookup:
        entity = entity_lookup[text_stripped.lower()]
        slug = slugify(entity["canonical_name"])
        return f"[{text_stripped}](../entities/{slug}.md)"

    # Partial match: search for entity names inside the text (longest first to avoid conflicts)
    result = text_stripped
    already_linked: set[str] = set()
    for name_lower in sorted(entity_lookup.keys(), key=len, reverse=True):
        if name_lower in already_linked or len(name_lower) < 4:
            continue
        idx = result.lower().find(name_lower)
        if idx >= 0:
            entity = entity_lookup[name_lower]
            slug = slugify(entity["canonical_name"])
            found_text = result[idx : idx + len(name_lower)]
            link = f"[{found_text}](../entities/{slug}.md)"
            result = result[:idx] + link + result[idx + len(name_lower) :]
            already_linked.add(name_lower)
            break  # One entity link per item to keep output clean

    return result


def generate_tech_page(conn: sqlite3.Connection, civ_id: int, civ_name: str, output_dir: str) -> None:
    """Generate technology index page + individual tech pages for a civilization.

    Creates:
    - civilizations/{civ_slug}/knowledge/technologies.md (index with links)
    - civilizations/{civ_slug}/knowledge/tech/{slug}.md (per-tech detail page)
    """
    civ_slug = slugify(civ_name)
    tech_tree = get_tech_tree(conn, civ_id)

    if not tech_tree:
        return  # No technologies to display

    entity_lookup = _build_entity_lookup(conn, civ_id)

    # Categorization keywords
    categories = {
        "Outils de chasse": ["gourdin", "pieux", "arc", "fleche", "lance", "harpon", "chasseur"],
        "Outils de peche": ["filet", "ligne", "hamecon", "peche", "nasse", "poisson"],
        "Agriculture": ["semence", "irrigation", "culture", "plantation", "recolte", "agriculture", "champ"],
        "Artisanat": ["tissage", "poterie", "vannerie", "tannage", "artisan", "metier"],
        "Construction": ["cabane", "palissade", "maison", "construction", "batiment", "architecture"],
    }

    # Build category mapping
    tech_by_category: dict[str, list[tuple[str, int]]] = {cat: [] for cat in categories}
    tech_by_category["Autre"] = []

    # Collect all unique techs for individual page generation
    all_techs: dict[str, list[int]] = {}  # tech_name -> [turn_numbers]

    lines = [
        f"# Arbre Technologique",
        "",
        "## Timeline chronologique",
        "",
    ]

    # Chronological section
    for turn_num, techs in tech_tree:
        tech_links = []
        for tech in techs:
            tslug = slugify(tech)
            tech_links.append(f"[{tech}](tech/{tslug}.md)")
            all_techs.setdefault(tech, []).append(turn_num)

        lines.append(f"**Tour {turn_num}** -> {', '.join(tech_links)}")

        # Categorize each tech
        for tech in techs:
            tech_lower = tech.lower()
            categorized = False
            for cat, keywords in categories.items():
                if any(kw in tech_lower for kw in keywords):
                    tech_by_category[cat].append((tech, turn_num))
                    categorized = True
                    break
            if not categorized:
                tech_by_category["Autre"].append((tech, turn_num))

    lines.append("")
    lines.append("## Par categorie")
    lines.append("")

    # Category sections with emojis
    category_emojis = {
        "Outils de chasse": "🛠️",
        "Outils de peche": "🎣",
        "Agriculture": "🌾",
        "Artisanat": "🎨",
        "Construction": "🏗️",
        "Autre": "📦",
    }

    for cat, emoji in category_emojis.items():
        if tech_by_category[cat]:
            lines.append(f"### {emoji} {cat}")
            lines.append("")
            for tech, turn_num in tech_by_category[cat]:
                tslug = slugify(tech)
                lines.append(f"- [{tech}](tech/{tslug}.md) (Tour {turn_num})")
            lines.append("")

    # Write index page
    content = "\n".join(lines)
    out_path = Path(output_dir) / "civilizations" / civ_slug / "knowledge"
    _write_page(out_path / "technologies.md", content)

    # Build tech -> category mapping for individual pages
    tech_categories: dict[str, str] = {}
    for cat, tech_list in tech_by_category.items():
        for tech, _ in tech_list:
            tech_categories[tech] = cat

    # Generate individual tech pages
    for tech_name, turn_numbers in all_techs.items():
        _generate_single_tech_page(
            conn, civ_id, civ_name, civ_slug, tech_name, turn_numbers,
            entity_lookup, all_techs, tech_categories, output_dir,
        )


def _generate_single_tech_page(
    conn: sqlite3.Connection,
    civ_id: int,
    civ_name: str,
    civ_slug: str,
    tech_name: str,
    turn_numbers: list[int],
    entity_lookup: dict[str, dict],
    all_techs: dict[str, list[int]],
    tech_categories: dict[str, str],
    output_dir: str,
) -> None:
    """Generate an individual technology detail page.

    Focus: gameplay/practical -- acquisition, category, same-era techs,
    tech timeline (before/after), cross-link to entity for narrative.
    """
    tslug = slugify(tech_name)
    first_turn = min(turn_numbers)
    category = tech_categories.get(tech_name, "Autre")

    # Cross-link to entity page if exists
    matched_entity = _find_best_entity_match(tech_name, entity_lookup)

    lines = [
        f"# {tech_name}",
        "",
        f"*Technologie* -- {civ_name}",
        "",
        "| | |",
        "|---|---|",
        f"| **Acquisition** | Tour {first_turn} |",
        f"| **Categorie** | {category} |",
    ]

    if len(turn_numbers) > 1:
        lines.append(f"| **Re-mentionne** | Tours {', '.join(str(t) for t in sorted(turn_numbers))} |")

    if matched_entity:
        entity_slug = slugify(matched_entity["canonical_name"])
        lines.append(f"| **Fiche narrative** | [Voir la page entite](../../entities/{entity_slug}.md) |")

    lines.append("")

    # Same-era techs (acquired same turn)
    same_turn_techs = [
        t for t, turns in all_techs.items()
        if min(turns) == first_turn and t != tech_name
    ]
    if same_turn_techs:
        lines.extend(["## Acquis en meme temps (Tour {})".format(first_turn), ""])
        for t in same_turn_techs:
            lines.append(f"- [{t}]({slugify(t)}.md)")
        lines.append("")

    # Tech before/after (chronological neighbors)
    all_first_turns = sorted(set(min(turns) for turns in all_techs.values()))
    current_idx = all_first_turns.index(first_turn) if first_turn in all_first_turns else -1

    prev_techs = []
    next_techs = []
    if current_idx > 0:
        prev_turn = all_first_turns[current_idx - 1]
        prev_techs = [t for t, turns in all_techs.items() if min(turns) == prev_turn]
    if current_idx >= 0 and current_idx < len(all_first_turns) - 1:
        next_turn = all_first_turns[current_idx + 1]
        next_techs = [t for t, turns in all_techs.items() if min(turns) == next_turn]

    if prev_techs or next_techs:
        lines.extend(["## Arbre chronologique", ""])
        if prev_techs:
            prev_turn = all_first_turns[current_idx - 1]
            prev_links = ", ".join(f"[{t}]({slugify(t)}.md)" for t in prev_techs)
            lines.append(f"**Tour {prev_turn}** (precedent) : {prev_links}")
        lines.append(f"**Tour {first_turn}** (actuel) : **{tech_name}**")
        if next_techs:
            next_turn = all_first_turns[current_idx + 1]
            next_links = ", ".join(f"[{t}]({slugify(t)}.md)" for t in next_techs)
            lines.append(f"**Tour {next_turn}** (suivant) : {next_links}")
        lines.append("")

    # Same-category techs
    same_cat_techs = [
        t for t, cat in tech_categories.items()
        if cat == category and t != tech_name
    ]
    if same_cat_techs:
        lines.extend([f"## Meme categorie : {category}", ""])
        for t in sorted(same_cat_techs, key=lambda x: min(all_techs.get(x, [99]))):
            t_turn = min(all_techs.get(t, [0]))
            lines.append(f"- [{t}]({slugify(t)}.md) (Tour {t_turn})")
        lines.append("")

    # Narrative excerpt -- search with stem-aware matching, fallback to summary
    turn = conn.execute(
        "SELECT id, summary FROM turn_turns WHERE civ_id = ? AND turn_number = ?",
        (civ_id, first_turn),
    ).fetchone()
    found_excerpt = False
    if turn:
        segments = conn.execute(
            "SELECT content FROM turn_segments WHERE turn_id = ? ORDER BY segment_order",
            (turn["id"],),
        ).fetchall()

        # Build search variants: exact, without trailing s/x/es, first word
        tech_lower = tech_name.lower()
        search_variants = [tech_lower]
        # Singular forms
        if tech_lower.endswith("x") or tech_lower.endswith("s"):
            search_variants.append(tech_lower[:-1])
        if tech_lower.endswith("es"):
            search_variants.append(tech_lower[:-2])
        # First significant word (for multi-word techs)
        first_word = tech_lower.split()[0] if " " in tech_lower else None
        if first_word and len(first_word) > 3:
            search_variants.append(first_word)

        for seg in segments:
            seg_lower = seg["content"].lower()
            for variant in search_variants:
                pos = seg_lower.find(variant)
                if pos != -1:
                    content = seg["content"]
                    start = max(0, pos - 150)
                    end = min(len(content), pos + len(variant) + 150)
                    excerpt = content[start:end].strip()
                    if start > 0:
                        excerpt = "..." + excerpt
                    if end < len(content):
                        excerpt = excerpt + "..."
                    lines.extend([
                        "## Extrait narratif",
                        "",
                        f"> {excerpt}",
                        "",
                    ])
                    found_excerpt = True
                    break
            if found_excerpt:
                break

        # Fallback: turn summary if no excerpt found
        if not found_excerpt and turn["summary"]:
            lines.extend([
                "## Contexte (Tour {})".format(first_turn),
                "",
                f"{turn['summary']}",
                "",
            ])

    lines.extend([
        "---",
        f"[Retour a l'arbre technologique](../technologies.md)",
        "",
    ])

    content = "\n".join(lines)
    out_path = Path(output_dir) / "civilizations" / civ_slug / "knowledge" / "tech"
    _write_page(out_path / f"{tslug}.md", content)


def generate_resources_page(conn: sqlite3.Connection, civ_id: int, civ_name: str, output_dir: str) -> None:
    """Generate resources knowledge base page for a civilization.

    Creates civilizations/{civ_slug}/knowledge/resources.md with:
    - Resources by turn (with entity links)
    - Resources by category (6 categories)
    """
    civ_slug = slugify(civ_name)
    entity_lookup = _build_entity_lookup(conn, civ_id)

    # Query resources from turn_turns
    rows = conn.execute(
        """SELECT turn_number, resources
           FROM turn_turns
           WHERE civ_id = ? AND resources IS NOT NULL AND resources != '[]'
           ORDER BY turn_number""",
        (civ_id,)
    ).fetchall()

    if not rows:
        return  # No resources to display

    # Categorization: ordered by priority (first match wins)
    category_order = ["Nourriture", "Végétaux", "Faune", "Matériaux", "Minéraux", "Artisanat", "Autre"]
    category_keywords: dict[str, list[str]] = {
        "Nourriture": [
            "viande", "poisson", "fruit", "légume", "céréale", "nourriture",
            "gibier", "baie", "recolt", "pêch", "mets", "fumé", "fumee",
            "saumon", "chair", "lait", "oeuf", "œuf", "miel",
        ],
        "Végétaux": [
            "herbe", "graine", "tubercule", "fleur", "plante", "champignon",
            "racine", "gingembre", "épice", "condiment", "algue", "bambou",
            "roseau", "baie", "noix", "résine", "parfum",
        ],
        "Faune": [
            "peau", "fourrure", "cuir", "plume", "écaille", "corne",
            "griffe", "os", "nanton",
        ],
        "Matériaux": [
            "bois", "pierre", "argile", "silex", "roche", "sable",
            "gravier", "terre", "calcaire", "granit",
        ],
        "Minéraux": [
            "cuivre", "bronze", "fer", "or", "argent", "métal", "minerai",
            "cristal", "sel", "obsidienne",
        ],
        "Artisanat": [
            "matériau travaillé", "matériaux travaillés", "matériau travaille",
            "materiaux travaille", "matériaux pour", "materiaux pour",
            "matériaux de", "materiaux de", "outil", "objet", "contenant", "tissu",
        ],
    }

    resource_by_category: dict[str, list[tuple[str, int]]] = {cat: [] for cat in category_order}

    lines = [
        "# Index des Ressources",
        "",
        "## Par tour",
        "",
    ]

    # Chronological section
    for row in rows:
        resources = _parse_json_list(row["resources"])
        if not resources:
            continue

        resources = sorted(set(resources))
        linked_resources = [_wikify_item(r, entity_lookup) for r in resources]
        resource_list = ", ".join(linked_resources)
        lines.append(f"**Tour {row['turn_number']}** : {resource_list}")

        # Categorize (original text, not linked version)
        for res in resources:
            res_lower = res.lower()
            categorized = False
            for cat in category_order[:-1]:  # skip "Autre"
                keywords = category_keywords[cat]
                if any(kw in res_lower for kw in keywords):
                    resource_by_category[cat].append((res, row["turn_number"]))
                    categorized = True
                    break
            if not categorized:
                resource_by_category["Autre"].append((res, row["turn_number"]))

    lines.append("")
    lines.append("## Par catégorie")
    lines.append("")

    category_emojis = {
        "Nourriture": "🍖",
        "Végétaux": "🌿",
        "Faune": "🦌",
        "Matériaux": "🪨",
        "Minéraux": "⚒️",
        "Artisanat": "🔨",
        "Autre": "📦",
    }

    for cat in category_order:
        items = resource_by_category[cat]
        if not items:
            continue
        emoji = category_emojis[cat]
        lines.append(f"### {emoji} {cat}")
        lines.append("")
        seen: set[str] = set()
        for res, turn_num in items:
            if res.lower() not in seen:
                seen.add(res.lower())
                linked = _wikify_item(res, entity_lookup)
                lines.append(f"- {linked} (Tour {turn_num})")
        lines.append("")

    # Write page
    content = "\n".join(lines)
    out_path = Path(output_dir) / "civilizations" / civ_slug / "knowledge"
    _write_page(out_path / "resources.md", content)


def generate_beliefs_page(conn: sqlite3.Connection, civ_id: int, civ_name: str, output_dir: str) -> None:
    """Generate beliefs knowledge base page for a civilization.

    Creates civilizations/{civ_slug}/knowledge/beliefs.md with:
    - Castes & Groupes sociaux (from entity_entities directly — clean source)
    - Rituels, Cosmologie, Valeurs, Autres (concise belief statements from turn_turns.beliefs)

    Design: no per-turn chronological dump. Entity names (which have their own pages)
    are excluded from thematic sections to avoid duplication.
    """
    civ_slug = slugify(civ_name)
    entity_lookup = _build_entity_lookup(conn, civ_id)

    # Query beliefs from turn_turns
    rows = conn.execute(
        """SELECT turn_number, beliefs
           FROM turn_turns
           WHERE civ_id = ? AND beliefs IS NOT NULL AND beliefs != '[]'
           ORDER BY turn_number""",
        (civ_id,)
    ).fetchall()

    # Query spiritual entities directly — clean, authoritative source
    # Castes: always spiritual (social groups with cosmological role)
    # Events: except diseases
    # Institutions: only those with spiritual/ritual keywords in name
    _SPIRITUAL_INST_KW = {
        "esprit", "oracle", "sage", "autel", "rituel", "rite",
        "gardien", "tribunal", "arbitre", "porteur", "ancetre", "ancêtre",
    }
    _DISEASE_KW = {"maladie", "épidémie", "epidemie"}

    spiritual_entities = conn.execute(
        """SELECT canonical_name, entity_type, first_seen_turn
           FROM entity_entities
           WHERE civ_id = ?
           ORDER BY first_seen_turn""",
        (civ_id,)
    ).fetchall()
    # Filter to only truly spiritual entities
    figures: list[tuple[str, int]] = []
    seen_fig: set[str] = set()
    for e in spiritual_entities:
        name = e["canonical_name"]
        etype = e["entity_type"]
        turn = e["first_seen_turn"] or 0
        key = name.lower()
        if key in seen_fig:
            continue
        name_lower = name.lower()
        if etype == "caste":
            figures.append((name, turn))
            seen_fig.add(key)
        elif etype == "event" and not any(kw in name_lower for kw in _DISEASE_KW):
            figures.append((name, turn))
            seen_fig.add(key)
        elif etype == "institution" and any(kw in name_lower for kw in _SPIRITUAL_INST_KW):
            figures.append((name, turn))
            seen_fig.add(key)

    # Noise: Discord meta, markdown artifacts, bold headers
    _NOISE_BELIEF = re.compile(
        r'Lootbox|Choix\s*:|Option libre|\*\*Option\s*\d|^##|^>\s|^-\s*$'
        r'|^Organisation\s*:|^\*\*?\w.*\*\*?$',
        re.IGNORECASE,
    )
    # Narrative sentence starters (case-insensitive: these words always signal narrative)
    _NARRATIVE_START = re.compile(
        r'^(Et |Mais |Parfois|Car |Or |Ainsi |En tant |'
        r'Je |J\'|Tu |Vous |Il |Elle |Ils |Elles |'
        r'D\'autres |D\'autant |Certain|Rare |'
        r'Au son |A la |À la |Lors |Quand |Comme si |'
        r'Ou |Telle |Que |Né |L\'un |'
        r'\*|>|\[)',
        re.IGNORECASE,
    )
    # Uppercase article starting a sentence = narrative (NOT lowercase = LLM belief phrase)
    # e.g. "Les Premiers Ancêtres ont bâti..." (bad) vs "les esprits des ancêtres..." (good)
    _UPPERCASE_ARTICLE_SENTENCE = re.compile(
        r'^(Le |La |Les |L\'|Un |Une |Des |Du )'
    )  # NO IGNORECASE — only matches when first letter is actually uppercase

    def _is_concise_belief(b: str) -> bool:
        """True if item looks like a belief/concept, not a narrative fragment."""
        b = b.strip()
        if len(b) < 8 or len(b) > 70:
            return False
        if _NOISE_BELIEF.search(b):
            return False
        if b.endswith(":") or b.endswith("…"):
            return False
        if _NARRATIVE_START.match(b):
            return False
        # Uppercase article + more than 3 words = narrative sentence
        # (lowercase article = LLM concept phrase, keep it)
        if _UPPERCASE_ARTICLE_SENTENCE.match(b) and len(b.split()) > 3:
            return False
        # Reject 2nd person direct address
        if " tu " in b.lower() or b.lower().startswith("tu "):
            return False
        # Reject 1st person conjugations (narrative voice)
        if "m'ont" in b or " nous ferons" in b.lower() or " leur a " in b.lower():
            return False
        # Reject observational sentences ("X est important dans...", "sont importantes")
        if re.search(r'\b(est important|sont important|a tendance|commence à|s\'en retrouve)', b, re.IGNORECASE):
            return False
        # Reject pure entity names — they have their own pages
        if b.lower() in entity_lookup:
            return False
        # Also reject "le/la/les + entity_name" (article + entity)
        b_stripped = re.sub(r'^(le |la |les |l\'|un |une |du |des )', '', b.lower()).strip()
        if b_stripped in entity_lookup:
            return False
        return True

    ritual_kw = {"rituel", "cérémonie", "offrande", "sacrifice", "célébration", "fête", "partage", "rite"}
    cosmo_kw = {"esprit", "âme", "ame", "ciel", "mort", "ancêtre", "ancetre", "au-delà", "au-dela",
                "cieux", "divin", "sacré", "sacre", "réincarnation", "reincarnation",
                "esprits", "bénédiction", "benediction", "cosmos", "céleste", "celeste"}
    values_kw = {"sacralité", "sacralite", "piété", "piete", "rôle", "role", "dialogue", "coutume",
                 "famille", "coopération", "cooperation", "valoris", "mission", "loi",
                 "exil", "respect", "parenté", "parente", "juridiction", "devoir", "honneur", "honorer"}

    rituals: list[tuple[str, int]] = []
    cosmo: list[tuple[str, int]] = []
    values: list[tuple[str, int]] = []
    others: list[tuple[str, int]] = []

    for row in rows:
        beliefs = _parse_json_list(row["beliefs"])
        for belief in beliefs:
            belief = belief.strip()
            if not _is_concise_belief(belief):
                continue
            b_lower = belief.lower()
            if any(kw in b_lower for kw in ritual_kw):
                rituals.append((belief, row["turn_number"]))
            elif any(kw in b_lower for kw in cosmo_kw):
                cosmo.append((belief, row["turn_number"]))
            elif any(kw in b_lower for kw in values_kw):
                values.append((belief, row["turn_number"]))
            else:
                others.append((belief, row["turn_number"]))

    lines = ["# Système de Croyances", ""]

    # Section 1: Figures vénérées — sourced from entity_entities (clean, authoritative)
    if figures:
        lines += ["## ✨ Figures & Entités vénérées", ""]
        for name, turn in sorted(figures, key=lambda x: x[1]):
            slug = slugify(name)
            turn_str = f" *(Tour {turn})*" if turn else ""
            lines.append(f"- [{name}](../entities/{slug}.md){turn_str}")
        lines.append("")

    def _section(title: str, emoji: str, items: list[tuple[str, int]]) -> None:
        if not items:
            return
        lines.append(f"## {emoji} {title}")
        lines.append("")
        seen: set[str] = set()
        for item, turn_num in sorted(items, key=lambda x: x[1]):
            if item.lower() not in seen:
                seen.add(item.lower())
                linked = _wikify_item(item, entity_lookup)
                lines.append(f"- {linked} *(Tour {turn_num})*")
        lines.append("")

    _section("Rituels & Pratiques", "🕯️", rituals)
    _section("Cosmologie & Spiritualité", "🌌", cosmo)
    _section("Valeurs & Normes sociales", "⚖️", values)
    _section("Autres croyances", "📿", others)

    content = "\n".join(lines)
    out_path = Path(output_dir) / "civilizations" / civ_slug / "knowledge"
    _write_page(out_path / "beliefs.md", content)


def generate_geography_page(conn: sqlite3.Connection, civ_id: int, civ_name: str, output_dir: str) -> None:
    """Generate geography knowledge base page for a civilization.

    Creates civilizations/{civ_slug}/knowledge/geography.md with:
    - Lieux par ordre de découverte
    - Carte textuelle (ASCII tree based on detected hierarchy)
    """
    civ_slug = slugify(civ_name)

    # Query geography from turn_turns
    rows = conn.execute(
        """SELECT turn_number, geography
           FROM turn_turns
           WHERE civ_id = ? AND geography IS NOT NULL AND geography != '[]'
           ORDER BY turn_number""",
        (civ_id,)
    ).fetchall()

    if not rows:
        return  # No geography to display

    lines = [
        f"# Géographie",
        "",
        "## Lieux par ordre de découverte",
        "",
    ]

    all_places = []

    # Chronological section
    for row in rows:
        places = _parse_json_list(row["geography"])
        if not places:
            continue

        # Deduplicate
        places = sorted(set(places))

        place_list = ", ".join(places)
        lines.append(f"**Tour {row['turn_number']}** : {place_list}")

        for place in places:
            all_places.append(place)

    lines.append("")

    # Build ASCII tree based on detected hierarchy
    if all_places:
        lines.append("## Carte textuelle")
        lines.append("")
        lines.append("```")

        # Simple heuristic: detect hierarchical keywords
        hierarchy_patterns = {
            "vallée": 0,
            "région": 0,
            "rivière": 1,
            "fleuve": 1,
            "village": 2,
            "campement": 3,
            "crête": 1,
            "montagne": 1,
            "forêt": 1,
        }

        # Categorize places by hierarchy level
        by_level: dict[int, list[str]] = {0: [], 1: [], 2: [], 3: []}

        # Deduplicate all_places
        unique_places = []
        seen = set()
        for place in all_places:
            if place.lower() not in seen:
                seen.add(place.lower())
                unique_places.append(place)

        for place in unique_places:
            place_lower = place.lower()
            level = 3  # Default to deepest level
            for keyword, lvl in hierarchy_patterns.items():
                if keyword in place_lower:
                    level = lvl
                    break
            by_level[level].append(place)

        # Generate tree
        if by_level[0]:
            # Main locations at root
            for i, place in enumerate(by_level[0]):
                is_last_root = (i == len(by_level[0]) - 1)
                lines.append(place)

                # Sub-locations
                if by_level[1]:
                    for j, sub in enumerate(by_level[1]):
                        is_last_sub = (j == len(by_level[1]) - 1) and not by_level[2]
                        prefix = "└─" if is_last_sub else "├─"
                        lines.append(f"{prefix} {sub}")

                # Villages/settlements
                if by_level[2]:
                    prefix = "└─" if not by_level[3] else "├─"
                    lines.append(f"{prefix} Villages")
                    for k, village in enumerate(by_level[2]):
                        is_last_village = (k == len(by_level[2]) - 1) and not by_level[3]
                        v_prefix = "   └─" if is_last_village else "   ├─"
                        lines.append(f"{v_prefix} {village}")

                # Campements
                if by_level[3]:
                    for m, camp in enumerate(by_level[3]):
                        is_last_camp = (m == len(by_level[3]) - 1)
                        c_prefix = "      └─" if is_last_camp else "      ├─"
                        lines.append(f"{c_prefix} {camp}")
        else:
            # No main location, list everything flat
            for place in unique_places[:10]:  # Limit to 10
                lines.append(f"- {place}")

        lines.append("```")
        lines.append("")

    # Write page
    content = "\n".join(lines)
    out_path = Path(output_dir) / "civilizations" / civ_slug / "knowledge"
    _write_page(out_path / "geography.md", content)


# -- Analytics pages (Phase 6) -------------------------------------------------

def generate_choices_page(conn: sqlite3.Connection, civ_id: int, civ_name: str, output_dir: str) -> None:
    """Generate choices/decisions page for a civilization.

    Creates civilizations/{civ_slug}/knowledge/choices.md with:
    - Chronological list of all GM-proposed choices and player decisions
    """
    civ_slug = slugify(civ_name)

    rows = conn.execute("""
        SELECT turn_number, title, summary, choices_proposed, choices_made
        FROM turn_turns
        WHERE civ_id = ? AND (choices_proposed IS NOT NULL OR choices_made IS NOT NULL)
        ORDER BY turn_number
    """, (civ_id,)).fetchall()

    if not rows:
        return  # No choices to display

    lines = [
        "# Choix et Decisions",
        "",
        f"Historique des choix proposes par le MJ et des decisions prises par le joueur pour **{civ_name}**.",
        "",
    ]

    for row in rows:
        turn_num = row["turn_number"]
        title = row["title"] or "(sans titre)"
        summary = row["summary"] or ""

        lines.append(f"## Tour {turn_num} : {title}")
        lines.append("")
        if summary:
            lines.append(f"*{summary[:200]}*")
            lines.append("")

        proposed = _parse_json_list(row["choices_proposed"])
        if proposed:
            lines.append('??? question "Choix proposes"')
            for i, choice in enumerate(proposed, 1):
                lines.append(f"    {i}. {choice}")
            lines.append("")

        made = _parse_json_list(row["choices_made"])
        if made:
            lines.append('!!! success "Decision prise"')
            for decision in made:
                lines.append(f"    {decision}")
            lines.append("")

    content = "\n".join(lines)
    out_path = Path(output_dir) / "civilizations" / civ_slug / "knowledge"
    _write_page(out_path / "choices.md", content)


def generate_relations_page(conn: sqlite3.Connection, civ_id: int, civ_name: str, output_dir: str) -> None:
    """Generate typed relations page for a civilization.

    Creates civilizations/{civ_slug}/knowledge/relations.md with:
    - Relations grouped by type (controls, member_of, located_in, etc.)
    """
    civ_slug = slugify(civ_name)

    rows = conn.execute("""
        SELECT r.relation_type, r.description,
               s.canonical_name AS source_name, s.entity_type AS source_type,
               t.canonical_name AS target_name, t.entity_type AS target_type,
               tt.turn_number
        FROM entity_relations r
        JOIN entity_entities s ON r.source_entity_id = s.id
        JOIN entity_entities t ON r.target_entity_id = t.id
        LEFT JOIN turn_turns tt ON r.turn_id = tt.id
        WHERE r.is_active = 1 AND (s.civ_id = ? OR t.civ_id = ?)
        ORDER BY r.relation_type, s.canonical_name
    """, (civ_id, civ_id)).fetchall()

    if not rows:
        return  # No relations to display

    lines = [
        "# Relations entre Entites",
        "",
        f"Graphe textuel des relations pour **{civ_name}**.",
        "",
    ]

    # Group by relation type
    by_type: dict[str, list] = {}
    for row in rows:
        rel_type = row["relation_type"]
        by_type.setdefault(rel_type, []).append(row)

    for rel_type, rels in sorted(by_type.items()):
        lines.append(f"## {rel_type.replace('_', ' ').title()} ({len(rels)})")
        lines.append("")
        lines.append("| Source | | Cible | Tour |")
        lines.append("|---|---|---|---|")
        for r in rels:
            src = f"{r['source_name']} ({r['source_type']})"
            tgt = f"{r['target_name']} ({r['target_type']})"
            turn = str(r["turn_number"]) if r["turn_number"] else "-"
            lines.append(f"| {src} | --> | {tgt} | {turn} |")
        lines.append("")

    content = "\n".join(lines)
    out_path = Path(output_dir) / "civilizations" / civ_slug / "knowledge"
    _write_page(out_path / "relations.md", content)


def generate_analytics_page(conn: sqlite3.Connection, civ_id: int, civ_name: str, output_dir: str) -> None:
    """Generate analytics page for a civilization.

    Creates civilizations/{civ_slug}/analytics.md with:
    - Evolution des entites decouvertes (bar chart by turn)
    - Densite narrative par tour (segments count bar chart)
    - Top 20 entites (mentions with bars)
    - Tours cles (turns with >5 new entities or >10 segments)
    """
    civ_slug = slugify(civ_name)

    lines = [
        f"# Analytics — {civ_name}",
        "",
    ]

    # 1. Evolution des entites decouvertes
    new_entities_by_turn = conn.execute(
        """SELECT t.turn_number, COUNT(DISTINCT e.id) as new_count
           FROM entity_entities e
           JOIN turn_turns t ON e.first_seen_turn = t.id
           WHERE e.civ_id = ?
           GROUP BY t.turn_number
           ORDER BY t.turn_number""",
        (civ_id,)
    ).fetchall()

    if new_entities_by_turn:
        lines.extend([
            "## 📈 Évolution des entités découvertes",
            "",
            "```",
        ])

        # Filter noise and recalculate
        clean_new_entities = []
        for row in new_entities_by_turn:
            turn_num = row["turn_number"]
            # Count clean entities for this turn
            entities = conn.execute(
                """SELECT e.canonical_name
                   FROM entity_entities e
                   JOIN turn_turns t ON e.first_seen_turn = t.id
                   WHERE e.civ_id = ? AND t.turn_number = ?""",
                (civ_id, turn_num)
            ).fetchall()
            clean_count = sum(1 for e in entities if not is_noise_entity(e["canonical_name"]))
            if clean_count > 0:
                clean_new_entities.append((turn_num, clean_count))

        if clean_new_entities:
            max_new = max(count for _, count in clean_new_entities)
            peak_turn = max(clean_new_entities, key=lambda x: x[1])[0]

            for turn_num, count in clean_new_entities:
                bar_length = int((count / max_new) * 20) if max_new > 0 else 0
                bar = "█" * bar_length if bar_length > 0 else ""
                peak_marker = "  ← Pic" if turn_num == peak_turn and count == max_new else ""
                lines.append(f"Tour {turn_num:2d}: {bar:<20s}{peak_marker}")

        lines.extend(["```", ""])

    # 2. Densite narrative par tour (segment count)
    segments_by_turn = conn.execute(
        """SELECT t.turn_number, COUNT(s.id) as segment_count
           FROM turn_turns t
           LEFT JOIN turn_segments s ON s.turn_id = t.id
           WHERE t.civ_id = ?
           GROUP BY t.turn_number
           ORDER BY t.turn_number""",
        (civ_id,)
    ).fetchall()

    if segments_by_turn:
        lines.extend([
            "## 📊 Densité narrative par tour",
            "",
            "```",
        ])

        max_segments = max(row["segment_count"] for row in segments_by_turn) if segments_by_turn else 1
        peak_seg_turn = max(segments_by_turn, key=lambda x: x["segment_count"])["turn_number"] if segments_by_turn else 0

        for row in segments_by_turn:
            turn_num = row["turn_number"]
            count = row["segment_count"]
            bar_length = int((count / max_segments) * 20) if max_segments > 0 else 0
            bar = "█" * bar_length if bar_length > 0 else ""
            peak_marker = "  ← Pic" if turn_num == peak_seg_turn else ""
            lines.append(f"Tour {turn_num:2d}: {bar:<20s} ({count} segments){peak_marker}")

        lines.extend(["```", ""])

    # 3. Top 20 entites
    top_entities = conn.execute(
        """SELECT e.canonical_name, e.entity_type,
                  COUNT(m.id) as mention_count
           FROM entity_entities e
           JOIN entity_mentions m ON m.entity_id = e.id
           WHERE e.civ_id = ?
           GROUP BY e.id
           ORDER BY mention_count DESC
           LIMIT 30""",
        (civ_id,)
    ).fetchall()

    if top_entities:
        lines.extend([
            "## 🏆 Top 20 entités",
            "",
        ])

        # Filter noise and take first 20 clean entities
        clean_entities = [e for e in top_entities if not is_noise_entity(e["canonical_name"])][:20]

        if clean_entities:
            max_mentions = clean_entities[0]["mention_count"]
            for i, entity in enumerate(clean_entities, 1):
                name = _capitalize_entity(entity["canonical_name"])
                etype_label = _entity_type_label(entity["entity_type"])
                bar_length = int((entity["mention_count"] / max_mentions) * 20) if max_mentions > 0 else 0
                bar = "█" * bar_length if bar_length > 0 else ""
                lines.append(f"{i}. **{name}** ({etype_label}) {bar:<20s} {entity['mention_count']} mentions")
        lines.append("")

    # 4. Tours cles (>5 new entities or >10 segments)
    key_turns = []

    # Check for turns with >5 new entities
    for turn_num, new_count in clean_new_entities if 'clean_new_entities' in locals() else []:
        if new_count > 5:
            key_turns.append((turn_num, f"Explosion de {new_count} nouvelles entités"))

    # Check for turns with >10 segments
    for row in segments_by_turn:
        if row["segment_count"] > 10:
            # Avoid duplicates
            if not any(t[0] == row["turn_number"] for t in key_turns):
                key_turns.append((row["turn_number"], f"Densité narrative élevée ({row['segment_count']} segments)"))
            else:
                # Update existing entry
                for i, (t, desc) in enumerate(key_turns):
                    if t == row["turn_number"]:
                        key_turns[i] = (t, f"Explosion de nouvelles entités + densité narrative ({row['segment_count']} segments)")

    if key_turns:
        lines.extend([
            "## 🎯 Tours clés",
            "",
        ])
        key_turns.sort(key=lambda x: x[0])
        for turn_num, description in key_turns:
            lines.append(f"- **Tour {turn_num}** : {description}")
        lines.append("")

    # Write page
    content = "\n".join(lines)
    out_path = Path(output_dir) / "civilizations" / civ_slug / "knowledge"
    _write_page(out_path / "analytics.md", content)


def generate_entity_network_page(conn: sqlite3.Connection, output_dir: str) -> None:
    """Generate global entity network page.

    Creates global/entity-network.md with:
    - Hub central (entity with most mentions)
    - ASCII tree of top 5 co-occurrences with the hub
    - Clusters par type (top 3 co-occurrences per entity type)
    """
    lines = [
        "# Réseau d'Entités",
        "",
    ]

    # Find hub central (entity with most mentions)
    hub_row = conn.execute(
        """SELECT e.canonical_name, e.entity_type,
                  COUNT(m.id) as mention_count
           FROM entity_entities e
           JOIN entity_mentions m ON m.entity_id = e.id
           GROUP BY e.id
           ORDER BY mention_count DESC
           LIMIT 20"""
    ).fetchall()

    # Filter noise to find the real hub
    clean_hubs = [h for h in hub_row if not is_noise_entity(h["canonical_name"])]

    if not clean_hubs:
        # No clean entities found
        content = "\n".join(lines + ["Aucune entité disponible."])
        _write_page(Path(output_dir) / "global" / "entity-network.md", content)
        return

    hub = clean_hubs[0]
    hub_name = hub["canonical_name"]
    hub_type = hub["entity_type"]
    hub_mentions = hub["mention_count"]

    lines.extend([
        f"## Hub central : {_capitalize_entity(hub_name)} ({hub_mentions} mentions)",
        "",
        "```",
    ])

    # Get co-occurrences for the hub
    # Find entity ID for the hub
    hub_id = conn.execute(
        "SELECT id FROM entity_entities WHERE canonical_name = ? LIMIT 1",
        (hub_name,)
    ).fetchone()

    if hub_id:
        hub_id = hub_id["id"]

        # Get turns where hub appears
        hub_turns = conn.execute(
            """SELECT DISTINCT turn_id
               FROM entity_mentions
               WHERE entity_id = ?""",
            (hub_id,)
        ).fetchall()

        if hub_turns:
            turn_ids = [t["turn_id"] for t in hub_turns]
            turn_placeholders = ",".join("?" * len(turn_ids))

            # Get co-occurring entities
            cooccurring = conn.execute(
                f"""SELECT e.canonical_name, e.entity_type,
                           COUNT(DISTINCT m.turn_id) as turns_together
                    FROM entity_mentions m
                    JOIN entity_entities e ON m.entity_id = e.id
                    WHERE m.turn_id IN ({turn_placeholders})
                      AND m.entity_id != ?
                    GROUP BY e.id
                    HAVING turns_together >= 2
                    ORDER BY turns_together DESC
                    LIMIT 20""",
                turn_ids + [hub_id]
            ).fetchall()

            # Filter noise and take top 5
            clean_cooccurrences = [c for c in cooccurring if not is_noise_entity(c["canonical_name"])][:5]

            # Display ASCII tree
            hub_display = f"{_capitalize_entity(hub_name)} ({_entity_type_label(hub_type).lower()})"
            lines.append(hub_display)

            for i, co in enumerate(clean_cooccurrences):
                is_last = (i == len(clean_cooccurrences) - 1)
                prefix = "└─" if is_last else "├─"
                co_name = _capitalize_entity(co["canonical_name"])
                co_type = _entity_type_label(co["entity_type"]).lower()
                turns = co["turns_together"]
                lines.append(f"{prefix} {co_name} ({co_type}) — {turns} tours ensemble")

    lines.extend(["```", ""])

    # Clusters par type (global co-occurrences grouped by entity type)
    lines.extend([
        "## Clusters par type",
        "",
    ])

    # Get all co-occurrences with min_turns=2
    all_cooccurrences = get_cooccurrences(conn, civ_id=None, min_turns=2)

    # Filter noise
    clean_cooccurrences_all = [
        (e1, e1_type, e2, e2_type, nb)
        for e1, e1_type, e2, e2_type, nb in all_cooccurrences
        if not is_noise_entity(e1) and not is_noise_entity(e2)
    ]

    # Group by entity type
    by_type: dict[str, list[tuple]] = {}
    for e1, e1_type, e2, e2_type, nb in clean_cooccurrences_all:
        # Add to both types
        by_type.setdefault(e1_type, []).append((e1, e2, nb))
        if e2_type != e1_type:
            by_type.setdefault(e2_type, []).append((e2, e1, nb))

    # Sort types by frequency
    type_order = ["caste", "place", "person", "technology", "institution", "civilization", "resource", "creature", "event"]
    sorted_types = sorted(by_type.keys(), key=lambda t: type_order.index(t) if t in type_order else 99)

    for etype in sorted_types[:5]:  # Top 5 types
        pairs = by_type[etype]
        # Deduplicate pairs (e1, e2) and (e2, e1)
        seen = set()
        unique_pairs = []
        for e1, e2, nb in pairs:
            pair_key = tuple(sorted([e1.lower(), e2.lower()]))
            if pair_key not in seen:
                seen.add(pair_key)
                unique_pairs.append((e1, e2, nb))

        # Sort by nb_turns and take top 3
        unique_pairs.sort(key=lambda x: x[2], reverse=True)
        top_pairs = unique_pairs[:3]

        if top_pairs:
            lines.append(f"### {_entity_type_label(etype)}")
            lines.append("")
            for e1, e2, nb in top_pairs:
                e1_cap = _capitalize_entity(e1)
                e2_cap = _capitalize_entity(e2)
                lines.append(f"- {e1_cap} ↔ {e2_cap} ({nb} tours)")
            lines.append("")

    # Write page
    content = "\n".join(lines)
    out_path = Path(output_dir) / "global"
    _write_page(out_path / "entity-network.md", content)


# -- Page generators -----------------------------------------------------------

def generate_index(conn: sqlite3.Connection) -> str:
    """Generate the wiki homepage."""
    civ_count = conn.execute("SELECT count(*) FROM civ_civilizations").fetchone()[0]
    turn_count = conn.execute("SELECT count(*) FROM turn_turns").fetchone()[0]
    entity_count = conn.execute("SELECT count(*) FROM entity_entities").fetchone()[0]
    mention_count = conn.execute("SELECT count(*) FROM entity_mentions").fetchone()[0]

    civs = conn.execute("SELECT name, player_name FROM civ_civilizations ORDER BY name").fetchall()
    civ_lines = []
    for r in civs:
        line = f"- [{r['name']}](civilizations/{slugify(r['name'])}/index.md)"
        if r["player_name"]:
            line += f" *(joueur: {r['player_name']})*"
        civ_lines.append(line)

    now = datetime.now().strftime("%d/%m/%Y %H:%M")

    lines = [
        "# Aurelm Wiki",
        "",
        "Bienvenue sur le wiki du monde d'Aurelm, genere automatiquement a partir des tours de jeu.",
        "",
        "## Statistiques",
        "",
        "| | |",
        "|---|---|",
        f"| Civilisations | **{civ_count}** |",
        f"| Tours de jeu | **{turn_count}** |",
        f"| Entites uniques | **{entity_count}** |",
        f"| Mentions d'entites | **{mention_count}** |",
        "",
        "## Civilisations",
        "",
        *civ_lines,
        "",
        "## Navigation",
        "",
        "- **[Civilisations](civilizations/index.md)** -- Historique et entites de chaque civilisation",
        "- **[Timeline](global/timeline.md)** -- Chronologie globale des tours de jeu",
        "- **[Entites](global/entities.md)** -- Index de toutes les entites par type",
        "- **[Pipeline](meta/pipeline.md)** -- Statistiques du pipeline ML",
        "",
        "---",
        "",
        f"*Derniere mise a jour : {now}*",
        "",
    ]
    return "\n".join(lines)


def generate_enriched_index(conn: sqlite3.Connection) -> str:
    """Generate enriched wiki dashboard with stats, activity graph, top entities, and recent turns.

    This is the Phase 3 implementation from REFACTOR_PLAN.md with:
    - Global stats table
    - ASCII activity graph by month
    - Top 10 entities with ASCII bars
    - Recent 5 turns with preview and Discord date
    - Quick navigation links
    """
    # Global stats
    turn_count = conn.execute("SELECT count(*) FROM turn_turns").fetchone()[0]
    entity_count = conn.execute("SELECT count(*) FROM entity_entities").fetchone()[0]
    mention_count = conn.execute("SELECT count(*) FROM entity_mentions").fetchone()[0]

    # Count technologies and resources from JSON fields
    tech_count = 0
    resource_count = 0
    turns_with_data = conn.execute(
        "SELECT technologies, resources FROM turn_turns WHERE technologies IS NOT NULL OR resources IS NOT NULL"
    ).fetchall()
    for row in turns_with_data:
        if row["technologies"]:
            tech_count += len(_parse_json_list(row["technologies"]))
        if row["resources"]:
            resource_count += len(_parse_json_list(row["resources"]))

    now = datetime.now().strftime("%d/%m/%Y %H:%M")

    lines = [
        "# Wiki Aurelm",
        "",
        "Bienvenue sur le wiki automatise du monde d'Aurelm. Ce wiki est genere a partir des tours de jeu Discord.",
        "",
        "## Statistiques globales",
        "",
        "| Tours | Entites | Mentions | Technologies | Ressources |",
        "|-------|---------|----------|--------------|------------|",
        f"| **{turn_count}** | **{entity_count}** | **{mention_count}** | **{tech_count}** | **{resource_count}** |",
        "",
    ]

    # Activity by month using get_activity_by_month()
    activity = get_activity_by_month(conn, civ_id=None)

    if activity:
        lines.extend([
            "## Activite par mois",
            "",
            "```",
        ])
        max_turns = max(count for _, count in activity) if activity else 1
        for year_month, count in activity:
            if year_month:
                # Format month as "Sept 2024"
                try:
                    year, month = year_month.split("-")
                    month_names = ["", "Jan", "Fev", "Mars", "Avr", "Mai", "Juin",
                                   "Juil", "Aout", "Sept", "Oct", "Nov", "Dec"]
                    month_label = f"{month_names[int(month)]} {year}"
                except (ValueError, IndexError):
                    month_label = year_month
            else:
                month_label = "(non date)"

            # Scale bars to max 20 chars
            bar_length = int((count / max_turns) * 20)
            bar = "█" * bar_length if bar_length > 0 else ""
            lines.append(f"{month_label:12s} {bar:<20s} {count} tours")
        lines.extend(["```", ""])

    # Top 10 entities by mentions
    top_entities = conn.execute(
        """SELECT e.canonical_name, e.entity_type,
                  COUNT(m.id) as mention_count
           FROM entity_entities e
           JOIN entity_mentions m ON m.entity_id = e.id
           GROUP BY e.id
           ORDER BY mention_count DESC
           LIMIT 15"""
    ).fetchall()

    if top_entities:
        lines.extend([
            "## Top 10 Entites (par mentions)",
            "",
        ])
        # Filter noise and take first 10 clean entities
        clean_entities = [e for e in top_entities if not is_noise_entity(e["canonical_name"])][:10]

        if clean_entities:
            max_mentions = clean_entities[0]["mention_count"]
            for i, entity in enumerate(clean_entities, 1):
                name = _capitalize_entity(entity["canonical_name"])
                etype = entity["entity_type"]
                # Scale bars to max 20 chars
                bar_length = int((entity["mention_count"] / max_mentions) * 20)
                bar = "█" * bar_length if bar_length > 0 else ""
                lines.append(f"{i}. **{name}** ({etype}) {bar:<20s} {entity['mention_count']} mentions")
        lines.append("")

    # Recent 5 turns with preview and Discord date
    recent_turns = conn.execute(
        """SELECT t.id, t.turn_number, t.summary, c.name as civ_name,
                  MIN(m.timestamp) as discord_date
           FROM turn_turns t
           JOIN civ_civilizations c ON t.civ_id = c.id
           LEFT JOIN json_each(t.raw_message_ids) AS msg_id
           LEFT JOIN turn_raw_messages m ON CAST(msg_id.value AS INTEGER) = m.id
           GROUP BY t.id
           ORDER BY t.turn_number DESC
           LIMIT 5"""
    ).fetchall()

    if recent_turns:
        lines.extend([
            "## Derniers tours",
            "",
        ])
        for turn in recent_turns:
            civ_slug = slugify(turn["civ_name"])
            turn_link = f"civilizations/{civ_slug}/turns/turn-{turn['turn_number']:02d}.md"

            # Format date
            date_str = ""
            if turn["discord_date"]:
                try:
                    # Parse ISO timestamp
                    dt = datetime.fromisoformat(turn["discord_date"].replace("Z", "+00:00"))
                    date_str = dt.strftime("%d/%m/%Y")
                except (ValueError, AttributeError):
                    date_str = str(turn["discord_date"])[:10]

            summary_preview = _clean_summary(turn["summary"] or "")[:100]
            if date_str:
                lines.append(f"- **[Tour {turn['turn_number']}]({turn_link})** — *{date_str}* — {summary_preview}...")
            else:
                lines.append(f"- **[Tour {turn['turn_number']}]({turn_link})** — {summary_preview}...")
        lines.append("")

    # Navigation rapide
    lines.extend([
        "## Navigation rapide",
        "",
        "- **[Civilisations](civilizations/index.md)** — Vue d'ensemble des civilisations",
        "- **[Timeline globale](global/timeline.md)** — Chronologie complete",
        "- **[Index des entites](global/entities.md)** — Toutes les entites par type",
        "- **[Pipeline](meta/pipeline.md)** — Statistiques du pipeline ML",
        "",
        "---",
        "",
        f"*Derniere mise a jour : {now}*",
        "",
    ])

    return "\n".join(lines)


def generate_civilizations_index(conn: sqlite3.Connection) -> str:
    """Generate the civilizations list page."""
    civs = conn.execute(
        "SELECT c.*, COUNT(t.id) as turn_count "
        "FROM civ_civilizations c LEFT JOIN turn_turns t ON t.civ_id = c.id "
        "GROUP BY c.id ORDER BY c.name"
    ).fetchall()

    lines = [
        "# Civilisations",
        "",
        "| Civilisation | Joueur | Tours | Entites |",
        "|---|---|---|---|",
    ]
    for c in civs:
        entity_count = conn.execute(
            "SELECT count(*) FROM entity_entities WHERE civ_id = ?", (c["id"],)
        ).fetchone()[0]
        slug = slugify(c["name"])
        lines.append(f"| [{c['name']}]({slug}/index.md) | {c['player_name'] or '-'} | {c['turn_count']} | {entity_count} |")

    lines.append("")
    return "\n".join(lines)


def generate_civ_index(conn: sqlite3.Connection, civ_id: int, civ_name: str, player_name: str | None) -> str:
    """Generate a civilization's overview page."""
    turn_count = conn.execute(
        "SELECT count(*) FROM turn_turns WHERE civ_id = ?", (civ_id,)
    ).fetchone()[0]

    entity_rows = conn.execute(
        "SELECT entity_type, count(*) as c FROM entity_entities WHERE civ_id = ? GROUP BY entity_type ORDER BY c DESC",
        (civ_id,),
    ).fetchall()

    recent_turns = conn.execute(
        "SELECT turn_number, summary FROM turn_turns WHERE civ_id = ? ORDER BY turn_number DESC LIMIT 5",
        (civ_id,),
    ).fetchall()

    lines = [
        f"# {civ_name}",
        "",
    ]
    if player_name:
        lines.append(f"**Joueur** : {player_name}")
        lines.append("")

    lines.extend([
        f"**Tours de jeu** : {turn_count}",
        "",
        "## Entites par type",
        "",
        "| Type | Nombre |",
        "|---|---|",
    ])
    for r in entity_rows:
        lines.append(f"| {_entity_type_label(r['entity_type'])} | {r['c']} |")

    lines.extend(["", "## Derniers tours", ""])
    for t in reversed(list(recent_turns)):
        summary_preview = _clean_summary(t["summary"] or "")[:120]
        lines.append(f"- **Tour {t['turn_number']}** -- {summary_preview}...")

    lines.extend([
        "",
        "## Pages",
        "",
        "- [Historique complet des tours](turns/index.md)",
        "- [Index des entites](entities/index.md)",
        "",
        "### Base de connaissances",
        "",
        "- [Technologies](knowledge/technologies.md)",
        "- [Ressources](knowledge/resources.md)",
        "- [Croyances](knowledge/beliefs.md)",
        "- [Geographie](knowledge/geography.md)",
        "- [Choix et Decisions](knowledge/choices.md)",
        "- [Relations entre Entites](knowledge/relations.md)",
        "",
    ])
    return "\n".join(lines)


def generate_civ_turns(conn: sqlite3.Connection, civ_id: int, civ_name: str) -> str:
    """Generate turn-by-turn history for a civilization.

    Renders each turn with:
    1. Summary block (detailed + key events + choices)
    2. Raw messages grouped by author (GM vs player), cleaned
    """
    turns = conn.execute(
        "SELECT * FROM turn_turns WHERE civ_id = ? ORDER BY turn_number",
        (civ_id,),
    ).fetchall()

    # Detect GM author(s) by frequency -- GM posts more than players
    gm_authors = _detect_gm_authors(conn)

    lines = [f"# {civ_name} -- Historique des tours", ""]

    for turn in turns:
        turn_id = turn["id"]

        # Use detailed_summary if available, fall back to short summary
        detailed = _clean_summary(turn["detailed_summary"] or "") if turn["detailed_summary"] else ""
        short = _clean_summary(turn["summary"] or "")
        display_summary = detailed or short or "Pas de resume disponible."

        key_events = _parse_json_list(turn["key_events"])
        choices_made = _parse_json_list(turn["choices_made"])

        # Parse structured facts (handle missing columns gracefully)
        try:
            media_links = _parse_json_data(turn["media_links"]) if turn["media_links"] else []
        except (KeyError, IndexError):
            media_links = []
        try:
            technologies = _parse_json_list(turn["technologies"]) if turn["technologies"] else []
        except (KeyError, IndexError):
            technologies = []
        try:
            resources = _parse_json_list(turn["resources"]) if turn["resources"] else []
        except (KeyError, IndexError):
            resources = []
        try:
            beliefs = _parse_json_list(turn["beliefs"]) if turn["beliefs"] else []
        except (KeyError, IndexError):
            beliefs = []
        try:
            geography = _parse_json_list(turn["geography"]) if turn["geography"] else []
        except (KeyError, IndexError):
            geography = []
        try:
            choices_proposed = _parse_json_list(turn["choices_proposed"]) if turn["choices_proposed"] else []
        except (KeyError, IndexError):
            choices_proposed = []

        entities = conn.execute(
            """SELECT DISTINCT e.canonical_name, e.entity_type
               FROM entity_mentions m JOIN entity_entities e ON m.entity_id = e.id
               WHERE m.turn_id = ? ORDER BY e.entity_type, e.canonical_name""",
            (turn_id,),
        ).fetchall()

        entity_tags = ", ".join(
            f"`{_capitalize_entity(e['canonical_name'])}`"
            for e in entities
            if not is_noise_entity(e["canonical_name"])
        )

        lines.extend([
            f"## Tour {turn['turn_number']}",
            "",
            f"> {display_summary[:400]}",
            "",
        ])

        # Media links (YouTube embeds)
        if media_links:
            for link in media_links:
                if isinstance(link, dict) and link.get("type") == "youtube":
                    video_id = link.get("video_id", "")
                    lines.append(f"🎵 **Ambiance** : [YouTube](https://www.youtube.com/watch?v={video_id})")
                    lines.append("")

        if key_events:
            lines.append("**Evenements cles** :")
            lines.append("")
            for evt in key_events:
                lines.append(f"- {evt}")
            lines.append("")

        # Structured facts sections
        if geography:
            lines.append("🗺️ **Geographie decouverte** :")
            lines.append("")
            for geo in geography[:10]:  # Limit to 10 items
                lines.append(f"- {geo}")
            lines.append("")

        if technologies:
            lines.append("🔧 **Technologies/Savoirs** :")
            lines.append("")
            for tech in technologies[:10]:
                lines.append(f"- {tech}")
            lines.append("")

        if resources:
            lines.append("🌾 **Ressources** :")
            lines.append("")
            for res in resources[:10]:
                lines.append(f"- {res}")
            lines.append("")

        if beliefs:
            lines.append("✨ **Croyances/Systemes sociaux** :")
            lines.append("")
            for belief in beliefs[:10]:
                lines.append(f"- {belief}")
            lines.append("")

        # Choices section (proposed vs made)
        if choices_proposed or choices_made:
            lines.append("⚖️ **Choix** :")
            lines.append("")
            if choices_proposed:
                lines.append("*Options proposees* :")
                for choice in choices_proposed:
                    lines.append(f"- {choice}")
                lines.append("")
            if choices_made:
                lines.append("*Decision* :")
                for choice in choices_made:
                    lines.append(f"- ✓ {choice}")
                lines.append("")

        lines.extend([
            f"**Entites** : {entity_tags if entity_tags else 'aucune'}",
            "",
        ])

        # Render raw messages grouped by author (GM / Player)
        raw_ids = _parse_json_list(turn["raw_message_ids"])
        if raw_ids:
            message_groups = _group_messages_by_author(conn, raw_ids, gm_authors)
            for group in message_groups:
                role_label = "Maitre du Jeu" if group["is_gm"] else group["author"]
                lines.append(f"### {role_label}")
                lines.append("")
                content = _clean_segment_content(group["content"])
                if content:
                    # Downgrade ### headers in content to #### to avoid collision with author headers
                    content = re.sub(r"^### ", "#### ", content, flags=re.MULTILINE)
                    lines.append(content)
                    lines.append("")

        lines.extend(["---", ""])

    return "\n".join(lines)


def _build_fused_entities(conn: sqlite3.Connection, civ_id: int) -> list[dict]:
    """Detect and merge duplicate entities within a civilization.

    Builds a graph of "same entity" relationships by checking:
    - Entity A has an alias matching Entity B's canonical_name (or vice versa)
    - Entity A's canonical_name appears as a substring of Entity B's (case-insensitive)

    Returns a list of fused entity dicts with merged stats.
    """
    entities = conn.execute(
        """SELECT e.id, e.canonical_name, e.entity_type, e.description, e.history,
                  e.first_seen_turn, e.last_seen_turn,
                  (SELECT count(*) FROM entity_mentions m WHERE m.entity_id = e.id) as mention_count
           FROM entity_entities e
           WHERE e.civ_id = ?
           ORDER BY e.canonical_name""",
        (civ_id,),
    ).fetchall()

    # Build alias lookup: entity_id -> set of alias strings (lowered)
    alias_lookup: dict[int, set[str]] = {}
    for e in entities:
        eid = e["id"]
        aliases = conn.execute(
            "SELECT alias FROM entity_aliases WHERE entity_id = ?", (eid,)
        ).fetchall()
        alias_lookup[eid] = {a["alias"].lower().strip() for a in aliases}

    # Build name lookup: lowered canonical_name -> entity row
    name_to_entity: dict[str, list] = {}
    for e in entities:
        key = e["canonical_name"].lower().strip()
        name_to_entity.setdefault(key, []).append(e)

    # Union-Find for grouping
    parent: dict[int, int] = {e["id"]: e["id"] for e in entities}

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a: int, b: int) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb

    # Merge entities where alias matches another entity's canonical name
    for e in entities:
        eid = e["id"]
        e_name_lower = e["canonical_name"].lower().strip()
        # Check if any other entity's canonical_name matches one of our aliases
        for alias in alias_lookup.get(eid, set()):
            if alias in name_to_entity:
                for other in name_to_entity[alias]:
                    if other["id"] != eid and other["entity_type"] == e["entity_type"]:
                        union(eid, other["id"])
        # Check if our canonical name matches another entity's alias
        for other in entities:
            if other["id"] == eid or other["entity_type"] != e["entity_type"]:
                continue
            if e_name_lower in alias_lookup.get(other["id"], set()):
                union(eid, other["id"])

    # Known fusion pairs (domain knowledge for this game)
    _KNOWN_FUSIONS = {
        "pupupasu": "cheveux de sang",
        "gingembre sauvage": "morsure-des-ancetres",
        "morsure-des-ancetres": "gingembre sauvage",
    }
    for e in entities:
        e_lower = e["canonical_name"].lower().strip()
        # Normalize accented chars for matching
        e_normalized = slugify(e["canonical_name"])
        for src, tgt in _KNOWN_FUSIONS.items():
            src_slug = slugify(src)
            tgt_slug = slugify(tgt)
            if e_normalized == src_slug:
                for other in entities:
                    if slugify(other["canonical_name"]) == tgt_slug:
                        union(e["id"], other["id"])

    # Group entities by root
    groups: dict[int, list] = {}
    for e in entities:
        root = find(e["id"])
        groups.setdefault(root, []).append(e)

    # Build fused entity list
    fused: list[dict] = []
    for group in groups.values():
        # Filter noise from the group
        clean = [e for e in group if not is_noise_entity(e["canonical_name"])]
        if not clean:
            continue

        # Pick the primary: highest mention count, then longest name
        primary = max(clean, key=lambda e: (e["mention_count"], len(e["canonical_name"])))

        # Merge stats
        total_mentions = sum(e["mention_count"] for e in clean)
        first_turn_ids = [e["first_seen_turn"] for e in clean if e["first_seen_turn"]]
        last_turn_ids = [e["last_seen_turn"] for e in clean if e["last_seen_turn"]]
        all_histories: list[str] = []
        for e in clean:
            all_histories.extend(_parse_json_list(e["history"]))
        # Deduplicate history entries
        seen_history: set[str] = set()
        unique_history: list[str] = []
        for h in all_histories:
            if h not in seen_history:
                seen_history.add(h)
                unique_history.append(h)

        # Pick longest description
        descriptions = [e["description"] for e in clean if e["description"]]
        best_desc = max(descriptions, key=len) if descriptions else None

        # Collect all names as aliases (excluding the primary name)
        all_names = set()
        for e in clean:
            all_names.add(e["canonical_name"])
            for alias in alias_lookup.get(e["id"], set()):
                all_names.add(alias)
        # Also add display-cased versions
        alias_set = {n for n in all_names if n.lower().strip() != primary["canonical_name"].lower().strip()}

        # Collect all entity IDs in the group (for mention queries)
        all_ids = [e["id"] for e in clean]

        fused.append({
            "id": primary["id"],
            "all_ids": all_ids,
            "canonical_name": primary["canonical_name"],
            "entity_type": primary["entity_type"],
            "description": best_desc,
            "history": unique_history,
            "mention_count": total_mentions,
            "first_seen_turn": min(first_turn_ids) if first_turn_ids else None,
            "last_seen_turn": max(last_turn_ids) if last_turn_ids else None,
            "aliases": sorted(alias_set),
        })

    return fused


def _build_id_to_primary(fused_list: list[dict]) -> dict[int, str]:
    """Build a reverse map: entity_id -> primary canonical_name for all fused groups."""
    mapping: dict[int, str] = {}
    for fe in fused_list:
        for eid in fe["all_ids"]:
            mapping[eid] = fe["canonical_name"]
    return mapping


def generate_entity_page(
    conn: sqlite3.Connection,
    entity: dict,
    civ_name: str,
    civ_slug: str,
    id_to_primary: dict[int, str] | None = None,
    tech_names: set[str] | None = None,
) -> str:
    """Generate a full markdown page for a single entity."""
    name = _capitalize_entity(entity["canonical_name"])
    etype_label = _entity_type_label(entity["entity_type"])
    first = _turn_link(entity["first_seen_turn"], conn) if entity["first_seen_turn"] else "-"
    last = _turn_link(entity["last_seen_turn"], conn) if entity["last_seen_turn"] else "-"

    lines = [
        f"# {name}",
        "",
        f"*{etype_label}* -- {civ_name}",
        "",
    ]

    # Cross-link to tech page if this entity is also a technology
    if tech_names:
        matched_tech = _find_best_tech_match(entity, tech_names)
        if matched_tech:
            tech_slug = slugify(matched_tech)
            lines.extend([
                f"!!! info \"Technologie active\"",
                f"    Cette entite est aussi une technologie developpee. Voir la [fiche technologique](../knowledge/tech/{tech_slug}.md).",
                "",
            ])

    # --- PHASE 4 ADDITION: Section "Vue d'ensemble" avec stats détaillées ---
    # Get entity timeline for stats calculation
    entity_timeline = get_entity_timeline(conn, entity["id"])

    if entity_timeline:
        first_turn_num = min(entity_timeline.keys())
        last_turn_num = max(entity_timeline.keys())
        duration = last_turn_num - first_turn_num + 1
        peak_turn = max(entity_timeline.items(), key=lambda x: x[1])[0]
        peak_mentions = entity_timeline[peak_turn]
        avg_mentions = entity["mention_count"] / len(entity_timeline)

        lines.extend([
            "## 📊 Vue d'ensemble",
            "",
            "| | |",
            "|---|---|",
            f"| **Mentions totales** | {entity['mention_count']} |",
            f"| **Tours actifs** | {first_turn_num}-{last_turn_num} ({duration} tours) |",
            f"| **Pic d'activite** | Tour {peak_turn} ({peak_mentions} mentions) |",
            f"| **Moyenne** | {avg_mentions:.1f} mentions/tour |",
            "",
        ])
    else:
        # Fallback to basic table
        lines.extend([
            "| | |",
            "|---|---|",
            f"| Mentions | **{entity['mention_count']}** |",
            f"| Premiere apparition | {first} |",
            f"| Derniere apparition | {last} |",
        ])
        if entity["aliases"]:
            alias_display = ", ".join(_capitalize_entity(a) for a in entity["aliases"])
            lines.append(f"| Alias | {alias_display} |")
        lines.append("")

    # --- PHASE 4 ADDITION: Section "Graphe d'activité" ---
    if entity_timeline:
        lines.extend([
            "## 📈 Graphe d'activite",
            "",
            "```",
        ])
        max_mentions_chart = max(entity_timeline.values())
        for turn_num in sorted(entity_timeline.keys()):
            mentions = entity_timeline[turn_num]
            # Scale bars to max 20 chars
            bar_length = int((mentions / max_mentions_chart) * 20) if max_mentions_chart > 0 else 0
            bar = "█" * bar_length if bar_length > 0 else ""
            peak_marker = "  ← Pic" if turn_num == peak_turn else ""
            lines.append(f"Tour {turn_num:2d}  {bar:<20s}{peak_marker}")
        lines.extend(["```", ""])

    # --- PHASE 4 ADDITION: Section "Réseau relationnel" avec co-occurrences ---
    # Get co-occurrences for this entity's turns
    all_ids = entity["all_ids"]
    placeholders = ",".join("?" * len(all_ids))
    turn_ids = conn.execute(
        f"""SELECT DISTINCT m.turn_id
            FROM entity_mentions m
            WHERE m.entity_id IN ({placeholders})""",
        all_ids,
    ).fetchall()

    if turn_ids:
        turn_id_list = [t["turn_id"] for t in turn_ids]
        turn_placeholders = ",".join("?" * len(turn_id_list))

        # Get co-occurring entities
        cooccurring = conn.execute(
            f"""SELECT e.id, e.canonical_name, e.entity_type,
                       COUNT(DISTINCT m.turn_id) as turns_together
                FROM entity_mentions m
                JOIN entity_entities e ON m.entity_id = e.id
                WHERE m.turn_id IN ({turn_placeholders})
                  AND m.entity_id NOT IN ({placeholders})
                GROUP BY e.id
                HAVING turns_together >= 2
                ORDER BY turns_together DESC
                LIMIT 10""",
            turn_id_list + all_ids,
        ).fetchall()

        # Filter noise and resolve to primary names
        clean_cooccurrences = []
        seen_primary = set()
        for co in cooccurring:
            if is_noise_entity(co["canonical_name"]):
                continue
            primary_name = (id_to_primary or {}).get(co["id"], co["canonical_name"])
            if is_noise_entity(primary_name) or primary_name in seen_primary:
                continue
            seen_primary.add(primary_name)
            clean_cooccurrences.append({
                "name": primary_name,
                "type": co["entity_type"],
                "turns_together": co["turns_together"],
            })

        if clean_cooccurrences:
            lines.extend([
                "## 🔗 Reseau relationnel",
                "",
                "**Entites souvent mentionnees ensemble :**",
                "",
            ])
            for co in clean_cooccurrences[:5]:
                co_name = _capitalize_entity(co["name"])
                co_slug = slugify(co["name"])
                co_type_label = _entity_type_label(co["type"])
                lines.append(
                    f"- 🔵 **[{co_name}]({co_slug}.md)** ({co_type_label}) — "
                    f"{co['turns_together']} tours"
                )
            lines.append("")

    # Description
    if entity["description"]:
        lines.extend(["## Description", "", entity["description"], ""])

    # Per-turn summaries (from LLM profiler) as main chronology
    if entity["history"]:
        lines.extend(["## Chronologie", ""])
        for event in entity["history"]:
            # History entries are now "Tour X: summary..." format
            lines.append(f"**{event}**" if event.startswith("Tour") else f"- {event}")
            lines.append("")

    # --- PHASE 4 ADDITION: Section "Mentions avec contexte" ---
    context_samples = get_entity_context_samples(conn, entity["id"], limit=5)
    if context_samples:
        lines.extend([
            "## 💬 Mentions avec contexte",
            "",
        ])
        for turn_num, mention_text, context in context_samples:
            # Clean context for display
            clean_ctx = _clean_segment_content(context) if context else mention_text
            lines.extend([
                f"**Tour {turn_num}**",
                f"> \"{mention_text}\"",
                ">",
                f"> Contexte : {clean_ctx[:200]}...",
                "",
            ])

    # Raw source passages (collapsible, for reference)
    # Note: all_ids and placeholders already defined above for co-occurrences
    mentions = conn.execute(
        f"""SELECT m.mention_text, m.context, t.turn_number
            FROM entity_mentions m
            JOIN turn_turns t ON m.turn_id = t.id
            WHERE m.entity_id IN ({placeholders})
            ORDER BY t.turn_number, m.id""",
        all_ids,
    ).fetchall()

    if mentions:
        lines.extend([
            "??? note \"Sources -- Passages originaux\"",
            "",
        ])
        _segment_cache: dict[int, list[str]] = {}
        current_turn = None
        seen_contexts: set[str] = set()
        for m in mentions:
            if m["turn_number"] != current_turn:
                current_turn = m["turn_number"]
                lines.append(f"    **Tour {current_turn}**")
                lines.append("")
            ctx = _find_rich_context(
                conn, m["mention_text"], m["turn_number"],
                m["context"], _segment_cache,
            )
            if ctx:
                ctx_key = ctx[:100]
                if ctx_key in seen_contexts:
                    continue
                seen_contexts.add(ctx_key)
                # Indent for admonition content
                for ctx_line in f"> {ctx}".splitlines():
                    lines.append(f"    {ctx_line}")
                lines.append("")

    # Related entities (co-occurring in same turns) - now in "Réseau relationnel" section above
    # This section is moved and enhanced earlier, so we remove the duplicate
    return "\n".join(lines)


def generate_civ_entities(conn: sqlite3.Connection, civ_id: int, civ_name: str) -> tuple[str, list[dict]]:
    """Generate clickable entity index for a civilization.

    Returns (index_page_content, list_of_fused_entity_dicts) so the caller
    can write individual entity pages.
    """
    civ_slug = slugify(civ_name)
    fused = _build_fused_entities(conn, civ_id)

    # Group by type
    by_type: dict[str, list[dict]] = {}
    for e in fused:
        by_type.setdefault(e["entity_type"], []).append(e)

    lines = [f"# {civ_name} -- Entites", ""]

    type_order = ["person", "place", "technology", "institution", "civilization",
                  "caste", "resource", "creature", "event"]
    sorted_types = sorted(by_type.keys(), key=lambda t: type_order.index(t) if t in type_order else 99)

    for etype in sorted_types:
        entities = sorted(by_type[etype], key=lambda e: e["canonical_name"].lower())
        if not entities:
            continue

        lines.extend([f"## {_entity_type_label(etype)}", ""])

        for e in entities:
            name = _capitalize_entity(e["canonical_name"])
            eslug = slugify(e["canonical_name"])
            first = _turn_link(e["first_seen_turn"], conn) if e["first_seen_turn"] else ""
            last = _turn_link(e["last_seen_turn"], conn) if e["last_seen_turn"] else ""

            # Build entry line
            turn_info = ""
            if first and last and first != last:
                turn_info = f", {first} - {last}"
            elif first:
                turn_info = f", {first}"

            alias_info = ""
            if e["aliases"]:
                alias_display = ", ".join(_capitalize_entity(a) for a in e["aliases"][:3])
                alias_info = f" | *alias: {alias_display}*"

            lines.append(
                f"- [**{name}**]({eslug}.md) "
                f"-- {e['mention_count']} mentions{turn_info}{alias_info}"
            )

        lines.append("")

    return "\n".join(lines), fused


def generate_global_timeline(conn: sqlite3.Connection) -> str:
    """Generate global timeline across all civilizations."""
    turns = conn.execute(
        """SELECT t.turn_number, t.summary, t.turn_type, c.name as civ_name
           FROM turn_turns t JOIN civ_civilizations c ON t.civ_id = c.id
           ORDER BY t.turn_number""",
    ).fetchall()

    lines = [
        "# Timeline Globale",
        "",
        "| Tour | Civilisation | Type | Resume |",
        "|---|---|---|---|",
    ]
    for t in turns:
        summary = _clean_summary(t["summary"] or "")[:150]
        civ_slug = slugify(t["civ_name"])
        lines.append(
            f"| {t['turn_number']} | "
            f"[{t['civ_name']}](../civilizations/{civ_slug}/index.md) | "
            f"{t['turn_type']} | "
            f"{summary} |"
        )
    lines.append("")
    return "\n".join(lines)


def generate_global_entities(conn: sqlite3.Connection, all_fused: dict[int, list[dict]] | None = None) -> str:
    """Generate global entity index across all civilizations.

    Links each entity to its dedicated page. Uses fused entities if provided.
    """
    # Build a flat list of all fused entities across civs
    global_entities: list[dict] = []
    if all_fused:
        for civ_id, fused_list in all_fused.items():
            civ_row = conn.execute(
                "SELECT name FROM civ_civilizations WHERE id = ?", (civ_id,)
            ).fetchone()
            civ_name = civ_row["name"] if civ_row else "Global"
            civ_slug = slugify(civ_name)
            for e in fused_list:
                global_entities.append({**e, "civ_name": civ_name, "civ_slug": civ_slug})
    else:
        # Fallback: query directly (no fusion)
        rows = conn.execute(
            """SELECT e.id, e.canonical_name, e.entity_type, e.description,
                      c.name as civ_name,
                      (SELECT count(*) FROM entity_mentions m WHERE m.entity_id = e.id) as mention_count
               FROM entity_entities e
               LEFT JOIN civ_civilizations c ON e.civ_id = c.id
               ORDER BY e.canonical_name"""
        ).fetchall()
        for e in rows:
            if is_noise_entity(e["canonical_name"]):
                continue
            global_entities.append({
                "canonical_name": e["canonical_name"],
                "entity_type": e["entity_type"],
                "mention_count": e["mention_count"],
                "description": e["description"],
                "civ_name": e["civ_name"] or "Global",
                "civ_slug": slugify(e["civ_name"]) if e["civ_name"] else "",
                "aliases": [],
            })

    # Group by type
    by_type: dict[str, list[dict]] = {}
    for e in global_entities:
        by_type.setdefault(e["entity_type"], []).append(e)

    lines = ["# Index des Entites", ""]

    type_order = ["person", "place", "technology", "institution", "civilization",
                  "caste", "resource", "creature", "event"]
    sorted_types = sorted(by_type.keys(), key=lambda t: type_order.index(t) if t in type_order else 99)

    for etype in sorted_types:
        entities = sorted(by_type[etype], key=lambda e: e["canonical_name"].lower())
        if not entities:
            continue

        lines.extend([f"## {_entity_type_label(etype)}", ""])

        for e in entities:
            name = _capitalize_entity(e["canonical_name"])
            civ = e["civ_name"]
            civ_slug = e["civ_slug"]
            eslug = slugify(e["canonical_name"])

            # Build turn range
            first = _turn_link(e.get("first_seen_turn"), conn) if e.get("first_seen_turn") else ""
            last = _turn_link(e.get("last_seen_turn"), conn) if e.get("last_seen_turn") else ""
            turn_info = ""
            if first and last and first != last:
                turn_info = f", {first} - {last}"
            elif first:
                turn_info = f", {first}"

            alias_str = ""
            if e.get("aliases"):
                alias_names = ", ".join(_capitalize_entity(a) for a in e["aliases"][:3])
                alias_str = f" | *alias: {alias_names}*"

            if civ_slug:
                link = f"../civilizations/{civ_slug}/entities/{eslug}.md"
                lines.append(
                    f"- [**{name}**]({link}) -- {civ}, {e['mention_count']} mentions{turn_info}{alias_str}"
                )
            else:
                lines.append(
                    f"- **{name}** -- {civ}, {e['mention_count']} mentions{turn_info}{alias_str}"
                )

            lines.append("")

    return "\n".join(lines)


def generate_pipeline_stats(conn: sqlite3.Connection) -> str:
    """Generate pipeline run statistics page."""
    runs = conn.execute(
        "SELECT * FROM pipeline_runs ORDER BY id DESC"
    ).fetchall()

    msg_count = conn.execute("SELECT count(*) FROM turn_raw_messages").fetchone()[0]
    turn_count = conn.execute("SELECT count(*) FROM turn_turns").fetchone()[0]
    entity_count = conn.execute("SELECT count(*) FROM entity_entities").fetchone()[0]
    mention_count = conn.execute("SELECT count(*) FROM entity_mentions").fetchone()[0]
    seg_count = conn.execute("SELECT count(*) FROM turn_segments").fetchone()[0]

    lines = [
        "# Pipeline ML",
        "",
        "## Etat de la base de donnees",
        "",
        "| Metrique | Valeur |",
        "|---|---|",
        f"| Messages bruts | {msg_count} |",
        f"| Tours de jeu | {turn_count} |",
        f"| Segments | {seg_count} |",
        f"| Entites uniques | {entity_count} |",
        f"| Mentions d'entites | {mention_count} |",
        "",
        "## Historique des runs",
        "",
        "| Run | Statut | Debut | Fin | Messages | Tours | Entites |",
        "|---|---|---|---|---|---|---|",
    ]
    for r in runs:
        status_icon = {"completed": "OK", "failed": "FAIL", "running": "..."}.get(r["status"], r["status"])
        lines.append(
            f"| {r['id']} | {status_icon} | "
            f"{r['started_at'] or '-'} | "
            f"{r['completed_at'] or '-'} | "
            f"{r['messages_processed'] or 0} | "
            f"{r['turns_created'] or 0} | "
            f"{r['entities_extracted'] or 0} |"
        )
    lines.append("")
    return "\n".join(lines)


# -- Helpers -------------------------------------------------------------------

def _entity_type_label(etype: str) -> str:
    """French label for entity types."""
    labels = {
        "person": "Personnages",
        "place": "Lieux",
        "technology": "Technologies",
        "institution": "Institutions",
        "civilization": "Civilisations",
        "caste": "Castes",
        "resource": "Ressources",
        "creature": "Creatures",
        "event": "Evenements",
    }
    return labels.get(etype, etype.capitalize())


def _clean_summary(summary: str) -> str:
    """Clean up a summary for display -- remove YouTube artifacts and markdown noise."""
    lines = summary.strip().splitlines()
    cleaned = []
    skip_youtube = False
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("https://") or stripped.startswith("http://"):
            skip_youtube = True
            continue
        if skip_youtube and (not stripped or stripped in ("YouTube",)):
            continue
        if skip_youtube:
            skip_youtube = False
            if len(stripped) < 60 and not stripped.endswith("."):
                continue
        cleaned.append(line)
    result = " ".join(l.strip() for l in cleaned if l.strip())
    result = re.sub(r"^\*\*[^*]+\*\*\s*", "", result)
    return result.strip()


# Patterns for segment content cleaning
_RE_YOUTUBE_URL = re.compile(r"https?://(?:www\.)?(?:youtube\.com|youtu\.be)/\S+")
_RE_YOUTUBE_META = re.compile(
    r"^\d+\s+.*(?:OST|Soundtrack|Remix|Topic|YouTube).*$",
    re.IGNORECASE | re.MULTILINE,
)
_RE_MODIFIE = re.compile(r"\s*\(modifi[eé]\)")
_RE_TIMESTAMP_LINE = re.compile(r"^\s*\[\s*\d{2}:\d{2}\s*\]\s*$", re.MULTILINE)
_RE_TIMESTAMP_INLINE = re.compile(r"\[\s*\d{2}:\d{2}\s*\]\s*")


def _clean_segment_content(content: str) -> str:
    """Clean segment content for wiki display.

    Removes YouTube URLs/metadata, (modifie) markers, timestamps, and duplicate paragraphs.
    """
    text = _RE_YOUTUBE_URL.sub("", content)
    text = _RE_YOUTUBE_META.sub("", text)
    text = _RE_MODIFIE.sub("", text)
    text = _RE_TIMESTAMP_LINE.sub("", text)
    text = _RE_TIMESTAMP_INLINE.sub("", text)

    # Deduplicate paragraphs
    paragraphs = text.split("\n\n")
    seen: set[str] = set()
    unique = []
    for para in paragraphs:
        normalized = para.strip()
        if not normalized:
            continue
        key = re.sub(r"\s+", " ", normalized).strip()
        if key in seen:
            continue
        seen.add(key)
        unique.append(normalized)
    text = "\n\n".join(unique)

    # Clean residual noise lines
    lines = text.splitlines()
    cleaned = []
    for line in lines:
        stripped = line.strip()
        if stripped in (",", "", "YouTube", "youtube"):
            continue
        if len(stripped) < 3 and not stripped.endswith("."):
            continue
        cleaned.append(line)

    return "\n".join(cleaned).strip()


def _parse_json_list(json_str: str | None) -> list[str]:
    """Safely parse a JSON string expected to be a list of strings."""
    if not json_str:
        return []
    try:
        data = json.loads(json_str)
        if isinstance(data, list):
            return [str(item) for item in data if item]
        return []
    except (json.JSONDecodeError, TypeError):
        return []


def _parse_json_data(json_str: str | None):
    """Safely parse a JSON string, preserving types (dicts, strings, etc)."""
    if not json_str:
        return []
    try:
        data = json.loads(json_str)
        if isinstance(data, list):
            return data
        return []
    except (json.JSONDecodeError, TypeError):
        return []


def _capitalize_entity(name: str) -> str:
    """Capitalize first letter of entity name for display."""
    if not name:
        return name
    return name[0].upper() + name[1:]


def _clean_author_name(name: str) -> str:
    """Normalize author names -- strip trailing ) from parsing artifacts."""
    return name.rstrip(")")


def _detect_gm_authors(conn: sqlite3.Connection) -> set[str]:
    """Detect GM authors by message frequency -- GM posts the most."""
    rows = conn.execute(
        "SELECT author_name, count(*) as c FROM turn_raw_messages GROUP BY author_name ORDER BY c DESC"
    ).fetchall()
    if not rows:
        return set()
    # The most frequent author is the GM; also include variants with trailing )
    gm_name = _clean_author_name(rows[0]["author_name"])
    return {r["author_name"] for r in rows if _clean_author_name(r["author_name"]) == gm_name}


def _group_messages_by_author(
    conn: sqlite3.Connection,
    raw_ids: list[str],
    gm_authors: set[str],
) -> list[dict]:
    """Group consecutive raw messages by author role (GM vs player).

    Returns list of dicts: {author, is_gm, content}
    """
    groups: list[dict] = []
    for msg_id in raw_ids:
        row = conn.execute(
            "SELECT author_name, content FROM turn_raw_messages WHERE id = ?",
            (int(msg_id),),
        ).fetchone()
        if not row:
            continue

        author = _clean_author_name(row["author_name"])
        is_gm = row["author_name"] in gm_authors

        # Merge with previous group if same role
        if groups and groups[-1]["is_gm"] == is_gm:
            groups[-1]["content"] += "\n\n" + row["content"]
        else:
            groups.append({
                "author": author,
                "is_gm": is_gm,
                "content": row["content"],
            })

    return groups


def _find_rich_context(
    conn: sqlite3.Connection,
    mention_text: str,
    turn_number: int,
    fallback_context: str | None,
    cache: dict[int, list[str]],
    window: int = 800,
) -> str:
    """Find a rich context excerpt for a mention by searching turn segments.

    Looks for mention_text in the turn's segments and returns a window of text
    around it. Falls back to the stored context field if no segment match.
    """
    if turn_number not in cache:
        segments = conn.execute(
            """SELECT s.content FROM turn_segments s
               JOIN turn_turns t ON s.turn_id = t.id
               WHERE t.turn_number = ?
               ORDER BY s.segment_order""",
            (turn_number,),
        ).fetchall()
        cache[turn_number] = [s["content"] for s in segments]

    # Search for mention in segments (case-insensitive)
    mention_lower = mention_text.lower()
    for seg_content in cache[turn_number]:
        pos = seg_content.lower().find(mention_lower)
        if pos != -1:
            # Extract window around the mention
            half = window // 2
            start = max(0, pos - half)
            end = min(len(seg_content), pos + len(mention_text) + half)
            excerpt = seg_content[start:end].strip()
            excerpt = _clean_segment_content(excerpt)
            if not excerpt:
                continue
            prefix = "..." if start > 0 else ""
            suffix = "..." if end < len(seg_content) else ""
            return f"{prefix}{excerpt}{suffix}"

    # Fallback to stored context
    if fallback_context:
        ctx = _clean_segment_content(fallback_context.strip())
        if ctx:
            return f"...{ctx}..."
    return ""


def _turn_link(turn_id: int | None, conn: sqlite3.Connection) -> str:
    """Create a turn reference string."""
    if not turn_id:
        return "-"
    row = conn.execute(
        "SELECT turn_number FROM turn_turns WHERE id = ?", (turn_id,)
    ).fetchone()
    return f"Tour {row['turn_number']}" if row else "-"


# -- Main generation -----------------------------------------------------------

def generate_wiki(
    db_path: str,
    output_dir: str,
    progress_callback=None,
    run_id: int | None = None,
) -> dict:
    """Generate all wiki pages from the database. Returns stats.

    Args:
        db_path: Path to SQLite database
        output_dir: Output directory for markdown files
        progress_callback: Optional callback(current, total, unit_type) for progress tracking
        run_id: Optional pipeline run ID for DB progress tracking
    """
    out = Path(output_dir)
    conn = get_connection(db_path)
    stats = {"pages_generated": 0, "entity_pages": 0}

    # Estimate total pages for progress tracking
    civ_count = conn.execute("SELECT count(*) FROM civ_civilizations").fetchone()[0]
    # Rough estimate: 5 base pages + 3 per civ + entity pages
    # We'll refine as we go
    estimated_base_pages = 5 + (3 * civ_count)
    total_pages = estimated_base_pages  # Will be updated with actual entity count
    current_page = 0

    try:
        # Phase 3: Use enriched index
        _write_page(out / "index.md", generate_enriched_index(conn))
        stats["pages_generated"] += 1
        current_page += 1
        if progress_callback:
            progress_callback(current_page, total_pages, "page")

        _write_page(out / "civilizations" / "index.md", generate_civilizations_index(conn))
        stats["pages_generated"] += 1
        current_page += 1
        if progress_callback:
            progress_callback(current_page, total_pages, "page")

        # Collect fused entities per civ for global index
        all_fused: dict[int, list[dict]] = {}

        civs = conn.execute("SELECT * FROM civ_civilizations ORDER BY name").fetchall()

        # Update total_pages estimate with actual entity count
        entity_count = conn.execute("SELECT count(*) FROM entity_entities WHERE is_active = 1").fetchone()[0]
        total_pages = estimated_base_pages + entity_count

        for civ in civs:
            civ_slug = slugify(civ["name"])
            civ_dir = out / "civilizations" / civ_slug

            _write_page(civ_dir / "index.md",
                        generate_civ_index(conn, civ["id"], civ["name"], civ["player_name"]))
            stats["pages_generated"] += 1
            current_page += 1
            if progress_callback:
                progress_callback(current_page, total_pages, "page")

            # Phase 2: Generate individual turn pages
            _write_page(civ_dir / "turns" / "index.md",
                        generate_turn_index(conn, civ["id"], civ["name"]))
            stats["pages_generated"] += 1

            # Generate individual turn pages
            turns = conn.execute(
                "SELECT * FROM turn_turns WHERE civ_id = ? ORDER BY turn_number",
                (civ["id"],)
            ).fetchall()
            for turn in turns:
                turn_page = generate_turn_page(conn, turn["id"], civ["name"], civ["player_name"])
                turn_slug = f"turn-{turn['turn_number']:02d}.md"
                _write_page(civ_dir / "turns" / turn_slug, turn_page)
                stats["pages_generated"] += 1

            # generate_civ_entities now returns (page_content, fused_list)
            entities_content, fused_list = generate_civ_entities(conn, civ["id"], civ["name"])
            _write_page(civ_dir / "entities" / "index.md", entities_content)
            all_fused[civ["id"]] = fused_list
            stats["pages_generated"] += 1
            current_page += 1
            if progress_callback:
                progress_callback(current_page, total_pages, "page")

            # Write individual entity pages
            entity_dir = civ_dir / "entities"
            id_to_primary = _build_id_to_primary(fused_list)

            # Build tech names set for cross-linking
            tech_tree = get_tech_tree(conn, civ["id"])
            tech_names: set[str] = set()
            for _, techs in tech_tree:
                tech_names.update(techs)

            used_slugs: set[str] = set()
            for entity in fused_list:
                eslug = slugify(entity["canonical_name"])
                # Deduplicate: append -2, -3, ... if slug already used
                if eslug in used_slugs:
                    counter = 2
                    while f"{eslug}-{counter}" in used_slugs:
                        counter += 1
                    eslug = f"{eslug}-{counter}"
                used_slugs.add(eslug)
                page_content = generate_entity_page(
                    conn, entity, civ["name"], civ_slug, id_to_primary, tech_names
                )
                _write_page(entity_dir / f"{eslug}.md", page_content)
                stats["entity_pages"] += 1
                current_page += 1
                if progress_callback:
                    progress_callback(current_page, total_pages, "page")

            # Phase 5: Generate knowledge base pages
            generate_tech_page(conn, civ["id"], civ["name"], output_dir)
            generate_resources_page(conn, civ["id"], civ["name"], output_dir)
            generate_beliefs_page(conn, civ["id"], civ["name"], output_dir)
            generate_geography_page(conn, civ["id"], civ["name"], output_dir)
            generate_choices_page(conn, civ["id"], civ["name"], output_dir)
            generate_relations_page(conn, civ["id"], civ["name"], output_dir)
            stats["pages_generated"] += 6

            # Phase 6: Generate analytics page
            generate_analytics_page(conn, civ["id"], civ["name"], output_dir)
            stats["pages_generated"] += 1

        _write_page(out / "global" / "timeline.md", generate_global_timeline(conn))
        stats["pages_generated"] += 1
        current_page += 1
        if progress_callback:
            progress_callback(current_page, total_pages, "page")

        _write_page(out / "global" / "entities.md", generate_global_entities(conn, all_fused))
        stats["pages_generated"] += 1
        current_page += 1
        if progress_callback:
            progress_callback(current_page, total_pages, "page")

        # Phase 6: Generate entity network page
        generate_entity_network_page(conn, output_dir)
        stats["pages_generated"] += 1
        current_page += 1
        if progress_callback:
            progress_callback(current_page, total_pages, "page")

        _write_page(out / "meta" / "pipeline.md", generate_pipeline_stats(conn))
        stats["pages_generated"] += 1
        current_page += 1
        if progress_callback:
            progress_callback(current_page, total_pages, "page")

        nav = _build_nav(civs)
        stats["nav_entries"] = nav

    finally:
        conn.close()

    # Count actual files written (authoritative — covers all generators)
    stats["pages_generated"] = sum(1 for _ in out.rglob("*.md"))

    return stats


def _write_page(path: Path, content: str) -> None:
    """Write a markdown page, creating directories as needed."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _build_nav(civs: list) -> list:
    """Build the nav structure for mkdocs.yml."""
    civ_nav = []
    for civ in civs:
        slug = slugify(civ["name"])
        civ_nav.append({
            civ["name"]: [
                {"Apercu": f"civilizations/{slug}/index.md"},
                {"Tours": f"civilizations/{slug}/turns/index.md"},
                {"Entites": f"civilizations/{slug}/entities/index.md"},
                {"Connaissances": [
                    {"Technologies": f"civilizations/{slug}/knowledge/technologies.md"},
                    {"Ressources": f"civilizations/{slug}/knowledge/resources.md"},
                    {"Croyances": f"civilizations/{slug}/knowledge/beliefs.md"},
                    {"Geographie": f"civilizations/{slug}/knowledge/geography.md"},
                    {"Choix": f"civilizations/{slug}/knowledge/choices.md"},
                    {"Relations": f"civilizations/{slug}/knowledge/relations.md"},
                    {"Analytics": f"civilizations/{slug}/knowledge/analytics.md"},
                ]},
            ]
        })

    return [
        {"Accueil": "index.md"},
        {"Civilisations": [
            {"Index": "civilizations/index.md"},
            *civ_nav,
        ]},
        {"Global": [
            {"Timeline": "global/timeline.md"},
            {"Entites": "global/entities.md"},
        ]},
        {"Meta": [
            {"Pipeline": "meta/pipeline.md"},
        ]},
    ]


def update_mkdocs_yml(wiki_dir: str, nav: list) -> None:
    """Update the mkdocs.yml nav section."""
    import yaml

    yml_path = Path(wiki_dir) / "mkdocs.yml"
    if not yml_path.exists():
        return

    with open(yml_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    config["nav"] = nav

    with open(yml_path, "w", encoding="utf-8") as f:
        yaml.dump(config, f, default_flow_style=False, allow_unicode=True, sort_keys=False)


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate Aurelm wiki from database")
    parser.add_argument("--db", required=True, help="Path to the SQLite database")
    parser.add_argument("--out", default="docs", help="Output directory for markdown files")
    parser.add_argument("--wiki-dir", default=None, help="Wiki root dir (for mkdocs.yml update)")
    args = parser.parse_args()

    print(f"Generating wiki from {args.db} -> {args.out}")
    stats = generate_wiki(args.db, args.out)
    print(f"Generated {stats['pages_generated']} pages + {stats.get('entity_pages', 0)} entity pages")

    if args.wiki_dir and stats.get("nav_entries"):
        try:
            update_mkdocs_yml(args.wiki_dir, stats["nav_entries"])
            print("Updated mkdocs.yml nav")
        except ImportError:
            print("PyYAML not available -- skipping mkdocs.yml update")


if __name__ == "__main__":
    main()
