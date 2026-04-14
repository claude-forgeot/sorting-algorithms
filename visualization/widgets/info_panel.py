"""Side information panel: current operation, statistics, complexity.

Displays three vertical sections in a panel ~180px wide:
  1. Current operation  -- type (comparison/swap), indices and values
  2. Statistics         -- step, total, comparisons, swaps
  3. Complexity         -- best/average/worst/space table for the active algo
"""

import pygame

from visualization.history import StepHistory
from visualization import theme


# ---------------------------------------------------------------------------
# Algorithmic complexity table
# ---------------------------------------------------------------------------

COMPLEXITES: dict[str, dict[str, str]] = {
    "bubble": {
        "meilleur": "O(n)",
        "moyen": "O(n^2)",
        "pire": "O(n^2)",
        "espace": "O(1)",
    },
    "selection": {
        "meilleur": "O(n^2)",
        "moyen": "O(n^2)",
        "pire": "O(n^2)",
        "espace": "O(1)",
    },
    "insertion": {
        "meilleur": "O(n)",
        "moyen": "O(n^2)",
        "pire": "O(n^2)",
        "espace": "O(1)",
    },
    "merge": {
        "meilleur": "O(n log n)",
        "moyen": "O(n log n)",
        "pire": "O(n log n)",
        "espace": "O(n)",
    },
    "quick": {
        "meilleur": "O(n log n)",
        "moyen": "O(n log n)",
        "pire": "O(n^2)",
        "espace": "O(log n)",
    },
    "heap": {
        "meilleur": "O(n log n)",
        "moyen": "O(n log n)",
        "pire": "O(n log n)",
        "espace": "O(1)",
    },
    "comb": {
        "meilleur": "O(n log n)",
        "moyen": "O(n^2/2^p)",
        "pire": "O(n^2)",
        "espace": "O(1)",
    },
}

# ---------------------------------------------------------------------------
# Colors
# ---------------------------------------------------------------------------

COULEUR_FOND = theme.PANNEAU
COULEUR_SEPARATEUR = (55, 55, 68)
COULEUR_TITRE = (160, 200, 255)
COULEUR_TEXTE = theme.TEXTE
COULEUR_GRIS = theme.DISCRET
COULEUR_COMPARE = theme.COMPARE
COULEUR_SWAP = theme.SWAP
COULEUR_VALEUR = (255, 220, 100)
COULEUR_OK = theme.DONE

PAD = 8


class InfoPanel:
    """Right-side information panel for the current step.

    Displays the ongoing operation (comparison or swap), cumulative statistics
    and the complexity table for the active algorithm.

    Args:
        rect:      placement rectangle (recommended width: ~180px)
        algo_name: algorithm identifier (e.g. "bubble", "merge")
        history:   optional history to compute cumulative stats
    """

    def __init__(
        self,
        rect: pygame.Rect,
        algo_name: str,
        history: StepHistory | None = None,
        scale: float = 1.0,
    ) -> None:
        self._rect = rect
        self._algo_name = algo_name
        self._history = history

        # Incremental cache: step_index -> (cumulative_comparisons, cumulative_swaps)
        # Grows to at most N entries (one per visited step).

        self._font_titre = pygame.font.SysFont(
            "monospace", theme.scaled_font(theme.F_STATS, scale), bold=True
        )
        self._font_corps = pygame.font.SysFont(
            "monospace", theme.scaled_font(theme.F_DETAIL, scale)
        )
        self._font_small = pygame.font.SysFont(
            "monospace", theme.scaled_font(theme.F_DETAIL, scale)
        )

    # ------------------------------------------------------------------ #
    # Statistics                                                            #
    # ------------------------------------------------------------------ #

    def _compter_jusqu_a(self, step_index: int) -> tuple[int, int]:
        """Count comparisons and swaps up to step_index inclusive.

        Returns:
            (comparisons, swaps) cumulated up to step_index.
        """
        if self._history is None:
            return (0, 0)

        comp, swap = 0, 0
        total_steps = len(self._history)
        for k in range(min(step_index + 1, total_steps)):
            evt = self._history.step_event(k)
            if evt == "compare":
                comp += 1
            elif evt in ("swap", "set"):
                swap += 1

        return (comp, swap)

    # ------------------------------------------------------------------ #
    # Main drawing                                                          #
    # ------------------------------------------------------------------ #

    def draw(
        self,
        surface: pygame.Surface,
        state: dict,
        step_index: int,
        total_steps: int,
    ) -> None:
        """Draws the information panel on the surface.

        Args:
            surface:     target pygame surface
            state:       current state obtained via StepHistory.get_state()
            step_index:  current step index (0-based)
            total_steps: total number of steps in the history
        """
        r = self._rect
        pygame.draw.rect(surface, COULEUR_FOND, r)
        # left border to separate from the main renderer
        pygame.draw.line(surface, COULEUR_SEPARATEUR, r.topleft, r.bottomleft, 1)

        y = r.top + PAD
        y = self._section_operation(surface, state, y)
        y = self._separateur(surface, y)
        y = self._section_stats(surface, state, step_index, total_steps, y)
        y = self._separateur(surface, y)
        self._section_complexite(surface, y)

    # ------------------------------------------------------------------ #
    # Rendering primitives                                                  #
    # ------------------------------------------------------------------ #

    def _separateur(self, surface: pygame.Surface, y: int) -> int:
        r = self._rect
        pygame.draw.line(
            surface,
            COULEUR_SEPARATEUR,
            (r.left + PAD, y + 4),
            (r.right - PAD, y + 4),
            1,
        )
        return y + 12

    def _titre_section(self, surface: pygame.Surface, texte: str, y: int) -> int:
        surf = self._font_titre.render(texte, True, COULEUR_TITRE)
        surface.blit(surf, (self._rect.left + PAD, y))
        return y + surf.get_height() + 4

    def _ligne(
        self,
        surface: pygame.Surface,
        texte: str,
        y: int,
        couleur: tuple[int, int, int] = COULEUR_TEXTE,
        indent: int = 0,
        font: pygame.font.Font | None = None,
    ) -> int:
        """Draws a line of text with automatic word wrapping.

        Args:
            indent: additional horizontal offset in px
            font:   font to use (self._font_corps by default)
        """
        police = font or self._font_corps
        x = self._rect.left + PAD + indent
        max_w = self._rect.width - 2 * PAD - indent

        # word-split with line wrap if too wide
        mots = texte.split()
        ligne_courante = ""
        for mot in mots:
            candidate = (ligne_courante + " " + mot).strip()
            if police.size(candidate)[0] <= max_w:
                ligne_courante = candidate
            else:
                if ligne_courante:
                    surf = police.render(ligne_courante, True, couleur)
                    surface.blit(surf, (x, y))
                    y += surf.get_height() + 1
                ligne_courante = mot
        if ligne_courante:
            # truncate the last word if still too wide (edge case)
            while police.size(ligne_courante)[0] > max_w and len(ligne_courante) > 1:
                ligne_courante = ligne_courante[:-1]
            surf = police.render(ligne_courante, True, couleur)
            surface.blit(surf, (x, y))
            y += surf.get_height() + 1

        return y + 2

    # ------------------------------------------------------------------ #
    # Current operation section                                             #
    # ------------------------------------------------------------------ #

    def _section_operation(self, surface: pygame.Surface, state: dict, y: int) -> int:
        y = self._titre_section(surface, "Operation", y)

        highlighted = state["highlighted"]

        if highlighted is None:
            if state["done"]:
                y = self._ligne(surface, "Sort complete.", y, COULEUR_OK)
            else:
                y = self._ligne(surface, "Waiting...", y, COULEUR_GRIS)
            return y

        i, j, event_type = highlighted
        arr = state["arr"]
        val_i = arr[i] if i < len(arr) else "?"
        val_j = arr[j] if j < len(arr) else "?"

        if event_type == "compare":
            y = self._ligne(surface, "Comparison", y, COULEUR_COMPARE)
            y = self._ligne(
                surface, f"arr[{i}] vs arr[{j}]", y, COULEUR_TEXTE, indent=6
            )
            # comparison result (only for comparable types)
            if isinstance(val_i, (int, float)) and isinstance(val_j, (int, float)):
                rel = ">" if val_i > val_j else "<" if val_i < val_j else "="
                y = self._ligne(
                    surface, f"{val_i} {rel} {val_j}", y, COULEUR_VALEUR, indent=6
                )

        elif event_type == "swap":
            y = self._ligne(surface, "Swap", y, COULEUR_SWAP)
            y = self._ligne(
                surface, f"arr[{i}] <-> arr[{j}]", y, COULEUR_TEXTE, indent=6
            )
            # display the values now in place (after the swap)
            y = self._ligne(
                surface, f"{val_i} <-> {val_j}", y, COULEUR_VALEUR, indent=6
            )

        elif event_type == "set":
            y = self._ligne(surface, "Write", y, COULEUR_SWAP)
            if i == j:
                y = self._ligne(
                    surface, f"arr[{i}] = {val_i}", y, COULEUR_TEXTE, indent=6
                )
            else:
                y = self._ligne(
                    surface, f"arr[{j}] = arr[{i}]", y, COULEUR_TEXTE, indent=6
                )

        return y

    # ------------------------------------------------------------------ #
    # Statistics section                                                    #
    # ------------------------------------------------------------------ #

    def _section_stats(
        self,
        surface: pygame.Surface,
        state: dict,
        step_index: int,
        total_steps: int,
        y: int,
    ) -> int:
        y = self._titre_section(surface, "Statistics", y)
        comp, swap = self._compter_jusqu_a(step_index)

        for texte in [
            f"Step: {step_index + 1} / {total_steps}",
            f"Comp.: {comp}",
            f"Swaps: {swap}",
        ]:
            y = self._ligne(surface, texte, y)

        return y

    # ------------------------------------------------------------------ #
    # Complexity section                                                    #
    # ------------------------------------------------------------------ #

    def _section_complexite(self, surface: pygame.Surface, y: int) -> int:
        y = self._titre_section(surface, "Complexity", y)

        complexite = COMPLEXITES.get(self._algo_name)
        if not complexite:
            y = self._ligne(surface, f"({self._algo_name})", y, COULEUR_GRIS)
            return y

        champs = [
            ("Best", "meilleur"),
            ("Average", "moyen"),
            ("Worst", "pire"),
            ("Space", "espace"),
        ]
        for label, cle in champs:
            valeur = complexite.get(cle, "?")
            y = self._ligne(
                surface,
                f"{label}: {valeur}",
                y,
                couleur=COULEUR_GRIS,
                font=self._font_small,
            )

        return y
