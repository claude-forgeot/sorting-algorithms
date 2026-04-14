"""Renderer for merge sort.

Displays two zones within the assigned area:

- Upper zone (75%): bars colored by sub-array being merged.
    · Remaining left sub-array  : blue   (#3b82f6)
    · Remaining right sub-array : orange (#f59e0b)
    · Already merged elements   : green  (#22c55e)
    · Outside merge zone        : dark grey
    · Direct placement (i==j)   : cyan   (#38bdf8) -- see anomaly below

- Lower zone (25%): recursive depth indicator.
    A row of dots representing recursion levels,
    with the active dot highlighted.

Identity color: #38bdf8 (sky blue).

Set events
----------
The algorithm emits ``on_step(arr, k, k, "set")`` (i == j) for all
placements (main merge and remainder loops). This renderer treats
these events as placements -- cyan color.

Bound inference
---------------
The renderer maintains internal state ``(_left, _mid, _right, _placed)``
updated on each call. Detection of a new merge relies on the
``_in_restes`` flag: once a placement ``k > mid`` is observed, the
next comparison always signals a new merge.
"""

import math

import pygame

from visualization.renderers.base import BaseRenderer

# ---------------------------------------------------------------------------
# Color constants
# ---------------------------------------------------------------------------

_BLEU: tuple[int, int, int] = (0x3B, 0x82, 0xF6)  # left sub-array
_ORANGE: tuple[int, int, int] = (0xF5, 0x9E, 0x0B)  # right sub-array
_VERT: tuple[int, int, int] = (0x22, 0xC5, 0x5E)  # already merged
_GRIS: tuple[int, int, int] = (0x1E, 0x29, 0x3B)  # outside zone
_CYAN: tuple[int, int, int] = (0x38, 0xBD, 0xF8)  # identity + placement


# ---------------------------------------------------------------------------
# Main renderer
# ---------------------------------------------------------------------------


class MergeRenderer(BaseRenderer):
    """Renderer for merge sort.

    Maintains internal state to infer the bounds ``(left, mid, right)``
    of the current merge from successive events.

    Subdivides the assigned area into two vertical parts:

    - 75% (top): bars with color code by sub-array.
    - 25% (bottom): dots representing recursion levels.
    """

    _RATIO_BARRES: float = 0.75

    def __init__(self) -> None:
        """Initializes the internal state for the current merge."""
        self._left: int = 0
        self._mid: int = -1
        self._right: int = -1
        self._placed: int = -1  # last index written in the merge
        self._last_a: int = -1  # last left pointer seen (compare)
        self._in_restes: bool = False  # True after k > mid (remainder phase)
        self._last_n: int = 0  # array size at last call

    # ------------------------------------------------------------------ #
    # BaseRenderer interface                                               #
    # ------------------------------------------------------------------ #

    def draw(
        self,
        surface: pygame.Surface,
        state: dict,
        rect: pygame.Rect,
    ) -> None:
        """Draws the current merge sort state in the rect zone.

        Args:
            surface: destination pygame surface.
            state:   dictionary ``{"arr", "highlighted", "done"}``.
            rect:    drawing zone assigned to this renderer.
        """
        arr: list[int | float] = state["arr"]
        highlighted: tuple[int, int, str] | None = state["highlighted"]
        n = len(arr)
        if n == 0:
            return

        if n != self._last_n:
            self._reset(n)

        self._update(highlighted, n)

        h_barres = int(rect.height * self._RATIO_BARRES)
        zone_barres = pygame.Rect(rect.left, rect.top, rect.width, h_barres)
        zone_dots = pygame.Rect(
            rect.left,
            rect.top + h_barres,
            rect.width,
            rect.height - h_barres,
        )

        self._dessiner_barres(surface, arr, highlighted, zone_barres)
        self._dessiner_dots(surface, n, zone_dots)

    # ------------------------------------------------------------------ #
    # Internal state management                                            #
    # ------------------------------------------------------------------ #

    def _reset(self, n: int) -> None:
        """Resets the state for a new array of size n."""
        self._left = 0
        self._mid = -1
        self._right = -1
        self._placed = -1
        self._last_a = -1
        self._in_restes = False
        self._last_n = n

    def _update(
        self,
        highlighted: tuple[int, int, str] | None,
        n: int,
    ) -> None:
        """Updates the internal state of the current merge.

        New merge detection:
        - First event ever seen (``_right == -1``).
        - We were in the remainder phase (``_in_restes == True``):
          every merge ends with at least one placement ``k > mid``,
          so the next compare always marks a new merge.

        Anomaly: ``on_step(k, k, "swap")`` may be emitted in the
        remainder loops of merge_sort. This case is treated as a
        direct placement (cyan color).
        """
        if highlighted is None:
            return

        h_i, h_j, event_type = highlighted

        if event_type == "compare" and h_i != h_j:
            a = min(h_i, h_j)
            b = max(h_i, h_j)

            is_new = (self._right == -1) or self._in_restes
            self._in_restes = False

            if is_new:
                self._left = a
                self._mid = b - 1
                half = self._mid - self._left + 1
                self._right = min(n - 1, self._left + 2 * half - 1)
                self._placed = a - 1

            self._last_a = a

        elif event_type in ("swap", "set") and h_i == h_j:
            k = h_i
            self._placed = k
            # Remainder phase: k exceeds mid -> no more comparisons
            # needed for the rest of this merge.
            if self._mid >= 0 and k > self._mid:
                self._in_restes = True

    # ------------------------------------------------------------------ #
    # Upper zone: bars                                                     #
    # ------------------------------------------------------------------ #

    def _dessiner_barres(
        self,
        surface: pygame.Surface,
        arr: list[int | float],
        highlighted: tuple[int, int, str] | None,
        rect: pygame.Rect,
    ) -> None:
        """Bars with color code by sub-array and highlighting.

        Special case: ``on_step(k, k, "swap")`` (i == j) is a direct
        placement, rendered in cyan instead of the usual red.
        """
        n = len(arr)
        if n == 0:
            return

        non_none: list[float] = [v for v in arr if v is not None]
        if not non_none:
            return
        min_val: float = float(min(non_none))
        max_val: float = float(max(non_none)) or 1.0
        amplitude: float = (max_val - min_val) or 1.0
        bar_w_f: float = rect.width / n

        # Zero reference line for data with negative values
        if min_val < 0 < max_val:
            zero_t = (0.0 - min_val) / amplitude
            zero_y = rect.bottom - int(rect.height * zero_t)
            pygame.draw.line(
                surface, (150, 150, 165), (rect.left, zero_y), (rect.right, zero_y), 1
            )

        # Highlighted indices and type
        hi_a = hi_b = -1
        est_placement = False

        if highlighted is not None:
            h_i, h_j, event_type = highlighted
            if event_type == "compare" and h_i != h_j:
                hi_a = min(h_i, h_j)
                hi_b = max(h_i, h_j)
            elif event_type in ("swap", "set") and h_i == h_j:
                hi_a = h_i
                est_placement = True
            elif event_type == "swap" and h_i != h_j:
                # Classic swap (should not occur in merge_sort)
                hi_a = h_i
                hi_b = h_j

        for idx, val in enumerate(arr):
            if val is None:
                continue  # empty bar for None values
            bar_h = max(1, int(rect.height * (val - min_val) / amplitude))
            x = rect.left + int(idx * bar_w_f)
            y = rect.bottom - bar_h
            w = max(1, int((idx + 1) * bar_w_f) - int(idx * bar_w_f))
            bar = pygame.Rect(x, y, w, bar_h)

            if est_placement and idx == hi_a:
                color = _CYAN
            elif not est_placement and idx in (hi_a, hi_b):
                color = (0xFB, 0xBF, 0x24)  # yellow -- comparison
            else:
                color = self._couleur_idx(idx)

            pygame.draw.rect(surface, color, bar)

    def _couleur_idx(self, idx: int) -> tuple[int, int, int]:
        """Zone color for an index based on its position in the merge.

        Zones (left to right in arr):
        - ``idx <= _placed``            -> green (already merged)
        - ``_placed < idx <= _mid``     -> blue (remaining left part)
        - ``_mid < idx <= _right``      -> orange (remaining right part)
        - ``idx > _right``              -> dark grey (not yet reached)

        Note: ``_placed`` is initialized to ``_left - 1`` at the start
        of a merge, which automatically colors elements from previous
        merges (indices < _left) in green.
        """
        if idx > self._right:
            return _GRIS
        if idx <= self._placed:
            return _VERT
        if idx <= self._mid:
            return _BLEU
        return _ORANGE

    # ------------------------------------------------------------------ #
    # Lower zone: recursion indicator                                      #
    # ------------------------------------------------------------------ #

    def _dessiner_dots(
        self,
        surface: pygame.Surface,
        n: int,
        zone: pygame.Rect,
    ) -> None:
        """Row of dots representing recursion levels.

        Each dot corresponds to a level (1 = pair merges,
        max = final merge of the whole array). The active dot is
        highlighted with the identity color (#38bdf8) and a halo.

        Args:
            surface: destination pygame surface.
            n:       array size (used to compute max_depth).
            zone:    rectangle assigned to the lower zone.
        """
        pygame.draw.rect(surface, (10, 15, 22), zone)

        max_depth = max(1, math.ceil(math.log2(max(n, 2))))

        # Current depth inferred from the merge window
        window = max(2, self._right - self._left + 1) if self._right > self._left else 2
        current_depth = max(1, min(max_depth, round(math.log2(window))))

        # Dot spacing
        total_dots = max_depth
        espacement_x = zone.width / (total_dots + 1)
        cy = zone.top + zone.height // 2
        r_actif = max(7, min(12, zone.height // 3))
        r_inactif = max(4, r_actif - 3)

        font: pygame.font.Font | None = None
        if zone.height >= 28 and total_dots <= 12:
            font = pygame.font.SysFont("monospace", max(8, r_actif - 2))

        for k in range(1, total_dots + 1):
            cx = int(zone.left + espacement_x * k)
            est_actif = k == current_depth

            if est_actif:
                # Halo
                r_halo = r_actif + 4
                surf_halo = pygame.Surface(
                    (r_halo * 2 + 2, r_halo * 2 + 2), pygame.SRCALPHA
                )
                pygame.draw.circle(
                    surf_halo, (*_CYAN, 60), (r_halo + 1, r_halo + 1), r_halo
                )
                surface.blit(surf_halo, (cx - r_halo - 1, cy - r_halo - 1))

                pygame.draw.circle(surface, _CYAN, (cx, cy), r_actif)
                pygame.draw.circle(surface, (255, 255, 255), (cx, cy), r_actif, 1)
            else:
                pygame.draw.circle(surface, (45, 65, 85), (cx, cy), r_inactif)

            if font is not None:
                label = font.render(
                    str(k), True, (220, 220, 220) if est_actif else (100, 120, 140)
                )
                surface.blit(
                    label,
                    (cx - label.get_width() // 2, cy - label.get_height() // 2),
                )
