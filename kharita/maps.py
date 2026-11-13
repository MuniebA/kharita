"""kh.Map: layers, basemap and legend, shown in a notebook or exported to one HTML file."""

import warnings
from dataclasses import replace
from pathlib import Path

from kharita import basemaps as kb
from kharita.adapter import build
from kharita.errors import KharitaWarning
from kharita.legend import (
    LEGEND_OPTIONS,
    frame_card,
    height_block,
    legend_block,
    legend_panel,
    size_block,
    width_block,
)

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
# Below this CIE76 distance a class colour reads as the basemap ground
GROUND_DELTA = 6.0

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

    def __init__(self, basemap: str | None = None, height: int | str = 500, title=None,
                 subtitle=None, source=None):
        if basemap is not None and basemap not in BASEMAPS:
            raise ValueError(f"basemap must be one of {', '.join(BASEMAPS)}, got '{basemap}'.")
        self.basemap = basemap
        self.theme: str | None = None
        self.relief: str | None = None
        self.buildings: str | None = None
        self.labels: bool | None = None
        self.glow = False
        self.elements: dict = {}
        self.data_labels: list[dict] = []
        self.height = height
        self.title, self.subtitle, self.source = title, subtitle, source
        self.layers: list = []
        self.bounds: list = []
        self._blocks: list[tuple] = []
        self._lonboard = None

    def add(self, gdf, style: str, legend: dict | None = None, colors: dict | None = None,
            order: list | None = None) -> "Map":
        """Add a GeoDataFrame drawn with a style; colors and order fix category colours."""
        options = dict(legend or {})
        unknown = set(options) - LEGEND_OPTIONS
        if unknown:
            raise ValueError(f"Unknown legend option {sorted(unknown)}; use "
                             f"{', '.join(sorted(LEGEND_OPTIONS))}.")
        layers, b = build(gdf, style, colors=colors, order=order)
        self.layers.extend(layers)
        self.bounds.append(b)
        spec = b.spec
        if self.basemap is None and spec.basemap is not None:
            self.basemap = spec.basemap
        for name in MAP_SETTINGS:
            if getattr(self, name) is None and getattr(spec, name) is not None:
                setattr(self, name, getattr(spec, name))
        self.glow = self.glow or spec.glow
        for name, value in spec.elements.items():
            self.elements.setdefault(name, value)
        if spec.label_by is not None:
            self.data_labels.extend(_label_collections(gdf, spec))
        self._check_basemap()
        scale = b.fill_scale or b.stroke_scale
        keys = (b.elevation, b.radius, b.width)
        if spec.legend and (scale is not None or any(k is not None for k in keys)):
            if scale is not None:
                # Build once now so a bad fmt, labels or style fails at add(), not at display
                legend_block(scale, **options)
            self._blocks.append((spec.legend_position or "br", b, options))
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
        asked += [f"{n}-" for n in self.elements]
        asked += ["label-[...]"] if self.data_labels else []
        if asked and not self.themed:
            raise ValueError(f"{', '.join(asked)} need a kharita basemap (paper, midnight, mono, "
                             f"neon, muted or terrain), not basemap-{self.basemap_name}.")

    @property
    def dark(self) -> bool:
        return kb.is_dark(self.basemap_name)

    def _check_ground(self) -> None:
        # Warn when a class colour almost matches the theme's ground, so it would vanish
        from kharita.catalog import delta_e

        if not self.themed:
            return
        theme, _ = kb.resolve(self.basemap_name)
        if kb.get_theme(theme).imagery:
            return
        ground = self.elements.get("land")
        ground = kb.css_color(ground) if ground else kb.get_theme(theme).background
        if not ground.startswith("#"):
            return
        for b in self.bounds:
            scale = b.fill_scale or b.stroke_scale
            if scale is None:
                continue
            # A diverging scale's neutral middle is meant to sit close to the ground
            middle = scale.k // 2 if scale.scheme.startswith("diverging") else None
            close = [lab for i, (c, lab) in enumerate(zip(scale.colors, scale.labels,
                                                         strict=False))
                     if i != middle and delta_e(c, ground) < GROUND_DELTA]
            if close:
                warnings.warn(f"The colour for {close[0]!r} in [{scale.label}] is almost the "
                              f"basemap's ground colour, so those features may vanish; try "
                              "another ramp or a darker land- colour.", KharitaWarning,
                              stacklevel=4)

    def _basemap(self):
        # Lonboard basemap, and the label layer kharita layers sit under, if any
        from lonboard.basemap import MaplibreBasemap

        name = self.basemap_name
        if name == "none":
            return None, None
        if name in kb.HOSTED:
            return MaplibreBasemap(style=kb.HOSTED[name]), None
        theme, alias_relief = kb.resolve(name)
        shown = kb.get_theme(theme).labels if self.labels is None else self.labels
        under = kb.FIRST_LABEL if shown else f"{kb.DATA_LABEL}-0" if self.data_labels else None
        bm = kb.basemap(theme, labels=self.labels, relief=self.relief or alias_relief,
                        buildings=self.buildings or "flat", elements=self.elements,
                        data_labels=self.data_labels,
                        mode="interleaved" if under else "overlaid")
        return bm, under

    @property
    def legend_position(self) -> str:
        return self._blocks[0][0] if self._blocks else "br"

    def legend_html(self) -> str:
        """The legend card for every layer that has one, or an empty string."""
        blocks = []
        for _, b, opts in self._blocks:
            scale = b.fill_scale or b.stroke_scale
            if scale is not None:
                blocks.append(legend_block(scale, dark=self.dark, **opts))
            if b.elevation is not None:
                expr = b.spec.extrude_by
                same = scale is not None and str(expr) == str(b.spec.fill_by or b.spec.stroke_by)
                label = opts.get("title") if scale is None and opts.get("title") else str(expr)
                blocks.append(height_block(label, b.elevation_top, b.elevation_max,
                                           fmt=opts.get("fmt") if same or scale is None else None,
                                           dark=self.dark))
            if b.radius is not None:
                blocks.append(size_block(str(b.spec.size_by), b.radius_top, b.radius_max,
                                         dark=self.dark))
            if b.width is not None:
                blocks.append(width_block(str(b.spec.width_by), b.width_top, b.width_max,
                                          dark=self.dark))
        return legend_panel(blocks, dark=self.dark) if blocks else ""

    def frame_html(self) -> str:
        """The title card, or an empty string when no title, subtitle or source is set."""
        return frame_card(self.title, self.subtitle, self.source, dark=self.dark)

    def _panels(self) -> dict[str, str]:
        # HTML per corner: the frame top left, the legend in its corner, stacked when they meet
        found: dict[str, list[str]] = {}
        if frame := self.frame_html():
            found["tl"] = [frame]
        if legend := self.legend_html():
            found.setdefault(self.legend_position, []).append(legend)
        stack = '<div style="display:flex;flex-direction:column;gap:8px;align-items:flex-start">'
        return {c: parts[0] if len(parts) == 1 else stack + "".join(parts) + "</div>"
                for c, parts in found.items()}

    @property
    def lonboard(self):
        """The underlying Lonboard Map, built on first use."""
        if self._lonboard is None:
            from lonboard import Map as LonboardMap

            if not self.layers:
                raise ValueError("The map has no layers; call add() first.")
            tooltip = any(b.spec.tooltip for b in self.bounds)
            self._check_ground()
            bm, under = self._basemap()
            for lyr in self.layers:
                # Interleaved layers draw below the first label so names stay on top
                lyr.before_id = under
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
        panels = self._panels()
        if not panels:
            return m
        rules, cards = [], []
        for corner, html in panels.items():
            valign, halign, margin = NOTEBOOK_CORNERS[corner]
            rules.append(f".kh-overlay-{corner}{{z-index:10;pointer-events:auto;"
                         f"align-self:{valign};justify-self:{halign};margin:{margin}}}")
            card = w.HTML(html, layout=w.Layout(grid_area="1 / 1 / 2 / 2", width="auto"))
            card.add_class("kh-overlay")
            card.add_class(f"kh-overlay-{corner}")
            cards.append(card)
        css = w.HTML(f"<style>{''.join(rules)}</style>")
        m.layout = w.Layout(grid_area="1 / 1 / 2 / 2")
        height = f"{self.height}px" if isinstance(self.height, int) else self.height
        grid = w.GridBox([m, *cards], layout=w.Layout(grid_template_columns="1fr",
                                                       grid_template_rows=height, width="100%"))
        return w.VBox([css, grid])

    def _ipython_display_(self) -> None:
        from IPython.display import display

        display(self.widget())

    def to_html(self, path: str | Path | None = None, title: str | None = None) -> str:
        """A single HTML page with the map filling the window, title and legend in their corners."""
        m = self.lonboard
        previous = m.height
        m.height = "100vh"
        try:
            page = m.to_html(title=title or self.title or "kharita map")
        finally:
            m.height = previous
        css = "body{margin:0}"
        divs = ""
        for corner, html in self._panels().items():
            css += f".kh-fixed-{corner}{{position:fixed;z-index:1000;{EXPORT_CORNERS[corner]}}}"
            divs += f'<div class="kh-fixed kh-fixed-{corner}">{html}</div>'
        page = page.replace("</body>", f"<style>{css}</style>{divs}</body>", 1)
        if path is not None:
            Path(path).write_text(page, encoding="utf-8")
        return page


LABEL_LIMIT = 5000


def _label_text(values) -> list:
    # Label strings: numbers with thousands separators, missing values dropped as None
    import pandas as pd

    from kharita.classify import fmt_number

    s = pd.Series(values)
    if pd.api.types.is_numeric_dtype(s) and not pd.api.types.is_bool_dtype(s):
        # Each label on its own: 1,200 and 50.5, never 1,200.0
        return [None if pd.isna(v) else fmt_number(float(v), 0 if float(v).is_integer() else 1)
                for v in s]
    return [None if pd.isna(v) else str(v) for v in s]


def _label_collections(gdf, spec) -> list[dict]:
    # GeoJSON for label-[...]: polygons at an inner point, points beside the symbol, lines along
    import json

    import shapely

    sub = gdf[[spec.label_by, gdf.geometry.name]].copy()
    if sub.crs is not None and not sub.crs.equals(4326):
        sub = sub.to_crs(4326)
    texts = _label_text(sub[spec.label_by].to_numpy())
    geoms = sub.geometry.to_numpy()
    groups: dict[str, list] = {"line": [], "beside": [], "point": []}
    for text, geom in zip(texts, geoms, strict=True):
        if text is None or geom is None or geom.is_empty:
            continue
        kind = geom.geom_type
        if kind in ("LineString", "MultiLineString"):
            groups["line"].append((text, geom))
        elif kind in ("Point", "MultiPoint"):
            groups["beside"].append((text, geom))
        else:
            groups["point"].append((text, geom.representative_point()))
    total = sum(len(v) for v in groups.values())
    if total > LABEL_LIMIT:
        warnings.warn(f"label-[{spec.label_by}] adds {total:,} labels; the map hides overlaps, "
                      "but the page grows large. Label a subset instead.", KharitaWarning,
                      stacklevel=4)
    out = []
    for placement, items in groups.items():
        if not items:
            continue
        shapes = shapely.set_precision([g for _, g in items], 1e-5)
        features = [{"type": "Feature", "properties": {"t": text},
                     "geometry": json.loads(shapely.to_geojson(g))}
                    for (text, _), g in zip(items, shapes, strict=True)]
        out.append({"placement": placement,
                    "geojson": {"type": "FeatureCollection", "features": features}})
    return out


def map(gdf, style: str, legend: dict | None = None, basemap: str | None = None,  # noqa: A001
        height: int | str = 500, title=None, subtitle=None, source=None,
        colors: dict | None = None, order: list | None = None) -> Map:
    """One GeoDataFrame, one style, one map; title, subtitle and source draw the title card."""
    return Map(basemap=basemap, height=height, title=title, subtitle=subtitle,
               source=source).add(gdf, style, legend=legend, colors=colors, order=order)


def legend(gdf, style: str, dark: bool = False, colors: dict | None = None,
           order: list | None = None, **options) -> str:
    """The legend HTML for a style on its own, for use with your own Lonboard map."""
    from kharita.binder import bind

    b = bind(gdf, style, colors=colors, order=order)
    scale = b.fill_scale or b.stroke_scale
    if scale is None:
        return ""
    return legend_panel([legend_block(scale, dark=dark, **options)], dark=dark)


def link_views(*maps) -> None:
    """Pan and zoom the maps together: moving one moves the rest (needs a running kernel)."""
    views = [m.lonboard for m in maps]
    busy = []

    def follow(change, source):
        # The guard stops the maps echoing each other's moves back and forth
        if busy:
            return
        busy.append(True)
        try:
            for other in views:
                if other is not source and other.view_state != change["new"]:
                    other.view_state = change["new"]
        finally:
            busy.clear()

    for view in views:
        view.observe(lambda change, view=view: follow(change, view), names="view_state")
    for other in views[1:]:
        other.view_state = views[0].view_state


def compare(*maps: "Map", link: bool = True):
    """Two or more kharita maps side by side; with link, they pan and zoom together."""
    import ipywidgets as w

    if len(maps) < 2:
        raise ValueError("kh.compare needs two or more maps, such as kh.compare(m1, m2).")
    for m in maps:
        if not isinstance(m, Map):
            raise TypeError("kh.compare takes kh.Map or kh.map(...) results, got "
                            f"{type(m).__name__}.")
    if link:
        link_views(*maps)
    return w.GridBox([m.widget() for m in maps],
                     layout=w.Layout(grid_template_columns=f"repeat({len(maps)}, minmax(0, 1fr))",
                                     grid_gap="8px", width="100%"))
