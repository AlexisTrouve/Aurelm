import type Database from "better-sqlite3";

interface CivRow {
  name: string;
  player_name: string | null;
  turn_count: number;
  entity_count: number;
}

export function listCivs(db: Database.Database): string {
  const rows = db.prepare(`
    SELECT c.name, c.player_name,
           (SELECT COUNT(*) FROM turn_turns t WHERE t.civ_id = c.id) AS turn_count,
           (SELECT COUNT(*) FROM entity_entities e WHERE e.civ_id = c.id) AS entity_count
    FROM civ_civilizations c
    ORDER BY c.name
  `).all() as CivRow[];

  if (rows.length === 0) {
    return "# Civilizations\n\nNo civilizations found in the database.";
  }

  const lines: string[] = [
    "# Civilizations",
    "",
    `**${rows.length}** civilization(s) in the database.`,
    "",
    "| Civilization | Player | Turns | Entities |",
    "|---|---|---|---|",
  ];

  for (const r of rows) {
    lines.push(
      `| ${r.name} | ${r.player_name ?? "unknown"} | ${r.turn_count} | ${r.entity_count} |`
    );
  }

  return lines.join("\n");
}
