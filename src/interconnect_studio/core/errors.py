"""Core domain exceptions."""


class InputValidationError(ValueError):
    """Raised when input data violates a core domain invariant."""


class DataFormatError(ValueError):
    """Raised when an input file or serialized representation is invalid."""
