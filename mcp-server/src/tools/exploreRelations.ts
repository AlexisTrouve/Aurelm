import type Database from "better-sqlite3";
import { escapeLike } from "../helpers.js";

interface EntityMatch {
  id: number;
  canonical_name: string;
  entity_type: string;
}

interface RelationRow {
  direction: string;
  other_id: number;
  other_name: string;
  other_type: string;
  relation_type: string;
  description: string | null;
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

export function exploreRelations(
  db: Database.Database,
  entityName: string,
  civId: number | null,
  depth: number
): string {
  const entities = resolveEntity(db, entityName, civId);
  if (entities.length === 0) {
    return `# Relations: "${entityName}"\n\nNo entity found matching "${entityName}".`;
  }

  const root = entities[0];
  const lines: string[] = [`# Relations: ${root.canonical_name} (${root.entity_type})`, ""];

  const visited = new Set<number>();
  const queue: Array<{ id: number; name: string; depth: number }> = [
    { id: root.id, name: root.canonical_name, depth: 0 },
  ];
  const relationLines: string[] = [];

  const relStmt = db.prepare(`
    SELECT 'outgoing' AS direction, t.id AS other_id, t.canonical_name AS other_name,
           t.entity_type AS other_type, r.relation_type, r.description
    FROM entity_relations r
    JOIN entity_entities t ON r.target_entity_id = t.id
    WHERE r.source_entity_id = ? AND r.is_active = 1
    UNION ALL
    SELECT 'incoming' AS direction, s.id AS other_id, s.canonical_name AS other_name,
           s.entity_type AS other_type, r.relation_type, r.description
    FROM entity_relations r
    JOIN entity_entities s ON r.source_entity_id = s.id
    WHERE r.target_entity_id = ? AND r.is_active = 1
  `);

  while (queue.length > 0) {
    const item = queue.shift()!;
    if (visited.has(item.id)) continue;
    visited.add(item.id);

    const rels = relStmt.all(item.id, item.id) as RelationRow[];

    for (const rel of rels) {
      const indent = "  ".repeat(item.depth);
      const arrow = rel.direction === "outgoing"
        ? `${item.name} --[${rel.relation_type}]--> ${rel.other_name} (${rel.other_type})`
        : `${rel.other_name} (${rel.other_type}) --[${rel.relation_type}]--> ${item.name}`;
      const detail = rel.description ? ` -- ${rel.description}` : "";
      relationLines.push(`${indent}- ${arrow}${detail}`);

      if (item.depth + 1 < depth && !visited.has(rel.other_id)) {
        queue.push({ id: rel.other_id, name: rel.other_name, depth: item.depth + 1 });
      }
    }
  }

  if (relationLines.length > 0) {
    lines.push(`**Depth:** ${depth}`);
    lines.push(`**Relations found:** ${relationLines.length}`);
    lines.push("");
    lines.push(...relationLines);
  } else {
    lines.push("No relations found for this entity.");
  }

  return lines.join("\n");
}
