"""Text normalization and the SINGLE sentence-splitting function.

Key architectural rule of the project: sentence splitting happens ONLY here and
serves both `/api/split` and `/api/tts`. The frontend never splits text itself —
it uses only the result of `/api/split`. Otherwise sentence boundaries on the
front and back would diverge, breaking highlighting and range selection.

char_start/char_end offsets are computed relative to the SOURCE text (as the
frontend sent it), not the normalized one, so that highlighting lands in the same
text shown in the textarea.
"""

import re

# Sentence terminator characters.
_TERMINATORS = ".!?…"

# Kazakh-specific Cyrillic letters — for the language heuristic.
_KAZAKH_SPECIFIC = set("әғқңөұүһі")
# Cyrillic as a whole — Unicode block U+0400–U+04FF (includes both Russian and
# the Kazakh-specific letters ә ғ қ ң ө ұ ү һ і).
_CYRILLIC = re.compile(r"[Ѐ-ӿ]")


def normalize_text(text: str) -> str:
    """Trim + collapse any whitespace runs into a single space.

    Used to normalize text before synthesis and to build the cache key (so that
    "text  with   spaces" and "text with spaces" match).
    """
    return " ".join(text.split()).strip()


def split_sentences(text: str) -> list[dict]:
    """Split text into sentences, preserving offsets into the source text.

    Returns a list of dicts: {index, text, char_start, char_end}, where
    text == the source slice text[char_start:char_end] (trimmed of surrounding
    whitespace), char_end is exclusive.
    """
    result: list[dict] = []
    n = len(text)
    start = 0
    i = 0
    while i < n:
        if text[i] in _TERMINATORS:
            # Capture consecutive terminators (?!, ..., !!).
            j = i + 1
            while j < n and text[j] in _TERMINATORS:
                j += 1
            _append_sentence(result, text, start, j)
            start = j
            i = j
        else:
            i += 1
    # Tail without a trailing punctuation mark.
    if start < n:
        _append_sentence(result, text, start, n)
    return result


def _append_sentence(result: list[dict], text: str, raw_start: int, raw_end: int) -> None:
    """Append a sentence, trimming whitespace at the edges of the raw range."""
    s, e = raw_start, raw_end
    while s < e and text[s].isspace():
        s += 1
    while e > s and text[e - 1].isspace():
        e -= 1
    if e <= s:
        # Empty range (only whitespace/marks with no content) — skip.
        return
    result.append(
        {
            "index": len(result),
            "text": text[s:e],
            "char_start": s,
            "char_end": e,
        }
    )


def looks_like_kazakh(text: str) -> bool:
    """Rough heuristic: does the text look like Kazakh Cyrillic?

    True if the text contains Cyrillic and has at least one Kazakh-specific letter
    OR Cyrillic makes up a noticeable share of the letters.
    """
    letters = [c for c in text.lower() if c.isalpha()]
    if not letters:
        return False
    cyrillic = [c for c in letters if _CYRILLIC.match(c)]
    if not cyrillic:
        return False
    has_kazakh = any(c in _KAZAKH_SPECIFIC for c in letters)
    cyrillic_ratio = len(cyrillic) / len(letters)
    return has_kazakh or cyrillic_ratio >= 0.8


def kazakh_warning(text: str) -> str | None:
    """Return a warning message if the input does not look like Kazakh Cyrillic.

    The message is user-facing (shown in the UI), so it stays in Russian.
    """
    if not looks_like_kazakh(text):
        return (
            "Текст не похож на казахскую кириллицу — модель KazakhTTS2 "
            "работает только с казахским текстом на кириллице."
        )
    return None
