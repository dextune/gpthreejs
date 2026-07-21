"""Optional image generation/edit provider port and budget contract."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


class ImageProvider(Protocol):
    """Port for optional image generation / edit backends."""

    name: str

    def generate(self, prompt: str, *, budget: "ProviderBudget") -> dict[str, Any]:
        ...

    def edit(
        self,
        image_path: str,
        prompt: str,
        *,
        budget: "ProviderBudget",
    ) -> dict[str, Any]:
        ...


@dataclass
class ProviderBudget:
    max_generations: int = 4
    max_edits: int = 8
    max_wall_seconds: float = 120.0
    spent_generations: int = 0
    spent_edits: int = 0
    spent_wall_seconds: float = 0.0
    notes: list[str] = field(default_factory=list)

    def can_generate(self) -> bool:
        return self.spent_generations < self.max_generations

    def can_edit(self) -> bool:
        return self.spent_edits < self.max_edits

    def record_generate(self, wall_seconds: float = 0.0) -> None:
        self.spent_generations += 1
        self.spent_wall_seconds += wall_seconds

    def record_edit(self, wall_seconds: float = 0.0) -> None:
        self.spent_edits += 1
        self.spent_wall_seconds += wall_seconds

    def exhausted(self) -> bool:
        return (
            self.spent_generations >= self.max_generations
            and self.spent_edits >= self.max_edits
        ) or self.spent_wall_seconds >= self.max_wall_seconds

    def to_dict(self) -> dict[str, Any]:
        return {
            "maxGenerations": self.max_generations,
            "maxEdits": self.max_edits,
            "maxWallSeconds": self.max_wall_seconds,
            "spentGenerations": self.spent_generations,
            "spentEdits": self.spent_edits,
            "spentWallSeconds": self.spent_wall_seconds,
            "notes": list(self.notes),
        }


class NullImageProvider:
    """Default provider: always asks the operator; never invents pixels."""

    name = "null"

    def generate(self, prompt: str, *, budget: ProviderBudget) -> dict[str, Any]:
        budget.notes.append("null provider cannot generate images")
        return {
            "status": "ask",
            "agentAction": "ask",
            "reason": "no image generation provider installed",
            "prompt": prompt,
            "budget": budget.to_dict(),
            "remedy": "install and configure an image provider, or supply additional reference views",
        }

    def edit(
        self,
        image_path: str,
        prompt: str,
        *,
        budget: ProviderBudget,
    ) -> dict[str, Any]:
        budget.notes.append("null provider cannot edit images")
        return {
            "status": "ask",
            "agentAction": "ask",
            "reason": "no image edit provider installed",
            "imagePath": image_path,
            "prompt": prompt,
            "budget": budget.to_dict(),
            "remedy": "install and configure an image provider, or supply missing views manually",
        }


def get_image_provider(name: str | None = None) -> ImageProvider:
    """Resolve a provider by name. Unknown/missing providers return NullImageProvider."""

    if name in (None, "", "null", "none"):
        return NullImageProvider()
    # Vendor-specific adapters are deferred (REF-150). Unknown names still ask.
    return NullImageProvider()


def plan_missing_views(
    target_views: list[str],
    present_views: list[str],
    *,
    budget: ProviderBudget | None = None,
    provider: ImageProvider | None = None,
) -> dict[str, Any]:
    """Plan generation/edit of missing target views under budget."""

    provider = provider or get_image_provider()
    budget = budget or ProviderBudget()
    present = {v.lower() for v in present_views}
    missing = [v for v in target_views if v.lower() not in present]

    if not missing:
        return {
            "status": "ok",
            "missingViews": [],
            "agentAction": "continue",
            "budget": budget.to_dict(),
            "provider": provider.name,
        }

    # Without a real provider, always ask.
    if isinstance(provider, NullImageProvider) or provider.name == "null":
        result = provider.generate(
            f"generate missing views: {', '.join(missing)}",
            budget=budget,
        )
        result["missingViews"] = missing
        return result

    actions: list[dict[str, Any]] = []
    for view in missing:
        if not budget.can_edit() and not budget.can_generate():
            return {
                "status": "budget_exhausted",
                "agentAction": "ask",
                "missingViews": missing,
                "completed": actions,
                "budget": budget.to_dict(),
                "reason": "provider budget exhausted before all views filled",
            }
        # Prefer edit of a hero view when available.
        actions.append({"view": view, "mode": "edit" if budget.can_edit() else "generate"})
        if budget.can_edit():
            budget.record_edit()
        else:
            budget.record_generate()

    return {
        "status": "planned",
        "missingViews": missing,
        "actions": actions,
        "agentAction": "continue",
        "budget": budget.to_dict(),
        "provider": provider.name,
    }
