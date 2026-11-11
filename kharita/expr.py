"""Parses what sits inside brackets: a column, a ratio, a scaled column or a column list."""

import math
from dataclasses import dataclass

QUOTES = "'\""
LIMITS = "Only [col], [col/col] or [col*number] are allowed; compute anything else in pandas first."


@dataclass(frozen=True)
class Expr:
    column: str
    divisor: str | None = None
    factor: float | None = None

    @property
    def columns(self) -> tuple[str, ...]:
        # Every column this expression reads
        return (self.column, self.divisor) if self.divisor else (self.column,)

    def __str__(self) -> str:
        if self.divisor:
            return f"{self.column} / {self.divisor}"
        if self.factor is not None:
            return f"{self.column} * {self.factor:g}"
        return self.column


def is_number(text: str) -> bool:
    # True for anything float() accepts
    try:
        float(text)
    except ValueError:
        return False
    return True


def _split_top(text: str, sep: str) -> list[str]:
    # Split on a separator that is not inside quotes
    parts, buf, quote = [], [], ""
    for ch in text:
        if quote:
            buf.append(ch)
            if ch == quote:
                quote = ""
        elif ch in QUOTES:
            quote = ch
            buf.append(ch)
        elif ch == sep:
            parts.append("".join(buf))
            buf = []
        else:
            buf.append(ch)
    parts.append("".join(buf))
    return parts


def _column(part: str) -> str:
    # A bare or quoted column name
    name = part.strip()
    if len(name) >= 2 and name[0] in QUOTES and name[-1] == name[0]:
        name = name[1:-1]
        if not name:
            raise ValueError("Quoted column name is empty.")
        return name
    if not name:
        raise ValueError("Column name is missing.")
    if any(q in name for q in QUOTES):
        raise ValueError(f"Quotes must wrap the whole column name: '{name}'.")
    return name


def parse_expr(text: str) -> Expr:
    # Inside of brackets to an Expr
    by_slash = _split_top(text, "/")
    by_star = _split_top(text, "*")
    if len(by_slash) > 1 and len(by_star) > 1:
        raise ValueError(LIMITS)
    if len(by_slash) > 2 or len(by_star) > 2:
        raise ValueError(LIMITS)
    if len(by_slash) == 2:
        return Expr(_column(by_slash[0]), divisor=_column(by_slash[1]))
    if len(by_star) == 2:
        left, right = by_star[0].strip(), by_star[1].strip()
        if is_number(left):
            raise ValueError(f"Put the column first: [{right}*{left}].")
        if not is_number(right):
            raise ValueError(f"'{right}' is not a number. {LIMITS}")
        factor = float(right)
        if not math.isfinite(factor) or factor == 0:
            raise ValueError("The multiplier must be a finite number other than 0.")
        return Expr(_column(left), factor=factor)
    return Expr(_column(text))


def parse_columns(text: str) -> tuple[str, ...]:
    # Inside of brackets to a tuple of column names separated by commas
    cols = tuple(_column(p) for p in _split_top(text, ","))
    if len(set(cols)) != len(cols):
        raise ValueError("A column is listed twice.")
    return cols
