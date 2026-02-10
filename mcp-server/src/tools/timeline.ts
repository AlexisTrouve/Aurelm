import type Database from "better-sqlite3";
import { truncate } from "../helpers.js";

interface TimelineRow {
  turn_number: number;
  title: string | null;
  summary: string | null;
  turn_type: string;
  game_date_start: string | null;
  game_date_end: string | null;
  civ_name: string;
  entity_count: number;
}

export function getTimeline(
  db: Database.Database,
  civId: number | null,
  limit: number
): string {
  let sql = `
    SELECT t.turn_number, t.title, t.summary, t.turn_type,
           t.game_date_start, t.game_date_end, c.name AS civ_name,
           (SELECT COUNT(DISTINCT m.entity_id) FROM entity_mentions m WHERE m.turn_id = t.id) AS entity_count
    FROM turn_turns t
    JOIN civ_civilizations c ON t.civ_id = c.id
  `;
  const params: unknown[] = [];

  if (civId !== null) {
    sql += " WHERE t.civ_id = ?";
    params.push(civId);
  }

  sql += " ORDER BY t.turn_number ASC, c.name LIMIT ?";
  params.push(limit);

  const rows = db.prepare(sql).all(...params) as TimelineRow[];

  if (rows.length === 0) {
    return "# Timeline\n\nNo turns found.";
  }

  const lines: string[] = [
    "# Timeline",
    "",
    `**${rows.length}** turn(s) shown.`,
    "",
    "| Civ | Turn | Title | Type | Date | Entities | Summary |",
    "|---|---|---|---|---|---|---|",
  ];

  for (const r of rows) {
    const title = r.title ?? "-";
    const date = r.game_date_start ?? "-";
    const summary = truncate(r.summary, 80);
    lines.push(
      `| ${r.civ_name} | ${r.turn_number} | ${title} | ${r.turn_type} | ${date} | ${r.entity_count} | ${summary} |`
    );
  }

  return lines.join("\n");
}
