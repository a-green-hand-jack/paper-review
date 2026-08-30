#!/usr/bin/env python3
"""Review three paper versions with identical settings and compare the opinions."""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import difflib
from pathlib import Path
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
    args = parser.parse_args()
    versions = [("v1", ROOT / args.v1), ("v2", ROOT / args.v2), ("v3", ROOT / args.v3)]
    missing = [str(path) for _, path in versions if not path.is_file()]
    if missing:
        parser.error("missing version PDF(s): " + ", ".join(missing))

    trails: dict[str, Path] = {}
    failures = []
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
    ]
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
