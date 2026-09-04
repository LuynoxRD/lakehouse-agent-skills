"""Tests for the TF-IDF index used by the Tier 2 evals."""

from __future__ import annotations

import math

from lib.tfidf import build_index, cosine, tokenize


def test_tokenize_stems_and_drops_stopwords() -> None:
    assert tokenize("Use when profiling the spreadsheets before charting!") == [
        "profil",
        "spreadsheet",
        "chart",
    ]
    assert tokenize("a I 1") == []


def test_rank_prefers_matching_document() -> None:
    index = build_index(
        {
            "charts": "Chooses chart types for comparisons and distributions.",
            "privacy": "Masks personal data before rows reach a language model.",
            "sql": "Queries parquet files with SQL and explains query plans.",
        }
    )
    ranking = index.rank("which chart should I use for a distribution")
    assert ranking[0][0] == "charts"
    assert ranking[0][1] > ranking[1][1]
    assert [name for name, _ in ranking] == sorted(
        [name for name, _ in ranking], key=lambda n: (-dict(ranking)[n], n)
    )


def test_vectors_are_unit_length_and_similarity_symmetric() -> None:
    index = build_index(
        {"a": "profile clean chart", "b": "profile clean chart chart", "c": "unrelated words"}
    )
    for vector in index.vectors.values():
        assert math.isclose(math.sqrt(sum(w * w for w in vector.values())), 1.0)
    assert math.isclose(index.similarity("a", "b"), index.similarity("b", "a"))
    assert index.similarity("a", "b") > index.similarity("a", "c")
    assert index.similarity("a", "c") == 0.0


def test_unseen_terms_do_not_break_queries() -> None:
    index = build_index({"a": "profile data"})
    assert index.rank("zebra") == [("a", 0.0)]
    assert cosine({}, {"x": 1.0}) == 0.0
    assert index.documents == ["a"]
