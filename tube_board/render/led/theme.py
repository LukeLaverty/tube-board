"""
Colours, fonts and drawing for the LED panel. Each pixel is one lamp, so
nothing is antialiased.
"""

from PIL import Image, ImageDraw, ImageFont

from ...models import Colour
from .. import FONT_DIRECTORY

AMBER = (255, 176, 0)
RED = (255, 60, 50)
WHITE = (255, 255, 255)
DIM = (60, 60, 60)
# An unlit lamp, and the background.
OFF = (0, 0, 0)

# 9pt is this TTF's native dot grid: one dot lands on exactly one pixel.
NATIVE_SIZE = 9
GLYPH_HEIGHT = 9
# Capitals and letters with tails hang one pixel below the baseline.
ROW_HEIGHT = 10


class BitmapFont:
    """
    A TTF at its native dot size, measured in whole pixels.
    """

    def __init__(self, path: str, size: int):
        # BASIC advances each glyph by whole pixels. The default layout
        # accumulates fractional advances, which puts later glyphs between
        # lamps.
        self.font = ImageFont.truetype(
            path, size, layout_engine=ImageFont.Layout.BASIC
        )
        # `textlength` needs a draw context; any image will do.
        self._ruler = ImageDraw.Draw(Image.new("RGB", (1, 1)))
        self._advances: dict[str, int] = {}

    def _advance(self, character: str) -> int:
        if character not in self._advances:
            length = self._ruler.textlength(character, font=self.font)
            self._advances[character] = round(length)
        return self._advances[character]

    def width(self, text: str) -> int:
        """
        The advance width of `text`, rounded per glyph to match where each one
        is drawn. Rounding the total once is a pixel out on "09:41:07".
        """
        return sum(self._advance(character) for character in text)


class Fonts:
    def __init__(self, scale: int = 1):
        regular = str(FONT_DIRECTORY / "LondonUnderground-Regular.ttf")
        self.text = BitmapFont(regular, NATIVE_SIZE * scale)


class Canvas:
    """
    A frame to draw on. Coordinates are panel pixels, and rectangles are
    (x, y, width, height).
    """

    def __init__(self, size: tuple[int, int]):
        self.image = Image.new("RGB", size, OFF)
        self._draw = ImageDraw.Draw(self.image)
        # "1" turns antialiasing off.
        self._draw.fontmode = "1"

    @property
    def width(self) -> int:
        return self.image.width

    @property
    def height(self) -> int:
        return self.image.height

    def text(
        self,
        font: BitmapFont,
        text: str,
        x: int,
        y: int,
        colour: Colour,
        align: str = "left",
        clip: tuple[int, int, int, int] | None = None,
    ) -> int:
        """
        Draw `text` and return its width. `align` is relative to `x`, and
        `clip` limits drawing to a rectangle.
        """
        width = font.width(text)
        if align == "right":
            x -= width
        elif align == "center":
            x -= width // 2

        if clip is None:
            self._draw.text((x, y), text, font=font.font, fill=colour)
            return width

        # Draw onto a copy of the clip region, then paste it back.
        left, top, box_width, box_height = clip
        if box_width <= 0 or box_height <= 0:
            return width
        patch = Canvas((box_width, box_height))
        patch.image.paste(
            self.image.crop((left, top, left + box_width, top + box_height))
        )
        patch._draw.text((x - left, y - top), text, font=font.font, fill=colour)
        self.image.paste(patch.image, (left, top))
        return width

    def rect(self, x: int, y: int, width: int, height: int, colour: Colour):
        self._draw.rectangle((x, y, x + width - 1, y + height - 1), fill=colour)

    def outline(self, x: int, y: int, width: int, height: int, colour: Colour):
        self._draw.rectangle(
            (x, y, x + width - 1, y + height - 1), outline=colour, width=1
        )

    def pixel(self, x: int, y: int, colour: Colour) -> None:
        self.image.putpixel((x, y), colour)

    def paste(self, other: Image.Image, x: int, y: int) -> None:
        self.image.paste(other, (x, y))
