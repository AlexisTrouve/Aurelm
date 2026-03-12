-- Migration 017: Link sessions to their database path
-- Sessions are scoped to a specific game database so switching DBs
-- shows only the sessions belonging to that game.

ALTER TABLE chat_sessions ADD COLUMN db_path TEXT;
CREATE INDEX IF NOT EXISTS idx_chat_sessions_db_path ON chat_sessions(db_path);
