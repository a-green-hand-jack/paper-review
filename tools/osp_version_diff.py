#!/usr/bin/env python3
"""Compare two OSP versions across a trail corpus on deterministic criteria only.

Sampling noise makes single-run recommendation labels unusable as evidence: a
prior audit found four papers whose recommendation moved a full grade while the
cited facts were unchanged. This tool therefore reports only properties that are
true or false by inspection of the artifacts -- whether a field was written,
whether a forbidden phrase appears, whether a required section exists -- and
deliberately does not compare recommendations or scores.

Trails are split into the two versions by timestamp: runs before --cutoff are
the baseline, runs at or after it are the candidate.

Usage:
    python3 tools/osp_version_diff.py --cutoff 20260831T074424
    python3 tools/osp_version_diff.py --cutoff ... --json out.json
"""
from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TRAIL_ROOT = ROOT / "osp-trails"

# Question vocabulary that the domain profiles' anti-pattern lists forbid for
# non-empirical papers. Counted inside Q&A questions only, never inside answers:
# an answer may legitimately say "the paper reports no baselines" while a
# question asking "what baselines were used" is the failure being measured.
ML_QUESTION_TERMS = re.compile(
    r"\b(baselines?|ablations?|datasets?|hyper-?parameters?|benchmarks?|"
    r"SOTA|state[- ]of[- ]the[- ]art|leaderboards?)\b",
    re.IGNORECASE,
)

# A numeric token: integers, decimals, powers, percentages, scientific notation.
NUMERIC = re.compile(r"(?<![\w.])[-+]?\d+(?:\.\d+)?(?:\s*[eE^]\s*[-+]?\d+)?%?")

DUAL_AXIS = re.compile(r"\*\*(Significance|Strength of evidence)\*\*", re.IGNORECASE)
OLD_AXIS = re.compile(r"##\s*(Decision recommendation|Confidence)\b", re.IGNORECASE)


def read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def evidence_block(summary: str) -> str:
    """The third component of the structured summary, whatever it is called."""
    m = re.search(
        r"^###\s+(Evidence|Formal Content).*?$(.*?)(?=^##\s|\Z)",
        summary,
        re.MULTILINE | re.DOTALL,
    )
    return m.group(2) if m else ""


def questions_only(qa_text: str) -> str:
    """Q&A files interleave questions and answers; measure questions alone."""
    return "\n".join(
        re.findall(r"^###\s*Q\d+.*?$(.*?)(?=^\*\*Answer|^###|\Z)",
                   qa_text, re.MULTILINE | re.DOTALL)
    ) or "\n".join(
        line for line in qa_text.splitlines()
        if line.lstrip().startswith(("### Q", "**Q", "Q:"))
    )


def probe(trail: Path) -> dict:
    brain = trail / "brain"
    session_raw = read(brain / "session.json")
    try:
        paper = json.loads(session_raw).get("paper", {}) if session_raw else {}
    except json.JSONDecodeError:
        paper = {}

    summary = read(brain / "raw" / "01_structured_summary.md")
    ev = evidence_block(summary)

    qa_files = sorted((brain / "raw").glob("05_qa_*.md"))
    qa_questions = "\n".join(questions_only(read(p)) for p in qa_files)

    review = read(brain / "review" / "final_review.md")

    return {
        "domain_profile": paper.get("domain_profile") or "",
        "numerical_slice": bool(paper.get("numerical_slice")),
        "review_mode": paper.get("review_mode") or "",
        # Extraction contract: how many named fields the evidence section carries
        "evidence_fields": len(re.findall(r"^\s*-\s+\*\*[^*]+\*\*", ev, re.MULTILINE)),
        # Quantitative capture: distinct numeric tokens surviving into the summary
        "evidence_numbers": len(set(NUMERIC.findall(ev))),
        "evidence_not_stated": len(re.findall(r"not stated", ev, re.IGNORECASE)),
        # Anti-pattern suppression, measured on questions only
        "qa_files": len(qa_files),
        "ml_terms_in_questions": len(ML_QUESTION_TERMS.findall(qa_questions)),
        # Output vocabulary and export gate
        "has_dual_axis": bool(DUAL_AXIS.search(review)),
        "has_old_axis": bool(OLD_AXIS.search(review)),
        "has_red_lines": bool(re.search(r"^##\s*Red lines", review, re.MULTILINE)),
        "has_not_checked": bool(re.search(r"^##\s*What was not checked", review, re.MULTILINE)),
        "review_written": bool(review.strip()),
    }


def status_of(trail: Path) -> str:
    try:
        return json.loads(read(trail / "manifest.json")).get("status", "?")
    except json.JSONDecodeError:
        return "?"


def collect(cutoff: str) -> dict[str, dict[str, dict]]:
    """paper -> {"baseline": probe, "candidate": probe} using the latest run of each side."""
    out: dict[str, dict[str, dict]] = defaultdict(dict)
    for manifest in sorted(TRAIL_ROOT.glob("*/*/manifest.json")):
        trail = manifest.parent
        stamp = trail.name
        paper = trail.parent.name
        if status_of(trail) != "completed":
            continue
        side = "candidate" if stamp >= cutoff else "baseline"
        # Later run of the same side wins; glob is sorted so this keeps the latest.
        out[paper][side] = probe(trail)
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--cutoff", required=True,
                    help="trail timestamp separating baseline from candidate, e.g. 20260831T074424")
    ap.add_argument("--json", help="also write the full table here")
    args = ap.parse_args()

    if not TRAIL_ROOT.is_dir():
        print(f"no trails at {TRAIL_ROOT}")
        return 2

    data = collect(args.cutoff)
    paired = {k: v for k, v in data.items() if "baseline" in v and "candidate" in v}

    print(f"\n{len(data)} papers with completed runs; {len(paired)} have both sides.\n")
    if not paired:
        print("Nothing to compare yet.")
        return 0

    hdr = f"{'paper':<34} {'profile':<10} {'fields':>11} {'numbers':>11} {'ML-in-Q':>11}"
    print(hdr)
    print("-" * len(hdr))

    tot = defaultdict(lambda: [0, 0])
    for paper in sorted(paired):
        b, c = paired[paper]["baseline"], paired[paper]["candidate"]
        prof = c["domain_profile"] + ("+num" if c["numerical_slice"] else "")
        for key in ("evidence_fields", "evidence_numbers", "ml_terms_in_questions"):
            tot[key][0] += b[key]
            tot[key][1] += c[key]
        print(f"{paper[:34]:<34} {prof or '-':<10} "
              f"{b['evidence_fields']:>4} → {c['evidence_fields']:<4} "
              f"{b['evidence_numbers']:>4} → {c['evidence_numbers']:<4} "
              f"{b['ml_terms_in_questions']:>4} → {c['ml_terms_in_questions']:<4}")

    print("-" * len(hdr))
    print(f"{'TOTAL':<34} {'':<10} "
          f"{tot['evidence_fields'][0]:>4} → {tot['evidence_fields'][1]:<4} "
          f"{tot['evidence_numbers'][0]:>4} → {tot['evidence_numbers'][1]:<4} "
          f"{tot['ml_terms_in_questions'][0]:>4} → {tot['ml_terms_in_questions'][1]:<4}")

    routed = sum(1 for p in paired.values() if p["candidate"]["domain_profile"])
    hybrid = sum(1 for p in paired.values() if p["candidate"]["numerical_slice"])
    dual = sum(1 for p in paired.values() if p["candidate"]["has_dual_axis"])
    old = sum(1 for p in paired.values() if p["candidate"]["has_old_axis"])
    redl = sum(1 for p in paired.values() if p["candidate"]["has_red_lines"])
    notck = sum(1 for p in paired.values() if p["candidate"]["has_not_checked"])
    ns = sum(p["candidate"]["evidence_not_stated"] for p in paired.values())

    n = len(paired)
    print(f"""
Candidate-side structural checks (n={n}):
  domain profile routed        {routed}/{n}
  numerical-slice overlay      {hybrid}/{n}
  dual-axis assessment         {dual}/{n}
  legacy Decision/Confidence   {old}/{n}   (expected 0)
  "Red lines" section          {redl}/{n}
  "What was not checked"       {notck}/{n}
  fields marked `not stated`   {ns} total  (gaps recorded rather than dropped)

Not measured on purpose: recommendation, scores, review length. Single-run
labels are not evidence -- run N>1 per configuration and compare distributions.
""")

    if args.json:
        Path(args.json).write_text(json.dumps(paired, indent=2) + "\n")
        print(f"full table → {args.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
