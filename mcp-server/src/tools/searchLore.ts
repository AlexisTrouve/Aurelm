import type Database from "better-sqlite3";
import { truncate } from "../helpers.js";

interface EntityRow {
  id: number;
  canonical_name: string;
  entity_type: string;
  description: string | null;
  civ_name: string | null;
  mention_count: number;
}

interface MentionRow {
  mention_text: string;
  context: string | null;
  turn_number: number;
}

interface AliasRow {
  alias: string;
}

export function searchLore(
  db: Database.Database,
  query: string,
  civId: number | null,
  entityType: string | undefined
): string {
  // Search entities by canonical name, description, AND aliases
  let sql = `
    SELECT DISTINCT e.id, e.canonical_name, e.entity_type, e.description,
           c.name AS civ_name,
           (SELECT COUNT(*) FROM entity_mentions m WHERE m.entity_id = e.id) AS mention_count
    FROM entity_entities e
    LEFT JOIN civ_civilizations c ON e.civ_id = c.id
    LEFT JOIN entity_aliases a ON a.entity_id = e.id
    WHERE (e.canonical_name LIKE ? OR e.description LIKE ? OR a.alias LIKE ?)
  `;
  const params: unknown[] = [`%${query}%`, `%${query}%`, `%${query}%`];

  if (civId !== null) {
    sql += " AND e.civ_id = ?";
    params.push(civId);
  }
  if (entityType) {
    sql += " AND e.entity_type = ?";
    params.push(entityType);
  }

  sql += " ORDER BY mention_count DESC LIMIT 20";

  const entities = db.prepare(sql).all(...params) as EntityRow[];

  if (entities.length === 0) {
    return `# Lore Search: "${query}"\n\nNo entities found matching "${query}".`;
  }

  const lines: string[] = [
    `# Lore Search: "${query}"`,
    "",
    `**${entities.length}** result(s) found.`,
    "",
  ];

  for (const e of entities) {
    lines.push(`## ${e.canonical_name} (${e.entity_type})`);
    if (e.civ_name) lines.push(`**Civilization:** ${e.civ_name}`);
    lines.push(`**Mentions:** ${e.mention_count}`);
    if (e.description) lines.push(`**Description:** ${e.description}`);

    // Aliases
    const aliases = db.prepare(
      "SELECT alias FROM entity_aliases WHERE entity_id = ?"
    ).all(e.id) as AliasRow[];
    if (aliases.length > 0) {
      lines.push(`**Aliases:** ${aliases.map((a) => a.alias).join(", ")}`);
    }

    // 3 most recent mentions with context
    const mentions = db.prepare(`
      SELECT m.mention_text, m.context, t.turn_number
      FROM entity_mentions m
      JOIN turn_turns t ON m.turn_id = t.id
      WHERE m.entity_id = ?
      ORDER BY t.turn_number DESC
      LIMIT 3
    `).all(e.id) as MentionRow[];

    if (mentions.length > 0) {
      lines.push("", "**Recent mentions:**");
      for (const m of mentions) {
        const ctx = m.context ? truncate(m.context, 150) : m.mention_text;
        lines.push(`- Turn ${m.turn_number}: ${ctx}`);
      }
    }

    lines.push("");
  }

  return lines.join("\n");
}
