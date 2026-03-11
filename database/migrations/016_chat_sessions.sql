-- Migration 016: Conversation sessions management
-- Persistent named sessions with tags and message history
-- Supports multiple concurrent sessions, compression phases, and tagging

CREATE TABLE IF NOT EXISTS chat_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    uuid TEXT NOT NULL UNIQUE,                -- Session ID for API reference
    name TEXT NOT NULL,                       -- User-given session name
    archived INTEGER NOT NULL DEFAULT 0,      -- 0=active, 1=archived
    message_count INTEGER NOT NULL DEFAULT 0, -- For quick UI list previews
    compressed_message_count INTEGER NOT NULL DEFAULT 0,  -- Compress blocks (phase 1)
    resume_count INTEGER NOT NULL DEFAULT 0,  -- Resume blocks (phase 2, max 3)
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    last_message_at TEXT                      -- For sorting by recency
);

-- Session tags: free tags + auto civ tag
CREATE TABLE IF NOT EXISTS chat_session_tags (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER NOT NULL REFERENCES chat_sessions(id) ON DELETE CASCADE,
    tag TEXT NOT NULL,
    tag_type TEXT NOT NULL DEFAULT 'free',  -- 'free' or 'civ' (auto-generated from lore context)
    UNIQUE(session_id, tag)
);

-- Full conversation history
CREATE TABLE IF NOT EXISTS chat_messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER NOT NULL REFERENCES chat_sessions(id) ON DELETE CASCADE,
    message_order INTEGER NOT NULL,            -- Chronological order within session
    role TEXT NOT NULL,                        -- 'user' or 'assistant'
    content TEXT NOT NULL,
    message_type TEXT NOT NULL DEFAULT 'text', -- 'text', 'compress', 'resume', 'thinking'
    tool_calls TEXT,                           -- JSON array of {name, input, result, tool_use_id}
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(session_id, message_order)
);

CREATE INDEX IF NOT EXISTS idx_chat_sessions_archived ON chat_sessions(archived);
CREATE INDEX IF NOT EXISTS idx_chat_sessions_updated ON chat_sessions(updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_chat_messages_session ON chat_messages(session_id, message_order);
CREATE INDEX IF NOT EXISTS idx_chat_session_tags_session ON chat_session_tags(session_id);
