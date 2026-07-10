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


def digits_kk(text: str) -> str:
    """Read every digit in the string one by one (for phone numbers, codes)."""
    return " ".join(
        "нөл" if ch == "0" else _ONES[int(ch)] for ch in text if ch.isdigit()
    )


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


# --- Ordinals (NUMBERS.md stage 2) ----------------------------------------
#
# Only the LAST word of a compound cardinal takes the ordinal suffix, and that
# last word is always one of these base words, so a lookup table (which also
# encodes the irregular stems қырық→қырқыншы, жиырма→жиырмасыншы) is enough.
_ORDINAL = {
    "нөл": "нөлінші",
    "бір": "бірінші", "екі": "екінші", "үш": "үшінші", "төрт": "төртінші",
    "бес": "бесінші", "алты": "алтыншы", "жеті": "жетінші", "сегіз": "сегізінші",
    "тоғыз": "тоғызыншы",
    "он": "оныншы", "жиырма": "жиырмасыншы", "отыз": "отызыншы",
    "қырық": "қырқыншы", "елу": "елуінші", "алпыс": "алпысыншы",
    "жетпіс": "жетпісінші", "сексен": "сексенінші", "тоқсан": "тоқсаныншы",
    "жүз": "жүзінші", "мың": "мыңыншы", "миллион": "миллионыншы",
    "миллиард": "миллиардыншы", "триллион": "триллионыншы",
}


def ordinal_kk(n: int) -> str:
    """Ordinal numeral: 2 -> 'екінші', 21 -> 'жиырма бірінші', 100 -> 'жүзінші'."""
    if n < 0:
        return "минус " + ordinal_kk(-n)
    words = cardinal_kk(n).split()
    words[-1] = _ORDINAL.get(words[-1], words[-1] + "ыншы")
    return " ".join(words)


# --- Case suffixes (NUMBERS.md stage 2) ------------------------------------
#
# Attach a grammatical case ending to the last word of a spelled number, with
# vowel harmony (front/back) and consonant assimilation. Rough working tables —
# to be validated by a native speaker (D4).
_BACK_VOWELS = "аоұы"
_FRONT_VOWELS = "әөүеі"
# Final-sound classes for choosing the allomorph. Note: final "у" is a
# semivowel/sonorant, not a plain vowel — "елу" takes consonant-type endings in
# the accusative/genitive ("елуді", "елудің"), so it is NOT in _VOWEL_ENDINGS.
_VOWEL_ENDINGS = "аәоөұүыіеиёэюя"
_VOICELESS = "кқпстфхшцчщ"
_NASALS = "мнң"           # sonorant nasals
_SONORANTS = "лруйw"      # sonorants л р у й (and semivowel у)
# everything else that is a consonant is a voiced obstruent (б в г ғ д ж з)

# (back, front) allomorph pairs by final-sound class; "_" is the default.
_CASE_ENDINGS = {
    "dative": {"voiceless": ("қа", "ке"), "_": ("ға", "ге")},
    "locative": {"voiceless": ("та", "те"), "_": ("да", "де")},
    "ablative": {"voiceless": ("тан", "тен"), "nasal": ("нан", "нен"),
                 "_": ("дан", "ден")},
    "accusative": {"vowel": ("ны", "ні"), "voiceless": ("ты", "ті"),
                   "_": ("ды", "ді")},
    "genitive": {"voiceless": ("тың", "тің"), "vowel": ("ның", "нің"),
                 "nasal": ("ның", "нің"), "_": ("дың", "дің")},
}
# Instrumental (does not harmonize front/back): after voiceless -> -пен, after a
# voiced obstruent (б в г ғ д ж з) -> -бен, after vowels/sonorants/nasals -> -мен.
_INSTRUMENTAL = {"voiceless": "пен", "voiced": "бен", "_": "мен"}


def _is_front(word: str) -> bool:
    """Vowel harmony: True if the last full front/back vowel is front."""
    for ch in reversed(word):
        if ch in _BACK_VOWELS:
            return False
        if ch in _FRONT_VOWELS:
            return True
    return False


def _final_class(word: str) -> str:
    last = word[-1].lower()
    if last in _VOWEL_ENDINGS:
        return "vowel"
    if last in _VOICELESS:
        return "voiceless"
    if last in _NASALS:
        return "nasal"
    if last in _SONORANTS:
        return "sonorant"
    return "voiced"


def postposition_kk(word: str) -> str:
    """The бен/мен/пен postposition ('and'/'with') for a word — same allomorph
    rule as the instrumental case. Used to join range parts ("X мен Y")."""
    return _INSTRUMENTAL.get(_final_class(word), _INSTRUMENTAL["_"])


def attach_case(words: str, case: str) -> str:
    """Attach a case ending to the last word of a spelled number.

    e.g. attach_case('он', 'dative') -> 'онға'; attach_case('жүз', 'dative') ->
    'жүзге' (allomorph re-derived from the spelled word, not the digit).
    """
    parts = words.split()
    last = parts[-1]
    cls = _final_class(last)
    if case == "instrumental":
        suffix = _INSTRUMENTAL.get(cls, _INSTRUMENTAL["_"])
    else:
        table = _CASE_ENDINGS[case]
        pair = table.get(cls, table["_"])
        suffix = pair[1] if _is_front(last) else pair[0]
    parts[-1] = last + suffix
    return " ".join(parts)


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
