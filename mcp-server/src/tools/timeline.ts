import Database from "better-sqlite3";

export interface TimelineEvent {
  turnNumber: number;
  title: string | null;
  summary: string | null;
  civName: string;
  turnType: string;
  gameDateStart: string | null;
  gameDateEnd: string | null;
}

export function getTimeline(
  db: Database.Database,
  civName?: string,
  limit: number = 20
): TimelineEvent[] {
  let sql = `
    SELECT t.turn_number, t.title, t.summary, t.turn_type,
           t.game_date_start, t.game_date_end, c.name as civ_name
    FROM turn_turns t
    JOIN civ_civilizations c ON t.civ_id = c.id
  `;
  const params: unknown[] = [];

  if (civName) {
    sql += " WHERE c.name = ?";
    params.push(civName);
  }

  sql += " ORDER BY t.created_at DESC LIMIT ?";
  params.push(limit);

  const rows = db.prepare(sql).all(...params) as Array<{
    turn_number: number;
    title: string | null;
    summary: string | null;
    turn_type: string;
    game_date_start: string | null;
    game_date_end: string | null;
    civ_name: string;
  }>;

  return rows.map((r) => ({
    turnNumber: r.turn_number,
    title: r.title,
    summary: r.summary,
    civName: r.civ_name,
    turnType: r.turn_type,
    gameDateStart: r.game_date_start,
    gameDateEnd: r.game_date_end,
  }));
}
