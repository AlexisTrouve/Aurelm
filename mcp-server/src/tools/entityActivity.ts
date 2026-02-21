import type Database from "better-sqlite3";
import { escapeLike, truncate } from "../helpers.js";

interface EntityMatch {
  id: number;
  canonical_name: string;
  entity_type: string;
}

interface TurnCountRow {
  turn_number: number;
  cnt: number;
}

interface MentionRow {
  context: string | null;
  turn_number: number;
}

function resolveEntity(
  db: Database.Database,
  entityName: string,
  civId: number | null
): EntityMatch[] {
  let sql = `
    SELECT e.id, e.canonical_name, e.entity_type
    FROM entity_entities e
    WHERE (e.canonical_name LIKE ? ESCAPE '!' OR e.id IN (
      SELECT a.entity_id FROM entity_aliases a WHERE a.alias LIKE ? ESCAPE '!'
    ))
  `;
  const pattern = `%${escapeLike(entityName)}%`;
  const params: unknown[] = [pattern, pattern];

  if (civId !== null) {
    sql += " AND e.civ_id = ?";
    params.push(civId);
  }
  sql += " ORDER BY e.canonical_name LIMIT 5";

  return db.prepare(sql).all(...params) as EntityMatch[];
}

export function entityActivity(
  db: Database.Database,
  entityName: string,
  civId: number | null
): string {
  const entities = resolveEntity(db, entityName, civId);
  if (entities.length === 0) {
    return `# Entity Activity: "${entityName}"\n\nNo entity found matching "${entityName}".`;
  }

  const entity = entities[0];

  const rows = db.prepare(`
    SELECT t.turn_number, COUNT(*) AS cnt
    FROM entity_mentions m
    JOIN turn_turns t ON m.turn_id = t.id
    WHERE m.entity_id = ?
    GROUP BY t.turn_number
    ORDER BY t.turn_number
  `).all(entity.id) as TurnCountRow[];

  const lines: string[] = [`# Entity Activity: ${entity.canonical_name} (${entity.entity_type})`, ""];

  if (rows.length === 0) {
    lines.push("No mentions found.");
    return lines.join("\n");
  }

  const firstTurn = rows[0].turn_number;
  const lastTurn = rows[rows.length - 1].turn_number;
  const totalMentions = rows.reduce((sum, r) => sum + r.cnt, 0);
  const peak = rows.reduce((best, r) => r.cnt > best.cnt ? r : best, rows[0]);

  lines.push(`**First appearance:** Turn ${firstTurn}`);
  lines.push(`**Last appearance:** Turn ${lastTurn}`);
  lines.push(`**Total mentions:** ${totalMentions}`);
  lines.push(`**Peak activity:** Turn ${peak.turn_number} (${peak.cnt} mentions)`);
  lines.push("");

  // ASCII sparkline
  const maxCount = Math.max(...rows.map((r) => r.cnt));
  const sparkChars = " _.-:=+*#";

  lines.push("## Activity by Turn", "", "```");
  for (const r of rows) {
    const barIdx = Math.min(
      Math.floor((r.cnt / maxCount) * (sparkChars.length - 1)),
      sparkChars.length - 1
    );
    const bar = sparkChars[barIdx].repeat(r.cnt);
    lines.push(`Turn ${String(r.turn_number).padStart(3)}: ${bar} (${r.cnt})`);
  }
  lines.push("```", "");

  // Recent contexts
  const recent = db.prepare(`
    SELECT m.context, t.turn_number
    FROM entity_mentions m
    JOIN turn_turns t ON m.turn_id = t.id
    WHERE m.entity_id = ?
    ORDER BY t.turn_number DESC
    LIMIT 3
  `).all(entity.id) as MentionRow[];

  if (recent.length > 0) {
    lines.push("## Recent Mentions", "");
    for (const r of recent) {
      const ctx = r.context ? truncate(r.context, 200) : "(no context)";
      lines.push(`- **Turn ${r.turn_number}:** ${ctx}`);
    }
  }

  return lines.join("\n");
}
