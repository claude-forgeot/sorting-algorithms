"""Renderer for the insertion sort algorithm.

Visualization: vertical bars, lavender overlay on the sorted area (left),
vertical purple separator, the element being inserted highlighted in purple
and slightly elevated, shifted elements in yellow.

Events received from insertion_sort:
    compare : (j, j+1, "compare") -- j = sorted element being compared, j+1 = key position
    set     : (j, j+1, "set")    -- arr[j] shifted to arr[j+1], key moves left
    set     : (k, k,   "set")    -- key placed at its final position k
"""

import colorsys

import pygame

from visualization.renderers.base import BaseRenderer

_COULEUR_ALGO = (167, 139, 250)  # #a78bfa -- insertion purple
_COULEUR_KEY = (200, 170, 255)  # light purple -- element being inserted
_COULEUR_SHIFT = (255, 255, 0)  # yellow -- shifted elements
_COULEUR_SEP = (167, 139, 250)  # purple -- separator
_ALPHA_ZONE = 35  # transparency of the sorted area overlay

_ELEVATION_PX = 3  # pixels of elevation for the key bar


def _couleur_normale(
    idx: int,
    val: int | float,
    min_val: int | float,
    max_val: int | float,
) -> tuple[int, int, int]:
    """Base color for a non-highlighted bar.

    Neutral bluish palette to contrast with the active purple and yellow.

    Args:
        idx:     bar index (unused, kept for compatibility)
        val:     element value
        min_val: minimum value in the array
        max_val: maximum value in the array

    Returns:
        Tuple (r, g, b) with values 0-255.
    """
    t = (val - min_val) / ((max_val - min_val) or 1)
    h = 0.58 + t * 0.08  # neutral blue-indigo
    r, g, b = colorsys.hsv_to_rgb(h, 0.60, 0.72)
    return (int(r * 255), int(g * 255), int(b * 255))


class InsertionRenderer(BaseRenderer):
    """Renderer for insertion sort.

    The sorted area (left, transparent lavender) grows with each iteration
    of the outer loop. The inserted element is visible as a slightly elevated
    purple bar that slides left; elements pushed rightward are yellow.

    Deduction from events:
        compare(j, j+1) -> key at j+1, outer boundary = max(prev, j+1)
        set(j, j+1)     -> shift in progress, key moves left, j and j+1 in yellow
        set(k, k)        -> key placed at final position k
    """

    def __init__(self) -> None:
        """Initialize the renderer with boundary and key position at 0."""
        self._outer_boundary: int = 0  # outer loop index i (monotonically increasing)
        self._key_pos: int = 0  # current position of the element being inserted
        self._event_type: str = "compare"
        self._prev_highlighted: tuple[int, int, str] | None = None
        self._font: pygame.font.Font | None = None

    def draw(
        self,
        surface: pygame.Surface,
        state: dict,
        rect: pygame.Rect,
    ) -> None:
        """Draw the current insertion sort state within the rect area.

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
                # j+1 is always highlighted[1]; it starts at i at the beginning
                # of each outer iteration -> outer_boundary grows monotonically
                self._outer_boundary = max(self._outer_boundary, j_h)
                self._key_pos = j_h  # current position of the key
                self._event_type = event_type
            self._prev_highlighted = highlighted

        if done:
            self._outer_boundary = n

        # Highlighted indices
        hi_i, hi_j = -1, -1
        if highlighted is not None:
            hi_i, hi_j, _ = highlighted

        non_none: list[float] = [v for v in arr if v is not None]
        if not non_none:
            return
        min_val: float = min(non_none)
        max_val: float = max(non_none) or 1
        amplitude: float = (max_val - min_val) or 1
        bar_w_f: float = rect.width / n

        # Sorted area overlay (transparent lavender on the left)
        if self._outer_boundary > 0:
            zone_w = int(self._outer_boundary * bar_w_f)
            overlay = pygame.Surface((zone_w, rect.height), pygame.SRCALPHA)
            overlay.fill((167, 139, 250, _ALPHA_ZONE))
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

            if not done and highlighted is not None and idx == hi_j:
                if self._event_type == "compare":
                    # Element being inserted: purple + slightly elevated
                    bar = pygame.Rect(x, y - _ELEVATION_PX, w, bar_h + _ELEVATION_PX)
                    pygame.draw.rect(surface, _COULEUR_KEY, bar)
                else:
                    # Swap: shift destination -> yellow
                    bar = pygame.Rect(x, y, w, bar_h)
                    pygame.draw.rect(surface, _COULEUR_SHIFT, bar)
            elif not done and highlighted is not None and idx == hi_i:
                # Sorted element being compared or shift source -> yellow
                bar = pygame.Rect(x, y, w, bar_h)
                pygame.draw.rect(surface, _COULEUR_SHIFT, bar)
            else:
                bar = pygame.Rect(x, y, w, bar_h)
                color = _couleur_normale(idx, val, min_val, max_val)
                pygame.draw.rect(surface, color, bar)

        # Vertical purple separator (sorted area / active area boundary)
        if 0 < self._outer_boundary < n and not done:
            sx = rect.left + int(self._outer_boundary * bar_w_f)
            pygame.draw.line(
                surface,
                _COULEUR_SEP,
                (sx, rect.top),
                (sx, rect.bottom),
                2,
            )
            label = self._font.render("insertion", True, _COULEUR_SEP)
            lx = max(rect.left + 2, sx - label.get_width() - 4)
            surface.blit(label, (lx, rect.top + 4))
