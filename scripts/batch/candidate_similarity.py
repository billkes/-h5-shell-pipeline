"""Candidate registry similarity checker — fallback ladder for skill.design.

Purpose
-------
After ``skill.design`` generates 3 candidates, this module compares them
against the contentpack registry and applies a 4-step fallback ladder:

  1. Pick the least-similar candidate (even if above threshold), emit WARN.
  2. Retry with differentiated dials + query until similarity drops below threshold.
  3. Anti-style search: pick a style from styles.csv that overlaps least with registry.
  4. Fail with actionable root-cause analysis.

Similarity is computed on:
  - style name (exact match = 0.5)
  - category (exact match = 0.3)
  - keywords overlap (up to 0.2)

Thresholds:
  - < 0.50 : PASS
  - 0.50 – 0.70 : WARN (still usable, logged)
  - > 0.70 : FAIL → trigger fallback
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# ─── Similarity computation ───────────────────────────────────────────────


def _norm(value: object) -> str:
    return str(value or "").strip().lower()


def _tokens(value: str) -> set[str]:
    return set(re.findall(r"[a-z]+", _norm(value)))


def candidate_similarity(candidate: dict[str, Any], registry_entries: list[dict]) -> float:
    """Compute a 0–1 similarity score between a single candidate and the *worst* registry entry.

    Returns the maximum similarity across all registry entries (we want the worst-case overlap).
    If registry is empty, returns 0.0.
    """
    if not registry_entries:
        return 0.0

    cand_style = _norm(candidate.get("style", {}).get("name", ""))
    cand_category = _norm(candidate.get("category", ""))
    cand_keywords = _tokens(candidate.get("style", {}).get("keywords", ""))
    cand_effects = _tokens(candidate.get("key_effects", ""))

    max_sim = 0.0
    for entry in registry_entries:
        reg_style = _norm(entry.get("style", {}).get("name", ""))
        reg_category = _norm(entry.get("category", ""))
        reg_keywords = _tokens(entry.get("style", {}).get("keywords", ""))
        reg_effects = _tokens(entry.get("key_effects", ""))

        score = 0.0

        # Style name exact match: 0.5
        if cand_style and reg_style and (cand_style == reg_style or cand_style in reg_style or reg_style in cand_style):
            score += 0.5

        # Category match: 0.3
        if cand_category and reg_category and (cand_category == reg_category or cand_category in reg_category or reg_category in cand_category):
            score += 0.3

        # Keyword overlap: up to 0.2
        if cand_keywords and reg_keywords:
            union = cand_keywords | reg_keywords
            if union:
                score += 0.2 * len(cand_keywords & reg_keywords) / len(union)

        # Effects overlap: up to 0.1
        if cand_effects and reg_effects:
            union = cand_effects | reg_effects
            if union:
                score += 0.1 * len(cand_effects & reg_effects) / len(union)

        max_sim = max(max_sim, score)

    return max_sim


# ─── Registry loading ─────────────────────────────────────────────────────


def load_registry_packages(registry_path: Path) -> list[dict]:
    """Load packages from contentpack-registry.json."""
    if not registry_path.is_file():
        return []
    try:
        data = json.loads(registry_path.read_text(encoding="utf-8"))
        packages = data.get("packages") or []
        return [p for p in packages if isinstance(p, dict)]
    except (json.JSONDecodeError, OSError):
        return []


def extract_candidate_registry_entry(candidate: dict[str, Any]) -> dict:
    """Convert a candidate dict into a registry-like dict for similarity comparison."""
    return {
        "style": {
            "name": candidate.get("style", {}).get("name", ""),
            "keywords": candidate.get("style", {}).get("keywords", ""),
        },
        "category": candidate.get("category", ""),
        "key_effects": candidate.get("key_effects", ""),
    }


# ─── Fallback Ladder ──────────────────────────────────────────────────────


@dataclass
class SimilarityResult:
    """Result of the similarity check + fallback ladder."""
    selected_candidate: dict[str, Any] | None = None
    similarity_score: float = 0.0
    status: str = "UNKNOWN"  # PASS, WARN, FAIL, RETRY
    log: list[str] = field(default_factory=list)
    next_action: str = ""  # What to do next


THRESHOLD_WARN = 0.50
THRESHOLD_FAIL = 0.70
MAX_RETRIES = 3


def check_and_select_candidate(
    candidates: list[dict[str, Any]],
    registry_path: Path,
    base_query: str,
    base_dials: dict[str, int],
) -> SimilarityResult:
    """Run the full 4-step fallback ladder and return the best candidate.

    Parameters
    ----------
    candidates : list of dicts from skill.design generate()
    registry_path : path to contentpack-registry.json
    base_query : original design query (before avoid suffix)
    base_dials : original variance/motion/density from designer_dials_from_row()

    Returns
    -------
    SimilarityResult with selected candidate, score, and status.
    """
    registry = load_registry_packages(registry_path)
    if not registry:
        return SimilarityResult(
            selected_candidate=candidates[0] if candidates else None,
            similarity_score=0.0,
            status="PASS",
            log=["Registry empty — no similarity check needed."],
        )

    # Convert registry entries to candidate-compatible format
    registry_entries = [extract_candidate_registry_entry(pkg) for pkg in registry]

    # ── Step 1: Pick the least-similar candidate ──────────────────────
    scored = []
    for cand in candidates:
        sim = candidate_similarity(cand, registry_entries)
        scored.append((sim, cand))

    scored.sort(key=lambda x: x[0])
    best_sim, best_cand = scored[0]

    if best_sim < THRESHOLD_WARN:
        return SimilarityResult(
            selected_candidate=best_cand,
            similarity_score=best_sim,
            status="PASS",
            log=[f"Candidate selected directly. Similarity: {best_sim:.2f}"],
        )

    if best_sim < THRESHOLD_FAIL:
        return SimilarityResult(
            selected_candidate=best_cand,
            similarity_score=best_sim,
            status="WARN",
            log=[
                f"Candidate selected with warning. Similarity: {best_sim:.2f} > {THRESHOLD_WARN}",
                "Consider differentiating in future batches.",
            ],
        )

    # ── Step 2: Retry with differentiated dials ───────────────────────
    log = [
        f"Step 1: All candidates above FAIL threshold ({best_sim:.2f}). Entering retry loop.",
    ]

    for attempt in range(1, MAX_RETRIES + 1):
        log.append(f"Step 2.{attempt}: Retrying with differentiated parameters...")

        new_query = _differentiate_query(base_query, registry_entries, attempt)
        new_dials = _differentiate_dials(base_dials, attempt)

        # Simulate re-generation with new params (caller will inject this)
        # For now, we return metadata for the caller to re-run generate()
        return SimilarityResult(
            selected_candidate=None,
            similarity_score=best_sim,
            status="RETRY",
            log=log,
            next_action=f"retry:{new_query}:{json.dumps(new_dials)}",
        )

    # ── Step 3: Anti-style search (if caller chooses to implement) ────
    # This would be called by the pipeline after retry exhaustion.
    # See anti_style_search() below.

    # ── Step 4: Fail with root cause ──────────────────────────────────
    return SimilarityResult(
        selected_candidate=None,
        similarity_score=best_sim,
        status="FAIL",
        log=log + [
            f"All {MAX_RETRIES} retries exhausted. Worst similarity: {best_sim:.2f}",
            "Root cause: registry is saturated with overlapping style/category/keywords.",
            "Action: change themeAngle or clean registry entries.",
        ],
    )


def _differentiate_query(base_query: str, registry_entries: list[dict], attempt: int) -> str:
    """Add anti-pollution keywords to steer away from registry themes."""
    # Collect all keywords from registry entries
    reg_keywords = set()
    for entry in registry_entries:
        reg_keywords.update(_tokens(entry.get("style", {}).get("keywords", "")))
        reg_keywords.update(_tokens(entry.get("category", "")))

    # Anti-keywords to push away from common registry themes
    anti_keywords = {
        "tracker": "minimalism clean flat professional saas",
        "journal": "dashboard productivity tool b2b",
        "mood": "data visualization analytics workflow",
        "dark": "light mode bright clean modern",
        "neon": "corporate enterprise trustworthy simple",
    }

    result = base_query
    for bad_word, good_words in anti_keywords.items():
        if bad_word in reg_keywords:
            result += f" {good_words}"

    # Add strength multiplier per attempt
    result += " " + " ".join(["distinct", "unique", "different"]) * attempt

    return result.strip()


def _differentiate_dials(base_dials: dict[str, int], attempt: int) -> dict[str, int]:
    """Shift dials to explore different style regions."""
    variance = base_dials.get("variance", 5)
    motion = base_dials.get("motion", 5)
    density = base_dials.get("density", 5)

    return {
        "variance": min(10, variance + 2 * attempt),  # Push toward Bold/Asymmetric
        "motion": min(10, motion + attempt),
        "density": min(10, density + attempt),
    }


# ─── Step 3: Anti-style search ────────────────────────────────────────────


def anti_style_search(
    registry_entries: list[dict],
    styles_csv_path: Path,
    max_results: int = 3,
) -> list[dict[str, Any]]:
    """Find styles from styles.csv that overlap LEAST with registry keywords.

    Returns up to max_results style dicts sorted by anti-similarity (least overlap first).
    """
    if not registry_entries:
        return []

    # Collect all registry keywords
    reg_keywords = set()
    for entry in registry_entries:
        reg_keywords.update(_tokens(entry.get("style", {}).get("keywords", "")))
        reg_keywords.update(_tokens(entry.get("category", "")))
        reg_keywords.update(_tokens(entry.get("key_effects", "")))

    # Load styles.csv
    if not styles_csv_path.is_file():
        return []

    try:
        import csv
        from io import StringIO
        styles_data = list(csv.DictReader(StringIO(styles_csv_path.read_text(encoding="utf-8"))))
    except Exception:
        return []

    # Score each style by anti-overlap (higher = less overlap = better)
    scored = []
    for style_row in styles_data:
        style_keywords = _tokens(style_row.get("Keywords", ""))
        style_name = _norm(style_row.get("Style Category", ""))
        style_type = _norm(style_row.get("Type", ""))

        # Calculate overlap
        union = reg_keywords | style_keywords
        if not union:
            overlap = 0.0
        else:
            overlap = len(reg_keywords & style_keywords) / len(union)

        # Bonus for light+dark support
        light_support = "Full" in str(style_row.get("Light Mode", ""))
        dark_support = "Full" in str(style_row.get("Dark Mode", ""))
        pair_bonus = 0.1 if (light_support and dark_support) else 0.0

        anti_score = 1.0 - overlap + pair_bonus

        scored.append((anti_score, style_row))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [dict(row) for _, row in scored[:max_results]]


# ─── Integration helper ──────────────────────────────────────────────────


def run_fallback_ladder(
    candidates: list[dict[str, Any]],
    registry_path: Path,
    base_query: str,
    base_dials: dict[str, int],
    styles_csv_path: Path | None = None,
    generator_fn=None,
) -> tuple[dict[str, Any] | None, SimilarityResult]:
    """Complete fallback ladder: retry → anti-style → fail.

    Parameters
    ----------
    candidates : initial candidates from skill.design
    registry_path : path to contentpack-registry.json
    base_query : original design query (without avoid suffix)
    base_dials : original dials from designer_dials_from_row()
    styles_csv_path : path to styles.csv (for anti-style search)
    generator_fn : callable(query, project_name, variance, motion, density) -> dict
                   If provided, will be called for retries.

    Returns
    -------
    (selected_candidate, result)
    """
    result = check_and_select_candidate(candidates, registry_path, base_query, base_dials)

    if result.status == "PASS":
        return result.selected_candidate, result

    if result.status == "WARN":
        return result.selected_candidate, result

    if result.status == "RETRY" and generator_fn and styles_csv_path:
        # Parse retry instruction
        try:
            _, new_query, new_dials_json = result.next_action.split(":", 2)
            new_dials = json.loads(new_dials_json)

            for attempt in range(1, MAX_RETRIES + 1):
                # Re-generate with differentiated params
                new_candidates = []
                for cid, dials in [("c1", new_dials), ("c2", {**new_dials, "variance": min(10, new_dials["variance"] + 2)})]:
                    ds = generator_fn(new_query, "Fallback", **dials)
                    ds["id"] = cid
                    new_candidates.append(ds)

                # Check similarity again
                retry_result = check_and_select_candidate(new_candidates, registry_path, new_query, new_dials)
                result.log.append(f"Retry {attempt}: best similarity = {retry_result.similarity_score:.2f} ({retry_result.status})")

                if retry_result.status in ("PASS", "WARN"):
                    result.selected_candidate = retry_result.selected_candidate
                    result.similarity_score = retry_result.similarity_score
                    result.status = retry_result.status
                    return result.selected_candidate, result

            # Exhausted retries → try anti-style search
            anti_styles = anti_style_search(
                [extract_candidate_registry_entry(pkg) for pkg in load_registry_packages(registry_path)],
                styles_csv_path,
                max_results=3,
            )

            if anti_styles:
                result.log.append(f"Step 3: Anti-style search found {len(anti_styles)} candidates.")
                result.log.append("  → Override style_priority in generator with: " + ", ".join(
                    s.get("Style Category", "") for s in anti_styles
                ))
                # Caller can use anti_styles to force a specific style
                return None, result  # Signal: use anti-styles to regenerate

        except Exception as e:
            result.log.append(f"Retry failed: {e}")

    # Step 4: Fail
    result.status = "FAIL"
    result.log.append("Step 4: All fallback strategies exhausted.")
    result.log.append("Root cause: registry saturation with overlapping styles.")
    result.log.append("Action: change themeAngle, clean registry, or increase THRESHOLD_FAIL.")

    return None, result
