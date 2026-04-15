"""Abstract base class shared by all sorting renderers.

A renderer receives a state (arr + highlights + done) and a rectangular
area, and is responsible for drawing it onto a pygame surface.
"""

from __future__ import annotations

import abc
from typing import Callable

import pygame

from visualization import theme


# Colors for highlighted indices (from the central theme)
_COULEUR_COMPARE: tuple[int, int, int] = theme.COMPARE  # orange -- comparison
_COULEUR_SWAP: tuple[int, int, int] = theme.SWAP  # crimson-red -- swap


class BaseRenderer(abc.ABC):
    """Abstract renderer for sorting algorithm visualization.

    Subclass and implement :meth:`draw` to obtain a concrete renderer
    (bars, polar circle, dots, etc.).

    Expected state::

        state = {
            "arr":         list[int | float],          # current array
            "highlighted": tuple[int, int, str] | None,# (i, j, event_type)
            "done":        bool,                       # sort complete
        }
    """

    @abc.abstractmethod
    def draw(
        self,
        surface: pygame.Surface,
        state: dict,
        rect: pygame.Rect,
    ) -> None:
        """Draw the current sort state within the rect area.

        Args:
            surface: destination pygame surface
            state:   dictionary {"arr", "highlighted", "done"}
            rect:    drawing area assigned to this renderer
        """

    # ------------------------------------------------------------------ #
    # Utility methods reusable by subclasses                               #
    # ------------------------------------------------------------------ #

    @staticmethod
    def draw_bars(
        surface: pygame.Surface,
        arr: list[int | float],
        highlighted: tuple[int, int, str] | None,
        rect: pygame.Rect,
        color_fn: Callable[
            [int, int | float, int | float, int | float],
            tuple[int, int, int],
        ],
    ) -> None:
        """Draw the array bars with highlighted active indices.

        Indices i and j from highlighted receive a fixed color
        (yellow for compare, red for swap); all others call
        color_fn to determine their color.

        Args:
            surface:    destination pygame surface
            arr:        array to visualize
            highlighted:(i, j, event_type) or None
            rect:       display area
            color_fn:   callable(idx, val, min_val, max_val) -> (r, g, b)
                        called for each non-highlighted bar
        """
        n = len(arr)
        if n == 0:
            return

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

        # Determine highlighted indices and color
        hi_indices: frozenset[int] = frozenset()
        hi_color: tuple[int, int, int] = _COULEUR_COMPARE
        if highlighted is not None:
            i_hi, j_hi, event_type = highlighted
            hi_indices = frozenset({i_hi, j_hi})
            hi_color = _COULEUR_COMPARE if event_type == "compare" else _COULEUR_SWAP

        for idx, val in enumerate(arr):
            if val is None:
                continue  # empty bar for None values
            bar_h = max(1, int(rect.height * (val - min_val) / amplitude))
            x = rect.left + int(idx * bar_w_f)
            y = rect.bottom - bar_h
            w = max(1, int((idx + 1) * bar_w_f) - int(idx * bar_w_f))
            bar = pygame.Rect(x, y, w, bar_h)

            color = (
                hi_color if idx in hi_indices else color_fn(idx, val, min_val, max_val)
            )
            pygame.draw.rect(surface, color, bar)
