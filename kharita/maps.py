"""kh.Map: layers, basemap and legend, shown in a notebook or exported to one HTML file."""

import warnings
from dataclasses import replace
from pathlib import Path

from kharita import basemaps as kb
from kharita.adapter import build
from kharita.errors import KharitaWarning
from kharita.legend import LEGEND_OPTIONS, legend_block, legend_panel

BASEMAPS = kb.BASEMAP_NAMES
EXTRUDED_VIEW = {"pitch": 45, "bearing": -10}
# Additive blending in luma.gl v9 names; the design spike confirmed these, not WebGL constants
GLOW = {
    "blend": True,
    "blendColorOperation": "add",
    "blendColorSrcFactor": "src-alpha",
    "blendColorDstFactor": "one",
    "blendAlphaOperation": "add",
    "blendAlphaSrcFactor": "one",
    "blendAlphaDstFactor": "one-minus-src-alpha",
    "depthCompare": "always",
}
# Map-wide settings a layer's style can set; the first layer to set one wins
MAP_SETTINGS = ("theme", "relief", "buildings", "labels")

# Fixed corners for exported pages; bottom corners clear attribution, scale bar and buttons
EXPORT_CORNERS = {
    "tl": "top:12px;left:12px",
    "tr": "top:12px;right:56px",
    "bl": "bottom:48px;left:12px",
    "br": "bottom:72px;right:12px",
}
# Grid alignment for the notebook overlay
NOTEBOOK_CORNERS = {
    "tl": ("start", "start", "12px 0 0 12px"),
    "tr": ("start", "end", "12px 56px 0 0"),
    "bl": ("end", "start", "0 0 48px 12px"),
    "br": ("end", "end", "0 12px 72px 0"),
}


class Map:
    """A kharita map: add layers with style strings, then show it or export it."""

    def __init__(self, basemap: str | None = None, height: int | str = 500):
        if basemap is not None and basemap not in BASEMAPS:
            raise ValueError(f"basemap must be one of {', '.join(BASEMAPS)}, got '{basemap}'.")
        self.basemap = basemap
        self.theme: str | None = None
        self.relief: str | None = None
        self.buildings: str | None = None
        self.labels: bool | None = None
        self.glow = False
        self.height = height
        self.layers: list = []
        self.bounds: list = []
        self._blocks: list[tuple[str, str]] = []
        self._lonboard = None

    def add(self, gdf, style: str, legend: dict | None = None) -> "Map":
        """Add a GeoDataFrame drawn with a style; legend takes title, fmt, labels and note."""
        options = dict(legend or {})
        unknown = set(options) - LEGEND_OPTIONS
        if unknown:
            raise ValueError(f"Unknown legend option {sorted(unknown)}; use "
                             f"{', '.join(sorted(LEGEND_OPTIONS))}.")
        layers, b = build(gdf, style)
        self.layers.extend(layers)
        self.bounds.append(b)
        spec = b.spec
        if self.basemap is None and spec.basemap is not None:
            self.basemap = spec.basemap
        for name in MAP_SETTINGS:
            if getattr(self, name) is None and getattr(spec, name) is not None:
                setattr(self, name, getattr(spec, name))
        self.glow = self.glow or spec.glow
        self._check_basemap()
        scale = b.fill_scale or b.stroke_scale
        if scale is not None and spec.legend:
            # Build once now so a bad fmt or labels fails at add(), not at display
            legend_block(scale, **options)
            self._blocks.append((spec.legend_position or "br", (scale, options)))
        self._lonboard = None
        return self

    @property
    def basemap_name(self) -> str:
        """The basemap drawn: set directly, from a theme, or paper when relief or buildings ask."""
        if self.basemap is not None:
            return self.basemap
        if self.theme is not None:
            return self.theme
        return "paper" if self.relief or self.buildings else "light"

    @property
    def themed(self) -> bool:
        # True when kharita builds the basemap style itself
        return self.basemap_name not in kb.HOSTED and self.basemap_name != "none"

    def _check_basemap(self) -> None:
        # relief, buildings and labels-none only work on a basemap kharita builds
        asked = [n for n in ("relief", "buildings") if getattr(self, n)]
        asked += ["labels"] if self.labels is False else []
        if asked and not self.themed:
            raise ValueError(f"{', '.join(asked)} need a kharita basemap (paper, midnight, mono, "
                             f"neon, muted or terrain), not basemap-{self.basemap_name}.")

    @property
    def dark(self) -> bool:
        return self.basemap_name in kb.DARK_BASEMAPS

    def _basemap(self):
        # Lonboard basemap, and whether kharita layers sit under its labels
        from lonboard.basemap import MaplibreBasemap

        name = self.basemap_name
        if name == "none":
            return None, False
        if name in kb.HOSTED:
            return MaplibreBasemap(style=kb.HOSTED[name]), False
        theme, alias_relief = kb.resolve(name)
        shown = kb.get_theme(theme).labels if self.labels is None else self.labels
        bm = kb.basemap(theme, labels=self.labels, relief=self.relief or alias_relief,
                        buildings=self.buildings or "flat",
                        mode="interleaved" if shown else "overlaid")
        return bm, shown

    @property
    def legend_position(self) -> str:
        return self._blocks[0][0] if self._blocks else "br"

    def legend_html(self) -> str:
        """The legend card for every layer that has one, or an empty string."""
        blocks = [legend_block(scale, dark=self.dark, **opts) for _, (scale, opts) in self._blocks]
        return legend_panel(blocks, dark=self.dark) if blocks else ""

    @property
    def lonboard(self):
        """The underlying Lonboard Map, built on first use."""
        if self._lonboard is None:
            from lonboard import Map as LonboardMap

            if not self.layers:
                raise ValueError("The map has no layers; call add() first.")
            tooltip = any(b.spec.tooltip for b in self.bounds)
            bm, under_labels = self._basemap()
            for lyr in self.layers:
                # Interleaved layers draw below the first label so place names stay on top
                lyr.before_id = kb.FIRST_LABEL if under_labels else None
            extra = {}
            if self.glow:
                if not self.dark and self.basemap_name != "none":
                    warnings.warn("glow adds colours together, so on a light basemap most "
                                  "features turn white; try basemap-dark, midnight or neon.",
                                  KharitaWarning, stacklevel=3)
                extra["parameters"] = GLOW
            m = LonboardMap(self.layers, basemap=bm, height=self.height, show_tooltip=tooltip,
                            show_side_panel=False, **extra)
            raised = any(b.elevation is not None for b in self.bounds)
            if raised or self.buildings == "3d":
                m.view_state = replace(m.view_state, **EXTRUDED_VIEW)
            self._lonboard = m
        return self._lonboard

    def widget(self):
        """The notebook widget: the map with the legend floating over one corner."""
        import ipywidgets as w

        m = self.lonboard
        legend = self.legend_html()
        if not legend:
            return m
        valign, halign, margin = NOTEBOOK_CORNERS[self.legend_position]
        css = w.HTML(
            "<style>.kh-overlay{z-index:10;pointer-events:auto;"
            f"align-self:{valign};justify-self:{halign};margin:{margin}}}</style>"
        )
        m.layout = w.Layout(grid_area="1 / 1 / 2 / 2")
        card = w.HTML(legend, layout=w.Layout(grid_area="1 / 1 / 2 / 2", width="auto"))
        card.add_class("kh-overlay")
        height = f"{self.height}px" if isinstance(self.height, int) else self.height
        grid = w.GridBox([m, card], layout=w.Layout(grid_template_columns="1fr",
                                                     grid_template_rows=height, width="100%"))
        return w.VBox([css, grid])

    def _ipython_display_(self) -> None:
        from IPython.display import display

        display(self.widget())

    def to_html(self, path: str | Path | None = None, title: str = "kharita map") -> str:
        """A single HTML page with the map filling the window and the legend in its corner."""
        m = self.lonboard
        previous = m.height
        m.height = "100vh"
        try:
            page = m.to_html(title=title)
        finally:
            m.height = previous
        legend = self.legend_html()
        css = "<style>body{margin:0}</style>"
        if legend:
            corner = EXPORT_CORNERS[self.legend_position]
            css += f"<style>.kh-fixed{{position:fixed;z-index:1000;{corner}}}</style>"
            legend = f'<div class="kh-fixed">{legend}</div>'
        page = page.replace("</body>", f"{css}{legend}</body>", 1)
        if path is not None:
            Path(path).write_text(page, encoding="utf-8")
        return page


def map(gdf, style: str, legend: dict | None = None, basemap: str | None = None,  # noqa: A001
        height: int | str = 500) -> Map:
    """One GeoDataFrame, one style, one map."""
    return Map(basemap=basemap, height=height).add(gdf, style, legend=legend)


def legend(gdf, style: str, dark: bool = False, **options) -> str:
    """The legend HTML for a style on its own, for use with your own Lonboard map."""
    from kharita.binder import bind

    b = bind(gdf, style)
    scale = b.fill_scale or b.stroke_scale
    if scale is None:
        return ""
    return legend_panel([legend_block(scale, dark=dark, **options)], dark=dark)
