"""Spatial layout of rendering zones for race mode.

Provides race_layout() which distributes N algorithms in the window in an
adaptive grid where all cells have exactly the same size.
"""

import math

import pygame


# Predefined distribution by number of algorithms.
# Each entry is the list of cell counts per row (top to bottom).
_DISPOSITIONS: dict[int, list[int]] = {
    1: [1],
    2: [2],
    3: [3],
    4: [2, 2],
    5: [3, 2],
    6: [3, 3],
    7: [4, 3],
}


def race_layout(
    algo_names: list[str],
    window_rect: pygame.Rect,
) -> dict[str, pygame.Rect]:
    """Computes the grid layout for N algorithms.

    Cells are uniform: same width and same height for all algorithms
    in a single call. Incomplete rows (e.g. 3 in a 4-column grid)
    are centered horizontally.

    Edge cases:
    - 0 algorithms: returns an empty dict.
    - N > 7       : generic grid with ceil(sqrt(N)) columns.

    Args:
        algo_names:  ordered list of algorithm names to lay out
        window_rect: rectangle of the available window (or sub-zone)

    Returns:
        Dictionary {algo_name: pygame.Rect} in algo_names order.
    """
    n = len(algo_names)
    if n == 0:
        return {}

    if n == 1:
        return {algo_names[0]: window_rect.copy()}

    # retrieve or compute the row-based layout
    lignes: list[int]
    if n in _DISPOSITIONS:
        lignes = _DISPOSITIONS[n]
    else:
        # generic fallback: minimal square grid
        n_cols = math.ceil(math.sqrt(n))
        n_rows = math.ceil(n / n_cols)
        remaining = n
        lignes = []
        for _ in range(n_rows):
            dans_cette_ligne = min(n_cols, remaining)
            lignes.append(dans_cette_ligne)
            remaining -= dans_cette_ligne

    n_rows = len(lignes)
    max_cols = max(lignes)

    # all cells have exactly these dimensions
    cell_w = window_rect.width // max_cols
    cell_h = window_rect.height // n_rows

    result: dict[str, pygame.Rect] = {}
    idx = 0
    for row_idx, n_dans_ligne in enumerate(lignes):
        # horizontal offset to center incomplete rows
        x_offset = (max_cols - n_dans_ligne) * cell_w // 2
        for col_idx in range(n_dans_ligne):
            if idx >= n:
                break
            x = window_rect.left + x_offset + col_idx * cell_w
            y = window_rect.top + row_idx * cell_h
            result[algo_names[idx]] = pygame.Rect(x, y, cell_w, cell_h)
            idx += 1

    return result


def focus_layout(
    focused: str,
    others: list[str],
    window_rect: pygame.Rect,
) -> dict[str, pygame.Rect]:
    """Focus layout: one main algorithm (70%) + sidebar (30%).

    Args:
        focused:     name of the main algorithm
        others:      names of thumbnail algorithms (right sidebar)
        window_rect: available rectangle

    Returns:
        Dictionary {algo_name: pygame.Rect} for the focused algo and thumbnails.
    """
    gap = 4
    focus_w = int(window_rect.width * 0.70) - gap
    sidebar_w = window_rect.width - focus_w - gap

    result: dict[str, pygame.Rect] = {
        focused: pygame.Rect(
            window_rect.left,
            window_rect.top,
            focus_w,
            window_rect.height,
        ),
    }

    if not others:
        return result

    cell_h = window_rect.height // len(others)
    for idx, nom in enumerate(others):
        result[nom] = pygame.Rect(
            window_rect.left + focus_w + gap,
            window_rect.top + idx * cell_h,
            sidebar_w,
            cell_h,
        )

    return result
