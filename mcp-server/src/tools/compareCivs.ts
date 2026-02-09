import Database from "better-sqlite3";

export interface CivComparison {
  civilizations: Array<{
    name: string;
    turnCount: number;
    entityCount: number;
    entityBreakdown: Record<string, number>;
  }>;
}

export function compareCivs(
  db: Database.Database,
  civNames: string[],
  _aspects?: string[]
): CivComparison {
  const civilizations = civNames.map((name) => {
    const civ = db
      .prepare("SELECT id, name FROM civ_civilizations WHERE name = ?")
      .get(name) as { id: number; name: string } | undefined;

    if (!civ) {
      return {
        name,
        turnCount: 0,
        entityCount: 0,
        entityBreakdown: {},
      };
    }

    const turnCount = db
      .prepare("SELECT COUNT(*) as count FROM turn_turns WHERE civ_id = ?")
      .get(civ.id) as { count: number };

    const entityCount = db
      .prepare("SELECT COUNT(*) as count FROM entity_entities WHERE civ_id = ?")
      .get(civ.id) as { count: number };

    const breakdown = db
      .prepare(
        "SELECT entity_type, COUNT(*) as count FROM entity_entities WHERE civ_id = ? GROUP BY entity_type"
      )
      .all(civ.id) as Array<{ entity_type: string; count: number }>;

    const entityBreakdown: Record<string, number> = {};
    for (const row of breakdown) {
      entityBreakdown[row.entity_type] = row.count;
    }

    return {
      name: civ.name,
      turnCount: turnCount.count,
      entityCount: entityCount.count,
      entityBreakdown,
    };
  });

  return { civilizations };
}
