# Evergreen system dashboard

Quickshell 0.3.2 on Hyprland 0.56.2, using the installed Lua `hl` API.
The existing system and NYC weather collectors remain in the same instance.
No packages, drivers, display modes, or service settings were changed.

## Layout and monitor selection

Hyprland has no primary-monitor flag. Both configurations sort connected screens
by logical x, then y, then name: the leftmost/topmost is primary, the next is the
secondary dashboard. This matches the existing side-by-side layout (the old
widget configuration selected DP-3; logs identify HDMI-A-3 and DP-3 as connected).
Live monitor coordinates could not be queried from the sandbox, so confirm this
convention with `hyprctl monitors`. One attached screen means no dashboard or
reserved area; reconnection recreates them automatically.

Only the secondary has a right-side layer-shell exclusive zone. Dwindle tiles
any number of normal application windows in its remaining left half; the primary
keeps its original full work area (apart from existing Waybar and gaps).
Weather and system cards sit beside each other entirely within the reservation.
Both use the top layer and accept no keyboard focus. Opening, closing, moving,
or switching workspaces does not remove the widgets.

The invisible reservation surface is input-transparent and remains mapped when
**Super+Shift+M** hides the cards. The collectors continue while hidden. If the
whole Quickshell process stops or crashes, its reservation disappears too; run
the existing startup script to restore it.

## Apply and startup

The existing `hyprland.start` callback starts `dashboard.sh start` on login.
The script's lock, IPC check and `--no-duplicate` protect against duplicate
instances. Hyprland reloads do not rerun the startup event; Quickshell watches its
QML files and reloads them automatically. Run from a terminal inside Hyprland:

```sh
Hyprland --verify-config -c "$HOME/.config/hypr/hyprland.lua" && hyprctl reload
hyprctl configerrors
sh ~/.config/quickshell/evergreen/dashboard.sh start
hyprctl monitors
hyprctl binds
qs -c evergreen ipc call dashboard status
```

## Keyboard reference

All shortcuts below include Super.

| Keys after Super | Action |
| --- | --- |
| Enter | Terminal |
| Q (also C) | Close focused window |
| F | Toggle true fullscreen |
| Shift+F | Toggle maximize within work area, retaining dashboard space |
| V | Toggle floating |
| H / J / K / L | Focus left / down / up / right |
| Shift+H / J / K / L | Move window left / down / up / right |
| Ctrl+Left / Right | Send window to adjacent monitor |
| 1–9 (also 0 for 10) | Switch workspace |
| Shift+1–9 (also 0) | Send window to workspace |
| R | Existing application launcher |
| Left / right mouse drag | Move / resize window |
| Ctrl+Enter | Launch a new terminal directly on secondary |
| Ctrl+R | Focus secondary, then open application launcher |
| Alt+H / L | Focus left / right monitor |
| Ctrl+J | Toggle dwindle split (formerly Super+J) |
| Shift+M | Hide/show dashboard cards, retaining reservation |

Existing arrows, file manager, scratchpad, pseudo, workspace scroll, media, audio,
brightness, and session-exit bindings remain. H/L and Shift+H/L previously used
monitor focus/movement; their new actions follow the requested spatial shortcuts.
Monitor movement is now Ctrl+Left/Right, explicit focus is Alt+H/L.

The launcher starts on the secondary with Ctrl+R, and newly started applications
normally follow its focused workspace. Apps that reuse an existing window or
have their own placement rules may stay elsewhere; use Ctrl+Left/Right for these.
Ctrl+Enter applies an explicit monitor rule to the new terminal.

## Width and limitations

Edit `widgetAreaFraction` in `~/.config/quickshell/evergreen/Style.qml`:
`0.50` reserves 50%; `0.40` reserves 40% and leaves 60% for applications.
Both card widths and the exclusive zone update together on QML reload. Geometry
uses logical pixels, so monitor scaling is accounted for. Very small widths may
make card contents cramped. Colors, margins and typography remain in Style.qml.

True fullscreen (**Super+F**, browser F11, fullscreen video/games) can ignore
exclusive zones and cover the widgets. **Super+Shift+F** uses maximized mode and
is the dashboard-preserving alternative. Floating windows can also extend into
the reserved area; top-layer cards render above ordinary floating windows.
Exclusive zones constrain normal tiling, not arbitrary fullscreen/floating
geometry. The primary monitor retains ordinary fullscreen behavior.

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
hyprctl monitors -j
hyprctl layers
hyprctl binds
hyprctl configerrors
qs -c evergreen ipc call dashboard status
qs -c evergreen ipc call dashboard weatherStatus
cat "$XDG_RUNTIME_DIR/evergreen-dashboard.log"
```

For this change, Hyprland's `--verify-config`, Lua syntax, QML lint, Stow dry-run
and `git diff --check` passed. The existing dashboard log reported configuration
reload and load success after editing. Sandbox access to Hyprland and Quickshell
IPC was denied, so reload, runtime bindings, window movement, actual reserved
geometry, widget visibility, process counts and reboot behavior were not tested.
No logout/reboot or duplicate shell instance was used for validation.

After applying from the desktop terminal, check the secondary's right reservation
is half its logical width in `hyprctl monitors`; the primary should have no new
right reservation. Launch two terminals on the secondary with Ctrl+Enter and
check both tile within its left half. Move one between monitors with
Ctrl+Left/Right, switch workspaces, close it, and toggle the cards with Shift+M:
the reserved work area should stay unchanged. Verify weather/metrics update.
Confirm the same behavior after the next normal login.

Backups of all four edited files, including preexisting uncommitted changes,
are in `~/.local/state/hypr-dashboard-backups/20261030-003904/`.
Run `sh ~/.local/state/hypr-dashboard-backups/20261030-003904/rollback.sh`
from a desktop terminal (or a TTY) to restore those exact files. The script reloads
Hyprland when available; from a TTY, log in again to load the restored settings.
Quickshell reloads restored QML automatically. Nothing was committed.

References: [Quickshell PanelWindow](https://quickshell.org/docs/v0.3.2/types/Quickshell/PanelWindow/),
[Wayland layers](https://quickshell.org/docs/v0.3.2/types/Quickshell.Wayland/WlrLayershell/),
and [IPC handlers](https://quickshell.org/docs/v0.3.2/types/Quickshell.Io/IpcHandler/).

## NYC weather card

A compact, top-aligned weather card sits **beside**, to the left of, the resource
panel on the secondary monitor. It shares the existing Quickshell instance, startup command, and
visibility toggle. It is a non-focusable top-layer surface inside the shared
exclusive zone; true fullscreen can cover it. No new packages are required.

At 2560 logical pixels and a 50% reservation, each card is 610 px wide, with a
20 px gap from the resource panel. In `Style.qml`, use `weatherGap` to change the
gap, `weatherOpacity` (default `0.80`) for background transparency, and
`weatherSeparator` (`#405347`) for borders/separators. It uses `surface` (`#1B261F`),
`sage` and `ivory` from the shared palette. `widgetAreaFraction` and `topMargin` apply to both cards; monitor selection is
automatic and weather height follows its content.

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
