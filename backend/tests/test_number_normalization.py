"""Tests for number expansion in text and the decimal-aware sentence splitter
(NUMBERS.md stage 1)."""

import pytest

from app.services import text_normalizer as tn


@pytest.mark.parametrize(
    "text,expected",
    [
        # Cardinals inside a sentence.
        ("Бізде 1250 кітап бар", "Бізде мың екі жүз елу кітап бар"),
        ("2024 жылы", "екі мың жиырма төрт жылы"),
        # Percent and tenge.
        ("5% жеңілдік", "бес пайыз жеңілдік"),
        ("1000 ₸", "мың теңге"),
        # Decimals: comma (primary) and dot.
        ("Баға 3,14", "Баға үш бүтін жүзден он төрт"),
        ("Баға 3.14", "Баға үш бүтін жүзден он төрт"),
        # Grouped thousands.
        ("1 000 000 адам", "бір миллион адам"),
        # Negative.
        ("-5 градус", "минус бес градус"),
        # No digits — unchanged.
        ("Сәлем әлем", "Сәлем әлем"),
    ],
)
def test_expand(text, expected):
    assert tn.expand_numbers_kk(text) == expected


@pytest.mark.parametrize(
    "text",
    [
        "5-ші орын",       # ordinal marker -> stage 2
        "10-ға дейін",     # case suffix -> stage 2
        "05.05.2024 жыл",  # dotted date -> stage 3
    ],
)
def test_expand_leaves_later_stages_untouched(text):
    assert tn.expand_numbers_kk(text) == text


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
