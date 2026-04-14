from benchmarks.runner import run_benchmark, run_full_benchmark
from sorting import ALGORITHMS


def test_returns_all_algorithms(unsorted):
    results = run_benchmark(unsorted)
    assert len(results) == len(ALGORITHMS)


def test_result_keys(unsorted):
    results = run_benchmark(unsorted)
    for r in results:
        assert "name" in r
        assert "time" in r
        assert "comparisons" in r
        assert "swaps" in r


def test_time_is_positive(unsorted):
    results = run_benchmark(unsorted)
    for r in results:
        assert r["time"] > 0


def test_comparisons_positive_for_unsorted(unsorted):
    results = run_benchmark(unsorted)
    for r in results:
        assert r["comparisons"] > 0, f"{r['name']} reported 0 comparisons"


def test_algorithm_names_match(unsorted):
    results = run_benchmark(unsorted)
    names = {r["name"] for r in results}
    assert names == set(ALGORITHMS.keys())


def test_full_benchmark_result_count():
    # 2 algos x 2 datasets x 1 N = 4 runs
    results = run_full_benchmark(
        n_values=(10,),
        datasets=["random_int", "reversed"],
        algos=["bubble", "quick"],
    )
    assert len(results) == 4


def test_full_benchmark_result_keys():
    results = run_full_benchmark(
        n_values=(10,),
        datasets=["random_int"],
        algos=["bubble"],
    )
    r = results[0]
    assert r["algorithm"] == "bubble"
    assert r["dataset"] == "random_int"
    assert r["n"] == 10
    assert r["time"] > 0
    assert r["comparisons"] > 0


def test_full_benchmark_progress_callback():
    calls = []

    def on_progress(current, total, algo, dataset, n):
        calls.append((current, total, algo, dataset, n))

    run_full_benchmark(
        n_values=(10,),
        datasets=["random_int"],
        algos=["bubble", "quick"],
        on_progress=on_progress,
    )
    assert len(calls) == 2
    assert calls[0][0] == 1  # current starts at 1
    assert calls[1][0] == 2
    assert calls[0][1] == 2  # total = 2
