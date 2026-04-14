"""Single source of truth for colors and font sizes.

Import this module in every visualization/ file:
    from visualization import theme

All color constants are centralized here. The palette follows a
"Data Science Vivant" direction: indigo background, carmine-red accent,
orange for comparisons, green for sorted elements.
"""

# ---------------------------------------------------------------------------
# Background and surfaces
# ---------------------------------------------------------------------------

FOND = (26, 26, 46)  # #1a1a2e — main background (night indigo)
PANNEAU = (22, 33, 62)  # #16213e — side panels
SURFACE = (15, 52, 96)  # #0f3460 — raised elements / hover

# ---------------------------------------------------------------------------
# Semantic colors (shared across all renderers)
# ---------------------------------------------------------------------------

COMPARE = (246, 166, 35)  # #f6a623 — comparison (orange)
SWAP = (233, 69, 96)  # #e94560 — swap (carmine red) + UI accent
DONE = (104, 211, 145)  # #68d391 — sorted element / success (green)

# ---------------------------------------------------------------------------
# Text
# ---------------------------------------------------------------------------

TEXTE = (226, 232, 240)  # #e2e8f0 — primary text
SOUS = (160, 174, 192)  # #a0aec0 — secondary text
DISCRET = (113, 128, 150)  # #718096 — hint / subtle text

# ---------------------------------------------------------------------------
# Font sizes (readable on laptop + projector simultaneously)
# ---------------------------------------------------------------------------

F_STATS = 14  # stats and labels
F_DETAIL = 12  # complexity info, secondary text
F_HINT = 14  # keyboard hint bar

# ---------------------------------------------------------------------------
# Responsive scaling
# ---------------------------------------------------------------------------

REF_H = 700  # reference height (original solo mode size)


def scale_factor(window_h: int) -> float:
    """Scale factor based on window height."""
    return window_h / REF_H


def scaled_font(base_size: int, scale: float) -> int:
    """Scaled font size, minimum 8 px."""
    return max(8, round(base_size * scale))
