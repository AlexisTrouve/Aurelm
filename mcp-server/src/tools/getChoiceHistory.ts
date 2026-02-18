import type Database from "better-sqlite3";
import { truncate } from "../helpers.js";

interface ChoiceRow {
  turn_number: number;
  title: string | null;
  summary: string | null;
  choices_proposed: string | null;
  choices_made: string | null;
}

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

export function getChoiceHistory(
  db: Database.Database,
  civId: number,
  civName: string,
  turnNumber: number | undefined
): string {
  let sql = `
    SELECT turn_number, title, summary, choices_proposed, choices_made
    FROM turn_turns
    WHERE civ_id = ? AND (choices_proposed IS NOT NULL OR choices_made IS NOT NULL)
  `;
  const params: unknown[] = [civId];

  if (turnNumber !== undefined) {
    sql += " AND turn_number = ?";
    params.push(turnNumber);
  }
  sql += " ORDER BY turn_number";

  const rows = db.prepare(sql).all(...params) as ChoiceRow[];

  const lines: string[] = [`# Choice History - ${civName}`, ""];

  if (rows.length === 0) {
    lines.push("No choices recorded for this civilization.");
    return lines.join("\n");
  }

  for (const row of rows) {
    lines.push(`## Turn ${row.turn_number}: ${row.title ?? "(untitled)"}`);
    if (row.summary) {
      lines.push(`*${truncate(row.summary, 200)}*`);
    }
    lines.push("");

    const proposed = parseJsonList(row.choices_proposed);
    if (proposed.length > 0) {
      lines.push("**Choices proposed:**");
      proposed.forEach((choice, i) => {
        lines.push(`${i + 1}. ${choice}`);
      });
      lines.push("");
    }

    const made = parseJsonList(row.choices_made);
    if (made.length > 0) {
      lines.push("**Decision:**");
      for (const decision of made) {
        lines.push(`-> ${decision}`);
      }
      lines.push("");
    }
  }

  return lines.join("\n");
}
