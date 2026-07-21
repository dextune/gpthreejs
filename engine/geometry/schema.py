"""Discriminated geometry schema contract."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class GeometrySpecDefinition:
    kind: str
    required_fields: tuple[str, ...]
    purpose: str


GEOMETRY_SPEC_DEFINITIONS: tuple[GeometrySpecDefinition, ...] = (
    GeometrySpecDefinition("box", ("size",), "rectangular mass and blockout forms"),
    GeometrySpecDefinition("sphere", ("radius",), "round joints and compact masses"),
    GeometrySpecDefinition("ellipsoid", ("radii",), "stretched organic or armor masses"),
    GeometrySpecDefinition("capsule", ("radius", "length"), "limbs, fingers, and padded struts"),
    GeometrySpecDefinition("cylinder", ("radiusTop", "radiusBottom", "height"), "round props and limb sections"),
    GeometrySpecDefinition("cone", ("radius", "height"), "tapered spikes, horns, and tips"),
    GeometrySpecDefinition("torus", ("radius", "tube"), "rings, rims, and circular trim"),
    GeometrySpecDefinition("rounded-box", ("size", "radius"), "torso shells, boots, and prop bodies"),
    GeometrySpecDefinition("shape-extrude", ("shape", "depth"), "flat profiles such as shields, swords, and emblems"),
    GeometrySpecDefinition("lathe", ("profile",), "helmet domes, pommels, and ringed forms"),
    GeometrySpecDefinition("tube", ("path", "radius"), "trim, straps, cables, and rims"),
    GeometrySpecDefinition("beveled-plate", ("outline", "thickness", "bevel"), "armor plates and shield frames"),
    GeometrySpecDefinition("curve-blade", ("length", "width", "curve"), "curved fantasy blades"),
    GeometrySpecDefinition("feather", ("length", "width", "barbCount"), "layered plume silhouettes"),
    GeometrySpecDefinition("cloth-patch", ("width", "height", "drape"), "scarves, capes, and tunic flaps"),
    GeometrySpecDefinition("instance-set", ("prototype", "count", "distribution"), "rivets, studs, and repeated detail"),
)

GEOMETRY_SPECS = {definition.kind: definition for definition in GEOMETRY_SPEC_DEFINITIONS}
SUPPORTED_GEOMETRY_KINDS = tuple(definition.kind for definition in GEOMETRY_SPEC_DEFINITIONS)


class UnsupportedGeometryError(ValueError):
    """Raised when a Blueprint requests an unknown geometry kind."""


def geometry_required_fields(kind: str) -> tuple[str, ...]:
    definition = GEOMETRY_SPECS.get(kind)
    return definition.required_fields if definition else ()


def geometry_schema() -> dict[str, Any]:
    """Return a JSON-schema-shaped discriminated union for geometry specs."""

    return deepcopy(_GEOMETRY_SCHEMA)


def validate_geometry_required_fields(spec: dict[str, Any], *, path: str = "$.geometry") -> list[str]:
    """Validate kind-specific required fields for a known geometry spec."""

    kind = spec.get("kind")
    if kind not in GEOMETRY_SPECS:
        return [f"{path}.kind: unsupported geometry kind {kind!r}"]
    return [
        f"{path}.{field}: missing required field for geometry kind {kind!r}"
        for field in geometry_required_fields(str(kind))
        if field not in spec
    ]


_GEOMETRY_SCHEMA: dict[str, Any] = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "$id": "https://gpthreejs.local/contracts/geometry.schema.json",
    "title": "gpthreejs GeometrySpec",
    "oneOf": [
        {
            "type": "object",
            "required": ["kind", *definition.required_fields],
            "properties": {
                "kind": {"const": definition.kind},
                **{field: {} for field in definition.required_fields},
            },
            "additionalProperties": True,
        }
        for definition in GEOMETRY_SPEC_DEFINITIONS
    ],
}
