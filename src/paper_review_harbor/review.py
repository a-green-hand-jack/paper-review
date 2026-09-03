"""Portable structured-review contract used by task verifiers and expert tooling."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

REVIEW_SCHEMA_VERSION = 1
SEVERITIES = frozenset({"critical", "major", "minor", "suggestion"})
CONFIDENCES = frozenset({"high", "medium", "low"})
DECISIONS = frozenset(
    {"accept", "weak_accept", "borderline", "weak_reject", "reject", "not_given"}
)
SCORE_FIELDS = ("soundness", "novelty", "clarity", "significance")


class ReviewContractError(ValueError):
    """A submitted structured review is malformed."""


def _require_mapping(value: object, field: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ReviewContractError(f"{field} must be an object")
    return value


def _require_text(value: object, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ReviewContractError(f"{field} must be a non-empty string")
    return value.strip()


def _require_text_list(value: object, field: str) -> list[str]:
    if not isinstance(value, list):
        raise ReviewContractError(f"{field} must be a list")
    return [_require_text(item, f"{field}[{index}]") for index, item in enumerate(value)]


def _choice(value: object, field: str, allowed: frozenset[str]) -> str:
    text = _require_text(value, field)
    if text not in allowed:
        choices = ", ".join(sorted(allowed))
        raise ReviewContractError(f"{field} must be one of: {choices}")
    return text


def _score(value: object, field: str) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= 5:
        raise ReviewContractError(f"{field} must be an integer from 1 to 5, or null")
    return value


def validate_review(payload: object) -> dict[str, Any]:
    """Validate and normalize the portable ``review.json`` schema.

    This establishes a machine-readable review shape only. It deliberately does
    not infer whether a finding is correct or score review quality; that is
    recorded by a separate human-expert assessment workflow.
    """
    root = _require_mapping(payload, "review")
    if root.get("schema_version") != REVIEW_SCHEMA_VERSION:
        raise ReviewContractError(f"schema_version must be {REVIEW_SCHEMA_VERSION}")

    findings_raw = root.get("findings")
    if not isinstance(findings_raw, list):
        raise ReviewContractError("findings must be a list")
    findings: list[dict[str, str]] = []
    for index, raw in enumerate(findings_raw):
        finding = _require_mapping(raw, f"findings[{index}]")
        findings.append(
            {
                "category": _require_text(finding.get("category"), f"findings[{index}].category"),
                "severity": _choice(
                    finding.get("severity"), f"findings[{index}].severity", SEVERITIES
                ),
                "location": _require_text(finding.get("location"), f"findings[{index}].location"),
                "claim": _require_text(finding.get("claim"), f"findings[{index}].claim"),
                "evidence": _require_text(finding.get("evidence"), f"findings[{index}].evidence"),
                "confidence": _choice(
                    finding.get("confidence"), f"findings[{index}].confidence", CONFIDENCES
                ),
            }
        )

    recommendation = _require_mapping(root.get("recommendation"), "recommendation")
    scores = _require_mapping(root.get("scores"), "scores")
    unexpected_scores = set(scores) - set(SCORE_FIELDS)
    missing_scores = set(SCORE_FIELDS) - set(scores)
    if unexpected_scores or missing_scores:
        raise ReviewContractError(f"scores must contain exactly: {', '.join(SCORE_FIELDS)}")
    return {
        "schema_version": REVIEW_SCHEMA_VERSION,
        "summary": _require_text(root.get("summary"), "summary"),
        "strengths": _require_text_list(root.get("strengths"), "strengths"),
        "findings": findings,
        "questions": _require_text_list(root.get("questions"), "questions"),
        "recommendation": {
            "decision": _choice(
                recommendation.get("decision"), "recommendation.decision", DECISIONS
            ),
            "confidence": _choice(
                recommendation.get("confidence"), "recommendation.confidence", CONFIDENCES
            ),
        },
        "scores": {field: _score(scores.get(field), f"scores.{field}") for field in SCORE_FIELDS},
    }


def load_review(path: Path) -> dict[str, Any]:
    """Read and validate a ``review.json`` file, with a useful contract error."""
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise ReviewContractError(f"{path}: invalid JSON") from error
    return validate_review(payload)
