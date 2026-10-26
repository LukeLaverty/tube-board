"""
The "Service Information" board: line statuses as a static image, scaled to
the panel.
"""

from datetime import datetime

from PIL import Image, ImageDraw

from ...models import LINE_COLOURS, UNKNOWN_COLOUR, LineStatus
from ...selection import rows_for
from .theme import (
    GREY,
    INK,
    PAPER,
    RED,
    RULE,
    RowMetrics,
    chip_text_colour,
    font,
)


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


_PREFIX_ALIASES = {
    "london trams": "tram",
    "docklands light railway": "dlr",
}


def _normalise(name: str) -> str:
    flat = " ".join(name.lower().replace("&", "and").replace("-", " ").split())
    flat = flat.removesuffix(" lines").removesuffix(" line")
    return _PREFIX_ALIASES.get(flat, flat)


def _prefix_names(head: str) -> set[str]:
    """
    The lines a reason prefix names. Usually one, but a shared disruption
    arrives as "Metropolitan and Jubilee lines: ...".
    """
    flat = _normalise(head)
    return {flat, *flat.replace(",", " and ").split(" and ")}


def _strip_line_prefix(reason: str, name: str) -> str:
    """
    Drop the "Central Line: " prefix TfL puts on reasons and capitalise what
    follows.
    """
    head, separator, rest = reason.partition(":")
    rest = rest.strip()
    if not separator or not rest:
        return reason
    if _normalise(name) not in _prefix_names(head):
        return reason
    return rest[0].upper() + rest[1:]


def _allocate_reasons(draw, rows, metrics: RowMetrics, text_width, available):
    """
    Share out reason lines round-robin, so every disrupted line gets one before
    any gets a second.
    """
    wrapped = [
        _wrap(
            draw,
            _strip_line_prefix(s.reason, s.name),
            metrics.reason,
            text_width,
        )
        if s.reason
        else []
        for s in rows
    ]
    shown = [0] * len(rows)
    used = len(rows) * metrics.base_row
    for depth in range(1, max(map(len, wrapped), default=0) + 1):
        for i, lines in enumerate(wrapped):
            if shown[i] >= min(depth, len(lines)):
                continue
            if used + metrics.reason_line > available:
                return shown, wrapped
            shown[i] += 1
            used += metrics.reason_line
    return shown, wrapped


def render_status_image(
    statuses: list[LineStatus],
    size: tuple[int, int] = (800, 480),
    selected: list[str] | None = None,
    updated: datetime | None = None,
    offline: bool = False,
) -> Image.Image:
    width, height = size
    scale = min(width, height) / 480
    image = Image.new("RGB", size, PAPER)
    draw = ImageDraw.Draw(image)
    margin = round(24 * scale)

    rows = rows_for(statuses, selected)

    header_font = font("HammersmithOne-Regular.ttf", max(14, round(30 * scale)))
    updated_font = font(
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
        fallback = RowMetrics(scale)
        draw.text(
            (margin, header_bottom + 20),
            "No line status data",
            font=fallback.status,
            fill=GREY,
        )
        return image

    available = height - header_bottom - round(8 * scale)

    disrupted = sum(1 for status in rows if status.reason)
    options = [RowMetrics(scale * f) for f in (1.0, 0.85, 0.72, 0.62, 0.55)]
    metrics = next(
        (m for m in options if len(rows) * m.base_row <= available),
        options[-1],
    )
    metrics = next(
        (
            m
            for m in options
            if len(rows) * m.base_row + disrupted * m.reason_line <= available
        ),
        metrics,
    )
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
        colour = LINE_COLOURS.get(status.line_id, UNKNOWN_COLOUR)
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
            fill=chip_text_colour(colour),
            anchor="lm",
        )

        if status.good:
            status_colour = GREY
        elif status.severe:
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
