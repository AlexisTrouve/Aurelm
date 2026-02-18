import type Database from "better-sqlite3";

interface TurnFactRow {
  turn_number: number;
  technologies: string | null;
  resources: string | null;
  beliefs: string | null;
  geography: string | null;
}

const VALID_FACT_TYPES = new Set(["technologies", "resources", "beliefs", "geography"]);

function parseJsonList(raw: string | null): string[] {
  if (!raw) return [];
  try {
    const parsed = JSON.parse(raw);
    if (Array.isArray(parsed)) return parsed.filter(Boolean).map(String);
  } catch {
    // Invalid JSON
  }
  return [];
}

export function getStructuredFacts(
  db: Database.Database,
  civId: number,
  civName: string,
  factType: string | undefined,
  turnNumber: number | undefined
): string {
  const typesToQuery = factType && VALID_FACT_TYPES.has(factType)
    ? [factType]
    : [...VALID_FACT_TYPES].sort();

  let sql = "SELECT turn_number, technologies, resources, beliefs, geography FROM turn_turns WHERE civ_id = ?";
  const params: unknown[] = [civId];

  if (turnNumber !== undefined) {
    sql += " AND turn_number = ?";
    params.push(turnNumber);
  }
  sql += " ORDER BY turn_number";

  const rows = db.prepare(sql).all(...params) as TurnFactRow[];

  const lines: string[] = [`# Structured Facts - ${civName}`, ""];
  if (factType && VALID_FACT_TYPES.has(factType)) {
    lines.push(`**Filter:** ${factType}`);
  }
  if (turnNumber !== undefined) {
    lines.push(`**Turn:** ${turnNumber}`);
  }
  lines.push("");

  let foundAny = false;
  for (const row of rows) {
    const colMap: Record<string, string | null> = {
      technologies: row.technologies,
      resources: row.resources,
      beliefs: row.beliefs,
      geography: row.geography,
    };

    const factsForTurn: Record<string, string[]> = {};
    for (const ft of typesToQuery) {
      const items = parseJsonList(colMap[ft]);
      if (items.length > 0) {
        factsForTurn[ft] = items;
      }
    }

    if (Object.keys(factsForTurn).length > 0) {
      foundAny = true;
      lines.push(`## Turn ${row.turn_number}`, "");
      for (const [ft, items] of Object.entries(factsForTurn)) {
        lines.push(`**${ft.charAt(0).toUpperCase() + ft.slice(1)}:**`);
        for (const item of items) {
          lines.push(`- ${item}`);
        }
        lines.push("");
      }
    }
  }

  if (!foundAny) {
    lines.push("No structured facts found for the given filters.");
  }

  return lines.join("\n");
}
