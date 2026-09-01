from __future__ import annotations

from pathlib import Path

from paper_review_harbor.publish import PublishPlan, PublishResult, upload


def test_upload_commands_use_requested_revision(tmp_path: Path, monkeypatch) -> None:
    local = tmp_path / "paper-review-exam"
    local.mkdir()
    plan = PublishPlan(
        repo_id="org/exam",
        dataset="paper-review-exam",
        local_dir=local,
        task_ids=("task",),
        total_bytes=0,
        revision="release-v2",
    )
    monkeypatch.setattr("paper_review_harbor.publish.shutil.which", lambda _: "/usr/bin/hf")
    result = upload(plan, readme="# card\n")
    assert isinstance(result, PublishResult)
    assert result.commands.count("--revision release-v2") == 2
    assert result.resolved_revision is None
    assert "/tree/release-v2/paper-review-exam" in plan.harbor_repo_url
