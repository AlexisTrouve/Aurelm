"""Test script for turn page generators."""

import sqlite3
import sys
from pathlib import Path

from generate import get_connection
from turn_page_generator import generate_turn_index, generate_turn_page

def test_turn_pages():
    """Test generating individual turn pages."""
    # Use absolute path to pipeline database
    db_path = Path("C:/Users/alexi/Documents/projects/Aurelm/pipeline/aurelm.db")

    if not db_path.exists():
        print(f"ERROR: Database not found at {db_path}")
        sys.exit(1)

    conn = get_connection(str(db_path))

    # Get first civilization
    civ = conn.execute("SELECT * FROM civ_civilizations LIMIT 1").fetchone()
    if not civ:
        print("ERROR: No civilizations found in database")
        sys.exit(1)

    print(f"Testing with civilization: {civ['name']}")

    # Generate turn index
    print("\n--- Generating turn index ---")
    index_content = generate_turn_index(conn, civ["id"], civ["name"])
    print(f"Generated {len(index_content)} characters")
    print(index_content[:500])

    # Get first turn
    turn = conn.execute(
        "SELECT * FROM turn_turns WHERE civ_id = ? ORDER BY turn_number LIMIT 1",
        (civ["id"],)
    ).fetchone()

    if not turn:
        print("ERROR: No turns found")
        sys.exit(1)

    # Generate turn page
    print(f"\n--- Generating turn page for Tour {turn['turn_number']} ---")
    page_content = generate_turn_page(conn, turn["id"], civ["name"], civ["player_name"])
    print(f"Generated {len(page_content)} characters")
    # Print first 800 chars, replacing emojis with [emoji]
    preview = page_content[:800].encode('ascii', 'ignore').decode('ascii')
    print(preview)

    conn.close()
    print("\n[OK] All tests passed!")

if __name__ == "__main__":
    test_turn_pages()
