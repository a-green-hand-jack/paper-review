#!/usr/bin/env python3
"""Run Open ScholarPeer once per paper and preserve every run."""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TRAIL_ROOT = ROOT / "osp-trails"


def timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def papers() -> list[Path]:
    return sorted(
        path
        for path in (ROOT / "papers").glob("**/*.pdf")
        if path.is_file() and "figures" not in path.parts and not path.name.startswith("fig-")
    )


def paper_name(path: Path) -> str:
    relative = path.relative_to(ROOT / "papers")
    return relative.with_suffix("").as_posix().replace("/", "__").replace("_", "-").lower()


def make_workspace(run_dir: Path, paper: Path) -> Path:
    workspace = run_dir / "workspace"
    brain_input = workspace / ".brain" / "input"
    brain_input.mkdir(parents=True)
    shutil.copy2(paper, brain_input / paper.name)
    shutil.copytree(ROOT / ".claude", workspace / ".claude")
    shutil.copy2(ROOT / ".mcp.json", workspace / ".mcp.json")
    shutil.copy2(ROOT / "AGENTS.md", workspace / "AGENTS.md")
    return workspace


def resolve_model(model: str) -> tuple[str, str]:
    if model == "gpt-5.6-sol-medium":
        return "openai/gpt-5.6-sol", "medium"
    raise ValueError("unsupported model; currently supported: gpt-5.6-sol-medium")


def run_one(paper: Path, venue: str, model: str, execute: bool) -> int:
    name = paper_name(paper)
    run_dir = TRAIL_ROOT / name / timestamp()
    workspace = run_dir / "workspace"
    provider_model, variant = resolve_model(model)
    command = [
        "opencode",
        "run",
        "--dir",
        str(workspace),
        "--model",
        provider_model,
        "--variant",
        variant,
        "Use Open ScholarPeer to complete the full review of the paper in this workspace. "
        f"The review venue is {venue}. Execute the numbered OSP phases in order; do not "
        "only report the dispatcher status, and do not process any other paper.",
    ]
    if not execute:
        print(f"DRY-RUN {name}: {' '.join(command)}")
        return 0

    run_dir.mkdir(parents=True)
    manifest = {
        "schema_version": 1,
        "paper": str(paper.relative_to(ROOT)),
        "paper_sha256": sha256(paper),
        "venue": venue,
        "model": model,
        "provider": "openai",
        "started_at": datetime.now(timezone.utc).isoformat(),
        "status": "created",
        "trail": str(run_dir.relative_to(ROOT)),
        "command": command,
    }
    manifest_path = run_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
    try:
        workspace = make_workspace(run_dir, paper)
        log_path = run_dir / "opencode.log"
        with log_path.open("w") as log:
            result = subprocess.run(command, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, text=True)
        final_review = workspace / ".brain" / "review" / "final_review.md"
        successful_review = result.returncode == 0 and final_review.is_file()
        manifest["status"] = "completed" if successful_review else "failed"
        manifest["returncode"] = result.returncode
        if result.returncode == 0 and not successful_review:
            manifest["error"] = "OpenCode exited successfully but final_review.md was not produced"
        if (workspace / ".brain").exists():
            shutil.copytree(workspace / ".brain", run_dir / "brain", dirs_exist_ok=True)
    except Exception as error:
        manifest["status"] = "failed"
        manifest["error"] = repr(error)
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"{manifest['status'].upper()} {name}: {run_dir.relative_to(ROOT)}")
    return 0 if manifest["status"] == "completed" else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--venue", required=True, help="review venue, for example arXiv-only")
    parser.add_argument("--model", default="gpt-5.6-sol-medium")
    parser.add_argument("--paper", help="relative paper PDF; omit to process all papers")
    parser.add_argument("--execute", action="store_true", help="actually invoke opencode")
    args = parser.parse_args()
    selected = papers()
    if args.paper:
        selected = [ROOT / args.paper]
        if selected[0] not in papers():
            parser.error(f"not a manuscript PDF under papers/: {args.paper}")
    if not selected:
        parser.error("no manuscript PDFs found under papers/")
    failures = 0
    for path in selected:
        try:
            failures += run_one(path, args.venue, args.model, args.execute) != 0
        except Exception as error:
            failures += 1
            print(f"FAILED {path.relative_to(ROOT)}: {error}", file=sys.stderr)
    if not args.execute:
        print(f"Prepared {len(selected)} isolated runs. Add --execute to invoke OpenCode.")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
