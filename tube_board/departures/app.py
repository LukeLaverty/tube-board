"""
Runs the departure board: poll TfL, draw a frame, push it to the LED output.
"""

import math
import os
import time

from ..config import load_app_key

SCREENSHOT_FRAMES = 90  # ~3 seconds at 30 FPS.
SCREENSHOT_WAIT = 15  # seconds to let the first live poll land.


def _next_minute(now: float) -> float:
    """
    The next whole minute on the wall clock.
    """
    return math.floor(now / 60) * 60 + 60


def _advance(next_at: float, every: float, now: float) -> float:
    """
    Move a trigger on to the first slot still ahead of `now`.

    Skips any slot missed while the status board held the panel, so a pass
    that runs longer than the interval does not fire again the moment it ends.
    """
    if every <= 0:
        return next_at
    while next_at <= now:
        next_at += every
    return next_at


def _snapshot_source(
    cfg: dict,
    mock: bool,
    wait_for_data: bool,
    status_modes: str | None = None,
):
    """
    Returns (get_snapshot, poller). The poller is None in mock mode.
    """
    if mock:
        from ..mock_data import mock_snapshot

        return mock_snapshot, None

    from ..tfl import STATUS_MODES, Poller, TflClient

    poller = Poller(
        TflClient(load_app_key()),
        cfg["station"]["id"],
        arrivals_every=float(cfg["refresh"]["arrivals_seconds"]),
        status_every=float(cfg["refresh"]["status_seconds"]),
        status_modes=status_modes or STATUS_MODES,
    )
    poller.start()
    if wait_for_data:
        deadline = time.time() + SCREENSHOT_WAIT
        while time.time() < deadline:
            snapshot = poller.snapshot()
            if snapshot.departures and snapshot.statuses:
                break
            time.sleep(0.2)
    return poller.snapshot, poller


def run(
    config: dict,
    *,
    mock: bool = False,
    screenshot: str | None = None,
) -> None:
    if screenshot:
        # Must land before Pygame is imported, hence the deferred imports below.
        os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

    import pygame

    from ..display.pygame_led import PygameWindow
    from ..matrix import Fonts
    from ..status import configured_lines, selection_for
    from ..status.screen import StatusScreen
    from ..tfl import modes_for
    from .screen import DeparturesScreen

    display_config = config["display"]
    width, height = (
        int(display_config["width"]),
        int(display_config["height"]),
    )
    scale = int(display_config["scale"])

    status_modes = modes_for(configured_lines(config))

    get_snapshot, poller = _snapshot_source(
        config,
        mock,
        wait_for_data=bool(screenshot),
        status_modes=status_modes,
    )

    window = PygameWindow(
        width,
        height,
        scale,
        title=f"Tube Board - {config['station']['name']}",
    )

    status_every = float(display_config.get("status_every", 0) or 0)

    selection = (
        (lambda: selection_for(config))
        if display_config.get("status_follows_schedule")
        else None
    )

    fonts = Fonts()
    status_screen = StatusScreen(fonts, selection)
    screens = [
        DeparturesScreen(fonts, config, ticker=not status_every),
        status_screen,
    ]
    current = 0
    pinned = False
    # Hang triggers off the wall clock so passes land on round times.
    elapsed = 0.0
    next_status = 0.0
    if status_every:
        next_status = status_every if screenshot else _next_minute(time.time())
    clock = pygame.time.Clock()
    frame_count = 0
    running = True

    try:
        while running:
            dt = (
                1 / 30
                if screenshot
                else clock.tick(int(display_config["fps"])) / 1000
            )
            elapsed += dt
            now = elapsed if screenshot else time.time()

            events = window.events()
            if "quit" in events:
                running = False
            if "next" in events:
                current = 1 - current
                pinned = current == 1
                if pinned:
                    status_screen.restart(repeat=True)
                else:
                    next_status = _advance(next_status, status_every, now)

            if current == 0:
                if status_every and now >= next_status:
                    current, pinned = 1, False
                    status_screen.restart()
                    next_status = _advance(next_status, status_every, now)
            elif not pinned and status_screen.finished:
                current = 0
                next_status = _advance(next_status, status_every, now)

            frame = pygame.Surface((width, height))
            screens[current].render(frame, get_snapshot(), dt)
            window.show(frame)

            frame_count += 1
            if screenshot and frame_count >= SCREENSHOT_FRAMES:
                window.save(screenshot)
                print(f"Saved {screenshot}")
                running = False
    finally:
        if poller:
            poller.stop()
        window.close()
