import threading
import time
from sorting import ALGORITHMS
from visualization.app import _start_race_threads
from visualization._common import SleepState


def make_states(base_arr):
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


def test_all_algorithms_finish():
    base_arr = [5, 3, 8, 1, 9, 2, 7, 4, 6]
    states = make_states(base_arr)
    stop_flag = threading.Event()
    pause_event = threading.Event()
    pause_event.set()
    sleep_state = SleepState(enabled=False, ms=0)
    threads = _start_race_threads(base_arr, states, stop_flag, pause_event, sleep_state)
    for t in threads:
        t.join(timeout=10)
    for name in ALGORITHMS:
        assert states[name]["done"] is True, f"{name} did not finish"


def test_all_algorithms_record_positive_time():
    base_arr = [5, 3, 8, 1, 9, 2, 7, 4, 6]
    states = make_states(base_arr)
    stop_flag = threading.Event()
    pause_event = threading.Event()
    pause_event.set()
    sleep_state = SleepState(enabled=False, ms=0)
    threads = _start_race_threads(base_arr, states, stop_flag, pause_event, sleep_state)
    for t in threads:
        t.join(timeout=10)
    for name in ALGORITHMS:
        assert states[name]["time"] > 0, f"{name} time should be positive"


def test_stop_flag_interrupts_threads():
    base_arr = list(range(200, 0, -1))  # reversed, worst case for most algos
    states = make_states(base_arr)
    stop_flag = threading.Event()
    pause_event = threading.Event()
    pause_event.set()
    sleep_state = SleepState(
        enabled=True, ms=1
    )  # slow enough that threads won't finish before we stop them
    threads = _start_race_threads(base_arr, states, stop_flag, pause_event, sleep_state)
    time.sleep(0.05)  # give threads time to start; 50 ms is enough on most machines
    stop_flag.set()  # signal all threads to stop
    for t in threads:
        t.join(timeout=3)
    for t in threads:
        assert not t.is_alive(), "thread still alive after stop_flag"


def test_each_algo_sorts_its_own_copy():
    base_arr = [3, 1, 4, 1, 5, 9, 2, 6]
    states = make_states(base_arr)
    stop_flag = threading.Event()
    pause_event = threading.Event()
    pause_event.set()
    sleep_state = SleepState(enabled=False, ms=0)
    threads = _start_race_threads(base_arr, states, stop_flag, pause_event, sleep_state)
    for t in threads:
        t.join(timeout=10)
    expected = sorted(base_arr)
    for name in ALGORITHMS:
        assert states[name]["arr"] == expected, f"{name} arr is not sorted after race"
