#!/usr/bin/env python3
"""Review two or more paper versions with identical settings and compare the opinions."""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import difflib
import json
from pathlib import Path
import re
import subprocess
import sys

from osp_batch import ROOT, TRAIL_ROOT, osp_provenance, paper_name, resolve_model, sha256

VERSION_FILE_RE = re.compile(r"^v\d+[^/]*\.pdf$", re.IGNORECASE)


def latest_trail(paper: Path) -> Path:
    candidates = sorted((TRAIL_ROOT / paper_name(paper)).glob("*/brain/review/final_review.md"))
    if not candidates:
        raise FileNotFoundError(f"no final review found for {paper}")
    return candidates[-1].parents[2]


def validate_reused_trail(trail: Path, paper: Path, args: argparse.Namespace) -> None:
    manifest_path = trail / "manifest.json"
    if not manifest_path.is_file():
        raise FileNotFoundError(f"manifest.json missing from {trail}")
    manifest = json.loads(manifest_path.read_text())
    if not isinstance(manifest, dict):
        raise ValueError(f"manifest.json must contain an object: {manifest_path}")
    expected_model, expected_variant = resolve_model(args.llm, args.variant)
    try:
        manifest_model, manifest_variant = resolve_model(
            manifest.get("llm", ""), manifest.get("variant")
        )
    except (TypeError, ValueError) as error:
        raise ValueError(f"invalid model settings in {manifest_path}: {error}") from error
    expected = {
        "paper_sha256": sha256(paper),
        "venue": args.venue,
        "model": expected_model,
        "variant": expected_variant,
        "harness": args.harness,
    }
    actual = {
        "paper_sha256": manifest.get("paper_sha256"),
        "venue": manifest.get("venue"),
        "model": manifest_model,
        "variant": manifest_variant,
        "harness": manifest.get("harness"),
    }
    mismatches = [
        f"{key}: expected {value!r}, found {actual.get(key)!r}"
        for key, value in expected.items()
        if actual.get(key) != value
    ]
    if manifest.get("status") != "completed" or manifest.get("returncode") != 0:
        mismatches.append(
            f"status: expected completed with returncode 0, found "
            f"{manifest.get('status')!r} with returncode {manifest.get('returncode')!r}"
        )
    current_osp = osp_provenance()
    recorded_osp = manifest.get("osp")
    if not isinstance(recorded_osp, dict):
        mismatches.append("osp provenance: missing or invalid")
    elif recorded_osp.get("fork_commit") != current_osp.get("fork_commit"):
        mismatches.append(
            f"osp fork commit: expected {current_osp.get('fork_commit')!r}, "
            f"found {recorded_osp.get('fork_commit')!r}"
        )
    if current_osp.get("fork_dirty"):
        mismatches.append("osp fork: current working tree is dirty")
    if mismatches:
        raise ValueError(f"reused trail does not match requested settings: {'; '.join(mismatches)}")


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
        r"^##\s+(?:Decision\s+)?Recommendation\s*$([\s\S]*?)(?=^##\s|\Z)",
        text,
        re.MULTILINE | re.IGNORECASE,
    )
    recommendation = "unknown"
    if recommendation_match:
        recommendation_line = next(
            (line.strip() for line in recommendation_match.group(1).splitlines() if line.strip()),
            "",
        )
        recommendation = recommendation_line.strip("*.").lower()

    confidence_match = re.search(
        r"^##\s+Confidence\s*$([\s\S]*?)(?=^##\s|\Z)",
        text,
        re.MULTILINE | re.IGNORECASE,
    )
    confidence = None
    if confidence_match:
        value_match = re.search(
            r"^\s*(?:Confidence\s*:?\s*)?([1-5])(?:\s*/\s*5)?\s*$",
            confidence_match.group(1),
            re.MULTILINE | re.IGNORECASE,
        )
        if value_match:
            confidence = int(value_match.group(1))
    return recommendation, confidence


def recommendation_rank(recommendation: str) -> int:
    return {
        "reject": 0,
        "weak reject": 1,
        "major revision": 2,
        "borderline": 3,
        "minor revision": 4,
        "weak accept": 5,
        "accept": 6,
    }.get(recommendation, -1)


def ordering_status(
    signals: dict[str, tuple[str, int | None]], expected_order: list[str]
) -> str:
    """Summarize whether recommendation ranks increase along the expected order."""
    ranks = [recommendation_rank(signals[label][0]) for label in expected_order]
    if -1 in ranks:
        return "inconclusive (missing recommendation)"
    if all(ranks[i] < ranks[i + 1] for i in range(len(ranks) - 1)):
        return "strictly increasing (recommendation-only)"
    if any(ranks[i] > ranks[i + 1] for i in range(len(ranks) - 1)):
        return "not increasing"
    return "inconclusive (tied reviewer outcomes)"


def discover_versions(paper_dir: Path) -> list[tuple[str, Path]]:
    """Return [(label, path), ...] for v*.pdf files under a corpus directory."""
    candidates = sorted(
        path for path in paper_dir.glob("*.pdf")
        if VERSION_FILE_RE.match(path.name) and path.is_file()
    )
    return [(path.stem, path) for path in candidates]


def parse_versions(args: argparse.Namespace) -> list[tuple[str, Path]]:
    """Resolve the version list from whichever CLI form the caller used."""
    if args.versions and any((args.v1, args.v2, args.v3)):
        raise ValueError("--versions cannot be combined with --v1/--v2/--v3")
    if args.paper_dir and (args.versions or any((args.v1, args.v2, args.v3))):
        raise ValueError("--paper-dir cannot be combined with --versions or --v1/--v2/--v3")
    if args.versions:
        if len(args.versions) < 2:
            raise ValueError("--versions needs at least 2 PDFs")
        versions = [(Path(value).stem, ROOT / Path(value)) for value in args.versions]
    elif args.paper_dir:
        versions = discover_versions(ROOT / Path(args.paper_dir))
        if len(versions) < 2:
            raise ValueError(f"no version PDFs (v*.pdf) found under {args.paper_dir}")
    elif args.v1 and args.v2 and args.v3:
        versions = [("v1", ROOT / args.v1), ("v2", ROOT / args.v2), ("v3", ROOT / args.v3)]
    else:
        raise ValueError(
            "specify versions with --versions PDF [PDF ...], --paper-dir DIR, "
            "or the classic --v1/--v2/--v3"
        )
    labels = [label for label, _ in versions]
    if len(set(labels)) != len(labels):
        raise ValueError(f"duplicate version labels: {labels}")
    missing = [str(path) for _, path in versions if not path.is_file()]
    if missing:
        raise ValueError("missing version PDF(s): " + ", ".join(missing))
    return versions


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--v1", type=Path, help="first version PDF (classic three-version form)")
    parser.add_argument("--v2", type=Path, help="second version PDF (classic three-version form)")
    parser.add_argument("--v3", type=Path, help="third version PDF (classic three-version form)")
    parser.add_argument("--versions", nargs="+", help="two or more version PDFs, in order")
    parser.add_argument("--paper-dir", help="corpus directory whose v*.pdf files are the versions")
    parser.add_argument("--name", help="comparison name, e.g. erdos973 (default: versions' parent dir)")
    parser.add_argument("--expected-order", help="comma-separated labels in expected quality order, e.g. v1,v2,v3")
    parser.add_argument("--venue", default="arxiv")
    parser.add_argument("--llm", default="openai/gpt-5.6-sol")
    parser.add_argument("--variant", default="medium")
    parser.add_argument("--harness", default="opencode")
    parser.add_argument("--trail-repo")
    parser.add_argument("--reuse", action="store_true", help="compare the latest existing trails without rerunning reviews")
    args = parser.parse_args()

    try:
        versions = parse_versions(args)
    except ValueError as error:
        parser.error(str(error))

    labels = [label for label, _ in versions]
    expected_order = labels
    if args.expected_order:
        expected_order = [label.strip() for label in args.expected_order.split(",") if label.strip()]
        unknown = [label for label in expected_order if label not in labels]
        if unknown:
            parser.error(f"--expected-order references unknown labels: {', '.join(unknown)}")
        if len(set(expected_order)) != len(expected_order):
            parser.error("--expected-order must not repeat labels")
    else:
        expected_order = labels

    trails: dict[str, Path] = {}
    failures = []
    if args.reuse:
        for label, path in versions:
            try:
                trail = latest_trail(path)
                validate_reused_trail(trail, path, args)
                trails[label] = trail
            except (FileNotFoundError, ValueError, TypeError, AttributeError, json.JSONDecodeError) as error:
                failures.append(f"{label}: {error}")
    else:
        with ThreadPoolExecutor(max_workers=len(versions)) as executor:
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

    name = args.name or versions[0][1].parent.name
    comparison = TRAIL_ROOT / f"{name}-comparison" / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    comparison.mkdir(parents=True)
    reviews = {label: (trail / "brain" / "review" / "final_review.md").read_text() for label, trail in trails.items()}
    signals = {label: review_signals(reviews[label]) for label in labels}
    for label, text in reviews.items():
        (comparison / f"{label}_review.md").write_text(text)
    report = [
        f"# {name} Version Comparison",
        "",
        "This report compares reviews generated with identical settings.",
        "",
        f"- Venue: {args.venue}",
        f"- LLM: {args.llm}",
        f"- Variant: {args.variant or 'none'}",
        f"- Harness: {args.harness}",
        f"- OSP provenance: {osp_provenance()}",
        "",
        "## Expected Ordering",
        "",
        "The expected quality progression is `" + " < ".join(expected_order) + "`.",
        "Inspect the decision, confidence, strengths, weaknesses, and questions below.",
        "",
        "## Structured Ordering Check",
        "",
        "The ordering signal ranks recommendations from reject to accept; it is recommendation-only, not a scientific quality score.",
        "It must not be treated as a scientific quality score without a paper-specific rubric.",
        "",
        "| Version | Recommendation | Confidence |",
        "| --- | --- | --- |",
    ]
    for label in labels:
        recommendation, confidence = signals[label]
        report.append(f"| {label} | {recommendation} | {confidence}/5 |" if confidence is not None else f"| {label} | {recommendation} | unknown |")
    report += ["", "## Source Trails", ""]
    report += [f"- {label}: `{trails[label].relative_to(ROOT)}`" for label in labels]
    report += ["", f"Ordering status: **{ordering_status(signals, expected_order)}**."]
    for label in labels:
        report += ["", f"## {label}", "", reviews[label]]
    for first, second in zip(labels, labels[1:]):
        report += ["", f"## {first} to {second} Diff", "", "```diff"]
        report += list(
            difflib.unified_diff(
                reviews[first].splitlines(), reviews[second].splitlines(),
                fromfile=first, tofile=second,
            )
        )
        report += ["```", ""]
    (comparison / "comparison.md").write_text("\n".join(report))
    if args.trail_repo and not args.reuse:
        upload = subprocess.run(
            [
                "hf", "upload", args.trail_repo, str(comparison),
                f"osp-trails/{name}-comparison/{comparison.name}",
                "--type", "dataset", "--private",
                "--commit-message", f"Add OSP comparison {comparison.name}",
            ],
            cwd=ROOT, capture_output=True, text=True,
        )
        (comparison / "upload.log").write_text(upload.stdout + upload.stderr)
        if upload.returncode:
            print("comparison upload failed", file=sys.stderr)
            return upload.returncode
    print(comparison.relative_to(ROOT))
    return 0


if __name__ == "__main__":
    sys.exit(main())