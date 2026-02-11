import { describe, it, expect, beforeAll, afterAll } from "vitest";
import Database from "better-sqlite3";
import { resolveCivName } from "../helpers.js";
import { listCivs } from "../tools/listCivs.js";
import { getCivState } from "../tools/getCivState.js";
import { searchLore } from "../tools/searchLore.js";
import { sanityCheck } from "../tools/sanityCheck.js";
import { getTimeline } from "../tools/timeline.js";
import { compareCivs } from "../tools/compareCivs.js";
import { getEntityDetail } from "../tools/getEntityDetail.js";
import { getTurnDetail } from "../tools/getTurnDetail.js";
import { searchTurnContent } from "../tools/searchTurnContent.js";

let db: Database.Database;

function seedDb(db: Database.Database) {
  // Create schema
  db.exec(`
    PRAGMA foreign_keys = ON;

    CREATE TABLE civ_civilizations (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      name TEXT NOT NULL UNIQUE,
      player_name TEXT,
      discord_channel_id TEXT,
      created_at TEXT NOT NULL DEFAULT (datetime('now')),
      updated_at TEXT NOT NULL DEFAULT (datetime('now'))
    );

    CREATE TABLE turn_turns (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      civ_id INTEGER NOT NULL REFERENCES civ_civilizations(id),
      turn_number INTEGER NOT NULL,
      title TEXT,
      summary TEXT,
      raw_message_ids TEXT NOT NULL,
      turn_type TEXT NOT NULL DEFAULT 'standard',
      game_date_start TEXT,
      game_date_end TEXT,
      created_at TEXT NOT NULL DEFAULT (datetime('now')),
      processed_at TEXT,
      UNIQUE(civ_id, turn_number)
    );

    CREATE TABLE turn_segments (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      turn_id INTEGER NOT NULL REFERENCES turn_turns(id),
      segment_order INTEGER NOT NULL,
      segment_type TEXT NOT NULL,
      content TEXT NOT NULL,
      UNIQUE(turn_id, segment_order)
    );

    CREATE TABLE entity_entities (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      canonical_name TEXT NOT NULL,
      entity_type TEXT NOT NULL,
      civ_id INTEGER REFERENCES civ_civilizations(id),
      description TEXT,
      history TEXT,
      first_seen_turn INTEGER REFERENCES turn_turns(id),
      last_seen_turn INTEGER REFERENCES turn_turns(id),
      is_active INTEGER NOT NULL DEFAULT 1,
      created_at TEXT NOT NULL DEFAULT (datetime('now')),
      updated_at TEXT NOT NULL DEFAULT (datetime('now')),
      UNIQUE(canonical_name, civ_id)
    );

    CREATE TABLE entity_aliases (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      entity_id INTEGER NOT NULL REFERENCES entity_entities(id) ON DELETE CASCADE,
      alias TEXT NOT NULL,
      UNIQUE(entity_id, alias)
    );

    CREATE TABLE entity_mentions (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      entity_id INTEGER NOT NULL REFERENCES entity_entities(id) ON DELETE CASCADE,
      turn_id INTEGER NOT NULL REFERENCES turn_turns(id),
      segment_id INTEGER REFERENCES turn_segments(id),
      mention_text TEXT NOT NULL,
      context TEXT
    );

    CREATE TABLE entity_relations (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      source_entity_id INTEGER NOT NULL REFERENCES entity_entities(id) ON DELETE CASCADE,
      target_entity_id INTEGER NOT NULL REFERENCES entity_entities(id) ON DELETE CASCADE,
      relation_type TEXT NOT NULL,
      description TEXT,
      turn_id INTEGER REFERENCES turn_turns(id),
      is_active INTEGER NOT NULL DEFAULT 1,
      created_at TEXT NOT NULL DEFAULT (datetime('now'))
    );
  `);

  // Seed data
  db.exec(`
    INSERT INTO civ_civilizations (name, player_name) VALUES
      ('Civilisation de la Confluence', 'Rubanc'),
      ('Cheveux de Sang', 'PlayerB');

    INSERT INTO turn_turns (civ_id, turn_number, title, summary, raw_message_ids, turn_type, game_date_start) VALUES
      (1, 1, 'Fondation', 'Les cinq castes fondent la cite au confluent des deux fleuves.', '[]', 'standard', 'An 1'),
      (1, 2, 'Premier Contact', 'Les eclaireurs rapportent une presence etrangere.', '[]', 'first_contact', 'An 5'),
      (1, 3, 'Decouverte des Ruines', 'Exploration des ruines anciennes revele l argile vivante.', '[]', 'standard', 'An 8'),
      (2, 1, 'Depart Maritime', 'Les Cheveux de Sang prennent la mer pour explorer.', '[]', 'standard', 'An 1');

    INSERT INTO turn_segments (turn_id, segment_order, segment_type, content) VALUES
      (1, 1, 'narrative', 'Au confluent des deux fleuves, cinq castes se reunissent pour fonder une nouvelle civilisation.'),
      (1, 2, 'description', 'Les castes sont: Air, Feu, Eau, Terre, et Ether. Chacune apporte un savoir unique.'),
      (2, 1, 'narrative', 'Des eclaireurs de la caste de l Air rapportent des voiles etrangeres sur la mer.'),
      (2, 2, 'choice', 'Faut-il envoyer une delegation diplomatique ou renforcer les defenses?'),
      (3, 1, 'narrative', 'L expedition vers les ruines anciennes decouvre une substance remarquable: l argile vivante.'),
      (3, 2, 'consequence', 'La technologie de l argile vivante est maintenant disponible.'),
      (4, 1, 'narrative', 'Les Cheveux de Sang construisent des navires et prennent la mer.');

    INSERT INTO entity_entities (canonical_name, entity_type, civ_id, description, first_seen_turn, last_seen_turn) VALUES
      ('Argile Vivante', 'technology', 1, 'Substance qui durcit instantanement au contact de l air', 3, 3),
      ('Caste de l Air', 'institution', 1, 'Une des cinq castes fondatrices', 1, 2),
      ('Caste du Feu', 'institution', 1, 'Une des cinq castes fondatrices', 1, 1),
      ('Ruines Anciennes', 'place', 1, 'Site archeologique pre-civilisation', 3, 3),
      ('Cheveux de Sang', 'institution', 2, 'Civilisation maritime etrangere', 2, 2);

    INSERT INTO entity_aliases (entity_id, alias) VALUES
      (1, 'argile'),
      (1, 'living clay'),
      (2, 'caste air'),
      (5, 'CdS');

    INSERT INTO entity_mentions (entity_id, turn_id, segment_id, mention_text, context) VALUES
      (1, 3, 5, 'argile vivante', 'decouvre une substance remarquable: l argile vivante'),
      (1, 3, 6, 'argile vivante', 'La technologie de l argile vivante est maintenant disponible'),
      (2, 1, 1, 'castes', 'cinq castes se reunissent pour fonder'),
      (2, 2, 3, 'caste de l Air', 'Des eclaireurs de la caste de l Air'),
      (3, 1, 2, 'Feu', 'Les castes sont: Air, Feu, Eau'),
      (4, 3, 5, 'ruines anciennes', 'L expedition vers les ruines anciennes'),
      (5, 2, 3, 'voiles etrangeres', 'des voiles etrangeres sur la mer');

    INSERT INTO entity_relations (source_entity_id, target_entity_id, relation_type, turn_id) VALUES
      (1, 4, 'discovered_at', 3),
      (2, 1, 'member_of', 1);
  `);
}

beforeAll(() => {
  db = new Database(":memory:");
  seedDb(db);
});

afterAll(() => {
  db.close();
});

// --- helpers ---
describe("resolveCivName", () => {
  it("finds exact match", () => {
    const result = resolveCivName(db, "Civilisation de la Confluence");
    expect("civ" in result).toBe(true);
    if ("civ" in result) {
      expect(result.civ.name).toBe("Civilisation de la Confluence");
    }
  });

  it("finds fuzzy match", () => {
    const result = resolveCivName(db, "Confluence");
    expect("civ" in result).toBe(true);
    if ("civ" in result) {
      expect(result.civ.name).toBe("Civilisation de la Confluence");
    }
  });

  it("returns error for unknown civ", () => {
    const result = resolveCivName(db, "Nope");
    expect("error" in result).toBe(true);
    if ("error" in result) {
      expect(result.error).toContain("not found");
      expect(result.error).toContain("Civilisation de la Confluence");
    }
  });
});

// --- listCivs ---
describe("listCivs", () => {
  it("lists all civilizations", () => {
    const result = listCivs(db);
    expect(result).toContain("Civilisation de la Confluence");
    expect(result).toContain("Cheveux de Sang");
    expect(result).toContain("Rubanc");
    expect(result).toContain("2");
  });
});

// --- getCivState ---
describe("getCivState", () => {
  it("returns civ state with entity breakdown", () => {
    const result = getCivState(db, 1, "Civilisation de la Confluence");
    expect(result).toContain("Civilisation de la Confluence");
    expect(result).toContain("technology");
    expect(result).toContain("institution");
    expect(result).toContain("Argile Vivante");
    expect(result).toContain("Turn 3");
  });
});

// --- searchLore ---
describe("searchLore", () => {
  it("finds entities by canonical name", () => {
    const result = searchLore(db, "Argile", null, undefined);
    expect(result).toContain("Argile Vivante");
    expect(result).toContain("technology");
  });

  it("finds entities by alias", () => {
    const result = searchLore(db, "living clay", null, undefined);
    expect(result).toContain("Argile Vivante");
  });

  it("filters by civ", () => {
    const result = searchLore(db, "Caste", 1, undefined);
    expect(result).toContain("Caste de l Air");
    expect(result).not.toContain("Cheveux de Sang");
  });

  it("returns empty message for no match", () => {
    const result = searchLore(db, "zzzzzzzzz", null, undefined);
    expect(result).toContain("No entities found");
  });
});

// --- sanityCheck ---
describe("sanityCheck", () => {
  it("matches entities from statement", () => {
    const result = sanityCheck(
      db,
      "Les Confluents maitrisent l'argile vivante",
      1,
      "Civilisation de la Confluence"
    );
    expect(result).toContain("Argile Vivante");
    expect(result).toContain("Matched Entities");
  });

  it("reports no match for unknown concepts", () => {
    const result = sanityCheck(db, "Le bronze est forge", 1, "Civilisation de la Confluence");
    expect(result).toContain("bronze");
    // Should have entity inventory even if no match
    expect(result).toContain("Entity Inventory");
  });

  it("includes entity inventory for civ", () => {
    const result = sanityCheck(db, "test", 1, "Civilisation de la Confluence");
    expect(result).toContain("Entity Inventory");
    expect(result).toContain("technology");
  });
});

// --- timeline ---
describe("getTimeline", () => {
  it("returns global timeline", () => {
    const result = getTimeline(db, null, 20);
    expect(result).toContain("Civilisation de la Confluence");
    expect(result).toContain("Cheveux de Sang");
    expect(result).toContain("4");
  });

  it("filters by civ", () => {
    const result = getTimeline(db, 1, 20);
    expect(result).toContain("Civilisation de la Confluence");
    expect(result).not.toContain("Depart Maritime");
  });
});

// --- compareCivs ---
describe("compareCivs", () => {
  it("compares two civs", () => {
    const civs = [
      { id: 1, name: "Civilisation de la Confluence", playerName: "Rubanc" },
      { id: 2, name: "Cheveux de Sang", playerName: "PlayerB" },
    ];
    const result = compareCivs(db, civs, undefined);
    expect(result).toContain("Civilisation de la Confluence");
    expect(result).toContain("Cheveux de Sang");
    expect(result).toContain("Comparison");
  });

  it("supports aspect filtering", () => {
    const civs = [
      { id: 1, name: "Civilisation de la Confluence", playerName: "Rubanc" },
      { id: 2, name: "Cheveux de Sang", playerName: "PlayerB" },
    ];
    const result = compareCivs(db, civs, ["technology"]);
    expect(result).toContain("technology");
  });
});

// --- getEntityDetail ---
describe("getEntityDetail", () => {
  it("returns entity details with aliases and mentions", () => {
    const result = getEntityDetail(db, "Argile", null);
    expect(result).toContain("Argile Vivante");
    expect(result).toContain("living clay");
    expect(result).toContain("argile");
    expect(result).toContain("Mentions");
  });

  it("shows relations", () => {
    const result = getEntityDetail(db, "Argile Vivante", null);
    expect(result).toContain("Relations");
    expect(result).toContain("discovered_at");
  });

  it("returns not found for unknown entity", () => {
    const result = getEntityDetail(db, "zzzzzzz", null);
    expect(result).toContain("No entity found");
  });
});

// --- getTurnDetail ---
describe("getTurnDetail", () => {
  it("returns turn detail with segments", () => {
    const result = getTurnDetail(db, 1, 1, "Civilisation de la Confluence");
    expect(result).toContain("Fondation");
    expect(result).toContain("narrative");
    expect(result).toContain("description");
    expect(result).toContain("cinq castes");
  });

  it("returns not found for invalid turn", () => {
    const result = getTurnDetail(db, 99, 1, "Civilisation de la Confluence");
    expect(result).toContain("not found");
    expect(result).toContain("1, 2, 3");
  });
});

// --- searchTurnContent ---
describe("searchTurnContent", () => {
  it("finds segments by content", () => {
    const result = searchTurnContent(db, "argile", null, undefined);
    expect(result).toContain("argile vivante");
  });

  it("filters by segment type", () => {
    const result = searchTurnContent(db, "castes", null, "narrative");
    expect(result).toContain("narrative");
  });

  it("returns empty for no match", () => {
    const result = searchTurnContent(db, "zzzzzzz", null, undefined);
    expect(result).toContain("No segments found");
  });
});
