"""Shared constants and helpers used by both solo and race visualizations."""

import random
from dataclasses import dataclass

from typing import Protocol

from visualization.renderers.bubble import BubbleRenderer
from visualization.renderers.selection import SelectionRenderer
from visualization.renderers.insertion import InsertionRenderer
from visualization.renderers.merge import MergeRenderer
from visualization.renderers.quick import QuickRenderer
from visualization.renderers.heap import HeapRenderer
from visualization.renderers.comb import CombRenderer


class Renderer(Protocol):
    def draw(self, screen, state, rect) -> None: ...

FPS = 60
_MIN_W, _MIN_H = 800, 600

MIN_SPEED = 0.001
MAX_SPEED = 1.0

DEFAULT_SLEEP_ENABLED = True
DEFAULT_SLEEP_MS = 10
MIN_SLEEP_MS = int(MIN_SPEED * 1000)
MAX_SLEEP_MS = int(MAX_SPEED * 1000)


def clamp_sleep_ms(value) -> int:
    try:
        v = int(value)
    except (TypeError, ValueError):
        return DEFAULT_SLEEP_MS
    return max(MIN_SLEEP_MS, min(MAX_SLEEP_MS, v))


@dataclass
class SleepState:
    enabled: bool = DEFAULT_SLEEP_ENABLED
    ms: int = DEFAULT_SLEEP_MS

    def __post_init__(self):
        self.ms = clamp_sleep_ms(self.ms)

    @property
    def seconds(self) -> float:
        return self.ms / 1000.0


# Mapping: algorithm name -> renderer class (single source of truth)
RENDERERS: dict[str, type[Renderer]] = {
    "bubble": BubbleRenderer,
    "selection": SelectionRenderer,
    "insertion": InsertionRenderer,
    "merge": MergeRenderer,
    "quick": QuickRenderer,
    "heap": HeapRenderer,
    "comb": CombRenderer,
}

_LEGACY_TO_PRESET: dict[str, str] = {
    "r": "random_int",
    "s": "nearly_sorted",
    "i": "reversed",
    "d": "few_unique",
    "n": "with_none",
}


def _build_array(size, preset):
    from visualization.datasets import PRESETS_META, generate

    preset_key = _LEGACY_TO_PRESET.get(preset, preset)

    if preset == "s":
        return list(range(1, size + 1))

    if preset_key in PRESETS_META:
        return generate(preset_key, size)

    return random.sample(range(size * 10), size)
