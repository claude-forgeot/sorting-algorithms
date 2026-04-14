"""Solo mode visualizer: one algorithm, full timeline navigation."""

import pygame
from sorting import ALGORITHMS
from visualization import theme
from visualization._common import (
    FPS,
    _MIN_W,
    _MIN_H,
    RENDERERS,
    _build_array,
)
from visualization.history import StepHistory
from visualization.widgets.timeline import Timeline
from visualization.widgets.sleep_form import SleepForm
from visualization._common import SleepState
from visualization.audio import generate_tones, play_tone
from visualization.widgets.info_panel import InfoPanel
from visualization.widgets.dataset_selector import DatasetSelector
from visualization.renderers.bubble import BubbleRenderer

TIMELINE_H: int = 60
INFO_RATIO: float = 0.20

N_MAX_PAR_ALGO: dict[str, int] = {
    "bubble": 300,
    "selection": 300,
    "insertion": 300,
    "comb": 300,
    "merge": 1000,
    "quick": 1000,
    "heap": 1000,
}


def _jouer_animation_fin(
    screen: pygame.Surface,
    state: dict,
    viz_rect: pygame.Rect,
    clock: pygame.time.Clock,
    history,
) -> None:
    """Display all bars in green + centered banner for 1.5s.

    Interrupted if the user presses a key or clicks.
    """
    arr = state["arr"]
    non_none = [v for v in arr if v is not None]
    if not non_none:
        return
    min_val = min(non_none)
    amplitude = (max(non_none) - min_val) or 1
    n = len(arr)
    bar_w_f = viz_rect.width / max(n, 1)

    try:
        font_ban = pygame.font.SysFont("monospace", 20, bold=True)
        nb_comp = sum(
            1 for k in range(len(history)) if history.step_event(k) == "compare"
        )
        nb_swap = sum(
            1 for k in range(len(history)) if history.step_event(k) in ("swap", "set")
        )
        banniere = f"Sort complete!  {nb_comp} comp.  {nb_swap} swaps"
    except Exception:
        font_ban = None
        banniere = ""

    debut = pygame.time.get_ticks()
    while pygame.time.get_ticks() - debut < 1500:
        for event in pygame.event.get():
            if event.type in (pygame.QUIT, pygame.KEYDOWN, pygame.MOUSEBUTTONDOWN):
                return

        screen.fill(theme.FOND, viz_rect)

        for idx, val in enumerate(arr):
            if val is None:
                continue
            bar_h = max(1, int(viz_rect.height * (val - min_val) / amplitude))
            x = viz_rect.left + int(idx * bar_w_f)
            w = max(1, int((idx + 1) * bar_w_f) - int(idx * bar_w_f))
            pygame.draw.rect(
                screen,
                theme.DONE,
                pygame.Rect(x, viz_rect.bottom - bar_h, w, bar_h),
            )

        if font_ban and banniere:
            surf_ban = font_ban.render(banniere, True, theme.DONE)
            bg_rect = surf_ban.get_rect(center=viz_rect.center).inflate(20, 10)
            pygame.draw.rect(screen, (10, 30, 20), bg_rect, border_radius=6)
            pygame.draw.rect(screen, theme.DONE, bg_rect, width=2, border_radius=6)
            screen.blit(surf_ban, surf_ban.get_rect(center=viz_rect.center))

        pygame.display.flip()
        clock.tick(60)


def run(
    algo_fn,
    size: int,
    preset: str,
    son: bool = False,
    speed: float = 0.05,
    sleep_enabled: bool = True,
    sleep_ms: int = 10,
) -> str:
    """Solo mode: pre-computes all steps then opens the visualizer.

    All steps are computed synchronously before opening the window, which
    allows free back-and-forth navigation via the Timeline.

    Args:
        son: if True, play a tone on each swap (requires pygame.mixer)

    Returns:
        "menu" in all cases (allows the main menu to relaunch).
    """
    algo_name = next((k for k, v in ALGORITHMS.items() if v is algo_fn), "bubble")

    def _precalculer(arr_brut):
        """Run the algorithm without delay; return (StepHistory, nb_none)."""
        valeurs = [v for v in arr_brut if v is not None]
        nb_none_l = len(arr_brut) - len(valeurs)
        arr_tri = valeurs if nb_none_l > 0 else arr_brut

        hist = StepHistory(arr_tri)
        running = arr_tri[:]

        def _on_step(arr_copy, i, j, event_type):
            if event_type == "set":
                hist.add_set(j, running[j], arr_copy[j])
                running[j] = arr_copy[j]
            elif event_type == "swap":
                hist.add_step(i, j, event_type)
                running[i], running[j] = running[j], running[i]
            else:
                hist.add_step(i, j, event_type)

        algo_fn(arr_tri[:], on_step=_on_step)
        return hist, nb_none_l

    arr_brut = _build_array(size, preset)
    history, nb_none = _precalculer(arr_brut)
    current_size = size

    if son:
        try:
            valeurs_son = [
                v for v in arr_brut if v is not None and isinstance(v, (int, float))
            ]
            if valeurs_son:
                generate_tones(valeurs_son)
        except Exception:
            son = False

    pygame.init()
    pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)

    scr_info = pygame.display.Info()
    win_w = max(_MIN_W, int(scr_info.current_w * 0.8))
    win_h = max(_MIN_H, int(scr_info.current_h * 0.8))
    screen = pygame.display.set_mode((win_w, win_h), pygame.RESIZABLE)
    pygame.display.set_caption(f"Sorting Visualizer -- {algo_name}")
    clock = pygame.time.Clock()

    def _calc_solo_layout(w, h):
        sc = theme.scale_factor(h)
        tl_h = max(40, int(TIMELINE_H * sc))
        iw = int(w * INFO_RATIO)
        vw = w - iw
        vh = h - tl_h
        return (
            sc,
            pygame.Rect(0, 0, vw, vh),
            pygame.Rect(vw, 0, iw, vh),
            pygame.Rect(0, vh, w, tl_h),
            pygame.Rect(0, 0, w, h),
        )

    scale, viz_rect, info_rect, timeline_rect, window_rect = _calc_solo_layout(
        win_w, win_h
    )

    def _make_solo_fonts(sc):
        return (
            pygame.font.SysFont("monospace", theme.scaled_font(theme.F_HINT, sc)),
            pygame.font.SysFont("monospace", theme.scaled_font(theme.F_HINT, sc)),
        )

    hint_font, warn_font = _make_solo_fonts(scale)

    renderer = RENDERERS.get(algo_name, BubbleRenderer)()
    timeline = Timeline(timeline_rect, history, scale=scale)
    timeline.set_interval_ms(0 if not sleep_enabled else sleep_ms)
    info_panel = InfoPanel(info_rect, algo_name, history, scale=scale)
    selector = None

    def _reconstruire(arr_brut_nouveau, taille):
        nonlocal history, nb_none, current_size, renderer, timeline, info_panel
        nonlocal animation_jouee, prev_idx
        history, nb_none = _precalculer(arr_brut_nouveau)
        current_size = taille
        animation_jouee = False
        prev_idx = -1
        renderer = RENDERERS.get(algo_name, BubbleRenderer)()
        timeline = Timeline(timeline_rect, history, scale=scale)
        timeline.set_interval_ms(0 if not sleep_enabled else sleep_ms)
        info_panel = InfoPanel(info_rect, algo_name, history, scale=scale)
        if son:
            try:
                valeurs_son = [
                    v
                    for v in arr_brut_nouveau
                    if v is not None and isinstance(v, (int, float))
                ]
                if valeurs_son:
                    generate_tones(valeurs_son)
            except Exception:
                pass

    animation_jouee = False
    prev_idx = -1

    solo_sleep_state = SleepState(enabled=sleep_enabled, ms=sleep_ms)
    sleep_form = SleepForm(
        pygame.Rect(8, viz_rect.bottom - 28, 220, 22),
        solo_sleep_state,
        font=hint_font,
    )

    running = True
    while running:
        dt = clock.tick(FPS) / 1000.0

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
                continue

            if sleep_form.active:
                validated = sleep_form.handle_event(event)
                if validated:
                    timeline.set_interval_ms(
                        0 if not solo_sleep_state.enabled else solo_sleep_state.ms
                    )
                continue

            if event.type == pygame.VIDEORESIZE:
                win_w = max(_MIN_W, event.w)
                win_h = max(_MIN_H, event.h)
                screen = pygame.display.set_mode((win_w, win_h), pygame.RESIZABLE)
                scale, viz_rect, info_rect, timeline_rect, window_rect = (
                    _calc_solo_layout(win_w, win_h)
                )
                hint_font, warn_font = _make_solo_fonts(scale)
                timeline = Timeline(timeline_rect, history, scale=scale)
                info_panel = InfoPanel(info_rect, algo_name, history, scale=scale)
                continue

            if selector is not None and selector.is_active:
                résultat = selector.handle_event(event)
                if résultat is not None:
                    from visualization.datasets import generate

                    preset_key, n = résultat
                    _reconstruire(generate(preset_key, n), n)
                    selector = None
                elif not selector.is_active:
                    selector = None
                continue

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_F11:
                    pygame.display.toggle_fullscreen()
                    continue

                if event.key in (pygame.K_q, pygame.K_m):
                    running = False

                elif event.key == pygame.K_SPACE:
                    timeline.toggle_pause()

                elif event.key == pygame.K_d:
                    selector = DatasetSelector(
                        window_rect, algo_name, n_initial=current_size, scale=scale
                    )

                elif event.key == pygame.K_e:
                    sleep_form.set_rect(pygame.Rect(8, viz_rect.bottom - 28, 220, 22))
                    sleep_form.open()

                elif event.key in (pygame.K_r, pygame.K_s, pygame.K_i):
                    code = {
                        pygame.K_r: "r",
                        pygame.K_s: "s",
                        pygame.K_i: "i",
                    }[event.key]
                    _reconstruire(_build_array(current_size, code), current_size)

                else:
                    timeline.handle_event(event)

            elif event.type in (
                pygame.MOUSEBUTTONDOWN,
                pygame.MOUSEBUTTONUP,
                pygame.MOUSEMOTION,
            ):
                timeline.handle_event(event)

        timeline.tick(dt)

        current_idx = timeline.index
        state = history.get_state(current_idx)

        if son and current_idx != prev_idx:
            if (
                history.step_event(current_idx) in ("swap", "set")
                and state["highlighted"] is not None
            ):
                try:
                    i_son = state["highlighted"][0]
                    val_son = state["arr"][i_son] if i_son < len(state["arr"]) else None
                    if val_son is not None:
                        play_tone(val_son)
                except Exception:
                    pass
        prev_idx = current_idx

        screen.fill(theme.FOND)

        renderer.draw(screen, state, viz_rect)

        info_panel.draw(screen, state, current_idx, len(history))

        timeline.draw(screen)

        seuil = N_MAX_PAR_ALGO.get(algo_name, 1000)
        if current_size > seuil:
            surf = warn_font.render(
                f"[WARN] N={current_size} > threshold {seuil} ({algo_name})",
                True,
                (255, 180, 60),
            )
            screen.blit(surf, (viz_rect.left + 8, viz_rect.top + 8))

        if selector is not None and selector.is_active:
            selector.draw(screen)

        if sleep_form.active:
            sleep_form.set_rect(pygame.Rect(8, viz_rect.bottom - 28, 220, 22))
            sleep_form.draw(screen)

        hint = "Space Pause  R Random  S Sorted  I Inverted  D Dataset  E Sleep  1-5 Speed  F11 Fullscreen  M Menu"
        hint_surf = hint_font.render(hint, True, theme.DISCRET)
        screen.blit(hint_surf, (8, viz_rect.bottom - hint_surf.get_height() - 4))

        total_steps = len(history)
        if current_idx >= total_steps - 1 and not animation_jouee and total_steps > 1:
            animation_jouee = True
            _jouer_animation_fin(screen, state, viz_rect, clock, history)

        pygame.display.flip()

    pygame.quit()
    return "menu"
