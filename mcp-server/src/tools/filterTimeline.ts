import type Database from "better-sqlite3";
import { truncate, escapeLike } from "../helpers.js";

interface TimelineRow {
  turn_number: number;
  title: string | null;
  summary: string | null;
  turn_type: string;
  game_date_start: string | null;
  civ_name: string;
}

export function filterTimeline(
  db: Database.Database,
  civId: number | null,
  turnType: string | undefined,
  fromTurn: number | undefined,
  toTurn: number | undefined,
  entityName: string | undefined
): string {
  let sql: string;
  const params: unknown[] = [];

  if (entityName) {
    const pattern = `%${escapeLike(entityName)}%`;
    sql = `
      SELECT DISTINCT t.turn_number, t.title, t.summary, t.turn_type,
             t.game_date_start, c.name AS civ_name
      FROM turn_turns t
      JOIN civ_civilizations c ON t.civ_id = c.id
      LEFT JOIN entity_mentions m ON m.turn_id = t.id
      LEFT JOIN entity_entities e ON m.entity_id = e.id
      LEFT JOIN entity_aliases a ON a.entity_id = e.id
      WHERE (e.canonical_name LIKE ? ESCAPE '!' OR a.alias LIKE ? ESCAPE '!')
    `;
    params.push(pattern, pattern);
  } else {
    sql = `
      SELECT t.turn_number, t.title, t.summary, t.turn_type,
             t.game_date_start, c.name AS civ_name
      FROM turn_turns t
      JOIN civ_civilizations c ON t.civ_id = c.id
      WHERE 1=1
    `;
  }

  if (civId !== null) {
    sql += " AND t.civ_id = ?";
    params.push(civId);
  }
  if (turnType) {
    sql += " AND t.turn_type = ?";
    params.push(turnType);
  }
  if (fromTurn !== undefined) {
    sql += " AND t.turn_number >= ?";
    params.push(fromTurn);
  }
  if (toTurn !== undefined) {
    sql += " AND t.turn_number <= ?";
    params.push(toTurn);
  }

  sql += " ORDER BY t.turn_number ASC, c.name LIMIT 100";

  const rows = db.prepare(sql).all(...params) as TimelineRow[];

  // Build title
  const filters: string[] = [];
  if (turnType) filters.push(`type=${turnType}`);
  if (fromTurn !== undefined || toTurn !== undefined) {
    filters.push(`turns ${fromTurn ?? "?"}-${toTurn ?? "?"}`);
  }
  if (entityName) filters.push(`entity=${entityName}`);
  const filterStr = filters.length > 0 ? ` (${filters.join(", ")})` : "";

  const lines: string[] = [`# Filtered Timeline${filterStr}`, ""];

  if (rows.length === 0) {
    lines.push("No turns match the given filters.");
    return lines.join("\n");
  }

  lines.push(
    `**${rows.length}** turn(s) found.`,
    "",
    "| Turn | Civilization | Type | Summary |",
    "|---|---|---|---|"
  );

  for (const r of rows) {
    const text = truncate(r.summary ?? r.title ?? "(no summary)", 100);
    lines.push(`| ${r.turn_number} | ${r.civ_name} | ${r.turn_type} | ${text} |`);
  }

  return lines.join("\n");
}
