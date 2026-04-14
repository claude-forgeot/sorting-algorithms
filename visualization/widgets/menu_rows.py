"""Reusable row widgets for the main menu quick-config panel.

Pure rendering functions extracted from main_menu.py to keep widget
presentation isolated from MainMenu state management. Each function
takes a surface + rect + value + visual state and draws the row;
event handling stays in the caller.

The color palette is duplicated from main_menu to avoid a circular
import (main_menu imports this module). Keep values synchronized.
"""

import time

import pygame

# ---------------------------------------------------------------------------
# Color palette (keep in sync with main_menu.py)
# ---------------------------------------------------------------------------

C_CONTOUR = (52, 52, 70)
C_TITRE = (190, 215, 255)
C_SOUS_TITRE = (125, 140, 170)
C_TEXTE = (205, 210, 222)
C_GRIS = (95, 105, 125)
C_SEPARATEUR = (38, 38, 54)
C_TOGGLE_ON = (42, 115, 70)
C_TOGGLE_OFF = (48, 48, 62)
C_CHK_ON = (48, 105, 168)
C_CHK_OFF = (40, 40, 56)
C_ROW_HOVER = (34, 34, 50)
C_ROW_FOND = (20, 20, 32)
C_HIST_ITEM = (26, 26, 40)
C_HIST_HOVER = (38, 38, 56)


def draw_cyclable_row(
    surface: pygame.Surface,
    rect: pygame.Rect,
    label: str,
    value: str,
    hovered: bool,
    font_label: pygame.font.Font,
    font_value: pygame.font.Font,
) -> None:
    """Draw a config row with '<' label value '>' arrows."""
    fond = C_ROW_HOVER if hovered else C_ROW_FOND
    pygame.draw.rect(surface, fond, rect, border_radius=3)

    surf_l = font_label.render(f"{label} :", True, C_SOUS_TITRE)
    surface.blit(surf_l, (rect.left + 5, rect.centery - surf_l.get_height() // 2))

    surf_fl = font_label.render("<", True, C_GRIS)
    surface.blit(surf_fl, (rect.left + 82, rect.centery - surf_fl.get_height() // 2))

    surf_v = font_value.render(value, True, C_TEXTE)
    surface.blit(surf_v, (rect.left + 96, rect.centery - surf_v.get_height() // 2))

    surf_fr = font_label.render(">", True, C_GRIS)
    surface.blit(
        surf_fr,
        (
            rect.right - surf_fr.get_width() - 5,
            rect.centery - surf_fr.get_height() // 2,
        ),
    )


def draw_text_input_row(
    surface: pygame.Surface,
    rect: pygame.Rect,
    label: str,
    text: str,
    focused: bool,
    hovered: bool,
    font_label: pygame.font.Font,
    font_value: pygame.font.Font,
) -> None:
    """Draw a label + editable numeric field row (with blinking cursor)."""
    fond = C_ROW_HOVER if hovered else C_ROW_FOND
    pygame.draw.rect(surface, fond, rect, border_radius=3)

    if focused:
        pygame.draw.rect(surface, C_TITRE, rect, width=1, border_radius=3)

    surf_l = font_label.render(f"{label} :", True, C_SOUS_TITRE)
    surface.blit(surf_l, (rect.left + 5, rect.centery - surf_l.get_height() // 2))

    affichage = text + ("|" if focused else "")
    couleur = C_TITRE if focused else C_TEXTE
    surf_v = font_value.render(affichage, True, couleur)
    surface.blit(surf_v, (rect.left + 82, rect.centery - surf_v.get_height() // 2))


def draw_toggle_row(
    surface: pygame.Surface,
    rect: pygame.Rect,
    label: str,
    value: bool,
    hovered: bool,
    font_label: pygame.font.Font,
) -> None:
    """Draw a label + on/off toggle switch row."""
    fond = C_ROW_HOVER if hovered else C_ROW_FOND
    pygame.draw.rect(surface, fond, rect, border_radius=3)

    surf_l = font_label.render(f"{label} :", True, C_SOUS_TITRE)
    surface.blit(surf_l, (rect.left + 5, rect.centery - surf_l.get_height() // 2))

    T_W, T_H = 40, 16
    t_rect = pygame.Rect(
        rect.right - T_W - 6,
        rect.centery - T_H // 2,
        T_W,
        T_H,
    )
    pygame.draw.rect(
        surface, C_TOGGLE_ON if value else C_TOGGLE_OFF, t_rect, border_radius=8
    )
    offset = T_W - T_H - 1 if value else 1
    pygame.draw.circle(
        surface,
        (215, 215, 215),
        (t_rect.left + offset + T_H // 2, t_rect.centery),
        T_H // 2 - 2,
    )

    label_on = "ON " if value else "OFF"
    surf_s = font_label.render(label_on, True, C_TEXTE)
    surface.blit(
        surf_s,
        (
            rect.right - T_W - surf_s.get_width() - 10,
            rect.centery - surf_s.get_height() // 2,
        ),
    )


def draw_sleep_row(
    surface: pygame.Surface,
    rect: pygame.Rect,
    enabled: bool,
    ms_str: str,
    focused: bool,
    hovered: bool,
    font_label: pygame.font.Font,
    font_value: pygame.font.Font,
) -> None:
    """Draw the hybrid Sleep row: toggle on the left + editable ms value."""
    fond = C_ROW_HOVER if hovered else C_ROW_FOND
    pygame.draw.rect(surface, fond, rect, border_radius=3)

    if focused:
        pygame.draw.rect(surface, C_TITRE, rect, width=1, border_radius=3)

    surf_l = font_label.render("Sleep :", True, C_SOUS_TITRE)
    surface.blit(surf_l, (rect.left + 5, rect.centery - surf_l.get_height() // 2))

    T_W, T_H = 32, 14
    t_rect = pygame.Rect(
        rect.left + 82,
        rect.centery - T_H // 2,
        T_W,
        T_H,
    )
    pygame.draw.rect(
        surface,
        C_TOGGLE_ON if enabled else C_TOGGLE_OFF,
        t_rect,
        border_radius=7,
    )
    offset = T_W - T_H - 1 if enabled else 1
    pygame.draw.circle(
        surface,
        (215, 215, 215),
        (t_rect.left + offset + T_H // 2, t_rect.centery),
        T_H // 2 - 2,
    )

    ms_text = ms_str + ("|" if focused else "") + " ms"
    couleur = C_TITRE if focused else C_TEXTE
    surf_m = font_value.render(ms_text, True, couleur)
    surface.blit(
        surf_m,
        (
            t_rect.right + 10,
            rect.centery - surf_m.get_height() // 2,
        ),
    )


def draw_checkbox(
    surface: pygame.Surface,
    rect: pygame.Rect,
    label: str,
    checked: bool,
    hovered: bool,
    font_label: pygame.font.Font,
) -> None:
    """Draw an algorithm checkbox with label."""
    fond_chk = C_CHK_ON if checked else C_CHK_OFF
    if hovered:
        fond_chk = tuple(min(255, c + 18) for c in fond_chk)  # type: ignore[assignment]
    pygame.draw.rect(surface, fond_chk, rect, border_radius=3)
    pygame.draw.rect(surface, C_CONTOUR, rect, width=1, border_radius=3)

    if checked:
        coche = pygame.Rect(rect.left + 3, rect.top + 4, 9, 9)
        pygame.draw.rect(surface, (175, 215, 255), coche, border_radius=2)

    surf_n = font_label.render(label, True, C_TEXTE if checked else C_GRIS)
    surface.blit(surf_n, (rect.left + 18, rect.centery - surf_n.get_height() // 2))


def draw_history_item(
    surface: pygame.Surface,
    rect: pygame.Rect,
    entry: dict,
    hovered: bool,
    font_label: pygame.font.Font,
    presets_meta: dict,
    modes_meta: dict,
) -> None:
    """Draw a recent session card with mode tag, info and relative timestamp."""
    fond = C_HIST_HOVER if hovered else C_HIST_ITEM
    pygame.draw.rect(surface, fond, rect, border_radius=3)
    pygame.draw.rect(surface, C_SEPARATEUR, rect, width=1, border_radius=3)

    mode = entry.get("mode", "?")
    preset = entry.get("preset", "?")
    n = entry.get("n", "?")
    ts = entry.get("timestamp", 0)

    label_preset = presets_meta.get(preset, {}).get("label", preset)
    accent_mode = modes_meta.get(mode, {}).get("accent", C_GRIS)

    mode_label = modes_meta.get(mode, {}).get("label", mode).upper()
    surf_m = font_label.render(f"[{mode_label}]", True, accent_mode)
    surface.blit(surf_m, (rect.left + 6, rect.centery - surf_m.get_height() // 2))

    surf_i = font_label.render(f"{label_preset}  N={n}", True, C_TEXTE)
    info_x = rect.left + 6 + surf_m.get_width() + 8
    surface.blit(surf_i, (info_x, rect.centery - surf_i.get_height() // 2))

    if ts:
        delta = int(time.time()) - int(ts)
        if delta < 60:
            t_str = "just now"
        elif delta < 3600:
            t_str = f"{delta // 60} min ago"
        elif delta < 86400:
            t_str = f"{delta // 3600} h ago"
        else:
            t_str = f"{delta // 86400} d ago"
        surf_ts = font_label.render(t_str, True, C_GRIS)
        surface.blit(
            surf_ts,
            (
                rect.right - surf_ts.get_width() - 6,
                rect.centery - surf_ts.get_height() // 2,
            ),
        )


def draw_history_empty_slot(
    surface: pygame.Surface,
    rect: pygame.Rect,
    font_label: pygame.font.Font,
) -> None:
    """Draw an empty history slot placeholder."""
    pygame.draw.rect(surface, C_HIST_ITEM, rect, border_radius=3)
    pygame.draw.rect(surface, C_SEPARATEUR, rect, width=1, border_radius=3)
    surf = font_label.render("--", True, C_GRIS)
    surface.blit(surf, (rect.left + 8, rect.centery - surf.get_height() // 2))


def draw_modal(
    surface: pygame.Surface,
    window_size: tuple[int, int],
    lines: list[tuple[str, str]],
    font_title: pygame.font.Font,
    font_body: pygame.font.Font,
) -> None:
    """Draw a semi-transparent fullscreen modal with formatted lines.

    Each line is a (style, text) tuple. Valid styles:
        titre   bold header (C_TITRE)
        sous    section subtitle (C_SOUS_TITRE)
        corps   body text (C_TEXTE)
        gris    faded text (C_GRIS)
        vide    vertical spacer (text ignored)
    """
    w, h = window_size
    overlay = pygame.Surface((w, h), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 210))
    surface.blit(overlay, (0, 0))

    W_D = min(580, w - 60)
    H_D = min(380, h - 80)
    r = pygame.Rect(
        w // 2 - W_D // 2,
        h // 2 - H_D // 2,
        W_D,
        H_D,
    )
    pygame.draw.rect(surface, (24, 24, 36), r, border_radius=8)
    pygame.draw.rect(surface, C_CONTOUR, r, width=1, border_radius=8)

    y = r.top + 20
    for style, texte in lines:
        if style == "vide":
            y += 6
            continue
        if style == "titre":
            surf = font_title.render(texte, True, C_TITRE)
        elif style == "sous":
            surf = font_body.render(texte, True, C_SOUS_TITRE)
        elif style == "gris":
            surf = font_body.render(texte, True, C_GRIS)
        else:
            surf = font_body.render(texte, True, C_TEXTE)
        surface.blit(surf, (r.left + 24, y))
        y += surf.get_height() + 3
