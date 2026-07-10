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


# --- Number expansion (NUMBERS.md, stages 1-3 + D4 review) -----------------
#
# A number token: optional sign, an integer (plain or space-grouped "1 000 000"),
# an optional decimal (comma or dot — comma is primary in Kazakh), an optional
# hyphen suffix ("5-ші" ordinal, "10-ға" case, "5-сынып" word), an optional unit
# (% or ₸) and an optional post-unit case suffix ("₸-ден"). Dates, time, phones,
# №, and ranges are handled by dedicated passes that run before this one.
_CYR = "а-яёәғқңөұүһі"
_NUMBER_RE = re.compile(
    r"(?<!\w)(-)?(\d{1,3}(?:[\s ]\d{3})+|\d+)([.,]\d+)?"
    r"(?:-([" + _CYR + r"]+))?(\s?[%₸])?(?:-([" + _CYR + r"]+))?",
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

# Context words: a bare "N <word>" reads the number as an ordinal (D1).
_YEAR_WORDS = {"жыл", "жылы", "жылғы", "жылдың", "жылдан", "жылда"}
_CENTURY_WORDS = {"ғасыр", "ғасырда", "ғасырдың", "ғасырға"}
_MONTHS = {
    1: "қаңтар", 2: "ақпан", 3: "наурыз", 4: "сәуір", 5: "мамыр", 6: "маусым",
    7: "шілде", 8: "тамыз", 9: "қыркүйек", 10: "қазан", 11: "қараша",
    12: "желтоқсан",
}
_MONTH_STEMS = tuple(_MONTHS.values())
# A number preceded by these words is read digit by digit (codes/PINs).
_CODE_WORDS = {"код", "коды", "пин", "pin"}
# A decimal preceded by these words is a version number ("2.0" -> "екі нүкте нөл").
_VERSION_WORDS = {"версия", "нұсқа", "версиясы"}

_NEXT_WORD_RE = re.compile(r"\s+([" + _CYR + r"]+)", re.IGNORECASE)
_PREV_WORD_RE = re.compile(r"([" + _CYR + r"]+)\s*$", re.IGNORECASE)


def _next_word(s: str, end: int) -> str:
    m = _NEXT_WORD_RE.match(s, end)
    return m.group(1).lower() if m else ""


def _prev_word(s: str, start: int) -> str:
    m = _PREV_WORD_RE.search(s[:start])
    return m.group(1).lower() if m else ""


def _is_month_context(word: str) -> bool:
    """True if the word is a month name, possibly case-inflected ("шілдеде")."""
    return word.startswith(_MONTH_STEMS)


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


def _apply_case_tail(reading: str, tail: str | None) -> str:
    """Attach a post-unit case suffix ("2500 ₸-ден" -> "…теңгеден")."""
    if tail:
        low = tail.lower()
        if low in _WRITTEN_CASE:
            return num2words_kk.attach_case(reading, _WRITTEN_CASE[low])
        return reading + " " + tail
    return reading


def _number_replacement(m: re.Match) -> str:
    """Replace one number token with its Kazakh reading, or leave it unchanged if
    it is part of a dotted chain the date pass did not consume."""
    s = m.string
    start, end = m.start(), m.end()
    sign, int_raw, frac_raw, suffix, unit_raw, case_tail = m.group(1, 2, 3, 4, 5, 6)

    # Part of a longer dotted/comma digit chain (unparsed date/version) — leave it.
    if start >= 2 and s[start - 1] in ".," and s[start - 2].isdigit():
        return m.group(0)
    if not suffix:
        after = s[end : end + 2]
        if after[:1] in ".," and len(after) >= 2 and after[1].isdigit():
            return m.group(0)

    digits = re.sub(r"[\s ]", "", int_raw)
    int_val = int(digits)
    prev = _prev_word(s, start)

    # Decimal — or a version number ("Версия 2.0" -> "екі нүкте нөл").
    if frac_raw:
        frac_digits = frac_raw[1:]
        if prev in _VERSION_WORDS:
            frac_read = (
                num2words_kk.digits_kk(frac_digits)
                if frac_digits.startswith("0")
                else num2words_kk.cardinal_kk(int(frac_digits))
            )
            reading = f"{num2words_kk.cardinal_kk(int_val)} нүкте {frac_read}"
            return _with_sign(reading, sign)
        reading = num2words_kk.decimal_kk(int_val, frac_digits)
        return _apply_case_tail(_apply_unit(_with_sign(reading, sign), unit_raw), case_tail)

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

    # Context ordinal: day before a month ("5 мамыр" / "10 шілдеде"), a 4-digit
    # year ("2015 жыл"), or a century ("21 ғасыр").
    word = _next_word(s, end)
    if _is_month_context(word) and 1 <= int_val <= 31:
        return _with_sign(num2words_kk.ordinal_kk(int_val), sign)
    if (word in _YEAR_WORDS and 1000 <= int_val <= 2999) or (
        word in _CENTURY_WORDS and 1 <= int_val <= 40
    ):
        return _with_sign(num2words_kk.ordinal_kk(int_val), sign)

    # Codes / PINs / leading-zero numbers -> read digit by digit.
    if prev in _CODE_WORDS or (len(digits) > 1 and digits[0] == "0"):
        return _with_sign(num2words_kk.digits_kk(digits), sign)

    reading = _with_sign(num2words_kk.cardinal_kk(int_val), sign)
    return _apply_case_tail(_apply_unit(reading, unit_raw), case_tail)


# --- Dates, time, phones, №, ranges ----------------------------------------

# Dotted date dd.mm.yyyy (requires the 4-digit year to avoid clashing with
# decimals like "05.05").
_DATE_RE = re.compile(r"(?<!\d)(\d{1,2})\.(\d{1,2})\.(\d{4})(?!\d)")

# Time HH:MM (24h) with an optional case suffix ("14:30-да").
_TIME_RE = re.compile(
    r"(?<!\d)([01]?\d|2[0-3]):([0-5]\d)(?:-([" + _CYR + r"]+))?(?!\d)",
    re.IGNORECASE,
)
# Time range with an en/em dash ("9:30–17:45" -> "…бен…").
_TIME_RANGE_RE = re.compile(
    r"(?<!\d)(\d{1,2}:[0-5]\d)\s*[–—]\s*(\d{1,2}:[0-5]\d)(?!\d)"
)

# Phone: a leading "+" then 9+ digits with optional spaces/dashes/parens.
_PHONE_RE = re.compile(r"\+\d[\d()\s\-]{7,}\d")

# Numero sign before a number ("№5 кабинет" -> "бесінші кабинет").
_NUMERO_RE = re.compile(r"№\s*(\d+)")

# Numeric range with an en/em dash ("2020–2024"); an optional trailing "жыл..."
# word is consumed for year ranges. A plain hyphen is NOT a range (ambiguous
# with scores like "2-1").
_RANGE_RE = re.compile(
    r"(?<!\d)(\d{1,4})\s*[–—]\s*(\d{1,4})(?!\d)(\s+жыл[" + _CYR + r"]*)?",
    re.IGNORECASE,
)


def _read_clock(hhmm: str) -> str:
    """Read HH:MM as bare cardinals ("14:30" -> "он төрт отыз"), keeping the
    leading zero of minutes 01-09 as "нөл" ("14:05" -> "он төрт нөл бес")."""
    hh, mm = hhmm.split(":")
    parts = [num2words_kk.cardinal_kk(int(hh))]
    if int(mm) > 0:
        minute = num2words_kk.cardinal_kk(int(mm))
        parts.append(f"нөл {minute}" if mm.startswith("0") else minute)
    return " ".join(parts)


def _date_replacement(m: re.Match) -> str:
    day, month, year = int(m.group(1)), int(m.group(2)), int(m.group(3))
    if not (1 <= day <= 31 and 1 <= month <= 12):
        return m.group(0)  # not a real date (e.g. a version) — leave it
    day_o = num2words_kk.ordinal_kk(day)
    year_o = num2words_kk.ordinal_kk(year)
    month_name = _MONTHS[month]
    word = _next_word(m.string, m.end())
    if word == "күні":
        # "<year>-дың <day> <month> күні" — the year leads, in the genitive.
        return f"{year_o} жылдың {day_o} {month_name}"
    reading = f"{day_o} {month_name} {year_o}"
    if word in _YEAR_WORDS:
        return reading  # the text already carries жыл/жылы
    # Adverbial date ("31.12.2025 дайын болады") — the year takes "жылы".
    return reading + " жылы"


def _time_replacement(m: re.Match) -> str:
    reading = _read_clock(f"{m.group(1)}:{m.group(2)}")
    suffix = m.group(3)
    if suffix:
        low = suffix.lower()
        if low in _WRITTEN_CASE:
            reading = num2words_kk.attach_case(reading, _WRITTEN_CASE[low])
        else:
            reading += " " + suffix
    return reading


def _time_range_replacement(m: re.Match) -> str:
    left = _read_clock(m.group(1))
    right = _read_clock(m.group(2))
    conn = num2words_kk.postposition_kk(left.split()[-1])
    return f"{left} {conn} {right}"


def _phone_replacement(m: re.Match) -> str:
    return "плюс " + num2words_kk.digits_kk(m.group(0))


def _numero_replacement(m: re.Match) -> str:
    return num2words_kk.ordinal_kk(int(m.group(1)))


def _range_replacement(m: re.Match) -> str:
    a, b = int(m.group(1)), int(m.group(2))
    year_tail = m.group(3)
    # Year range -> ordinal years with "жыл" declined ("2020 жылдан 2024 жылға").
    if year_tail or (1000 <= a <= 2999 and 1000 <= b <= 2999):
        return (
            f"{num2words_kk.ordinal_kk(a)} жылдан "
            f"{num2words_kk.ordinal_kk(b)} жылға дейін"
        )
    left = num2words_kk.cardinal_kk(a)
    right = num2words_kk.cardinal_kk(b)
    # "120–150 аралығында" -> "жүз жиырма мен жүз елу аралығында" (no "дейін").
    if _next_word(m.string, m.end()) == "аралығында":
        conn = num2words_kk.postposition_kk(left.split()[-1])
        return f"{left} {conn} {right}"
    # Default numeric range: "X-дан Y-ға дейін".
    return (
        f"{num2words_kk.attach_case(left, 'ablative')} "
        f"{num2words_kk.attach_case(right, 'dative')} дейін"
    )


def expand_numbers_kk(text: str) -> str:
    """Expand digit numbers into Kazakh words for synthesis (stages 1-3 + review).

    Order matters: dates, time (ranges first), phones, №, and numeric ranges
    consume their digits first, then the general number pass handles the rest.
    Applied per segment right before the TTS model, so the UI keeps the digits.
    """
    text = _DATE_RE.sub(_date_replacement, text)
    text = _TIME_RANGE_RE.sub(_time_range_replacement, text)
    text = _TIME_RE.sub(_time_replacement, text)
    text = _PHONE_RE.sub(_phone_replacement, text)
    text = _NUMERO_RE.sub(_numero_replacement, text)
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
