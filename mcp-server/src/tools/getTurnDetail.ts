import type Database from "better-sqlite3";
import { truncate } from "../helpers.js";

interface TurnRow {
  id: number;
  turn_number: number;
  title: string | null;
  summary: string | null;
  turn_type: string;
  game_date_start: string | null;
  game_date_end: string | null;
  civ_name: string;
}

interface SegmentRow {
  segment_order: number;
  segment_type: string;
  content: string;
}

interface MentionedEntity {
  canonical_name: string;
  entity_type: string;
  mention_count: number;
}

export function getTurnDetail(
  db: Database.Database,
  turnNumber: number,
  civId: number,
  civName: string
): string {
  const turn = db.prepare(`
    SELECT t.id, t.turn_number, t.title, t.summary, t.turn_type,
           t.game_date_start, t.game_date_end, c.name AS civ_name
    FROM turn_turns t
    JOIN civ_civilizations c ON t.civ_id = c.id
    WHERE t.turn_number = ? AND t.civ_id = ?
  `).get(turnNumber, civId) as TurnRow | undefined;

  if (!turn) {
    // Find available turn numbers for this civ
    const turns = db.prepare(
      "SELECT turn_number FROM turn_turns WHERE civ_id = ? ORDER BY turn_number"
    ).all(civId) as Array<{ turn_number: number }>;

    const available = turns.map((t) => t.turn_number).join(", ");
    return `# Turn ${turnNumber} - ${civName}\n\nTurn not found. Available turns: ${available || "none"}`;
  }

  const lines: string[] = [
    `# Turn ${turn.turn_number}: ${turn.title ?? "(untitled)"} - ${turn.civ_name}`,
    "",
  ];

  if (turn.turn_type !== "standard") lines.push(`**Type:** ${turn.turn_type}`);
  if (turn.game_date_start) lines.push(`**Game date:** ${turn.game_date_start}${turn.game_date_end ? ` -- ${turn.game_date_end}` : ""}`);
  if (turn.summary) lines.push(`**Summary:** ${turn.summary}`);
  lines.push("");

  // Segments
  const segments = db.prepare(
    "SELECT segment_order, segment_type, content FROM turn_segments WHERE turn_id = ? ORDER BY segment_order"
  ).all(turn.id) as SegmentRow[];

  if (segments.length > 0) {
    lines.push("## Segments", "");
    for (const s of segments) {
      lines.push(`### [${s.segment_type}] (segment ${s.segment_order})`);
      // Truncate very long segments to avoid overwhelming the LLM
      lines.push(truncate(s.content, 1000));
      lines.push("");
    }
  }

  // Entities mentioned in this turn
  const entities = db.prepare(`
    SELECT e.canonical_name, e.entity_type, COUNT(*) AS mention_count
    FROM entity_mentions m
    JOIN entity_entities e ON m.entity_id = e.id
    WHERE m.turn_id = ?
    GROUP BY e.id
    ORDER BY mention_count DESC
  `).all(turn.id) as MentionedEntity[];

  if (entities.length > 0) {
    lines.push("## Entities Mentioned", "");
    lines.push("| Entity | Type | Mentions |", "|---|---|---|");
    for (const e of entities) {
      lines.push(`| ${e.canonical_name} | ${e.entity_type} | ${e.mention_count} |`);
    }
  }

  return lines.join("\n");
}
