"""
Pygame window that renders a native-resolution frame as an LED matrix.
"""

import pygame

from .base import Output

BACKGROUND = (7, 7, 9)
OFF_DOT = (17, 17, 20)


class PygameWindow(Output):
    def __init__(
        self,
        width: int,
        height: int,
        scale: int = 6,
        title: str = "Tube Board",
    ):
        pygame.init()
        self._native = (width, height)
        self._scale = scale
        self._size = (width * scale, height * scale)
        self._screen = pygame.display.set_mode(self._size)
        pygame.display.set_caption(title)
        self._background = self._build_background()
        self._mask = self._build_mask()

    def _build_background(self) -> pygame.Surface:
        """
        Black panel with a faint grid of unlit dots.
        """
        scale = self._scale
        background = pygame.Surface(self._size)
        background.fill(BACKGROUND)
        tile = pygame.Surface((scale, scale))
        tile.fill(BACKGROUND)
        pygame.draw.circle(tile, OFF_DOT, (scale / 2, scale / 2), scale * 0.44)
        for x in range(0, self._size[0], scale):
            for y in range(0, self._size[1], scale):
                background.blit(tile, (x, y))
        return background

    def _build_mask(self) -> pygame.Surface:
        """
        Opaque black with a round transparent hole per LED cell.
        """
        scale = self._scale
        tile = pygame.Surface((scale, scale), pygame.SRCALPHA)
        tile.fill((0, 0, 0, 255))
        pygame.draw.circle(
            tile, (0, 0, 0, 0), (scale / 2, scale / 2), scale * 0.44
        )
        mask = pygame.Surface(self._size, pygame.SRCALPHA)
        for x in range(0, self._size[0], scale):
            for y in range(0, self._size[1], scale):
                mask.blit(tile, (x, y))
        return mask

    def show(self, frame: pygame.Surface) -> None:
        crisp = pygame.transform.scale(frame, self._size)
        glow = pygame.transform.smoothscale(frame, self._size)
        glow.fill((70, 70, 70), special_flags=pygame.BLEND_MULT)
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
        return out

    def save(self, path: str) -> None:
        pygame.image.save(self._screen, path)

    def close(self) -> None:
        pygame.quit()
