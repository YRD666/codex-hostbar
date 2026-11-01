# Changelog

## 0.1.4

- Keep the composer footer folded while selection or scrollback navigation hints
  replace the normal shortcuts. Preserve those hints in the outer status row.
- Cover typed input with a retained selection in the terminal regression test.

## 0.1.3

- Keep mouse support enabled in the private tmux server so Codex captures wheel
  events and scrolls fullscreen conversation history.
- Add PTY regression coverage for Codex's tmux mouse probe and wheel delivery.

## 0.1.2

- Make `Shift+PageUp` open Codex's native Transcript view so earlier
  conversation content remains reachable in fullscreen mode.
- Add terminal regression coverage for the Transcript shortcut and viewport.

## 0.1.1

- Keep the two-row layout while the composer contains text and Codex hides its
  native shortcut row.
- Add regression coverage for typed input while preserving unknown-screen and
  warning-panel viewport protection.

## 0.1.0

- Two adjacent rows for Codex status and Linux host metrics.
- White status text, warning priority and width-aware compact labels.
- Full viewport restoration for unknown panels and copy mode.
- Private tmux sessions, configurable labels and data filesystem paths.
- User-local installation and hash-checked uninstallation.
- Chinese and English documentation; standard-library tests and CI.
