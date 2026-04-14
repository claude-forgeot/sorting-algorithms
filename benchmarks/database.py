"""SQLite storage for benchmark results.

Provides persistent storage for benchmark sessions and individual runs.
All queries go through module-level functions that accept a database path.
"""

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path


_SCHEMA = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS sessions (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT    NOT NULL,
    note      TEXT    DEFAULT ''
);

CREATE TABLE IF NOT EXISTS runs (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id  INTEGER NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    algorithm   TEXT    NOT NULL,
    dataset     TEXT    NOT NULL,
    n           INTEGER NOT NULL,
    time        REAL    NOT NULL,
    comparisons INTEGER NOT NULL,
    swaps       INTEGER NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_runs_session ON runs(session_id);
CREATE INDEX IF NOT EXISTS idx_runs_lookup  ON runs(algorithm, dataset, n);
"""


@contextmanager
def _connect(db_path: str):
    """Open a connection with foreign keys enabled; closes on exit even on error."""
    conn = sqlite3.connect(db_path)
    try:
        conn.execute("PRAGMA foreign_keys = ON")
        conn.row_factory = sqlite3.Row
        yield conn
    finally:
        conn.close()


def init_db(db_path: str) -> None:
    """Create tables and indexes if they don't exist.

    On first creation, automatically imports any legacy benchmark_*.json
    files found in the same directory as the database.
    """
    is_new = not Path(db_path).exists()
    with _connect(db_path) as conn:
        conn.executescript(_SCHEMA)

    if is_new:
        _import_all_legacy(db_path)


def _import_all_legacy(db_path: str) -> None:
    """Scan for benchmark_*.json files and import them.

    Each file is imported best-effort: a malformed JSON or a failed
    insert is logged to stderr but does not prevent other files from
    being imported.
    """
    import sys

    db_dir = Path(db_path).parent
    for json_file in sorted(db_dir.glob("benchmark_*.json")):
        try:
            import_legacy_json(db_path, str(json_file))
        except (json.JSONDecodeError, OSError, sqlite3.Error) as exc:
            print(
                f"[WARN] failed to import legacy file {json_file.name}: {exc}",
                file=sys.stderr,
            )


def import_legacy_json(db_path: str, json_path: str) -> int:
    """Import a legacy benchmark JSON file as a session.

    Legacy files contain results for random_int at N=1000.

    Returns:
        The session id of the imported session.
    """
    with open(json_path, "r") as f:
        data = json.load(f)

    # Extract timestamp from filename (benchmark_YYYYMMDD_HHMMSS.json)
    stem = Path(json_path).stem
    parts = stem.replace("benchmark_", "")
    try:
        ts = datetime.strptime(parts, "%Y%m%d_%H%M%S")
        timestamp = ts.isoformat()
    except ValueError:
        timestamp = datetime.now(timezone.utc).isoformat()

    with _connect(db_path) as conn:
        cursor = conn.execute(
            "INSERT INTO sessions (timestamp, note) VALUES (?, ?)",
            (timestamp, "legacy import"),
        )
        session_id = cursor.lastrowid

        rows = [
            (
                session_id,
                r["name"],
                "random_int",
                1000,
                r["time"],
                r["comparisons"],
                r["swaps"],
            )
            for r in data
        ]
        conn.executemany(
            "INSERT INTO runs (session_id, algorithm, dataset, n, time, comparisons, swaps) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            rows,
        )
        conn.commit()
    return session_id


def insert_session(db_path: str, note: str = "") -> int:
    """Create a new session and return its id."""
    timestamp = datetime.now(timezone.utc).isoformat()
    with _connect(db_path) as conn:
        cursor = conn.execute(
            "INSERT INTO sessions (timestamp, note) VALUES (?, ?)",
            (timestamp, note),
        )
        session_id = cursor.lastrowid
        conn.commit()
    return session_id


def insert_runs(db_path: str, session_id: int, rows: list[dict]) -> None:
    """Batch insert run results for a session.

    Each dict must have keys: algorithm, dataset, n, time, comparisons, swaps.
    """
    with _connect(db_path) as conn:
        conn.executemany(
            "INSERT INTO runs (session_id, algorithm, dataset, n, time, comparisons, swaps) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            [
                (
                    session_id,
                    r["algorithm"],
                    r["dataset"],
                    r["n"],
                    r["time"],
                    r["comparisons"],
                    r["swaps"],
                )
                for r in rows
            ],
        )
        conn.commit()


def get_matrix(db_path: str, metric: str, aggregation: str, n: int) -> dict:
    """Query aggregated values for the score matrix.

    Args:
        metric:      "time", "comparisons", or "swaps".
        aggregation: "avg", "min", or "max".
        n:           array size filter.

    Returns:
        Dict mapping (algorithm, dataset) to the aggregated value.
    """
    agg_fn = {"avg": "AVG", "min": "MIN", "max": "MAX"}[aggregation.lower()]
    col = {"time": "time", "comparisons": "comparisons", "swaps": "swaps"}[metric]

    with _connect(db_path) as conn:
        cursor = conn.execute(
            f"SELECT algorithm, dataset, {agg_fn}({col}) AS val "
            f"FROM runs WHERE n = ? GROUP BY algorithm, dataset",
            (n,),
        )
        result = {(row["algorithm"], row["dataset"]): row["val"] for row in cursor}
    return result


def get_sessions(db_path: str) -> list[dict]:
    """List all sessions with summary info."""
    with _connect(db_path) as conn:
        cursor = conn.execute(
            "SELECT s.id, s.timestamp, s.note, "
            "       COUNT(r.id) AS run_count, "
            "       COUNT(DISTINCT r.dataset) AS dataset_count, "
            "       GROUP_CONCAT(DISTINCT r.n) AS n_values "
            "FROM sessions s "
            "LEFT JOIN runs r ON r.session_id = s.id "
            "GROUP BY s.id "
            "ORDER BY s.timestamp DESC"
        )
        sessions = []
        for row in cursor:
            sessions.append(
                {
                    "id": row["id"],
                    "timestamp": row["timestamp"],
                    "note": row["note"],
                    "run_count": row["run_count"],
                    "dataset_count": row["dataset_count"],
                    "n_values": row["n_values"] if row["n_values"] is not None else "",
                }
            )
    return sessions


def delete_session(db_path: str, session_id: int) -> None:
    """Delete a session and all its runs (cascade)."""
    with _connect(db_path) as conn:
        conn.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
        conn.commit()


def update_session_note(db_path: str, session_id: int, note: str) -> None:
    """Update the note of a session."""
    with _connect(db_path) as conn:
        conn.execute("UPDATE sessions SET note = ? WHERE id = ?", (note, session_id))
        conn.commit()


def get_run_count(db_path: str) -> int:
    """Return total number of runs in the database."""
    with _connect(db_path) as conn:
        cursor = conn.execute("SELECT COUNT(*) FROM runs")
        count = cursor.fetchone()[0]
    return count
