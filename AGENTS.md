# Project guidance

## Environment and repository

This repository manages an Arch Linux desktop with Git and GNU Stow.
The machine uses Hyprland on an AMD Ryzen 7950X3D with an NVIDIA RTX 3060 Ti.
Hyprland configuration is written in Lua; preserve that format and the existing
`hl` API conventions rather than converting it to Hyprlang.

The current tracked configuration is `hypr/.config/hypr/hyprland.lua`.
`hypr` is a Stow package whose contents mirror paths under the home directory.
The other components below are intended additions, not configurations already
present in this repository. The current launcher command is `hyprlauncher`;
moving to Fuzzel must preserve the existing launcher shortcut.

## Design direction

Build a minimalist, dark evergreen desktop inspired by e-ink Linux rices and
Pacific Northwest forests. Favor typography, readable contrast, restrained
spacing, and quiet surfaces. Keep animations subtle and window borders modest.
Avoid visual clutter, bright accents, and excessive effects.

Use this shared palette across components, adapting color syntax to each tool:

| Role | Color |
| --- | --- |
| Background | `#101713` |
| Panel | `#1B261F` |
| Raised surface | `#29352C` |
| Evergreen | `#547660` |
| Sage | `#9AAE94` |
| Ivory | `#E2E3D8` |

## Intended components

- **Hyprland Lua:** window management, restrained borders, and subtle animations.
- **Waybar:** CPU, RAM, GPU, network, audio, clock, and workspaces. Keep monitoring
  compact; use NVIDIA-compatible GPU metrics without altering driver settings.
- **btop:** detailed system monitoring outside the bar.
- **hyprpaper:** a dark evergreen forest wallpaper.
- **Kitty and Fuzzel:** matching terminal and launcher themes.
- **SwayNC:** notifications styled with the same palette and typography.

## Safety and compatibility

- Preserve all existing working keybindings, including workspace, mouse, media,
  and audio bindings. Check indirect command changes as well as binding lines;
  do not remove or remap shortcuts without an explicit request.
- Never break NVIDIA, bootloader, or network settings. Desktop styling does not
  authorize changes to drivers, kernel parameters, initramfs, boot configuration,
  networking services, or existing hardware workarounds. Keep those outside the
  scope of routine theme work.
- Keep dotfiles compatible with GNU Stow. Put new component files in separate
  top-level packages that mirror their home-relative destinations, for example
  `waybar/.config/waybar/`. Keep this root guidance file outside deployed packages.
- Do not overwrite live configuration or resolve Stow conflicts by deleting
  existing files. Inspect destinations and dry-run Stow before applying links.
- Keep machine-specific paths and generated state out of reusable configuration
  where practical. Do not commit credentials or unrelated local changes.

## Change and validation workflow

1. Inspect the relevant files and `git status` before editing. Preserve unrelated
   work and make small, incremental changes scoped to the request.
2. Follow installed component versions and existing conventions. Verify supported
   settings before introducing them, especially Hyprland Lua APIs.
3. Review and show Git diffs for each change, including new files. Explain the
   effect on appearance or behavior and identify any keybinding implications.
4. Validate configurations before committing. Use available component-specific
   syntax checks, parsers, and dry runs; Lua syntax checking alone does not
   validate Hyprland's runtime API. Check Stow layout and conflicts with a dry run
   such as `stow --simulate --verbose --target="$HOME" hypr` from this repository
   for the affected package, and run `git diff --check`.
5. When runtime validation is needed, use a controlled reload and inspect errors
   while preserving a recovery path. Do not restart the desktop or critical
   services merely to validate a theme. Report unavailable checks and unresolved
   errors clearly; do not claim validation passed if it was not performed.
6. Commit only when requested, after relevant checks pass and the diff has been
   reviewed. Report what changed, checks performed, and any remaining limitations.
