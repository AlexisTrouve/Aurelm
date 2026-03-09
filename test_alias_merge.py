"""Quick test: apply the new store_aliases merge logic to existing aliases in a DB copy."""
import shutil
import sqlite3
import sys
import os

# Run from pipeline/ dir
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "pipeline"))

from pipeline.alias_resolver import store_aliases, ConfirmedAlias

DB_SRC = "../pipeline/aurelm_v22_2_2.db"
DB_TEST = "../pipeline/aurelm_alias_merge_test.db"

# Copy DB
shutil.copy2(DB_SRC, DB_TEST)
print(f"Copied {DB_SRC} -> {DB_TEST}\n")

# Apply pending migrations on the copy
conn_tmp = sqlite3.connect(DB_TEST)
for migration_sql in [
    "ALTER TABLE entity_entities ADD COLUMN tags TEXT",
]:
    try:
        conn_tmp.execute(migration_sql)
        print(f"  Applied: {migration_sql[:50]}")
    except Exception:
        pass  # already applied
conn_tmp.commit()
conn_tmp.close()
print()

# Read current state
conn = sqlite3.connect(DB_TEST)
conn.row_factory = sqlite3.Row

before_active = conn.execute("SELECT COUNT(*) FROM entity_entities WHERE is_active=1").fetchone()[0]
before_mentions = conn.execute("SELECT COUNT(*) FROM entity_mentions").fetchone()[0]
before_aliases = conn.execute("SELECT COUNT(*) FROM entity_aliases").fetchone()[0]

print(f"BEFORE: {before_active} active entities, {before_mentions} mentions, {before_aliases} aliases")
print()

# Reconstruct ConfirmedAlias objects from existing entity_aliases + entity_entities
# Primary = entity_id in aliases table, Secondary = entity with alias_name as canonical_name
aliases_to_apply: list[ConfirmedAlias] = []
skipped = 0

rows = conn.execute("""
    SELECT a.entity_id as pid, ep.canonical_name as pname,
           es.id as sid, es.canonical_name as sname
    FROM entity_aliases a
    JOIN entity_entities ep ON ep.id = a.entity_id
    JOIN entity_entities es ON es.canonical_name = a.alias
                            AND es.civ_id = ep.civ_id
    WHERE es.is_active = 1
""").fetchall()

conn.close()

for row in rows:
    aliases_to_apply.append(ConfirmedAlias(
        primary_entity_id=row["pid"],
        primary_name=row["pname"],
        alias_entity_id=row["sid"],
        alias_name=row["sname"],
        confidence="high",
        reasoning="retroactive merge from existing aliases",
    ))
    print(f"  Will merge: '{row['sname']}' (id={row['sid']}) -> '{row['pname']}' (id={row['pid']})")

print(f"\nFound {len(aliases_to_apply)} entity pairs to merge ({skipped} aliases skipped — no matching entity row)\n")

if not aliases_to_apply:
    print("Nothing to merge — aliases already have no matching active entity rows, or are name-only aliases.")
    sys.exit(0)

# Apply merge
stored = store_aliases(DB_TEST, aliases_to_apply)
print(f"\nstore_aliases applied {stored} merges")

# After state
conn = sqlite3.connect(DB_TEST)
after_active = conn.execute("SELECT COUNT(*) FROM entity_entities WHERE is_active=1").fetchone()[0]
after_inactive = conn.execute("SELECT COUNT(*) FROM entity_entities WHERE is_active=0").fetchone()[0]
after_mentions = conn.execute("SELECT COUNT(*) FROM entity_mentions").fetchone()[0]

print(f"\nAFTER:  {after_active} active entities ({after_inactive} deactivated), {after_mentions} mentions")
print(f"        Entities merged away: {before_active - after_active}")
print(f"        Mentions are all still there: {after_mentions == before_mentions}")

# Verify no orphan mentions (pointing to inactive entities)
orphan_mentions = conn.execute("""
    SELECT COUNT(*) FROM entity_mentions m
    JOIN entity_entities e ON e.id = m.entity_id
    WHERE e.is_active = 0
""").fetchone()[0]
print(f"        Orphan mentions (pointing to inactive entity): {orphan_mentions}  (should be 0)")

# Show a sample merged entity with its accumulated mentions
print("\nSample: mention counts on merged primaries")
for row in conn.execute("""
    SELECT e.canonical_name, COUNT(m.id) as cnt, e.tags
    FROM entity_entities e
    JOIN entity_mentions m ON m.entity_id = e.id
    WHERE e.id IN (SELECT DISTINCT entity_id FROM entity_aliases)
    GROUP BY e.id ORDER BY cnt DESC LIMIT 8
""").fetchall():
    print(f"  {row[0]}: {row[1]} mentions, tags={row[2]}")

conn.close()
print("\nDone. Test DB left at:", DB_TEST)
