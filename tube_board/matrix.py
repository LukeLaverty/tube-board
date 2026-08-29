"""
Drawing primitives for the LED dot-matrix panel.
"""

import pygame

from .config import FONT_DIRECTORY

AMBER = (255, 176, 0)
RED = (255, 60, 50)
WHITE = (255, 255, 255)
DIM = (60, 60, 60)

# 9pt is this TTF's native dot grid: one dot lands on exactly one pixel.
NATIVE_SIZE = 9
GLYPH_HEIGHT = 9
# Capitals and letters with tails hang one pixel below the baseline.
ROW_HEIGHT = 10


class Fonts:
    def __init__(self, scale: int = 1):
        regular = str(FONT_DIRECTORY / "LondonUnderground-Regular.ttf")
        self.text = pygame.font.Font(regular, NATIVE_SIZE * scale)


def draw_text(frame, font, text, x, y, colour, align="left") -> int:
    surface = font.render(text, False, colour)
    if align == "right":
        x -= surface.get_width()
    elif align == "center":
        x -= surface.get_width() // 2
    frame.blit(surface, (x, y))
    return surface.get_width()
