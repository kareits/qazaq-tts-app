"""Tests for sentence-range selection and its validation."""

import pytest

from app.services.tts_service import _select_range

# _select_range only relies on list length and slicing, so minimal dicts suffice.
SENTENCES = [{"index": i} for i in range(3)]


def test_none_returns_all():
    assert _select_range(SENTENCES, None) == SENTENCES


def test_subrange_inclusive():
    assert _select_range(SENTENCES, {"from": 1, "to": 2}) == SENTENCES[1:3]


def test_single_sentence():
    assert _select_range(SENTENCES, {"from": 0, "to": 0}) == [SENTENCES[0]]


def test_invalid_order_raises():
    with pytest.raises(ValueError):
        _select_range(SENTENCES, {"from": 2, "to": 1})


def test_out_of_bounds_raises():
    with pytest.raises(ValueError):
        _select_range(SENTENCES, {"from": 0, "to": 5})
    with pytest.raises(ValueError):
        _select_range(SENTENCES, {"from": -1, "to": 1})
