import Database from "better-sqlite3";

export interface LoreResult {
  entityName: string;
  entityType: string;
  civName: string | null;
  description: string | null;
  mentionCount: number;
}

export function searchLore(
  db: Database.Database,
  query: string,
  civName?: string,
  entityType?: string
): LoreResult[] {
  let sql = `
    SELECT e.canonical_name, e.entity_type, e.description, c.name as civ_name,
           (SELECT COUNT(*) FROM entity_mentions m WHERE m.entity_id = e.id) as mention_count
    FROM entity_entities e
    LEFT JOIN civ_civilizations c ON e.civ_id = c.id
    WHERE (e.canonical_name LIKE ? OR e.description LIKE ?)
  `;
  const params: unknown[] = [`%${query}%`, `%${query}%`];

  if (civName) {
    sql += " AND c.name = ?";
    params.push(civName);
  }
  if (entityType) {
    sql += " AND e.entity_type = ?";
    params.push(entityType);
  }

  sql += " ORDER BY mention_count DESC LIMIT 20";

  const rows = db.prepare(sql).all(...params) as Array<{
    canonical_name: string;
    entity_type: string;
    civ_name: string | null;
    description: string | null;
    mention_count: number;
  }>;

  return rows.map((r) => ({
    entityName: r.canonical_name,
    entityType: r.entity_type,
    civName: r.civ_name,
    description: r.description,
    mentionCount: r.mention_count,
  }));
}
