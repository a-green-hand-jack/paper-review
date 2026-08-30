#!/usr/bin/env python3
"""Review three paper versions with identical settings and compare the opinions."""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import difflib
from pathlib import Path
import re
import subprocess
import sys

from osp_batch import ROOT, TRAIL_ROOT, paper_name


def latest_trail(paper: Path) -> Path:
    candidates = sorted((TRAIL_ROOT / paper_name(paper)).glob("*/brain/review/final_review.md"))
    if not candidates:
        raise FileNotFoundError(f"no final review found for {paper}")
    return candidates[-1].parents[2]


def review_version(paper: Path, args: argparse.Namespace) -> tuple[str, int, str]:
    command = [
        sys.executable, str(ROOT / "tools" / "osp_batch.py"),
        "--paper", str(paper.relative_to(ROOT)), "--venue", args.venue,
        "--llm", args.llm, "--harness", args.harness, "--workers", "1", "--execute",
    ]
    if args.variant:
        command += ["--variant", args.variant]
    if args.trail_repo:
        command += ["--trail-repo", args.trail_repo, "--upload"]
    result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
    if result.returncode:
        return paper.name, result.returncode, result.stdout + result.stderr
    return paper.name, 0, str(latest_trail(paper))


def review_signals(text: str) -> tuple[str, int | None]:
    recommendation_match = re.search(
        r"^## (?:Decision )?Recommendation\s*$([\s\S]*?)(?=^## |\Z)",
        text,
        re.MULTILINE,
    )
    recommendation = "unknown"
    if recommendation_match:
        recommendation_line = next(
            (line.strip() for line in recommendation_match.group(1).splitlines() if line.strip()),
            "",
        )
        recommendation = recommendation_line.strip("*.").lower()

    confidence_match = re.search(r"^## Confidence\s*$([\s\S]*?)^##? ", text, re.MULTILINE)
    confidence = None
    if confidence_match:
        value_match = re.search(r"\b([1-5])\s*/\s*5\b", confidence_match.group(1))
        if value_match:
            confidence = int(value_match.group(1))
    return recommendation, confidence


def ordering_status(signals: list[tuple[str, int | None]]) -> str:
    recommendation_ranks = {
        "reject": 0,
        "major revision": 1,
        "minor revision": 2,
        "accept": 3,
    }
    ranks = [recommendation_ranks.get(recommendation, -1) for recommendation, _ in signals]
    confidences = [confidence for _, confidence in signals]
    if -1 in ranks or any(value is None for value in confidences):
        return "inconclusive (missing structured signal)"
    if ranks[0] < ranks[1] < ranks[2] and confidences[0] <= confidences[1] <= confidences[2]:
        return "strictly increasing"
    if ranks[0] > ranks[1] or ranks[1] > ranks[2] or confidences[0] > confidences[1] or confidences[1] > confidences[2]:
        return "not increasing"
    return "inconclusive (tied reviewer outcomes)"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--v1", required=True, type=Path)
    parser.add_argument("--v2", required=True, type=Path)
    parser.add_argument("--v3", required=True, type=Path)
    parser.add_argument("--venue", default="arxiv")
    parser.add_argument("--llm", default="openai/gpt-5.6-sol")
    parser.add_argument("--variant", default="medium")
    parser.add_argument("--harness", default="opencode")
    parser.add_argument("--trail-repo")
    parser.add_argument("--reuse", action="store_true", help="compare the latest existing trails without rerunning reviews")
    args = parser.parse_args()
    versions = [("v1", ROOT / args.v1), ("v2", ROOT / args.v2), ("v3", ROOT / args.v3)]
    missing = [str(path) for _, path in versions if not path.is_file()]
    if missing:
        parser.error("missing version PDF(s): " + ", ".join(missing))

    trails: dict[str, Path] = {}
    failures = []
    if args.reuse:
        for label, path in versions:
            try:
                trails[label] = latest_trail(path)
            except FileNotFoundError as error:
                failures.append(f"{label}: {error}")
    else:
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = {executor.submit(review_version, path, args): label for label, path in versions}
            for future in as_completed(futures):
                label = futures[future]
                _, code, value = future.result()
                if code:
                    failures.append(f"{label}: {value}")
                else:
                    trails[label] = Path(value)
    if failures:
        print("\n".join(failures), file=sys.stderr)
        return 1

    comparison = TRAIL_ROOT / "erdos973-comparison" / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    comparison.mkdir(parents=True)
    reviews = {label: (trail / "brain" / "review" / "final_review.md").read_text() for label, trail in trails.items()}
    signals = {label: review_signals(reviews[label]) for label in ("v1", "v2", "v3")}
    for label, text in reviews.items():
        (comparison / f"{label}_review.md").write_text(text)
    report = [
        "# erdos973 Version Comparison",
        "",
        "This report compares reviews generated with identical settings.",
        "",
        f"- Venue: {args.venue}",
        f"- LLM: {args.llm}",
        f"- Variant: {args.variant or 'none'}",
        f"- Harness: {args.harness}",
        "",
        "## Expected Ordering",
        "",
        "The expected quality progression is `v1 < v2 < v3`.",
        "Inspect the decision, confidence, strengths, weaknesses, and questions below.",
        "",
        "## Structured Ordering Check",
        "",
        "The outcome score is only a reviewer signal: accept=3, minor revision=2, major revision=1, reject=0.",
        "It must not be treated as a scientific quality score without a paper-specific rubric.",
        "",
        "| Version | Recommendation | Confidence |",
        "| --- | --- | --- |",
    ]
    for label in ("v1", "v2", "v3"):
        recommendation, confidence = signals[label]
        report.append(f"| {label} | {recommendation} | {confidence}/5 |" if confidence is not None else f"| {label} | {recommendation} | unknown |")
    report += ["", f"Ordering status: **{ordering_status([signals[label] for label in ('v1', 'v2', 'v3')])}**."]
    for label in ("v1", "v2", "v3"):
        report += ["", f"## {label}", "", reviews[label]]
    report += ["", "## v1 to v2 Diff", "", "```diff"]
    report += list(difflib.unified_diff(reviews["v1"].splitlines(), reviews["v2"].splitlines(), fromfile="v1", tofile="v2"))
    report += ["```", "", "## v2 to v3 Diff", "", "```diff"]
    report += list(difflib.unified_diff(reviews["v2"].splitlines(), reviews["v3"].splitlines(), fromfile="v2", tofile="v3"))
    report += ["```", ""]
    (comparison / "comparison.md").write_text("\n".join(report))
    print(comparison.relative_to(ROOT))
    return 0


if __name__ == "__main__":
    sys.exit(main())
