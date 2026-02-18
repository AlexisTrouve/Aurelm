import type Database from "better-sqlite3";

interface TurnTechRow {
  turn_number: number;
  technologies: string | null;
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

const TECH_CATEGORIES: Record<string, string[]> = {
  "Outils de chasse": ["gourdin", "pieux", "pieu", "arc", "fleche", "lance", "harpon", "chasseur"],
  "Outils de peche": ["filet", "ligne", "hamecon", "peche", "nasse", "poisson"],
  "Agriculture": ["semence", "irrigation", "culture", "plantation", "recolte", "agriculture", "champ"],
  "Artisanat": ["tissage", "poterie", "vannerie", "tannage", "artisan", "metier"],
  "Construction": ["cabane", "palissade", "maison", "construction", "batiment", "architecture"],
  "Navigation": ["radeau", "barque", "bateau", "pirogue", "navigation", "voile"],
  "Feu et lumiere": ["feu", "flambeau", "braise", "torche", "foyer", "fumage"],
  "Musique et rituel": ["rhombe", "pipeau", "tambour", "chant", "rituel", "musique", "voix", "presage"],
  "Materiaux": ["argile", "pierre", "roche", "os", "bois", "pigment"],
};

function categorizeTech(techName: string): string {
  const lower = techName.toLowerCase();
  for (const [cat, keywords] of Object.entries(TECH_CATEGORIES)) {
    if (keywords.some((kw) => lower.includes(kw))) {
      return cat;
    }
  }
  return "Autre";
}

export function getTechTree(
  db: Database.Database,
  civId: number,
  civName: string,
  category: string | undefined
): string {
  const rows = db
    .prepare(
      `SELECT turn_number, technologies FROM turn_turns
       WHERE civ_id = ? AND technologies IS NOT NULL AND technologies != '[]'
       ORDER BY turn_number`
    )
    .all(civId) as TurnTechRow[];

  if (rows.length === 0) {
    return `No technologies found for ${civName}.`;
  }

  // Build flat list
  const allTechs: Array<{ name: string; turn: number; category: string }> = [];
  for (const row of rows) {
    const techs = parseJsonList(row.technologies);
    for (const t of techs) {
      allTechs.push({ name: t, turn: row.turn_number, category: categorizeTech(t) });
    }
  }

  // Filter by category if requested
  let filtered = allTechs;
  if (category) {
    const catLower = category.toLowerCase();
    filtered = allTechs.filter((t) => t.category.toLowerCase().includes(catLower));
    if (filtered.length === 0) {
      const available = [...new Set(allTechs.map((t) => t.category))].sort();
      return `No technologies in category '${category}'. Available: ${available.join(", ")}`;
    }
  }

  // Group by category
  const byCat: Record<string, Array<{ name: string; turn: number }>> = {};
  for (const t of filtered) {
    (byCat[t.category] ??= []).push({ name: t.name, turn: t.turn });
  }

  const lines: string[] = [`# Tech Tree -- ${civName}`, ""];

  // Summary
  const firstTurn = Math.min(...filtered.map((t) => t.turn));
  const lastTurn = Math.max(...filtered.map((t) => t.turn));
  lines.push(`**${filtered.length} technologies** acquired from Turn ${firstTurn} to Turn ${lastTurn}`);
  lines.push(`**Categories:** ${Object.keys(byCat).sort().join(", ")}`);
  lines.push("");

  // By category
  for (const cat of Object.keys(byCat).sort()) {
    const techs = byCat[cat].sort((a, b) => a.turn - b.turn);
    lines.push(`## ${cat} (${techs.length})`, "");
    for (const t of techs) {
      lines.push(`- **${t.name}** (Tour ${t.turn})`);
    }
    lines.push("");
  }

  // Timeline
  lines.push("## Timeline", "");
  const byTurn: Record<number, string[]> = {};
  for (const t of filtered.sort((a, b) => a.turn - b.turn)) {
    (byTurn[t.turn] ??= []).push(t.name);
  }
  for (const turnNum of Object.keys(byTurn).map(Number).sort((a, b) => a - b)) {
    lines.push(`**Tour ${turnNum}** -> ${byTurn[turnNum].join(", ")}`);
  }
  lines.push("");

  return lines.join("\n");
}
