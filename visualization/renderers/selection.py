"""Renderer for the selection sort algorithm.

Visualization: vertical bars, transparent green overlay on the sorted area
(left), orange line marking the scanner, bright orange bar for the current
minimum, red flash during the final swap.

Events received from selection_sort:
    compare : (j, min_idx, "compare") -- j = scanner, min_idx = minimum candidate
    swap    : (i, min_idx, "swap")    -- i = target position (boundary), min_idx = source
"""

import colorsys

import pygame

from visualization.renderers.base import BaseRenderer

_COULEUR_ALGO = (255, 107, 53)  # #ff6b35 -- selection orange
_COULEUR_MIN = (255, 160, 40)  # bright orange -- current minimum
_COULEUR_SCANNER = (255, 107, 53)  # orange -- scanner line
_COULEUR_COMPARE = (255, 255, 0)  # yellow -- comparison
_COULEUR_SWAP = (255, 50, 50)  # red -- final swap
_ALPHA_ZONE = 45  # transparency of the sorted area overlay


def _couleur_normale(
    idx: int,
    val: int | float,
    min_val: int | float,
    max_val: int | float,
) -> tuple[int, int, int]:
    """Base color for a non-highlighted bar.

    Uses a cool HSV hue (blue-cyan) for the neutral background, leaving
    warm colors (orange, red) for active elements.

    Args:
        idx:     bar index (unused, kept for compatibility)
        val:     element value
        min_val: minimum value in the array
        max_val: maximum value in the array

    Returns:
        Tuple (r, g, b) with values 0-255.
    """
    t = (val - min_val) / ((max_val - min_val) or 1)
    h = 0.55 + t * 0.10  # cool blue to cyan
    r, g, b = colorsys.hsv_to_rgb(h, 0.70, 0.75)
    return (int(r * 255), int(g * 255), int(b * 255))


class SelectionRenderer(BaseRenderer):
    """Renderer for selection sort.

    The sorted area (left) grows by one slot with each swap.
    The scanner traverses the unsorted area from left to right.
    The current minimum is highlighted in bright orange.

    Deduction from events:
        compare(j, min_idx) -> scanner = j, min candidate = min_idx
        swap(i, min_idx)    -> boundary advances to i+1, min placed at i
    """

    def __init__(self) -> None:
        """Initialize the renderer with boundary and scanner at 0."""
        self._sorted_boundary: int = (
            0  # number of definitively sorted elements on the left
        )
        self._scanner: int = 0  # current scanner index
        self._min_candidate: int = 0  # current minimum index
        self._prev_highlighted: tuple[int, int, str] | None = None
        self._font: pygame.font.Font | None = None

    def draw(
        self,
        surface: pygame.Surface,
        state: dict,
        rect: pygame.Rect,
    ) -> None:
        """Draw the current selection sort state within the rect area.

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

        if self._font is None:
            self._font = pygame.font.SysFont("monospace", 12)

        # Update internal state when highlighted changes
        if highlighted != self._prev_highlighted:
            if highlighted is not None:
                i_h, j_h, event_type = highlighted
                if event_type == "compare":
                    # j = scanner (advances from i+1 to n-1), min_idx = candidate
                    self._scanner = i_h
                    self._min_candidate = j_h
                else:
                    # swap(i, min_idx): i becomes the next boundary
                    self._sorted_boundary = i_h + 1
                    self._min_candidate = i_h  # min placed at its final position
                    self._scanner = i_h
            self._prev_highlighted = highlighted

        if done:
            self._sorted_boundary = n

        # Colors for highlighted bars
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

        # Sorted area overlay (transparent green on the left)
        if self._sorted_boundary > 0:
            zone_w = int(self._sorted_boundary * bar_w_f)
            overlay = pygame.Surface((zone_w, rect.height), pygame.SRCALPHA)
            overlay.fill((0, 200, 80, _ALPHA_ZONE))
            surface.blit(overlay, (rect.left, rect.top))

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

            if highlighted is not None and idx in (hi_i, hi_j):
                color: tuple[int, int, int] = hi_color
            elif idx == self._min_candidate and not done:
                color = _COULEUR_MIN
            else:
                color = _couleur_normale(idx, val, min_val, max_val)

            pygame.draw.rect(surface, color, bar)

        # Vertical scanner line (orange, unsorted area)
        if not done and self._sorted_boundary < n:
            sx = rect.left + int(self._scanner * bar_w_f + bar_w_f / 2)
            pygame.draw.line(
                surface,
                _COULEUR_SCANNER,
                (sx, rect.top),
                (sx, rect.bottom),
                2,
            )
