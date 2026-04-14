"""Renderer for heap sort.

Displays two zones within the assigned area:

- Upper zone (60%): vertical bars whose color varies according to
  the node's level in the implicit binary heap (root = dark,
  leaves = bright amber).
- Lower zone (40%): implicit binary tree drawn with circles
  (normalized value -> dark/orange/yellow gradient) and lines.
  Active nodes (indices i or j) are highlighted with a halo.

Identity color: #f59e0b (amber).
"""

import pygame

from visualization.renderers.base import BaseRenderer

# ---------------------------------------------------------------------------
# Color constants
# ---------------------------------------------------------------------------

_AMBRE: tuple[int, int, int] = (0xF5, 0x9E, 0x0B)  # identity color
_FOND: tuple[int, int, int] = (12, 12, 18)  # tree zone background


# ---------------------------------------------------------------------------
# Color utility functions
# ---------------------------------------------------------------------------


def _lerp3(
    t: float,
    c0: tuple[int, int, int],
    c1: tuple[int, int, int],
) -> tuple[int, int, int]:
    """Linear interpolation between two RGB colors for t in [0, 1]."""
    return (
        int(c0[0] + (c1[0] - c0[0]) * t),
        int(c0[1] + (c1[1] - c0[1]) * t),
        int(c0[2] + (c1[2] - c0[2]) * t),
    )


def _couleur_niveau(t: float) -> tuple[int, int, int]:
    """Dark -> amber gradient for bars.

    Args:
        t: normalized level in the heap, 0 = root, 1 = leaves.
    """
    return _lerp3(t, (35, 22, 5), _AMBRE)


def _couleur_noeud(t: float) -> tuple[int, int, int]:
    """Dark -> orange -> yellow gradient for tree nodes.

    Args:
        t: normalized value of the element, 0 = minimum, 1 = maximum.
    """
    _ORANGE: tuple[int, int, int] = (0xF9, 0x73, 0x16)
    _JAUNE: tuple[int, int, int] = (0xFA, 0xCC, 0x15)
    if t <= 0.5:
        return _lerp3(t * 2.0, (25, 18, 40), _ORANGE)
    return _lerp3((t - 0.5) * 2.0, _ORANGE, _JAUNE)


# ---------------------------------------------------------------------------
# Node position computation
# ---------------------------------------------------------------------------


def _positions_noeuds(
    n: int,
    zone: pygame.Rect,
    max_niveaux: int | None = None,
) -> list[tuple[float, float]]:
    """Computes the (x, y) coordinates of each binary tree node.

    Node at index ``i`` is at level ``floor(log2(i+1))``.
    The root (i=0) is at the top of the rectangle.

    Args:
        n:           number of nodes to position.
        zone:        rectangle available for the tree.
        max_niveaux: if provided, limits display to the first levels
                     (nodes at higher levels receive off-screen
                     coordinates).

    Returns:
        List of ``(x, y)`` in the same order as array indices.
    """
    if n == 0:
        return []

    n_niveaux = n.bit_length()  # floor(log2(n)) + 1
    if max_niveaux is not None:
        n_niveaux = min(n_niveaux, max_niveaux)

    marge_v = zone.height * 0.10
    if n_niveaux > 1:
        h_step = (zone.height - 2.0 * marge_v) / (n_niveaux - 1)
    else:
        h_step = 0.0

    positions: list[tuple[float, float]] = []
    for idx in range(n):
        # Heap level: floor(log2(idx + 1)) for 0-indexed array
        level = (idx + 1).bit_length() - 1

        if max_niveaux is not None and level >= max_niveaux:
            positions.append((-9999.0, -9999.0))
            continue

        nodes_in_level = 1 << level  # 2^level
        pos_in_level = idx - (nodes_in_level - 1)
        cell_w = zone.width / nodes_in_level

        x = zone.left + cell_w * (pos_in_level + 0.5)
        y = zone.top + marge_v + h_step * level
        positions.append((x, y))

    return positions


# ---------------------------------------------------------------------------
# Halo drawing
# ---------------------------------------------------------------------------


def _dessiner_halo(
    surface: pygame.Surface,
    centre: tuple[int, int],
    rayon: int,
    couleur: tuple[int, int, int],
    couches: int = 3,
) -> None:
    """Draws a concentric glow halo around an active node.

    Args:
        surface:  destination pygame surface.
        centre:   (x, y) coordinates of the node center.
        rayon:    node radius (layers extend beyond it).
        couleur:  base RGB color of the halo.
        couches:  number of gradient rings.
    """
    cx, cy = centre
    for k in range(couches, 0, -1):
        r = rayon + k * 5
        alpha = int(90 * k / couches)
        surf = pygame.Surface((r * 2 + 2, r * 2 + 2), pygame.SRCALPHA)
        pygame.draw.circle(surf, (*couleur, alpha), (r + 1, r + 1), r)
        surface.blit(surf, (cx - r - 1, cy - r - 1))


# ---------------------------------------------------------------------------
# Main renderer
# ---------------------------------------------------------------------------


class HeapRenderer(BaseRenderer):
    """Renderer for heap sort.

    Subdivides the assigned area into two vertical parts:

    - 60% (top): bars colored according to each index's level
      in the implicit binary heap.
    - 40% (bottom): binary tree with circles and lines.
      Node color = normalized value (dark -> orange -> yellow).
      Active nodes highlighted with an amber halo.
    """

    _RATIO_BARRES: float = 0.60

    def draw(
        self,
        surface: pygame.Surface,
        state: dict,
        rect: pygame.Rect,
    ) -> None:
        """Draws the current heap sort state in the rect zone.

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

        h_barres = int(rect.height * self._RATIO_BARRES)
        zone_barres = pygame.Rect(rect.left, rect.top, rect.width, h_barres)
        zone_arbre = pygame.Rect(
            rect.left,
            rect.top + h_barres,
            rect.width,
            rect.height - h_barres,
        )

        self._dessiner_barres(surface, arr, highlighted, zone_barres)
        self._dessiner_arbre(surface, arr, highlighted, zone_arbre)

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
        """Bars colored according to each index's level in the heap."""
        n = len(arr)
        max_level = max(1, n.bit_length() - 1)

        def color_fn(
            idx: int,
            val: int | float,
            min_val: float,
            max_val: float,
        ) -> tuple[int, int, int]:
            # Heap level: floor(log2(idx + 1)) for 0-indexed array
            level = (idx + 1).bit_length() - 1
            t = level / max_level
            return _couleur_niveau(t)

        self.draw_bars(surface, arr, highlighted, rect, color_fn)

    # ------------------------------------------------------------------ #
    # Lower zone: implicit binary tree                                     #
    # ------------------------------------------------------------------ #

    def _dessiner_arbre(
        self,
        surface: pygame.Surface,
        arr: list[int | float],
        highlighted: tuple[int, int, str] | None,
        zone: pygame.Rect,
    ) -> None:
        """Implicit binary tree with halos on active nodes.

        In race mode (N > 64), only the first 3 levels are drawn
        to preserve readability.
        Values are displayed inside nodes if N <= 32.
        """
        n = len(arr)
        pygame.draw.rect(surface, _FOND, zone)

        max_niveaux = 3 if n > 64 else None
        n_affich = ((1 << max_niveaux) - 1) if max_niveaux else n
        n_affich = min(n, n_affich)

        if n_affich == 0:
            return

        vals_affich = arr[:n_affich]
        non_none_affich = [v for v in vals_affich if v is not None]
        if not non_none_affich:
            return
        min_val = float(min(non_none_affich))
        max_val = float(max(non_none_affich)) or 1.0

        positions = _positions_noeuds(n_affich, zone, max_niveaux)

        # Node radius: adapted to the density of the last displayed level
        dernier_niveau = max(0, (n_affich - 1).bit_length() - 1)
        noeuds_max_niveau = 1 << dernier_niveau
        rayon = max(4, min(18, zone.width // (noeuds_max_niveau * 3 + 2)))

        # Active indices (filtered to the displayed range)
        actifs: frozenset[int] = frozenset()
        if highlighted is not None:
            hi, hj, _ = highlighted
            actifs = frozenset(x for x in (hi, hj) if 0 <= x < n_affich)

        # 1. Edges (parent -> child lines)
        for idx in range(1, n_affich):
            parent = (idx - 1) // 2
            cx, cy = positions[idx]
            px, py = positions[parent]
            if cx < 0 or px < 0:
                continue
            pygame.draw.line(
                surface,
                (55, 55, 68),
                (int(px), int(py)),
                (int(cx), int(cy)),
                1,
            )

        # 2. Active node halos (before circles to stay in the background)
        for hi_idx in actifs:
            cx, cy = positions[hi_idx]
            if cx < 0:
                continue
            _dessiner_halo(surface, (int(cx), int(cy)), rayon, _AMBRE)

        # 3. Circles and values
        afficher_val = n_affich <= 32
        font: pygame.font.Font | None = None
        if afficher_val:
            taille_police = max(8, min(12, rayon - 1))
            font = pygame.font.SysFont("monospace", taille_police)

        for idx in range(n_affich):
            cx, cy = positions[idx]
            if cx < 0:
                continue

            val = arr[idx]
            if val is None:
                continue  # None node: no circle drawn
            t = (val - min_val) / (max_val - min_val) if max_val > min_val else 0.5
            couleur = _couleur_noeud(t)
            bordure = _AMBRE if idx in actifs else (68, 68, 80)

            pygame.draw.circle(surface, couleur, (int(cx), int(cy)), rayon)
            pygame.draw.circle(surface, bordure, (int(cx), int(cy)), rayon, 1)

            if afficher_val and font is not None:
                label = font.render(str(int(val)), True, (230, 230, 230))
                surface.blit(
                    label,
                    (
                        int(cx) - label.get_width() // 2,
                        int(cy) - label.get_height() // 2,
                    ),
                )
