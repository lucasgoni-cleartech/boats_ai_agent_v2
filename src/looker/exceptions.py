"""Looker service exceptions."""


class LookerAuthError(Exception):
    """Raised when Looker authentication fails."""
    pass


class LookerAPIError(Exception):
    """Raised when Looker API requests fail."""
    pass