"""Identify the build that archived a trail, without naming the host.

A trail is evidence, and the archiver is part of the chain that produced it: it
decides what is copied and what is scrubbed. Two trails whose manifests both say
`schema_version: 2` can still have been written by builds with different scrub
rules, so the manifest has to say which build ran.

Everything here is best effort and never raises. Failing to identify the
archiver is worth a warning, not a refusal to archive a completed run -- the
alternative is losing the run.

One rule constrains the whole module: a locally installed package records its
own filesystem path in PEP 610 metadata, and that path names the contributor's
machine. The commit is provenance; the path is a host detail of exactly the kind
`trail.py` exists to strip. So a local checkout reports its commit and never its
location.
"""

from __future__ import annotations

import json
import subprocess
from importlib.metadata import Distribution, PackageNotFoundError
from pathlib import Path

DISTRIBUTION = "paper-review-harbor"

#: Long enough for a cold index, short enough not to stall an archive.
GIT_TIMEOUT = 10


def _git(directory: Path, *args: str) -> str | None:
    try:
        result = subprocess.run(
            ["git", "-C", str(directory), *args],
            capture_output=True,
            text=True,
            timeout=GIT_TIMEOUT,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if result.returncode:
        return None
    return result.stdout.strip()


def _checkout_source() -> dict[str, object]:
    """Describe the checkout this package is imported from, path excluded."""
    directory = Path(__file__).resolve().parent
    commit = _git(directory, "rev-parse", "HEAD")
    if commit is None:
        return {"kind": "unknown"}
    status = _git(directory, "status", "--porcelain")
    return {
        "kind": "local-checkout",
        "commit": commit,
        # `None` would claim the tree was clean; unknown is the honest answer.
        "dirty": bool(status) if status is not None else None,
    }


def _direct_url() -> dict | None:
    try:
        raw = Distribution.from_name(DISTRIBUTION).read_text("direct_url.json")
    except (PackageNotFoundError, OSError):
        return None
    if not raw:
        return None
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, dict) else None


def _version() -> str | None:
    try:
        return Distribution.from_name(DISTRIBUTION).version
    except (PackageNotFoundError, OSError):
        from . import __version__

        return __version__


def archiver_source() -> dict[str, object]:
    """Where this build came from: a published commit, a checkout, or unknown."""
    direct = _direct_url()
    if direct is None:
        # No PEP 610 record: an ordinary release install, or an import from a
        # tree that was never installed. A checkout can still identify itself.
        checkout = _checkout_source()
        return checkout if checkout["kind"] != "unknown" else {"kind": "release"}

    vcs = direct.get("vcs_info")
    url = direct.get("url")
    if isinstance(vcs, dict) and vcs.get("commit_id"):
        source: dict[str, object] = {
            "kind": "vcs",
            "commit": str(vcs["commit_id"]),
            "requested_revision": vcs.get("requested_revision"),
        }
        # A `file://` remote is a local clone; its URL is a host path.
        if isinstance(url, str) and not url.startswith("file://"):
            source["url"] = url
        return source

    # Editable or local-directory install. `url` is this machine's path, so it
    # is deliberately dropped and the commit is read from the checkout instead.
    return _checkout_source()


def archiver_provenance() -> dict[str, object]:
    """The `archiver` block written into every trail manifest."""
    return {
        "name": DISTRIBUTION,
        "version": _version(),
        "source": archiver_source(),
    }


def provenance_warnings(provenance: dict[str, object]) -> list[str]:
    """Say when a trail cannot be traced back to a specific published build."""
    source = provenance.get("source")
    if not isinstance(source, dict):
        return ["the archiver could not identify itself"]
    kind = source.get("kind")
    warnings: list[str] = []
    if kind == "vcs":
        if not source.get("requested_revision"):
            warnings.append(
                "archiver installed from an unpinned revision; "
                "pin `@<tag>` so this trail names the build that wrote it"
            )
    elif kind == "local-checkout":
        warnings.append("archiver running from a local checkout, not a published build")
        if source.get("dirty"):
            warnings.append("archiver checkout has uncommitted changes")
        elif source.get("dirty") is None:
            warnings.append("archiver checkout state could not be determined")
    else:
        warnings.append(f"archiver build is not traceable to a commit (kind: {kind})")
    return warnings
