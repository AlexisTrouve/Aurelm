import type Database from "better-sqlite3";
import { escapeLike, truncate } from "../helpers.js";

interface SegmentResult {
  turn_number: number;
  civ_name: string;
  segment_type: string;
  content: string;
  title: string | null;
}

export function searchTurnContent(
  db: Database.Database,
  query: string,
  civId: number | null,
  segmentType: string | undefined
): string {
  let sql = `
    SELECT t.turn_number, c.name AS civ_name, s.segment_type, s.content, t.title
    FROM turn_segments s
    JOIN turn_turns t ON s.turn_id = t.id
    JOIN civ_civilizations c ON t.civ_id = c.id
    WHERE s.content LIKE ? ESCAPE '!'
  `;
  const params: unknown[] = [`%${escapeLike(query)}%`];

  if (civId !== null) {
    sql += " AND t.civ_id = ?";
    params.push(civId);
  }

  if (segmentType) {
    sql += " AND s.segment_type = ?";
    params.push(segmentType);
  }

  sql += " ORDER BY t.turn_number DESC LIMIT 20";

  const rows = db.prepare(sql).all(...params) as SegmentResult[];

  if (rows.length === 0) {
    return `# Turn Content Search: "${query}"\n\nNo segments found matching "${query}".`;
  }

  const lines: string[] = [
    `# Turn Content Search: "${query}"`,
    "",
    `**${rows.length}** segment(s) found.`,
    "",
  ];

  for (const r of rows) {
    const title = r.title ?? `Turn ${r.turn_number}`;
    lines.push(`## ${r.civ_name} - Turn ${r.turn_number}: ${title}`);
    lines.push(`**Segment type:** ${r.segment_type}`);
    lines.push("");
    lines.push(`> ${truncate(r.content, 500)}`);
    lines.push("");
  }

  return lines.join("\n");
}
