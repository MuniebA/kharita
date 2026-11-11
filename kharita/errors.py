"""Typed errors raised by kharita."""


class KharitaError(Exception):
    """Base class for every kharita error."""


class StyleSyntaxError(KharitaError):
    """A style string could not be parsed."""

    def __init__(self, message: str, token: str | None = None, position: int | None = None):
        self.token = token
        self.position = position
        super().__init__(message)


class BindingError(KharitaError):
    """A style refers to data that is missing or unusable."""

    def __init__(self, message: str, column: str | None = None):
        self.column = column
        super().__init__(message)
