from __future__ import annotations

import json

import pytest

from paper_review_harbor import provenance
from paper_review_harbor.trail import (
    TrailError,
    archive_harbor_trial,
    archive_trail,
    upload_trail,
)


def test_archive_trail_is_timestamped_and_excludes_workspace(tmp_path) -> None:
    run = tmp_path / "run"
    (run / "logs" / "agent").mkdir(parents=True)
    (run / "workspace" / "submission").mkdir(parents=True)
    (run / "workspace" / "submission" / "review.md").write_text("review")
    (run / "logs" / "agent" / "trajectory.json").write_text("{}")
    (run / ".env").write_text("SECRET=x")
    trail = archive_trail(run, tmp_path / "trails", task_id="task", task_revision="abc")
    manifest = json.loads((trail / "trail-manifest.json").read_text())
    assert manifest["task_revision"] == "abc"
    assert (trail / "review.md").is_file()
    assert not (trail / ".env").exists()


def test_upload_trail_includes_revision(tmp_path, monkeypatch) -> None:
    trail = tmp_path / "task" / "run"
    trail.mkdir(parents=True)
    (trail / "trail-manifest.json").write_text("{}")
    monkeypatch.setattr("paper_review_harbor.trail.shutil.which", lambda _: "/usr/bin/hf")
    command = upload_trail(trail, "org/trails", revision="release-v1")
    assert "--revision release-v1" in command


def test_archive_trail_rejects_path_escape(tmp_path) -> None:
    run = tmp_path / "run"
    (run / "workspace" / "submission").mkdir(parents=True)
    (run / "workspace" / "submission" / "review.md").write_text("review")
    try:
        archive_trail(run, tmp_path / "trails", task_id="../outside", task_revision="abc")
    except TrailError:
        pass
    else:
        raise AssertionError("unsafe task id was accepted")


def test_archive_harbor_trial_keeps_required_provenance_and_brain(tmp_path) -> None:
    trial = tmp_path / "trial"
    review = trial / "artifacts" / "workspace" / "submission" / "review.md"
    review.parent.mkdir(parents=True)
    review.write_text("review")
    (trial / "artifacts" / "workspace" / ".brain" / "review").mkdir(parents=True)
    (trial / "artifacts" / "workspace" / ".brain" / "review" / "final_review.md").write_text(
        "full review"
    )
    (trial / "artifacts" / "workspace" / "material-manifest.json").write_text("{}")
    (trial / "artifacts" / "manifest.json").write_text("{}")
    (trial / "config.json").write_text("{}")
    (trial / "lock.json").write_text("{}")
    trail = archive_harbor_trial(trial, tmp_path / "trails", task_id="task", task_revision="sha")
    assert (trail / "input" / "material-manifest.json").is_file()
    assert (trail / "brain" / "review" / "final_review.md").is_file()


def test_archive_harbor_trial_rejects_secret_metadata(tmp_path) -> None:
    trial = tmp_path / "trial"
    review = trial / "artifacts" / "workspace" / "submission" / "review.md"
    review.parent.mkdir(parents=True)
    review.write_text("review")
    (trial / "artifacts" / "workspace" / "material-manifest.json").write_text("{}")
    (trial / "artifacts" / "manifest.json").write_text("{}")
    (trial / "config.json").write_text("{}")
    (trial / "lock.json").write_text("{}")
    with pytest.raises(TrailError, match="possible secret"):
        archive_harbor_trial(
            trial,
            tmp_path / "trails",
            task_id="task",
            task_revision="sha",
            metadata={"nested": {"token": "sk-abcdefghijklmnopqrst"}},
        )


def test_archive_harbor_trial_skips_binary_runtime_state(tmp_path) -> None:
    trial = tmp_path / "trial"
    review = trial / "artifacts" / "workspace" / "submission" / "review.md"
    review.parent.mkdir(parents=True)
    review.write_text("review")
    (trial / "artifacts" / "workspace" / "material-manifest.json").write_text("{}")
    (trial / "artifacts" / "manifest.json").write_text("{}")
    (trial / "config.json").write_text("{}")
    (trial / "lock.json").write_text("{}")
    # opencode runtime state: binary sqlite would accidentally match SECRET_RE,
    # and git template hooks contain innocent text like "use IPC::Open2". Both
    # must be excluded from the archived trail.
    xdg = trial / "agent" / "opencode" / "xdg-data" / "opencode"
    (xdg / "snapshot" / "global").mkdir(parents=True)
    (xdg / "hooks").mkdir(parents=True)
    (xdg / "opencode.db").write_bytes(b"\x00\x17\x01\x00index=\x17\x01\x00\x81\x19\x00")
    (xdg / "hooks" / "fsmonitor-watchman.sample").write_text(
        "example hook script to integrate Watchman\n"
    )
    # A real text agent log outside the runtime state must be archived, but the
    # raw stdout tee (opencode.txt) is skipped: it can carry provider metadata
    # (e.g. encrypted reasoning fields) that the secret regex cannot classify.
    agent_root = trial / "agent"
    (agent_root / "opencode.txt").write_text(
        '{"reasoningEncryptedContent":"gAAAAABqlyJ7BKBaQqpQbrIgFA0sK-LXqJC_WE3idu"}\n'
    )
    (agent_root / "agent-summary.txt").write_text("structured agent summary\n")
    trail = archive_harbor_trial(trial, tmp_path / "trails", task_id="task", task_revision="sha")
    assert (trail / "review.md").is_file()
    assert not (trail / "agent" / "opencode" / "xdg-data" / "opencode" / "opencode.db").exists()
    assert not (trail / "agent" / "opencode" / "xdg-data").exists()
    assert not (trail / "agent" / "opencode.txt").exists()
    # Text logs at the agent root are still archived.
    assert (trail / "agent" / "agent-summary.txt").is_file()


def test_manifest_records_the_archiver(tmp_path) -> None:
    trial = tmp_path / "trial"
    review = trial / "artifacts" / "workspace" / "submission" / "review.md"
    review.parent.mkdir(parents=True)
    review.write_text("review")
    trail = archive_harbor_trial(trial, tmp_path / "trails", task_id="t", task_revision="abc")
    archiver = json.loads((trail / "trail-manifest.json").read_text())["archiver"]
    assert archiver["name"] == "paper-review-harbor"
    assert archiver["version"]
    assert archiver["source"]["kind"]


def test_manifest_archiver_never_names_the_host(tmp_path, monkeypatch) -> None:
    """An editable install records its own filesystem path in PEP 610 metadata.

    That path names the contributor's machine, which is the exact class of
    detail this module strips everywhere else.
    """
    monkeypatch.setattr(
        provenance,
        "_direct_url",
        lambda: {"url": "file:///home/someone/secret-project", "dir_info": {"editable": True}},
    )
    source = provenance.archiver_source()
    assert "secret-project" not in json.dumps(source)
    assert "url" not in source


def test_vcs_install_is_traceable_to_a_commit(monkeypatch) -> None:
    monkeypatch.setattr(
        provenance,
        "_direct_url",
        lambda: {
            "url": "https://github.com/a-green-hand-jack/paper-review-bench",
            "vcs_info": {"vcs": "git", "commit_id": "e" * 40, "requested_revision": "v0.2.0"},
        },
    )
    source = provenance.archiver_source()
    assert source == {
        "kind": "vcs",
        "commit": "e" * 40,
        "requested_revision": "v0.2.0",
        "url": "https://github.com/a-green-hand-jack/paper-review-bench",
    }
    assert provenance.provenance_warnings({"source": source}) == []


def test_unpinned_vcs_install_warns(monkeypatch) -> None:
    monkeypatch.setattr(
        provenance,
        "_direct_url",
        lambda: {
            "url": "https://github.com/a-green-hand-jack/paper-review-bench",
            "vcs_info": {"vcs": "git", "commit_id": "f" * 40, "requested_revision": None},
        },
    )
    warnings = provenance.provenance_warnings({"source": provenance.archiver_source()})
    assert any("pin" in warning for warning in warnings)


def test_local_checkout_warns_and_reports_dirt(monkeypatch) -> None:
    monkeypatch.setattr(provenance, "_direct_url", lambda: None)
    monkeypatch.setattr(
        provenance,
        "_git",
        lambda directory, *args: "a" * 40 if args[0] == "rev-parse" else " M src/x.py",
    )
    source = provenance.archiver_source()
    assert source == {"kind": "local-checkout", "commit": "a" * 40, "dirty": True}
    warnings = provenance.provenance_warnings({"source": source})
    assert any("uncommitted" in warning for warning in warnings)


def test_provenance_survives_git_being_unavailable(monkeypatch) -> None:
    """Archiving a finished run must not fail because provenance is unknown."""
    monkeypatch.setattr(provenance, "_direct_url", lambda: None)
    monkeypatch.setattr(provenance, "_git", lambda directory, *args: None)
    source = provenance.archiver_source()
    assert source == {"kind": "release"}
    assert provenance.provenance_warnings({"source": source})


def test_unreadable_dirty_state_is_not_reported_as_clean(monkeypatch) -> None:
    monkeypatch.setattr(provenance, "_direct_url", lambda: None)
    monkeypatch.setattr(
        provenance,
        "_git",
        lambda directory, *args: "b" * 40 if args[0] == "rev-parse" else None,
    )
    source = provenance.archiver_source()
    assert source["dirty"] is None
    warnings = provenance.provenance_warnings({"source": source})
    assert any("could not be determined" in warning for warning in warnings)
