"""Tests for the Kazakh number-to-words core (NUMBERS.md stage 1: cardinals)."""

import pytest

from app.services import num2words_kk as n


@pytest.mark.parametrize(
    "value,expected",
    [
        (0, "нөл"),
        (1, "бір"),
        (5, "бес"),
        (9, "тоғыз"),
        (10, "он"),
        (11, "он бір"),
        (19, "он тоғыз"),
        (20, "жиырма"),
        (21, "жиырма бір"),
        (40, "қырық"),
        (90, "тоқсан"),
        (99, "тоқсан тоғыз"),
        (100, "жүз"),
        (101, "жүз бір"),
        (200, "екі жүз"),
        (234, "екі жүз отыз төрт"),
        (999, "тоғыз жүз тоқсан тоғыз"),
        (1000, "мың"),
        (1001, "мың бір"),
        (1250, "мың екі жүз елу"),
        (2000, "екі мың"),
        (2024, "екі мың жиырма төрт"),
        (1000000, "бір миллион"),
        (2000000, "екі миллион"),
        (1234567, "бір миллион екі жүз отыз төрт мың бес жүз алпыс жеті"),
        (1000000000, "бір миллиард"),
    ],
)
def test_cardinal(value, expected):
    assert n.cardinal_kk(value) == expected


def test_cardinal_negative():
    assert n.cardinal_kk(-5) == "минус бес"
    assert n.cardinal_kk(-2024) == "минус екі мың жиырма төрт"


def test_cardinal_leading_one_omitted_only_for_hundred_and_thousand():
    # "бір жүз"/"бір мың" -> "жүз"/"мың"; but "бір миллион" keeps "бір".
    assert n.cardinal_kk(100) == "жүз"
    assert n.cardinal_kk(1000) == "мың"
    assert n.cardinal_kk(1000000) == "бір миллион"


@pytest.mark.parametrize(
    "int_part,frac,expected",
    [
        (3, "14", "үш бүтін жүзден он төрт"),
        (3, "5", "үш бүтін оннан бес"),
        (3, "05", "үш бүтін жүзден бес"),
        (0, "5", "нөл бүтін оннан бес"),
        (3, "0", "үш"),      # .0 -> just the whole part
        (3, "00", "үш"),
    ],
)
def test_decimal(int_part, frac, expected):
    assert n.decimal_kk(int_part, frac) == expected
