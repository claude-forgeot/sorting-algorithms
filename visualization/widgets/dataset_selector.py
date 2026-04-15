"""Dataset selector widget (full-window modal overlay).

Displays a centered semi-transparent dialog with:
  - Tabs: Integers | Floats | With None
  - Grid of preset cards with mini bar chart visualization
  - Preview area (description + tags + max recommended N)
  - N field with warning if N exceeds the recommended max
  - Confirm / Cancel buttons

Returns (preset, n) when the user confirms, or None while the modal
is open. The is_active property becomes False after confirmation or cancellation.
"""

from __future__ import annotations

import pygame

from visualization.datasets import PRESETS_META, generate, normalize


# ---------------------------------------------------------------------------
# Preset organization by tab
# ---------------------------------------------------------------------------

ONGLETS: dict[str, list[str]] = {
    "Integers": [
        "random_int",
        "nearly_sorted",
        "reversed",
        "identical",
        "few_unique",
        "stairs",
    ],
    "Floats": ["float_01", "float_n", "float_neg"],
    "With None": ["with_none"],
}

# ---------------------------------------------------------------------------
# Colors
# ---------------------------------------------------------------------------

COULEUR_OVERLAY = (0, 0, 0, 160)  # alpha required (SRCALPHA)
COULEUR_FOND_DIALOG = (32, 32, 42)
COULEUR_FOND_SECTION = (40, 40, 52)
COULEUR_CONTOUR = (65, 65, 82)
COULEUR_ONGLET_INACTIF = (45, 45, 58)
COULEUR_ONGLET_ACTIF = (60, 100, 160)
COULEUR_CARTE = (42, 42, 55)
COULEUR_CARTE_HOVER = (55, 55, 70)
COULEUR_CARTE_SEL = (50, 80, 130)
COULEUR_TITRE = (160, 200, 255)
COULEUR_TEXTE = (210, 210, 225)
COULEUR_GRIS = (130, 130, 145)
COULEUR_WARNING = (255, 180, 60)
COULEUR_BTN_OK = (50, 120, 70)
COULEUR_BTN_OK_H = (60, 150, 85)
COULEUR_BTN_ANN = (80, 50, 50)
COULEUR_BTN_ANN_H = (100, 65, 65)
COULEUR_BARRE_MINI = (70, 130, 180)
COULEUR_BARRE_NONE = (90, 60, 90)

# ---------------------------------------------------------------------------
# Dimensions
# ---------------------------------------------------------------------------

PAD = 10
HAUTEUR_TITRE = 40
HAUTEUR_ONGLET = 32
HAUTEUR_CARTE = 90
LARGEUR_CARTE = 148
HAUTEUR_PREVIEW = 82
HAUTEUR_N = 30
HAUTEUR_BOUTON = 34
SAMPLE_N = 24  # elements in mini-visualizations (fixed)


class DatasetSelector:
    """Modal overlay for dataset selection.

    Public interface:
        draw(surface)         -> draws the modal overlay
        handle_event(event)   -> handles an event; returns (preset, n) if confirmed
        is_active (property)  -> False after confirmation or cancellation

    Args:
        window_rect: rectangle of the full window
        algo_name:   active algorithm identifier (for the N max warning)
    """

    def __init__(
        self,
        window_rect: pygame.Rect,
        algo_name: str | None = None,
        n_initial: int = 50,
        scale: float = 1.0,
    ) -> None:
        self._window_rect = window_rect
        self._algo_name = algo_name
        self._actif = True

        self._onglet_actif = "Integers"
        self._preset_selectionne = "random_int"
        self._n_str = str(max(1, n_initial))
        self._n_focus = False  # True if the N field has keyboard focus
        self._survol_carte = ""
        self._survol_btn_ok = False
        self._survol_btn_ann = False

        # Pre-compute mini-visualizations (normalized) -- once at init
        self._mini: dict[str, list[float]] = {}
        for preset in PRESETS_META:
            try:
                données = generate(preset, SAMPLE_N)
                self._mini[preset] = normalize(données)
            except Exception:
                self._mini[preset] = [0.5] * SAMPLE_N

        from visualization import theme as _th

        self._font_titre = pygame.font.SysFont(
            "monospace", _th.scaled_font(14, scale), bold=True
        )
        self._font_corps = pygame.font.SysFont("monospace", _th.scaled_font(12, scale))
        self._font_small = pygame.font.SysFont("monospace", _th.scaled_font(11, scale))
        self._font_n = pygame.font.SysFont("monospace", _th.scaled_font(13, scale))

        self._recalculer_rects()

    # ------------------------------------------------------------------ #
    # Properties                                                            #
    # ------------------------------------------------------------------ #

    @property
    def is_active(self) -> bool:
        """True if the modal is still displayed."""
        return self._actif

    @property
    def n_valeur(self) -> int:
        """Integer value of the N field (minimum 1)."""
        try:
            return max(1, int(self._n_str))
        except ValueError:
            return 1

    # ------------------------------------------------------------------ #
    # Geometry                                                              #
    # ------------------------------------------------------------------ #

    def _recalculer_rects(self) -> None:
        """Computes the dialog rectangle and all its sub-rectangles."""
        w_dial = min(self._window_rect.width - 40, 700)
        h_dial = min(self._window_rect.height - 40, 560)
        cx = self._window_rect.centerx
        cy = self._window_rect.centery
        r = pygame.Rect(cx - w_dial // 2, cy - h_dial // 2, w_dial, h_dial)
        self._rect_dialog = r

        # tabs (below the title)
        y = r.top + HAUTEUR_TITRE
        self._rect_onglets_zone = pygame.Rect(r.left, y, r.width, HAUTEUR_ONGLET)

        # card grid (height calculated to fill available space)
        y += HAUTEUR_ONGLET + PAD
        h_grille = (
            h_dial
            - HAUTEUR_TITRE
            - HAUTEUR_ONGLET
            - HAUTEUR_PREVIEW
            - HAUTEUR_N
            - HAUTEUR_BOUTON
            - 5 * PAD
        )
        self._rect_grille = pygame.Rect(r.left + PAD, y, r.width - 2 * PAD, h_grille)

        # preview area
        y += h_grille + PAD
        self._rect_preview = pygame.Rect(
            r.left + PAD, y, r.width - 2 * PAD, HAUTEUR_PREVIEW
        )

        # N field (label + input + warning on the same line)
        y += HAUTEUR_PREVIEW + PAD
        x_label = r.left + PAD
        w_label = 42
        x_input = x_label + w_label
        w_input = 78
        x_warn = x_input + w_input + PAD
        self._rect_n_label = pygame.Rect(x_label, y, w_label, HAUTEUR_N)
        self._rect_n_input = pygame.Rect(x_input, y, w_input, HAUTEUR_N)
        self._rect_n_warning = pygame.Rect(x_warn, y, r.right - x_warn - PAD, HAUTEUR_N)

        # Confirm / Cancel buttons (right-aligned)
        y += HAUTEUR_N + PAD
        larg_btn = 112
        self._rect_btn_ok = pygame.Rect(
            r.right - 2 * larg_btn - 2 * PAD, y, larg_btn, HAUTEUR_BOUTON
        )
        self._rect_btn_ann = pygame.Rect(
            r.right - larg_btn - PAD, y, larg_btn, HAUTEUR_BOUTON
        )

    def _rects_onglets(self) -> list[tuple[str, pygame.Rect]]:
        """Returns the (name, rect) list for each tab."""
        noms = list(ONGLETS.keys())
        r = self._rect_onglets_zone
        larg = r.width // len(noms)
        return [
            (nom, pygame.Rect(r.left + idx * larg, r.top, larg, r.height))
            for idx, nom in enumerate(noms)
        ]

    def _rects_cartes(self) -> list[tuple[str, pygame.Rect]]:
        """Returns the (preset, rect) list for the active tab."""
        presets = ONGLETS[self._onglet_actif]
        r = self._rect_grille
        résultat: list[tuple[str, pygame.Rect]] = []
        x, y = r.left + PAD // 2, r.top + PAD // 2

        for preset in presets:
            if x + LARGEUR_CARTE > r.right:
                x = r.left + PAD // 2
                y += HAUTEUR_CARTE + PAD
            résultat.append((preset, pygame.Rect(x, y, LARGEUR_CARTE, HAUTEUR_CARTE)))
            x += LARGEUR_CARTE + PAD

        return résultat

    # ------------------------------------------------------------------ #
    # Drawing                                                               #
    # ------------------------------------------------------------------ #

    def draw(self, surface: pygame.Surface) -> None:
        """Draws the complete modal overlay on the surface."""
        if not self._actif:
            return

        # semi-transparent background over the entire window
        overlay = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        overlay.fill(COULEUR_OVERLAY)
        surface.blit(overlay, (0, 0))

        # dialog box
        r = self._rect_dialog
        pygame.draw.rect(surface, COULEUR_FOND_DIALOG, r, border_radius=8)
        pygame.draw.rect(surface, COULEUR_CONTOUR, r, width=1, border_radius=8)

        # title
        surf = self._font_titre.render("Dataset selection", True, COULEUR_TITRE)
        surface.blit(surf, surf.get_rect(centerx=r.centerx, top=r.top + 10))

        self._dessiner_onglets(surface)
        self._dessiner_grille(surface)
        self._dessiner_preview(surface)
        self._dessiner_champ_n(surface)
        self._dessiner_boutons(surface)

    def _dessiner_onglets(self, surface: pygame.Surface) -> None:
        for nom, rect in self._rects_onglets():
            actif = nom == self._onglet_actif
            couleur = COULEUR_ONGLET_ACTIF if actif else COULEUR_ONGLET_INACTIF
            pygame.draw.rect(surface, couleur, rect, border_radius=5 if actif else 3)
            surf = self._font_corps.render(nom, True, COULEUR_TEXTE)
            surface.blit(surf, surf.get_rect(center=rect.center))

    def _dessiner_grille(self, surface: pygame.Surface) -> None:
        pygame.draw.rect(
            surface, COULEUR_FOND_SECTION, self._rect_grille, border_radius=4
        )

        for preset, rect in self._rects_cartes():
            sélectionné = preset == self._preset_selectionne
            survolé = preset == self._survol_carte
            couleur = (
                COULEUR_CARTE_SEL
                if sélectionné
                else COULEUR_CARTE_HOVER
                if survolé
                else COULEUR_CARTE
            )
            pygame.draw.rect(surface, couleur, rect, border_radius=5)
            pygame.draw.rect(surface, COULEUR_CONTOUR, rect, width=1, border_radius=5)

            self._dessiner_mini_visu(surface, preset, rect)

            # label centered at the bottom of the card
            label = PRESETS_META[preset]["label"]
            surf = self._font_small.render(label, True, COULEUR_TEXTE)
            surface.blit(
                surf, surf.get_rect(centerx=rect.centerx, bottom=rect.bottom - 5)
            )

    def _dessiner_mini_visu(
        self, surface: pygame.Surface, preset: str, carte: pygame.Rect
    ) -> None:
        """Draws a mini bar chart in the upper part of the card."""
        hauteur_visu = carte.height - 22  # leave room for the label
        zone = pygame.Rect(
            carte.left + 4,
            carte.top + 4,
            carte.width - 8,
            hauteur_visu,
        )
        valeurs = self._mini.get(preset, [])
        n = len(valeurs)
        if n == 0:
            return

        larg_barre = max(1, zone.width // n)
        for k, val in enumerate(valeurs):
            h_barre = max(1, int(val * zone.height))
            # None values are normalized to 0.0 in datasets.normalize
            couleur = COULEUR_BARRE_NONE if val == 0.0 else COULEUR_BARRE_MINI
            pygame.draw.rect(
                surface,
                couleur,
                pygame.Rect(
                    zone.left + k * larg_barre,
                    zone.bottom - h_barre,
                    max(1, larg_barre - 1),
                    h_barre,
                ),
            )

    def _dessiner_preview(self, surface: pygame.Surface) -> None:
        r = self._rect_preview
        pygame.draw.rect(surface, COULEUR_FOND_SECTION, r, border_radius=4)

        preset = self._preset_selectionne
        meta = PRESETS_META.get(preset, {})
        label = meta.get("label", preset)
        desc = meta.get("description", "")
        max_n = meta.get("max_n", 500)

        # category (tag on the right)
        catégorie = next((ong for ong, ps in ONGLETS.items() if preset in ps), "")
        tag_surf = self._font_small.render(f"[{catégorie}]", True, COULEUR_GRIS)
        surface.blit(tag_surf, (r.right - tag_surf.get_width() - PAD, r.top + 8))

        y = r.top + 8
        surf = self._font_corps.render(label, True, COULEUR_TITRE)
        surface.blit(surf, (r.left + PAD, y))
        y += surf.get_height() + 4

        surf = self._font_small.render(desc, True, COULEUR_TEXTE)
        surface.blit(surf, (r.left + PAD, y))
        y += surf.get_height() + 4

        surf = self._font_small.render(
            f"Max recommended N: {max_n}", True, COULEUR_GRIS
        )
        surface.blit(surf, (r.left + PAD, y))

    def _dessiner_champ_n(self, surface: pygame.Surface) -> None:
        # "N:" label
        surf_label = self._font_n.render("N :", True, COULEUR_TEXTE)
        surface.blit(
            surf_label,
            surf_label.get_rect(
                midleft=(self._rect_n_label.left, self._rect_n_label.centery)
            ),
        )

        # input field
        couleur_contour = COULEUR_TITRE if self._n_focus else COULEUR_CONTOUR
        pygame.draw.rect(
            surface, COULEUR_FOND_SECTION, self._rect_n_input, border_radius=4
        )
        pygame.draw.rect(
            surface, couleur_contour, self._rect_n_input, width=1, border_radius=4
        )

        # blinking cursor represented by "|"
        affichage = self._n_str + ("|" if self._n_focus else "")
        surf_val = self._font_n.render(affichage, True, COULEUR_TEXTE)
        surface.blit(
            surf_val,
            surf_val.get_rect(
                midleft=(self._rect_n_input.left + 5, self._rect_n_input.centery)
            ),
        )

        # warning if N exceeds the recommended maximum for this preset
        max_n = PRESETS_META.get(self._preset_selectionne, {}).get("max_n", 500)
        if self.n_valeur > max_n:
            surf_w = self._font_small.render(
                f"Warning: N > {max_n} (recommended limit)", True, COULEUR_WARNING
            )
            surface.blit(
                surf_w,
                surf_w.get_rect(
                    midleft=(self._rect_n_warning.left, self._rect_n_warning.centery)
                ),
            )

    def _dessiner_boutons(self, surface: pygame.Surface) -> None:
        couleur_ok = COULEUR_BTN_OK_H if self._survol_btn_ok else COULEUR_BTN_OK
        couleur_ann = COULEUR_BTN_ANN_H if self._survol_btn_ann else COULEUR_BTN_ANN

        pygame.draw.rect(surface, couleur_ok, self._rect_btn_ok, border_radius=5)
        surf = self._font_corps.render("Confirm", True, COULEUR_TEXTE)
        surface.blit(surf, surf.get_rect(center=self._rect_btn_ok.center))

        pygame.draw.rect(surface, couleur_ann, self._rect_btn_ann, border_radius=5)
        surf = self._font_corps.render("Cancel", True, COULEUR_TEXTE)
        surface.blit(surf, surf.get_rect(center=self._rect_btn_ann.center))

    # ------------------------------------------------------------------ #
    # Event handling                                                        #
    # ------------------------------------------------------------------ #

    def handle_event(self, event: pygame.event.Event) -> tuple[str, int] | None:
        """Handles a pygame event.

        Returns:
            (preset, n) if the user confirmed the selection.
            None while the modal is open or if cancelled.
            Check is_active to know whether the modal is still visible.
        """
        if not self._actif:
            return None

        if event.type == pygame.KEYDOWN:
            return self._traiter_touche(event)

        if event.type == pygame.MOUSEMOTION:
            self._mettre_a_jour_survol(event.pos)
            return None

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            return self._traiter_clic(event.pos)

        return None

    def _traiter_touche(self, event: pygame.event.Event) -> tuple[str, int] | None:
        if event.key == pygame.K_ESCAPE:
            self._actif = False
            return None

        if event.key == pygame.K_RETURN:
            return self._confirmer()

        if self._n_focus:
            if event.key == pygame.K_BACKSPACE:
                self._n_str = self._n_str[:-1]
            elif event.unicode.isdigit() and len(self._n_str) < 4:
                self._n_str += event.unicode

        return None

    def _traiter_clic(self, pos: tuple[int, int]) -> tuple[str, int] | None:
        x, y = pos

        # click outside the dialog -> close
        if not self._rect_dialog.collidepoint(x, y):
            self._actif = False
            return None

        # tabs
        for nom, rect in self._rects_onglets():
            if rect.collidepoint(x, y) and nom != self._onglet_actif:
                self._onglet_actif = nom
                presets = ONGLETS[nom]
                if presets:
                    self._preset_selectionne = presets[0]
                return None

        # preset cards
        for preset, rect in self._rects_cartes():
            if rect.collidepoint(x, y):
                self._preset_selectionne = preset
                self._n_focus = False
                return None

        # N field
        if self._rect_n_input.collidepoint(x, y):
            self._n_focus = True
            return None
        self._n_focus = False

        # Confirm button
        if self._rect_btn_ok.collidepoint(x, y):
            return self._confirmer()

        # Cancel button
        if self._rect_btn_ann.collidepoint(x, y):
            self._actif = False
            return None

        return None

    def _confirmer(self) -> tuple[str, int]:
        self._actif = False
        return (self._preset_selectionne, self.n_valeur)

    def _mettre_a_jour_survol(self, pos: tuple[int, int]) -> None:
        self._survol_btn_ok = self._rect_btn_ok.collidepoint(pos)
        self._survol_btn_ann = self._rect_btn_ann.collidepoint(pos)
        self._survol_carte = ""
        for preset, rect in self._rects_cartes():
            if rect.collidepoint(pos):
                self._survol_carte = preset
                break
