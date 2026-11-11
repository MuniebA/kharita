"""Typed errors raised by kharita."""


class KharitaError(Exception):
    """Base class for every kharita error."""


def _pointer(style: str, position: int, length: int) -> str:
    # Two extra lines showing the style string with a caret under the problem
    return f"\n  {style}\n  {' ' * position}{'^' * max(length, 1)}"


class StyleSyntaxError(KharitaError):
    """A style string could not be parsed."""

    def __init__(
        self,
        message: str,
        token: str | None = None,
        position: int | None = None,
        style: str | None = None,
    ):
        self.token = token
        self.position = position
        self.style = style
        if style is not None and position is not None:
            message += _pointer(style, position, len(token) if token else 1)
        super().__init__(message)


class BindingError(KharitaError):
    """A style refers to data that is missing or unusable."""

    def __init__(self, message: str, column: str | None = None):
        self.column = column
        super().__init__(message)
