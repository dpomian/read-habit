"""Tests for the JSON-backed reading session repository."""

import pytest

from read_habit.timer.models import PageRecord, TimerStats
from read_habit.timer.repository import SessionRepository


def make_stats(pages_read: int = 1) -> TimerStats:
    page = PageRecord(page_number=1, duration_seconds=10)
    return TimerStats(
        pages_read=pages_read,
        slowest_page=page,
        fastest_page=page,
        actual_reading_seconds=10,
        elapsed_seconds=10,
        paused_seconds=0,
    )


@pytest.fixture
def repo(tmp_path):
    return SessionRepository(path=tmp_path / "sessions.json")


def test_list_is_empty_when_file_does_not_exist(repo):
    assert repo.list() == []


def test_add_assigns_incrementing_ids(repo):
    first = repo.add(make_stats(), book_id=1)
    second = repo.add(make_stats(), book_id=None)

    assert first.id == 1
    assert first.book_id == 1
    assert second.id == 2
    assert second.book_id is None


def test_add_persists_across_repository_instances(tmp_path):
    path = tmp_path / "sessions.json"
    SessionRepository(path=path).add(make_stats(), book_id=5)

    reloaded = SessionRepository(path=path)
    sessions = reloaded.list()

    assert len(sessions) == 1
    assert sessions[0].book_id == 5
    assert sessions[0].stats.pages_read == 1


def test_list_is_sorted_by_id(repo):
    repo.add(make_stats())
    repo.add(make_stats())

    ids = [session.id for session in repo.list()]
    assert ids == sorted(ids)
