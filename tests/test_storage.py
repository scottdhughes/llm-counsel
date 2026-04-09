"""Storage round-trip and concurrent-write safety tests."""

from __future__ import annotations

import multiprocessing
import os
import threading


def test_create_and_get_matter(isolated_data_dir):
    storage = isolated_data_dir
    matter = storage.create_matter(matter_name="Smith v. Acme")
    fetched = storage.get_matter(matter["id"])
    assert fetched is not None
    assert fetched["matter_name"] == "Smith v. Acme"
    assert fetched["messages"] == []


def test_get_returns_none_for_missing(isolated_data_dir):
    assert isolated_data_dir.get_matter("matter_missing") is None


def test_list_returns_newest_first(isolated_data_dir):
    storage = isolated_data_dir
    a = storage.create_matter(matter_name="A")
    b = storage.create_matter(matter_name="B")
    listed = storage.list_matters()
    assert [m["id"] for m in listed][:2] == [b["id"], a["id"]]


def test_delete_matter(isolated_data_dir):
    storage = isolated_data_dir
    matter = storage.create_matter()
    assert storage.delete_matter(matter["id"]) is True
    assert storage.delete_matter(matter["id"]) is False
    assert storage.get_matter(matter["id"]) is None


def test_append_user_then_assistant(isolated_data_dir):
    storage = isolated_data_dir
    matter = storage.create_matter()
    storage.append_user_message(matter["id"], "Question?", context="Some facts")
    storage.append_assistant_message(
        matter["id"],
        {
            "stage1": {"plaintiff_strategist": {"content": "..."}},
            "stage2": {
                "assessments": {},
                "label_mapping": {},
                "aggregate_rankings": [],
            },
            "stage3": {
                "model": "google/gemini-3.1-pro-preview",
                "content": "...",
                "error": None,
            },
        },
    )
    fetched = storage.get_matter(matter["id"])
    assert len(fetched["messages"]) == 2
    assert fetched["messages"][0]["role"] == "user"
    assert fetched["messages"][0]["context"] == "Some facts"
    assert fetched["messages"][1]["role"] == "assistant"
    assert "stage3" in fetched["messages"][1]


def test_concurrent_appends_do_not_lose_messages(isolated_data_dir):
    """Hammer the same matter from N threads; every message must be persisted."""
    storage = isolated_data_dir
    matter = storage.create_matter()
    n_threads = 10

    def append(i: int) -> None:
        storage.append_user_message(matter["id"], f"msg-{i}")

    threads = [
        threading.Thread(target=append, args=(i,)) for i in range(n_threads)
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    fetched = storage.get_matter(matter["id"])
    contents = sorted(m["content"] for m in fetched["messages"])
    assert contents == sorted(f"msg-{i}" for i in range(n_threads))


# Codex-driven addition: cross-process concurrency via fcntl


def _append_in_subprocess(data_dir, matter_id, content):
    """Worker for the cross-process concurrency test."""
    os.environ["DATA_DIR"] = str(data_dir)
    os.environ["OPENROUTER_API_KEY"] = "test"
    import importlib

    import backend.config
    import backend.storage

    importlib.reload(backend.config)
    importlib.reload(backend.storage)
    backend.storage.append_user_message(matter_id, content)


def test_update_matter_metadata_changes_fields(isolated_data_dir):
    storage = isolated_data_dir
    matter = storage.create_matter(
        matter_name="Original",
        practice_area="civil",
        jurisdiction="federal",
    )
    updated = storage.update_matter_metadata(
        matter["id"],
        matter_name="Renamed",
        jurisdiction="state-ca",
    )
    assert updated is not None
    assert updated["matter_name"] == "Renamed"
    assert updated["jurisdiction"] == "state-ca"
    assert updated["practice_area"] == "civil"  # unchanged

    # Persisted to disk
    fetched = storage.get_matter(matter["id"])
    assert fetched["matter_name"] == "Renamed"
    assert fetched["jurisdiction"] == "state-ca"


def test_update_matter_metadata_ignores_none_and_unknown_fields(isolated_data_dir):
    storage = isolated_data_dir
    matter = storage.create_matter(
        matter_name="Keep",
        practice_area="civil",
        jurisdiction="federal",
    )
    updated = storage.update_matter_metadata(
        matter["id"],
        matter_name=None,  # None values must not clobber
        jurisdiction="state-ny",
        messages="EVIL",  # not in the allowlist; must be ignored
    )
    assert updated["matter_name"] == "Keep"
    assert updated["jurisdiction"] == "state-ny"
    assert updated["messages"] == []  # untouched


def test_update_matter_metadata_returns_none_for_missing(isolated_data_dir):
    assert isolated_data_dir.update_matter_metadata("matter_nope", matter_name="x") is None


def test_update_matter_metadata_preserves_messages(isolated_data_dir):
    storage = isolated_data_dir
    matter = storage.create_matter(matter_name="With Messages")
    storage.append_user_message(matter["id"], "hi")
    storage.append_user_message(matter["id"], "there")
    storage.update_matter_metadata(matter["id"], matter_name="Renamed")

    fetched = storage.get_matter(matter["id"])
    assert fetched["matter_name"] == "Renamed"
    assert len(fetched["messages"]) == 2
    assert [m["content"] for m in fetched["messages"]] == ["hi", "there"]


def test_concurrent_appends_across_processes(isolated_data_dir, tmp_path):
    """Threads share an interpreter; processes don't. fcntl.flock is the
    only thing keeping cross-process writers from clobbering each other."""
    storage = isolated_data_dir
    matter = storage.create_matter()
    n = 6
    procs = [
        multiprocessing.Process(
            target=_append_in_subprocess,
            args=(tmp_path, matter["id"], f"proc-{i}"),
        )
        for i in range(n)
    ]
    for p in procs:
        p.start()
    for p in procs:
        p.join()
        assert p.exitcode == 0

    fetched = storage.get_matter(matter["id"])
    contents = sorted(m["content"] for m in fetched["messages"])
    assert contents == sorted(f"proc-{i}" for i in range(n))
