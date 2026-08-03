"""H2.8E — Identity Generation subsystem (governed path over design.image_generation).

Designed against docs/architecture/marketsynth_subsystem_standard.md.
Not a second Runtime or Agent Registry.
"""

from app.identity_generation.errors import identity_error_message
from app.identity_generation.recipes import list_identity_recipes

__all__ = ["identity_error_message", "list_identity_recipes"]
