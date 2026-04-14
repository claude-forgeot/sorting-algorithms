"""Tests for the sleep toggle feature (race + solo + form)."""

import os
import threading
import time

import pygame
import pytest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

from sorting import ALGORITHMS
from visualization._common import (
    DEFAULT_SLEEP_MS,
    MAX_SLEEP_MS,
    MIN_SLEEP_MS,
    SleepState,
    clamp_sleep_ms,
)
from visualization.app import _start_race_threads


def test_clamp_sleep_ms_bounds():
    assert clamp_sleep_ms(-100) == MIN_SLEEP_MS
    assert clamp_sleep_ms(999999) == MAX_SLEEP_MS
    assert clamp_sleep_ms(50) == 50


def test_clamp_sleep_ms_invalid():
    assert clamp_sleep_ms("abc") == DEFAULT_SLEEP_MS
    assert clamp_sleep_ms(None) == DEFAULT_SLEEP_MS
    assert clamp_sleep_ms("42") == 42


def test_sleep_state_clamps_on_init():
    s = SleepState(enabled=True, ms=99999)
    assert s.ms == MAX_SLEEP_MS


def test_sleep_state_seconds_conversion():
    assert SleepState(enabled=True, ms=10).seconds == pytest.approx(0.01)
    assert SleepState(enabled=True, ms=500).seconds == pytest.approx(0.5)


def _make_states(base_arr):
    return {
        name: {
            "arr": base_arr[:],
            "highlighted": None,
            "done": False,
            "time": 0.0,
            "steps": 0,
            "nb_none": 0,
        }
        for name in ALGORITHMS
    }


def _run_race(sleep_state: SleepState, base_arr) -> float:
    states = _make_states(base_arr)
    stop = threading.Event()
    pause = threading.Event()
    pause.set()
    t0 = time.time()
    threads = _start_race_threads(base_arr, states, stop, pause, sleep_state)
    for t in threads:
        t.join(timeout=10)
    return time.time() - t0


def test_race_sleep_off_faster_than_on():
    base_arr = list(range(30, 0, -1))
    t_off = _run_race(SleepState(enabled=False, ms=10), base_arr)
    t_on = _run_race(SleepState(enabled=True, ms=10), base_arr)
    assert t_off < t_on, f"OFF ({t_off:.3f}s) should be faster than ON ({t_on:.3f}s)"


def test_sleep_form_parse_digits():
    pygame.init()
    pygame.display.set_mode((100, 100))
    from visualization.widgets.sleep_form import SleepForm

    state = SleepState(enabled=True, ms=10)
    form = SleepForm(pygame.Rect(0, 0, 200, 30), state)
    form.open()

    for _ in range(10):
        form.handle_event(
            pygame.event.Event(pygame.KEYDOWN, key=pygame.K_BACKSPACE, unicode="")
        )

    for digit in "250":
        ev = pygame.event.Event(pygame.KEYDOWN, key=0, unicode=digit)
        form.handle_event(ev)

    ev_enter = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN, unicode="")
    assert form.handle_event(ev_enter) is True
    assert state.ms == 250


def test_sleep_form_rejects_non_digits():
    pygame.init()
    pygame.display.set_mode((100, 100))
    from visualization.widgets.sleep_form import SleepForm

    state = SleepState(enabled=True, ms=10)
    form = SleepForm(pygame.Rect(0, 0, 200, 30), state)
    form.open()
    initial = form._ms_str

    for char in "abc!":
        ev = pygame.event.Event(pygame.KEYDOWN, key=0, unicode=char)
        form.handle_event(ev)
    assert form._ms_str == initial


def test_sleep_form_escape_cancels():
    pygame.init()
    pygame.display.set_mode((100, 100))
    from visualization.widgets.sleep_form import SleepForm

    state = SleepState(enabled=True, ms=10)
    form = SleepForm(pygame.Rect(0, 0, 200, 30), state)
    form.open()
    form.handle_event(pygame.event.Event(pygame.KEYDOWN, key=0, unicode="9"))
    form.handle_event(
        pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE, unicode="")
    )
    assert state.ms == 10
    assert form.active is False


def test_sleep_form_toggle_enabled_with_space():
    pygame.init()
    pygame.display.set_mode((100, 100))
    from visualization.widgets.sleep_form import SleepForm

    state = SleepState(enabled=True, ms=10)
    form = SleepForm(pygame.Rect(0, 0, 200, 30), state)
    form.open()
    form.handle_event(
        pygame.event.Event(pygame.KEYDOWN, key=pygame.K_SPACE, unicode=" ")
    )
    form.handle_event(
        pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN, unicode="")
    )
    assert state.enabled is False
