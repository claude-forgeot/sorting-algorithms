"""Race mode visualizer: all algorithms compete in parallel threads."""

import threading
import time
import pygame
from sorting import ALGORITHMS
from visualization import theme
from visualization._common import (
    FPS,
    _MIN_W,
    _MIN_H,
    MIN_SLEEP_MS,
    MAX_SLEEP_MS,
    SleepState,
    RENDERERS,
    _build_array,
)
from visualization.layout import race_layout, focus_layout
from visualization.widgets.dataset_selector import DatasetSelector
from visualization.widgets.sleep_form import SleepForm

RACE_INITIAL_SPEED = 0.01  # default step delay for race mode

# Base heights for fixed areas (dynamically scaled)
_BASE_CHIP_H = 38
_BASE_STATS_H = 52
_BASE_CELL_HDR = 22

# Base chip dimensions
CHIP_PAD = 10
CHIP_GAP = 6
CHIP_MARG = 8

# Colors
C_FOND = (20, 20, 20)
C_CHIP_BAR = (22, 22, 32)
C_CHIP_ON = (45, 95, 175)
C_CHIP_OFF = (50, 50, 65)
C_CHIP_BORD = (75, 75, 95)
C_CHIP_TEXTE = (210, 210, 230)
C_CELL_FOND = (26, 26, 36)
C_HDR_RUN = (32, 32, 48)
C_HDR_DONE = (25, 65, 35)
C_HDR_TEXTE_RUN = (170, 170, 200)
C_HDR_TEXTE_DONE = (100, 230, 130)
C_CELL_BORD = (50, 50, 70)
C_STATS_FOND = (22, 22, 32)
C_STATS_TEXTE = (200, 200, 220)
C_VAINQUEUR = (255, 215, 0)
C_HINT = (110, 110, 135)
C_PAUSED = (255, 200, 0)
C_FOCUS_BORD = (255, 215, 0)


def _start_race_threads(base_arr, states, stop_flag, pause_event, sleep_state):
    # Creates one thread per algorithm and starts them all.

    def make_on_step(algo_name):
        def on_step(arr, i, j, event_type):
            if stop_flag.is_set():
                return
            pause_event.wait()
            if stop_flag.is_set():
                return
            if sleep_state.enabled:
                time.sleep(sleep_state.ms / 1000.0)
            states[algo_name]["arr"] = arr
            states[algo_name]["highlighted"] = (i, j, event_type)
            states[algo_name]["steps"] += 1

        return on_step

    def _run_algo(algo_fn, arr, name):
        start = time.time()
        result = algo_fn(arr, on_step=make_on_step(name))
        nb_none = states[name].get("nb_none", 0)
        if nb_none > 0:
            result = result + [None] * nb_none
        states[name]["arr"] = result
        states[name]["done"] = True
        states[name]["time"] = time.time() - start
        states[name]["highlighted"] = None

    threads = []
    for name, algo_fn in ALGORITHMS.items():
        arr_copy = base_arr[:]
        t = threading.Thread(
            target=_run_algo,
            args=(algo_fn, arr_copy, name),
            daemon=True,
        )
        threads.append(t)

    for t in threads:
        t.start()

    return threads


def run_race(
    size: int,
    preset: str,
    speed: float = RACE_INITIAL_SPEED,
    sleep_enabled: bool = True,
    sleep_ms: int = 10,
) -> str:
    """Race mode: all sorting algorithms compete in parallel.

    Controls:
        SPACE        pause / resume
        +  / -       speed up / slow down
        D            open dataset selector
        Click chip   enable / disable an algorithm
        Q / Close    quit
    """
    pygame.init()

    scr_info = pygame.display.Info()
    cur_w = max(_MIN_W, int(scr_info.current_w * 0.8))
    cur_h = max(_MIN_H, int(scr_info.current_h * 0.8))
    screen = pygame.display.set_mode((cur_w, cur_h), pygame.RESIZABLE)
    pygame.display.set_caption("Sorting Race")
    clock = pygame.time.Clock()

    def _calc_race_layout(w, h):
        sc = theme.scale_factor(h)
        chip_h = max(28, int(_BASE_CHIP_H * sc))
        stats_h = max(36, int(_BASE_STATS_H * sc))
        cell_hdr = max(16, int(_BASE_CELL_HDR * sc))
        wr = pygame.Rect(0, 0, w, h)
        mr = pygame.Rect(0, chip_h, w, h - chip_h - stats_h)
        return sc, chip_h, stats_h, cell_hdr, wr, mr

    scale, CHIP_H, STATS_H, CELL_HDR, window_rect, main_rect = _calc_race_layout(
        cur_w, cur_h
    )

    def _make_race_fonts(sc):
        return (
            pygame.font.SysFont("monospace", theme.scaled_font(13, sc)),
            pygame.font.SysFont("monospace", theme.scaled_font(14, sc)),
            pygame.font.SysFont("monospace", theme.scaled_font(12, sc)),
            pygame.font.SysFont("monospace", theme.scaled_font(18, sc)),
        )

    font_cell, font_stats, font_hint, font_titre = _make_race_fonts(scale)

    algos_actifs: set[str] = set(ALGORITHMS.keys())

    vainqueur: list[str | None] = [None]
    race_start_time: list[float] = [time.time()]
    renderers_actifs: dict[str, object] = {}

    def demarrer_course(preset_val: str, size_val: int) -> tuple:
        """Prepare an array, instantiate renderers and start all threads."""
        arr_base = _build_array(size_val, preset_val)
        valeurs = [v for v in arr_base if v is not None]
        nb_none = len(arr_base) - len(valeurs)
        arr_race = valeurs if nb_none > 0 else arr_base

        _sleep = SleepState(enabled=sleep_enabled, ms=sleep_ms)
        _pause_ev = threading.Event()
        _pause_ev.set()
        _stop = threading.Event()

        _states: dict[str, dict] = {
            nom: {
                "arr": arr_race[:],
                "highlighted": None,
                "done": False,
                "time": 0.0,
                "steps": 0,
                "nb_none": nb_none,
            }
            for nom in ALGORITHMS
        }

        renderers_actifs.clear()
        renderers_actifs.update(
            {nom: RENDERERS[nom]() for nom in ALGORITHMS if nom in RENDERERS}
        )

        vainqueur[0] = None
        race_start_time[0] = time.time()

        _threads = _start_race_threads(arr_race, _states, _stop, _pause_ev, _sleep)
        return _states, _threads, _stop, _pause_ev, _sleep

    def arreter_threads(
        stop_flag: threading.Event,
        pause_ev: threading.Event,
        threads: list,
    ) -> None:
        """Cleanly stop all running threads."""
        stop_flag.set()
        pause_ev.set()
        for t in threads:
            t.join(timeout=2)

    _chip_rects: dict[str, pygame.Rect] = {}

    def _recalc_chips():
        """Recalculate chip rects based on current fonts."""
        _chip_rects.clear()
        chip_h_px = max(16, int(24 * scale))
        _surf_lbl = font_hint.render("Algos :", True, (0, 0, 0))
        _x = CHIP_MARG + _surf_lbl.get_width() + CHIP_GAP
        for _nom in ALGORITHMS:
            _w = font_cell.render(_nom, True, (0, 0, 0)).get_width() + 2 * CHIP_PAD
            _chip_rects[_nom] = pygame.Rect(
                _x, (CHIP_H - chip_h_px) // 2, _w, chip_h_px
            )
            _x += _w + CHIP_GAP

    _recalc_chips()

    def _dessiner_chips() -> None:
        """Draw the chip bar at the top of the screen."""
        pygame.draw.rect(screen, C_CHIP_BAR, pygame.Rect(0, 0, cur_w, CHIP_H))
        surf_lbl = font_hint.render("Algos :", True, (120, 120, 150))
        screen.blit(surf_lbl, (CHIP_MARG, (CHIP_H - surf_lbl.get_height()) // 2))
        for nom, rect in _chip_rects.items():
            actif = nom in algos_actifs
            pygame.draw.rect(
                screen, C_CHIP_ON if actif else C_CHIP_OFF, rect, border_radius=4
            )
            pygame.draw.rect(screen, C_CHIP_BORD, rect, width=1, border_radius=4)
            surf = font_cell.render(nom, True, C_CHIP_TEXTE)
            screen.blit(surf, surf.get_rect(center=rect.center))

    def _dessiner_stats(cur_states: dict, elapsed: float) -> None:
        """Draw the stats bar and hints at the bottom of the screen."""
        stats_rect = pygame.Rect(0, cur_h - STATS_H, cur_w, STATS_H)
        pygame.draw.rect(screen, C_STATS_FOND, stats_rect)

        if vainqueur[0] is not None:
            t_vainq = cur_states[vainqueur[0]].get("time", 0.0)
            texte = f"Time: {elapsed:.1f}s    Winner: {vainqueur[0]} ({t_vainq:.2f}s)"
            surf = font_stats.render(texte, True, C_VAINQUEUR)
        else:
            nb_actifs = len(algos_actifs)
            nb_done = sum(
                1
                for name, s in cur_states.items()
                if s["done"] and name in algos_actifs
            )
            texte = f"Time: {elapsed:.1f}s    {nb_done}/{nb_actifs} done"
            surf = font_stats.render(texte, True, C_STATS_TEXTE)
        screen.blit(surf, (CHIP_MARG, stats_rect.top + 5))

        sleep_label = f"{sleep_state.ms}ms" if sleep_state.enabled else "OFF"
        hint = (
            f"Space pause   +/- speed ({sleep_label})   S sleep   "
            "D dataset   TAB focus   F11 fullscreen   M menu"
        )
        surf_h = font_hint.render(hint, True, C_HINT)
        screen.blit(
            surf_h, (CHIP_MARG, stats_rect.top + 5 + font_stats.get_height() + 4)
        )

    current_preset = [preset]
    current_size = [size]

    states, threads, stop_flag, pause_event, sleep_state = demarrer_course(
        current_preset[0], current_size[0]
    )

    dataset_selector: DatasetSelector | None = None
    sleep_form = SleepForm(
        pygame.Rect(CHIP_MARG, cur_h - STATS_H + 4, 220, STATS_H - 8),
        sleep_state,
        font=font_hint,
    )

    focus_mode: bool = False
    focused_algo: str | None = None
    _algo_keys = list(ALGORITHMS.keys())

    running = True
    while running:
        for event in pygame.event.get():
            if sleep_form.active:
                sleep_form.handle_event(event)
                if event.type == pygame.QUIT:
                    pause_event.set()
                    stop_flag.set()
                    running = False
                continue

            if dataset_selector is not None and dataset_selector.is_active:
                résultat = dataset_selector.handle_event(event)
                if résultat is not None:
                    new_preset, new_n = résultat
                    current_preset[0] = new_preset
                    current_size[0] = new_n
                    arreter_threads(stop_flag, pause_event, threads)
                    states, threads, stop_flag, pause_event, sleep_state = (
                        demarrer_course(current_preset[0], current_size[0])
                    )
                    dataset_selector = None
                elif not dataset_selector.is_active:
                    dataset_selector = None
                if event.type == pygame.QUIT:
                    pause_event.set()
                    stop_flag.set()
                    running = False
                continue

            if event.type == pygame.QUIT:
                pause_event.set()
                stop_flag.set()
                running = False

            elif event.type == pygame.VIDEORESIZE:
                cur_w = max(_MIN_W, event.w)
                cur_h = max(_MIN_H, event.h)
                screen = pygame.display.set_mode((cur_w, cur_h), pygame.RESIZABLE)
                scale, CHIP_H, STATS_H, CELL_HDR, window_rect, main_rect = (
                    _calc_race_layout(cur_w, cur_h)
                )
                font_cell, font_stats, font_hint, font_titre = _make_race_fonts(scale)
                _recalc_chips()

            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_F11:
                    pygame.display.toggle_fullscreen()

                elif event.key in (pygame.K_q, pygame.K_m):
                    pause_event.set()
                    stop_flag.set()
                    running = False

                elif event.key == pygame.K_SPACE:
                    if pause_event.is_set():
                        pause_event.clear()
                    else:
                        pause_event.set()

                elif event.unicode == "+":
                    sleep_state.ms = max(MIN_SLEEP_MS, sleep_state.ms // 2)

                elif event.unicode == "-":
                    sleep_state.ms = min(MAX_SLEEP_MS, sleep_state.ms * 2)

                elif event.key == pygame.K_d:
                    dataset_selector = DatasetSelector(
                        window_rect, n_initial=current_size[0], scale=scale
                    )

                elif event.key == pygame.K_s:
                    sleep_form.set_rect(
                        pygame.Rect(CHIP_MARG, cur_h - STATS_H + 4, 220, STATS_H - 8)
                    )
                    sleep_form.open()

                elif event.key == pygame.K_TAB:
                    focus_mode = not focus_mode
                    if focus_mode and focused_algo is None:
                        noms_a = [n for n in _algo_keys if n in algos_actifs]
                        focused_algo = noms_a[0] if noms_a else _algo_keys[0]

                elif event.key in (
                    pygame.K_1,
                    pygame.K_2,
                    pygame.K_3,
                    pygame.K_4,
                    pygame.K_5,
                    pygame.K_6,
                    pygame.K_7,
                ):
                    idx = event.key - pygame.K_1
                    if idx < len(_algo_keys) and _algo_keys[idx] in algos_actifs:
                        focused_algo = _algo_keys[idx]
                        focus_mode = True

            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if focus_mode:
                    noms_actifs_l = [n for n in _algo_keys if n in algos_actifs]
                    others = [n for n in noms_actifs_l if n != focused_algo]
                    layout_f = focus_layout(
                        focused_algo or noms_actifs_l[0],
                        others,
                        main_rect,
                    )
                    for nom, rect in layout_f.items():
                        if nom != focused_algo and rect.collidepoint(event.pos):
                            focused_algo = nom
                            break

                for nom, chip_rect in _chip_rects.items():
                    if chip_rect.collidepoint(event.pos):
                        if nom in algos_actifs:
                            if len(algos_actifs) > 1:
                                algos_actifs.discard(nom)
                                if focused_algo == nom:
                                    noms_rest = [
                                        n for n in _algo_keys if n in algos_actifs
                                    ]
                                    focused_algo = noms_rest[0] if noms_rest else None
                        else:
                            algos_actifs.add(nom)
                        break

        if vainqueur[0] is None:
            for nom in ALGORITHMS:
                if nom in algos_actifs and states[nom]["done"]:
                    vainqueur[0] = nom
                    break

        screen.fill(C_FOND)

        _dessiner_chips()

        noms_actifs = [n for n in ALGORITHMS if n in algos_actifs]

        if focus_mode and focused_algo and focused_algo in algos_actifs:
            others = [n for n in noms_actifs if n != focused_algo]
            layout = focus_layout(focused_algo, others, main_rect)
        else:
            layout = race_layout(noms_actifs, main_rect)

        for nom in noms_actifs:
            if nom not in layout:
                continue
            cell_rect = layout[nom]
            renderer = renderers_actifs.get(nom)
            if renderer is None:
                continue

            s = states[nom]
            is_done = s["done"]
            elapsed_algo = s["time"] if is_done else (time.time() - race_start_time[0])

            is_focused = focus_mode and nom == focused_algo

            pygame.draw.rect(screen, C_CELL_FOND, cell_rect)

            hdr_h = CELL_HDR * (2 if is_focused else 1)
            hdr_rect = pygame.Rect(
                cell_rect.left, cell_rect.top, cell_rect.width, hdr_h
            )
            pygame.draw.rect(screen, C_HDR_DONE if is_done else C_HDR_RUN, hdr_rect)

            if is_focused:
                f_nom = font_titre if is_focused else font_cell
                surf_nom = f_nom.render(
                    nom, True, C_HDR_TEXTE_DONE if is_done else C_HDR_TEXTE_RUN
                )
                screen.blit(surf_nom, (cell_rect.left + 8, cell_rect.top + 4))
                stats_txt = f"{s['steps']} steps   {elapsed_algo:.1f}s"
                if is_done:
                    stats_txt += "  [OK]"
                surf_st = font_stats.render(
                    stats_txt, True, C_HDR_TEXTE_DONE if is_done else C_HDR_TEXTE_RUN
                )
                screen.blit(
                    surf_st,
                    (cell_rect.left + 8, cell_rect.top + surf_nom.get_height() + 6),
                )
            else:
                label = f"{nom}   {s['steps']} steps   {elapsed_algo:.1f}s"
                if is_done:
                    label += "  [OK]"
                c_texte = C_HDR_TEXTE_DONE if is_done else C_HDR_TEXTE_RUN
                surf_h = font_cell.render(label, True, c_texte)
                screen.blit(
                    surf_h,
                    (
                        cell_rect.left + 4,
                        cell_rect.top + (hdr_h - surf_h.get_height()) // 2,
                    ),
                )

            render_rect = pygame.Rect(
                cell_rect.left,
                cell_rect.top + hdr_h,
                cell_rect.width,
                cell_rect.height - hdr_h,
            )
            renderer.draw(screen, s, render_rect)

            bord_color = C_FOCUS_BORD if is_focused else C_CELL_BORD
            bord_width = 2 if is_focused else 1
            pygame.draw.rect(screen, bord_color, cell_rect, bord_width)

        if not pause_event.is_set():
            surf_p = font_titre.render("PAUSED", True, C_PAUSED)
            screen.blit(
                surf_p,
                (
                    cur_w // 2 - surf_p.get_width() // 2,
                    CHIP_H + 10,
                ),
            )

        if noms_actifs and all(states[n]["done"] for n in noms_actifs):
            surf_done = font_titre.render("Race complete!", True, theme.DONE)
            screen.blit(
                surf_done,
                (
                    cur_w // 2 - surf_done.get_width() // 2,
                    cur_h // 2 - surf_done.get_height() // 2,
                ),
            )

        _dessiner_stats(states, time.time() - race_start_time[0])

        if dataset_selector is not None and dataset_selector.is_active:
            dataset_selector.draw(screen)

        if sleep_form.active:
            sleep_form.set_rect(
                pygame.Rect(CHIP_MARG, cur_h - STATS_H + 4, 220, STATS_H - 8)
            )
            sleep_form.draw(screen)

        pygame.display.flip()
        clock.tick(FPS)

    stop_flag.set()
    pause_event.set()
    for t in threads:
        t.join(timeout=2)
    pygame.quit()
    return "menu"
