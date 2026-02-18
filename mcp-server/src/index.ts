import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { z } from "zod";
import { getDb, closeDb } from "./db.js";
import { resolveCivName, textResult, errorResult } from "./helpers.js";
import { listCivs } from "./tools/listCivs.js";
import { getCivState } from "./tools/getCivState.js";
import { searchLore } from "./tools/searchLore.js";
import { sanityCheck } from "./tools/sanityCheck.js";
import { getTimeline } from "./tools/timeline.js";
import { compareCivs } from "./tools/compareCivs.js";
import { getEntityDetail } from "./tools/getEntityDetail.js";
import { getTurnDetail } from "./tools/getTurnDetail.js";
import { searchTurnContent } from "./tools/searchTurnContent.js";
import { getStructuredFacts } from "./tools/getStructuredFacts.js";
import { getChoiceHistory } from "./tools/getChoiceHistory.js";
import { exploreRelations } from "./tools/exploreRelations.js";
import { filterTimeline } from "./tools/filterTimeline.js";
import { entityActivity } from "./tools/entityActivity.js";
import { getTechTree } from "./tools/getTechTree.js";

const server = new McpServer({
  name: "aurelm",
  version: "0.3.0",
});

// --- Tool: listCivs ---
server.tool(
  "listCivs",
  "List all civilizations with basic stats (turns, entities). Use this first to discover available civilizations.",
  {},
  async () => {
    try {
      return textResult(listCivs(getDb()));
    } catch (e) {
      console.error("listCivs error:", e);
      return errorResult(`Error: ${e instanceof Error ? e.message : String(e)}`);
    }
  }
);

// --- Tool: getCivState ---
server.tool(
  "getCivState",
  "Get the current state of a civilization: entity breakdown, key entities, recent turns",
  {
    civName: z.string().describe("Name of the civilization (partial match supported)"),
  },
  async ({ civName }) => {
    try {
      const db = getDb();
      const resolved = resolveCivName(db, civName);
      if ("error" in resolved) return errorResult(resolved.error);
      return textResult(getCivState(db, resolved.civ.id, resolved.civ.name));
    } catch (e) {
      console.error("getCivState error:", e);
      return errorResult(`Error: ${e instanceof Error ? e.message : String(e)}`);
    }
  }
);

// --- Tool: searchLore ---
server.tool(
  "searchLore",
  "Search established lore: entities by name/description/alias, with mention contexts",
  {
    query: z.string().describe("Search query (entity name, keyword, or alias)"),
    civName: z.string().optional().describe("Filter to a specific civilization"),
    entityType: z
      .string()
      .optional()
      .describe("Filter by entity type: person, place, technology, institution, resource, creature, event"),
  },
  async ({ query, civName, entityType }) => {
    try {
      const db = getDb();
      let civId: number | null = null;
      if (civName) {
        const resolved = resolveCivName(db, civName);
        if ("error" in resolved) return errorResult(resolved.error);
        civId = resolved.civ.id;
      }
      return textResult(searchLore(db, query, civId, entityType));
    } catch (e) {
      console.error("searchLore error:", e);
      return errorResult(`Error: ${e instanceof Error ? e.message : String(e)}`);
    }
  }
);

// --- Tool: sanityCheck ---
server.tool(
  "sanityCheck",
  "Verify a statement against established lore. Returns matched entities, entity inventory, and recent turns for reasoning.",
  {
    statement: z.string().describe("The statement to verify against established lore"),
    civName: z.string().optional().describe("Civilization context for the check"),
  },
  async ({ statement, civName }) => {
    try {
      const db = getDb();
      let civId: number | null = null;
      let resolvedName: string | null = null;
      if (civName) {
        const resolved = resolveCivName(db, civName);
        if ("error" in resolved) return errorResult(resolved.error);
        civId = resolved.civ.id;
        resolvedName = resolved.civ.name;
      }
      return textResult(sanityCheck(db, statement, civId, resolvedName));
    } catch (e) {
      console.error("sanityCheck error:", e);
      return errorResult(`Error: ${e instanceof Error ? e.message : String(e)}`);
    }
  }
);

// --- Tool: timeline ---
server.tool(
  "timeline",
  "Get a chronological timeline of turns, with entity counts per turn",
  {
    civName: z.string().optional().describe("Civilization name, or omit for global timeline"),
    limit: z.number().min(1).max(100).optional().default(20).describe("Max number of turns to return (1-100)"),
  },
  async ({ civName, limit }) => {
    try {
      const db = getDb();
      let civId: number | null = null;
      if (civName) {
        const resolved = resolveCivName(db, civName);
        if ("error" in resolved) return errorResult(resolved.error);
        civId = resolved.civ.id;
      }
      return textResult(getTimeline(db, civId, limit));
    } catch (e) {
      console.error("timeline error:", e);
      return errorResult(`Error: ${e instanceof Error ? e.message : String(e)}`);
    }
  }
);

// --- Tool: compareCivs ---
server.tool(
  "compareCivs",
  "Compare two or more civilizations side-by-side. Supports aspect filtering: military, technology, politics, economy, culture.",
  {
    civNames: z
      .array(z.string())
      .min(2)
      .describe("Names of civilizations to compare"),
    aspects: z
      .array(z.string())
      .optional()
      .describe("Aspects to compare: military, technology, politics, economy, culture"),
  },
  async ({ civNames, aspects }) => {
    try {
      const db = getDb();
      const resolvedCivs = [];
      for (const name of civNames) {
        const resolved = resolveCivName(db, name);
        if ("error" in resolved) return errorResult(resolved.error);
        resolvedCivs.push(resolved.civ);
      }
      return textResult(compareCivs(db, resolvedCivs, aspects));
    } catch (e) {
      console.error("compareCivs error:", e);
      return errorResult(`Error: ${e instanceof Error ? e.message : String(e)}`);
    }
  }
);

// --- Tool: getEntityDetail ---
server.tool(
  "getEntityDetail",
  "Deep dive on an entity: metadata, aliases, relations, up to 20 mentions with context",
  {
    entityName: z.string().describe("Entity name to look up (partial match supported)"),
    civName: z.string().optional().describe("Scope to a specific civilization"),
  },
  async ({ entityName, civName }) => {
    try {
      const db = getDb();
      let civId: number | null = null;
      if (civName) {
        const resolved = resolveCivName(db, civName);
        if ("error" in resolved) return errorResult(resolved.error);
        civId = resolved.civ.id;
      }
      return textResult(getEntityDetail(db, entityName, civId));
    } catch (e) {
      console.error("getEntityDetail error:", e);
      return errorResult(`Error: ${e instanceof Error ? e.message : String(e)}`);
    }
  }
);

// --- Tool: getTurnDetail ---
server.tool(
  "getTurnDetail",
  "Get full turn content: all segments with types, entities mentioned, summary",
  {
    turnNumber: z.number().describe("Turn number"),
    civName: z.string().describe("Civilization name (required to identify the turn)"),
  },
  async ({ turnNumber, civName }) => {
    try {
      const db = getDb();
      const resolved = resolveCivName(db, civName);
      if ("error" in resolved) return errorResult(resolved.error);
      return textResult(getTurnDetail(db, turnNumber, resolved.civ.id, resolved.civ.name));
    } catch (e) {
      console.error("getTurnDetail error:", e);
      return errorResult(`Error: ${e instanceof Error ? e.message : String(e)}`);
    }
  }
);

// --- Tool: searchTurnContent ---
server.tool(
  "searchTurnContent",
  "Full-text search on turn segment content. Finds narrative events not captured as entities.",
  {
    query: z.string().describe("Search text (LIKE match on segment content)"),
    civName: z.string().optional().describe("Filter to a specific civilization"),
    segmentType: z
      .string()
      .optional()
      .describe("Filter by segment type: narrative, choice, consequence, ooc, description"),
  },
  async ({ query, civName, segmentType }) => {
    try {
      const db = getDb();
      let civId: number | null = null;
      if (civName) {
        const resolved = resolveCivName(db, civName);
        if ("error" in resolved) return errorResult(resolved.error);
        civId = resolved.civ.id;
      }
      return textResult(searchTurnContent(db, query, civId, segmentType));
    } catch (e) {
      console.error("searchTurnContent error:", e);
      return errorResult(`Error: ${e instanceof Error ? e.message : String(e)}`);
    }
  }
);

// --- Tool: getStructuredFacts ---
server.tool(
  "getStructuredFacts",
  "Get structured facts (technologies, resources, beliefs, geography) per turn for a civilization",
  {
    civName: z.string().describe("Civilization name (partial match supported)"),
    factType: z.string().optional().describe("Filter: technologies, resources, beliefs, geography"),
    turnNumber: z.number().optional().describe("Filter to a specific turn number"),
  },
  async ({ civName, factType, turnNumber }) => {
    try {
      const db = getDb();
      const resolved = resolveCivName(db, civName);
      if ("error" in resolved) return errorResult(resolved.error);
      return textResult(getStructuredFacts(db, resolved.civ.id, resolved.civ.name, factType, turnNumber));
    } catch (e) {
      console.error("getStructuredFacts error:", e);
      return errorResult(`Error: ${e instanceof Error ? e.message : String(e)}`);
    }
  }
);

// --- Tool: getChoiceHistory ---
server.tool(
  "getChoiceHistory",
  "Get the history of choices proposed by GM and decisions made by the player",
  {
    civName: z.string().describe("Civilization name (partial match supported)"),
    turnNumber: z.number().optional().describe("Filter to a specific turn number"),
  },
  async ({ civName, turnNumber }) => {
    try {
      const db = getDb();
      const resolved = resolveCivName(db, civName);
      if ("error" in resolved) return errorResult(resolved.error);
      return textResult(getChoiceHistory(db, resolved.civ.id, resolved.civ.name, turnNumber));
    } catch (e) {
      console.error("getChoiceHistory error:", e);
      return errorResult(`Error: ${e instanceof Error ? e.message : String(e)}`);
    }
  }
);

// --- Tool: exploreRelations ---
server.tool(
  "exploreRelations",
  "Explore the relation graph of an entity (controls, membership, alliances, etc.) with configurable depth",
  {
    entityName: z.string().describe("Entity name to explore (partial match supported)"),
    civName: z.string().optional().describe("Scope to a specific civilization"),
    depth: z.number().min(1).max(3).optional().default(1).describe("Graph traversal depth (1-3)"),
  },
  async ({ entityName, civName, depth }) => {
    try {
      const db = getDb();
      let civId: number | null = null;
      if (civName) {
        const resolved = resolveCivName(db, civName);
        if ("error" in resolved) return errorResult(resolved.error);
        civId = resolved.civ.id;
      }
      return textResult(exploreRelations(db, entityName, civId, depth));
    } catch (e) {
      console.error("exploreRelations error:", e);
      return errorResult(`Error: ${e instanceof Error ? e.message : String(e)}`);
    }
  }
);

// --- Tool: filterTimeline ---
server.tool(
  "filterTimeline",
  "Get a filtered timeline by turn type, turn range, civilization, or entity mentioned",
  {
    civName: z.string().optional().describe("Filter to a specific civilization"),
    turnType: z.string().optional().describe("Filter by turn type: standard, event, first_contact, crisis"),
    fromTurn: z.number().optional().describe("Start turn number (inclusive)"),
    toTurn: z.number().optional().describe("End turn number (inclusive)"),
    entityName: z.string().optional().describe("Filter turns mentioning this entity"),
  },
  async ({ civName, turnType, fromTurn, toTurn, entityName }) => {
    try {
      const db = getDb();
      let civId: number | null = null;
      if (civName) {
        const resolved = resolveCivName(db, civName);
        if ("error" in resolved) return errorResult(resolved.error);
        civId = resolved.civ.id;
      }
      return textResult(filterTimeline(db, civId, turnType, fromTurn, toTurn, entityName));
    } catch (e) {
      console.error("filterTimeline error:", e);
      return errorResult(`Error: ${e instanceof Error ? e.message : String(e)}`);
    }
  }
);

// --- Tool: entityActivity ---
server.tool(
  "entityActivity",
  "Get the temporal activity profile of an entity: mention counts per turn, peak, sparkline, recent context",
  {
    entityName: z.string().describe("Entity name (partial match supported)"),
    civName: z.string().optional().describe("Scope to a specific civilization"),
  },
  async ({ entityName, civName }) => {
    try {
      const db = getDb();
      let civId: number | null = null;
      if (civName) {
        const resolved = resolveCivName(db, civName);
        if ("error" in resolved) return errorResult(resolved.error);
        civId = resolved.civ.id;
      }
      return textResult(entityActivity(db, entityName, civId));
    } catch (e) {
      console.error("entityActivity error:", e);
      return errorResult(`Error: ${e instanceof Error ? e.message : String(e)}`);
    }
  }
);

// --- Tool: getTechTree ---
server.tool(
  "getTechTree",
  "Full technology tree for a civilization, organized by category (hunting, fishing, construction, etc.) with timeline.",
  {
    civName: z.string().describe("Civilization name"),
    category: z.string().optional().describe("Filter by category (optional): Outils de chasse, Outils de peche, Construction, Navigation, etc."),
  },
  async ({ civName, category }) => {
    try {
      const db = getDb();
      const resolved = resolveCivName(db, civName);
      if ("error" in resolved) return errorResult(resolved.error);
      return textResult(getTechTree(db, resolved.civ.id, resolved.civ.name, category));
    } catch (e) {
      console.error("getTechTree error:", e);
      return errorResult(`Error: ${e instanceof Error ? e.message : String(e)}`);
    }
  }
);

// --- Start server ---
async function main() {
  const transport = new StdioServerTransport();
  await server.connect(transport);
  console.error("Aurelm MCP server running on stdio (15 tools registered)");
}

// Clean shutdown
process.on("SIGINT", () => {
  closeDb();
  process.exit(0);
});

process.on("SIGTERM", () => {
  closeDb();
  process.exit(0);
});

main().catch((error) => {
  console.error("Fatal error:", error);
  closeDb();
  process.exit(1);
});
