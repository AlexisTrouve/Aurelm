import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { z } from "zod";

const server = new McpServer({
  name: "aurelm",
  version: "0.1.0",
});

// --- Tool: getCivState ---
server.tool(
  "getCivState",
  "Get the current state of a civilization: entities, recent turns, key stats",
  {
    civName: z.string().describe("Name of the civilization"),
  },
  async ({ civName }) => {
    // TODO: Query SQLite for civilization state
    return {
      content: [
        {
          type: "text" as const,
          text: `[stub] State of civilization: ${civName}`,
        },
      ],
    };
  }
);

// --- Tool: searchLore ---
server.tool(
  "searchLore",
  "Search established lore across all civilizations or a specific one",
  {
    query: z.string().describe("Search query (natural language or keyword)"),
    civName: z.string().optional().describe("Filter to a specific civilization"),
    entityType: z
      .string()
      .optional()
      .describe("Filter by entity type: person, place, technology, institution"),
  },
  async ({ query, civName, entityType }) => {
    // TODO: Full-text search in SQLite + wiki markdown
    return {
      content: [
        {
          type: "text" as const,
          text: `[stub] Lore search: "${query}" (civ: ${civName ?? "all"}, type: ${entityType ?? "all"})`,
        },
      ],
    };
  }
);

// --- Tool: sanityCheck ---
server.tool(
  "sanityCheck",
  "Verify if a statement is consistent with established lore. Returns contradictions if any.",
  {
    statement: z.string().describe("The statement to verify against established lore"),
    civName: z.string().optional().describe("Civilization context for the check"),
  },
  async ({ statement, civName }) => {
    // TODO: Compare statement against entity DB and turn history
    return {
      content: [
        {
          type: "text" as const,
          text: `[stub] Sanity check: "${statement}" (civ: ${civName ?? "global"})`,
        },
      ],
    };
  }
);

// --- Tool: timeline ---
server.tool(
  "timeline",
  "Get a chronological timeline of events for a civilization or globally",
  {
    civName: z.string().optional().describe("Civilization name, or omit for global timeline"),
    limit: z.number().optional().default(20).describe("Max number of events to return"),
  },
  async ({ civName, limit }) => {
    // TODO: Query turn_turns ordered by game date
    return {
      content: [
        {
          type: "text" as const,
          text: `[stub] Timeline for ${civName ?? "all civilizations"} (limit: ${limit})`,
        },
      ],
    };
  }
);

// --- Tool: compareCivs ---
server.tool(
  "compareCivs",
  "Compare two or more civilizations side-by-side on specified aspects",
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
    // TODO: Aggregate data per civ and format comparison
    return {
      content: [
        {
          type: "text" as const,
          text: `[stub] Comparing: ${civNames.join(" vs ")} on ${aspects?.join(", ") ?? "all aspects"}`,
        },
      ],
    };
  }
);

// --- Start server ---
async function main() {
  const transport = new StdioServerTransport();
  await server.connect(transport);
  console.error("Aurelm MCP server running on stdio");
}

main().catch((error) => {
  console.error("Fatal error:", error);
  process.exit(1);
});
