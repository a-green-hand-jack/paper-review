"""Private human-expert assessment contract for collected review trails."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ASSESSMENT_SCHEMA_VERSION = 1
CRITERIA = ("grounding", "correctness", "coverage", "actionability")


class AssessmentContractError(ValueError):
    """A human-expert assessment record is malformed."""


def _text(value: object, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise AssessmentContractError(f"{field} must be a non-empty string")
    return value.strip()


def _mapping(value: object, field: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise AssessmentContractError(f"{field} must be an object")
    return value


def _score(value: object, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= 5:
        raise AssessmentContractError(f"{field} must be an integer from 1 to 5")
    return value


def validate_assessment(payload: object) -> dict[str, Any]:
    """Validate a private expert label without judging its content.

    Human labels are deliberately outside the Harbor task runtime and should be
    stored only in an access-controlled evaluation asset.
    """
    root = _mapping(payload, "assessment")
    if root.get("schema_version") != ASSESSMENT_SCHEMA_VERSION:
        raise AssessmentContractError(f"schema_version must be {ASSESSMENT_SCHEMA_VERSION}")
    criteria = _mapping(root.get("criteria"), "criteria")
    unexpected = set(criteria) - set(CRITERIA)
    missing = set(CRITERIA) - set(criteria)
    if unexpected or missing:
        raise AssessmentContractError(
            f"criteria must contain exactly: {', '.join(CRITERIA)}"
        )
    return {
        "schema_version": ASSESSMENT_SCHEMA_VERSION,
        "assessment_id": _text(root.get("assessment_id"), "assessment_id"),
        "source_record_id": _text(root.get("source_record_id"), "source_record_id"),
        "task_id": _text(root.get("task_id"), "task_id"),
        "task_revision": _text(root.get("task_revision"), "task_revision"),
        "trail_id": _text(root.get("trail_id"), "trail_id"),
        "rubric_version": _text(root.get("rubric_version"), "rubric_version"),
        "assessor_id": _text(root.get("assessor_id"), "assessor_id"),
        "criteria": {field: _score(criteria[field], f"criteria.{field}") for field in CRITERIA},
        "overall_score": _score(root.get("overall_score"), "overall_score"),
        "rationale": _text(root.get("rationale"), "rationale"),
    }


def load_assessment(path: Path) -> dict[str, Any]:
    """Read and validate one private expert assessment JSON document."""
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise AssessmentContractError(f"{path}: invalid JSON") from error
    return validate_assessment(payload)
