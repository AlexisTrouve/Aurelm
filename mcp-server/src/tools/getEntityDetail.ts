import type Database from "better-sqlite3";
import { truncate } from "../helpers.js";

interface EntityRow {
  id: number;
  canonical_name: string;
  entity_type: string;
  description: string | null;
  history: string | null;
  civ_name: string | null;
  is_active: number;
  first_turn: number | null;
  last_turn: number | null;
}

interface RelationRow {
  direction: string;
  other_name: string;
  other_type: string;
  relation_type: string;
  description: string | null;
  turn_number: number | null;
}

interface MentionRow {
  mention_text: string;
  context: string | null;
  turn_number: number;
  segment_type: string | null;
}

export function getEntityDetail(
  db: Database.Database,
  entityName: string,
  civId: number | null
): string {
  // Find entity by canonical name or alias, optionally scoped to civ
  let entitySql = `
    SELECT e.id, e.canonical_name, e.entity_type, e.description, e.history,
           c.name AS civ_name, e.is_active,
           ft.turn_number AS first_turn, lt.turn_number AS last_turn
    FROM entity_entities e
    LEFT JOIN civ_civilizations c ON e.civ_id = c.id
    LEFT JOIN turn_turns ft ON e.first_seen_turn = ft.id
    LEFT JOIN turn_turns lt ON e.last_seen_turn = lt.id
    WHERE (e.canonical_name LIKE ? OR e.id IN (
      SELECT a.entity_id FROM entity_aliases a WHERE a.alias LIKE ?
    ))
  `;
  const params: unknown[] = [`%${entityName}%`, `%${entityName}%`];

  if (civId !== null) {
    entitySql += " AND e.civ_id = ?";
    params.push(civId);
  }

  entitySql += " ORDER BY e.canonical_name LIMIT 5";

  const entities = db.prepare(entitySql).all(...params) as EntityRow[];

  if (entities.length === 0) {
    return `# Entity Detail: "${entityName}"\n\nNo entity found matching "${entityName}".`;
  }

  const lines: string[] = [];

  for (const e of entities) {
    lines.push(`# ${e.canonical_name} (${e.entity_type})`);
    lines.push("");
    if (e.civ_name) lines.push(`**Civilization:** ${e.civ_name}`);
    lines.push(`**Status:** ${e.is_active ? "active" : "inactive"}`);
    if (e.first_turn !== null) lines.push(`**First seen:** Turn ${e.first_turn}`);
    if (e.last_turn !== null) lines.push(`**Last seen:** Turn ${e.last_turn}`);
    if (e.description) lines.push(`**Description:** ${e.description}`);

    // History timeline from LLM profiler
    if (e.history) {
      try {
        const events = JSON.parse(e.history) as string[];
        if (events.length > 0) {
          lines.push("", "## Chronologie", "");
          for (const event of events) {
            lines.push(`- ${event}`);
          }
        }
      } catch {
        // Invalid JSON — skip history
      }
    }

    // Aliases
    const aliases = db.prepare(
      "SELECT alias FROM entity_aliases WHERE entity_id = ?"
    ).all(e.id) as Array<{ alias: string }>;
    if (aliases.length > 0) {
      lines.push(`**Aliases:** ${aliases.map((a) => a.alias).join(", ")}`);
    }

    // Relations (both directions)
    const relations = db.prepare(`
      SELECT 'outgoing' AS direction, t.canonical_name AS other_name, t.entity_type AS other_type,
             r.relation_type, r.description, tt.turn_number
      FROM entity_relations r
      JOIN entity_entities t ON r.target_entity_id = t.id
      LEFT JOIN turn_turns tt ON r.turn_id = tt.id
      WHERE r.source_entity_id = ? AND r.is_active = 1
      UNION ALL
      SELECT 'incoming' AS direction, s.canonical_name AS other_name, s.entity_type AS other_type,
             r.relation_type, r.description, tt.turn_number
      FROM entity_relations r
      JOIN entity_entities s ON r.source_entity_id = s.id
      LEFT JOIN turn_turns tt ON r.turn_id = tt.id
      WHERE r.target_entity_id = ? AND r.is_active = 1
    `).all(e.id, e.id) as RelationRow[];

    if (relations.length > 0) {
      lines.push("", "## Relations", "");
      lines.push("| Direction | Entity | Type | Relation | Turn |", "|---|---|---|---|---|");
      for (const r of relations) {
        const arrow = r.direction === "outgoing" ? "->" : "<-";
        const turn = r.turn_number !== null ? `${r.turn_number}` : "-";
        lines.push(`| ${arrow} | ${r.other_name} | ${r.other_type} | ${r.relation_type} | ${turn} |`);
      }
    }

    // Mentions (up to 20)
    const mentions = db.prepare(`
      SELECT m.mention_text, m.context, t.turn_number, s.segment_type
      FROM entity_mentions m
      JOIN turn_turns t ON m.turn_id = t.id
      LEFT JOIN turn_segments s ON m.segment_id = s.id
      WHERE m.entity_id = ?
      ORDER BY t.turn_number DESC
      LIMIT 20
    `).all(e.id) as MentionRow[];

    if (mentions.length > 0) {
      lines.push("", "## Mentions", "");
      for (const m of mentions) {
        const segType = m.segment_type ? ` [${m.segment_type}]` : "";
        const ctx = m.context ? truncate(m.context, 200) : m.mention_text;
        lines.push(`- **Turn ${m.turn_number}**${segType}: ${ctx}`);
      }
    }

    lines.push("");
  }

  return lines.join("\n");
}
