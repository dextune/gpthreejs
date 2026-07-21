"""Generic surface detail stack — bake maps and annotate blueprints."""

from engine.cast.surface.bake_maps import bake_surface_stack, SURFACE_PRESETS
from engine.cast.surface.schema import default_surface_stack, merge_surface_into_blueprint

__all__ = [
    "bake_surface_stack",
    "SURFACE_PRESETS",
    "default_surface_stack",
    "merge_surface_into_blueprint",
]
