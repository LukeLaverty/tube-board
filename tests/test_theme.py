"""
The LED panel's text measurement, which the layouts align everything against.
"""

from tube_board.render.led.theme import AMBER, WHITE, Canvas, Fonts

font = Fonts().text


class TestWidth:
    def test_is_the_sum_of_its_glyphs(self):
        assert font.width("ab") == font.width("a") + font.width("b")

    def test_empty_text_takes_no_room(self):
        assert font.width("") == 0

    def test_narrow_glyphs_do_not_drift(self):
        # The colon advances just under three pixels, so rounding the total
        # once loses a pixel across two colons.
        assert font.width("09:41:07") == font.width("09") + font.width(
            ":"
        ) * 2 + font.width("41") + font.width("07")


class TestCanvas:
    def test_starts_unlit(self):
        canvas = Canvas((16, 8))
        assert canvas.image.getbbox() is None

    def test_reports_its_size(self):
        canvas = Canvas((256, 64))
        assert (canvas.width, canvas.height) == (256, 64)

    def test_text_returns_the_width_it_drew(self):
        canvas = Canvas((256, 16))
        assert canvas.text(font, "Brixton", 0, 0, AMBER) == font.width(
            "Brixton"
        )

    def test_right_aligned_text_ends_where_it_was_put(self):
        aligned = Canvas((256, 16))
        aligned.text(font, "12 min", 200, 0, AMBER, align="right")
        # Same as placing it at the anchor minus its width. The ink can stop
        # short of the anchor because of the glyph's bearing.
        placed = Canvas((256, 16))
        placed.text(font, "12 min", 200 - font.width("12 min"), 0, AMBER)
        assert aligned.image.tobytes() == placed.image.tobytes()
        assert aligned.image.getbbox()[2] <= 200

    def test_centred_text_straddles_the_point(self):
        canvas = Canvas((256, 16))
        width = font.width("09:41:07")
        canvas.text(font, "09:41:07", 128, 0, AMBER, align="center")
        assert canvas.image.getbbox()[0] == 128 - width // 2

    def test_clipping_keeps_text_inside_its_box(self):
        canvas = Canvas((256, 16))
        canvas.text(
            font,
            "Docklands Light Railway",
            10,
            0,
            WHITE,
            clip=(10, 0, 40, 10),
        )
        left, _, right, _ = canvas.image.getbbox()
        assert left >= 10
        assert right <= 50

    def test_a_zero_width_clip_draws_nothing(self):
        canvas = Canvas((256, 16))
        canvas.text(font, "Anything", 10, 0, WHITE, clip=(10, 0, 0, 10))
        assert canvas.image.getbbox() is None

    def test_rect_covers_exactly_its_size(self):
        canvas = Canvas((32, 32))
        canvas.rect(4, 6, 5, 10, WHITE)
        assert canvas.image.getbbox() == (4, 6, 9, 16)

    def test_outline_leaves_the_middle_unlit(self):
        canvas = Canvas((32, 32))
        canvas.outline(4, 6, 5, 10, WHITE)
        assert canvas.image.getpixel((4, 6)) == WHITE
        assert canvas.image.getpixel((6, 10)) == (0, 0, 0)

    def test_pixel_lights_one_lamp(self):
        canvas = Canvas((32, 32))
        canvas.pixel(7, 9, WHITE)
        assert canvas.image.getbbox() == (7, 9, 8, 10)
