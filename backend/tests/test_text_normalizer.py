"""Tests for the single sentence-splitting function and text normalization —
the architectural keystone shared by /api/split and /api/tts."""

from app.services import text_normalizer as tn


def test_split_matches_spec_example():
    # The exact example from the specification.
    text = "Сәлеметсіз бе! Бұл мысал. Тағы бір сөйлем."
    sentences = tn.split_sentences(text)
    assert [(s["char_start"], s["char_end"]) for s in sentences] == [
        (0, 14),
        (15, 25),
        (26, 42),
    ]
    assert [s["text"] for s in sentences] == [
        "Сәлеметсіз бе!",
        "Бұл мысал.",
        "Тағы бір сөйлем.",
    ]
    assert [s["index"] for s in sentences] == [0, 1, 2]


def test_offsets_map_back_to_source_text():
    text = "  Бір.  Екі сөз.  Үшінші "
    for s in tn.split_sentences(text):
        assert text[s["char_start"] : s["char_end"]] == s["text"]


def test_multiple_consecutive_terminators_stay_together():
    sentences = tn.split_sentences("Не?! Иә... Бітті.")
    assert [s["text"] for s in sentences] == ["Не?!", "Иә...", "Бітті."]


def test_tail_without_terminator_is_a_sentence():
    sentences = tn.split_sentences("Бірінші. Нүктесіз екінші")
    assert [s["text"] for s in sentences] == ["Бірінші.", "Нүктесіз екінші"]


def test_empty_and_whitespace_only():
    assert tn.split_sentences("") == []
    assert tn.split_sentences("   \n\t  ") == []


def test_normalize_text_collapses_whitespace():
    assert tn.normalize_text("  a   b  c ") == "a b c"
    assert tn.normalize_text("\n\t x \n") == "x"
    assert tn.normalize_text("") == ""


def test_looks_like_kazakh():
    assert tn.looks_like_kazakh("қазақ тілі")  # Kazakh-specific letters present
    assert not tn.looks_like_kazakh("hello world")  # Latin
    assert not tn.looks_like_kazakh("12345 !!!")  # no letters


def test_kazakh_warning():
    assert tn.kazakh_warning("Сәлеметсіз бе") is None  # Kazakh → no warning
    assert tn.kazakh_warning("Hello world") is not None  # Latin → warning
