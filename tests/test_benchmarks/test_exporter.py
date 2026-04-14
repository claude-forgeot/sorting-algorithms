import csv
import os
from benchmarks.database import init_db, insert_session, insert_runs
from benchmarks.exporter import export_csv, export_pdf


def _setup_db(tmp_path):
    """Create a test database with sample data."""
    db_path = str(tmp_path / "test.db")
    init_db(db_path)
    sid = insert_session(db_path, note="test")
    insert_runs(
        db_path,
        sid,
        [
            {
                "algorithm": "bubble",
                "dataset": "random_int",
                "n": 100,
                "time": 0.5,
                "comparisons": 4950,
                "swaps": 2400,
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
                "algorithm": "bubble",
                "dataset": "reversed",
                "n": 100,
                "time": 0.8,
                "comparisons": 4950,
                "swaps": 4950,
            },
        ],
    )
    return db_path


def test_export_csv_creates_file(tmp_path):
    db_path = _setup_db(tmp_path)
    output = str(tmp_path / "export.csv")
    returned = export_csv(db_path, output)
    assert returned == output
    assert os.path.exists(output)


def test_export_csv_content(tmp_path):
    db_path = _setup_db(tmp_path)
    output = str(tmp_path / "export.csv")
    export_csv(db_path, output)

    with open(output, newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    assert len(rows) == 3
    assert rows[0]["algorithm"] in ("bubble", "quick")
    assert "time_avg" in rows[0]
    assert "run_count" in rows[0]


def test_export_csv_headers(tmp_path):
    db_path = _setup_db(tmp_path)
    output = str(tmp_path / "export.csv")
    export_csv(db_path, output)

    with open(output, newline="") as f:
        reader = csv.DictReader(f)
        expected = [
            "algorithm",
            "dataset",
            "n",
            "time_avg",
            "time_min",
            "time_max",
            "comparisons_avg",
            "swaps_avg",
            "run_count",
        ]
        assert reader.fieldnames == expected


def test_export_csv_auto_filename(tmp_path, monkeypatch):
    db_path = _setup_db(tmp_path)
    monkeypatch.chdir(tmp_path)
    filepath = export_csv(db_path)
    assert filepath.startswith("benchmark_export_")
    assert filepath.endswith(".csv")
    assert os.path.exists(filepath)


def test_export_pdf_creates_file(tmp_path):
    db_path = _setup_db(tmp_path)
    output = str(tmp_path / "export.pdf")
    returned = export_pdf(db_path, output)
    assert returned == output
    assert os.path.exists(output)
    assert os.path.getsize(output) > 0
