"""Renderer for the bubble sort algorithm.

Visualization: vertical bars colored in HSV according to their value.
A green line marks the boundary between the unsorted area (left)
and the sorted area (right); it advances one step after each complete pass.

Events received:
    compare : (j, j+1, "compare") -- adjacent pair being compared
    swap    : (j, j+1, "swap")    -- adjacent pair being swapped
"""

import colorsys

import pygame

from visualization.renderers.base import BaseRenderer

_COULEUR_ALGO = (0, 255, 136)  # #00ff88 -- bubble green
_COULEUR_COMPARE = (255, 255, 0)  # yellow -- comparison
_COULEUR_SWAP = (255, 50, 50)  # red -- swap


def _hsv_couleur(t: float) -> tuple[int, int, int]:
    """Convert a normalized value t in [0, 1] to an HSV color.

    The hue ranges from red-orange (t=0) to cyan-green (t=1), without
    wrapping around the full color wheel (range reduced to 0.65).

    Args:
        t: normalized value between 0 and 1

    Returns:
        Tuple (r, g, b) with values 0-255.
    """
    h = t * 0.65
    r, g, b = colorsys.hsv_to_rgb(h, 0.85, 0.88)
    return (int(r * 255), int(g * 255), int(b * 255))


class BubbleRenderer(BaseRenderer):
    """Renderer for bubble sort.

    Boundary deduction strategy: in bubble_sort, max(j, j+1)
    increases throughout a pass then drops back to 1 when the next pass
    starts. This drop signals that one more element is sorted on the right,
    which decrements the boundary.
    """

    def __init__(self) -> None:
        """Initialize the renderer with an undetermined boundary."""
        self._frontier: int = -1  # -1 = not yet initialized
        self._prev_max: int = -1  # max(i, j) of the last processed highlighted
        self._prev_highlighted: tuple[int, int, str] | None = None
        self._font: pygame.font.Font | None = None

    def draw(
        self,
        surface: pygame.Surface,
        state: dict,
        rect: pygame.Rect,
    ) -> None:
        """Draw the current bubble sort state within the rect area.

        Args:
            surface: destination pygame surface
            state:   dictionary {"arr", "highlighted", "done"}
            rect:    drawing area assigned to this renderer
        """
        arr: list[int | float] = state["arr"]
        highlighted: tuple[int, int, str] | None = state.get("highlighted")
        done: bool = state.get("done", False)
        n = len(arr)

        if n == 0:
            return

        # Lazy font initialization
        if self._font is None:
            self._font = pygame.font.SysFont("monospace", 12)

        # Initialize boundary on first call
        if self._frontier < 0:
            self._frontier = n

        # Update boundary only when highlighted changes
        if highlighted != self._prev_highlighted:
            if highlighted is not None:
                i_h, j_h, _ = highlighted
                curr_max = max(i_h, j_h)
                # Drop in curr_max -> new pass: one more element is sorted
                if self._prev_max >= 0 and curr_max < self._prev_max:
                    self._frontier = max(0, self._frontier - 1)
                self._prev_max = curr_max
            self._prev_highlighted = highlighted

        if done:
            self._frontier = 0

        # Highlight colors
        hi_i, hi_j = -1, -1
        hi_color: tuple[int, int, int] = _COULEUR_COMPARE
        if highlighted is not None:
            hi_i, hi_j, event_type = highlighted
            hi_color = _COULEUR_SWAP if event_type == "swap" else _COULEUR_COMPARE

        non_none: list[float] = [v for v in arr if v is not None]
        if not non_none:
            return
        min_val: float = min(non_none)
        max_val: float = max(non_none) or 1
        amplitude: float = (max_val - min_val) or 1
        bar_w_f: float = rect.width / n

        # Zero reference line for data containing negative values
        if min_val < 0 < max_val:
            zero_t = (0.0 - min_val) / amplitude
            zero_y = rect.bottom - int(rect.height * zero_t)
            pygame.draw.line(
                surface, (150, 150, 165), (rect.left, zero_y), (rect.right, zero_y), 1
            )

        # Draw bars
        for idx, val in enumerate(arr):
            if val is None:
                continue  # empty bar for None values
            bar_h = max(1, int(rect.height * (val - min_val) / amplitude))
            x = rect.left + int(idx * bar_w_f)
            y = rect.bottom - bar_h
            w = max(1, int((idx + 1) * bar_w_f) - int(idx * bar_w_f))
            bar = pygame.Rect(x, y, w, bar_h)

            if idx in (hi_i, hi_j):
                color = hi_color
            else:
                t = (val - min_val) / amplitude
                color = _hsv_couleur(t)

            pygame.draw.rect(surface, color, bar)

        # Boundary line (start of the sorted area, right side)
        if 0 < self._frontier < n:
            fx = rect.left + int(self._frontier * bar_w_f)
            pygame.draw.line(
                surface,
                _COULEUR_ALGO,
                (fx, rect.top),
                (fx, rect.bottom),
                2,
            )
            label = self._font.render("sorted area", True, _COULEUR_ALGO)
            lx = min(fx + 4, rect.right - label.get_width() - 2)
            surface.blit(label, (lx, rect.top + 4))
