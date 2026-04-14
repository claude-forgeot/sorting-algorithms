import argparse
import random
import sys
from sorting import ALGORITHMS
from benchmarks.runner import run_benchmark


# Mapping from PRESETS_META keys to codes accepted by _build_array.
# Intentionally conservative: only direct equivalences are kept.
_PRESET_VERS_CODE: dict[str, str] = {
    "random_int": "r",
    "nearly_sorted": "r",
    "reversed": "i",
    "identical": "d",
    "few_unique": "d",
    "stairs": "r",
    "float_01": "r",
    "float_n": "r",
    "float_neg": "r",
    "with_none": "n",
}


def _preset_code(preset_key: str) -> str:
    """Convert a PRESETS_META key to a legacy code understood by _build_array."""
    return _PRESET_VERS_CODE.get(preset_key, "r")


def benchmark_mode():
    from pathlib import Path
    from benchmarks.database import init_db, insert_session, insert_runs

    db_path = str(Path(__file__).parent / ".benchmark.db")
    init_db(db_path)

    arr = random.sample(range(10000), 1000)
    print("Running benchmarks on 1000 random integers...")
    results = run_benchmark(arr)

    # Store in database
    sid = insert_session(db_path, note="CLI benchmark")
    insert_runs(
        db_path,
        sid,
        [
            {
                "algorithm": r["name"],
                "dataset": "random_int",
                "n": 1000,
                "time": r["time"],
                "comparisons": r["comparisons"],
                "swaps": r["swaps"],
            }
            for r in results
        ],
    )
    print(f"Results saved to database ({db_path})")

    print()
    print(f"{'algorithm':<12} {'time (s)':>10} {'comparisons':>13} {'swaps':>8}")
    print("-" * 47)
    for r in results:
        print(
            f"{r['name']:<12} {r['time']:>10.6f} {r['comparisons']:>13} {r['swaps']:>8}"
        )


def _prompt(message: str, default: str = "") -> str:
    """Safe wrapper around input() that handles non-interactive stdin.

    When stdin is not a TTY (piped run, CI, subprocess), input() either
    returns EOF or blocks forever. Returning the default in that case
    keeps --visual/--race usable in scripted contexts.
    """
    if not sys.stdin.isatty():
        return default
    try:
        return input(message)
    except EOFError:
        return default


def visual_mode():
    from visualization.app import run as run_visual

    algo_names = "/".join(ALGORITHMS.keys())
    name = _prompt(f"Choose algorithm ({algo_names}): ", next(iter(ALGORITHMS))).strip()
    if name not in ALGORITHMS:
        print(f"Error: unknown algorithm '{name}'.")
        sys.exit(1)

    raw_size = _prompt("Array size (default 64): ", "").strip()
    if raw_size.isdigit() and int(raw_size) > 0:
        size = int(raw_size)
    else:
        size = 64
        if raw_size:
            print("Invalid size, using default 64.")

    preset = (
        _prompt(
            "Preset (r=random, s=sorted, i=inverted, d=duplicates, n=with_none) [r]: ",
            "r",
        )
        .strip()
        .lower()
    )
    if preset not in ("r", "s", "i", "d", "n"):
        preset = "r"

    run_visual(ALGORITHMS[name], size, preset)


def race_mode():
    from visualization.app import run_race

    raw_size = _prompt("Array size (default 128): ", "").strip()
    if raw_size.isdigit() and int(raw_size) > 0:
        size = int(raw_size)
    else:
        size = 128
        if raw_size:
            print("Invalid size, using default 128.")

    preset = (
        _prompt(
            "Preset (r=random, s=sorted, i=inverted, d=duplicates, n=with_none) [r]: ",
            "r",
        )
        .strip()
        .lower()
    )
    if preset not in ("r", "s", "i", "d", "n"):
        preset = "r"

    run_race(size, preset)


def menu_mode() -> None:
    """Launch the pygame graphical menu and start the chosen mode.

    Opens a welcome window that allows configuring and launching one of
    the three modes (Race, Solo, Benchmark) without using the CLI.
    The main loop allows returning to the menu after each session.
    """
    import pygame
    from pathlib import Path
    from visualization.main_menu import run_main_menu
    from visualization.app import run as run_visual, run_race
    from benchmarks.database import init_db

    db_path = str(Path(__file__).parent / ".benchmark.db")
    init_db(db_path)

    pygame.init()
    pygame.display.set_caption("Papyrus de Heron")
    scr_info = pygame.display.Info()
    init_w = max(800, int(scr_info.current_w * 0.8))
    init_h = max(600, int(scr_info.current_h * 0.8))
    screen = pygame.display.set_mode((init_w, init_h), pygame.RESIZABLE)

    while True:
        if not pygame.get_init():
            pygame.init()
            pygame.display.set_caption("Papyrus de Heron")
            screen = pygame.display.set_mode((init_w, init_h), pygame.RESIZABLE)

        config = run_main_menu(screen)

        mode = config["mode"]

        if mode == "scores":
            from visualization.score_screen import run_score_screen

            run_score_screen(screen, db_path)
            continue

        # Release pygame before relaunching in a mode that resets its own window
        pygame.quit()

        if mode == "benchmark":
            benchmark_mode()
            break  # after benchmark, exit (no return to menu)

        elif mode == "course":
            resultat = run_race(
                config["n"],
                _preset_code(config["preset"]),
                speed=config["speed"],
                sleep_enabled=config.get("sleep_enabled", True),
                sleep_ms=config.get("sleep_ms", 10),
            )
            if resultat != "menu":
                break

        elif mode == "solo":
            algos_actifs = config["algos"] or list(ALGORITHMS.keys())
            algo_name = algos_actifs[0]
            if algo_name not in ALGORITHMS:
                algo_name = next(iter(ALGORITHMS))
            resultat = run_visual(
                ALGORITHMS[algo_name],
                config["n"],
                _preset_code(config["preset"]),
                son=config.get("son", False),
                speed=config["speed"],
                sleep_enabled=config.get("sleep_enabled", True),
                sleep_ms=config.get("sleep_ms", 10),
            )
            if resultat != "menu":
                break

        else:
            break  # unknown mode or window closed


def main():
    parser = argparse.ArgumentParser(description="Sorting algorithms demo")
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument("--benchmark", action="store_true", help="Run benchmarks")
    mode_group.add_argument("--visual", action="store_true", help="Visualize sorting")
    mode_group.add_argument("--race", action="store_true", help="Race all algorithms")
    mode_group.add_argument(
        "--menu",
        action="store_true",
        help="Open graphical menu (default without arguments)",
    )
    args = parser.parse_args()

    if args.visual:
        visual_mode()
    elif args.race:
        race_mode()
    elif args.benchmark:
        benchmark_mode()
    else:
        menu_mode()


if __name__ == "__main__":
    main()
