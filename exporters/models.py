"""Plain data models shared by every exporter.

WHAT: Frozen-ish dataclasses that mirror the four domain-neutral Aurelm tables
plus the derived graph structures. They decouple the SQL layer (db.py) from the
rendering layers (glossary/history/graph exporters).

WHY: Passing dataclasses instead of raw sqlite3.Row objects makes the exporter
code readable and testable without a live DB (a test can hand-build an Entity).
No behaviour lives here — these are pure records.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Entity:
    """One row of entity_entities, with history already parsed to a list.

    ``history`` is stored in the DB as a JSON array of strings, each typically
    prefixed ``"Tour N: ..."``. We keep it as a list[str]; the turn number is
    parsed on demand by the history exporter (it is not a structured column).
    """

    id: int
    canonical_name: str
    entity_type: str
    description: str | None = None
    history: list[str] = field(default_factory=list)
    # NOTE: these hold the human TURN NUMBER (already resolved from the DB's
    # turn_turns.id foreign key by db.py), not the internal turn row id.
    first_seen_turn: int | None = None
    last_seen_turn: int | None = None
    is_active: bool = True
    civ_id: int | None = None


@dataclass
class Relation:
    """One row of entity_relations (a directed, typed edge between two entities)."""

    source_id: int
    target_id: int
    relation_type: str
    description: str | None = None
    turn_id: int | None = None
    is_active: bool = True


@dataclass
class Mention:
    """One row of entity_mentions, joined to turn_turns for the human turn number."""

    entity_id: int
    turn_id: int | None
    turn_number: int | None
    mention_text: str | None
    context: str | None


@dataclass
class GraphNode:
    """A node in a laid-out ego-graph.

    ``depth`` is BFS distance from the center (0 = center). ``x``/``y`` are the
    radial-layout coordinates in abstract data units (center at origin), filled
    in by ego_graph.layout_radial().
    """

    id: int
    name: str
    entity_type: str
    depth: int
    x: float = 0.0
    y: float = 0.0


@dataclass
class GraphEdge:
    """An edge in a laid-out ego-graph (undirected for drawing purposes)."""

    source_id: int
    target_id: int
    relation_type: str
    description: str | None = None


@dataclass
class EgoGraph:
    """A center entity plus its neighbourhood, laid out for rendering."""

    center_id: int
    nodes: list[GraphNode] = field(default_factory=list)
    edges: list[GraphEdge] = field(default_factory=list)

    def node(self, node_id: int) -> GraphNode | None:
        """Return the node with the given id, or None."""
        for n in self.nodes:
            if n.id == node_id:
                return n
        return None
