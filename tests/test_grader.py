from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

GRADER_PATH = (
    Path(__file__).resolve().parents[1]
    / "src"
    / "paper_review_harbor"
    / "templates"
    / "grader_review.py"
)


def load_grader():
    spec = importlib.util.spec_from_file_location("grader_review", GRADER_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    # Register before executing: @dataclass resolves annotations through
    # sys.modules[cls.__module__], which is None for an unregistered module.
    sys.modules["grader_review"] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def grader():
    return load_grader()


RUBRIC = {
    "task_id_base": "erdos973--v1",
    "protocol": "offline",
    "paper": {"slug": "erdos973", "version": "v1", "domain": "mathematics"},
    "min_review_chars": 200,
    "findings": [
        {
            "id": "F1",
            "title": "Title over-claims priority",
            "severity": "major",
            "gating": True,
            "detectability": "high",
            "protocols": ["offline", "online"],
            "location": "main.tex:26",
            "claim": "presents the negative answer as its own",
            "defect": "Luo-Yang-Zhu got there first",
            "accept_if": "Says the priority claim is not the paper's to make.",
            "reject_if": "Merely asks for more related work.",
        },
        {
            "id": "F2",
            "title": "Abstract omits the upper bound",
            "severity": "minor",
            "gating": False,
            "detectability": "medium",
            "protocols": ["offline", "online"],
            "location": "abstract",
            "claim": "asserts a limit",
            "defect": "no witnessing polynomial",
            "accept_if": "Notes the missing complementary upper bound.",
        },
        {
            "id": "F3",
            "title": "Needs a literature check",
            "severity": "major",
            "gating": True,
            "detectability": "low",
            "protocols": ["online"],
            "location": "section 1",
            "claim": "claims novelty",
            "defect": "superseded",
            "accept_if": "Identifies the superseding result.",
        },
    ],
    "distractors": [
        {
            "id": "D1",
            "description": "Uses amsart rather than a journal class.",
            "why_not_a_defect": "A submission detail, not a defect.",
        }
    ],
}


def write_rubric(tmp_path: Path) -> Path:
    path = tmp_path / "rubric.json"
    path.write_text(json.dumps(RUBRIC), encoding="utf-8")
    return path


def run(grader, tmp_path: Path, review: str | None, monkeypatch, env=None) -> dict:
    submission = tmp_path / "submission"
    submission.mkdir(exist_ok=True)
    if review is not None:
        (submission / "review.md").write_text(review, encoding="utf-8")
    out = tmp_path / "logs"
    for key in ("JUDGE_API_KEY", "OPENAI_API_KEY"):
        monkeypatch.delenv(key, raising=False)
    for key, value in (env or {}).items():
        monkeypatch.setenv(key, value)
    monkeypatch.setattr(
        "sys.argv",
        [
            "grader_review.py",
            "--rubric", str(write_rubric(tmp_path)),
            "--submission", str(submission),
            "--protocol", "offline",
            "--out", str(out),
        ],
    )
    grader.main()
    return json.loads((out / "reward.json").read_text(encoding="utf-8"))


class TestDeterministicGate:
    def test_missing_review_scores_zero(self, grader, tmp_path, monkeypatch) -> None:
        reward = run(grader, tmp_path, None, monkeypatch)
        assert reward["reward"] == 0.0
        assert reward["submitted"] == 0.0
        assert reward["judged"] == 0.0

    def test_too_short_a_review_is_not_judged(self, grader, tmp_path, monkeypatch) -> None:
        reward = run(grader, tmp_path, "Looks fine to me.", monkeypatch)
        assert reward["reward"] == 0.0
        assert reward["submitted"] == 1.0
        assert reward["judged"] == 0.0

    def test_missing_judge_credentials_is_flagged_not_silently_zero(
        self, grader, tmp_path, monkeypatch
    ) -> None:
        """A run with no judge is broken infrastructure, not a failed agent."""
        reward = run(grader, tmp_path, "x" * 500, monkeypatch)
        assert reward["grader_error"] == 1.0
        assert reward["judged"] == 0.0
        assert reward["submitted"] == 1.0


class TestEvidenceGuard:
    def test_real_quote_is_accepted(self, grader) -> None:
        review = "The title claims priority that the body itself concedes to others."
        assert grader._quote_is_real("claims priority that the body", review)

    def test_whitespace_differences_are_tolerated(self, grader) -> None:
        review = "The title claims\n   priority that the body concedes."
        assert grader._quote_is_real("claims priority that the body", review)

    def test_invented_quote_is_rejected(self, grader) -> None:
        assert not grader._quote_is_real("a passage that is simply not there", "short review")

    def test_trivially_short_quote_is_rejected(self, grader) -> None:
        assert not grader._quote_is_real("the", "the review")


class TestScoring:
    """Reward is gating recall. These pin down exactly what that means."""

    def _report(self, grader, verdicts, review="r" * 500, distractors=()):
        findings = [f for f in RUBRIC["findings"] if "offline" in f["protocols"]]
        judgements = [
            grader.Judgement(
                finding_id=f["id"],
                verdict=verdicts[f["id"]],
                votes=[verdicts[f["id"]]] * 3,
                evidence="",
                reasoning="",
                gating=bool(f["gating"]),
                detectability=f["detectability"],
                severity=f["severity"],
            )
            for f in findings
        ]
        reward, evaluation = grader.build_report(
            RUBRIC, review, [], judgements, list(distractors), 3, judged=True
        )
        return reward, evaluation

    def test_online_only_finding_is_excluded_offline(self, grader) -> None:
        reward, _ = self._report(grader, {"F1": grader.FOUND, "F2": grader.FOUND})
        assert reward["n_findings"] == 2.0, "F3 is online-only and must not be scored here"
        assert reward["n_gating"] == 1.0

    def test_perfect_review_scores_one(self, grader) -> None:
        reward, _ = self._report(grader, {"F1": grader.FOUND, "F2": grader.FOUND})
        assert reward["reward"] == 1.0
        assert reward["finding_recall"] == 1.0

    def test_missing_the_gating_finding_scores_zero(self, grader) -> None:
        """Catching every minor point does not rescue a missed gating defect."""
        reward, _ = self._report(grader, {"F1": grader.MISSED, "F2": grader.FOUND})
        assert reward["reward"] == 0.0
        assert reward["finding_recall"] == 0.5

    def test_partial_credit_is_half(self, grader) -> None:
        reward, _ = self._report(grader, {"F1": grader.PARTIAL, "F2": grader.MISSED})
        assert reward["reward"] == 0.5
        assert reward["strict_gating_recall"] == 0.0

    def test_detectability_tiers_are_reported_separately(self, grader) -> None:
        reward, _ = self._report(grader, {"F1": grader.FOUND, "F2": grader.MISSED})
        assert reward["recall_high"] == 1.0
        assert reward["recall_medium"] == 0.0

    def test_distractors_are_counted_but_do_not_move_the_reward(self, grader) -> None:
        clean, _ = self._report(grader, {"F1": grader.FOUND, "F2": grader.FOUND})
        noisy, _ = self._report(
            grader, {"F1": grader.FOUND, "F2": grader.FOUND}, distractors=["D1"]
        )
        assert clean["distractor_rate"] == 0.0
        assert noisy["distractor_rate"] == 1.0
        assert clean["reward"] == noisy["reward"] == 1.0

    def test_evaluation_records_every_verdict_for_human_review(self, grader) -> None:
        _, evaluation = self._report(grader, {"F1": grader.FOUND, "F2": grader.MISSED})
        assert [f["id"] for f in evaluation["findings"]] == ["F1", "F2"]
        assert evaluation["findings"][0]["credit"] == 1.0


class TestVoting:
    def test_majority_wins(self, grader, monkeypatch) -> None:
        review = "The title claims priority that the body itself concedes to others."
        finding = RUBRIC["findings"][0]
        judge = grader.Judge.__new__(grader.Judge)
        judge._model = "stub"
        judge._votes = 3
        answers = iter(
            [
                {"verdict": "found", "evidence": "claims priority that the body", "reasoning": ""},
                {"verdict": "missed", "evidence": ""},
                {"verdict": "found", "evidence": "claims priority that the body", "reasoning": ""},
            ]
        )
        monkeypatch.setattr(judge, "_ask_safely", lambda prompt: next(answers))
        result = judge.judge_finding(finding, review, "mathematics")
        assert result.verdict == grader.FOUND
        assert result.votes == ["found", "missed", "found"]

    def test_unquotable_found_is_downgraded(self, grader, monkeypatch) -> None:
        """A judge that cannot point at the passage has not found anything."""
        review = "The manuscript is competently written throughout."
        finding = RUBRIC["findings"][0]
        judge = grader.Judge.__new__(grader.Judge)
        judge._model = "stub"
        judge._votes = 3
        monkeypatch.setattr(
            judge,
            "_ask_safely",
            lambda prompt: {"verdict": "found", "evidence": "it says the priority is wrong"},
        )
        result = judge.judge_finding(finding, review, "mathematics")
        assert result.verdict != grader.FOUND

    def test_a_failed_judge_call_counts_as_missed(self, grader, monkeypatch) -> None:
        judge = grader.Judge.__new__(grader.Judge)
        judge._model = "stub"
        judge._votes = 3
        monkeypatch.setattr(judge, "_ask_safely", lambda prompt: {})
        result = judge.judge_finding(RUBRIC["findings"][0], "x" * 500, "mathematics")
        assert result.verdict == grader.MISSED


class TestLenientJson:
    r"""Reviews of maths papers quote LaTeX, and judges serialise it carelessly."""

    def test_plain_json_still_parses(self, grader) -> None:
        assert grader.loads_lenient('{"verdict": "found"}') == {"verdict": "found"}

    def test_unescaped_latex_backslash_is_repaired(self, grader) -> None:
        raw = r'{"verdict": "found", "evidence": "contradicting \eqref{eq:bad}"}'
        parsed = grader.loads_lenient(raw)
        assert parsed["verdict"] == "found"
        assert parsed["evidence"] == r"contradicting \eqref{eq:bad}"

    def test_legitimate_escapes_survive_the_repair(self, grader) -> None:
        raw = r'{"a": "line\nbreak", "b": "quote\"inside", "c": "back\\slash"}'
        parsed = grader.loads_lenient(raw)
        assert parsed["a"] == "line\nbreak"
        assert parsed["b"] == 'quote"inside'
        assert parsed["c"] == "back\\slash"

    def test_unrepairable_output_is_dropped_not_raised(self, grader) -> None:
        assert grader.loads_lenient("not json at all") == {}

    def test_non_object_json_is_dropped(self, grader) -> None:
        assert grader.loads_lenient('["a", "b"]') == {}
