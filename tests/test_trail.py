from __future__ import annotations

import json

from paper_review_harbor.trail import TrailError, archive_trail, upload_trail


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
