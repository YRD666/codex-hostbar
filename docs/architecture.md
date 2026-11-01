# Implementation

`hostbar.py` uses only the Python standard library and the system tmux command.
It can run directly or via the installer-created symlink. It never replaces the
Codex binary. Per-launch display overrides enable the fullscreen layout.

## Viewport

The native fullscreen Codex composer has two footer rows. Hostbar reserves two
tmux status rows and reads the last two pane rows each second. When these match
the supported native footer, it sets the window height to the client height.
The two native rows then extend below the visible pane area, while the composer
stays above them. Hostbar combines their information in its first status row.
The second row is generated from `/proc/meminfo` and `statvfs`.

If the footer is unrecognized, a menu opens, copy mode is active, or the terminal
is too small, the window height returns to client height minus two. Unknown
screens are not intentionally cropped. A resize can take one refresh cycle to
settle. This adapter depends on upstream layout details and is deliberately
limited to known text patterns; it is not a general-purpose screen parser.

## Isolation and data

Each launch creates a mode-0700 temporary directory under `/tmp`, containing its
private tmux socket and generated config. No global tmux server is changed.
The launcher removes its own private server and temporary directory on normal
exit, including Ctrl+Z detach. Abrupt SIGKILL cannot guarantee cleanup. A private
tmux history buffer exists in memory while the session runs; Hostbar does not
write pane captures or chat history to disk. Codex may retain its own history.

Executable and prompt arguments are passed as an argv list, never concatenated
into a shell command. Status helper paths are expanded from quoted environment
variables. Status output strips control characters and escapes tmux `#` markers.
No auth files are read. The inherited environment remains available to the
original Codex executable, including any existing proxy setup.

## Installation boundary

`install.py` copies four allowlisted files, records their hashes, and creates one
new command. It refuses to overwrite existing destinations. The uninstall path
validates every owned file before deleting anything and preserves unknown files.
No shell startup file, network service, package manager, or Codex setting is edited.

## Verification

Unit tests cover width limits, Chinese text, warning priority, inline/menu
rejection, metrics, argument preservation and safe install/uninstall behavior.
The tmux integration test launches a deterministic simulated fullscreen program
in a real pseudo-terminal, resizes it, opens a mock dialog, enters copy mode and
exits with Ctrl+Z. Real Codex compatibility must also be checked manually for
each newly supported version.
