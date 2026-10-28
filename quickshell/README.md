# Evergreen system dashboard

Quickshell 0.3.2 on Hyprland 0.56.2. This is a layer-shell desktop widget, not a
Kitty window: it accepts no keyboard focus, never enters Alt-Tab, and remains on
DP-3 across workspace changes. Waybar, wallpaper and the existing session services
are independent of it.

## Install and run

Dependencies: `quickshell`, `python`, `util-linux` (findmnt/flock), and the existing
`nvidia-smi` utility. No pip packages or system service are needed.

From the dotfiles repository:

```sh
stow --simulate --verbose --target="$HOME" quickshell hypr
stow --target="$HOME" quickshell hypr
hyprctl reload
sh ~/.config/quickshell/evergreen/dashboard.sh start
```

The existing `hyprland.start` callback starts the dashboard at next login. Reloading
Hyprland does not rerun that event; the final command activates it immediately.
Repeated `start` requests are harmless. A runtime lock and Quickshell's
`--no-duplicate` option prevent duplicate instances.

**Super + Shift + M** hides/shows both panels without killing it or resetting its
history. If it isn't running, that shortcut starts it. Super + M retains the
existing session exit command. The collector continues sampling while hidden.

## Appearance and position

Edit `.config/quickshell/evergreen/Style.qml` in this package:

| Setting | Default | Adjustment |
| --- | --- | --- |
| `monitor` | `DP-3` | Exact output name from `hyprctl monitors -j` |
| `widthFraction` | `0.23` | Fraction of logical monitor width; use `0.20`–`0.25` |
| `edgeMargin` | `20` | Right and bottom margin in logical pixels |
| `topMargin` | `54` | Top offset; accounts for the existing 30 px Waybar |
| `panelOpacity` | `0.82` | Background alpha only; text stays opaque |
| Color properties | Evergreen palette | RGB hex values for surfaces, text and graphs |
| `font` | `DejaVu Sans Mono` | Installed font family |

On the current 2560×1440, scale-1 DP-3 display, the panel is 589×1366 at global
(4511, 54), with a 20 px right/bottom margin. The corners have a 12 px radius in
`shell.qml`. Settings reload automatically; hidden state survives QML reloads.
If the monitor is disconnected, the panel is removed and returns on reconnection.
It intentionally does not fall back to the left monitor.

The panel uses the **bottom layer**, above hyprpaper but below application windows.
It reserves no workspace space: normal windows still tile over the full work area
and can cover it. For an overlay that stays above applications, change
`WlrLayershell.layer` from `WlrLayer.Bottom` to `WlrLayer.Top` in `shell.qml`; that
will cover part of applications instead of reserving space. No Hyprland floating
window rules are needed for a layer-shell surface. Notifications stay above it.

## Metrics and resource use

One persistent standard-library Python collector reads `/proc` and `/sys` every
two seconds. One bounded `nvidia-smi` query runs per sample, with a 1.5-second
timeout. It retains 40 samples (about 80 seconds) for the graphs. There are no
animated transitions, network requests, privileged reads, or driver changes.

- CPU: overall and 32 logical-CPU utilization deltas, average reported frequency,
  and the k10temp `Tctl` package temperature. These are logical CPUs, not 32
  physical cores. CPU utilization excludes idle and I/O-wait time.
- GPU: NVIDIA GPU index 0, verified as the RTX 3060 Ti; utilization, temperature,
  used/total VRAM and power via `nvidia-smi`. Unsupported values display a dash.
- Memory: total minus `MemAvailable`, available RAM, total swap usage and zram
  logical/resident sizes. Swap totals already include zram; do not add them twice.
- Disk: root filesystem usage and user-available capacity. Read/write activity is
  for the root backing block device/partition, not individual files. Multi-device
  filesystems can have incomplete I/O coverage; unresolvable devices show
  unavailable rather than fabricated activity. Capacity is unaffected.
- Network: default-route interface (IPv4/IPv6), or an active-link fallback;
  receive/transmit byte-counter deltas. On interface changes, throughput waits for
  the next comparable sample. “Connected” means link up with a default route,
  not verified Internet reachability.
- Processes: exactly five, sorted by CPU delta then resident memory. Here 100%
  means one logical CPU; overall CPU usage is normalized across all CPUs. Process
  exit and PID reuse are handled. Inaccessible processes are omitted.
- System: uptime and 1/5/15-minute load averages.

A stale/error notice appears if samples fail or stop arriving; the collector is
restarted after failure, at most once per five seconds. Initial metrics take about
two seconds. On smaller screens, the content scrolls without taking keyboard
focus. Qt rendering has a larger resident-memory footprint than the Python
collector; a live spot check showed roughly 437 MiB for Quickshell, 17 MiB for
Python, and about 0.5–0.6% CPU each (process percentages, not total-machine CPU).

## Diagnostics and validation

```sh
qs -c evergreen ipc call dashboard status
qs -c evergreen ipc call dashboard visible
sh ~/.config/quickshell/evergreen/dashboard.sh toggle
cat "$XDG_RUNTIME_DIR/evergreen-dashboard.log"
hyprctl layers
hyprctl configerrors
python3 ~/.config/quickshell/evergreen/metrics.py --once
```

Validated in the live session: all requested metrics, the panel dimensions and
monitor, hide/show, repeated startup without duplicates, workspace persistence,
and a temporary ordinary Kitty window tiling correctly on DP-3. The original
workspace and keyboard focus were restored after testing. The 49 preexisting
bindings remain, plus one unique Super + Shift + M binding. Lua syntax, shell
syntax, QML lint and Stow conflict checks pass. A complete logout/login was not
performed; the exact command registered for startup was exercised directly.

References: [Quickshell PanelWindow](https://quickshell.org/docs/v0.3.2/types/Quickshell/PanelWindow/),
[Wayland layers](https://quickshell.org/docs/v0.3.2/types/Quickshell.Wayland/WlrLayershell/),
and [IPC handlers](https://quickshell.org/docs/v0.3.2/types/Quickshell.Io/IpcHandler/).

## NYC weather card

A compact, top-aligned weather card sits **beside**, to the left of, the resource
panel on DP-3. It shares the existing Quickshell instance, startup command, and
visibility toggle. It is a non-focusable bottom-layer surface, so tiled and
fullscreen applications cover it. No Hyprland configuration changes or new
packages are required for weather.

The card is 589 px wide and about 520 px tall on the current display, with a
20 px gap from the resource panel. In `Style.qml`, use `weatherGap` to change the
gap, `weatherOpacity` (default `0.80`) for background transparency, and
`weatherSeparator` (`#405347`) for borders/separators. It uses `surface` (`#1B261F`),
`sage` and `ivory` from the shared palette. `widthFraction`, `monitor` and
`topMargin` apply to both panels; height follows weather content automatically.

`weather.py` uses Python's standard library and the Open-Meteo forecast endpoint
for 40.7128, -74.0060 with `America/New_York`, native Fahrenheit temperatures and
mph wind. Today shows the daily high/low and maximum daily precipitation
probability; the three forecast cards cover **tomorrow and the following two
days**. Weather codes map to restrained monochrome symbols. The update timestamp
is the last successful retrieval, formatted in NYC time with the correct EDT/EST
suffix, rather than the time of the most recent failed attempt. Data is provided
by [Open-Meteo](https://open-meteo.com/en/docs); the public non-commercial endpoint
requires no API key.

One persistent weather process refreshes every **900 seconds**, independently of
the two-second resource collector and UI redraws. It atomically stores the last
successful raw response and attempt time at
`${XDG_CACHE_HOME:-~/.cache}/evergreen-weather/nyc.json`. This is generated runtime
state, not a dotfile to commit. Fresh cache is shown immediately on startup;
shell reloads honor the saved cooldown. Failed requests show an unobtrusive
`OFFLINE · CACHED` status, keep the last successful data/time, and retry after
15 minutes. Without any cache, the card shows an offline/unavailable state rather
than invented values. Bad JSON, mismatched units and incomplete forecasts cannot
replace a good response. Old forecast dates are never relabeled as new dates.
Requests time out after 15 seconds. No Internet connectivity is changed to test
failure handling.

Weather diagnostics:

```sh
qs -c evergreen ipc call dashboard weatherStatus
python3 ~/.config/quickshell/evergreen/weather.py --once
python3 ~/.config/quickshell/evergreen/weather.py --offline
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -p test_weather.py -v
```

The `--offline` option makes no API request and reads cached data only. `--once`
respects the 15-minute cooldown too. `--cache /tmp/weather-test.json` isolates
validation state from the live feed. Tests cover failed networking with and
without cache, corrupt responses, rate limiting across restarts, dates around UTC
midnight, and DST. Live imperial and metric API responses were compared to verify
Celsius-to-Fahrenheit and km/h-to-mph conversions within rounding precision.
