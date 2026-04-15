"""Timeline widget for navigating through sorting history.

Horizontal strip (~60px) composed of two rows:
- Top row: draggable progress bar with yellow swap markers
- Bottom row: navigation buttons + speed selector

Keyboard shortcuts: 1-5 to change playback speed (0.25x to 5x).
"""

from __future__ import annotations

import pygame

from visualization.history import StepHistory
from visualization import theme


# ---------------------------------------------------------------------------
# Speed constants
# ---------------------------------------------------------------------------

VITESSES: list[float] = [0.25, 0.5, 1.0, 2.0, 5.0]
LABELS_VITESSE: list[str] = ["0.25x", "0.5x", "1x", "2x", "5x"]

# ---------------------------------------------------------------------------
# Colors
# ---------------------------------------------------------------------------

COULEUR_FOND = theme.PANNEAU
COULEUR_PISTE = (50, 50, 62)
COULEUR_FILL = theme.SURFACE
COULEUR_CURSEUR = theme.TEXTE
COULEUR_MARQUEUR = theme.COMPARE
COULEUR_BOUTON = (50, 50, 62)
COULEUR_BTN_HOVER = (70, 70, 88)
COULEUR_BTN_ACTIF = theme.SWAP
COULEUR_TEXTE = theme.TEXTE
COULEUR_TEXTE_GRIS = theme.DISCRET

# ---------------------------------------------------------------------------
# Dimensions
# ---------------------------------------------------------------------------

H_BARRE = 28  # height of the progress row (px)
H_BOUTONS = 32  # height of the buttons row (px)
PAD = 4  # internal spacing between elements (px)
LARGEUR_BTN_NAV = 38  # width of a navigation button (px)
LARGEUR_BTN_SPD = 42  # width of a speed button (px)


class Timeline:
    """Temporal navigation strip through sorting step history.

    Displays a draggable progress bar (with yellow markers for major swaps),
    navigation buttons and a speed selector.

    Public interface:
        draw(surface)              -> draws the widget
        handle_event(event)        -> handles a pygame event, returns current index if changed
        tick(dt_seconds)           -> advances automatically in playback mode

    Properties:
        index       : current step (int)
        en_lecture  : True if automatic playback is active (bool)
        vitesse     : current speed multiplier (float)

    Args:
        rect:    placement rectangle in the window (recommended height: 60px)
        history: step history to navigate
    """

    def __init__(
        self, rect: pygame.Rect, history: StepHistory, scale: float = 1.0
    ) -> None:
        self._rect = rect
        self._history = history

        self._index = 0  # current step (0-based)
        self._en_lecture = False  # automatic playback active
        self._vitesse_idx = 2  # index into VITESSES -> 1x by default
        self._glissement = False  # cursor currently being dragged
        self._accum_dt = 0.0  # accumulated seconds for auto-advance
        self._survol_nav = -1  # index of hovered nav button (-1 = none)
        self._survol_spd = -1  # index of hovered speed button
        self._override_interval_ms: int | None = None

        self._font = pygame.font.SysFont(
            "monospace", theme.scaled_font(theme.F_STATS, scale), bold=True
        )

        self._recalculer_rects()
        self._precomputer_marqueurs()

    # ------------------------------------------------------------------ #
    # Geometry                                                              #
    # ------------------------------------------------------------------ #

    def _recalculer_rects(self) -> None:
        """Computes all sub-rectangles from the main rect."""
        r = self._rect
        y_barre = r.top
        y_bouton = r.top + H_BARRE

        # progress bar: full width with margins
        self._rect_barre = pygame.Rect(
            r.left + PAD,
            y_barre + PAD,
            r.width - 2 * PAD,
            H_BARRE - 2 * PAD,
        )

        # 5 navigation buttons: left-aligned
        self._rects_nav: list[pygame.Rect] = []
        x = r.left + PAD
        for _ in range(5):
            self._rects_nav.append(
                pygame.Rect(x, y_bouton + PAD, LARGEUR_BTN_NAV, H_BOUTONS - 2 * PAD)
            )
            x += LARGEUR_BTN_NAV + PAD

        # speed buttons: right-aligned
        nb_spd = len(VITESSES)
        largeur_totale_spd = nb_spd * LARGEUR_BTN_SPD + (nb_spd - 1) * PAD
        self._rects_spd: list[pygame.Rect] = []
        x = r.right - largeur_totale_spd - PAD
        for _ in range(nb_spd):
            self._rects_spd.append(
                pygame.Rect(x, y_bouton + PAD, LARGEUR_BTN_SPD, H_BOUTONS - 2 * PAD)
            )
            x += LARGEUR_BTN_SPD + PAD

    def _precomputer_marqueurs(self) -> None:
        """Pre-computes normalized positions [0..1] of swaps for yellow markers.

        Uses step_event() (O(1) per call) for a global traversal in O(N).
        """
        total = len(self._history)
        self._marqueurs: list[float] = []
        if total <= 1:
            return
        dénominateur = total - 1
        for k in range(total):
            if self._history.step_event(k) in ("swap", "set"):
                self._marqueurs.append(k / dénominateur)

    # ------------------------------------------------------------------ #
    # Utilities                                                             #
    # ------------------------------------------------------------------ #

    def _total_steps(self) -> int:
        return max(1, len(self._history))

    def _index_depuis_x(self, x: int) -> int:
        """Converts an X coordinate to a step index (with clamping)."""
        b = self._rect_barre
        ratio = (x - b.left) / max(1, b.width)
        return round(max(0.0, min(1.0, ratio)) * (self._total_steps() - 1))

    def _x_depuis_index(self, index: int) -> int:
        """Converts a step index to an X coordinate on the bar."""
        b = self._rect_barre
        total = self._total_steps()
        if total <= 1:
            return b.left
        return b.left + int(index / (total - 1) * b.width)

    # ------------------------------------------------------------------ #
    # Properties                                                            #
    # ------------------------------------------------------------------ #

    @property
    def index(self) -> int:
        """Current step (0-based)."""
        return self._index

    @property
    def en_lecture(self) -> bool:
        """True if automatic playback is active."""
        return self._en_lecture

    @property
    def vitesse(self) -> float:
        """Current speed multiplier."""
        return VITESSES[self._vitesse_idx]

    def toggle_pause(self) -> None:
        """Toggles play / pause (equivalent to clicking the central button).

        Call from the main loop when the user presses Space.
        If playback resumes from the end of the history, rewinds to the start.
        """
        total = self._total_steps()
        self._en_lecture = not self._en_lecture
        if self._en_lecture and self._index >= total - 1:
            self._index = 0
        self._accum_dt = 0.0

    # ------------------------------------------------------------------ #
    # Auto-advance                                                          #
    # ------------------------------------------------------------------ #

    def tick(self, dt_secondes: float) -> int | None:
        """Advances one step if playing and enough time has elapsed.

        Call in the main loop with the clock delta time.
        Target ~60 steps/second at 1x. At 5x: ~300 steps/second.

        Args:
            dt_secondes: time elapsed since the last call (seconds)

        Returns:
            New index if the step advanced, None otherwise.
        """
        if not self._en_lecture:
            return None

        if self._override_interval_ms is not None:
            intervalle = self._override_interval_ms / 1000.0
        else:
            intervalle = (1.0 / 60.0) / self.vitesse

        if intervalle <= 0:
            total = self._total_steps()
            if self._index >= total - 1:
                self._en_lecture = False
                return None
            self._index += 1
            return self._index

        self._accum_dt += dt_secondes
        if self._accum_dt >= intervalle:
            self._accum_dt -= intervalle
            total = self._total_steps()
            if self._index >= total - 1:
                self._en_lecture = False
                return None
            self._index += 1
            return self._index

        return None

    def set_interval_ms(self, ms: int | None) -> None:
        """Override tick interval in milliseconds.

        ms=None restores the default VITESSES-based multiplier logic.
        ms=0 disables throttling (advance every frame).
        """
        self._override_interval_ms = ms
        self._accum_dt = 0.0

    # ------------------------------------------------------------------ #
    # Drawing                                                               #
    # ------------------------------------------------------------------ #

    def draw(self, surface: pygame.Surface) -> None:
        """Draws the complete timeline on the surface."""
        pygame.draw.rect(surface, COULEUR_FOND, self._rect)
        self._dessiner_barre(surface)
        self._dessiner_nav(surface)
        self._dessiner_vitesse(surface)

    def _dessiner_barre(self, surface: pygame.Surface) -> None:
        b = self._rect_barre
        total = self._total_steps()

        # background track
        pygame.draw.rect(surface, COULEUR_PISTE, b, border_radius=4)

        # completed portion
        if total > 1 and self._index > 0:
            fill_w = int(self._index / (total - 1) * b.width)
            pygame.draw.rect(
                surface,
                COULEUR_FILL,
                pygame.Rect(b.left, b.top, fill_w, b.height),
                border_radius=4,
            )

        # swap markers (yellow vertical lines)
        for pos_norm in self._marqueurs:
            mx = b.left + int(pos_norm * b.width)
            pygame.draw.line(
                surface,
                COULEUR_MARQUEUR,
                (mx, b.top + 2),
                (mx, b.bottom - 2),
                1,
            )

        # draggable cursor
        cx = self._x_depuis_index(self._index)
        pygame.draw.rect(
            surface,
            COULEUR_CURSEUR,
            pygame.Rect(cx - 4, b.top - 2, 8, b.height + 4),
            border_radius=3,
        )

    def _dessiner_nav(self, surface: pygame.Surface) -> None:
        # The central button label changes based on playback state
        labels = ["|<", "<", "||" if self._en_lecture else ">", ">", ">|"]
        for idx, (rect, label) in enumerate(zip(self._rects_nav, labels)):
            if idx == 2 and self._en_lecture:
                couleur = COULEUR_BTN_ACTIF
            elif idx == self._survol_nav:
                couleur = COULEUR_BTN_HOVER
            else:
                couleur = COULEUR_BOUTON
            pygame.draw.rect(surface, couleur, rect, border_radius=3)
            surf = self._font.render(label, True, COULEUR_TEXTE)
            surface.blit(surf, surf.get_rect(center=rect.center))

    def _dessiner_vitesse(self, surface: pygame.Surface) -> None:
        for idx, (rect, label) in enumerate(zip(self._rects_spd, LABELS_VITESSE)):
            actif = idx == self._vitesse_idx
            if actif:
                couleur = COULEUR_BTN_ACTIF
            elif idx == self._survol_spd:
                couleur = COULEUR_BTN_HOVER
            else:
                couleur = COULEUR_BOUTON
            pygame.draw.rect(surface, couleur, rect, border_radius=3)
            couleur_texte = COULEUR_TEXTE if actif else COULEUR_TEXTE_GRIS
            surf = self._font.render(label, True, couleur_texte)
            surface.blit(surf, surf.get_rect(center=rect.center))

    # ------------------------------------------------------------------ #
    # Event handling                                                        #
    # ------------------------------------------------------------------ #

    def handle_event(self, event: pygame.event.Event) -> int | None:
        """Handles a pygame event and updates the internal state.

        Args:
            event: pygame event received from the main loop

        Returns:
            Current index if the step changed as a result of this event, None otherwise.
        """
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            return self._clic_souris(event.pos)

        if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self._glissement = False
            return None

        if event.type == pygame.MOUSEMOTION:
            self._survol_nav = self._btn_nav_sous(event.pos)
            self._survol_spd = self._btn_spd_sous(event.pos)
            if self._glissement:
                nouvel = self._index_depuis_x(event.pos[0])
                if nouvel != self._index:
                    self._index = nouvel
                    return self._index
            return None

        if event.type == pygame.KEYDOWN:
            return self._traiter_touche(event.key)

        return None

    def _clic_souris(self, pos: tuple[int, int]) -> int | None:
        x, y = pos

        # click on the progress bar -> start drag
        if self._rect_barre.collidepoint(x, y):
            self._glissement = True
            self._index = self._index_depuis_x(x)
            return self._index

        # click on a navigation button
        for idx, rect in enumerate(self._rects_nav):
            if rect.collidepoint(x, y):
                return self._action_nav(idx)

        # click on a speed button
        for idx, rect in enumerate(self._rects_spd):
            if rect.collidepoint(x, y):
                self._vitesse_idx = idx
                return None

        return None

    def _action_nav(self, idx: int) -> int | None:
        """Executes the action corresponding to navigation button idx."""
        total = self._total_steps()
        if idx == 0:  # beginning
            self._index = 0
            self._en_lecture = False
        elif idx == 1:  # step back
            self._index = max(0, self._index - 1)
            self._en_lecture = False
        elif idx == 2:  # play / pause
            self._en_lecture = not self._en_lecture
            if self._en_lecture and self._index >= total - 1:
                # automatic rewind if playback resumes from the end
                self._index = 0
            self._accum_dt = 0.0
        elif idx == 3:  # step forward
            self._index = min(total - 1, self._index + 1)
            self._en_lecture = False
        elif idx == 4:  # end
            self._index = total - 1
            self._en_lecture = False
        return self._index

    def _traiter_touche(self, key: int) -> int | None:
        """Maps keys 1-5 to the speed selector."""
        touches = [pygame.K_1, pygame.K_2, pygame.K_3, pygame.K_4, pygame.K_5]
        if key in touches:
            self._vitesse_idx = touches.index(key)
        return None

    def _btn_nav_sous(self, pos: tuple[int, int]) -> int:
        for idx, rect in enumerate(self._rects_nav):
            if rect.collidepoint(pos):
                return idx
        return -1

    def _btn_spd_sous(self, pos: tuple[int, int]) -> int:
        for idx, rect in enumerate(self._rects_spd):
            if rect.collidepoint(pos):
                return idx
        return -1
