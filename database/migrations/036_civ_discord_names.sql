-- Store Discord display names alongside channel ID so we never show raw IDs
ALTER TABLE civ_civilizations ADD COLUMN discord_guild_name TEXT;
ALTER TABLE civ_civilizations ADD COLUMN discord_channel_name TEXT;
