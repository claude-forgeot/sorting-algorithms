"""Facade module preserving the historical public API of visualization.app.

The real implementation lives in:
    - visualization.solo  (solo mode: run)
    - visualization.race  (race mode: run_race, _start_race_threads)
    - visualization._common (shared constants and helpers)
"""

from visualization._common import (
    FPS,
    MIN_SPEED,
    MAX_SPEED,
    RENDERERS,
    _build_array,
)
from visualization.solo import (
    run,
    N_MAX_PAR_ALGO,
    TIMELINE_H,
    INFO_RATIO,
    _jouer_animation_fin,
)
from visualization.race import (
    run_race,
    _start_race_threads,
    RACE_INITIAL_SPEED,
)

__all__ = [
    "run",
    "run_race",
    "_start_race_threads",
    "RENDERERS",
    "N_MAX_PAR_ALGO",
    "RACE_INITIAL_SPEED",
    "FPS",
    "MIN_SPEED",
    "MAX_SPEED",
    "TIMELINE_H",
    "INFO_RATIO",
    "_build_array",
    "_jouer_animation_fin",
]
