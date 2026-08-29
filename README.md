# Tube Board

Two live London Underground displays, powered by the free
[TfL Unified API](https://api.tfl.gov.uk).

- **[Departure board](#departure-board-departurespy)** - a platform "next train
  indicator" on an LED dot-matrix panel.
- **[Status board](#status-board-statuspy)** - a "service information" panel of
  line statuses and disruption reasons.

## Setup

```sh
python -m venv .venv
.venv/bin/pip install requests pygame Pillow ruff
```

An API key is optional at hobby polling rates; see `.env.example`.

## Departure Board (`departures.py`)

A platform "next train indicator", rendered for an LED dot-matrix panel using
the [London Underground Dot Matrix Typeface](https://github.com/petykowski/London-Underground-Dot-Matrix-Typeface).

```sh
.venv/bin/python departures.py
.venv/bin/python departures.py --search "canary wharf"  # find a station's stop ID.
```

### Flags

| Flag                     | Effect                                               |
|--------------------------|------------------------------------------------------|
| `--lines`, `--platforms` | Filters, or `all`                                    |
| `--rows N`               | Number of departure rows                             |
| `--status-every N`       | Seconds between line status passes, `0` for tab only |
| `--mock`                 | Canned data, no network                              |
| `--screenshot out.png`   | Render headless and save a PNG                       |

### Examples

```sh
# Every line in the station.
.venv/bin/python departures.py --lines all --platforms all
# Just the two lines that share platform 2.
.venv/bin/python departures.py --lines circle,hammersmith-city --platforms "Platform 2"
```

A line-name column appears automatically whenever the board mixes lines
(`show_line_names` in config overrides this). Grid size and window scale can be
configured in `config.toml`.

## Status Board (`status.py`)

A "service information" panel listing each selected line with its status and
disruption reasons. Rendered as a static, e-ink friendly image.

```sh
.venv/bin/python status.py
```

### Flags

| Flag          | Effect                             |
|---------------|------------------------------------|
| `--lines`     | Ignore the schedule and show these |
| `--day fri`   | Preview another day's schedule     |
| `--once PATH` | Fetch once, save a PNG, exit       |
| `--text`      | The same board in the terminal     |
| `--mock`      | Canned data, no network            |

### Examples

```sh
# Preview Friday's scheduled selection without waiting for Friday.
.venv/bin/python status.py --day fri --once friday.png
# A one-shot render for cron, e.g. an e-ink refresh every 15 minutes.
.venv/bin/python status.py --once /tmp/status.png
```

With many lines selected, rows shrink and reason text is trimmed to fit - pick
a subset for the fullest layout.

## Both Boards

`Q`/`ESC` quits either window; `R` forces a refresh on the status board.

### Status Passes on the Departure Board

The departure board's panel shows departures by default. Every `status_every`
seconds (default 60) the line status board interrupts for one pass through its
pages and then hands the panel back; `tab` calls it up at any time and pins it
there until you press `tab` again.

Passes are timed off the clock rather than off startup: the first lands on the
next whole minute and the rest follow at the interval, so the default puts one
on every minute no matter how long a pass runs or when the board was started.

The bottom row carries the clock while that is running, since the status board
is already reporting the disruptions. Set `status_every = 0` and the scrolling
disruption ticker takes the row back instead, with the status board left to
`tab`. Either way, `status_follows_schedule = true` makes that pass honour the
`[status]` selection and its day rules rather than listing every line.

## Configuration

Everything lives in `config.toml`:

- **`[station]`**: Which station (`id`, from `--search`), plus `lines` and
  `platforms` filters. Both are lists; empty means "everything". Use one of
  each (`lines = ["victoria"]`, `platforms = ["Southbound"]`) to mimic a single
  platform's board, or leave them empty for a whole-station board.
- **`[display]`**: LED grid size (default 256×64) and window scale.
- **`[status]`**: Which lines the status board shows, in the order given
  (empty means all 20, in TfL's order). See the schedule rules below.
- **`[status_display]`**: Status board canvas size (default 800×480).
- **`[refresh]`**: API polling intervals, used by both boards.

### Scheduling the Status Selection

Optional `[[status.schedule]]` blocks vary the selection by day: each has a
`days` spec (`"mon-thu"`, `"fri"`, `"sat,sun"`, `"weekday"`, `"weekend"`,
`"all"`) and its own `lines`. The first rule matching today wins, and the board
re-checks on every refresh so it follows the schedule over midnight. Preview
another day with `--day fri`; `--lines` ignores the schedule.

### National Rail

Thameslink is the one National Rail operator these boards know. Naming it
widens the status fetch to the National Rail mode, and the other 24 operators
on that mode are dropped as they arrive, so an "everything" selection stays a
London board.

## Project :ayout

The two boards are peers. Each owns its run loop and its layouts; they share
the TfL client, the data shapes, and the LED panel both can draw on.

Fonts are vendored in `fonts/`: the London Underground dot-matrix TTFs for the
departure board, plus Hammersmith One (Johnston-style, for the status board's
headings and line names) and Inter (status and reason text).

## Linting and formatting

[Ruff](https://docs.astral.sh/ruff/) handles both linting and formatting;
rules live in `ruff.toml`.

```sh
.venv/bin/ruff check .        # lint.
.venv/bin/ruff check --fix .  # lint, auto-fixing what's safe.
.venv/bin/ruff format .       # format.
```
