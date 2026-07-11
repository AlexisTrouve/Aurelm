# exporters/ — headless artefact exporters

Standalone, **read-only** exporters that turn any Aurelm SQLite DB into portable
artefacts. They read only the four domain-neutral tables (`entity_entities`,
`entity_aliases`, `entity_mentions`, `entity_relations`) plus `turn_turns`, so
they work on **any** Aurelm DB — the existing civ games *and* future non-civ
corpora (a novel, etc.) — with no knowledge of Discord, castes or MJ/PJ turns.

Like `wiki/`, this is a separate package (no Flutter, no ML stack). The DB is
opened in SQLite `mode=ro`, so an export can never mutate a live game DB.

## Exporters

| kind | output | what |
|------|--------|------|
| `graph` | PNG + SVG | radial ego-graph centred on one entity; nodes coloured by `entity_type`, edges coloured/labelled by `relation_type`; rings by BFS depth; legend. Reproduces the app's ego-graph look. |
| `glossary` | md + json | one entry per entity: `canonical_name`, `description`, `aliases`, active/inactive. |
| `history` | md + json | per-entity chronology: the `history` event log + mentions per turn + first/last seen. |

Every exporter emits both a **machine** (json) and a **human** (md/png/svg)
format so outputs compose (embed in a wiki, a PDF, etc.).

## Install

```bash
pip install -r exporters/requirements.txt   # networkx + matplotlib
```

`matplotlib` renders self-contained images and embeds a CJK-capable font
(auto-detected: Noto Sans SC / SimHei on Windows), so Chinese/Japanese names
render without tofu. SVG text is exported as vector paths (portable everywhere).

## Usage (CLI)

Run from the repo root:

```bash
# Radial ego-graph, persons only, 2 hops, PNG + SVG
python -m exporters graph --db aurelm_clean.db --center "Drazim" \
    --depth 2 --filter entity_type=person --out out/drazim

# Glossary of every place, md + json
python -m exporters glossary --db aurelm_clean.db --type place --out out/gloss

# History of one entity
python -m exporters history --db aurelm_clean.db --entity "Drazim" --out out/hist
```

Shared styling flags: `--font PATH` (force a font), `--background #RRGGBB`.
Center by id instead of name with `--center-id N` / `--entity-id N`.

## Styling / customer profiles

All colours, the font and the background live in `exporters/style.py`
(`ExportStyle`). The defaults reproduce Aurelm's Flutter palette; a customer
profile can pass a different `ExportStyle` to restyle output without touching
exporter code. No French/game text is hardcoded in the exporters.

## Tests

```bash
python -m pytest exporters/tests -q      # 20 tests
```

Tests use a synthetic DB (one node deliberately has a Chinese name), so a CJK
render regression fails a test rather than shipping silently.

## Module map

- `db.py` — read-only SQL helpers → dataclasses (resolves turn-id FKs to turn numbers)
- `models.py` — plain dataclasses (`Entity`, `Relation`, `Mention`, `EgoGraph`, …)
- `style.py` — `ExportStyle` (palettes, font resolution) — the config seam
- `ego_graph.py` — BFS neighbourhood + radial layout (mirrors `ego_painter.dart`)
- `graph_exporter.py` — matplotlib render → PNG/SVG
- `glossary_exporter.py` / `history_exporter.py` — md + json
- `cli.py` / `__main__.py` — `python -m exporters …`
