"""skill.adapt must follow MASTER factory — not a second pick_candidate."""

from __future__ import annotations

from batch.skill_adapt import candidate_aligned_to_master

MASTER = """
# Design System Master File

### Color Palette

| Role | Hex | CSS Variable |
|------|-----|--------------|
| Primary | `#1E3A5F` | `--color-primary` |
| Accent/CTA | `#A16207` | `--color-accent` |
| Background | `#F8FAFC` | `--color-background` |
| Foreground | `#0F172A` | `--color-foreground` |

**Color Notes:** Academic navy + gold keynote

### Typography

- **Heading Font:** Outfit
- **Body Font:** Outfit
- **Mood:** bauhaus, geometric
- **Google Fonts:** [Outfit](https://fonts.googleapis.com/css2?family=Outfit:wght@400;700&display=swap)

## Style Guidelines

**Style:** Feature-Rich Showcase

**Keywords:** grid layout, benefit cards

### Page Pattern

**Pattern Name:** App Store Style Landing
"""


def test_aligns_to_master_matching_c1_not_dark_c3() -> None:
    candidates = [
        {
            "id": "c1",
            "style": {"name": "Feature-Rich Showcase", "keywords": "grid"},
            "colors": {
                "primary": "#1E3A5F",
                "accent": "#A16207",
                "background": "#F8FAFC",
                "foreground": "#0F172A",
            },
            "typography": {"heading": "Outfit", "body": "Outfit"},
            "pattern": {"name": "App Store Style Landing"},
        },
        {
            "id": "c3",
            "style": {"name": "Bauhaus (包豪斯)", "keywords": "hard shadow"},
            "colors": {
                "primary": "#0F172A",
                "accent": "#16A34A",
                "background": "#020617",
                "foreground": "#F8FAFC",
            },
            "typography": {"heading": "Playfair Display", "body": "Source Serif 4"},
            "pattern": {"name": "Horizontal Scroll Journey"},
        },
    ]
    selected, rationale = candidate_aligned_to_master(candidates, MASTER)
    assert selected["id"] == "c1"
    assert selected["colors"]["primary"] == "#1E3A5F"
    assert selected["colors"]["accent"] == "#A16207"
    assert selected["colors"]["background"] == "#F8FAFC"
    assert selected["typography"]["heading"] == "Outfit"
    assert "Bauhaus" not in str(selected.get("style", {}).get("name", ""))
    assert "no re-pick" in rationale
    assert selected["colors"]["cta"] == "#A16207"


def test_overlays_master_when_no_palette_match() -> None:
    candidates = [
        {
            "id": "c3",
            "style": {"name": "Bauhaus (包豪斯)"},
            "colors": {"primary": "#0F172A", "accent": "#16A34A", "background": "#020617"},
            "typography": {"heading": "Playfair Display"},
            "pattern": {"name": "Horizontal Scroll Journey"},
        }
    ]
    selected, _ = candidate_aligned_to_master(candidates, MASTER)
    assert selected["colors"]["primary"] == "#1E3A5F"
    assert selected["colors"]["accent"] == "#A16207"
    assert selected["typography"]["heading"] == "Outfit"
    assert selected["style"]["name"] == "Feature-Rich Showcase"
    assert selected["pattern"]["name"] == "App Store Style Landing"
