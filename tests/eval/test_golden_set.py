"""Structural checks on golden_set.json (no LLM, no Ollama).

Catches the mistakes that would silently corrupt an eval run: duplicate ids, a
category the harness has no scorer for, expected source files that don't exist
or belong to the wrong tier, and RAG entries missing the fields their scorer reads.
"""
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
GOLDEN = json.loads((ROOT / "tests" / "eval" / "golden_set.json").read_text(encoding="utf-8"))

_spec = importlib.util.spec_from_file_location("run_eval", ROOT / "tests" / "eval" / "run_eval.py")
_run_eval = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_run_eval)

KNOWN_EMAILS = {"john@doe.com", "michaeljackson@gmail.com", "carl@sagan.com"}
RAG_CATEGORIES = {
    "free_tier_question",
    "paid_tier_question",
    "adversarial_tier_crossing",
    "out_of_scope_question",
}
RAG = [e for e in GOLDEN if e["category"] in RAG_CATEGORIES]


def test_ids_are_unique():
    ids = [e["id"] for e in GOLDEN]
    assert len(ids) == len(set(ids))


def test_every_category_has_a_scorer():
    unknown = {e["category"] for e in GOLDEN} - set(_run_eval.CATEGORY_SCORERS)
    assert not unknown


@pytest.mark.parametrize("entry", RAG, ids=lambda e: e["id"])
def test_rag_entry_is_well_formed(entry):
    expected = entry["expected"]
    tier = expected["tier_used"]
    assert tier in ("free", "paid")
    assert len(entry["turns"]) == 2 and entry["turns"][0] in KNOWN_EMAILS

    files = expected["retrieval"]["expected_source_files"]
    if entry["category"] == "out_of_scope_question":
        assert files == [] and expected["expected_behavior"]
    else:
        assert files and expected["retrieval"]["expected_key_facts"]
    for f in files:
        assert f.startswith(f"assets/{tier}/"), f"{f} is not in the {tier} tier"
        assert (ROOT / f).is_file(), f"{f} does not exist"


def test_rag_id_prefix_matches_category():
    prefix = {
        "free_tier_question": "rag-free-",
        "paid_tier_question": "rag-paid-",
        "adversarial_tier_crossing": "rag-adv-",
        "out_of_scope_question": "rag-oos-",
    }
    for e in RAG:
        assert e["id"].startswith(prefix[e["category"]]), e["id"]
