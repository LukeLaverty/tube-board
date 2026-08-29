"""
Line status board rendered as a static image.

Deliberately e-ink friendly: paper-white background, dark text, no animation.
"""

import contextlib
from datetime import datetime

from PIL import Image, ImageDraw, ImageFont

from ..config import FONT_DIRECTORY
from ..models import LINE_COLOURS, LineStatus, line_sort_key

PAPER = (255, 255, 255)
INK = (20, 20, 20)
GREY = (108, 108, 108)
RULE = (216, 216, 216)
RED = (196, 30, 20)


def _font(
    name: str, size: int, weight: int | None = None
) -> ImageFont.FreeTypeFont:
    font = ImageFont.truetype(str(FONT_DIRECTORY / name), size)
    if weight is not None:
        with contextlib.suppress(OSError):
            font.set_variation_by_axes([14, weight])
    return font


class _RowMetrics:
    def __init__(self, s: float):
        self.name = _font("HammersmithOne-Regular.ttf", max(10, round(19 * s)))
        self.status = _font(
            "Inter-Variable.ttf", max(10, round(18 * s)), weight=600
        )
        self.reason = _font(
            "Inter-Variable.ttf", max(9, round(15 * s)), weight=400
        )
        self.chip_width = round(206 * s)
        self.chip_height = round(30 * s)
        self.base_row = round(42 * s)
        self.reason_line = round(20 * s)
        self.text_gap = round(18 * s)
        self.chip_pad = round(10 * s)


def _chip_text_colour(
    colour: tuple[int, int, int],
) -> tuple[int, int, int]:
    luminance = 0.299 * colour[0] + 0.587 * colour[1] + 0.114 * colour[2]
    return INK if luminance > 160 else PAPER


def _wrap(
    draw: ImageDraw.ImageDraw, text: str, font, max_width: float
) -> list[str]:
    lines: list[str] = []
    current = ""
    for word in text.split():
        trial = f"{current} {word}".strip()
        if not current or draw.textlength(trial, font=font) <= max_width:
            current = trial
        else:
            lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def _normalise(name: str) -> str:
    flat = " ".join(name.lower().replace("&", "and").replace("-", " ").split())
    return flat.removesuffix(" line")


def _strip_line_prefix(reason: str, name: str) -> str:
    """
    Drop the "Central Line: " TfL puts on the front of a reason.
    """
    head, separator, rest = reason.partition(":")
    if not separator or not rest.strip():
        return reason
    if _normalise(head) != _normalise(name):
        return reason
    return rest.strip()


MAX_REASON_LINES = 4


def _allocate_reasons(draw, rows, metrics: _RowMetrics, text_width, available):
    """
    Hand out reason lines a round at a time, so every disrupted line gets
    its first line before any line gets a second, until the space runs out.
    """
    wrapped = [
        _wrap(
            draw,
            _strip_line_prefix(s.reason, s.name),
            metrics.reason,
            text_width,
        )[:MAX_REASON_LINES]
        if s.reason
        else []
        for s in rows
    ]
    shown = [0] * len(rows)
    used = len(rows) * metrics.base_row
    for depth in range(1, MAX_REASON_LINES + 1):
        for i, lines in enumerate(wrapped):
            if shown[i] >= min(depth, len(lines)):
                continue
            if used + metrics.reason_line > available:
                return shown, wrapped
            shown[i] += 1
            used += metrics.reason_line
    return shown, wrapped


def rows_for(
    statuses: list[LineStatus], selected: list[str] | None = None
) -> list[LineStatus]:
    """
    The lines this board shows, in the order it shows them.
    """
    if selected:
        # An explicit selection sets the running order too.
        position = {line: i for i, line in enumerate(selected)}
        return sorted(
            (status for status in statuses if status.line_id in position),
            key=lambda s: position[s.line_id],
        )
    return sorted(statuses, key=lambda s: line_sort_key(s.line_id))


def render_status_image(
    statuses: list[LineStatus],
    size: tuple[int, int] = (800, 480),
    selected: list[str] | None = None,
    updated: datetime | None = None,
    offline: bool = False,
) -> Image.Image:
    width, height = size
    scale = min(width / 800, height / 480)
    image = Image.new("RGB", size, PAPER)
    draw = ImageDraw.Draw(image)
    margin = round(24 * scale)

    rows = rows_for(statuses, selected)

    header_font = _font(
        "HammersmithOne-Regular.ttf", max(14, round(30 * scale))
    )
    updated_font = _font(
        "Inter-Variable.ttf", max(9, round(14 * scale)), weight=500
    )
    draw.text(
        (margin, round(16 * scale)),
        "Service Information",
        font=header_font,
        fill=INK,
    )
    if updated:
        note = f"Updated {updated:%H:%M}" + ("  ·  offline" if offline else "")
        note_width = draw.textlength(note, font=updated_font)
        draw.text(
            (width - margin - note_width, round(30 * scale)),
            note,
            font=updated_font,
            fill=RED if offline else GREY,
        )
    header_bottom = round(64 * scale)
    draw.line(
        (margin, header_bottom, width - margin, header_bottom),
        fill=RULE,
        width=max(1, round(2 * scale)),
    )

    if not rows:
        fallback = _RowMetrics(scale)
        draw.text(
            (margin, header_bottom + 20),
            "No line status data",
            font=fallback.status,
            fill=GREY,
        )
        return image

    available = height - header_bottom - round(8 * scale)

    for factor in (1.0, 0.85, 0.72, 0.62, 0.55):
        metrics = _RowMetrics(scale * factor)
        if len(rows) * metrics.base_row <= available:
            break
    text_x = margin + metrics.chip_width + metrics.text_gap
    text_width = width - margin - text_x
    shown, wrapped = _allocate_reasons(
        draw, rows, metrics, text_width, available
    )
    heights = [metrics.base_row + n * metrics.reason_line for n in shown]

    y = header_bottom + round(6 * scale)
    for index, (status, row_height) in enumerate(
        zip(rows, heights, strict=True)
    ):
        colour = LINE_COLOURS.get(status.line_id, (90, 90, 90))
        chip_y = (
            y + (metrics.base_row - metrics.chip_height) // 2 - round(2 * scale)
        )
        draw.rounded_rectangle(
            (
                margin,
                chip_y,
                margin + metrics.chip_width,
                chip_y + metrics.chip_height,
            ),
            radius=round(4 * scale),
            fill=colour,
        )
        draw.text(
            (
                margin + metrics.chip_pad,
                chip_y + metrics.chip_height / 2,
            ),
            status.name,
            font=metrics.name,
            fill=_chip_text_colour(colour),
            anchor="lm",
        )

        if status.good:
            status_colour = GREY
        elif status.severity <= 6:
            status_colour = RED
        else:
            status_colour = INK
        draw.text(
            (text_x, chip_y + metrics.chip_height / 2),
            status.description,
            font=metrics.status,
            fill=status_colour,
            anchor="lm",
        )

        n_lines = shown[index]
        if n_lines:
            lines = list(wrapped[index][:n_lines])
            if n_lines < len(wrapped[index]):
                lines[-1] = lines[-1].rstrip(".,;") + "…"
            for i, line in enumerate(lines):
                draw.text(
                    (
                        text_x,
                        y
                        + metrics.base_row
                        - round(6 * scale)
                        + i * metrics.reason_line,
                    ),
                    line,
                    font=metrics.reason,
                    fill=GREY,
                )

        y += row_height
        draw.line(
            (margin, y - 1, width - margin, y - 1),
            fill=RULE,
            width=1,
        )

    return image
