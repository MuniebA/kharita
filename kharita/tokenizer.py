"""Splits a style string into tokens, keeping bracket contents whole."""

from dataclasses import dataclass

from kharita.errors import StyleSyntaxError

QUOTES = "'\""


@dataclass(frozen=True)
class Token:
    text: str
    start: int
    via: str = ""

    @property
    def shown(self) -> str:
        # What the user typed at this position: the token, or the preset it came from
        return self.via or self.text

    @property
    def label(self) -> str:
        # Token text, naming the preset when it came from one
        return f"{self.text} (from {self.via})" if self.via else self.text


def tokenize(style: str) -> list[Token]:
    # Split on whitespace outside brackets; quotes inside brackets may hold any character
    if not isinstance(style, str):
        raise StyleSyntaxError(f"A style must be a string, not {type(style).__name__}.")
    tokens: list[Token] = []
    buf: list[str] = []
    start = 0
    in_bracket = False
    bracket_at = -1
    quote = ""
    quote_at = -1

    for i, ch in enumerate(style):
        if quote:
            buf.append(ch)
            if ch == quote:
                quote = ""
            continue
        if in_bracket and ch in QUOTES:
            quote, quote_at = ch, i
            buf.append(ch)
            continue
        if ch == "[":
            if in_bracket:
                raise StyleSyntaxError(
                    "Brackets cannot be nested.", token="[", position=i, style=style
                )
            in_bracket, bracket_at = True, i
        elif ch == "]":
            if not in_bracket:
                raise StyleSyntaxError(
                    "Closing bracket without an opening one.", token="]", position=i, style=style
                )
            in_bracket = False
        elif ch.isspace() and not in_bracket:
            if buf:
                tokens.append(Token("".join(buf), start))
                buf = []
            continue
        if not buf:
            start = i
        buf.append(ch)

    if quote:
        raise StyleSyntaxError(
            "Quote is never closed.", token=quote, position=quote_at, style=style
        )
    if in_bracket:
        raise StyleSyntaxError(
            "Bracket is never closed.", token="[", position=bracket_at, style=style
        )
    if buf:
        tokens.append(Token("".join(buf), start))
    return tokens
