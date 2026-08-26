from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

from app.detection import Detector


def evaluate(path: Path) -> dict[str, object]:
    detector = Detector()
    true_positive = false_positive = false_negative = 0
    by_type: Counter[str] = Counter()
    missed: list[dict[str, object]] = []
    for line in path.read_text().splitlines():
        if not line.strip():
            continue
        sample = json.loads(line)
        expected = {(item["type"], item["start"], item["end"]) for item in sample["entities"]}
        allowed = {kind for kind, _, _ in expected} or {
            "EMAIL",
            "PHONE",
            "CARD_OR_ACCOUNT",
            "PAN",
            "IFSC",
            "MRN",
            "SECRET",
            "IP_ADDRESS",
        }
        actual = {
            (item.entity_type, item.start, item.end) for item in detector.detect(sample["text"], allowed)
        }
        true_positive += len(expected & actual)
        false_positive += len(actual - expected)
        false_negative += len(expected - actual)
        by_type.update(kind for kind, _, _ in expected & actual)
        for entity in sorted(expected - actual):
            missed.append({"sample": sample["id"], "entity": entity})
    precision = true_positive / max(1, true_positive + false_positive)
    recall = true_positive / max(1, true_positive + false_negative)
    return {
        "fixture": str(path),
        "true_positive": true_positive,
        "false_positive": false_positive,
        "false_negative": false_negative,
        "micro_precision": round(precision, 6),
        "micro_recall": round(recall, 6),
        "recognized_by_type": dict(sorted(by_type.items())),
        "missed": missed,
        "production_gate_satisfied": False,
        "notice": "Synthetic smoke fixtures never satisfy the representative production model gate.",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("fixture", type=Path)
    parser.add_argument("--require-perfect", action="store_true")
    args = parser.parse_args()
    result = evaluate(args.fixture)
    print(json.dumps(result, indent=2))
    return int(bool(args.require_perfect and (result["false_positive"] or result["false_negative"])))


if __name__ == "__main__":
    raise SystemExit(main())
