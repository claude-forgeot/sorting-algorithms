"""Tests for visualization.layout -- pure geometry, no rendering."""

import pygame
from visualization.layout import race_layout, focus_layout


WINDOW = pygame.Rect(0, 0, 1200, 800)


def _uniform(rects):
    """All rects have the same width and height."""
    ws = {r.width for r in rects}
    hs = {r.height for r in rects}
    return len(ws) == 1 and len(hs) == 1


def test_race_empty_returns_empty_dict():
    assert race_layout([], WINDOW) == {}


def test_race_single_takes_full_window():
    layout = race_layout(["bubble"], WINDOW)
    assert layout["bubble"] == WINDOW


def test_race_two_algos_side_by_side_uniform():
    layout = race_layout(["a", "b"], WINDOW)
    assert set(layout.keys()) == {"a", "b"}
    assert _uniform(layout.values())
    # side by side -> same y, different x
    assert layout["a"].y == layout["b"].y
    assert layout["a"].x != layout["b"].x


def test_race_three_algos_single_row():
    layout = race_layout(["a", "b", "c"], WINDOW)
    assert _uniform(layout.values())
    ys = {r.y for r in layout.values()}
    assert len(ys) == 1  # same row
    assert all(r.width == WINDOW.width // 3 for r in layout.values())


def test_race_four_algos_two_by_two():
    layout = race_layout(["a", "b", "c", "d"], WINDOW)
    assert _uniform(layout.values())
    ys = sorted({r.y for r in layout.values()})
    assert len(ys) == 2


def test_race_five_algos_has_centered_second_row():
    layout = race_layout(["a", "b", "c", "d", "e"], WINDOW)
    assert _uniform(layout.values())
    # row 1 has 3, row 2 has 2 -- row 2 should be horizontally centered
    cell_w = WINDOW.width // 3
    row1_xs = sorted(layout[k].x for k in ("a", "b", "c"))
    row2_xs = sorted(layout[k].x for k in ("d", "e"))
    assert row1_xs == [0, cell_w, 2 * cell_w]
    # row 2 centered: starts at cell_w/2
    assert row2_xs[0] == cell_w // 2


def test_race_six_algos_two_rows_of_three():
    layout = race_layout(["a", "b", "c", "d", "e", "f"], WINDOW)
    assert _uniform(layout.values())
    ys = sorted({r.y for r in layout.values()})
    assert len(ys) == 2


def test_race_seven_algos_four_plus_three():
    layout = race_layout(["a", "b", "c", "d", "e", "f", "g"], WINDOW)
    assert _uniform(layout.values())
    assert len(layout) == 7


def test_race_eight_algos_generic_fallback():
    names = list("abcdefgh")
    layout = race_layout(names, WINDOW)
    assert len(layout) == 8
    assert _uniform(layout.values())


def test_race_cells_fit_inside_window():
    for n in range(1, 12):
        names = [f"a{i}" for i in range(n)]
        layout = race_layout(names, WINDOW)
        for r in layout.values():
            assert r.left >= WINDOW.left
            assert r.top >= WINDOW.top
            assert r.right <= WINDOW.right + 1  # rounding tolerance
            assert r.bottom <= WINDOW.bottom + 1


def test_race_preserves_order_of_names():
    names = ["bubble", "merge", "quick"]
    layout = race_layout(names, WINDOW)
    assert list(layout.keys()) == names


def test_race_with_offset_window():
    offset = pygame.Rect(100, 50, 600, 400)
    layout = race_layout(["a", "b"], offset)
    for r in layout.values():
        assert r.left >= offset.left
        assert r.top >= offset.top


def test_focus_no_others_uses_full_width_minus_sidebar():
    layout = focus_layout("bubble", [], WINDOW)
    assert list(layout.keys()) == ["bubble"]
    focus_w = int(WINDOW.width * 0.70) - 4
    assert layout["bubble"].width == focus_w
    assert layout["bubble"].height == WINDOW.height


def test_focus_with_thumbnails_stacked_vertically():
    layout = focus_layout("bubble", ["merge", "quick", "heap"], WINDOW)
    assert set(layout.keys()) == {"bubble", "merge", "quick", "heap"}
    thumbs = [layout[n] for n in ("merge", "quick", "heap")]
    # all thumbnails share the same x and width
    assert len({t.x for t in thumbs}) == 1
    assert len({t.width for t in thumbs}) == 1
    # stacked: y increases
    ys = [t.y for t in thumbs]
    assert ys == sorted(ys)
    assert ys[0] < ys[1] < ys[2]


def test_focus_main_larger_than_thumbnails():
    layout = focus_layout("bubble", ["merge"], WINDOW)
    assert layout["bubble"].width > layout["merge"].width


def test_focus_thumbnails_right_of_focused():
    layout = focus_layout("bubble", ["merge"], WINDOW)
    assert layout["merge"].left >= layout["bubble"].right
