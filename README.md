# Tube Board

Two live London Underground displays, using data from the free
[TfL Unified API](https://api.tfl.gov.uk).

- **[Departure board](#departure-board-departurespy)**: a platform "next train
  indicator" for an LED dot-matrix panel.
- **[Status board](#status-board-statuspy)**: a "service information" panel of
  line statuses and disruption reasons.

## Setup

```sh
python -m venv .venv
.venv/bin/pip install Pillow requests   # required.
.venv/bin/pip install pygame            # to preview a board in a window.
.venv/bin/pip install pytest ruff       # for development.
```

Pygame is only used for the preview window, so it isn't needed to render a
board to a file.

The project itself isn't installed as a package; run it from the checkout.
Config is read from `--config PATH` if given, otherwise from the first of these
that exists:

1. `./config.toml`
2. `config.toml` in the checkout
3. `~/.config/tube-board/config.toml`
4. `/etc/tube-board/config.toml`

`.env` is looked for in the same places. An API key is optional at hobby polling
rates; see `.env.example`.

`departures.py` and `status.py` are shorthands for `python -m tube_board
departures` and `python -m tube_board status`, and take the same flags.

## Departure Board (`departures.py`)

A platform "next train indicator", drawn with the
[London Underground Dot Matrix Typeface](https://github.com/petykowski/London-Underground-Dot-Matrix-Typeface).

```sh
.venv/bin/python departures.py
.venv/bin/python -m tube_board search "canary wharf"  # find a stop ID.
```

### Flags

| Flag                     | Effect                                               |
|--------------------------|------------------------------------------------------|
| `--lines`, `--platforms` | Filters, or `all`                                    |
| `--rows N`               | Number of departure rows                             |
| `--status-every N`       | Seconds between line status passes, `0` for Tab only |
| `--mock`                 | Canned data, no network                              |
| `--screenshot out.png`   | Render headless and save a PNG                       |

### Examples

```sh
# Every line in the station.
.venv/bin/python departures.py --lines all --platforms all
# Just the two lines that share platform 2.
.venv/bin/python departures.py --lines circle,hammersmith-city --platforms "Platform 2"
```

A line-name column appears when the board shows more than one line. Set
`show_line_names` to `"always"` or `"never"` to override that.

### Status Passes

Every `status_every` seconds (default 60), the panel switches to the line
status board for one pass through its pages, then back to departures. Passes
start on the next whole minute, so with the default there is one every minute.
Tab shows the status board and keeps it there until tab is pressed again.

While passes are on, the bottom row shows the clock. With `status_every = 0`,
it shows a scrolling ticker of disruptions instead.

The pass lists every line unless `status_follows_schedule = true`, which uses
the `[status]` selection and schedule.

## Status Board (`status.py`)

A "service information" panel listing each selected line with its status and
any disruption reason, as a static image suitable for e-ink.

```sh
.venv/bin/python status.py
```

### Flags

| Flag          | Effect                             |
|---------------|------------------------------------|
| `--lines`     | Ignore the schedule and show these |
| `--day fri`   | Preview another day's schedule     |
| `--once PATH` | Fetch once, save a PNG, exit       |
| `--text`      | Print the board to the terminal    |
| `--mock`      | Canned data, no network            |

### Examples

```sh
# Preview Friday's selection.
.venv/bin/python status.py --day fri --once friday.png
# A one-shot render, e.g. from cron for an e-ink refresh.
.venv/bin/python status.py --once /tmp/status.png
```

`--once` exits with status 1 and writes nothing if the API can't be reached.

With many lines selected, rows shrink and reasons are cut short to fit.

## Keys

| Key        | Effect                                |
|------------|---------------------------------------|
| `Q`, `Esc` | Quit                                  |
| `Tab`      | Show or hide status (departure board) |
| `R`        | Refresh now (status board)            |

## Configuration

All settings live in `config.toml`. A missing `--config` file or a bad schedule
rule stops either board at startup.

- **`[station]`**: the station `id` (from `python -m tube_board search`), and
  `lines` and `platforms` filters. Both are lists, and empty means everything.
  For example, `lines = ["victoria"]` and `platforms = ["Southbound"]` give a
  single platform's board.
- **`[display]`**: LED panel size (default 256×64), window scale, and the
  status pass settings above.
- **`[status]`**: which lines the status board shows, in the order given. Empty
  means all 21, in TfL's order.
- **`[status_display]`**: status board size (default 800×480).
- **`[refresh]`**: API polling intervals for both boards.

### Scheduling the Status Selection

Optional `[[status.schedule]]` blocks change the selection by day. Each has a
`days` value (`"mon-thu"`, `"fri"`, `"sat,sun"`, `"weekday"`, `"weekend"`,
`"all"`) and its own `lines`. The first matching rule wins. The board checks
again on every refresh, so it switches over at midnight.

### National Rail

Thameslink is the only National Rail operator the boards support. Selecting it,
or leaving the selection empty, adds National Rail to the status fetch; the
other operators are filtered out. Its reason text is dropped, because National
Rail returns a link there instead of a description.

## Project Layout

```
tube_board/
  render/       layouts: data in, image out
    led/        LED panel theme, departures and status
    paper/      e-ink theme and status
    fonts/      vendored TTFs
    text.py     the status board as text
  boards/       panel.py and paper.py: what's on screen and when
  drivers/      window.py (Pygame preview) and png.py: where frames go
  runner.py     the frame loop
  sources/      tfl.py (live API) and mock.py
  selection.py  which lines to show, and in what order
  config.py     config files and defaults
  models.py     data classes and line constants
  cli.py        argument parsing and setup
departures.py   shorthand for `python -m tube_board departures`
status.py       shorthand for `python -m tube_board status`
```

Boards render Pillow images and drivers display them, so any board works with
any driver. Pillow is used rather than Pygame because LED panel and e-ink
libraries also take Pillow images.

The LED layouts draw without antialiasing at the font's native 9px size, so
each dot of a glyph is one lamp. The status board uses Hammersmith One for
headings and line names, and Inter for status and reason text.

## Tests

```sh
.venv/bin/pytest
```

`pytest.ini` puts the checkout on `sys.path`, so nothing needs installing.

`tests/golden/` holds reference images for the LED layouts, compared pixel for
pixel. After an intended layout change, regenerate them and check the diff:

```sh
UPDATE_GOLDENS=1 .venv/bin/pytest tests/test_render.py
```

## Linting and Formatting

[Ruff](https://docs.astral.sh/ruff/) handles both, configured in `ruff.toml`.

```sh
.venv/bin/ruff check .        # lint.
.venv/bin/ruff check --fix .  # lint and apply safe fixes.
.venv/bin/ruff format .       # format.
```

## Attribution and Licencing

Live data comes from the [TfL Unified API](https://api.tfl.gov.uk) under
TfL's [transport data terms](https://tfl.gov.uk/corporate/terms-and-conditions/transport-data-service):

- Powered by TfL Open Data.
- Contains OS data (c) Crown copyright and database rights 2016.
- Geomni UK Map data (c) and database rights 2019.

The fonts in [`tube_board/render/fonts/`](tube_board/render/fonts/) are
third-party, unmodified, and licenced under the SIL Open Font Licence 1.1. See
[`fonts/README.md`](tube_board/render/fonts/README.md) for each font's
copyright notice and [`fonts/OFL.txt`](tube_board/render/fonts/OFL.txt) for the
licence.
