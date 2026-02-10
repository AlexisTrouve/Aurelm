import type Database from "better-sqlite3";
import { FRENCH_STOPWORDS, truncate } from "../helpers.js";

interface MatchedEntity {
  id: number;
  canonical_name: string;
  entity_type: string;
  description: string | null;
  civ_name: string | null;
  aliases: string[];
  mention_count: number;
  recent_mentions: Array<{ turn_number: number; context: string }>;
}

interface InventoryEntry {
  canonical_name: string;
  entity_type: string;
}

/**
 * Extract candidate search terms from a natural language statement.
 * Removes French stopwords, generates unigrams + bigrams + trigrams.
 */
function extractSearchTerms(statement: string): string[] {
  // Normalize: lowercase, remove punctuation except hyphens
  const normalized = statement
    .toLowerCase()
    .replace(/[^a-z\u00e0-\u00ff\s'-]/g, "")
    .trim();

  const words = normalized.split(/\s+/).filter(
    (w) => w.length > 2 && !FRENCH_STOPWORDS.has(w)
  );

  const terms = new Set<string>();

  // Unigrams
  for (const w of words) {
    terms.add(w);
  }

  // Bigrams
  for (let i = 0; i < words.length - 1; i++) {
    terms.add(`${words[i]} ${words[i + 1]}`);
  }

  // Trigrams
  for (let i = 0; i < words.length - 2; i++) {
    terms.add(`${words[i]} ${words[i + 1]} ${words[i + 2]}`);
  }

  return [...terms];
}

export function sanityCheck(
  db: Database.Database,
  statement: string,
  civId: number | null,
  civName: string | null
): string {
  const searchTerms = extractSearchTerms(statement);

  // Find matching entities by canonical_name or alias
  const matchedEntityIds = new Set<number>();
  const matchedEntities: MatchedEntity[] = [];

  for (const term of searchTerms) {
    const pattern = `%${term}%`;

    // Search canonical names
    const byName = db.prepare(`
      SELECT e.id FROM entity_entities e
      WHERE e.canonical_name LIKE ?
      ${civId !== null ? "AND e.civ_id = ?" : ""}
    `).all(...(civId !== null ? [pattern, civId] : [pattern])) as Array<{ id: number }>;

    for (const row of byName) matchedEntityIds.add(row.id);

    // Search aliases
    const byAlias = db.prepare(`
      SELECT a.entity_id AS id FROM entity_aliases a
      JOIN entity_entities e ON a.entity_id = e.id
      WHERE a.alias LIKE ?
      ${civId !== null ? "AND e.civ_id = ?" : ""}
    `).all(...(civId !== null ? [pattern, civId] : [pattern])) as Array<{ id: number }>;

    for (const row of byAlias) matchedEntityIds.add(row.id);
  }

  // Fetch details for each matched entity
  for (const entityId of matchedEntityIds) {
    const entity = db.prepare(`
      SELECT e.id, e.canonical_name, e.entity_type, e.description,
             c.name AS civ_name
      FROM entity_entities e
      LEFT JOIN civ_civilizations c ON e.civ_id = c.id
      WHERE e.id = ?
    `).get(entityId) as {
      id: number; canonical_name: string; entity_type: string;
      description: string | null; civ_name: string | null;
    } | undefined;

    if (!entity) continue;

    const aliases = db.prepare(
      "SELECT alias FROM entity_aliases WHERE entity_id = ?"
    ).all(entityId) as Array<{ alias: string }>;

    const mentionCount = (
      db.prepare("SELECT COUNT(*) AS count FROM entity_mentions WHERE entity_id = ?").get(entityId) as { count: number }
    ).count;

    const recentMentions = db.prepare(`
      SELECT t.turn_number, m.context
      FROM entity_mentions m
      JOIN turn_turns t ON m.turn_id = t.id
      WHERE m.entity_id = ?
      ORDER BY t.turn_number DESC
      LIMIT 5
    `).all(entityId) as Array<{ turn_number: number; context: string | null }>;

    matchedEntities.push({
      id: entity.id,
      canonical_name: entity.canonical_name,
      entity_type: entity.entity_type,
      description: entity.description,
      civ_name: entity.civ_name,
      aliases: aliases.map((a) => a.alias),
      mention_count: mentionCount,
      recent_mentions: recentMentions.map((m) => ({
        turn_number: m.turn_number,
        context: m.context ?? "(no context)",
      })),
    });
  }

  // Get civ entity inventory (all entities grouped by type)
  let inventoryLines: string[] = [];
  if (civId !== null) {
    const inventory = db.prepare(`
      SELECT canonical_name, entity_type
      FROM entity_entities
      WHERE civ_id = ?
      ORDER BY entity_type, canonical_name
      LIMIT 200
    `).all(civId) as InventoryEntry[];

    if (inventory.length > 0) {
      const grouped: Record<string, string[]> = {};
      for (const e of inventory) {
        if (!grouped[e.entity_type]) grouped[e.entity_type] = [];
        grouped[e.entity_type].push(e.canonical_name);
      }

      inventoryLines.push("## Entity Inventory" + (civName ? ` - ${civName}` : ""), "");
      for (const [type, names] of Object.entries(grouped)) {
        inventoryLines.push(`**${type}** (${names.length}): ${names.join(", ")}`);
      }
    }
  }

  // Get last 5 turns for temporal context
  let recentTurnsLines: string[] = [];
  const turnFilter = civId !== null ? "WHERE t.civ_id = ?" : "";
  const turnParams = civId !== null ? [civId] : [];
  const recentTurns = db.prepare(`
    SELECT t.turn_number, t.title, t.summary, c.name AS civ_name
    FROM turn_turns t
    JOIN civ_civilizations c ON t.civ_id = c.id
    ${turnFilter}
    ORDER BY t.turn_number DESC
    LIMIT 5
  `).all(...turnParams) as Array<{
    turn_number: number; title: string | null; summary: string | null; civ_name: string;
  }>;

  if (recentTurns.length > 0) {
    recentTurnsLines.push("## Recent Turns (temporal context)", "");
    for (const t of recentTurns) {
      recentTurnsLines.push(`- **Turn ${t.turn_number}** (${t.civ_name}): ${truncate(t.summary ?? t.title ?? "(no summary)", 200)}`);
    }
  }

  // Build output
  const lines: string[] = [
    "# Sanity Check",
    "",
    `**Statement:** "${statement}"`,
    `**Context:** ${civName ?? "global"}`,
    `**Search terms extracted:** ${searchTerms.join(", ")}`,
    "",
  ];

  if (matchedEntities.length === 0) {
    lines.push("## Matched Entities: NONE", "");
    lines.push(
      "No entities in the database match the terms in this statement. " +
      "This could mean the statement introduces new lore, or uses terms not yet tracked."
    );
  } else {
    lines.push(`## Matched Entities (${matchedEntities.length})`, "");
    for (const e of matchedEntities) {
      lines.push(`### ${e.canonical_name} (${e.entity_type})`);
      if (e.civ_name) lines.push(`**Civilization:** ${e.civ_name}`);
      if (e.description) lines.push(`**Description:** ${e.description}`);
      if (e.aliases.length > 0) lines.push(`**Aliases:** ${e.aliases.join(", ")}`);
      lines.push(`**Mentions:** ${e.mention_count}`);

      if (e.recent_mentions.length > 0) {
        lines.push("", "**Recent references:**");
        for (const m of e.recent_mentions) {
          lines.push(`- Turn ${m.turn_number}: ${truncate(m.context, 200)}`);
        }
      }
      lines.push("");
    }
  }

  lines.push("");
  if (inventoryLines.length > 0) lines.push(...inventoryLines, "");
  if (recentTurnsLines.length > 0) lines.push(...recentTurnsLines, "");

  return lines.join("\n");
}
