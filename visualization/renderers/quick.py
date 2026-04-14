"""Quicksort renderer: zones colored relative to the pivot.

Identity color: #ef4444 (red).
"""

import pygame

from visualization.renderers.base import BaseRenderer


# Zone color palette
_VERT = (34, 197, 94)  # #22c55e -- elements < pivot
_ROUGE = (239, 68, 68)  # #ef4444 -- pivot (identity color)
_BLEU = (59, 130, 246)  # #3b82f6 -- elements > pivot
_GRIS = (107, 114, 128)  # #6b7280 -- unexamined elements

_LABEL_FONT_SIZE = 14
_INDICATOR_FONT_SIZE = 12
_LABEL_HEIGHT = 22  # height reserved for the bottom label row


class QuickRenderer(BaseRenderer):
    """Renderer for the quicksort algorithm.

    Displays bars in colored zones according to their value relative
    to the current pivot:

    - green : value strictly less than the pivot value
    - red   : pivot bar itself
    - blue  : value strictly greater than the pivot value
    - grey  : elements not yet examined (index > scan position)

    The pivot is inferred from state: the last index ``i`` received with
    the ``"swap"`` event is kept as the pivot position.
    A ``▲ pivot`` indicator is displayed above the pivot bar.
    """

    def __init__(self) -> None:
        self._pivot_idx: int | None = None
        self._scan_j: int | None = None  # last scan position (index j)
        self._font_lbl: pygame.font.Font | None = None
        self._font_ind: pygame.font.Font | None = None

    # ------------------------------------------------------------------ #
    # Main interface                                                       #
    # ------------------------------------------------------------------ #

    def draw(
        self,
        surface: pygame.Surface,
        state: dict,
        rect: pygame.Rect,
    ) -> None:
        """Draws the quicksort state in the rect zone.

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

        # Font initialization (lazy, once only)
        if self._font_lbl is None:
            self._font_lbl = pygame.font.SysFont("monospace", _LABEL_FONT_SIZE)
        if self._font_ind is None:
            self._font_ind = pygame.font.SysFont("monospace", _INDICATOR_FONT_SIZE)
        assert self._font_lbl is not None
        assert self._font_ind is not None

        # Update pivot and scan position
        if done:
            self._pivot_idx = None
            self._scan_j = None
        elif highlighted is not None:
            i, j, event_type = highlighted
            if event_type == "swap":
                self._pivot_idx = i
            self._scan_j = j

        # Bar zone: reserve space for labels at the bottom
        bars_rect = pygame.Rect(
            rect.left,
            rect.top,
            rect.width,
            rect.height - _LABEL_HEIGHT,
        )

        non_none_vals = [v for v in arr if v is not None]
        min_val: float = float(min(non_none_vals, default=0))
        max_val: float = float(max(non_none_vals, default=1)) or 1.0
        amplitude: float = (max_val - min_val) or 1.0
        bar_w_f: float = bars_rect.width / n

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

        pivot_val: float | None = (
            float(arr[self._pivot_idx])
            if self._pivot_idx is not None
            and 0 <= self._pivot_idx < n
            and arr[self._pivot_idx] is not None
            else None
        )

        # Draw bars + count by zone
        n_lt = n_gt = n_unexamined = 0

        for idx in range(n):
            val = arr[idx]
            if val is None:
                continue

            bar_h = max(1, int(bars_rect.height * (val - min_val) / amplitude))
            x = bars_rect.left + int(idx * bar_w_f)
            y = bars_rect.bottom - bar_h
            w = max(1, int((idx + 1) * bar_w_f) - int(idx * bar_w_f))

            color, zone = self._color_for(idx, float(val), pivot_val)
            if zone == "lt":
                n_lt += 1
            elif zone == "gt":
                n_gt += 1
            elif zone == "unexamined":
                n_unexamined += 1

            pygame.draw.rect(surface, color, pygame.Rect(x, y, w, bar_h))

        # "▲ pivot" indicator above the pivot bar
        if (
            self._pivot_idx is not None
            and 0 <= self._pivot_idx < n
            and arr[self._pivot_idx] is not None
        ):
            ind_surf = self._font_ind.render("\u25b2 pivot", True, _ROUGE)
            px = bars_rect.left + int(self._pivot_idx * bar_w_f)
            piv_bar_h = max(
                1, int(bars_rect.height * (arr[self._pivot_idx] - min_val) / amplitude)
            )
            py = bars_rect.bottom - piv_bar_h - ind_surf.get_height() - 2
            py = max(bars_rect.top, py)
            surface.blit(ind_surf, (px, py))

        # Zone labels at the bottom
        labels: list[tuple[str, tuple[int, int, int]]] = [
            (f"< pivot ({n_lt})", _VERT),
            ("pivot", _ROUGE),
            (f"> pivot ({n_gt})", _BLEU),
            (f"unexamined ({n_unexamined})", _GRIS),
        ]
        label_y = rect.bottom - _LABEL_HEIGHT + 2
        self._draw_labels_row(surface, labels, rect.left, rect.right, label_y)

    # ------------------------------------------------------------------ #
    # Private methods                                                      #
    # ------------------------------------------------------------------ #

    def _color_for(
        self,
        idx: int,
        val: float,
        pivot_val: float | None,
    ) -> tuple[tuple[int, int, int], str]:
        """Returns (color, zone) for the bar at index idx.

        Possible zones are: "pivot", "lt", "gt", "unexamined".

        Args:
            idx:       index of the bar in the array
            val:       numeric value of the bar
            pivot_val: value of the current pivot, or None if unknown

        Returns:
            Tuple (RGB color, zone identifier).
        """
        if idx == self._pivot_idx:
            return _ROUGE, "pivot"
        if pivot_val is None:
            return _GRIS, "unexamined"
        if self._scan_j is not None and idx <= self._scan_j:
            if val < pivot_val:
                return _VERT, "lt"
            if val > pivot_val:
                return _BLEU, "gt"
            # Value equal to pivot but not the pivot itself (duplicates)
            return _GRIS, "unexamined"
        return _GRIS, "unexamined"

    def _draw_labels_row(
        self,
        surface: pygame.Surface,
        labels: list[tuple[str, tuple[int, int, int]]],
        x_left: int,
        x_right: int,
        y: int,
    ) -> None:
        """Distributes labels evenly across a horizontal row.

        Args:
            surface: destination surface
            labels:  list of (text, color) pairs
            x_left:  left edge of the zone
            x_right: right edge of the zone
            y:       row ordinate
        """
        total_text_w = sum(self._font_lbl.size(t)[0] for t, _ in labels)
        zone_w = x_right - x_left
        spacing = max(4, (zone_w - total_text_w) // (len(labels) + 1))
        x = x_left + spacing
        for text, color in labels:
            surf = self._font_lbl.render(text, True, color)
            surface.blit(surf, (x, y))
            x += surf.get_width() + spacing
