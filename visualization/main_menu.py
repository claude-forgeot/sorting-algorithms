"""Main menu for the Papyrus de Heron visualizer.

Displays a welcome screen with:
  - Algorithm bar silhouettes as decorative background (opacity 7 %)
  - 3 clickable mode cards (Race, Solo, Benchmark)
  - A quick-config panel (dataset, N, speed, active algos, sound)
  - History of the last 4 sessions (persisted in .menu_history.json)
  - A footer with Help / About links

Public interface:
    run_main_menu(screen) -> dict

The returned dict has these keys:
    mode   str         "course" | "solo" | "benchmark"
    preset str         key from PRESETS_META (e.g. "random_int")
    n      int         array size
    speed  float       delay in seconds per step
    son    bool        enable sound (Solo mode only)
    algos  list[str]   active subset of ALGORITHMS
"""

import json
import random
import time
from pathlib import Path
import pygame

from visualization.datasets import PRESETS_META
from visualization._common import (
    DEFAULT_SLEEP_ENABLED,
    DEFAULT_SLEEP_MS,
    clamp_sleep_ms,
)
from visualization.widgets.menu_rows import (
    draw_checkbox,
    draw_cyclable_row,
    draw_history_empty_slot,
    draw_history_item,
    draw_modal,
    draw_sleep_row,
    draw_text_input_row,
    draw_toggle_row,
)
from sorting import ALGORITHMS


VERSION = "0.7.0"

# ---------------------------------------------------------------------------
# dict is a plain dict with keys:
#   "mode":   str        -- "course" | "solo" | "benchmark"
#   "preset": str        -- key from PRESETS_META
#   "n":      int        -- array size
#   "speed":  float      -- delay in seconds per step
#   "son":    bool       -- enable sound (Solo only)
#   "algos":  list[str]  -- active subset of ALGORITHMS
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# History persistence
# ---------------------------------------------------------------------------

_HISTORY_PATH = Path(__file__).parent.parent / ".menu_history.json"
_MAX_HISTORY = 4


def _lire_historique() -> list[dict]:
    """Load session history from the local JSON file."""
    if not _HISTORY_PATH.exists():
        return []
    try:
        data = json.loads(_HISTORY_PATH.read_text(encoding="utf-8"))
        if isinstance(data, list):
            return data[-_MAX_HISTORY:]
    except Exception:
        pass
    return []


def _ecrire_historique(config: dict) -> None:
    """Append an entry to the persistent history (max 4 sessions)."""
    historique = _lire_historique()
    historique.append(
        {
            "mode": config["mode"],
            "preset": config["preset"],
            "n": config["n"],
            "speed": config["speed"],
            "son": config["son"],
            "sleep_enabled": config.get("sleep_enabled", True),
            "sleep_ms": config.get("sleep_ms", 10),
            "timestamp": int(time.time()),
        }
    )
    historique = historique[-_MAX_HISTORY:]
    try:
        _HISTORY_PATH.write_text(
            json.dumps(historique, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Visual constants
# ---------------------------------------------------------------------------

PAD = 12
RADIUS = 6

# Color palette (consistent with visualization/widgets/)
C_FOND = (14, 14, 20)
C_CONTOUR = (52, 52, 70)
C_TITRE = (190, 215, 255)
C_SOUS_TITRE = (125, 140, 170)
C_TEXTE = (205, 210, 222)
C_GRIS = (95, 105, 125)
C_FOOTER_TEXTE = (60, 68, 85)
C_SEPARATEUR = (38, 38, 54)
C_BTN_PIED = (36, 40, 55)
C_BTN_PIED_H = (52, 58, 78)

# Definition of the 3 modes
_MODES: dict[str, dict] = {
    "course": {
        "label": "Race",
        "sous_titre": "All algorithms in parallel",
        "description": "Compare 7 algorithms side by side in real time.",
        "commande": "python3 main.py --race",
        "fond": (68, 16, 16),
        "fond_hover": (88, 22, 22),
        "accent": (210, 65, 65),
    },
    "solo": {
        "label": "Solo",
        "sous_titre": "Visualize one algorithm",
        "description": "Watch sorting step by step with sound and colors.",
        "commande": "python3 main.py --visual",
        "fond": (15, 50, 24),
        "fond_hover": (20, 68, 32),
        "accent": (55, 180, 85),
    },
    "benchmark": {
        "label": "Benchmark",
        "sous_titre": "Performance measurements",
        "description": "Time, comparisons and swaps on 1000 integers.",
        "commande": "python3 main.py --benchmark",
        "fond": (60, 38, 7),
        "fond_hover": (78, 50, 10),
        "accent": (210, 145, 45),
    },
}

_NIVEAUX_VITESSE: list[tuple[str, float]] = [
    ("Very slow", 0.20),
    ("Slow", 0.10),
    ("Normal", 0.05),
    ("Fast", 0.02),
    ("Very fast", 0.005),
]

_LABELS_PRESETS: list[str] = list(PRESETS_META.keys())
_NOMS_ALGOS: list[str] = list(ALGORITHMS.keys())


# ---------------------------------------------------------------------------
# Main class
# ---------------------------------------------------------------------------


class MainMenu:
    """Pygame welcome screen for Papyrus de Heron.

    Typical usage (see also run_main_menu) ::

        menu = MainMenu(screen)
        clock = pygame.time.Clock()
        while True:
            for event in pygame.event.get():
                result = menu.handle_event(event)
                if result is not None:
                    return result
            menu.draw()
            pygame.display.flip()
            clock.tick(60)

    Args:
        screen: pygame surface created by the caller.
    """

    def __init__(self, screen: pygame.Surface) -> None:
        self._screen = screen
        self._w, self._h = screen.get_size()

        # Quick-config state
        self._preset_idx: int = 0
        self._n_str: str = "64"
        self._n_focus: bool = False
        self._vitesse_idx: int = 2  # "Normal"
        self._son: bool = True
        self._sleep_enabled: bool = DEFAULT_SLEEP_ENABLED
        self._sleep_ms_str: str = str(DEFAULT_SLEEP_MS)
        self._sleep_ms_focus: bool = False
        self._algos_actifs: set[str] = set(_NOMS_ALGOS)

        # Hover states
        self._mode_survol: str | None = None
        self._survol_row: str | None = None
        self._survol_algo: str | None = None
        self._hist_survol: int = -1
        self._survol_aide: bool = False
        self._survol_apropos: bool = False

        # Modal (help / about)
        self._modal: str | None = None

        # History loaded at startup
        self._historique: list[dict] = _lire_historique()

        self._recalc_visuals()

    def _recalc_visuals(self) -> None:
        """Recompute background, fonts and layout based on current size."""
        from visualization import theme

        sc = theme.scale_factor(self._h)

        # Pre-rendered background surface (silhouettes, opacity 7 %)
        self._bg_surf = self._creer_fond_silhouette()

        # Scaled fonts
        self._f_xl = pygame.font.SysFont(
            "monospace", theme.scaled_font(26, sc), bold=True
        )
        self._f_lg = pygame.font.SysFont(
            "monospace", theme.scaled_font(18, sc), bold=True
        )
        self._f_md = pygame.font.SysFont(
            "monospace", theme.scaled_font(14, sc), bold=True
        )
        self._f_sm = pygame.font.SysFont("monospace", theme.scaled_font(13, sc))
        self._f_xs = pygame.font.SysFont("monospace", theme.scaled_font(11, sc))

        self._calculer_rects()

    def resize(self, screen: pygame.Surface) -> None:
        """Update after a window resize."""
        self._screen = screen
        self._w, self._h = screen.get_size()
        self._recalc_visuals()

    # ------------------------------------------------------------------ #
    # Silhouette background                                                #
    # ------------------------------------------------------------------ #

    def _creer_fond_silhouette(self) -> pygame.Surface:
        """Generate a surface with algo bar silhouettes (opacity 7 %).

        The surface is created once at initialization to avoid
        re-allocating every frame.
        """
        surf = pygame.Surface((self._w, self._h), pygame.SRCALPHA)
        n_bars = 70
        larg = self._w // n_bars
        alpha = 18  # 7 % of 255 ~ 18
        rng = random.Random(42)  # fixed seed: stable silhouette across sessions

        for k in range(n_bars):
            h_bar = rng.randint(self._h // 6, self._h - 15)
            pygame.draw.rect(
                surf,
                (168, 182, 215, alpha),
                pygame.Rect(k * larg + 1, self._h - h_bar, max(1, larg - 2), h_bar),
            )
        return surf

    # ------------------------------------------------------------------ #
    # Layout computation                                                   #
    # ------------------------------------------------------------------ #

    def _calculer_rects(self) -> None:
        """Compute all layout rectangles."""
        w, h = self._w, self._h

        H_HEADER = 75
        H_FOOTER = 30

        self._rect_header = pygame.Rect(0, 0, w, H_HEADER)
        self._rect_footer = pygame.Rect(0, h - H_FOOTER, w, H_FOOTER)

        zone_y = H_HEADER + PAD
        zone_h = h - H_HEADER - H_FOOTER - 2 * PAD

        # Left panel -- mode cards (53 % of width)
        W_G = int(w * 0.53)
        card_h = (zone_h - 2 * PAD) // 3

        self._rects_mode: dict[str, pygame.Rect] = {}
        for idx, mode in enumerate(["course", "solo", "benchmark"]):
            y = zone_y + idx * (card_h + PAD)
            self._rects_mode[mode] = pygame.Rect(PAD, y, W_G, card_h)

        # Right panel -- config + history
        x_d = PAD + W_G + PAD
        W_D = w - x_d - PAD
        y = zone_y

        H_ROW = 30

        # Config section title
        self._rect_conf_titre = pygame.Rect(x_d, y, W_D, 24)
        y += 24 + PAD // 2

        # Config rows (dataset, n, speed, sound)
        self._rect_row: dict[str, pygame.Rect] = {}
        for cle in ("dataset", "n", "vitesse", "son", "sleep"):
            self._rect_row[cle] = pygame.Rect(x_d, y, W_D, H_ROW)
            y += H_ROW + 4

        y += PAD // 2

        # Active algos title
        self._rect_algos_titre = pygame.Rect(x_d, y, W_D, 20)
        y += 20 + PAD // 2

        # Algo checkboxes (2 columns)
        CHK_H = 23
        CHK_W = (W_D - PAD) // 2
        self._rects_algo: dict[str, pygame.Rect] = {}
        for idx, nom in enumerate(_NOMS_ALGOS):
            col = idx % 2
            rang = idx // 2
            self._rects_algo[nom] = pygame.Rect(
                x_d + col * (CHK_W + PAD),
                y + rang * (CHK_H + 4),
                CHK_W,
                CHK_H,
            )
        n_lignes_algos = (len(_NOMS_ALGOS) + 1) // 2
        y += n_lignes_algos * (CHK_H + 4) + PAD

        # Separator
        self._y_sep = y
        y += PAD + 2

        # History title
        self._rect_hist_titre = pygame.Rect(x_d, y, W_D, 22)
        y += 22 + PAD // 2

        # History items (4 slots)
        H_HIST = 32
        self._rects_hist: list[pygame.Rect] = [
            pygame.Rect(x_d, y + k * (H_HIST + 4), W_D, H_HIST)
            for k in range(_MAX_HISTORY)
        ]
        y += _MAX_HISTORY * (H_HIST + 4) + PAD

        # Scores button (below history)
        H_BTN_SCORES = 30
        self._rect_btn_scores = pygame.Rect(x_d, y, W_D, H_BTN_SCORES)
        self._survol_scores = False

        # Footer buttons (Help, About)
        self._rect_btn_aide = pygame.Rect(w - 195, h - H_FOOTER + 4, 86, 22)
        self._rect_btn_apropos = pygame.Rect(w - 100, h - H_FOOTER + 4, 86, 22)

    # ------------------------------------------------------------------ #
    # Main drawing                                                         #
    # ------------------------------------------------------------------ #

    def draw(self) -> None:
        """Draw the full menu on self._screen."""
        s = self._screen
        s.fill(C_FOND)
        s.blit(self._bg_surf, (0, 0))

        self._dessiner_header(s)
        self._dessiner_cartes_mode(s)
        self._dessiner_panneau_droite(s)
        self._dessiner_footer(s)

        if self._modal:
            self._dessiner_modal(s)

    # ------------------------------------------------------------------ #
    # Section rendering                                                    #
    # ------------------------------------------------------------------ #

    def _dessiner_header(self, s: pygame.Surface) -> None:
        r = self._rect_header
        pygame.draw.rect(s, (16, 16, 26), r)
        pygame.draw.line(s, C_CONTOUR, (0, r.bottom - 1), (self._w, r.bottom - 1))

        titre = self._f_xl.render("Papyrus de Heron", True, C_TITRE)
        s.blit(titre, (PAD * 2, r.top + 12))

        sous = self._f_xs.render(
            "Sorting algorithm visualizer  --  Python / pygame", True, C_SOUS_TITRE
        )
        s.blit(sous, (PAD * 2, r.top + 48))

        ver = self._f_xs.render(f"v{VERSION}", True, C_GRIS)
        s.blit(ver, (self._w - ver.get_width() - PAD, r.top + PAD))

    def _dessiner_cartes_mode(self, s: pygame.Surface) -> None:
        for mode, rect in self._rects_mode.items():
            self._dessiner_une_carte(s, mode, rect)

    def _dessiner_une_carte(
        self, s: pygame.Surface, mode: str, rect: pygame.Rect
    ) -> None:
        defn = _MODES[mode]
        survol = mode == self._mode_survol

        fond = defn["fond_hover"] if survol else defn["fond"]
        pygame.draw.rect(s, fond, rect, border_radius=RADIUS)
        pygame.draw.rect(
            s,
            defn["accent"] if survol else C_CONTOUR,
            rect,
            width=1,
            border_radius=RADIUS,
        )

        # Decorative mini bars on the right
        self._dessiner_mini_barres(s, rect, defn["accent"])

        x_txt = rect.left + PAD * 2

        # Mode title
        surf_t = self._f_lg.render(defn["label"], True, defn["accent"])
        s.blit(surf_t, (x_txt, rect.top + PAD))

        # Subtitle
        surf_s = self._f_sm.render(defn["sous_titre"], True, C_TEXTE)
        s.blit(surf_s, (x_txt, rect.top + PAD + surf_t.get_height() + 4))

        # Description
        surf_d = self._f_xs.render(defn["description"], True, C_GRIS)
        s.blit(
            surf_d,
            (
                x_txt,
                rect.top + PAD + surf_t.get_height() + 4 + surf_s.get_height() + 5,
            ),
        )

        # CLI command at the bottom
        surf_c = self._f_xs.render(defn["commande"], True, (72, 82, 105))
        s.blit(surf_c, (x_txt, rect.bottom - surf_c.get_height() - PAD))

        # Hover indicator (arrow)
        if survol:
            fl = self._f_md.render(">", True, defn["accent"])
            s.blit(
                fl,
                (
                    rect.right - fl.get_width() - PAD * 2,
                    rect.centery - fl.get_height() // 2,
                ),
            )

    def _dessiner_mini_barres(
        self,
        s: pygame.Surface,
        carte: pygame.Rect,
        couleur: tuple[int, int, int],
    ) -> None:
        """Draw a decorative mini bar chart in the right area of the card."""
        n_bars = 16
        w_zone = int(carte.width * 0.26)
        h_zone = carte.height - 2 * PAD
        x_zone = carte.right - w_zone - PAD
        y_zone = carte.top + PAD
        larg = w_zone // n_bars
        rng = random.Random(carte.top)  # stable seed per card

        for k in range(n_bars):
            h_b = max(4, int(rng.random() * h_zone))
            pygame.draw.rect(
                s,
                couleur,
                pygame.Rect(
                    x_zone + k * larg,
                    y_zone + h_zone - h_b,
                    max(1, larg - 1),
                    h_b,
                ),
            )

    def _dessiner_panneau_droite(self, s: pygame.Surface) -> None:
        # Semi-transparent panel background
        x_panel = self._rect_conf_titre.left - PAD
        y_panel = self._rect_conf_titre.top - PAD // 2
        w_panel = self._rect_conf_titre.width + PAD * 2
        h_panel = self._rect_footer.top - y_panel - PAD

        fond_surf = pygame.Surface((w_panel, h_panel), pygame.SRCALPHA)
        fond_surf.fill((17, 17, 28, 210))
        s.blit(fond_surf, (x_panel, y_panel))
        pygame.draw.rect(
            s,
            C_CONTOUR,
            pygame.Rect(x_panel, y_panel, w_panel, h_panel),
            width=1,
            border_radius=RADIUS,
        )

        # Config section title
        surf = self._f_md.render("Quick config", True, C_TITRE)
        s.blit(surf, (self._rect_conf_titre.left, self._rect_conf_titre.top))

        # Cyclable config rows
        self._dessiner_ligne_cyclable(
            s,
            "dataset",
            "Data",
            PRESETS_META[_LABELS_PRESETS[self._preset_idx]]["label"],
        )
        self._dessiner_ligne_n(s)
        self._dessiner_ligne_cyclable(
            s,
            "vitesse",
            "Speed",
            _NIVEAUX_VITESSE[self._vitesse_idx][0],
        )
        self._dessiner_ligne_son(s)
        self._dessiner_ligne_sleep(s)

        # Active algos title
        surf_a = self._f_xs.render("Active algos:", True, C_SOUS_TITRE)
        s.blit(surf_a, (self._rect_algos_titre.left, self._rect_algos_titre.top))

        self._dessiner_checkboxes_algos(s)

        # Separator
        pygame.draw.line(
            s,
            C_SEPARATEUR,
            (self._rect_conf_titre.left, self._y_sep),
            (self._rect_conf_titre.left + self._rect_conf_titre.width, self._y_sep),
        )

        # History title
        surf_h = self._f_md.render("Recent sessions", True, C_TITRE)
        s.blit(surf_h, (self._rect_hist_titre.left, self._rect_hist_titre.top))

        self._dessiner_historique(s)
        self._dessiner_bouton_scores(s)

    def _dessiner_bouton_scores(self, s: pygame.Surface) -> None:
        """Draw the Scores button below the history section."""
        rect = self._rect_btn_scores
        fond = C_BTN_PIED_H if self._survol_scores else C_BTN_PIED
        pygame.draw.rect(s, fond, rect, border_radius=4)
        pygame.draw.rect(s, C_CONTOUR, rect, width=1, border_radius=4)

        surf = self._f_sm.render("Scores  [S]", True, C_SOUS_TITRE)
        s.blit(surf, surf.get_rect(center=rect.center))

    def _dessiner_ligne_cyclable(
        self, s: pygame.Surface, cle: str, label: str, valeur: str
    ) -> None:
        draw_cyclable_row(
            s,
            self._rect_row[cle],
            label,
            valeur,
            hovered=(cle == self._survol_row),
            font_label=self._f_xs,
            font_value=self._f_sm,
        )

    def _dessiner_ligne_n(self, s: pygame.Surface) -> None:
        draw_text_input_row(
            s,
            self._rect_row["n"],
            "N",
            self._n_str,
            focused=self._n_focus,
            hovered=(self._survol_row == "n"),
            font_label=self._f_xs,
            font_value=self._f_sm,
        )

    def _dessiner_ligne_son(self, s: pygame.Surface) -> None:
        draw_toggle_row(
            s,
            self._rect_row["son"],
            "Sound",
            self._son,
            hovered=(self._survol_row == "son"),
            font_label=self._f_xs,
        )

    def _dessiner_ligne_sleep(self, s: pygame.Surface) -> None:
        draw_sleep_row(
            s,
            self._rect_row["sleep"],
            self._sleep_enabled,
            self._sleep_ms_str,
            focused=self._sleep_ms_focus,
            hovered=(self._survol_row == "sleep"),
            font_label=self._f_xs,
            font_value=self._f_sm,
        )

    def _dessiner_checkboxes_algos(self, s: pygame.Surface) -> None:
        for nom, rect in self._rects_algo.items():
            draw_checkbox(
                s,
                rect,
                nom,
                checked=(nom in self._algos_actifs),
                hovered=(nom == self._survol_algo),
                font_label=self._f_xs,
            )

    def _dessiner_historique(self, s: pygame.Surface) -> None:
        for k, rect in enumerate(self._rects_hist):
            if k < len(self._historique):
                draw_history_item(
                    s,
                    rect,
                    self._historique[-(k + 1)],
                    hovered=(k == self._hist_survol),
                    font_label=self._f_xs,
                    presets_meta=PRESETS_META,
                    modes_meta=_MODES,
                )
            else:
                draw_history_empty_slot(s, rect, font_label=self._f_xs)

    def _dessiner_footer(self, s: pygame.Surface) -> None:
        r = self._rect_footer
        pygame.draw.line(s, C_CONTOUR, (0, r.top), (self._w, r.top))

        surf_v = self._f_xs.render(
            f"Papyrus de Heron v{VERSION}  --  Python / pygame",
            True,
            C_FOOTER_TEXTE,
        )
        s.blit(surf_v, (PAD, r.centery - surf_v.get_height() // 2))

        for label, rect, survol in [
            ("Help", self._rect_btn_aide, self._survol_aide),
            ("About", self._rect_btn_apropos, self._survol_apropos),
        ]:
            fond = C_BTN_PIED_H if survol else C_BTN_PIED
            pygame.draw.rect(s, fond, rect, border_radius=3)
            pygame.draw.rect(s, C_CONTOUR, rect, width=1, border_radius=3)
            surf = self._f_xs.render(label, True, C_SOUS_TITRE)
            s.blit(surf, surf.get_rect(center=rect.center))

    def _dessiner_modal(self, s: pygame.Surface) -> None:
        """Draw a semi-transparent fullscreen modal (Help or About)."""
        if self._modal == "aide":
            lignes: list[tuple[str, str]] = [
                ("titre", "Help -- Keyboard shortcuts"),
                ("vide", ""),
                ("sous", "In the menu:"),
                ("corps", "  Escape       Close this modal"),
                ("vide", ""),
                ("sous", "In Solo mode:"),
                ("corps", "  Space        Pause / Resume"),
                ("corps", "  1 2 3 4 5    Timeline speed (0.25x .. 5x)"),
                ("corps", "  R S I        Quick dataset (random/sorted/inv.)"),
                ("corps", "  D            Dataset selector"),
                ("corps", "  E            Edit sleep interval"),
                ("corps", "  F11          Toggle fullscreen"),
                ("corps", "  Q / M        Quit to menu"),
                ("vide", ""),
                ("sous", "In Race mode:"),
                ("corps", "  Space        Pause / Resume"),
                ("corps", "  + / -        Speed up / Slow down"),
                ("corps", "  S            Edit sleep interval"),
                ("corps", "  D            Dataset selector"),
                ("corps", "  TAB          Focus mode toggle"),
                ("corps", "  F11          Toggle fullscreen"),
                ("corps", "  Q / M        Quit to menu"),
            ]
        else:
            lignes = [
                ("titre", f"Papyrus de Heron  v{VERSION}"),
                ("vide", ""),
                ("sous", "School project -- Sorting algorithms"),
                ("corps", "7 algorithms: bubble, selection, insertion,"),
                ("corps", "              merge, quick, heap, comb"),
                ("vide", ""),
                ("sous", "Available modes:"),
                ("corps", "  Solo         Step-by-step visualization"),
                ("corps", "  Race         7 algorithms in parallel"),
                ("corps", "  Benchmark    Performance measurements"),
                ("vide", ""),
                ("gris", "Click or Escape to close"),
            ]

        draw_modal(
            s,
            (self._w, self._h),
            lignes,
            font_title=self._f_md,
            font_body=self._f_xs,
        )

    # ------------------------------------------------------------------ #
    # Event handling                                                       #
    # ------------------------------------------------------------------ #

    def handle_event(self, event: pygame.event.Event) -> dict | None:
        """Process a pygame event.

        Returns:
            dict if the user has selected a mode, None otherwise.
        """
        # Modal takes priority
        if self._modal:
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                self._modal = None
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                self._modal = None
            return None

        if event.type == pygame.MOUSEMOTION:
            self._maj_survol(event.pos)

        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            return self._traiter_clic(event.pos)

        elif event.type == pygame.KEYDOWN:
            return self._traiter_touche(event)

        return None

    def _maj_survol(self, pos: tuple[int, int]) -> None:
        """Update hover states based on cursor position."""
        self._mode_survol = None
        self._survol_row = None
        self._survol_algo = None
        self._hist_survol = -1
        self._survol_aide = self._rect_btn_aide.collidepoint(pos)
        self._survol_apropos = self._rect_btn_apropos.collidepoint(pos)
        self._survol_scores = self._rect_btn_scores.collidepoint(pos)

        for mode, rect in self._rects_mode.items():
            if rect.collidepoint(pos):
                self._mode_survol = mode
                return

        for cle, rect in self._rect_row.items():
            if rect.collidepoint(pos):
                self._survol_row = cle
                return

        for nom, rect in self._rects_algo.items():
            if rect.collidepoint(pos):
                self._survol_algo = nom
                return

        for k, rect in enumerate(self._rects_hist):
            if rect.collidepoint(pos):
                self._hist_survol = k
                return

    def _traiter_clic(self, pos: tuple[int, int]) -> dict | None:
        """Handle a left mouse click."""
        # Mode cards -> immediate launch
        for mode, rect in self._rects_mode.items():
            if rect.collidepoint(pos):
                return self._construire_config(mode)

        # Dataset row (left click < x center = go back, right = go forward)
        r_ds = self._rect_row["dataset"]
        if r_ds.collidepoint(pos):
            pivot = r_ds.left + 90
            if pos[0] < pivot:
                self._preset_idx = (self._preset_idx - 1) % len(_LABELS_PRESETS)
            else:
                self._preset_idx = (self._preset_idx + 1) % len(_LABELS_PRESETS)
            return None

        # N row -> activate keyboard editing
        r_n = self._rect_row["n"]
        if r_n.collidepoint(pos):
            self._n_focus = True
            return None
        self._n_focus = False

        # Speed row
        r_v = self._rect_row["vitesse"]
        if r_v.collidepoint(pos):
            pivot = r_v.left + 90
            if pos[0] < pivot:
                self._vitesse_idx = (self._vitesse_idx - 1) % len(_NIVEAUX_VITESSE)
            else:
                self._vitesse_idx = (self._vitesse_idx + 1) % len(_NIVEAUX_VITESSE)
            return None

        # Sound row -> toggle
        if self._rect_row["son"].collidepoint(pos):
            self._son = not self._son
            return None

        # Sleep row: toggle area (left ~120px) vs ms edit (rest)
        r_sleep = self._rect_row["sleep"]
        if r_sleep.collidepoint(pos):
            toggle_pivot = r_sleep.left + 120
            if pos[0] < toggle_pivot:
                self._sleep_enabled = not self._sleep_enabled
                self._sleep_ms_focus = False
            else:
                self._sleep_ms_focus = True
            return None
        self._sleep_ms_focus = False

        # Algo checkboxes
        for nom, rect in self._rects_algo.items():
            if rect.collidepoint(pos):
                if nom in self._algos_actifs:
                    # Keep at least one algo active
                    if len(self._algos_actifs) > 1:
                        self._algos_actifs.discard(nom)
                else:
                    self._algos_actifs.add(nom)
                return None

        # History items -> load and launch
        for k, rect in enumerate(self._rects_hist):
            if rect.collidepoint(pos) and k < len(self._historique):
                return self._charger_historique(self._historique[-(k + 1)])

        # Scores button
        if self._rect_btn_scores.collidepoint(pos):
            return {"mode": "scores"}

        # Footer buttons
        if self._rect_btn_aide.collidepoint(pos):
            self._modal = "aide"
        elif self._rect_btn_apropos.collidepoint(pos):
            self._modal = "apropos"

        return None

    def _traiter_touche(self, event: pygame.event.Event) -> dict | None:
        """Handle a keypress."""
        if self._n_focus:
            if event.key == pygame.K_BACKSPACE:
                self._n_str = self._n_str[:-1]
            elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                self._n_focus = False
            elif event.unicode.isdigit() and len(self._n_str) < 4:
                self._n_str += event.unicode
            return None

        if self._sleep_ms_focus:
            if event.key == pygame.K_BACKSPACE:
                self._sleep_ms_str = self._sleep_ms_str[:-1]
            elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_ESCAPE):
                self._sleep_ms_str = str(
                    clamp_sleep_ms(self._sleep_ms_str or DEFAULT_SLEEP_MS)
                )
                self._sleep_ms_focus = False
            elif event.unicode.isdigit() and len(self._sleep_ms_str) < 4:
                self._sleep_ms_str += event.unicode
            return None

        if event.key == pygame.K_ESCAPE:
            pygame.event.post(pygame.event.Event(pygame.QUIT))
            return None

        if event.key == pygame.K_s:
            return {"mode": "scores"}

        return None

    # ------------------------------------------------------------------ #
    # Config construction                                                  #
    # ------------------------------------------------------------------ #

    @property
    def _n_valeur(self) -> int:
        """Integer value of the N field (minimum 1)."""
        try:
            return max(1, int(self._n_str)) if self._n_str else 1
        except ValueError:
            return 1

    def _construire_config(self, mode: str) -> dict:
        """Build the dict from the current panel state."""
        return dict(
            mode=mode,
            preset=_LABELS_PRESETS[self._preset_idx],
            n=self._n_valeur,
            speed=_NIVEAUX_VITESSE[self._vitesse_idx][1],
            son=self._son,
            sleep_enabled=self._sleep_enabled,
            sleep_ms=clamp_sleep_ms(self._sleep_ms_str or DEFAULT_SLEEP_MS),
            algos=sorted(self._algos_actifs),
        )

    def _charger_historique(self, entree: dict) -> dict:
        """Reconstruct a dict from a history entry.

        Also synchronizes the config panel so the displayed state
        matches the loaded values.
        """
        mode = str(entree.get("mode", "solo"))
        preset = str(entree.get("preset", "random_int"))
        n = int(entree.get("n", 64))
        speed = float(entree.get("speed", 0.05))
        son = bool(entree.get("son", True))
        sleep_enabled = bool(entree.get("sleep_enabled", DEFAULT_SLEEP_ENABLED))
        sleep_ms = clamp_sleep_ms(entree.get("sleep_ms", DEFAULT_SLEEP_MS))

        # Sync panel
        if preset in _LABELS_PRESETS:
            self._preset_idx = _LABELS_PRESETS.index(preset)
        self._n_str = str(n)
        for idx, (_, s) in enumerate(_NIVEAUX_VITESSE):
            if abs(s - speed) < 1e-9:
                self._vitesse_idx = idx
                break
        self._son = son
        self._sleep_enabled = sleep_enabled
        self._sleep_ms_str = str(sleep_ms)

        return dict(
            mode=mode,
            preset=preset,
            n=max(1, n),
            speed=speed,
            son=son,
            sleep_enabled=sleep_enabled,
            sleep_ms=sleep_ms,
            algos=list(ALGORITHMS.keys()),
        )


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def run_main_menu(screen: pygame.Surface) -> dict:
    """Launch the main menu and return the chosen configuration.

    Blocks until the user selects a mode (click on a card or
    click on a history item).
    Writes the session to the JSON history before returning.

    Args:
        screen: pygame surface created by the caller (recommended size
                MENU_W x MENU_H).

    Returns:
        dict with mode, preset, n, speed, son and algos.
    """
    menu = MainMenu(screen)
    clock = pygame.time.Clock()

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                import sys

                pygame.quit()
                sys.exit(0)

            if event.type == pygame.VIDEORESIZE:
                w = max(800, event.w)
                h = max(600, event.h)
                screen = pygame.display.set_mode((w, h), pygame.RESIZABLE)
                menu.resize(screen)
                continue

            if event.type == pygame.KEYDOWN and event.key == pygame.K_F11:
                pygame.display.toggle_fullscreen()
                continue

            result = menu.handle_event(event)
            if result is not None:
                if result.get("mode") != "scores":
                    _ecrire_historique(result)
                return result

        menu.draw()
        pygame.display.flip()
        clock.tick(60)
