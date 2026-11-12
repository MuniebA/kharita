"""Turns a style string into a StyleSpec, plus define, explain, validate and help."""

import re
from difflib import get_close_matches

from kharita.errors import BindingError, StyleSyntaxError
from kharita.palette import get_ramp
from kharita.registry import BUILTIN_PRESETS, USER_PRESETS, UTILITIES, Utility
from kharita.spec import DEFAULT_NULL, DEFAULT_NUMERIC, DEFAULT_TEXT, LEGEND_POSITIONS, StyleSpec
from kharita.tokenizer import Token, tokenize

MAX_PRESET_DEPTH = 5
PRESET_NAME = re.compile(r"[a-z][a-z0-9_-]*")


class _Builder:
    # Applies utilities to a StyleSpec and catches the same property being set twice

    def __init__(self, style: str):
        self.style = style
        self.spec = StyleSpec()
        self.token: Token | None = None
        self.from_preset = False
        self.preset_owned: set[str] = set()
        self.group_keys: dict[str, set[str]] = {}

    def set(self, group: str, **values) -> None:
        tok = self.token
        if group in self.spec.origins:
            if group in self.preset_owned and not self.from_preset:
                # An explicit token replaces everything the preset set for this group
                blank = StyleSpec()
                for key in self.group_keys[group]:
                    setattr(self.spec, key, getattr(blank, key))
                self.preset_owned.discard(group)
                self.spec.origins[group] = []
            else:
                first = self.spec.origins[group][0].label
                raise StyleSyntaxError(
                    f"'{tok.label}' conflicts with '{first}'; both set {group.replace('_', ' ')}.",
                    token=tok.shown, position=tok.start, style=self.style,
                )
        for key, value in values.items():
            setattr(self.spec, key, value)
        self.group_keys.setdefault(group, set()).update(values)
        self.spec.origins.setdefault(group, []).append(tok)
        if self.from_preset:
            self.preset_owned.add(group)


def _preset_style(name: str, tok: Token, style: str) -> str:
    # The style string behind a preset name
    if name in USER_PRESETS:
        return USER_PRESETS[name]
    if name in BUILTIN_PRESETS:
        return BUILTIN_PRESETS[name]
    known = list(BUILTIN_PRESETS) + list(USER_PRESETS)
    match = get_close_matches(name, known, n=1)
    if match:
        hint = f" Did you mean 'preset-{match[0]}'?"
    else:
        hint = f" Known presets: {', '.join(known)}."
    raise StyleSyntaxError(f"Unknown preset '{name}'.{hint}", tok.text, tok.start, style)


def _expand(tokens: list[Token], style: str, depth: int = 0) -> tuple[list, list]:
    # Split into preset-sourced tokens and explicit tokens, expanding nested presets
    preset_tokens, explicit = [], []
    for tok in tokens:
        if not tok.text.startswith("preset-"):
            explicit.append(tok)
            continue
        if depth >= MAX_PRESET_DEPTH:
            raise StyleSyntaxError("Presets nest too deeply; check for a loop.",
                                   tok.text, tok.start, style)
        inner = _preset_style(tok.text[len("preset-"):], tok, style)
        # Inner tokens report the position of the preset token in the user's style
        inner_tokens = [Token(t.text, tok.start, via=tok.text) for t in tokenize(inner)]
        nested_presets, nested_explicit = _expand(inner_tokens, style, depth + 1)
        preset_tokens.extend(nested_presets + nested_explicit)
    return preset_tokens, explicit


def _apply(b: _Builder, tok: Token) -> None:
    # Route one token to its utility handler
    prefix, dash, rest = tok.text.partition("-")
    utility = UTILITIES.get(prefix)
    if utility is None or not dash or not rest:
        if utility is not None:
            msg = f"'{tok.text}' needs a value, like '{utility.examples[0]}'."
        else:
            match = get_close_matches(prefix, list(UTILITIES), n=1)
            hint = f" Did you mean '{match[0]}{dash}{rest}'?" if match and dash else ""
            msg = f"Unknown utility '{tok.label}'.{hint} Run kh.help() to list every utility."
        raise StyleSyntaxError(msg, tok.shown, tok.start, b.style)
    b.token = tok
    try:
        utility.handler(b, rest)
    except ValueError as err:
        raise StyleSyntaxError(f"{tok.label}: {err}", tok.shown, tok.start, b.style) from None


def _check(spec: StyleSpec, style: str) -> None:
    # Rules that involve more than one utility
    def fail(group: str, message: str):
        tok = spec.origins[group][0]
        raise StyleSyntaxError(message, tok.shown, tok.start, style)

    if spec.fill_by is not None and spec.stroke_by is not None:
        fail("stroke", "Only one colour can come from data; "
                       "use fill-[...] or stroke-[...], not both.")
    if spec.fill_by is None and spec.stroke_by is None:
        for group in ("ramp", "scheme"):
            if group in spec.origins and not spec.origins[group][0].via:
                fail(group, f"'{spec.origins[group][0].text}' needs a data-bound colour like "
                            "fill-[column] or stroke-[column].")
    if spec.extrude_max is not None and spec.extrude_by is None:
        fail("extrude_max", "extrude-max needs extrude-[column] to scale.")
    if spec.ramp and spec.scheme:
        kind = get_ramp(spec.ramp)["kind"]
        clash = (kind == "categorical" and spec.scheme.kind != "categorical") or (
            spec.scheme.kind == "diverging" and kind != "diverging")
        if clash and spec.from_preset("scheme"):
            # A preset's scheme yields to a ramp the user typed
            spec.scheme = None
            spec.origins.pop("scheme")
            return
        if kind == "categorical" and spec.scheme.kind != "categorical":
            fail("ramp", f"ramp-{spec.ramp} is for categories; "
                         "use scheme-cat or a sequential ramp.")
        if spec.scheme.kind == "diverging" and kind != "diverging":
            fail("ramp", "scheme-div needs a diverging ramp such as ramp-rdbu, "
                         f"not ramp-{spec.ramp}.")


def parse(style: str) -> StyleSpec:
    """Compile a style string to a StyleSpec, raising StyleSyntaxError on any problem."""
    return _parse(style, cross_check=True)


def _parse(style: str, cross_check: bool) -> StyleSpec:
    # Presets skip the cross-checks because their data-bound fill arrives when they are used
    tokens = tokenize(style)
    preset_tokens, explicit = _expand(tokens, style)
    b = _Builder(style)
    b.from_preset = True
    for tok in preset_tokens:
        _apply(b, tok)
    b.from_preset = False
    for tok in explicit:
        _apply(b, tok)
    if cross_check:
        _check(b.spec, style)
    return b.spec


def define(name: str, style: str) -> None:
    """Save a style under a name so it can be used as preset-<name>."""
    if not isinstance(name, str) or not PRESET_NAME.fullmatch(name):
        raise ValueError("Preset names use lowercase letters, digits, '_' and '-', "
                         "starting with a letter.")
    if name in BUILTIN_PRESETS:
        raise ValueError(f"'{name}' is a built-in preset; pick another name.")
    previous = USER_PRESETS.get(name)
    USER_PRESETS[name] = style
    try:
        _parse(style, cross_check=False)
    except Exception:
        if previous is None:
            USER_PRESETS.pop(name)
        else:
            USER_PRESETS[name] = previous
        raise


def validate(style: str, columns=None) -> StyleSpec:
    """Parse a style and, if columns are given, check every referenced column exists."""
    spec = parse(style)
    if columns is not None:
        check_columns(spec, columns)
    return spec


def check_columns(spec: StyleSpec, columns) -> None:
    # Raise BindingError for the first referenced column that is missing
    available = [str(c) for c in columns]
    lower = {c.lower(): c for c in available}
    for col in spec.columns:
        if col in available:
            continue
        if col.lower() in lower:
            hint = f" Did you mean '{lower[col.lower()]}'? Column names are case-sensitive."
        else:
            close = get_close_matches(col, available, n=3)
            hint = f" Closest: {', '.join(close)}." if close else ""
        raise BindingError(f"Column '{col}' is not in the data.{hint}", column=col)


class Explanation(str):
    # Prints cleanly when it is the last line of a notebook cell
    def __repr__(self) -> str:
        return str(self)


def _rgba(c) -> str:
    return f"rgba({c[0]}, {c[1]}, {c[2]}, {c[3]})"


def explain(style: str) -> Explanation:
    """Show what a style compiles to and which token set each part."""
    s = parse(style)
    rows: list[tuple[str, str, str]] = []

    def src(group: str) -> str:
        return ", ".join(t.label for t in s.origins.get(group, [])) or "default"

    data_by = s.fill_by if s.fill_by is not None else s.stroke_by
    if data_by is not None:
        target = "fill" if s.fill_by is not None else "stroke"
        rows.append((target, f"data: {data_by}", src(target)))
        ramp = f"{s.ramp}{' reversed' if s.ramp_reverse else ''}" if s.ramp else (
            f"{DEFAULT_NUMERIC[0]} for numbers, {DEFAULT_TEXT[0]} for text")
        rows.append(("ramp", ramp, src("ramp")))
        default_scheme = "quantiles, 5 classes for numbers; categorical for text"
        scheme = str(s.scheme) if s.scheme else default_scheme
        rows.append(("scheme", scheme, src("scheme")))
        rows.append(("null", _rgba(s.null) if s.null else DEFAULT_NULL, src("null")))
    elif s.fill is not None:
        rows.append(("fill", _rgba(s.fill), src("fill")))
    if s.fill is not None and data_by is not None:
        rows.append(("fill", _rgba(s.fill), src("fill")))
    if s.stroke is not None:
        rows.append(("stroke", _rgba(s.stroke), src("stroke")))
    if s.stroke_width is not None:
        rows.append(("stroke width", f"{s.stroke_width:g} px", src("stroke_width")))
    if s.size is not None:
        rows.append(("size", f"{s.size:g} px", src("size")))
    if s.opacity is not None:
        rows.append(("opacity", f"{s.opacity:g}", src("opacity")))
    if s.highlight is not None:
        rows.append(("highlight", _rgba(s.highlight), src("highlight")))
    if s.tooltip:
        rows.append(("tooltip", ", ".join(s.tooltip), src("tooltip")))
    if s.extrude_by is not None:
        top = f", tallest {s.extrude_max:g} m" if s.extrude_max else ""
        rows.append(("extrude", f"data: {s.extrude_by}{top}", src("extrude")))
    rows.append(("basemap", s.basemap or "light", src("basemap")))
    legend = "hidden" if not s.legend else LEGEND_POSITIONS[s.legend_position or "br"]
    rows.append(("legend", legend, src("legend")))
    if s.columns:
        rows.append(("columns read", ", ".join(s.columns), ""))

    w1 = max(len(r[0]) for r in rows)
    w2 = max(len(r[1]) for r in rows)
    lines = [f"{a:<{w1}}  {b:<{w2}}  {c}".rstrip() for a, b, c in rows]
    return Explanation("\n".join(lines))


def utilities() -> list[Utility]:
    """Every utility kharita understands."""
    return list(UTILITIES.values())


def help(name: str | None = None) -> None:  # noqa: A001
    """Print every utility, or the details and examples for one."""
    if name is None:
        width = max(len(u.name) for u in UTILITIES.values())
        for u in UTILITIES.values():
            print(f"{u.name:<{width}}  {u.description}")
        print("\nkh.help('fill') shows the syntax and examples for one utility.")
        return
    u = UTILITIES.get(name.split("-")[0])
    if u is None:
        match = get_close_matches(name, list(UTILITIES), n=1)
        hint = f" Did you mean '{match[0]}'?" if match else ""
        raise ValueError(f"No utility '{name}'.{hint}")
    print(f"{u.name}: {u.description}\n\nSyntax:   {u.syntax}\nExamples: {'  '.join(u.examples)}")
    if u.name == "preset":
        print(f"Built-in: {', '.join(BUILTIN_PRESETS)}")
        if USER_PRESETS:
            print(f"Defined:  {', '.join(USER_PRESETS)}")
