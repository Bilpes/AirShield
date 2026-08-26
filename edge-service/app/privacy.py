from __future__ import annotations

import importlib.util
import re
from collections import Counter
from dataclasses import dataclass


@dataclass
class Entity:
    type: str
    raw: str
    start: int
    end: int
    confidence: float
    token: str = ""


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
    ("PHONE", re.compile(r"(?<!\d)(?:\+?91[\s-]?)?[6-9]\d{4}[\s-]?\d{5}(?!\d)"), 0.98),
    ("PAN", re.compile(r"\b[A-Z]{5}\d{4}[A-Z]\b"), 0.99),
    ("IFSC", re.compile(r"\b[A-Z]{4}0[A-Z0-9]{6}\b"), 0.98),
    ("MRN", re.compile(r"\b(?:MRN\s*(?:is|:|#)?\s*)?[A-Z]{2,5}-\d{5,10}\b", re.I), 0.97),
    (
        "DATE_OF_BIRTH",
        re.compile(
            r"\b(?:DOB\s*(?:is|:)?\s*)?(?:\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{1,2}\s+[A-Za-z]{3,9}\s+\d{4})\b",
            re.I,
        ),
        0.96,
    ),
    ("IP_ADDRESS", re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b"), 0.97),
    ("CARD_OR_ACCOUNT", re.compile(r"(?<!\d)\d{10,19}(?!\d)"), 0.90),
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


class PrivacyEngine:
    """Hybrid local privacy engine.

    Presidio is loaded when available for contextual PERSON/LOCATION/DATE detection;
    deterministic industry rules run regardless. Token mappings remain in this process.
    """

    def __init__(self) -> None:
        self.analyzer = None
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
            print(f"Development NLP unavailable: {type(exc).__name__}")

    def detect(self, text: str) -> list[Entity]:
        candidates: list[Entity] = []
        for kind, pattern, confidence, capture in CONTEXT_RULES:
            for match in pattern.finditer(text):
                raw = match.group(capture)
                candidates.append(Entity(kind, raw, match.start(capture), match.end(capture), confidence))
        for kind, pattern, confidence in RULES:
            for match in pattern.finditer(text):
                candidates.append(Entity(kind, match.group(), match.start(), match.end(), confidence))
        if self.analyzer:
            try:
                for item in self.analyzer.analyze(
                    text=text, language="en", entities=["PERSON", "LOCATION", "DATE_TIME"]
                ):
                    candidates.append(
                        Entity(
                            item.entity_type,
                            text[item.start : item.end],
                            item.start,
                            item.end,
                            float(item.score),
                        )
                    )
            except Exception as exc:
                print(f"Development NLP failed closed to review: {type(exc).__name__}")
        candidates.sort(key=lambda e: (e.start, -(e.end - e.start), -e.confidence))
        selected: list[Entity] = []
        occupied = -1
        for entity in candidates:
            if entity.start >= occupied:
                selected.append(entity)
                occupied = entity.end
        return selected

    def protect(self, text: str, vault: dict[str, str]) -> tuple[str, list[dict]]:
        entities = self.detect(text)
        counters = Counter(token.strip("[]").rsplit("_", 1)[0] for token in vault.values())
        cursor = 0
        output: list[str] = []
        for entity in entities:
            token = vault.get(entity.raw)
            if not token:
                counters[entity.type] += 1
                token = f"[{entity.type}_{counters[entity.type]}]"
                vault[entity.raw] = token
            entity.token = token
            output.extend((text[cursor : entity.start], token))
            cursor = entity.end
        output.append(text[cursor:])
        public = [
            {"type": e.type, "token": e.token, "start": e.start, "end": e.end, "confidence": e.confidence}
            for e in entities
        ]
        return "".join(output), public
