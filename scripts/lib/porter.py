"""Porter stemmer, implemented from the published algorithm (M. F. Porter, 1980).

Used by the Tier 2 trigger evals so that "profiling" and "profile" share a term.
Standard library only; no third-party NLP package.
"""

from __future__ import annotations

_VOWELS = frozenset("aeiou")
_DOUBLE = 2
_CVC_LENGTH = 3
_MIN_STEM_LENGTH = 2

_STEP2_SUFFIXES: tuple[tuple[str, str], ...] = (
    ("ational", "ate"),
    ("tional", "tion"),
    ("enci", "ence"),
    ("anci", "ance"),
    ("izer", "ize"),
    ("bli", "ble"),
    ("alli", "al"),
    ("entli", "ent"),
    ("eli", "e"),
    ("ousli", "ous"),
    ("ization", "ize"),
    ("ation", "ate"),
    ("ator", "ate"),
    ("alism", "al"),
    ("iveness", "ive"),
    ("fulness", "ful"),
    ("ousness", "ous"),
    ("aliti", "al"),
    ("iviti", "ive"),
    ("biliti", "ble"),
    ("logi", "log"),
)

_STEP3_SUFFIXES: tuple[tuple[str, str], ...] = (
    ("icate", "ic"),
    ("ative", ""),
    ("alize", "al"),
    ("iciti", "ic"),
    ("ical", "ic"),
    ("ful", ""),
    ("ness", ""),
)

_STEP4_SUFFIXES: tuple[str, ...] = (
    "al",
    "ance",
    "ence",
    "er",
    "ic",
    "able",
    "ible",
    "ant",
    "ement",
    "ment",
    "ent",
    "ion",
    "ou",
    "ism",
    "ate",
    "iti",
    "ous",
    "ive",
    "ize",
)


def _longest_first(pairs: tuple[tuple[str, str], ...]) -> tuple[tuple[str, str], ...]:
    return tuple(sorted(pairs, key=lambda pair: len(pair[0]), reverse=True))


_STEP2 = _longest_first(_STEP2_SUFFIXES)
_STEP3 = _longest_first(_STEP3_SUFFIXES)
_STEP4 = tuple(sorted(_STEP4_SUFFIXES, key=len, reverse=True))


def _is_consonant(word: str, index: int) -> bool:
    char = word[index]
    if char in _VOWELS:
        return False
    if char == "y":
        return index == 0 or not _is_consonant(word, index - 1)
    return True


def _measure(stem: str) -> int:
    """Number of vowel-consonant sequences in ``[C](VC){m}[V]``."""
    measure = 0
    index = 0
    length = len(stem)
    while index < length and _is_consonant(stem, index):
        index += 1
    while index < length:
        while index < length and not _is_consonant(stem, index):
            index += 1
        if index >= length:
            break
        while index < length and _is_consonant(stem, index):
            index += 1
        measure += 1
    return measure


def _contains_vowel(stem: str) -> bool:
    return any(not _is_consonant(stem, index) for index in range(len(stem)))


def _ends_double_consonant(word: str) -> bool:
    return len(word) >= _DOUBLE and word[-1] == word[-2] and _is_consonant(word, len(word) - 1)


def _ends_cvc(word: str) -> bool:
    if len(word) < _CVC_LENGTH:
        return False
    return (
        _is_consonant(word, len(word) - 3)
        and not _is_consonant(word, len(word) - 2)
        and _is_consonant(word, len(word) - 1)
        and word[-1] not in "wxy"
    )


def _step1a(word: str) -> str:
    if word.endswith("sses"):
        return word[:-2]
    if word.endswith("ies"):
        return word[:-2]
    if word.endswith("ss"):
        return word
    if word.endswith("s"):
        return word[:-1]
    return word


def _step1b_cleanup(stem: str) -> str:
    if stem.endswith(("at", "bl", "iz")):
        return stem + "e"
    if _ends_double_consonant(stem) and stem[-1] not in "lsz":
        return stem[:-1]
    if _measure(stem) == 1 and _ends_cvc(stem):
        return stem + "e"
    return stem


def _step1b(word: str) -> str:
    if word.endswith("eed"):
        stem = word[:-3]
        return stem + "ee" if _measure(stem) > 0 else word
    for suffix in ("ed", "ing"):
        if word.endswith(suffix):
            stem = word[: -len(suffix)]
            return _step1b_cleanup(stem) if _contains_vowel(stem) else word
    return word


def _step1c(word: str) -> str:
    if word.endswith("y") and _contains_vowel(word[:-1]):
        return word[:-1] + "i"
    return word


def _replace_longest(word: str, table: tuple[tuple[str, str], ...], minimum_measure: int) -> str:
    for suffix, replacement in table:
        if word.endswith(suffix):
            stem = word[: -len(suffix)]
            if _measure(stem) > minimum_measure:
                return stem + replacement
            return word
    return word


def _step2(word: str) -> str:
    return _replace_longest(word, _STEP2, 0)


def _step3(word: str) -> str:
    return _replace_longest(word, _STEP3, 0)


def _step4(word: str) -> str:
    for suffix in _STEP4:
        if word.endswith(suffix):
            stem = word[: -len(suffix)]
            if _measure(stem) <= 1:
                return word
            if suffix == "ion" and not stem.endswith(("s", "t")):
                return word
            return stem
    return word


def _step5a(word: str) -> str:
    if word.endswith("e"):
        stem = word[:-1]
        measure = _measure(stem)
        if measure > 1 or (measure == 1 and not _ends_cvc(stem)):
            return stem
    return word


def _step5b(word: str) -> str:
    if _measure(word) > 1 and _ends_double_consonant(word) and word.endswith("l"):
        return word[:-1]
    return word


def stem(word: str) -> str:
    """Return the Porter stem of an ASCII word; words of two letters or fewer are unchanged."""
    lowered = word.lower()
    if len(lowered) <= _MIN_STEM_LENGTH:
        return lowered
    for step in (_step1a, _step1b, _step1c, _step2, _step3, _step4, _step5a, _step5b):
        lowered = step(lowered)
    return lowered
