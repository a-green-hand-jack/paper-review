#!/usr/bin/env python3
"""Run Open ScholarPeer once per paper and preserve every run."""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TRAIL_ROOT = ROOT / "osp-trails"
FORK_ROOT = Path(__file__).resolve().parents[2] / "open-scholar-peer"


def timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def osp_provenance() -> dict[str, str | bool | None]:
    fork_dir = Path(os.environ.get("OSP_FORK_DIR", FORK_ROOT))
    if not (fork_dir / ".git").exists():
        return {"fork_dir": str(fork_dir), "fork_commit": None, "fork_dirty": None}
    commit = subprocess.run(
        ["git", "-C", str(fork_dir), "rev-parse", "HEAD"],
        capture_output=True, text=True, check=False,
    )
    dirty = subprocess.run(
        ["git", "-C", str(fork_dir), "status", "--porcelain"],
        capture_output=True, text=True, check=False,
    )
    return {
        "fork_dir": str(fork_dir),
        "fork_commit": commit.stdout.strip() if commit.returncode == 0 else None,
        "fork_dirty": bool(dirty.stdout) if dirty.returncode == 0 else None,
    }


def papers() -> list[Path]:
    return sorted(
        path
        for path in (ROOT / "papers").glob("**/*.pdf")
        if path.is_file() and "figures" not in path.parts and not path.name.startswith("fig-")
    )


def paper_name(path: Path) -> str:
    relative = path.relative_to(ROOT / "papers")
    return relative.with_suffix("").as_posix().replace("/", "__").replace("_", "-").lower()


def make_workspace(run_dir: Path, paper: Path, venue: str) -> Path:
    workspace = run_dir / "workspace"
    brain_input = workspace / ".brain" / "input"
    brain_input.mkdir(parents=True)
    shutil.copy2(paper, brain_input / paper.name)
    session = json.loads((ROOT / ".brain" / "session.json").read_text())
    session["paper"] = {
        "title": paper.stem,
        "path": str(Path(".brain") / "input" / paper.name),
        "parsed_path": str(Path(".brain") / "input" / "paper.md"),
        "type": paper.suffix.lstrip("."),
    }
    session["venue"] = {"name": venue, "year": "", "source_url": "", "criteria_source": "pending"}
    (workspace / ".brain" / "session.json").write_text(json.dumps(session, indent=2) + "\n")
    shutil.copytree(ROOT / ".claude", workspace / ".claude")
    shutil.copytree(ROOT / "docs", workspace / "docs")
    shutil.copy2(ROOT / ".mcp.json", workspace / ".mcp.json")
    shutil.copy2(ROOT / "AGENTS.md", workspace / "AGENTS.md")
    return workspace


def resolve_model(llm: str, variant: str | None) -> tuple[str, str | None]:
    if llm == "gpt-5.6-sol-medium":
        if variant not in (None, "medium"):
            raise ValueError("--llm gpt-5.6-sol-medium cannot be combined with a non-medium --variant")
        return "openai/gpt-5.6-sol", "medium"
    if "/" not in llm:
        raise ValueError("--llm must be provider/model, for example openai/gpt-5.6-sol")
    return llm, variant


def upload_trail(run_dir: Path, paper_name_value: str, trail_repo: str) -> tuple[int, str]:
    destination = f"osp-trails/{paper_name_value}/{run_dir.name}"
    command = [
        "hf", "upload", trail_repo, str(run_dir), destination,
        "--type", "dataset", "--private", "--exclude", "workspace/**",
        "--commit-message", f"Add OSP trail {paper_name_value}/{run_dir.name}",
    ]
    result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
    return result.returncode, result.stdout + result.stderr


def upload_file(path: Path, destination: str, trail_repo: str, message: str) -> tuple[int, str]:
    command = [
        "hf", "upload", trail_repo, str(path), destination,
        "--type", "dataset", "--private",
        "--commit-message", message,
    ]
    result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
    return result.returncode, result.stdout + result.stderr


def run_one(
    paper: Path, venue: str, llm: str, variant: str | None, harness: str,
    trail_repo: str | None, upload: bool, execute: bool,
) -> int:
    name = paper_name(paper)
    run_dir = TRAIL_ROOT / name / timestamp()
    workspace = run_dir / "workspace"
    if harness != "opencode":
        raise ValueError("unsupported --harness; currently supported: opencode")
    provider_model, resolved_variant = resolve_model(llm, variant)
    command = [
        "opencode",
        "run",
        "--dir",
        str(workspace),
        "--model",
        provider_model,
    ]
    if resolved_variant:
        command += ["--variant", resolved_variant]
    command += [
        "Use Open ScholarPeer to complete the full review of the paper in this workspace. "
        f"The review venue is {venue}. Execute the numbered OSP phases in order; do not "
        "only report the dispatcher status, and do not process any other paper.",
    ]
    if not execute:
        print(f"DRY-RUN {name}: {' '.join(command)}")
        if upload:
            print(f"DRY-RUN upload: {trail_repo}/osp-trails/{name}/<timestamp>")
        return 0

    run_dir.mkdir(parents=True)
    log_path = run_dir / "opencode.log"
    manifest = {
        "schema_version": 1,
        "paper": str(paper.relative_to(ROOT)),
        "paper_sha256": sha256(paper),
        "venue": venue,
        "llm": llm,
        "variant": resolved_variant,
        "harness": harness,
        "provider": provider_model.split("/", 1)[0],
        "started_at": datetime.now(timezone.utc).isoformat(),
        "status": "created",
        "trail": str(run_dir.relative_to(ROOT)),
        "command": command,
        "trail_repo": trail_repo,
        "upload_status": "pending" if upload else "not requested",
    }
    manifest["osp"] = osp_provenance()
    manifest_path = run_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
    result = None
    try:
        with log_path.open("w") as log:
            workspace = make_workspace(run_dir, paper, venue)
            result = subprocess.run(command, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, text=True)
        final_review = workspace / ".brain" / "review" / "final_review.md"
        successful_review = result is not None and result.returncode == 0 and final_review.is_file()
        manifest["status"] = "completed" if successful_review else "failed"
        if result is not None:
            manifest["returncode"] = result.returncode
        if result is not None and result.returncode == 0 and not successful_review:
            manifest["error"] = "OpenCode exited successfully but final_review.md was not produced"
        if (workspace / ".brain").exists():
            shutil.copytree(workspace / ".brain", run_dir / "brain", dirs_exist_ok=True)
    except Exception as error:
        with log_path.open("a") as log:
            log.write(f"setup or execution failed: {error!r}\n")
        manifest["status"] = "failed"
        manifest["error"] = repr(error)
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
    if upload:
        try:
            code, output = upload_trail(run_dir, name, trail_repo)
            manifest["upload_status"] = "uploaded" if code == 0 else "failed"
            if code:
                manifest["upload_error"] = f"hf upload exited with code {code}"
            (run_dir / "upload.log").write_text(output)
        except Exception as error:
            code = 1
            manifest["upload_status"] = "failed"
            manifest["upload_error"] = repr(error)
            (run_dir / "upload.log").write_text(f"hf upload failed: {error!r}\n")
        manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
        if code == 0:
            try:
                log_code, log_output = upload_file(
                    run_dir / "upload.log",
                    f"osp-trails/{name}/{run_dir.name}/upload.log",
                    trail_repo,
                    f"Add OSP upload log {name}/{run_dir.name}",
                )
                with (run_dir / "upload.log").open("a") as log:
                    log.write(log_output)
            except Exception as error:
                log_code = 1
                with (run_dir / "upload.log").open("a") as log:
                    log.write(f"upload log failed: {error!r}\n")
            if log_code:
                manifest["upload_status"] = "failed"
                manifest["upload_error"] = f"upload log exited with code {log_code}"
                code = log_code
                manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
            else:
                manifest["upload_status"] = "uploaded"
                manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
                try:
                    manifest_code, manifest_output = upload_file(
                        manifest_path,
                        f"osp-trails/{name}/{run_dir.name}/manifest.json",
                        trail_repo,
                        f"Finalize OSP trail manifest {name}/{run_dir.name}",
                    )
                    with (run_dir / "upload.log").open("a") as log:
                        log.write(manifest_output)
                except Exception as error:
                    manifest_code = 1
                    with (run_dir / "upload.log").open("a") as log:
                        log.write(f"manifest upload failed: {error!r}\n")
                if manifest_code:
                    manifest["upload_status"] = "failed"
                    manifest["upload_error"] = f"manifest upload exited with code {manifest_code}"
                    code = manifest_code
                    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
    status = manifest["status"].upper()
    if upload and manifest["upload_status"] != "uploaded":
        status = "FAILED"
    print(f"{status} {name}: {run_dir.relative_to(ROOT)}")
    archive_failed = upload and manifest["upload_status"] != "uploaded"
    return 0 if manifest["status"] == "completed" and not archive_failed else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--venue", default="arxiv", help="review venue (default: arxiv)")
    parser.add_argument("--llm", default="openai/gpt-5.6-sol", help="provider/model")
    parser.add_argument("--variant", default="medium", help="model variant, or omit it")
    parser.add_argument("--harness", default="opencode", help="agent harness (default: opencode)")
    parser.add_argument("--paper", action="append", help="relative paper PDF; repeat for multiple papers")
    parser.add_argument("--all", action="store_true", help="process all manuscript PDFs")
    parser.add_argument("--trail-repo", help="Hugging Face private dataset repository")
    parser.add_argument("--upload", action="store_true", help="upload each trail to --trail-repo")
    parser.add_argument("--execute", action="store_true", help="actually invoke opencode")
    parser.add_argument("--workers", type=int, default=4, help="parallel papers (default: 4)")
    args = parser.parse_args()
    if args.upload and not args.trail_repo:
        parser.error("--upload requires --trail-repo NAMESPACE/DATASET")
    available = papers()
    selected = available if args.all or not args.paper else [ROOT / path for path in args.paper]
    invalid = [path for path in selected if path not in available]
    if invalid:
        parser.error("not manuscript PDFs under papers/: " + ", ".join(str(path) for path in invalid))
    if not selected:
        parser.error("no manuscript PDFs found under papers/")
    if args.workers < 1:
        parser.error("--workers must be at least 1")
    if args.harness != "opencode":
        parser.error("unsupported --harness; currently supported: opencode")
    try:
        resolve_model(args.llm, args.variant)
    except ValueError as error:
        parser.error(str(error))
    failures = 0
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = {
            executor.submit(
                run_one, path, args.venue, args.llm, args.variant, args.harness,
                args.trail_repo, args.upload, args.execute,
            ): path
            for path in selected
        }
        for future in as_completed(futures):
            path = futures[future]
            try:
                failures += future.result() != 0
            except Exception as error:
                failures += 1
                print(f"FAILED {path.relative_to(ROOT)}: {error}", file=sys.stderr)
    if not args.execute:
        print(f"Prepared {len(selected)} isolated runs. Add --execute to invoke OpenCode.")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
