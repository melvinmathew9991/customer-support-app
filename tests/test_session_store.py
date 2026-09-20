import json
import sqlite3

import pytest

from customer_support_app.session_store import SessionRecord, SessionStore, SessionStoreError


def _record(session_id="s1", **overrides):
    fields = dict(
        session_id=session_id,
        conversation_id="conv-1",
        node="AuthenticatedUserNode",
        node_input={"type": "UserProfile", "data": {"name": "Michael Jackson", "user_id": 1}},
        edge_fails={"UserInfoChainBasedEdge": 0, "CallCustomerEdge": 2},
        messages=[
            {"role": "assistant", "content": "welcome"},
            {"role": "user", "content": "michaeljackson@gmail.com"},
        ],
        is_over=False,
    )
    fields.update(overrides)
    return SessionRecord(**fields)


@pytest.fixture
def store(tmp_path):
    return SessionStore(tmp_path / "sessions.sqlite")


def test_a_saved_session_round_trips_exactly(store):
    record = _record()

    store.save(record)

    assert store.load("s1") == record


@pytest.mark.parametrize(
    "node_input",
    [
        None,
        {"type": "UserProfile", "data": {"name": "A", "user_id": 1}},
        {"type": "PhoneCallRequest", "data": {"phone_number": "0452 333 666"}},
        {"type": "MessageOutput", "data": {"message": "could not verify", "role": "system"}},
    ],
)
def test_every_kind_of_node_input_round_trips(store, node_input):
    store.save(_record(node_input=node_input))

    assert store.load("s1").node_input == node_input


def test_saving_again_replaces_the_row_instead_of_adding_one(store, tmp_path):
    store.save(_record())
    store.save(_record(messages=[{"role": "user", "content": "second"}], is_over=True))

    loaded = store.load("s1")
    assert loaded.messages == [{"role": "user", "content": "second"}]
    assert loaded.is_over is True
    with sqlite3.connect(tmp_path / "sessions.sqlite") as conn:
        assert conn.execute("SELECT COUNT(*) FROM sessions").fetchone()[0] == 1


def test_an_unknown_session_loads_as_none(store):
    assert store.load("nope") is None


def test_sessions_are_kept_apart(store):
    store.save(_record("a", conversation_id="conv-a"))
    store.save(_record("b", conversation_id="conv-b"))

    assert store.load("a").conversation_id == "conv-a"
    assert store.load("b").conversation_id == "conv-b"


def test_data_survives_opening_the_store_again(tmp_path):
    path = tmp_path / "sessions.sqlite"
    SessionStore(path).save(_record())

    assert SessionStore(path).load("s1") == _record()


def test_the_database_folder_is_created_when_missing(tmp_path):
    store = SessionStore(tmp_path / "data" / "nested" / "sessions.sqlite")

    store.save(_record())

    assert store.load("s1") is not None


def test_latest_unfinished_returns_the_most_recently_saved_open_session(store):
    store.save(_record("old"))
    store.save(_record("finished", is_over=True))
    store.save(_record("new"))
    store.save(_record("finished-later", is_over=True))

    assert store.latest_unfinished() == "new"

    store.save(_record("old"))  # saving again makes it the most recent

    assert store.latest_unfinished() == "old"


def test_latest_unfinished_is_none_when_nothing_is_open(store):
    assert store.latest_unfinished() is None
    store.save(_record(is_over=True))
    assert store.latest_unfinished() is None


def _corrupt(tmp_path, column, value):
    with sqlite3.connect(tmp_path / "sessions.sqlite") as conn:
        conn.execute(f"UPDATE sessions SET {column} = ? WHERE session_id = 's1'", (value,))


@pytest.mark.parametrize(
    ("column", "value"),
    [
        ("messages", "{not json"),
        ("messages", json.dumps({"not": "a list"})),
        ("messages", json.dumps([{"role": "user"}])),
        ("edge_fails", "[]"),
        ("node_input", "[1, 2]"),
        ("node_input", "{broken"),
    ],
)
def test_an_unreadable_row_warns_and_loads_as_none(store, tmp_path, caplog, column, value):
    store.save(_record())
    _corrupt(tmp_path, column, value)

    with caplog.at_level("WARNING", logger="customer_support_app.session_store"):
        assert store.load("s1") is None

    assert any("unreadable saved session" in r.getMessage() for r in caplog.records)


def test_a_fresh_file_is_brought_up_to_the_current_schema(tmp_path):
    path = tmp_path / "sessions.sqlite"

    SessionStore(path)

    with sqlite3.connect(path) as conn:
        assert conn.execute("PRAGMA user_version").fetchone()[0] == 1
        tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")]
    assert tables == ["sessions"]


def test_opening_an_existing_current_schema_file_changes_nothing(tmp_path):
    path = tmp_path / "sessions.sqlite"
    SessionStore(path).save(_record())

    SessionStore(path)

    assert SessionStore(path).load("s1") == _record()


def test_a_database_from_a_newer_schema_is_refused(tmp_path):
    path = tmp_path / "sessions.sqlite"
    with sqlite3.connect(path) as conn:
        conn.execute("PRAGMA user_version = 99")

    with pytest.raises(SessionStoreError, match="schema 99"):
        SessionStore(path)


def test_a_failed_migration_leaves_no_half_built_schema(tmp_path, monkeypatch):
    import customer_support_app.session_store as module

    def broken(conn):
        conn.execute("CREATE TABLE partial (x INTEGER)")
        raise RuntimeError("boom")

    monkeypatch.setattr(module, "_MIGRATIONS", [broken])
    path = tmp_path / "sessions.sqlite"

    with pytest.raises(RuntimeError):
        SessionStore(path)

    with sqlite3.connect(path) as conn:
        assert conn.execute("PRAGMA user_version").fetchone()[0] == 0
        assert conn.execute("SELECT name FROM sqlite_master").fetchall() == []
