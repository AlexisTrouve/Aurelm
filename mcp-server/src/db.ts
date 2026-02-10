import Database from "better-sqlite3";

let db: Database.Database | null = null;

/**
 * Get or create the singleton database connection.
 * Reads AURELM_DB_PATH from environment. Read-only mode.
 */
export function getDb(): Database.Database {
  if (db) return db;

  const dbPath = process.env.AURELM_DB_PATH;
  if (!dbPath) {
    throw new Error(
      "AURELM_DB_PATH environment variable is not set. " +
      "Set it to the path of your Aurelm SQLite database."
    );
  }

  db = new Database(dbPath, { readonly: true });
  db.pragma("foreign_keys = ON");
  return db;
}

/**
 * Close the database connection (for clean shutdown).
 */
export function closeDb(): void {
  if (db) {
    db.close();
    db = null;
  }
}
