"""Regression: entity dedup must not crash when merged entities share an alias.

_periodic_entity_dedup moves the secondary entity's aliases onto the primary.
If both already carry the same alias (e.g. two "Cendre" entities each seeded/
extracted with the ZH alias 阿灰), the (entity_id, alias) UNIQUE constraint fired
and aborted the whole incremental run — which silently broke per-chapter history
and relation accumulation. The fix is UPDATE OR IGNORE.
"""

from __future__ import annotations

from pipeline.db import init_db, run_migrations, get_connection
from pipeline.runner import _periodic_entity_dedup


def test_dedup_survives_shared_alias(tmp_path):
    db = str(tmp_path / "dedup.db")
    init_db(db)
    run_migrations(db)
    conn = get_connection(db)
    conn.execute("INSERT INTO civ_civilizations (id, name) VALUES (1, 'R')")
    # Two DISTINCT canonical names that normalize to the same key (accents/case)
    # -> merge candidates. (UNIQUE(canonical_name, civ_id) forbids identical names.)
    conn.executemany(
        "INSERT INTO entity_entities (id, canonical_name, entity_type, civ_id, is_active) "
        "VALUES (?, ?, ?, 1, 1)",
        [(1, "Cendre", "person"), (2, "Cendré", "creature")],
    )
    # Both carry the SAME alias -> the merge would violate the UNIQUE constraint.
    conn.executemany(
        "INSERT INTO entity_aliases (entity_id, alias) VALUES (?, ?)",
        [(1, "阿灰"), (2, "阿灰")],
    )
    conn.commit()

    merged = _periodic_entity_dedup(conn, 1)   # must NOT raise

    assert merged == 1
    active = conn.execute(
        "SELECT COUNT(*) FROM entity_entities WHERE is_active = 1 AND canonical_name = 'Cendre'"
    ).fetchone()[0]
    assert active == 1                          # one primary survives, secondary deactivated
