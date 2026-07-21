"""Matte confidence scoring for reference images."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from engine.sense.matte import matte_heuristic
from engine.shared.pngio import Image, read_png


def _connected_components(mask: list[bool], width: int, height: int) -> list[int]:
    visited = [False] * (width * height)
    sizes: list[int] = []
    for y in range(height):
        for x in range(width):
            idx = y * width + x
            if not mask[idx] or visited[idx]:
                continue
            stack = [idx]
            visited[idx] = True
            size = 0
            while stack:
                current = stack.pop()
                size += 1
                cx, cy = current % width, current // width
                for nx, ny in (
                    (cx - 1, cy),
                    (cx + 1, cy),
                    (cx, cy - 1),
                    (cx, cy + 1),
                ):
                    if nx < 0 or ny < 0 or nx >= width or ny >= height:
                        continue
                    nidx = ny * width + nx
                    if mask[nidx] and not visited[nidx]:
                        visited[nidx] = True
                        stack.append(nidx)
            sizes.append(size)
    return sizes


def assess_matte_confidence(
    image: str | Path | Image,
    *,
    matte: Image | None = None,
    threshold: int = 42,
) -> dict[str, Any]:
    """Score matte quality and return structured confidence signals."""

    if isinstance(image, Image):
        src = image
        source_path = None
    else:
        source_path = str(image)
        src = read_png(image)

    matted = matte if matte is not None else matte_heuristic(src, threshold=threshold)
    width, height = matted.width, matted.height
    area = max(1, width * height)
    rgba = matted.rgba

    mask = [False] * area
    opaque = 0
    edge_contact = 0
    edge_pixels = 0
    hole_like = 0

    for y in range(height):
        for x in range(width):
            alpha = rgba[(y * width + x) * 4 + 3]
            on = alpha > 128
            mask[y * width + x] = on
            if on:
                opaque += 1
            on_edge = x == 0 or y == 0 or x == width - 1 or y == height - 1
            if on_edge:
                edge_pixels += 1
                if on:
                    edge_contact += 1
            # Local noise: isolated opaque/transparent flips vs 4-neighbors later via components.

    occupancy = opaque / area
    edge_contact_ratio = edge_contact / max(1, edge_pixels)
    components = _connected_components(mask, width, height)
    largest = max(components) if components else 0
    largest_ratio = largest / max(1, opaque) if opaque else 0.0
    noise_ratio = 0.0
    if components:
        small = sum(1 for size in components if size < max(4, area * 0.0005))
        noise_ratio = small / max(1, len(components))

    # Corner background variance on source RGB.
    corners = [
        src.pixel(0, 0),
        src.pixel(width - 1, 0),
        src.pixel(0, height - 1),
        src.pixel(width - 1, height - 1),
    ]
    means = [sum(c[i] for c in corners) / 4.0 for i in range(3)]
    corner_var = sum(
        ((c[i] - means[i]) ** 2 for c in corners for i in range(3))
    ) / 12.0

    # Boundary roughness: alpha transitions per interior edge.
    transitions = 0
    samples = 0
    for y in range(height):
        for x in range(width - 1):
            a0 = rgba[(y * width + x) * 4 + 3] > 128
            a1 = rgba[(y * width + x + 1) * 4 + 3] > 128
            transitions += int(a0 != a1)
            samples += 1
    for y in range(height - 1):
        for x in range(width):
            a0 = rgba[(y * width + x) * 4 + 3] > 128
            a1 = rgba[((y + 1) * width + x) * 4 + 3] > 128
            transitions += int(a0 != a1)
            samples += 1
    boundary_roughness = transitions / max(1, samples)

    # Confidence composite in [0, 1].
    confidence = 1.0
    issues: list[str] = []
    if occupancy < 0.02 or occupancy > 0.98:
        confidence -= 0.35
        issues.append("occupancy_extreme")
    if edge_contact_ratio > 0.35:
        confidence -= 0.25
        issues.append("subject_fills_frame")
    if largest_ratio < 0.7 and opaque > 0:
        confidence -= 0.15
        issues.append("fragmented_components")
    if noise_ratio > 0.4:
        confidence -= 0.1
        issues.append("noise_components")
    if corner_var > 800:
        confidence -= 0.15
        issues.append("complex_background")
    if boundary_roughness > 0.15:
        confidence -= 0.05
        issues.append("rough_boundary")
    confidence = max(0.0, min(1.0, confidence))

    normalization_candidate = "subject_fills_frame" in issues and occupancy > 0.55

    return {
        "schemaVersion": 1,
        "sourcePath": source_path,
        "method": "corner-distance" if matte is None else "provided",
        "signals": {
            "occupancy": occupancy,
            "edgeContactRatio": edge_contact_ratio,
            "largestComponentRatio": largest_ratio,
            "noiseRatio": noise_ratio,
            "cornerBackgroundVariance": corner_var,
            "boundaryRoughness": boundary_roughness,
            "componentCount": len(components),
            "opaquePixels": opaque,
        },
        "confidence": confidence,
        "issues": issues,
        "normalizationCandidate": normalization_candidate,
        "agentAction": (
            "normalize"
            if normalization_candidate and confidence < 0.7
            else "continue"
            if confidence >= 0.55
            else "ask"
        ),
    }
