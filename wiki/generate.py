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
        "- [Historique complet des tours](turns.md)",
        "- [Index des entites](entities.md)",
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

        if key_events:
            lines.append("**Evenements cles** :")
            lines.append("")
            for evt in key_events:
                lines.append(f"- {evt}")
            lines.append("")

        if choices_made:
            lines.append("**Choix effectues** :")
            lines.append("")
            for choice in choices_made:
                lines.append(f"- {choice}")
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


def generate_civ_entities(conn: sqlite3.Connection, civ_id: int, civ_name: str) -> str:
    """Generate entity index for a civilization."""
    types = conn.execute(
        "SELECT DISTINCT entity_type FROM entity_entities WHERE civ_id = ? ORDER BY entity_type",
        (civ_id,),
    ).fetchall()

    lines = [f"# {civ_name} -- Entites", ""]

    for t in types:
        etype = t["entity_type"]
        entities = conn.execute(
            """SELECT e.canonical_name, e.entity_type, e.first_seen_turn, e.last_seen_turn,
                      (SELECT count(*) FROM entity_mentions m WHERE m.entity_id = e.id) as mention_count
               FROM entity_entities e
               WHERE e.civ_id = ? AND e.entity_type = ?
               ORDER BY e.canonical_name""",
            (civ_id, etype),
        ).fetchall()

        filtered = [e for e in entities if not is_noise_entity(e["canonical_name"])]
        if not filtered:
            continue

        lines.extend([
            f"## {_entity_type_label(etype)}",
            "",
            "| Nom | Mentions | Premiere apparition | Derniere apparition |",
            "|---|---|---|---|",
        ])
        for e in filtered:
            first = _turn_link(e["first_seen_turn"], conn) if e["first_seen_turn"] else "-"
            last = _turn_link(e["last_seen_turn"], conn) if e["last_seen_turn"] else "-"
            lines.append(f"| {_capitalize_entity(e['canonical_name'])} | {e['mention_count']} | {first} | {last} |")
        lines.append("")

    return "\n".join(lines)


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


def generate_global_entities(conn: sqlite3.Connection) -> str:
    """Generate global entity index across all civilizations."""
    types = conn.execute(
        "SELECT DISTINCT entity_type FROM entity_entities ORDER BY entity_type"
    ).fetchall()

    lines = ["# Index des Entites", ""]

    for t in types:
        etype = t["entity_type"]
        entities = conn.execute(
            """SELECT e.canonical_name, e.entity_type, c.name as civ_name,
                      (SELECT count(*) FROM entity_mentions m WHERE m.entity_id = e.id) as mention_count
               FROM entity_entities e
               LEFT JOIN civ_civilizations c ON e.civ_id = c.id
               WHERE e.entity_type = ?
               ORDER BY e.canonical_name""",
            (etype,),
        ).fetchall()

        filtered = [e for e in entities if not is_noise_entity(e["canonical_name"])]
        if not filtered:
            continue

        lines.extend([
            f"## {_entity_type_label(etype)}",
            "",
            "| Nom | Civilisation | Mentions |",
            "|---|---|---|",
        ])
        for e in filtered:
            civ = e["civ_name"] or "Global"
            lines.append(f"| {_capitalize_entity(e['canonical_name'])} | {civ} | {e['mention_count']} |")
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


def _turn_link(turn_id: int | None, conn: sqlite3.Connection) -> str:
    """Create a turn reference string."""
    if not turn_id:
        return "-"
    row = conn.execute(
        "SELECT turn_number FROM turn_turns WHERE id = ?", (turn_id,)
    ).fetchone()
    return f"Tour {row['turn_number']}" if row else "-"


# -- Main generation -----------------------------------------------------------

def generate_wiki(db_path: str, output_dir: str) -> dict:
    """Generate all wiki pages from the database. Returns stats."""
    out = Path(output_dir)
    conn = get_connection(db_path)
    stats = {"pages_generated": 0}

    try:
        _write_page(out / "index.md", generate_index(conn))
        stats["pages_generated"] += 1

        _write_page(out / "civilizations" / "index.md", generate_civilizations_index(conn))
        stats["pages_generated"] += 1

        civs = conn.execute("SELECT * FROM civ_civilizations ORDER BY name").fetchall()
        for civ in civs:
            civ_slug = slugify(civ["name"])
            civ_dir = out / "civilizations" / civ_slug

            _write_page(civ_dir / "index.md",
                        generate_civ_index(conn, civ["id"], civ["name"], civ["player_name"]))
            _write_page(civ_dir / "turns.md",
                        generate_civ_turns(conn, civ["id"], civ["name"]))
            _write_page(civ_dir / "entities.md",
                        generate_civ_entities(conn, civ["id"], civ["name"]))
            stats["pages_generated"] += 3

        _write_page(out / "global" / "timeline.md", generate_global_timeline(conn))
        _write_page(out / "global" / "entities.md", generate_global_entities(conn))
        stats["pages_generated"] += 2

        _write_page(out / "meta" / "pipeline.md", generate_pipeline_stats(conn))
        stats["pages_generated"] += 1

        nav = _build_nav(civs)
        stats["nav_entries"] = nav

    finally:
        conn.close()

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
                {"Tours": f"civilizations/{slug}/turns.md"},
                {"Entites": f"civilizations/{slug}/entities.md"},
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
    print(f"Generated {stats['pages_generated']} pages")

    if args.wiki_dir and stats.get("nav_entries"):
        try:
            update_mkdocs_yml(args.wiki_dir, stats["nav_entries"])
            print("Updated mkdocs.yml nav")
        except ImportError:
            print("PyYAML not available -- skipping mkdocs.yml update")


if __name__ == "__main__":
    main()
