"""Comb sort renderer: classic bars with a horizontal gap arrow.

Identity color: #f472b6 (pink).
"""

import pygame

from visualization.renderers.base import BaseRenderer


# Colors
_ROSE = (244, 114, 182)  # #f472b6 -- identity color
_JAUNE = (255, 255, 0)  # active comparison
_ROUGE_V = (255, 50, 50)  # active swap

_LABEL_FONT_SIZE = 16
_ARROW_HEAD_SIZE = 7  # half-height of each arrowhead (pixels)
_ARROW_THICKNESS = 2  # thickness of the main arrow line
_LABEL_TOP_H = 28  # height reserved for the top "gap = X" label


class CombRenderer(BaseRenderer):
    """Renderer for the comb sort algorithm.

    Displays vertical bars and a horizontal double arrow between
    the two compared elements, visually representing the current gap.

    - The ``gap = X`` label is displayed centered at the top (X = |j - i|).
    - The arrow naturally shortens with each pass: as the gap
      shrinks, the two bars draw closer and the arrow follows.
    """

    def __init__(self) -> None:
        self._font: pygame.font.Font | None = None

    # ------------------------------------------------------------------ #
    # Main interface                                                       #
    # ------------------------------------------------------------------ #

    def draw(
        self,
        surface: pygame.Surface,
        state: dict,
        rect: pygame.Rect,
    ) -> None:
        """Draws the comb sort state in the rect zone.

        Args:
            surface: destination pygame surface
            state:   {"arr", "highlighted", "done"}
            rect:    drawing zone assigned to this renderer
        """
        arr: list[int | float] = state["arr"]
        highlighted: tuple[int, int, str] | None = state["highlighted"]
        done: bool = state["done"]
        n = len(arr)
        if n == 0:
            return

        if self._font is None:
            self._font = pygame.font.SysFont("monospace", _LABEL_FONT_SIZE)
        assert self._font is not None

        # Decompose the active state
        hi_i: int | None = None
        hi_j: int | None = None
        gap: int | None = None
        bar_hi_color = _JAUNE

        if highlighted is not None:
            hi_i, hi_j, event_type = highlighted
            bar_hi_color = _JAUNE if event_type == "compare" else _ROUGE_V
            if hi_i is not None and hi_j is not None:
                gap = abs(hi_j - hi_i)

        # Bar zone below the top label reserve
        bars_rect = pygame.Rect(
            rect.left,
            rect.top + _LABEL_TOP_H,
            rect.width,
            rect.height - _LABEL_TOP_H,
        )

        non_none_vals = [v for v in arr if v is not None]
        min_val: float = float(min(non_none_vals, default=0))
        max_val: float = float(max(non_none_vals, default=1)) or 1.0
        amplitude: float = (max_val - min_val) or 1.0
        bar_w_f: float = bars_rect.width / n
        hi_set: frozenset[int] = frozenset(x for x in (hi_i, hi_j) if x is not None)

        # Zero reference line for data with negative values
        if min_val < 0 < max_val:
            zero_t = (0.0 - min_val) / amplitude
            zero_y = bars_rect.bottom - int(bars_rect.height * zero_t)
            pygame.draw.line(
                surface,
                (150, 150, 165),
                (bars_rect.left, zero_y),
                (bars_rect.right, zero_y),
                1,
            )

        # Draw bars
        for idx in range(n):
            val = arr[idx]
            if val is None:
                continue

            bar_h = max(1, int(bars_rect.height * (val - min_val) / amplitude))
            x = bars_rect.left + int(idx * bar_w_f)
            y = bars_rect.bottom - bar_h
            w = max(1, int((idx + 1) * bar_w_f) - int(idx * bar_w_f))

            if idx in hi_set:
                color = bar_hi_color
            else:
                # Dark -> light gradient according to normalized value
                t_color = (val - min_val) / amplitude
                intensity = int(60 + 160 * t_color)
                color = (intensity, intensity, intensity)

            pygame.draw.rect(surface, color, pygame.Rect(x, y, w, bar_h))

        # Horizontal arrow between the two compared bars
        if hi_i is not None and hi_j is not None and gap is not None and gap > 0:
            self._draw_gap_arrow(
                surface, arr, bars_rect, bar_w_f, min_val, amplitude, hi_i, hi_j
            )

        # "gap = X" label centered at the top
        self._draw_gap_label(surface, rect, gap, done)

    # ------------------------------------------------------------------ #
    # Private methods                                                      #
    # ------------------------------------------------------------------ #

    def _draw_gap_arrow(
        self,
        surface: pygame.Surface,
        arr: list[int | float],
        bars_rect: pygame.Rect,
        bar_w_f: float,
        min_val: float,
        amplitude: float,
        hi_i: int,
        hi_j: int,
    ) -> None:
        """Draws the double arrow connecting bars hi_i and hi_j.

        The arrow is positioned slightly above the top of the tallest
        bar (the one whose top is highest on screen, i.e. the smallest
        in value) to remain always visible.

        Args:
            surface:   destination surface
            arr:       current array of values
            bars_rect: bar drawing zone
            bar_w_f:   floating-point width of one bar (pixels)
            min_val:   minimum value among non-None elements
            amplitude: range (max - min), > 0
            hi_i:      index of the first compared element
            hi_j:      index of the second compared element
        """
        left_idx = min(hi_i, hi_j)
        right_idx = max(hi_i, hi_j)

        def bar_center_x(idx: int) -> int:
            x = bars_rect.left + int(idx * bar_w_f)
            w = max(1, int((idx + 1) * bar_w_f) - int(idx * bar_w_f))
            return x + w // 2

        def bar_top_y(idx: int) -> int:
            val = arr[idx]
            if val is None:
                return bars_rect.bottom
            bar_h = max(1, int(bars_rect.height * (float(val) - min_val) / amplitude))
            return bars_rect.bottom - bar_h

        cx_l = bar_center_x(left_idx)
        cx_r = bar_center_x(right_idx)

        # Arrow height: above the top of the shorter bar
        arrow_y = min(bar_top_y(left_idx), bar_top_y(right_idx)) - 8
        arrow_y = max(bars_rect.top + 4, arrow_y)

        ah = _ARROW_HEAD_SIZE

        # Main horizontal line
        pygame.draw.line(
            surface, _ROSE, (cx_l, arrow_y), (cx_r, arrow_y), _ARROW_THICKNESS
        )

        # Left arrowhead <- (triangle pointing left)
        pygame.draw.polygon(
            surface,
            _ROSE,
            [
                (cx_l, arrow_y),
                (cx_l + 9, arrow_y - ah),
                (cx_l + 9, arrow_y + ah),
            ],
        )

        # Right arrowhead -> (triangle pointing right)
        pygame.draw.polygon(
            surface,
            _ROSE,
            [
                (cx_r, arrow_y),
                (cx_r - 9, arrow_y - ah),
                (cx_r - 9, arrow_y + ah),
            ],
        )

        # Short vertical tick marks at each end (boundary brackets)
        pygame.draw.line(surface, _ROSE, (cx_l, arrow_y - ah), (cx_l, arrow_y + ah), 1)
        pygame.draw.line(surface, _ROSE, (cx_r, arrow_y - ah), (cx_r, arrow_y + ah), 1)

    def _draw_gap_label(
        self,
        surface: pygame.Surface,
        rect: pygame.Rect,
        gap: int | None,
        done: bool,
    ) -> None:
        """Displays the ``gap = X`` label centered at the top of the zone.

        Args:
            surface: destination surface
            rect:    full renderer zone (including the top reserve)
            gap:     current gap value, or None if unknown
            done:    True if sorting is complete
        """
        if gap is not None:
            text = f"gap = {gap}"
        elif done:
            text = "gap = 1  (done)"
        else:
            text = "gap = ?"

        surf = self._font.render(text, True, _ROSE)
        x = rect.left + (rect.width - surf.get_width()) // 2
        y = rect.top + 4
        surface.blit(surf, (x, y))
