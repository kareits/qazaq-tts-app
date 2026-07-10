"""Tests for number expansion in text and the decimal-aware sentence splitter
(NUMBERS.md stages 1-2)."""

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
        # --- Stage 2: hyphen + attributive word -> ordinal ---
        ("5-сынып", "бесінші сынып"),
        # --- Stage 2: context ordinal for a year / century ---
        ("2015 жыл", "екі мың он бесінші жыл"),
        ("2024 жылы", "екі мың жиырма төртінші жылы"),
        ("21 ғасыр", "жиырма бірінші ғасыр"),
        # ...but a duration stays cardinal.
        ("2 жыл бойы", "екі жыл бойы"),
    ],
)
def test_expand(text, expected):
    assert tn.expand_numbers_kk(text) == expected


def test_expand_leaves_dates_for_stage3():
    # Dotted dates are still left untouched (stage 3).
    assert tn.expand_numbers_kk("05.05.2024 жыл") == "05.05.2024 жыл"


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
