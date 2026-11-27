"""Source binding must preserve roots, local refs and honest candidate status."""
import copy
import json

import pytest

from sn import source_expansion as s


@pytest.fixture(scope="module")
def cards():
    return s.load()


def test_eight_source_cards_have_valid_examples_and_real_hashes(cards):
    cards, raws = cards
    assert len(cards) == 8
    for c in cards:
        assert s.common.su.sha(raws[c["card_id"]]) == c["schema_sha256"]
        assert s.validator(c, raws[c["card_id"]]).is_valid(c["example"])


def test_caption_wrapper_preserves_local_reference_root(cards):
    cards, raws = cards
    card = next(c for c in cards if c["card_id"] == "X006")
    raw = raws["X006"]; original = copy.deepcopy(raw)
    wrapped = s.validator(card, raw); direct = s.common.validator(raw)
    examples = [card["example"]["value"], [], [[{"time": "bad", "type": "text", "text": "Hi"}]], [17]]
    for value in examples:
        assert wrapped.is_valid({"value": value}) == direct.is_valid(value)
    assert not wrapped.is_valid({"value": card["example"]["value"], "extra": True})
    assert raw == original


def test_country_code_wrapper_does_not_turn_names_into_codes(cards):
    cards, raws = cards
    card = next(c for c in cards if c["card_id"] == "X007")
    assert s.validator(card, raws["X007"]).is_valid({"value": "CR"})
    assert not s.validator(card, raws["X007"]).is_valid({"value": "Costa Rica"})


def test_unknown_binding_is_not_guessed(cards):
    cards, raws = cards
    card = dict(cards[0], binding="invented")
    with pytest.raises(ValueError, match="Unknown source binding"):
        s.binding(card, raws[card["card_id"]])


def test_source_audit_cannot_claim_real_apis_or_insert_competitors():
    files = s.build()
    rows = [json.loads(line) for line in files["cards.jsonl"].splitlines()]
    summary = json.loads(files["validation.json"])
    assert all(not r["production_endpoint_verified"] and not r["near_miss_verified"] for r in rows)
    assert all(not r["catalog_insertion_approved"] and r["split"] == "development_only" for r in rows)
    assert all(r["exact_frozen_pool_match"] is None for r in rows)
    assert summary["near_misses_verified"] == summary["catalog_insertions"] == summary["approved_test_intents"] == 0
    assert summary["remaining_unrepresented_gap_targets"] == ["T045", "T243"]
