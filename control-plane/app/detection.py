from __future__ import annotations

import importlib.util
import re
from dataclasses import dataclass
from functools import lru_cache

from .config import get_settings


@dataclass(frozen=True)
class Detection:
    entity_type: str
    raw: str
    start: int
    end: int
    confidence: float


CONTEXT_RULES = [
    (
        "PERSON",
        re.compile(
            r"\b(?:patient|customer|member|caller|client)\s+(?:is\s+|named\s+)?"
            r"([A-Z][A-Za-z'’.-]*(?:\s+[A-Z][A-Za-z'’.-]*){0,2})"
            r"(?=\s*[,.;:]|\s+(?:with|account|called|phone|mobile|email)\b|$)",
            re.I,
        ),
        0.92,
        1,
    ),
    (
        "CARD_OR_ACCOUNT",
        re.compile(
            r"\b(?:account(?:\s+(?:number|no\.?|id))?|acct(?:\s+(?:number|no\.?|id))?|"
            r"customer\s+id)\s*(?:is|:|#|-)?\s*"
            r"([A-Z0-9](?:[A-Z0-9 -]{4,22}[A-Z0-9]))"
            r"(?=\s*[,.;]|\s+(?:and|called|phone|mobile|email|from)\b|$)",
            re.I,
        ),
        0.98,
        1,
    ),
    (
        "PHONE",
        re.compile(
            r"\b(?:called\s+from|phone|mobile|telephone|tel)\s*(?:is|:|#|-)?\s*"
            r"(\+?\d(?:[\s().-]*\d){6,14})"
            r"(?=\s*[,.;]|\s+(?:and|email|account|from)\b|$)",
            re.I,
        ),
        0.98,
        1,
    ),
]

RULES = [
    ("EMAIL", re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.I), 0.99),
    ("SECRET", re.compile(r"\b(?:sk|pk|api)[_-](?:live|test)?[_-]?[A-Za-z0-9]{8,}\b", re.I), 0.99),
    (
        "PHONE",
        re.compile(
            r"(?<!\d)(?:\+?91[\s-]?)?[6-9]\d{4}[\s-]?\d{5}(?!\d)|(?<!\d)(?:\+?1[\s-]?)?\(?\d{3}\)?[\s-]\d{3}[\s-]\d{4}(?!\d)"
        ),
        0.98,
    ),
    ("PAN", re.compile(r"\b[A-Z]{5}\d{4}[A-Z]\b"), 0.99),
    ("IFSC", re.compile(r"\b[A-Z]{4}0[A-Z0-9]{6}\b"), 0.98),
    ("MRN", re.compile(r"\b(?:MRN\s*(?:is|:|#)?\s*)?[A-Z]{2,5}-\d{5,10}\b", re.I), 0.97),
    (
        "DATE_TIME",
        re.compile(
            r"\b(?:DOB\s*(?:is|:)?\s*)?(?:\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{1,2}\s+[A-Za-z]{3,9}\s+\d{4})\b",
            re.I,
        ),
        0.96,
    ),
    ("IP_ADDRESS", re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b"), 0.97),
    ("CARD_OR_ACCOUNT", re.compile(r"(?<!\d)(?:\d[ -]?){9,18}\d(?!\d)"), 0.90),
    (
        "ADDRESS",
        re.compile(
            r"\b\d{1,5}\s+[A-Z][A-Za-z ]+"
            r"(?:Road|Rd|Street|St|Avenue|Ave|Lane|Ln|Drive|Dr)"
            r"(?:,\s*[A-Z][A-Za-z]+)?\b"
        ),
        0.88,
    ),
]


def luhn_valid(value: str) -> bool:
    digits = [int(character) for character in value if character.isdigit()]
    if not 12 <= len(digits) <= 19:
        return False
    total = 0
    parity = len(digits) % 2
    for index, digit in enumerate(digits):
        if index % 2 == parity:
            digit *= 2
            if digit > 9:
                digit -= 9
        total += digit
    return total % 10 == 0


class Detector:
    def __init__(self) -> None:
        self.analyzer = None
        self.error: str | None = None
        try:
            if importlib.util.find_spec("en_core_web_sm") is None:
                raise ModuleNotFoundError("en_core_web_sm is not installed")
            from presidio_analyzer import AnalyzerEngine
            from presidio_analyzer.nlp_engine import NlpEngineProvider

            provider = NlpEngineProvider(
                nlp_configuration={
                    "nlp_engine_name": "spacy",
                    "models": [{"lang_code": "en", "model_name": "en_core_web_sm"}],
                }
            )
            self.analyzer = AnalyzerEngine(nlp_engine=provider.create_engine(), supported_languages=["en"])
        except Exception as exc:
            self.error = type(exc).__name__

    @property
    def healthy(self) -> bool:
        return self.analyzer is not None or not get_settings().fail_closed

    def detect(self, text: str, allowed: set[str]) -> list[Detection]:
        candidates: list[Detection] = []
        for kind, pattern, confidence, capture in CONTEXT_RULES:
            if kind not in allowed:
                continue
            for match in pattern.finditer(text):
                raw = match.group(capture)
                candidates.append(Detection(kind, raw, match.start(capture), match.end(capture), confidence))
        for kind, pattern, confidence in RULES:
            if kind not in allowed:
                continue
            for match in pattern.finditer(text):
                score = 0.995 if kind == "CARD_OR_ACCOUNT" and luhn_valid(match.group()) else confidence
                candidates.append(Detection(kind, match.group(), match.start(), match.end(), score))
        if self.analyzer:
            for item in self.analyzer.analyze(
                text=text,
                language="en",
                entities=list(allowed & {"PERSON", "LOCATION", "DATE_TIME", "ORGANIZATION"}),
            ):
                candidates.append(
                    Detection(
                        item.entity_type, text[item.start : item.end], item.start, item.end, float(item.score)
                    )
                )
        elif allowed & {"PERSON", "LOCATION", "ORGANIZATION"} and get_settings().fail_closed:
            raise RuntimeError("Contextual detector unavailable")
        candidates.sort(key=lambda item: (item.start, -(item.end - item.start), -item.confidence))
        selected: list[Detection] = []
        occupied = -1
        for candidate in candidates:
            if candidate.start >= occupied:
                selected.append(candidate)
                occupied = candidate.end
        return selected


@lru_cache(maxsize=1)
def get_detector() -> Detector:
    return Detector()
