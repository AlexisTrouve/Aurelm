import type Database from "better-sqlite3";
import { type ResolvedCiv, truncate } from "../helpers.js";

// Map aspects to entity types and segment keywords
const ASPECT_ENTITY_MAP: Record<string, { types: string[]; keywords: string[] }> = {
  military: {
    types: ["person", "creature", "institution"],
    keywords: ["guerre", "militaire", "armee", "soldat", "combat", "arme", "defense", "attaque", "bataille", "guerrier"],
  },
  technology: {
    types: ["technology", "resource"],
    keywords: ["technologie", "technique", "decouverte", "invention", "outil", "savoir", "connaissance", "forge"],
  },
  politics: {
    types: ["institution", "person"],
    keywords: ["politique", "gouvernement", "loi", "chef", "roi", "conseil", "caste", "pouvoir", "alliance", "diplomatie"],
  },
  economy: {
    types: ["resource", "technology", "place"],
    keywords: ["economie", "commerce", "ressource", "echange", "marche", "production", "agriculture", "recolte"],
  },
  culture: {
    types: ["institution", "event", "place"],
    keywords: ["culture", "religion", "rituel", "tradition", "art", "musique", "fete", "ceremonie", "croyance", "mythe"],
  },
};

interface CivData {
  civ: ResolvedCiv;
  turnCount: number;
  entityBreakdown: Record<string, number>;
  topEntities: Array<{ name: string; type: string; mentions: number }>;
  relevantSegments: string[];
}

export function compareCivs(
  db: Database.Database,
  civs: ResolvedCiv[],
  aspects: string[] | undefined
): string {
  const activeAspects = aspects?.filter((a) => a in ASPECT_ENTITY_MAP) ?? Object.keys(ASPECT_ENTITY_MAP);

  // Collect relevant entity types and keywords from all requested aspects
  const relevantTypes = new Set<string>();
  const relevantKeywords: string[] = [];
  for (const aspect of activeAspects) {
    const mapping = ASPECT_ENTITY_MAP[aspect];
    if (mapping) {
      for (const t of mapping.types) relevantTypes.add(t);
      relevantKeywords.push(...mapping.keywords);
    }
  }

  const civData: CivData[] = [];

  for (const civ of civs) {
    const turnCount = (
      db.prepare("SELECT COUNT(*) AS count FROM turn_turns WHERE civ_id = ?").get(civ.id) as { count: number }
    ).count;

    // Entity breakdown (filtered by aspect types if specified)
    const breakdown = db.prepare(
      "SELECT entity_type, COUNT(*) AS count FROM entity_entities WHERE civ_id = ? GROUP BY entity_type ORDER BY count DESC"
    ).all(civ.id) as Array<{ entity_type: string; count: number }>;

    const entityBreakdown: Record<string, number> = {};
    for (const row of breakdown) {
      entityBreakdown[row.entity_type] = row.count;
    }

    // Top entities filtered by relevant types
    let entitySql = `
      SELECT e.canonical_name AS name, e.entity_type AS type,
             (SELECT COUNT(*) FROM entity_mentions m WHERE m.entity_id = e.id) AS mentions
      FROM entity_entities e
      WHERE e.civ_id = ?
    `;
    const entityParams: unknown[] = [civ.id];

    if (aspects && relevantTypes.size > 0) {
      const placeholders = [...relevantTypes].map(() => "?").join(", ");
      entitySql += ` AND e.entity_type IN (${placeholders})`;
      entityParams.push(...relevantTypes);
    }

    entitySql += " ORDER BY mentions DESC LIMIT 10";
    const topEntities = db.prepare(entitySql).all(...entityParams) as Array<{ name: string; type: string; mentions: number }>;

    // Relevant segment snippets (keyword search in segments)
    const relevantSegments: string[] = [];
    if (aspects && relevantKeywords.length > 0) {
      // Search for aspect-related content in turn segments
      for (const keyword of relevantKeywords.slice(0, 5)) {
        const segments = db.prepare(`
          SELECT s.content, t.turn_number
          FROM turn_segments s
          JOIN turn_turns t ON s.turn_id = t.id
          WHERE t.civ_id = ? AND s.content LIKE ?
          ORDER BY t.turn_number DESC
          LIMIT 2
        `).all(civ.id, `%${keyword}%`) as Array<{ content: string; turn_number: number }>;

        for (const seg of segments) {
          relevantSegments.push(`Turn ${seg.turn_number}: ${truncate(seg.content, 150)}`);
        }
        if (relevantSegments.length >= 5) break;
      }
    }

    civData.push({ civ, turnCount, entityBreakdown, topEntities, relevantSegments });
  }

  // Format output
  const lines: string[] = [
    `# Civilization Comparison`,
    "",
    `**Comparing:** ${civs.map((c) => c.name).join(" vs ")}`,
    `**Aspects:** ${activeAspects.join(", ")}`,
    "",
  ];

  // Summary table
  lines.push("## Overview", "");
  const headers = ["Metric", ...civData.map((d) => d.civ.name)];
  lines.push(`| ${headers.join(" | ")} |`);
  lines.push(`| ${headers.map(() => "---").join(" | ")} |`);
  lines.push(`| Turns | ${civData.map((d) => d.turnCount).join(" | ")} |`);

  // Entity counts by type
  const allTypes = new Set<string>();
  for (const d of civData) {
    for (const t of Object.keys(d.entityBreakdown)) allTypes.add(t);
  }
  for (const type of allTypes) {
    lines.push(`| ${type} entities | ${civData.map((d) => d.entityBreakdown[type] ?? 0).join(" | ")} |`);
  }
  lines.push("");

  // Per-civ detail
  for (const data of civData) {
    lines.push(`## ${data.civ.name}`, "");
    if (data.civ.playerName) lines.push(`**Player:** ${data.civ.playerName}`);

    if (data.topEntities.length > 0) {
      lines.push("", "**Key entities:**");
      for (const e of data.topEntities) {
        lines.push(`- ${e.name} (${e.type}, ${e.mentions} mentions)`);
      }
    }

    if (data.relevantSegments.length > 0) {
      lines.push("", "**Relevant excerpts:**");
      for (const seg of data.relevantSegments) {
        lines.push(`> ${seg}`);
      }
    }

    lines.push("");
  }

  return lines.join("\n");
}
