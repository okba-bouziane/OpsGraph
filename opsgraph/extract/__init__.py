from opsgraph.extract.base import Extractor, build_registry
from opsgraph.extract.llm import LLMExtractor
from opsgraph.extract.rules import RuleExtractor

__all__ = ["Extractor", "LLMExtractor", "RuleExtractor", "build_registry", "get_extractor"]


def get_extractor(kind: str) -> Extractor:
    if kind == "rules":
        return RuleExtractor()
    if kind == "llm":
        return LLMExtractor()
    raise ValueError(f"unknown extractor: {kind!r} (use 'rules' or 'llm')")
