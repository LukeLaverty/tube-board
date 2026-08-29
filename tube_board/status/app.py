"""
Runs the status board: fetch line status, render the board, show or save it.
"""

import time
from collections.abc import Callable
from datetime import datetime

import requests

from ..config import load_app_key
from ..models import LineStatus
from .board import render_status_image, rows_for
from .schedule import lines_for

Fetcher = Callable[[list[str]], list[LineStatus]]


def make_fetcher(mock: bool = False) -> Fetcher:
    """
    A callable taking the selected line IDs and returning their statuses.
    """
    if mock:
        from ..mock_data import mock_statuses

        return lambda selected: mock_statuses()

    from ..tfl import TflClient, modes_for

    client = TflClient(load_app_key())
    return lambda selected: client.line_status(modes_for(selected))


def selection_for(
    config: dict,
    override: list[str] | None = None,
    weekday: int | None = None,
) -> list[str]:
    """
    CLI override beats the day's schedule, which beats [status] lines.
    """
    if override is not None:
        return override
    fallback = [
        line.strip().lower()
        for line in config["status"]["lines"]
        if line.strip()
    ]
    return lines_for(config["status"]["schedule"], fallback, weekday)


def configured_lines(config: dict) -> list[str]:
    """
    Every line [status] names, across the fallback list and each schedule
    rule, so one fetch can cover whichever day it turns out to be.
    """
    names = list(config["status"]["lines"])
    for rule in config["status"]["schedule"]:
        names.extend(rule.get("lines", []))
    ordered = {}
    for name in names:
        if key := str(name).strip().lower():
            ordered.setdefault(key)
    return list(ordered)


def board_size(config: dict) -> tuple[int, int]:
    display_config = config["status_display"]
    return int(display_config["width"]), int(display_config["height"])


def print_status_text(
    statuses: list[LineStatus], selected: list[str] | None = None
) -> None:
    """
    The board's plain-text form, for a terminal instead of a screen.
    """
    for status in rows_for(statuses, selected):
        print(f"{status.name:24s} {status.description}")
        if status.reason:
            print(f"{'':24s} {status.reason}")


def render_once(
    config: dict,
    path: str,
    fetch: Fetcher,
    override: list[str] | None = None,
    weekday: int | None = None,
) -> None:
    """
    Fetch once and save a PNG for cron.
    """
    selected = selection_for(config, override, weekday)
    image = render_status_image(
        fetch(selected),
        board_size(config),
        selected,
        datetime.now(),
    )
    image.save(path)
    print(f"Saved {path}")


def run(
    config: dict,
    fetch: Fetcher,
    override: list[str] | None = None,
    weekday: int | None = None,
) -> None:
    import pygame

    size = board_size(config)
    pygame.init()
    screen = pygame.display.set_mode(size)
    pygame.display.set_caption("Tube Board - Service Information")
    clock = pygame.time.Clock()

    refresh_every = float(config["refresh"]["status_seconds"])
    statuses: list[LineStatus] = []
    updated: datetime | None = None
    last_success = 0.0
    next_fetch = 0.0
    running = True

    while running:
        now = time.monotonic()
        if now >= next_fetch:
            next_fetch = now + refresh_every
            # Re-read each cycle so board follows the schedule over midnight.
            selected = selection_for(config, override, weekday)
            try:
                statuses = fetch(selected)
                updated = datetime.now()
                last_success = now
            except requests.RequestException:
                pass
            offline = (
                now - last_success > refresh_every * 2 if last_success else True
            )
            image = render_status_image(
                statuses, size, selected, updated, offline
            )
            frame = pygame.image.frombuffer(image.tobytes(), image.size, "RGB")
            screen.blit(frame, (0, 0))
            pygame.display.flip()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_q, pygame.K_ESCAPE):
                    running = False
                elif event.key == pygame.K_r:
                    next_fetch = 0.0
        clock.tick(10)

    pygame.quit()
