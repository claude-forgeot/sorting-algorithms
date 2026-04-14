import json
import os
import pytest
from benchmarks.database import (
    init_db,
    insert_session,
    insert_runs,
    get_matrix,
    get_sessions,
    delete_session,
    update_session_note,
    import_legacy_json,
    get_run_count,
)


@pytest.fixture
def db_path(tmp_path):
    return str(tmp_path / "test.db")


@pytest.fixture
def populated_db(db_path):
    """Database with one session containing 2 algos x 2 datasets x 1 N."""
    init_db(db_path)
    sid = insert_session(db_path, note="test session")
    rows = [
        {
            "algorithm": "bubble",
            "dataset": "random_int",
            "n": 100,
            "time": 0.5,
            "comparisons": 4950,
            "swaps": 2400,
        },
        {
            "algorithm": "bubble",
            "dataset": "reversed",
            "n": 100,
            "time": 0.8,
            "comparisons": 4950,
            "swaps": 4950,
        },
        {
            "algorithm": "quick",
            "dataset": "random_int",
            "n": 100,
            "time": 0.01,
            "comparisons": 600,
            "swaps": 300,
        },
        {
            "algorithm": "quick",
            "dataset": "reversed",
            "n": 100,
            "time": 0.02,
            "comparisons": 700,
            "swaps": 350,
        },
    ]
    insert_runs(db_path, sid, rows)
    return db_path, sid


def test_init_creates_db(db_path):
    init_db(db_path)
    assert os.path.exists(db_path)


def test_insert_and_get_sessions(db_path):
    init_db(db_path)
    sid = insert_session(db_path, note="first run")
    sessions = get_sessions(db_path)
    assert len(sessions) == 1
    assert sessions[0]["id"] == sid
    assert sessions[0]["note"] == "first run"


def test_insert_runs_and_count(populated_db):
    db_path, _ = populated_db
    assert get_run_count(db_path) == 4


def test_get_matrix_avg(populated_db):
    db_path, _ = populated_db
    matrix = get_matrix(db_path, "time", "avg", 100)
    assert ("bubble", "random_int") in matrix
    assert ("quick", "reversed") in matrix
    assert matrix[("bubble", "random_int")] == pytest.approx(0.5)


def test_get_matrix_aggregation_with_multiple_sessions(db_path):
    init_db(db_path)

    # Session 1
    sid1 = insert_session(db_path, note="run 1")
    insert_runs(
        db_path,
        sid1,
        [
            {
                "algorithm": "bubble",
                "dataset": "random_int",
                "n": 100,
                "time": 0.4,
                "comparisons": 4950,
                "swaps": 2000,
            },
        ],
    )

    # Session 2
    sid2 = insert_session(db_path, note="run 2")
    insert_runs(
        db_path,
        sid2,
        [
            {
                "algorithm": "bubble",
                "dataset": "random_int",
                "n": 100,
                "time": 0.6,
                "comparisons": 4950,
                "swaps": 2800,
            },
        ],
    )

    avg = get_matrix(db_path, "time", "avg", 100)
    assert avg[("bubble", "random_int")] == pytest.approx(0.5)

    min_val = get_matrix(db_path, "time", "min", 100)
    assert min_val[("bubble", "random_int")] == pytest.approx(0.4)

    max_val = get_matrix(db_path, "time", "max", 100)
    assert max_val[("bubble", "random_int")] == pytest.approx(0.6)


def test_delete_session_cascades(populated_db):
    db_path, sid = populated_db
    assert get_run_count(db_path) == 4
    delete_session(db_path, sid)
    assert get_run_count(db_path) == 0
    assert len(get_sessions(db_path)) == 0


def test_update_session_note(populated_db):
    db_path, sid = populated_db
    update_session_note(db_path, sid, "updated note")
    sessions = get_sessions(db_path)
    assert sessions[0]["note"] == "updated note"


def test_import_legacy_json(tmp_path):
    db_path = str(tmp_path / "test.db")

    # Create a fake legacy JSON
    legacy_data = [
        {"name": "bubble", "time": 1.2, "comparisons": 499500, "swaps": 250000},
        {"name": "quick", "time": 0.03, "comparisons": 11000, "swaps": 6000},
    ]
    json_path = tmp_path / "benchmark_20260403_091100.json"
    json_path.write_text(json.dumps(legacy_data))

    init_db(db_path)
    import_legacy_json(db_path, str(json_path))

    sessions = get_sessions(db_path)
    # init_db already imported it, plus our explicit import
    assert any(s["note"] == "legacy import" for s in sessions)
    assert get_run_count(db_path) > 0


def test_auto_import_legacy_on_first_init(tmp_path):
    """init_db should auto-import benchmark_*.json on first creation."""
    legacy_data = [
        {"name": "bubble", "time": 1.0, "comparisons": 100, "swaps": 50},
    ]
    json_path = tmp_path / "benchmark_20260401_120000.json"
    json_path.write_text(json.dumps(legacy_data))

    db_path = str(tmp_path / ".benchmark.db")
    init_db(db_path)

    sessions = get_sessions(db_path)
    assert len(sessions) == 1
    assert sessions[0]["note"] == "legacy import"
    assert get_run_count(db_path) == 1


def test_get_sessions_summary(db_path):
    init_db(db_path)
    sid = insert_session(db_path, note="full run")
    insert_runs(
        db_path,
        sid,
        [
            {
                "algorithm": "bubble",
                "dataset": "random_int",
                "n": 100,
                "time": 0.5,
                "comparisons": 100,
                "swaps": 50,
            },
            {
                "algorithm": "bubble",
                "dataset": "reversed",
                "n": 500,
                "time": 0.8,
                "comparisons": 200,
                "swaps": 100,
            },
        ],
    )
    sessions = get_sessions(db_path)
    s = sessions[0]
    assert s["run_count"] == 2
    assert s["dataset_count"] == 2
    assert "100" in s["n_values"]
    assert "500" in s["n_values"]
