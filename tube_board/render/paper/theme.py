"""
Colours, fonts and row metrics for the paper board. White background and
dark text, for e-ink.
"""

import contextlib

from PIL import ImageFont

from ...models import Colour
from .. import FONT_DIRECTORY

PAPER = (255, 255, 255)
INK = (20, 20, 20)
GREY = (108, 108, 108)
RULE = (216, 216, 216)
RED = (196, 30, 20)


def font(
    name: str, size: int, weight: int | None = None
) -> ImageFont.FreeTypeFont:
    face = ImageFont.truetype(
        str(FONT_DIRECTORY / name),
        size,
        layout_engine=ImageFont.Layout.BASIC,
    )
    if weight is not None:
        with contextlib.suppress(OSError):
            face.set_variation_by_axes([14, weight])
    return face


class RowMetrics:
    """
    Every size a row needs at a given scale. The board uses the largest scale
    that fits.
    """

    def __init__(self, s: float):
        self.name = font("HammersmithOne-Regular.ttf", max(10, round(19 * s)))
        self.status = font(
            "Inter-Variable.ttf", max(10, round(18 * s)), weight=600
        )
        self.reason = font(
            "Inter-Variable.ttf", max(9, round(15 * s)), weight=400
        )
        self.chip_width = round(206 * s)
        self.chip_height = round(30 * s)
        self.base_row = round(42 * s)
        self.reason_line = round(20 * s)
        self.text_gap = round(18 * s)
        self.chip_pad = round(10 * s)


def chip_text_colour(colour: Colour) -> Colour:
    luminance = 0.299 * colour[0] + 0.587 * colour[1] + 0.114 * colour[2]
    return INK if luminance > 160 else PAPER
