from __future__ import annotations

import json

import pytest

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
