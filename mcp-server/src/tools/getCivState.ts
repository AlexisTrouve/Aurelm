import Database from "better-sqlite3";

export interface CivState {
  name: string;
  playerName: string | null;
  totalTurns: number;
  entityCount: number;
  recentTurns: Array<{
    turnNumber: number;
    title: string | null;
    summary: string | null;
  }>;
}

export function getCivState(db: Database.Database, civName: string): CivState | null {
  const civ = db
    .prepare("SELECT * FROM civ_civilizations WHERE name = ?")
    .get(civName) as { id: number; name: string; player_name: string | null } | undefined;

  if (!civ) return null;

  const totalTurns = db
    .prepare("SELECT COUNT(*) as count FROM turn_turns WHERE civ_id = ?")
    .get(civ.id) as { count: number };

  const entityCount = db
    .prepare("SELECT COUNT(*) as count FROM entity_entities WHERE civ_id = ?")
    .get(civ.id) as { count: number };

  const recentTurns = db
    .prepare(
      "SELECT turn_number, title, summary FROM turn_turns WHERE civ_id = ? ORDER BY turn_number DESC LIMIT 5"
    )
    .all(civ.id) as Array<{ turn_number: number; title: string | null; summary: string | null }>;

  return {
    name: civ.name,
    playerName: civ.player_name,
    totalTurns: totalTurns.count,
    entityCount: entityCount.count,
    recentTurns: recentTurns.map((t) => ({
      turnNumber: t.turn_number,
      title: t.title,
      summary: t.summary,
    })),
  };
}
