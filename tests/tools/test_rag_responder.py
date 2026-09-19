from types import SimpleNamespace

import pytest
from langchain_core.embeddings import DeterministicFakeEmbedding

from customer_support_app.tools import rag_responder
from customer_support_app.tools.rag_responder import HelpCenterAgent


@pytest.fixture
def kb(tmp_path, monkeypatch):
    """A tiny two-tier knowledge base in a temp dir, with fake embeddings (no Ollama)."""
    assets = tmp_path / "assets"
    for tier in ("free", "paid"):
        (assets / tier).mkdir(parents=True)
        (assets / tier / "locations.txt").write_text(f"{tier} locations: one place.", "utf-8")
        (assets / tier / "payments.txt").write_text(f"{tier} payments: cards.", "utf-8")
    settings = SimpleNamespace(assets_dir=assets, chroma_dir=tmp_path / "chroma")
    monkeypatch.setattr(rag_responder, "get_settings", lambda: settings)
    fake = DeterministicFakeEmbedding(size=16)
    monkeypatch.setattr(rag_responder, "get_embeddings", lambda: fake)
    return SimpleNamespace(assets=assets)


def _stored_texts(agent, tier):
    return sorted(agent._dbs[tier]._collection.get()["documents"])


def test_fresh_index_matches_assets(kb):
    agent = HelpCenterAgent()

    for tier in ("free", "paid"):
        status = agent.index_status(tier)
        assert status["ok"] is True
        assert status["indexed_chunks"] == status["expected_chunks"] == 2


def test_chunk_ids_are_stable_and_relative(kb):
    ids_first = HelpCenterAgent.load_chunks(kb.assets / "free")[1]
    ids_second = HelpCenterAgent.load_chunks(kb.assets / "free")[1]

    assert ids_first == ids_second == ["locations.txt#0", "payments.txt#0"]


def test_editing_assets_makes_index_stale_until_reindexed(kb):
    agent = HelpCenterAgent()
    edited = "free locations: a single place only."
    (kb.assets / "free" / "locations.txt").write_text(edited, "utf-8")

    stale = agent.index_status("free")
    assert stale["ok"] is False
    assert stale["missing"] == 1 and stale["extra"] == 1
    assert agent.index_status("paid")["ok"] is True

    assert agent.reindex(["free"]) == {"free": 2}

    assert agent.index_status("free")["ok"] is True
    assert "free locations: a single place only." in _stored_texts(agent, "free")
    assert "free locations: one place." not in _stored_texts(agent, "free")


def test_reindex_is_idempotent_and_leaves_no_duplicates(kb):
    agent = HelpCenterAgent()

    for _ in range(3):
        assert agent.reindex() == {"free": 2, "paid": 2}

    assert agent.index_status("free")["indexed_chunks"] == 2
    assert agent.index_status("paid")["indexed_chunks"] == 2


def test_removed_asset_file_is_dropped_on_reindex(kb):
    agent = HelpCenterAgent()
    (kb.assets / "free" / "payments.txt").unlink()

    stale = agent.index_status("free")
    assert stale["ok"] is False and stale["extra"] == 1

    assert agent.reindex(["free"]) == {"free": 1}
    assert agent.index_status("free")["ok"] is True
    assert _stored_texts(agent, "free") == ["free locations: one place."]


def test_reindexing_one_tier_leaves_the_other_untouched(kb):
    agent = HelpCenterAgent()
    (kb.assets / "paid" / "locations.txt").write_text("paid locations: many places.", "utf-8")

    agent.reindex(["free"])

    assert agent.index_status("free")["ok"] is True
    assert agent.index_status("paid")["ok"] is False


def test_reusing_a_populated_index_does_not_duplicate(kb):
    HelpCenterAgent()
    agent = HelpCenterAgent()

    assert agent.index_status("free")["indexed_chunks"] == 2


def test_stale_index_logs_a_warning_on_startup(kb, caplog):
    HelpCenterAgent()
    (kb.assets / "free" / "payments.txt").write_text("free payments: changed.", "utf-8")

    with caplog.at_level("WARNING"):
        HelpCenterAgent()

    assert any("out of date" in r.message and "free" in r.message for r in caplog.records)
    assert not any("'paid'" in r.message for r in caplog.records)
