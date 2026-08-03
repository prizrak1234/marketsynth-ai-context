"""Discovery errors."""

from __future__ import annotations


class DiscoveryError(Exception):
    """Base discovery error."""


class DiscoveryValidationError(DiscoveryError):
    """Invalid query or result."""


class DiscoverySecurityError(DiscoveryError):
    """Rejected sensitive input."""
