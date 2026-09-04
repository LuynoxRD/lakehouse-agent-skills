"""TF-IDF ranking with Porter stemming, used by the Tier 2 trigger and routing evals.

The catalog is tiny (a dozen descriptions), so a plain in-memory implementation
with sublinear term frequency, smoothed inverse document frequency and cosine
similarity is enough and stays dependency-free.
"""

from __future__ import annotations

import math
import re
from collections.abc import Mapping
from dataclasses import dataclass

from lib.porter import stem

STOPWORDS = frozenset(
    {
        "a",
        "about",
        "above",
        "after",
        "again",
        "against",
        "all",
        "am",
        "an",
        "and",
        "any",
        "are",
        "as",
        "at",
        "be",
        "because",
        "been",
        "before",
        "being",
        "below",
        "between",
        "both",
        "but",
        "by",
        "can",
        "could",
        "did",
        "do",
        "does",
        "doing",
        "down",
        "during",
        "each",
        "few",
        "for",
        "from",
        "further",
        "had",
        "has",
        "have",
        "having",
        "he",
        "her",
        "here",
        "hers",
        "herself",
        "him",
        "himself",
        "his",
        "how",
        "i",
        "if",
        "in",
        "into",
        "is",
        "it",
        "its",
        "itself",
        "just",
        "let",
        "me",
        "more",
        "most",
        "my",
        "myself",
        "no",
        "nor",
        "not",
        "now",
        "of",
        "off",
        "on",
        "once",
        "only",
        "or",
        "other",
        "our",
        "ours",
        "ourselves",
        "out",
        "over",
        "own",
        "same",
        "she",
        "should",
        "so",
        "some",
        "such",
        "than",
        "that",
        "the",
        "their",
        "theirs",
        "them",
        "themselves",
        "then",
        "there",
        "these",
        "they",
        "this",
        "those",
        "through",
        "to",
        "too",
        "under",
        "until",
        "up",
        "very",
        "was",
        "we",
        "were",
        "what",
        "when",
        "where",
        "which",
        "while",
        "who",
        "whom",
        "why",
        "will",
        "with",
        "would",
        "you",
        "your",
        "yours",
        "yourself",
        "yourselves",
        "use",
        "using",
        "used",
    }
)

_TOKEN_RE = re.compile(r"[a-z0-9]+")
_MIN_TOKEN_LENGTH = 2


def tokenize(text: str) -> list[str]:
    """Lowercase, split on non-alphanumerics, drop stopwords and one-character tokens, stem."""
    tokens: list[str] = []
    for raw in _TOKEN_RE.findall(text.lower()):
        if raw in STOPWORDS or len(raw) < _MIN_TOKEN_LENGTH:
            continue
        tokens.append(stem(raw))
    return tokens


def _term_frequencies(tokens: list[str]) -> dict[str, float]:
    counts: dict[str, int] = {}
    for token in tokens:
        counts[token] = counts.get(token, 0) + 1
    return {term: 1.0 + math.log(count) for term, count in counts.items()}


def _normalize(vector: dict[str, float]) -> dict[str, float]:
    norm = math.sqrt(sum(weight * weight for weight in vector.values()))
    if norm == 0.0:
        return {}
    return {term: weight / norm for term, weight in vector.items()}


def cosine(left: Mapping[str, float], right: Mapping[str, float]) -> float:
    """Cosine similarity of two already-normalized sparse vectors."""
    if len(left) > len(right):
        left, right = right, left
    return sum(weight * right.get(term, 0.0) for term, weight in left.items())


@dataclass(frozen=True, slots=True)
class Index:
    """Normalized TF-IDF vectors for a set of named documents."""

    idf: dict[str, float]
    vectors: dict[str, dict[str, float]]
    unseen_idf: float

    @property
    def documents(self) -> list[str]:
        """Document names in insertion order."""
        return list(self.vectors)

    def vectorize(self, text: str) -> dict[str, float]:
        """Weight a query with the index's inverse document frequencies."""
        weighted = {
            term: tf * self.idf.get(term, self.unseen_idf)
            for term, tf in _term_frequencies(tokenize(text)).items()
        }
        return _normalize(weighted)

    def rank(self, query: str) -> list[tuple[str, float]]:
        """Every document with its similarity to *query*, best first; ties break by name."""
        vector = self.vectorize(query)
        scored = [(name, cosine(vector, doc)) for name, doc in self.vectors.items()]
        return sorted(scored, key=lambda item: (-item[1], item[0]))

    def similarity(self, left: str, right: str) -> float:
        """Cosine similarity between two indexed documents."""
        return cosine(self.vectors[left], self.vectors[right])


def build_index(documents: Mapping[str, str]) -> Index:
    """Build an index from ``{name: text}``."""
    tokenized = {name: tokenize(text) for name, text in documents.items()}
    total = len(tokenized)
    document_frequency: dict[str, int] = {}
    for tokens in tokenized.values():
        for term in set(tokens):
            document_frequency[term] = document_frequency.get(term, 0) + 1
    idf = {
        term: math.log((total + 1) / (frequency + 1)) + 1.0
        for term, frequency in document_frequency.items()
    }
    unseen_idf = math.log(total + 1) + 1.0
    vectors = {
        name: _normalize({term: tf * idf[term] for term, tf in _term_frequencies(tokens).items()})
        for name, tokens in tokenized.items()
    }
    return Index(idf=idf, vectors=vectors, unseen_idf=unseen_idf)
