import type Database from "better-sqlite3";
import { truncate } from "../helpers.js";

interface TurnRow {
  turn_number: number;
  title: string | null;
  summary: string | null;
  turn_type: string;
  game_date_start: string | null;
}

interface EntityBreakdown {
  entity_type: string;
  count: number;
}

interface RecentEntity {
  canonical_name: string;
  entity_type: string;
  mention_count: number;
}

export function getCivState(db: Database.Database, civId: number, civName: string): string {
  const totalTurns = (
    db.prepare("SELECT COUNT(*) AS count FROM turn_turns WHERE civ_id = ?").get(civId) as { count: number }
  ).count;

  const totalEntities = (
    db.prepare("SELECT COUNT(*) AS count FROM entity_entities WHERE civ_id = ?").get(civId) as { count: number }
  ).count;

  // Entity breakdown by type
  const breakdown = db.prepare(
    "SELECT entity_type, COUNT(*) AS count FROM entity_entities WHERE civ_id = ? GROUP BY entity_type ORDER BY count DESC"
  ).all(civId) as EntityBreakdown[];

  // Recent 5 turns
  const recentTurns = db.prepare(
    "SELECT turn_number, title, summary, turn_type, game_date_start FROM turn_turns WHERE civ_id = ? ORDER BY turn_number DESC LIMIT 5"
  ).all(civId) as TurnRow[];

  // Most mentioned entities (top 10)
  const topEntities = db.prepare(`
    SELECT e.canonical_name, e.entity_type,
           (SELECT COUNT(*) FROM entity_mentions m WHERE m.entity_id = e.id) AS mention_count
    FROM entity_entities e
    WHERE e.civ_id = ?
    ORDER BY mention_count DESC
    LIMIT 10
  `).all(civId) as RecentEntity[];

  const lines: string[] = [
    `# ${civName}`,
    "",
    `**Total turns:** ${totalTurns}`,
    `**Total entities:** ${totalEntities}`,
    "",
  ];

  // Entity breakdown
  if (breakdown.length > 0) {
    lines.push("## Entity Breakdown", "");
    lines.push("| Type | Count |", "|---|---|");
    for (const b of breakdown) {
      lines.push(`| ${b.entity_type} | ${b.count} |`);
    }
    lines.push("");
  }

  // Top entities
  if (topEntities.length > 0) {
    lines.push("## Key Entities (by mentions)", "");
    lines.push("| Entity | Type | Mentions |", "|---|---|---|");
    for (const e of topEntities) {
      lines.push(`| ${e.canonical_name} | ${e.entity_type} | ${e.mention_count} |`);
    }
    lines.push("");
  }

  // Recent turns
  if (recentTurns.length > 0) {
    lines.push("## Recent Turns", "");
    for (const t of recentTurns) {
      const title = t.title ?? `Turn ${t.turn_number}`;
      const date = t.game_date_start ? ` (${t.game_date_start})` : "";
      lines.push(`### Turn ${t.turn_number}: ${title}${date}`);
      if (t.turn_type !== "standard") {
        lines.push(`**Type:** ${t.turn_type}`);
      }
      lines.push(`> ${truncate(t.summary, 300)}`);
      lines.push("");
    }
  }

  return lines.join("\n");
}
