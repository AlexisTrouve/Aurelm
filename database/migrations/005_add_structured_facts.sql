-- Add structured facts fields to turn_turns table
-- Migration 005: Structured facts extraction

-- JSON array of {type: 'youtube'|'image', url: string, title?: string}
ALTER TABLE turn_turns ADD COLUMN media_links TEXT;

-- JSON array of strings (tools, techniques discovered)
ALTER TABLE turn_turns ADD COLUMN technologies TEXT;

-- JSON array of strings (resources mentioned)
ALTER TABLE turn_turns ADD COLUMN resources TEXT;

-- JSON array of strings (beliefs, rituals, social systems)
ALTER TABLE turn_turns ADD COLUMN beliefs TEXT;

-- JSON array of strings (places, topography, environment)
ALTER TABLE turn_turns ADD COLUMN geography TEXT;

-- JSON array of strings (choices offered by GM)
ALTER TABLE turn_turns ADD COLUMN choices_proposed TEXT;

-- Note: choices_made already exists in schema
