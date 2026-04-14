"""Score matrix screen for benchmark results.

Displays a heatmap table of algorithm performance across datasets,
with metric tabs, N filters, and session management.

Public interface:
    run_score_screen(screen, db_path) -> None
"""

import time as _time
from datetime import datetime
import pygame

from visualization import theme
from visualization.datasets import PRESETS_META
from sorting import ALGORITHMS

# ---------------------------------------------------------------------------
# Identity colors per algorithm (matches each renderer)
# ---------------------------------------------------------------------------

ALGO_COLORS: dict[str, tuple[int, int, int]] = {
    "bubble": (0, 255, 136),  # #00ff88
    "selection": (255, 107, 53),  # #ff6b35
    "insertion": (167, 139, 250),  # #a78bfa
    "merge": (56, 189, 248),  # #38bdf8
    "quick": (239, 68, 68),  # #ef4444
    "heap": (245, 158, 11),  # #f59e0b
    "comb": (244, 114, 182),  # #f472b6
}

_ALGO_KEYS = list(ALGORITHMS.keys())
_DATASET_KEYS = [k for k, v in PRESETS_META.items() if v.get("benchmarkable", True)]
_METRICS = ["time", "comparisons", "swaps"]
_METRIC_LABELS = ["Time (ms)", "Comparisons", "Swaps"]
_N_VALUES = [100, 500, 1000]
_AGGREGATIONS = ["avg", "min", "max"]

# Colors
_C_FOND = (14, 14, 20)
_C_PANEL = (22, 33, 62)
_C_CONTOUR = (52, 52, 70)
_C_TITRE = (190, 215, 255)
_C_TEXTE = (205, 210, 222)
_C_SOUS = (125, 140, 170)
_C_GRIS = (95, 105, 125)
_C_DISCRET = (60, 68, 85)
_C_TAB_ON = theme.SWAP
_C_TAB_OFF = (48, 48, 62)
_C_BTN = (36, 40, 55)
_C_BTN_HOVER = (52, 58, 78)
_C_BTN_ACCENT = theme.SWAP
_C_GREEN = theme.DONE
_C_ORANGE = theme.COMPARE
_C_RED = theme.SWAP
_C_CONFIRM_BG = (40, 20, 20)

FPS = 60
PAD = 10


# ---------------------------------------------------------------------------
# Heatmap color interpolation
# ---------------------------------------------------------------------------


def _lerp_color(t: float) -> tuple[int, int, int]:
    """Interpolate green -> orange -> red for t in [0, 1]."""
    t = max(0.0, min(1.0, t))
    if t < 0.5:
        r = t * 2.0
        return (
            int(_C_GREEN[0] + (_C_ORANGE[0] - _C_GREEN[0]) * r),
            int(_C_GREEN[1] + (_C_ORANGE[1] - _C_GREEN[1]) * r),
            int(_C_GREEN[2] + (_C_ORANGE[2] - _C_GREEN[2]) * r),
        )
    r = (t - 0.5) * 2.0
    return (
        int(_C_ORANGE[0] + (_C_RED[0] - _C_ORANGE[0]) * r),
        int(_C_ORANGE[1] + (_C_RED[1] - _C_ORANGE[1]) * r),
        int(_C_ORANGE[2] + (_C_RED[2] - _C_ORANGE[2]) * r),
    )


# ---------------------------------------------------------------------------
# Sub-views
# ---------------------------------------------------------------------------

_VIEW_MATRIX = "matrix"
_VIEW_SESSIONS = "sessions"
_VIEW_PROGRESS = "progress"


class _ScoreScreen:
    """Internal state for the score screen."""

    def __init__(self, screen: pygame.Surface, db_path: str) -> None:
        self._screen = screen
        self._db_path = db_path
        self._w, self._h = screen.get_size()

        self._view = _VIEW_MATRIX
        self._metric_idx = 0
        self._n_idx = 2  # default N=1000
        self._agg_idx = 0  # default AVG

        # Session view
        self._session_cursor = 0
        self._sessions: list[dict] = []

        # Progress view
        self._progress_current = 0
        self._progress_total = 0
        self._progress_label = ""
        self._progress_cancelled = False
        self._progress_start_time = 0.0

        # Confirm delete dialog
        self._confirm_delete = False

        # Note editing
        self._editing_note = False
        self._note_text = ""

        # Matrix data cache
        self._matrix: dict = {}

        self._recalc()
        self._refresh_data()

    def _recalc(self) -> None:
        """Recompute fonts and layout after resize."""
        self._w, self._h = self._screen.get_size()
        sc = theme.scale_factor(self._h)
        self._f_xl = pygame.font.SysFont(
            "monospace", theme.scaled_font(22, sc), bold=True
        )
        self._f_lg = pygame.font.SysFont(
            "monospace", theme.scaled_font(16, sc), bold=True
        )
        self._f_md = pygame.font.SysFont(
            "monospace", theme.scaled_font(13, sc), bold=True
        )
        self._f_sm = pygame.font.SysFont("monospace", theme.scaled_font(11, sc))
        self._f_xs = pygame.font.SysFont("monospace", theme.scaled_font(10, sc))

    def _refresh_data(self) -> None:
        """Reload matrix data and session list from database."""
        from benchmarks.database import get_matrix, get_sessions, get_run_count

        metric = _METRICS[self._metric_idx]
        agg = _AGGREGATIONS[self._agg_idx]
        n = _N_VALUES[self._n_idx]
        self._matrix = get_matrix(self._db_path, metric, agg, n)
        self._sessions = get_sessions(self._db_path)
        self._total_runs = get_run_count(self._db_path)

        # Compute column min/max for heatmap normalization
        self._col_range: dict[str, tuple[float, float]] = {}
        for ds in _DATASET_KEYS:
            vals = [self._matrix.get((a, ds)) for a in _ALGO_KEYS]
            vals = [v for v in vals if v is not None]
            if vals:
                self._col_range[ds] = (min(vals), max(vals))

    # ------------------------------------------------------------------
    # Drawing: matrix view
    # ------------------------------------------------------------------

    def _draw_matrix(self) -> None:
        s = self._screen
        s.fill(_C_FOND)

        y = PAD

        # Header
        title = self._f_xl.render("Score Matrix", True, _C_GREEN)
        s.blit(title, (PAD, y))

        last_ts = self._sessions[0]["timestamp"] if self._sessions else "--"
        if isinstance(last_ts, str):
            last_ts = last_ts[:10]
        info = self._f_xs.render(
            f"{len(self._sessions)} sessions | {self._total_runs} runs | Last: {last_ts}",
            True,
            _C_GRIS,
        )
        s.blit(info, (self._w - info.get_width() - PAD, y + 6))
        y += title.get_height() + PAD

        # Metric tabs
        tab_x = PAD
        self._tab_rects = []
        for i, label in enumerate(_METRIC_LABELS):
            surf = self._f_md.render(
                label, True, (255, 255, 255) if i == self._metric_idx else _C_GRIS
            )
            tw = surf.get_width() + 20
            rect = pygame.Rect(tab_x, y, tw, 26)
            color = _C_TAB_ON if i == self._metric_idx else _C_TAB_OFF
            pygame.draw.rect(s, color, rect, border_radius=4)
            s.blit(surf, (tab_x + 10, y + 4))
            self._tab_rects.append(rect)
            tab_x += tw + 4

        # Aggregation toggle (right-aligned)
        agg_label = f"Aggregation: {_AGGREGATIONS[self._agg_idx].upper()}"
        agg_surf = self._f_sm.render(agg_label, True, _C_SOUS)
        self._agg_rect = pygame.Rect(
            self._w - agg_surf.get_width() - 24 - PAD, y, agg_surf.get_width() + 24, 26
        )
        pygame.draw.rect(s, _C_TAB_OFF, self._agg_rect, border_radius=4)
        s.blit(agg_surf, (self._agg_rect.x + 12, y + 5))
        y += 32

        # N filter
        nx = PAD
        n_label = self._f_sm.render("N =", True, _C_GRIS)
        s.blit(n_label, (nx, y + 4))
        nx += n_label.get_width() + 8
        self._n_rects = []
        for i, nv in enumerate(_N_VALUES):
            surf = self._f_md.render(
                str(nv), True, _C_FOND if i == self._n_idx else _C_GRIS
            )
            nw = surf.get_width() + 16
            rect = pygame.Rect(nx, y, nw, 24)
            if i == self._n_idx:
                pygame.draw.rect(s, _C_ORANGE, rect, border_radius=4)
            else:
                pygame.draw.rect(s, _C_TAB_OFF, rect, border_radius=4)
            s.blit(surf, (nx + 8, y + 3))
            self._n_rects.append(rect)
            nx += nw + 4
        y += 30

        # Table
        self._draw_table(s, y)

        # Bottom action bar
        self._draw_action_bar(s)

    def _draw_table(self, s: pygame.Surface, y_start: int) -> None:
        """Draw the algorithm x dataset matrix table."""
        bar_h = 36  # action bar height
        available_h = self._h - y_start - bar_h - PAD
        row_h = min(28, max(18, available_h // (len(_ALGO_KEYS) + 1)))

        # Column widths
        col_algo_w = max(80, int(self._w * 0.09))
        remaining = self._w - col_algo_w - 2 * PAD - 60  # 60 for AVG column
        col_w = max(55, remaining // len(_DATASET_KEYS))
        avg_col_w = 60

        x_start = PAD
        y = y_start

        # Header row (dataset labels)
        x = x_start + col_algo_w
        surf_h = self._f_xs.render("Algorithm", True, _C_GRIS)
        s.blit(surf_h, (x_start + 4, y + row_h // 2 - surf_h.get_height() // 2))

        for ds in _DATASET_KEYS:
            label = PRESETS_META[ds]["label"]
            if len(label) > 8:
                label = label[:7] + "."
            surf = self._f_xs.render(label, True, _C_GRIS)
            s.blit(
                surf,
                (
                    x + col_w // 2 - surf.get_width() // 2,
                    y + row_h // 2 - surf.get_height() // 2,
                ),
            )
            x += col_w

        # AVG column header
        surf_avg = self._f_xs.render("AVG", True, _C_ORANGE)
        s.blit(
            surf_avg,
            (
                x + avg_col_w // 2 - surf_avg.get_width() // 2,
                y + row_h // 2 - surf_avg.get_height() // 2,
            ),
        )

        y += row_h
        pygame.draw.line(
            s,
            _C_CONTOUR,
            (x_start, y),
            (x_start + col_algo_w + col_w * len(_DATASET_KEYS) + avg_col_w, y),
            2,
        )
        y += 2

        # Data rows
        for algo in _ALGO_KEYS:
            x = x_start
            # Alternating row background
            row_rect = pygame.Rect(
                x, y, col_algo_w + col_w * len(_DATASET_KEYS) + avg_col_w, row_h
            )
            if _ALGO_KEYS.index(algo) % 2 == 0:
                pygame.draw.rect(s, (18, 18, 28), row_rect)

            # Algorithm name
            algo_color = ALGO_COLORS.get(algo, _C_TEXTE)
            surf_name = self._f_sm.render(algo, True, algo_color)
            s.blit(surf_name, (x + 4, y + row_h // 2 - surf_name.get_height() // 2))
            x += col_algo_w

            # Values per dataset
            row_values = []
            for ds in _DATASET_KEYS:
                val = self._matrix.get((algo, ds))
                row_values.append(val)

                cell_rect = pygame.Rect(x, y, col_w, row_h)

                if val is not None:
                    # Heatmap background
                    vmin, vmax = self._col_range.get(ds, (0, 1))
                    span = vmax - vmin
                    t = (val - vmin) / span if span > 0 else 0.5
                    hc = _lerp_color(t)
                    bg = (hc[0] // 5, hc[1] // 5, hc[2] // 5)
                    pygame.draw.rect(s, bg, cell_rect)

                    # Value text
                    display = self._format_value(val)
                    text_color = _lerp_color(t)
                    surf_v = self._f_xs.render(display, True, text_color)
                    s.blit(
                        surf_v,
                        (
                            x + col_w - surf_v.get_width() - 4,
                            y + row_h // 2 - surf_v.get_height() // 2,
                        ),
                    )
                else:
                    surf_v = self._f_xs.render("--", True, _C_DISCRET)
                    s.blit(
                        surf_v,
                        (
                            x + col_w // 2 - surf_v.get_width() // 2,
                            y + row_h // 2 - surf_v.get_height() // 2,
                        ),
                    )
                x += col_w

            # AVG column
            valid_vals = [v for v in row_values if v is not None]
            if valid_vals:
                avg_val = sum(valid_vals) / len(valid_vals)
                display = self._format_value(avg_val)
                surf_a = self._f_sm.render(display, True, _C_ORANGE)
                s.blit(
                    surf_a,
                    (
                        x + avg_col_w - surf_a.get_width() - 4,
                        y + row_h // 2 - surf_a.get_height() // 2,
                    ),
                )

            y += row_h
            pygame.draw.line(
                s, (28, 28, 38), (x_start, y), (x_start + row_rect.width, y)
            )

        # Bottom legend
        y += 8
        legend = self._f_xs.render(
            "Heatmap: fast  medium  slow  |  Tab: next metric  |  1/2/3: select N  |  A: aggregation",
            True,
            _C_DISCRET,
        )
        s.blit(legend, (PAD, y))

    def _format_value(self, val: float) -> str:
        """Format a metric value for display."""
        metric = _METRICS[self._metric_idx]
        if metric == "time":
            ms = val * 1000
            if ms < 1:
                return f"{ms:.3f}"
            if ms < 100:
                return f"{ms:.1f}"
            return f"{int(ms)}"
        if val > 999999:
            return f"{val / 1000:.0f}k"
        return f"{int(val)}"

    def _draw_action_bar(self, s: pygame.Surface) -> None:
        """Draw the bottom action bar."""
        bar_h = 36
        bar_y = self._h - bar_h
        pygame.draw.line(s, _C_CONTOUR, (0, bar_y), (self._w, bar_y))

        x = PAD
        self._btn_rects = {}

        for key, label, accent in [
            ("run", "Run All Benchmarks (R)", True),
            ("sessions", f"Sessions ({len(self._sessions)})", False),
            ("csv", "Export CSV (C)", False),
            ("pdf", "Export PDF (P)", False),
        ]:
            surf = self._f_sm.render(
                label, True, (255, 255, 255) if accent else _C_SOUS
            )
            bw = surf.get_width() + 20
            rect = pygame.Rect(x, bar_y + 5, bw, 26)
            bg = _C_BTN_ACCENT if accent else _C_BTN
            pygame.draw.rect(s, bg, rect, border_radius=4)
            s.blit(surf, (x + 10, bar_y + 9))
            self._btn_rects[key] = rect
            x += bw + 8

        # ESC hint (right-aligned)
        esc = self._f_sm.render("ESC: Back", True, _C_DISCRET)
        s.blit(esc, (self._w - esc.get_width() - PAD, bar_y + 10))

    # ------------------------------------------------------------------
    # Drawing: sessions view
    # ------------------------------------------------------------------

    def _draw_sessions(self) -> None:
        s = self._screen
        s.fill(_C_FOND)

        y = PAD
        title = self._f_xl.render("Benchmark Sessions", True, _C_GREEN)
        s.blit(title, (PAD, y))

        info = self._f_xs.render(
            f"{len(self._sessions)} sessions | {self._total_runs} total runs",
            True,
            _C_GRIS,
        )
        s.blit(info, (self._w - info.get_width() - PAD, y + 6))
        y += title.get_height() + PAD + 4

        # Session list
        ITEM_H = 42
        self._session_rects = []
        for i, sess in enumerate(self._sessions):
            rect = pygame.Rect(PAD, y, self._w - 2 * PAD, ITEM_H)
            self._session_rects.append(rect)

            selected = i == self._session_cursor
            bg = (37, 37, 69) if selected else (26, 26, 40)
            pygame.draw.rect(s, bg, rect, border_radius=4)
            if selected:
                pygame.draw.rect(s, _C_ORANGE, rect, width=1, border_radius=4)

            # Cursor
            if selected:
                cursor = self._f_md.render(">", True, _C_ORANGE)
                s.blit(cursor, (rect.x + 6, rect.centery - cursor.get_height() // 2))

            # Timestamp
            try:
                ts = datetime.fromisoformat(sess["timestamp"])
                date_str = ts.strftime("%Y-%m-%d %H:%M")
            except Exception:
                date_str = sess["timestamp"][:16]
            surf_ts = self._f_sm.render(date_str, True, _C_TEXTE)
            s.blit(surf_ts, (rect.x + 22, rect.y + 4))

            # Relative time
            try:
                ts = datetime.fromisoformat(sess["timestamp"])
                delta = int(_time.time() - ts.timestamp())
                if delta < 60:
                    rel = "just now"
                elif delta < 3600:
                    rel = f"{delta // 60} min ago"
                elif delta < 86400:
                    rel = f"{delta // 3600} h ago"
                else:
                    rel = f"{delta // 86400} d ago"
            except Exception:
                rel = ""
            surf_rel = self._f_xs.render(rel, True, _C_DISCRET)
            s.blit(surf_rel, (rect.x + 22, rect.y + 22))

            # Run count
            rc_color = _C_GREEN if sess["run_count"] >= 70 else _C_ORANGE
            surf_rc = self._f_sm.render(f"{sess['run_count']} runs", True, rc_color)
            s.blit(surf_rc, (rect.x + 180, rect.centery - surf_rc.get_height() // 2))

            # N values
            surf_n = self._f_xs.render(f"N: {sess['n_values']}", True, _C_SOUS)
            s.blit(surf_n, (rect.x + 280, rect.centery - surf_n.get_height() // 2))

            # Dataset coverage
            dc = sess["dataset_count"]
            _total = len(_DATASET_KEYS)
            dc_color = _C_GREEN if dc >= _total else (_C_ORANGE if dc >= 5 else _C_RED)
            surf_dc = self._f_xs.render(f"Datasets: {dc}/{_total}", True, dc_color)
            s.blit(surf_dc, (rect.x + 420, rect.centery - surf_dc.get_height() // 2))

            # Note
            note = sess["note"] or ""
            if self._editing_note and selected:
                note_display = self._note_text + "|"
                note_color = _C_TITRE
            else:
                note_display = note
                note_color = _C_DISCRET
            if note_display:
                surf_note = self._f_xs.render(note_display, True, note_color)
                s.blit(
                    surf_note,
                    (rect.x + 570, rect.centery - surf_note.get_height() // 2),
                )

            y += ITEM_H + 4

        # Empty state
        if not self._sessions:
            empty = self._f_md.render(
                "No sessions yet -- Press ESC to go back and run a benchmark",
                True,
                _C_GRIS,
            )
            s.blit(empty, (self._w // 2 - empty.get_width() // 2, self._h // 2))

        # Action bar
        bar_y = self._h - 36
        pygame.draw.line(s, _C_CONTOUR, (0, bar_y), (self._w, bar_y))

        actions = self._f_sm.render(
            "Del: Delete  |  E: Edit note  |  ESC: Back to matrix",
            True,
            _C_GRIS,
        )
        s.blit(actions, (PAD, bar_y + 10))

        # Confirm delete dialog
        if self._confirm_delete:
            self._draw_confirm_dialog(s)

    def _draw_confirm_dialog(self, s: pygame.Surface) -> None:
        """Draw a confirmation overlay for session deletion."""
        overlay = pygame.Surface((self._w, self._h), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        s.blit(overlay, (0, 0))

        dw, dh = 360, 120
        rect = pygame.Rect(self._w // 2 - dw // 2, self._h // 2 - dh // 2, dw, dh)
        pygame.draw.rect(s, (30, 20, 20), rect, border_radius=8)
        pygame.draw.rect(s, _C_RED, rect, width=1, border_radius=8)

        msg = self._f_md.render("Delete this session?", True, _C_TEXTE)
        s.blit(msg, (rect.centerx - msg.get_width() // 2, rect.y + 20))

        hint = self._f_sm.render("Enter: Confirm  |  ESC: Cancel", True, _C_GRIS)
        s.blit(hint, (rect.centerx - hint.get_width() // 2, rect.y + 70))

    # ------------------------------------------------------------------
    # Drawing: progress view
    # ------------------------------------------------------------------

    def _draw_progress(self) -> None:
        s = self._screen
        s.fill(_C_FOND)

        cy = self._h // 2

        title = self._f_xl.render("Running Benchmarks...", True, _C_ORANGE)
        s.blit(title, (self._w // 2 - title.get_width() // 2, cy - 80))

        # Progress bar
        bar_w = min(600, self._w - 100)
        bar_h = 24
        bar_x = self._w // 2 - bar_w // 2
        bar_y = cy - 10
        pygame.draw.rect(s, _C_TAB_OFF, (bar_x, bar_y, bar_w, bar_h), border_radius=4)

        if self._progress_total > 0:
            fill_w = int(bar_w * self._progress_current / self._progress_total)
            if fill_w > 0:
                pygame.draw.rect(
                    s, _C_GREEN, (bar_x, bar_y, fill_w, bar_h), border_radius=4
                )

            # Counter
            counter = self._f_md.render(
                f"{self._progress_current} / {self._progress_total}",
                True,
                _C_TEXTE,
            )
            s.blit(
                counter, (self._w // 2 - counter.get_width() // 2, bar_y + bar_h + 10)
            )

        # Current run label
        if self._progress_label:
            lbl = self._f_sm.render(self._progress_label, True, _C_SOUS)
            s.blit(lbl, (self._w // 2 - lbl.get_width() // 2, cy + 40))

        # Elapsed time
        elapsed = _time.time() - self._progress_start_time
        if self._progress_current > 0 and self._progress_total > 0:
            eta = (
                elapsed
                / self._progress_current
                * (self._progress_total - self._progress_current)
            )
            time_str = f"Elapsed: {elapsed:.0f}s  |  ETA: {eta:.0f}s"
        else:
            time_str = f"Elapsed: {elapsed:.0f}s"
        surf_t = self._f_xs.render(time_str, True, _C_GRIS)
        s.blit(surf_t, (self._w // 2 - surf_t.get_width() // 2, cy + 65))

        # ESC hint
        esc = self._f_xs.render(
            "ESC to cancel (completed runs will be saved)", True, _C_DISCRET
        )
        s.blit(esc, (self._w // 2 - esc.get_width() // 2, cy + 100))

    # ------------------------------------------------------------------
    # Drawing: empty state
    # ------------------------------------------------------------------

    def _draw_empty(self, s: pygame.Surface) -> None:
        msg = self._f_lg.render(
            "No data -- Press R to run your first benchmark", True, _C_GRIS
        )
        s.blit(
            msg,
            (self._w // 2 - msg.get_width() // 2, self._h // 2 - msg.get_height() // 2),
        )

    # ------------------------------------------------------------------
    # Main draw dispatch
    # ------------------------------------------------------------------

    def draw(self) -> None:
        if self._view == _VIEW_PROGRESS:
            self._draw_progress()
        elif self._view == _VIEW_SESSIONS:
            self._draw_sessions()
        else:
            if not self._matrix:
                self._screen.fill(_C_FOND)
                self._draw_empty(self._screen)
                self._draw_action_bar(self._screen)
            else:
                self._draw_matrix()

    # ------------------------------------------------------------------
    # Event handling
    # ------------------------------------------------------------------

    def handle_event(self, event: pygame.event.Event) -> str | None:
        """Process one event. Returns 'quit' to exit the screen."""
        if event.type == pygame.QUIT:
            return "quit"

        if event.type == pygame.VIDEORESIZE:
            self._screen = pygame.display.set_mode(
                (max(800, event.w), max(600, event.h)), pygame.RESIZABLE
            )
            self._recalc()
            self._refresh_data()
            return None

        if self._view == _VIEW_MATRIX:
            return self._handle_matrix_event(event)
        elif self._view == _VIEW_SESSIONS:
            return self._handle_sessions_event(event)
        return None

    def _handle_matrix_event(self, event: pygame.event.Event) -> str | None:
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                return "quit"
            if event.key == pygame.K_TAB:
                self._metric_idx = (self._metric_idx + 1) % len(_METRICS)
                self._refresh_data()
            elif event.key == pygame.K_1:
                self._n_idx = 0
                self._refresh_data()
            elif event.key == pygame.K_2:
                self._n_idx = 1
                self._refresh_data()
            elif event.key == pygame.K_3:
                self._n_idx = 2
                self._refresh_data()
            elif event.key == pygame.K_a:
                self._agg_idx = (self._agg_idx + 1) % len(_AGGREGATIONS)
                self._refresh_data()
            elif event.key == pygame.K_r:
                self._start_benchmark()
            elif event.key == pygame.K_s:
                self._view = _VIEW_SESSIONS
                self._session_cursor = 0
            elif event.key == pygame.K_c:
                self._export_csv()
            elif event.key == pygame.K_p:
                self._export_pdf()

        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            pos = event.pos
            # Tab clicks
            for i, rect in enumerate(getattr(self, "_tab_rects", [])):
                if rect.collidepoint(pos):
                    self._metric_idx = i
                    self._refresh_data()
                    return None
            # N filter clicks
            for i, rect in enumerate(getattr(self, "_n_rects", [])):
                if rect.collidepoint(pos):
                    self._n_idx = i
                    self._refresh_data()
                    return None
            # Aggregation click
            if hasattr(self, "_agg_rect") and self._agg_rect.collidepoint(pos):
                self._agg_idx = (self._agg_idx + 1) % len(_AGGREGATIONS)
                self._refresh_data()
                return None
            # Action bar clicks
            for key, rect in getattr(self, "_btn_rects", {}).items():
                if rect.collidepoint(pos):
                    if key == "run":
                        self._start_benchmark()
                    elif key == "sessions":
                        self._view = _VIEW_SESSIONS
                        self._session_cursor = 0
                    elif key == "csv":
                        self._export_csv()
                    elif key == "pdf":
                        self._export_pdf()
                    return None

        return None

    def _handle_sessions_event(self, event: pygame.event.Event) -> str | None:
        if event.type == pygame.KEYDOWN:
            # Confirm delete dialog
            if self._confirm_delete:
                if event.key == pygame.K_RETURN:
                    self._do_delete_session()
                    self._confirm_delete = False
                elif event.key == pygame.K_ESCAPE:
                    self._confirm_delete = False
                return None

            # Note editing
            if self._editing_note:
                if event.key == pygame.K_RETURN:
                    self._save_note()
                elif event.key == pygame.K_ESCAPE:
                    self._editing_note = False
                elif event.key == pygame.K_BACKSPACE:
                    self._note_text = self._note_text[:-1]
                elif event.unicode and event.unicode.isprintable():
                    self._note_text += event.unicode
                return None

            if event.key == pygame.K_ESCAPE:
                self._view = _VIEW_MATRIX
                self._refresh_data()
            elif event.key == pygame.K_UP:
                self._session_cursor = max(0, self._session_cursor - 1)
            elif event.key == pygame.K_DOWN:
                self._session_cursor = min(
                    len(self._sessions) - 1, self._session_cursor + 1
                )
            elif event.key == pygame.K_DELETE:
                if self._sessions:
                    self._confirm_delete = True
            elif event.key == pygame.K_e:
                if self._sessions:
                    self._editing_note = True
                    self._note_text = self._sessions[self._session_cursor].get(
                        "note", ""
                    )

        return None

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def _start_benchmark(self) -> None:
        """Run a full benchmark with progress updates."""
        from benchmarks.runner import run_full_benchmark
        from benchmarks.database import insert_session, insert_runs

        self._view = _VIEW_PROGRESS
        self._progress_current = 0
        self._progress_total = len(_ALGO_KEYS) * len(_DATASET_KEYS) * len(_N_VALUES)
        self._progress_label = ""
        self._progress_cancelled = False
        self._progress_start_time = _time.time()

        clock = pygame.time.Clock()

        # We run the benchmark synchronously but pump events for ESC
        sid = insert_session(self._db_path, note="")
        completed_rows = []

        def on_progress(current, total, algo, dataset, n):
            self._progress_current = current
            self._progress_total = total
            self._progress_label = f"{algo} | {dataset} | N={n}"

            # Pump events to keep window responsive and check for ESC
            for ev in pygame.event.get():
                if ev.type == pygame.QUIT:
                    self._progress_cancelled = True
                if ev.type == pygame.KEYDOWN and ev.key == pygame.K_ESCAPE:
                    self._progress_cancelled = True

            self.draw()
            pygame.display.flip()
            clock.tick(FPS)

        results = run_full_benchmark(
            n_values=tuple(_N_VALUES),
            on_progress=on_progress,
        )

        # Filter results up to cancellation point
        for i, r in enumerate(results):
            if self._progress_cancelled and i >= self._progress_current:
                break
            completed_rows.append(r)

        if completed_rows:
            insert_runs(self._db_path, sid, completed_rows)
        else:
            from benchmarks.database import delete_session

            delete_session(self._db_path, sid)

        self._view = _VIEW_MATRIX
        self._refresh_data()

    def _do_delete_session(self) -> None:
        """Delete the currently selected session."""
        if not self._sessions:
            return
        from benchmarks.database import delete_session

        sess = self._sessions[self._session_cursor]
        delete_session(self._db_path, sess["id"])
        self._sessions = []
        self._refresh_data()
        self._session_cursor = min(
            self._session_cursor, max(0, len(self._sessions) - 1)
        )

    def _save_note(self) -> None:
        """Save the edited note to the database."""
        if not self._sessions:
            return
        from benchmarks.database import update_session_note

        sess = self._sessions[self._session_cursor]
        update_session_note(self._db_path, sess["id"], self._note_text)
        self._editing_note = False
        self._refresh_data()

    def _export_csv(self) -> None:
        from benchmarks.exporter import export_csv

        export_csv(self._db_path)

    def _export_pdf(self) -> None:
        from benchmarks.exporter import export_pdf

        export_pdf(self._db_path)


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def run_score_screen(screen: pygame.Surface, db_path: str) -> None:
    """Main loop for the score matrix screen.

    Args:
        screen:  existing pygame display surface.
        db_path: path to the SQLite benchmark database.
    """
    sc = _ScoreScreen(screen, db_path)
    clock = pygame.time.Clock()

    while True:
        for event in pygame.event.get():
            result = sc.handle_event(event)
            if result == "quit":
                return

        sc.draw()
        pygame.display.flip()
        clock.tick(FPS)
