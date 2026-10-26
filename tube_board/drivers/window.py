"""
A Pygame window for previewing boards.

Plain mode shows the frame as is. Dot-matrix mode scales it up and adds a
grid of unlit lamps, a round LED mask and a glow, so the 256x64 panel looks
roughly like the real thing.
"""

import os

import pygame
from PIL import Image

from .base import Driver

BACKGROUND = (7, 7, 9)
OFF_DOT = (17, 17, 20)
GLOW = (70, 70, 70)
DOT_RADIUS = 0.44  # as a fraction of the cell.


class Window(Driver):
    def __init__(
        self,
        width: int,
        height: int,
        scale: int = 1,
        title: str = "Tube Board",
        dot_matrix: bool = False,
        headless: bool = False,
    ):
        if headless:
            # Must be set before `pygame.init()`.
            os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
        pygame.init()
        self._native = (width, height)
        self._scale = scale
        self._size = (width * scale, height * scale)
        self._dot_matrix = dot_matrix
        self._screen = pygame.display.set_mode(self._size)
        pygame.display.set_caption(title)
        self._background = self._build_grid() if dot_matrix else None
        self._mask = self._build_mask() if dot_matrix else None
        self._last: Image.Image | None = None

    def _build_grid(self) -> pygame.Surface:
        """
        Black, with a faint grid of unlit lamps.
        """
        surface = pygame.Surface(self._size)
        surface.fill(BACKGROUND)
        scale = self._scale
        tile = pygame.Surface((scale, scale))
        tile.fill(BACKGROUND)
        pygame.draw.circle(
            tile, OFF_DOT, (scale / 2, scale / 2), scale * DOT_RADIUS
        )
        for x in range(0, self._size[0], scale):
            for y in range(0, self._size[1], scale):
                surface.blit(tile, (x, y))
        return surface

    def _build_mask(self) -> pygame.Surface:
        """
        Opaque black with a round transparent hole per LED cell.
        """
        scale = self._scale
        tile = pygame.Surface((scale, scale), pygame.SRCALPHA)
        tile.fill((0, 0, 0, 255))
        pygame.draw.circle(
            tile, (0, 0, 0, 0), (scale / 2, scale / 2), scale * DOT_RADIUS
        )
        mask = pygame.Surface(self._size, pygame.SRCALPHA)
        for x in range(0, self._size[0], scale):
            for y in range(0, self._size[1], scale):
                mask.blit(tile, (x, y))
        return mask

    def show(self, frame: Image.Image) -> None:
        # Boards return the same image when nothing has changed.
        if frame is self._last:
            return
        self._last = frame
        surface = pygame.image.frombuffer(frame.tobytes(), frame.size, "RGB")
        if not self._dot_matrix:
            self._screen.blit(
                pygame.transform.scale(surface, self._size)
                if self._scale != 1
                else surface,
                (0, 0),
            )
            pygame.display.flip()
            return

        crisp = pygame.transform.scale(surface, self._size)
        glow = pygame.transform.smoothscale(surface, self._size)
        glow.fill(GLOW, special_flags=pygame.BLEND_MULT)
        self._screen.blit(self._background, (0, 0))
        self._screen.blit(crisp, (0, 0), special_flags=pygame.BLEND_ADD)
        self._screen.blit(self._mask, (0, 0))
        self._screen.blit(glow, (0, 0), special_flags=pygame.BLEND_ADD)
        pygame.display.flip()

    def events(self) -> list[str]:
        out = []
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                out.append("quit")
            elif event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_q, pygame.K_ESCAPE):
                    out.append("quit")
                elif event.key == pygame.K_TAB:
                    out.append("next")
                elif event.key == pygame.K_r:
                    out.append("refresh")
        return out

    def save(self, path: str) -> None:
        # The composited window, including the glow.
        pygame.image.save(self._screen, path)

    def close(self) -> None:
        pygame.quit()
