import type Database from "better-sqlite3";

// French stopwords for keyword extraction (sanityCheck)
export const FRENCH_STOPWORDS = new Set([
  "le", "la", "les", "de", "du", "des", "un", "une",
  "et", "ou", "en", "au", "aux", "ce", "ces", "son", "sa", "ses",
  "mon", "ma", "mes", "ton", "ta", "tes", "leur", "leurs",
  "qui", "que", "quoi", "dont", "il", "elle", "ils", "elles",
  "je", "tu", "nous", "vous", "on", "se", "ne", "pas", "plus",
  "est", "sont", "a", "ont", "fait", "ete", "avec", "pour",
  "dans", "par", "sur", "sous", "entre", "vers", "chez",
  "mais", "donc", "car", "ni", "si", "peut", "bien", "tout",
  "cette", "cet", "aussi", "comme", "sans", "tres", "peu",
  "encore", "deja", "toujours", "jamais", "ici", "y",
  "avoir", "etre", "faire", "dire", "pouvoir", "vouloir",
  "meme", "autre", "autres", "chaque", "quelques",
]);

export interface ResolvedCiv {
  id: number;
  name: string;
  playerName: string | null;
}

/**
 * Fuzzy-match a civilization name. Tries exact match first, then LIKE.
 * Returns null with a helpful message listing available civs if not found.
 */
export function resolveCivName(
  db: Database.Database,
  civName: string
): { civ: ResolvedCiv } | { error: string } {
  // Exact match
  const exact = db
    .prepare("SELECT id, name, player_name FROM civ_civilizations WHERE name = ?")
    .get(civName) as { id: number; name: string; player_name: string | null } | undefined;

  if (exact) {
    return { civ: { id: exact.id, name: exact.name, playerName: exact.player_name } };
  }

  // Fuzzy match with LIKE -- check for ambiguity
  const fuzzyAll = db
    .prepare("SELECT id, name, player_name FROM civ_civilizations WHERE name LIKE ?")
    .all(`%${civName}%`) as Array<{ id: number; name: string; player_name: string | null }>;

  if (fuzzyAll.length === 1) {
    const f = fuzzyAll[0];
    return { civ: { id: f.id, name: f.name, playerName: f.player_name } };
  }

  if (fuzzyAll.length > 1) {
    const matches = fuzzyAll.map((c) => c.name).join(", ");
    return {
      error: `Ambiguous civilization name "${civName}". Multiple matches: ${matches}. Please be more specific.`,
    };
  }

  // Not found -- list available civs
  const allCivs = db
    .prepare("SELECT name FROM civ_civilizations ORDER BY name")
    .all() as Array<{ name: string }>;

  const civList = allCivs.map((c) => c.name).join(", ");
  return {
    error: `Civilization "${civName}" not found. Available civilizations: ${civList || "none"}`,
  };
}

/**
 * Format a successful text result for MCP.
 */
export function textResult(text: string) {
  return {
    content: [{ type: "text" as const, text }],
  };
}

/**
 * Format an error/not-found result. Sets isError so MCP clients can distinguish from success.
 * Still returns text (not an MCP protocol error) so the LLM can self-correct.
 */
export function errorResult(text: string) {
  return {
    content: [{ type: "text" as const, text }],
    isError: true,
  };
}

/**
 * Truncate text to a max length, adding "..." if truncated.
 */
export function truncate(text: string | null, maxLen: number = 200): string {
  if (!text) return "(none)";
  if (text.length <= maxLen) return text;
  return text.slice(0, maxLen) + "...";
}
