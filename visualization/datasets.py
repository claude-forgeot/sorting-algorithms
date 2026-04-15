"""Dataset generation and configuration for the visualization."""

from __future__ import annotations

import random  # nosec B311 - dataset generation, not cryptographic

# ---------------------------------------------------------------------------
# Preset metadata
# ---------------------------------------------------------------------------

PRESETS_META: dict[str, dict] = {
    "random_int": {
        "label": "Random",
        "description": "Random integers between 1 and N",
        "max_n": 500,
    },
    "nearly_sorted": {
        "label": "Nearly sorted",
        "description": "95% sorted array, a few elements displaced",
        "max_n": 500,
    },
    "reversed": {
        "label": "Reversed",
        "description": "Descending order [N, N-1, ..., 1]",
        "max_n": 500,
    },
    "identical": {
        "label": "Identical",
        "description": "All elements have the same value (N//2)",
        "max_n": 500,
    },
    "few_unique": {
        "label": "Few unique",
        "description": "5 distinct values repeated randomly",
        "max_n": 500,
    },
    "stairs": {
        "label": "Stairs",
        "description": "4 ascending blocks of size N//4",
        "max_n": 500,
    },
    "float_01": {
        "label": "Floats [0, 1]",
        "description": "Random floats in [0.0, 1.0]",
        "max_n": 300,
    },
    "float_n": {
        "label": "Floats [0, N]",
        "description": "Random floats in [0.0, N]",
        "max_n": 300,
    },
    "float_neg": {
        "label": "Negative floats",
        "description": "Random floats in [-N/2, N/2]",
        "max_n": 300,
    },
    "with_none": {
        "label": "With None",
        "description": "Random integers with 15% None values",
        "max_n": 300,
        "benchmarkable": False,
    },
}

# ---------------------------------------------------------------------------
# Dataset generation
# ---------------------------------------------------------------------------


def generate(preset: str, n: int) -> list:
    """Generate an array of size n according to the requested preset.

    Args:
        preset: preset identifier (key from PRESETS_META).
        n:      number of elements in the generated array.

    Returns:
        Generated array. May contain None for "with_none".

    Raises:
        ValueError: if the preset is unknown.
    """
    if preset not in PRESETS_META:
        raise ValueError(
            f"Unknown preset: '{preset}'. Valid values: {list(PRESETS_META)}"
        )

    if preset == "random_int":
        return random.sample(range(1, n * 10 + 1), min(n, n * 10))

    if preset == "nearly_sorted":
        arr = list(range(1, n + 1))
        nb_swaps = max(1, int(n * 0.05))
        for _ in range(nb_swaps):
            i = random.randint(0, n - 1)
            j = random.randint(0, n - 1)
            arr[i], arr[j] = arr[j], arr[i]
        return arr

    if preset == "reversed":
        return list(range(n, 0, -1))

    if preset == "identical":
        return [n // 2] * n

    if preset == "few_unique":
        values = [max(1, n // 5 * k) for k in range(1, 6)]
        return [random.choice(values) for _ in range(n)]

    if preset == "stairs":
        block_size = max(1, n // 4)
        arr: list = []
        for k in range(4):
            block = list(range(1, block_size + 1))
            arr.extend(block)
        if len(arr) < n:
            arr.extend(range(1, 1 + (n - len(arr))))
        return arr[:n]

    if preset == "float_01":
        return [random.random() for _ in range(n)]

    if preset == "float_n":
        return [random.uniform(0.0, float(n)) for _ in range(n)]

    if preset == "float_neg":
        half = n / 2.0
        return [random.uniform(-half, half) for _ in range(n)]

    if preset == "with_none":
        sampled = random.sample(range(1, n * 10 + 1), min(n, n * 10))
        result: list[int | None] = list(sampled)
        nb_none = max(1, int(n * 0.15))
        positions = random.sample(range(len(result)), min(nb_none, len(result)))
        for pos in positions:
            result[pos] = None
        return result

    # never reached thanks to the initial check
    raise ValueError(f"Unhandled preset: '{preset}'")


# ---------------------------------------------------------------------------
# Visual normalization
# ---------------------------------------------------------------------------


def normalize(arr: list) -> list[float]:
    """Map non-None values to [0.0, 1.0] for rendering.

    None values are mapped to 0.0 visually.
    If all values are identical, they are all mapped to 0.5.

    Args:
        arr: input array (integers, floats or None).

    Returns:
        List of floats in [0.0, 1.0], same length as arr.
    """
    values = [v for v in arr if v is not None]
    if not values:
        return [0.0] * len(arr)

    vmin = min(values)
    vmax = max(values)
    span = vmax - vmin

    def _mapper(v: object) -> float:
        if v is None:
            return 0.0
        if span == 0:
            return 0.5
        return (v - vmin) / span  # type: ignore[operator]

    return [_mapper(v) for v in arr]
