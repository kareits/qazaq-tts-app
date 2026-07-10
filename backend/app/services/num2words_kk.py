"""Kazakh number-to-words for TTS.

Stage 1 (NUMBERS.md): cardinal numerals — integers and decimals. Ordinals and
case-suffix morphology come in later stages. Pure functions, no external
dependencies (the `num2words` package has no usable Kazakh morphology).

All spoken forms should be validated by a native speaker before release (D4).
"""

# Units 1..9 and tens 10..90 (index 0 unused).
_ONES = ["", "бір", "екі", "үш", "төрт", "бес", "алты", "жеті", "сегіз", "тоғыз"]
_TENS = ["", "он", "жиырма", "отыз", "қырық", "елу", "алпыс", "жетпіс", "сексен", "тоқсан"]

# Scale words above the hundred, largest first.
_SCALES = [
    (10**12, "триллион"),
    (10**9, "миллиард"),
    (10**6, "миллион"),
    (10**3, "мың"),
]

# Ablative forms of the 10**k denominators used to read the fractional part
# ("3,14" -> "үш бүтін жүзден он төрт"); key = number of fractional digits.
_FRACTION_DENOM = {
    1: "оннан",
    2: "жүзден",
    3: "мыңнан",
    4: "он мыңнан",
    5: "жүз мыңнан",
    6: "миллионнан",
}


def _below_1000(n: int) -> list[str]:
    """Spell 1..999 as a list of words."""
    words: list[str] = []
    hundreds, rem = divmod(n, 100)
    if hundreds:
        # "бір жүз" is said simply "жүз".
        if hundreds > 1:
            words.append(_ONES[hundreds])
        words.append("жүз")
    tens, units = divmod(rem, 10)
    if tens:
        words.append(_TENS[tens])
    if units:
        words.append(_ONES[units])
    return words


def _positive_int_words(n: int) -> list[str]:
    """Spell a positive integer (< 10**15) as a list of words."""
    words: list[str] = []
    for value, name in _SCALES:
        if n >= value:
            count, n = divmod(n, value)
            # "бір мың" is said simply "мың"; "бір миллион" keeps "бір".
            if not (name == "мың" and count == 1):
                words.extend(_below_1000(count))
            words.append(name)
    if n:
        words.extend(_below_1000(n))
    return words


def _digit_by_digit(digits: str) -> str:
    """Read a run of digits one by one (fallback for out-of-range/long parts)."""
    return " ".join("нөл" if d == "0" else _ONES[int(d)] for d in digits)


def cardinal_kk(n: int) -> str:
    """Cardinal numeral for an integer, e.g. 2024 -> 'екі мың жиырма төрт'."""
    if n < 0:
        return "минус " + cardinal_kk(-n)
    if n == 0:
        return "нөл"
    if n >= 10**15:
        # Out of the supported range — read digit by digit.
        return _digit_by_digit(str(n))
    return " ".join(_positive_int_words(n))


def decimal_kk(int_part: int, frac_digits: str) -> str:
    """Read a decimal: (3, '14') -> 'үш бүтін жүзден он төрт'.

    frac_digits keeps significant leading zeros, so (3, '05') ->
    'үш бүтін жүзден бес' (five hundredths).
    """
    whole = cardinal_kk(int_part)
    numerator = int(frac_digits)
    if numerator == 0:
        # e.g. "3,0" / "3,00" — just the whole part.
        return whole
    denom = _FRACTION_DENOM.get(len(frac_digits))
    if denom is None:
        # Unusual precision (>6 digits) — read the fraction digit by digit.
        return f"{whole} бүтін {_digit_by_digit(frac_digits)}"
    return f"{whole} бүтін {denom} {cardinal_kk(numerator)}"
