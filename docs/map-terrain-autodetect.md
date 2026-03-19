# Map — Auto-detect terrain from image

## Purpose

When the GM uploads a background image for a map, automatically classify each
hex or square cell into a terrain type based on the dominant pixel color of
that region. This eliminates manual terrain painting for maps derived from
real-world or hand-drawn cartography.

---

## Pipeline

```
Image file
    │
    ▼
dart:ui decode → RGBA byte buffer (W × H × 4)
    │
    ▼
For each cell (q, r):
  1. Compute cell center in image pixel space
       cx_px = (center_x / canvas_w) * image_w
       cy_px = (center_y / canvas_h) * image_h
  2. Sample pixels within radius r_px = cellSize_px * 0.45
       (circle approximation — iterate bounding box, skip outside circle)
  3. Average sampled R, G, B → convert to HSV
  4. Classify HSV → terrain type  (see rules below)
    │
    ▼
Preview dialog: grid of TerrainChips (color + name) before committing
    │  [Confirm]
    ▼
Bulk upsert all cells → map_cells table
```

---

## Color → terrain classification (HSV)

Evaluated in priority order (first match wins).

| Terrain    | Hue range | Sat range | Val range | Notes |
|------------|-----------|-----------|-----------|-------|
| `glacier`  | any       | < 0.12    | > 0.88    | Near-white |
| `sea`      | 200–240°  | > 0.40    | any       | Deep blue |
| `coast`    | 175–215°  | 0.15–0.50 | any       | Light cyan-blue |
| `tundra`   | 165–200°  | < 0.35    | any       | Muted cyan |
| `forest`   | 90–155°   | > 0.35    | < 0.55    | Dark green |
| `swamp`    | 58–95°    | < 0.35    | < 0.45    | Murky green |
| `plain`    | 70–125°   | 0.15–0.65 | > 0.45    | Light green / meadow |
| `desert`   | 35–70°    | > 0.35    | > 0.50    | Yellow / ochre |
| `hills`    | 22–52°    | 0.18–0.58 | 0.28–0.68 | Warm brown-green |
| `mountain` | 0–35°     | < 0.25    | 0.20–0.70 | Grey-brown |
| `ruins`    | fallback  | —         | —         | Anything else |

> **Why HSV?** RGB euclidean distance is misleading for perceptual similarity.
> HSV separates color identity (hue) from brightness/saturation, making
> thresholds intuitive and easy to tune.

---

## Preview dialog

Before applying, the GM sees a compact grid matching the map layout:

- Each cell rendered as a small colored square (terrain palette color)
- Tooltip on hover: terrain name + HSV values
- "Apply all" button → bulk upsert
- "Cancel" → no changes

This gives the GM a chance to review before committing ~300 DB writes.

---

## Implementation files

| File | Role |
|---|---|
| `gui/lib/screens/map/terrain_detector.dart` | Core logic: image decode, pixel sampling, HSV classification |
| `gui/lib/screens/map/widgets/terrain_preview_dialog.dart` | Preview dialog + apply |
| `gui/lib/screens/map/map_screen.dart` | "Auto-detect" button in `_CanvasToolbar` |

---

## Limitations & future work

- **Blended pixels** (e.g. forest/mountain border) will be classified by
  majority — expected and acceptable.
- **Custom color schemes** — the thresholds assume standard cartographic
  conventions. If Arthur uses non-standard map colors, the thresholds need
  manual tuning (expose as settings later).
- **Performance** — sampling all pixels for a 20×15 hex grid (~300 cells)
  on a 2000×1500 image runs in < 1s on desktop. No async needed.
- **Manual override** — the cell editor panel always allows terrain override
  after auto-detect.
