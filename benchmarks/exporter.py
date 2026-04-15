"""Export benchmark data from the SQLite database to CSV or PDF."""

from __future__ import annotations

import csv
from datetime import datetime

from benchmarks.database import _connect


def _timestamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def export_csv(db_path: str, output_path: str | None = None) -> str:
    """Export aggregated benchmark data to a CSV file.

    Columns: algorithm, dataset, n, time_avg, time_min, time_max,
             comparisons_avg, swaps_avg, run_count

    Returns:
        Path to the generated CSV file.
    """
    if output_path is None:
        output_path = f"benchmark_export_{_timestamp()}.csv"

    with _connect(db_path) as conn:
        cursor = conn.execute(
            "SELECT algorithm, dataset, n, "
            "       AVG(time) AS time_avg, MIN(time) AS time_min, MAX(time) AS time_max, "
            "       AVG(comparisons) AS comparisons_avg, AVG(swaps) AS swaps_avg, "
            "       COUNT(*) AS run_count "
            "FROM runs GROUP BY algorithm, dataset, n "
            "ORDER BY n, dataset, algorithm"
        )

        fieldnames = [
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

        with open(output_path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for row in cursor:
                writer.writerow(
                    {
                        "algorithm": row["algorithm"],
                        "dataset": row["dataset"],
                        "n": row["n"],
                        "time_avg": f"{row['time_avg']:.6f}",
                        "time_min": f"{row['time_min']:.6f}",
                        "time_max": f"{row['time_max']:.6f}",
                        "comparisons_avg": int(row["comparisons_avg"]),
                        "swaps_avg": int(row["swaps_avg"]),
                        "run_count": row["run_count"],
                    }
                )

    return output_path


def export_pdf(db_path: str, output_path: str | None = None) -> str:
    """Export a formatted PDF report with one table per N value.

    Requires the fpdf2 package.

    Returns:
        Path to the generated PDF file.
    """
    from fpdf import FPDF

    if output_path is None:
        output_path = f"benchmark_export_{_timestamp()}.pdf"

    with _connect(db_path) as conn:
        n_values = [
            row[0]
            for row in conn.execute("SELECT DISTINCT n FROM runs ORDER BY n").fetchall()
        ]

        datasets = [
            row[0]
            for row in conn.execute(
                "SELECT DISTINCT dataset FROM runs ORDER BY dataset"
            ).fetchall()
        ]
        algorithms = [
            row[0]
            for row in conn.execute(
                "SELECT DISTINCT algorithm FROM runs ORDER BY algorithm"
            ).fetchall()
        ]

        pdf = FPDF()
        pdf.set_auto_page_break(auto=True, margin=15)

        pdf.add_page()
        pdf.set_font("Helvetica", "B", 24)
        pdf.cell(0, 40, "Benchmark Report", new_x="LMARGIN", new_y="NEXT", align="C")
        pdf.set_font("Helvetica", "", 12)
        pdf.cell(
            0,
            10,
            "Papyrus de Heron -- Sorting Algorithms",
            new_x="LMARGIN",
            new_y="NEXT",
            align="C",
        )
        pdf.cell(
            0,
            10,
            f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            new_x="LMARGIN",
            new_y="NEXT",
            align="C",
        )

        total_runs = conn.execute("SELECT COUNT(*) FROM runs").fetchone()[0]
        total_sessions = conn.execute("SELECT COUNT(*) FROM sessions").fetchone()[0]
        pdf.cell(
            0,
            10,
            f"{total_sessions} sessions, {total_runs} runs",
            new_x="LMARGIN",
            new_y="NEXT",
            align="C",
        )

        for n in n_values:
            pdf.add_page("L")
            pdf.set_font("Helvetica", "B", 16)
            pdf.cell(
                0, 12, f"Average Time (ms) -- N = {n}", new_x="LMARGIN", new_y="NEXT"
            )
            pdf.ln(4)

            cursor = conn.execute(
                "SELECT algorithm, dataset, AVG(time) AS avg_time "
                "FROM runs WHERE n = ? GROUP BY algorithm, dataset",
                (n,),
            )
            data = {}
            for row in cursor:
                data[(row["algorithm"], row["dataset"])] = row["avg_time"]

            col_w_algo = 28
            col_w = (277 - col_w_algo) / max(1, len(datasets))

            pdf.set_font("Helvetica", "B", 8)
            pdf.cell(col_w_algo, 8, "Algorithm", border=1)
            for ds in datasets:
                label = ds[:12]
                pdf.cell(col_w, 8, label, border=1, align="C")
            pdf.ln()

            pdf.set_font("Helvetica", "", 8)
            for algo in algorithms:
                pdf.cell(col_w_algo, 7, algo, border=1)
                for ds in datasets:
                    val = data.get((algo, ds))
                    text = f"{val * 1000:.1f}" if val is not None else "--"
                    pdf.cell(col_w, 7, text, border=1, align="R")
                pdf.ln()

    pdf.output(output_path)
    return output_path
