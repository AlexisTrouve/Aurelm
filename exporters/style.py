"""Export styling — the single configuration seam for all exporters.

WHAT: An ExportStyle dataclass holding every visual/structural choice the
exporters make: entity-type colours, relation-type colours, background, and the
font used for rendering (CJK-capable by default).

WHY: The wishlist requires "zero hardcoded FR text / colours" inside the export
modules. Centralising styling here means a future domain profile (P2) or a
per-customer config can restyle output (e.g. a novel's palette, a Chinese font)
by building a different ExportStyle — no exporter code changes. The defaults
below reproduce Aurelm's Flutter ego-graph look so civ exports match the app.

COLOUR SOURCES (kept in sync with the Flutter app on purpose):
- entity_type -> colour: gui/lib/core/theme/app_colors.dart (Material 400 shades)
- relation_type -> colour: gui/lib/screens/graph/widgets/ego_painter.dart
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field

# --- Default palettes -------------------------------------------------------
# QUOI: mapping type -> couleur hex, repris 1:1 de l'app Flutter pour que les
# exports civ ressemblent au graphe in-app. POURQUOI defaults et pas hardcode
# inline: un customer peut fournir sa propre palette via ExportStyle(entity_colors=...).

DEFAULT_ENTITY_COLORS: dict[str, str] = {
    "person": "#42A5F5",        # blue 400
    "place": "#66BB6A",         # green 400
    "technology": "#FFCA28",    # amber 400
    "institution": "#AB47BC",   # purple 400
    "resource": "#8D6E63",      # brown 400
    "creature": "#EF5350",      # red 400
    "event": "#26C6DA",         # cyan 400
    "civilization": "#FF7043",  # deep orange 400
    "caste": "#7E57C2",         # deep purple 400
    "belief": "#29B6F6",        # light blue 400
}

DEFAULT_RELATION_COLORS: dict[str, str] = {
    "allied_with": "#4CAF50",   # green
    "enemy_of": "#F44336",      # red
    "trades_with": "#FFC107",   # amber
    "worships": "#9C27B0",      # purple
    "controls": "#2196F3",      # blue
    "member_of": "#2196F3",     # blue
    "part_of": "#2196F3",       # blue
    "produces": "#FF9800",      # orange
    "located_in": "#009688",    # teal
    # created_by has no explicit colour in the app -> falls back to default grey
}

DEFAULT_FALLBACK_COLOR = "#9E9E9E"  # grey — unknown type

# QUOI: fonts candidates, cherchees dans l'ordre. POURQUOI CJK d'abord: le
# customer #1 (roman) est en chinois; une police latine afficherait des tofus.
# COMMENT: on prend le premier fichier existant; sinon None => defaut matplotlib.
_CJK_FONT_CANDIDATES = (
    "NotoSansSC-VF.ttf",   # Noto Sans Simplified Chinese (variable) — best coverage
    "simhei.ttf",          # SimHei — reliable static CJK
    "msyh.ttc",            # Microsoft YaHei
    "simsun.ttc",          # SimSun
    "Deng.ttf",            # DengXian
)
_WINDOWS_FONTS_DIR = r"C:\Windows\Fonts"


def _resolve_cjk_font() -> str | None:
    """Return an absolute path to a CJK-capable TTF/TTC, or None if none found.

    WHY: we want Chinese/Japanese glyphs to render in the image export without
    bundling a font file in the repo. On the target machine (Windows) Noto SC
    and SimHei ship with the OS. On other OSes we return None and matplotlib
    uses its default (latin) font — acceptable for latin-only corpora.
    """
    for name in _CJK_FONT_CANDIDATES:
        path = os.path.join(_WINDOWS_FONTS_DIR, name)
        if os.path.isfile(path):
            return path
    return None


@dataclass
class ExportStyle:
    """All visual + structural knobs for the exporters.

    Build the default (civ-matching) style with ExportStyle(); override any
    field for a custom look, e.g. ExportStyle(background="#111111").
    """

    entity_colors: dict[str, str] = field(default_factory=lambda: dict(DEFAULT_ENTITY_COLORS))
    relation_colors: dict[str, str] = field(default_factory=lambda: dict(DEFAULT_RELATION_COLORS))
    fallback_color: str = DEFAULT_FALLBACK_COLOR
    background: str = "#FFFFFF"          # clean light paper — good default for embedding
    # font_path=None triggers auto CJK resolution at render time; pass a path to force one.
    font_path: str | None = None

    def entity_color(self, entity_type: str) -> str:
        """Colour for an entity type, falling back to grey for unknown types."""
        return self.entity_colors.get(entity_type, self.fallback_color)

    def relation_color(self, relation_type: str) -> str:
        """Colour for a relation type, falling back to grey for unknown types."""
        return self.relation_colors.get(relation_type, self.fallback_color)

    def resolve_font_path(self) -> str | None:
        """Explicit font_path if set, else best available CJK font, else None."""
        if self.font_path:
            return self.font_path
        return _resolve_cjk_font()
