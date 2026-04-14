"""Inline sleep config widget for the race/solo hint bar.

Compact form: [checkbox enabled] [ms input] [label]. Consumes minimal
vertical space to slot into existing hint bars without layout changes.
"""

import pygame

from visualization._common import (
    DEFAULT_SLEEP_MS,
    SleepState,
    clamp_sleep_ms,
)

C_BG = (26, 26, 38)
C_BORDER = (78, 90, 120)
C_TEXT = (210, 215, 230)
C_MUTED = (130, 140, 165)
C_CHK_ON = (48, 160, 90)
C_CHK_OFF = (60, 60, 80)
C_FOCUS = (255, 215, 0)


class SleepForm:
    """Inline edit form for a SleepState.

    Usage:
        form = SleepForm(rect, state)
        form.active = True    # grab focus
        form.handle_event(ev) # returns True when validated (Enter)
        form.draw(surface)

    The form mutates the SleepState passed in place on validation.
    """

    def __init__(
        self,
        rect: pygame.Rect,
        state: SleepState | None = None,
        font: pygame.font.Font | None = None,
    ) -> None:
        self._rect = rect
        self._state = state or SleepState()
        self._font = font or pygame.font.SysFont("monospace", 12)
        self._ms_str = str(self._state.ms)
        self._enabled = self._state.enabled
        self.active = False

    @property
    def state(self) -> SleepState:
        return self._state

    def set_rect(self, rect: pygame.Rect) -> None:
        self._rect = rect

    def open(self) -> None:
        self._ms_str = str(self._state.ms)
        self._enabled = self._state.enabled
        self.active = True

    def close(self, commit: bool) -> None:
        if commit:
            self._state.enabled = self._enabled
            self._state.ms = clamp_sleep_ms(self._ms_str or DEFAULT_SLEEP_MS)
        self.active = False

    def handle_event(self, event: pygame.event.Event) -> bool:
        """Return True if form was validated (caller should apply state)."""
        if not self.active:
            return False

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.close(commit=False)
                return False
            if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                self.close(commit=True)
                return True
            if event.key == pygame.K_SPACE:
                self._enabled = not self._enabled
                return False
            if event.key == pygame.K_BACKSPACE:
                self._ms_str = self._ms_str[:-1]
                return False
            if event.unicode.isdigit() and len(self._ms_str) < 4:
                self._ms_str += event.unicode
                return False

        return False

    def draw(self, surface: pygame.Surface) -> None:
        r = self._rect
        pygame.draw.rect(surface, C_BG, r, border_radius=3)
        border_color = C_FOCUS if self.active else C_BORDER
        pygame.draw.rect(surface, border_color, r, width=1, border_radius=3)

        pad = 6
        x = r.left + pad
        cy = r.centery

        label = self._font.render("Sleep", True, C_MUTED)
        surface.blit(label, (x, cy - label.get_height() // 2))
        x += label.get_width() + pad

        chk_size = max(10, r.height - 10)
        chk_rect = pygame.Rect(x, cy - chk_size // 2, chk_size, chk_size)
        pygame.draw.rect(
            surface,
            C_CHK_ON if self._enabled else C_CHK_OFF,
            chk_rect,
            border_radius=2,
        )
        pygame.draw.rect(surface, C_BORDER, chk_rect, width=1, border_radius=2)
        if self._enabled:
            mark = self._font.render("X", True, C_TEXT)
            surface.blit(mark, mark.get_rect(center=chk_rect.center))
        x = chk_rect.right + pad

        ms_display = self._ms_str + ("|" if self.active else "")
        ms_surf = self._font.render(f"{ms_display} ms", True, C_TEXT)
        surface.blit(ms_surf, (x, cy - ms_surf.get_height() // 2))
