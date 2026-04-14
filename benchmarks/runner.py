import time
from sorting import ALGORITHMS


def run_benchmark(arr):
    """Run all algorithms on a single array. Returns list of result dicts."""
    results = []
    for name, fn in ALGORITHMS.items():
        comparisons = 0
        swaps = 0

        def on_step(state, i, j, event_type):
            nonlocal comparisons, swaps
            if event_type == "compare":
                comparisons += 1
            elif event_type in ("swap", "set"):
                swaps += 1

        start = time.perf_counter()
        fn(arr, on_step=on_step)
        elapsed = time.perf_counter() - start

        results.append(
            {
                "name": name,
                "time": elapsed,
                "comparisons": comparisons,
                "swaps": swaps,
            }
        )
    return results


def run_full_benchmark(
    n_values=(100, 500, 1000),
    datasets=None,
    algos=None,
    on_progress=None,
):
    """Run benchmarks for all combinations of algorithms, datasets, and sizes.

    Args:
        n_values:    tuple of array sizes to test.
        datasets:    list of dataset keys (default: all from PRESETS_META).
        algos:       list of algorithm keys (default: all from ALGORITHMS).
        on_progress: callback(current, total, algo, dataset, n) called before
                     each individual run.

    Returns:
        List of dicts with keys: algorithm, dataset, n, time, comparisons, swaps.
    """
    from visualization.datasets import PRESETS_META, generate

    if datasets is None:
        datasets = [k for k, v in PRESETS_META.items() if v.get("benchmarkable", True)]
    if algos is None:
        algos = list(ALGORITHMS.keys())

    total = len(algos) * len(datasets) * len(n_values)
    results = []
    current = 0

    for n in n_values:
        for dataset in datasets:
            arr = generate(dataset, n)
            for algo_name in algos:
                current += 1
                if on_progress:
                    on_progress(current, total, algo_name, dataset, n)

                fn = ALGORITHMS[algo_name]
                comparisons = 0
                swaps = 0

                def on_step(state, i, j, event_type):
                    nonlocal comparisons, swaps
                    if event_type == "compare":
                        comparisons += 1
                    elif event_type in ("swap", "set"):
                        swaps += 1

                start = time.perf_counter()
                fn(list(arr), on_step=on_step)
                elapsed = time.perf_counter() - start

                results.append(
                    {
                        "algorithm": algo_name,
                        "dataset": dataset,
                        "n": n,
                        "time": elapsed,
                        "comparisons": comparisons,
                        "swaps": swaps,
                    }
                )

    return results
