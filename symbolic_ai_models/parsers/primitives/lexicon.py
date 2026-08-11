"""Surface-form normalization. Owned by symbolic-ai-001; import it from here if
another agent ever needs the same lexicon.
"""

from __future__ import annotations

import re

QUANTIFIERS: dict[str, str] = {
    "all": "all",
    "every": "all",
    "each": "all",
    "any": "all",
    "no": "no",
    "none": "no",
    "some": "some",
    "there": "some",  # "there are some ..."
    "most": "some",
    "many": "some",
    "a": "some",
    "at": "some",  # "at least one ..."
}

COPULAS = ("are not", "is not", "aren't", "isn't", "are", "is")

ARTICLES = {"a", "an", "the"}

CONCLUSION_MARKERS = (
    "does it follow that",
    "therefore",
    "so it follows that",
    "it follows that",
    "conclusion:",
    "hence",
    "thus",
)

QUESTION_LEADS = ("is ", "are ", "does ", "do ")

IRREGULAR_PLURALS = {
    "people": "person",
    "men": "man",
    "women": "woman",
    "children": "child",
    "mice": "mouse",
    "geese": "goose",
    "feet": "foot",
    "teeth": "tooth",
}

_WORD = re.compile(r"[a-z0-9']+")


def words(text: str) -> list[str]:
    return _WORD.findall(text.lower())


def singular(word: str) -> str:
    """Enough morphology for categorical terms; deliberately not a real stemmer."""
    if word in IRREGULAR_PLURALS:
        return IRREGULAR_PLURALS[word]
    if len(word) > 3 and word.endswith("ies"):
        return word[:-3] + "y"
    if len(word) > 3 and word.endswith(("ses", "xes", "zes", "ches", "shes")):
        return word[:-2]
    if len(word) > 2 and word.endswith("s") and not word.endswith(("ss", "us", "is")):
        return word[:-1]
    return word


def term(text: str) -> str:
    """Normalize a noun phrase to a canonical term: drop articles, singularize."""
    parts = [w for w in words(text) if w not in ARTICLES]
    if not parts:
        return ""
    return " ".join([*parts[:-1], singular(parts[-1])])


def sentences(text: str) -> list[str]:
    """Split a prompt into candidate statements on sentence and line boundaries."""
    chunks = re.split(r"(?<=[.;?!])\s+|\n+", text)
    return [c.strip(" \t-*•") for c in chunks if c and c.strip(" \t-*•")]
