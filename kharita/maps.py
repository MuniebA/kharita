"""kh.Map: layers, basemap and legend, shown in a notebook or exported to one HTML file."""

from dataclasses import replace
from pathlib import Path

from kharita.adapter import build
from kharita.legend import LEGEND_OPTIONS, legend_block, legend_panel

BASEMAPS = ("light", "dark", "none")
OPENFREEMAP_POSITRON = "https://tiles.openfreemap.org/styles/positron"
EXTRUDED_VIEW = {"pitch": 45, "bearing": -10}

# Fixed corners for exported pages; bottom corners clear the attribution and scale bar
EXPORT_CORNERS = {
    "tl": "top:12px;left:12px",
    "tr": "top:12px;right:56px",
    "bl": "bottom:48px;left:12px",
    "br": "bottom:36px;right:12px",
}
# Grid alignment for the notebook overlay
NOTEBOOK_CORNERS = {
    "tl": ("start", "start", "12px 0 0 12px"),
    "tr": ("start", "end", "12px 56px 0 0"),
    "bl": ("end", "start", "0 0 48px 12px"),
    "br": ("end", "end", "0 12px 36px 0"),
}


def _basemap(name: str):
    # Lonboard basemap object for a kharita basemap name
    from lonboard.basemap import CartoStyle, MaplibreBasemap

    if name == "none":
        return None
    if name == "dark":
        return MaplibreBasemap(style=CartoStyle.DarkMatter)
    return MaplibreBasemap(style=OPENFREEMAP_POSITRON)


class Map:
    """A kharita map: add layers with style strings, then show it or export it."""

    def __init__(self, basemap: str | None = None, height: int | str = 500):
        if basemap is not None and basemap not in BASEMAPS:
            raise ValueError(f"basemap must be one of {', '.join(BASEMAPS)}, got '{basemap}'.")
        self.basemap = basemap
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
        scale = b.fill_scale or b.stroke_scale
        if scale is not None and spec.legend:
            # Build once now so a bad fmt or labels fails at add(), not at display
            legend_block(scale, **options)
            self._blocks.append((spec.legend_position or "br", (scale, options)))
        self._lonboard = None
        return self

    @property
    def dark(self) -> bool:
        return self.basemap == "dark"

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
            m = LonboardMap(self.layers, basemap=_basemap(self.basemap or "light"),
                            height=self.height, show_tooltip=tooltip, show_side_panel=False)
            if any(b.elevation is not None for b in self.bounds):
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
