"""Tests for number expansion in text and the decimal-aware sentence splitter
(NUMBERS.md stages 1-3)."""

import pytest

from app.services import text_normalizer as tn


@pytest.mark.parametrize(
    "text,expected",
    [
        # --- Stage 1: cardinals, decimals, percent, tenge ---
        ("Бізде 1250 кітап бар", "Бізде мың екі жүз елу кітап бар"),
        ("5% жеңілдік", "бес пайыз жеңілдік"),
        ("1000 ₸", "мың теңге"),
        ("Баға 3,14", "Баға үш бүтін жүзден он төрт"),
        ("Баға 3.14", "Баға үш бүтін жүзден он төрт"),
        ("1 000 000 адам", "бір миллион адам"),
        ("-5 градус", "минус бес градус"),
        ("Сәлем әлем", "Сәлем әлем"),
        # --- Stage 2: ordinals (explicit marker) ---
        ("5-ші орын", "бесінші орын"),
        ("2-ші", "екінші"),
        ("21-ші", "жиырма бірінші"),
        # --- Stage 2: case suffixes (allomorph re-derived from the word) ---
        ("10-ға дейін", "онға дейін"),
        ("100-ға", "жүзге"),
        ("5-тен", "бестен"),
        # A harmony-wrong written suffix is corrected from the spelled word:
        # "10-ге" (front) -> "онға" (он is back).
        ("10-ге", "онға"),
        # --- Stage 2: hyphen + attributive word -> ordinal ---
        ("5-сынып", "бесінші сынып"),
        # --- Stage 2: context ordinal for a year / century ---
        ("2015 жыл", "екі мың он бесінші жыл"),
        ("2024 жылы", "екі мың жиырма төртінші жылы"),
        ("21 ғасыр", "жиырма бірінші ғасыр"),
        ("2 жыл бойы", "екі жыл бойы"),
        # --- Stage 3: dates ---
        ("05.05.2024", "бесінші мамыр екі мың жиырма төртінші жыл"),
        ("31.12.1999", "отыз бірінші желтоқсан мың тоғыз жүз тоқсан тоғызыншы жыл"),
        # No double "жыл" when the text already has it.
        ("05.05.2024 жыл", "бесінші мамыр екі мың жиырма төртінші жыл"),
        # Textual date: day before a month name -> ordinal.
        ("5 мамыр", "бесінші мамыр"),
        ("5 мамыр 2024 жыл", "бесінші мамыр екі мың жиырма төртінші жыл"),
        # Invalid date (month 13) — left unchanged.
        ("45.13.2024", "45.13.2024"),
        # --- Stage 3: time ---
        ("14:30", "он төрт отыз"),
        ("9:00", "тоғыз"),
        ("сағат 14:30", "сағат он төрт отыз"),
        # Time with a case suffix — attached to the last word (harmony-correct).
        ("сағат 14:30-да", "сағат он төрт отызда"),
        ("9:00-дан", "тоғыздан"),
        ("18:00-ге", "он сегізге"),
        # --- Stage 3: phone (digit by digit) ---
        (
            "+77011234567",
            "плюс жеті жеті нөл бір бір екі үш төрт бес алты жеті",
        ),
        (
            "+7 701 123 45 67",
            "плюс жеті жеті нөл бір бір екі үш төрт бес алты жеті",
        ),
        # --- Stage 3: ranges (en dash only) ---
        ("5–10", "бестен онға дейін"),
        ("2020–2024", "екі мың жиырмадан екі мың жиырма төртке дейін"),
        # A plain hyphen is NOT a range (ambiguous): the two numbers are just read
        # as cardinals ("екі-бір"), not "…дан …ға дейін".
        ("2-1 есеп", "екі-бір есеп"),
    ],
)
def test_expand(text, expected):
    assert tn.expand_numbers_kk(text) == expected


def test_mixed_date_and_time_sentence():
    out = tn.expand_numbers_kk("Кездесу 05.05.2024, сағат 14:30-да")
    assert out == (
        "Кездесу бесінші мамыр екі мың жиырма төртінші жыл, "
        "сағат он төрт отызда"
    )


def test_decimal_not_a_sentence_break():
    assert [s["text"] for s in tn.split_sentences("3.14")] == ["3.14"]
    assert [s["text"] for s in tn.split_sentences("05.05.2024 жыл.")] == [
        "05.05.2024 жыл."
    ]


def test_decimal_split_still_finds_real_terminators():
    sentences = tn.split_sentences("Баға 3.14 теңге. Рахмет.")
    assert [s["text"] for s in sentences] == ["Баға 3.14 теңге.", "Рахмет."]


def test_trailing_dot_after_decimal_ends_sentence():
    # Internal dot is a decimal; the final dot is a real terminator.
    assert [s["text"] for s in tn.split_sentences("Цена 1.5.")] == ["Цена 1.5."]
