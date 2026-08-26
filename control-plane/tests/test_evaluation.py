from pathlib import Path

from evaluation.evaluate import evaluate


def test_regex_smoke_fixture_has_no_span_regressions():
    result = evaluate(Path("evaluation/fixtures/regex-gate.jsonl"))
    assert result["false_negative"] == 0
    assert result["false_positive"] == 0
    assert result["production_gate_satisfied"] is False
