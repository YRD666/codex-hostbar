# Codex Hostbar

[中文说明](README.md)

Keep Codex status and Linux host metrics on **two adjacent terminal rows**.
The first row combines the model, quota, context, token usage and warning count
reported by Codex. The second shows memory, root filesystem and optional data
filesystem usage. Text is compacted to fit narrower terminals.

Independent community project, not affiliated with OpenAI. Codex is installed
and authenticated separately; no Codex binaries or credentials are distributed.

## Install and run

Requires Linux, Python 3.10+, tmux 3.4+, a UTF-8 terminal and working Codex CLI.
Live compatibility checked with Codex 0.166.0, Ubuntu 24.04, Python 3.12 and
tmux 3.4. Other Codex versions have not been individually verified.

```bash
git clone https://github.com/YRD666/codex-hostbar.git
cd codex-hostbar
python3 install.py
~/.local/bin/codex-hostbar --language en
```

The installer needs no root privileges or network access. It installs a separate
command under `~/.local/bin` and leaves the original `codex` command available.
It refuses existing destinations. You may also run `python3 hostbar.py` directly.

```bash
codex-hostbar --host-label demo-server --data-path /mnt/data --language en
codex-hostbar --codex /path/to/original/codex
codex-hostbar -- resume --last
codex-hostbar -- -m your-model
codex-hostbar -- exec 'Explain this repository'
```

Put Codex arguments after `--`. Noninteractive subcommands must come first,
followed by their options. Data usage describes the filesystem containing the
selected path. By default, `/srv` is shown only when it is a mount point;
`--data-path ''` hides it. `CODEX_HOSTBAR_CODEX`, `CODEX_HOSTBAR_LABEL`,
`CODEX_HOSTBAR_DATA_PATH` and `CODEX_HOSTBAR_LANGUAGE` provide matching defaults.

## Behavior and limitations

- A private tmux server folds recognized native fullscreen footer rows into one.
  Unknown screens and warning panels regain the normal viewport on
  the next refresh (approximately one second). The external title becomes `Codex`.
- Supports the English footer text structure observed in Codex 0.166.0. Upstream
  changes may produce extra native rows. This is not an upstream rendering API.
- Use at least 80 columns for useful detail. Narrow screens truncate values;
  fewer than 35 columns or 10 rows disables folding. Complex emoji widths are
  approximate.
- The mouse wheel scrolls Codex history directly; `PageUp` / `PageDown` also
  work. `Shift+PageUp` opens Codex Transcript, `Esc` returns, and `F2` opens
  the native warning panel.
- In older sessions without Codex mouse capture, tmux handles drag selection.
  Release keeps the selection; `Ctrl+C` or `Enter` copies, and `Esc` cancels.
  Status refreshes preserve the selection's window size.
- Copies are kept in the private tmux buffer and forwarded to the SSH client's
  clipboard using OSC 52. The client must support and allow clipboard writes;
  a successful server-side copy does not confirm desktop clipboard delivery.
  Use your terminal's paste action for desktop clipboard text. A raw `Ctrl+V`
  sent to Codex cannot read your computer's clipboard over SSH. tmux's default
  `Ctrl+B`, then `]` pastes its last copied buffer, which may differ from the
  desktop clipboard. Many terminals also support Shift+drag for local selection.
- **Ctrl+Z closes this private terminal session, not Unix suspend.** `fg` cannot
  restore it. Use `codex-hostbar -- resume --last` where appropriate. Hostbar
  does not explicitly stop the shared Codex daemon or other tmux sessions.
- Non-TTY, nested tmux, `TERM=dumb`, `CODEX_HOSTBAR=0` and known noninteractive
  commands pass through unchanged.
- Interactive launches provide per-process `-c` overrides for fullscreen,
  alternate screen, raw output off, status colors off, github theme and the
  model/weekly/context/usage status items. They do not edit Codex configuration.
  Display overrides passed after `--` may change the layout.
- Hostbar reads Linux metrics and the last two pane rows. It does not read Codex
  authentication files, change proxy settings or configure network services.
  Existing proxy environment variables and original Codex wrappers are retained.
- Outer status text is white. Codex status colors are disabled; the entire chat
  interface is not recolored.

## Uninstall and test

From the source checkout:

```bash
python3 install.py --uninstall
python3 -m unittest discover -s tests -v
python3 scripts/check_public.py
```

Use the same `--prefix /your/prefix` for custom installation and uninstallation.
Uninstallation checks file hashes and refuses to delete locally modified files.
To upgrade, close Hostbar sessions, uninstall the old version and install the new
one. Existing Codex configuration, binaries and history are preserved.

The test suite includes a simulated Codex PTY fixture requiring no API calls or
credentials; it does not establish compatibility with every real Codex version.
See [architecture](docs/architecture.md) and [release checks](docs/releasing.md).

Licensed under [MIT](LICENSE).
