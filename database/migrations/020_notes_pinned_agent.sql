-- Migration 020: add pinned flag and note_type to notes
-- pinned = 1 means the note is always shown (even in compact tool output)
-- note_type: 'gm' (default, GM annotation), 'agent' (injected into agent system prompt)

ALTER TABLE notes ADD COLUMN pinned INTEGER NOT NULL DEFAULT 0;
ALTER TABLE notes ADD COLUMN note_type TEXT NOT NULL DEFAULT 'gm';
