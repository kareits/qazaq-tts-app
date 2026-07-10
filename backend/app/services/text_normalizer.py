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

from app.services import num2words_kk

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
        if text[i] in _TERMINATORS and not _is_decimal_point(text, i):
            # Capture consecutive terminators (?!, ..., !!).
            j = i + 1
            while j < n and text[j] in _TERMINATORS and not _is_decimal_point(text, j):
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


def _is_decimal_point(text: str, i: int) -> bool:
    """True if the '.' at index i sits between two digits, so it is a decimal
    separator or a date dot (3.14, 05.05.2024) — not a sentence break."""
    return (
        text[i] == "."
        and 0 < i < len(text) - 1
        and text[i - 1].isdigit()
        and text[i + 1].isdigit()
    )


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


# --- Number expansion (NUMBERS.md, stages 1-3) -----------------------------
#
# A number token: optional sign, an integer (plain or space-grouped "1 000 000"),
# an optional decimal (comma or dot — comma is primary in Kazakh), an optional
# hyphen suffix ("5-ші" ordinal, "10-ға" case, "5-сынып" attributive word) and an
# optional unit (% or ₸). Dates, time, phones and ranges are handled by dedicated
# passes that run before this one (see expand_numbers_kk).
_NUMBER_RE = re.compile(
    r"(?<!\w)(-)?(\d{1,3}(?:[\s ]\d{3})+|\d+)([.,]\d+)?"
    r"(?:-([а-яёәғқңөұүһі]+))?(\s?[%₸])?",
    re.IGNORECASE,
)

# Explicit ordinal markers written after the hyphen ("5-ші" -> бесінші).
_ORDINAL_MARKERS = {"ші", "шы", "ыншы", "інші", "нші", "ншы"}

# Written case allomorph -> case name. The number is spelled and the correct
# allomorph is re-derived from the spelled word (so "100-ға" -> "жүзге").
_WRITTEN_CASE = {
    "ға": "dative", "ге": "dative", "қа": "dative", "ке": "dative",
    "да": "locative", "де": "locative", "та": "locative", "те": "locative",
    "дан": "ablative", "ден": "ablative", "тан": "ablative", "тен": "ablative",
    "нан": "ablative", "нен": "ablative",
    "ны": "accusative", "ні": "accusative", "ды": "accusative",
    "ді": "accusative", "ты": "accusative", "ті": "accusative",
    "ның": "genitive", "нің": "genitive", "дың": "genitive", "дің": "genitive",
    "тың": "genitive", "тің": "genitive",
    "мен": "instrumental", "бен": "instrumental", "пен": "instrumental",
}

# Following words that make a bare "N <word>" ordinal (D1): a 4-digit year, a
# century, or a month (day of the date). Duration ("2 жыл") stays cardinal via
# the numeric range guards.
_YEAR_WORDS = {"жыл", "жылы", "жылғы", "жылдың", "жылдан", "жылда"}
_CENTURY_WORDS = {"ғасыр", "ғасырда", "ғасырдың", "ғасырға"}
_MONTHS = {
    1: "қаңтар", 2: "ақпан", 3: "наурыз", 4: "сәуір", 5: "мамыр", 6: "маусым",
    7: "шілде", 8: "тамыз", 9: "қыркүйек", 10: "қазан", 11: "қараша",
    12: "желтоқсан",
}
_MONTH_WORDS = set(_MONTHS.values())
_NEXT_WORD_RE = re.compile(r"\s+([а-яёәғқңөұүһі]+)", re.IGNORECASE)


def _with_sign(reading: str, sign: str | None) -> str:
    return "минус " + reading if sign else reading


def _apply_unit(reading: str, unit_raw: str | None) -> str:
    if unit_raw:
        symbol = unit_raw.strip()[-1]
        if symbol == "%":
            reading += " пайыз"
        elif symbol == "₸":
            reading += " теңге"
    return reading


def _number_replacement(m: re.Match) -> str:
    """Replace one number token with its Kazakh reading, or leave it unchanged if
    it is part of a dotted chain the date pass did not consume."""
    s = m.string
    start, end = m.start(), m.end()
    sign, int_raw, frac_raw, suffix, unit_raw = m.group(1, 2, 3, 4, 5)

    # Part of a longer dotted/comma digit chain (unparsed date/version) — leave it.
    if start >= 2 and s[start - 1] in ".," and s[start - 2].isdigit():
        return m.group(0)
    if not suffix:
        tail = s[end : end + 2]
        if tail[:1] in ".," and len(tail) >= 2 and tail[1].isdigit():
            return m.group(0)

    int_val = int(re.sub(r"[\s ]", "", int_raw))

    # Decimal (units/suffix ignored — decimals do not take them).
    if frac_raw:
        reading = num2words_kk.decimal_kk(int_val, frac_raw[1:])
        return _apply_unit(_with_sign(reading, sign), unit_raw)

    # Hyphen suffix: ordinal marker, case allomorph, or an attributive word.
    if suffix:
        low = suffix.lower()
        if low in _ORDINAL_MARKERS:
            return _with_sign(num2words_kk.ordinal_kk(int_val), sign)
        if low in _WRITTEN_CASE:
            spelled = num2words_kk.cardinal_kk(int_val)
            return _with_sign(
                num2words_kk.attach_case(spelled, _WRITTEN_CASE[low]), sign
            )
        # "5-сынып" — the number modifies the noun as an ordinal.
        return _with_sign(num2words_kk.ordinal_kk(int_val) + " " + suffix, sign)

    # Context ordinal: day before a month ("5 мамыр"), a 4-digit year
    # ("2015 жыл"), or a century ("21 ғасыр").
    nxt = _NEXT_WORD_RE.match(s, end)
    if nxt:
        word = nxt.group(1).lower()
        if word in _MONTH_WORDS and 1 <= int_val <= 31:
            return _with_sign(num2words_kk.ordinal_kk(int_val), sign)
        if (word in _YEAR_WORDS and 1000 <= int_val <= 2999) or (
            word in _CENTURY_WORDS and 1 <= int_val <= 40
        ):
            return _with_sign(num2words_kk.ordinal_kk(int_val), sign)

    return _apply_unit(_with_sign(num2words_kk.cardinal_kk(int_val), sign), unit_raw)


# --- Stage 3: dates, time, phones, ranges ----------------------------------

# Dotted date dd.mm.yyyy (requires the 4-digit year to avoid clashing with
# decimals like "05.05"). Read as "<day ordinal> <month> <year ordinal> жыл".
_DATE_RE = re.compile(r"(?<!\d)(\d{1,2})\.(\d{1,2})\.(\d{4})(?!\d)")

# Time HH:MM (24h) with an optional case suffix ("14:30-да"). Read as
# "<hours> сағат [<minutes> минут]", with the case attached to the last word.
_TIME_RE = re.compile(
    r"(?<!\d)([01]?\d|2[0-3]):([0-5]\d)(?:-([а-яёәғқңөұүһі]+))?(?!\d)",
    re.IGNORECASE,
)

# Phone: a leading "+" then 9+ digits with optional spaces/dashes/parens. Read
# digit by digit. The "+" is a strong phone signal, so this rarely misfires.
_PHONE_RE = re.compile(r"\+\d[\d()\s\-]{7,}\d")

# Numeric range with an en/em dash ("2020–2024" -> "…дан …ға дейін"). A plain
# hyphen is intentionally NOT treated as a range (too ambiguous with scores like
# "2-1"); such cases fall through to the number pass.
_RANGE_RE = re.compile(r"(?<!\d)(\d{1,4})\s*[–—]\s*(\d{1,4})(?!\d)")


def _date_replacement(m: re.Match) -> str:
    day, month, year = int(m.group(1)), int(m.group(2)), int(m.group(3))
    if not (1 <= day <= 31 and 1 <= month <= 12):
        return m.group(0)  # not a real date (e.g. a version) — leave it
    reading = (
        f"{num2words_kk.ordinal_kk(day)} {_MONTHS[month]} "
        f"{num2words_kk.ordinal_kk(year)}"
    )
    # Append "жыл" unless the text already has a year word right after.
    nxt = _NEXT_WORD_RE.match(m.string, m.end())
    if not (nxt and nxt.group(1).lower() in _YEAR_WORDS):
        reading += " жыл"
    return reading


def _time_replacement(m: re.Match) -> str:
    # Kazakh reads a clock time as bare cardinals ("14:30" -> "он төрт отыз"); the
    # word "сағат" comes from the surrounding text, not inserted here. A case
    # suffix ("14:30-де") attaches to the last word ("…отызда").
    hours, minutes = int(m.group(1)), int(m.group(2))
    parts = [num2words_kk.cardinal_kk(hours)]
    if minutes:
        parts.append(num2words_kk.cardinal_kk(minutes))
    reading = " ".join(parts)
    suffix = m.group(3)
    if suffix:
        low = suffix.lower()
        if low in _WRITTEN_CASE:
            reading = num2words_kk.attach_case(reading, _WRITTEN_CASE[low])
        else:
            reading += " " + suffix
    return reading


def _phone_replacement(m: re.Match) -> str:
    return "плюс " + num2words_kk.digits_kk(m.group(0))


def _range_replacement(m: re.Match) -> str:
    left = num2words_kk.attach_case(num2words_kk.cardinal_kk(int(m.group(1))), "ablative")
    right = num2words_kk.attach_case(num2words_kk.cardinal_kk(int(m.group(2))), "dative")
    return f"{left} {right} дейін"


def expand_numbers_kk(text: str) -> str:
    """Expand digit numbers into Kazakh words for synthesis (stages 1-3).

    Order matters: dates, time, phones and ranges consume their digits first, then
    the general number pass handles the rest (cardinals, decimals, percent/tenge,
    ordinals, case suffixes, year/century/month context). Applied per segment right
    before the TTS model, so the UI keeps the original digits.
    """
    text = _DATE_RE.sub(_date_replacement, text)
    text = _TIME_RE.sub(_time_replacement, text)
    text = _PHONE_RE.sub(_phone_replacement, text)
    text = _RANGE_RE.sub(_range_replacement, text)
    return _NUMBER_RE.sub(_number_replacement, text)


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
