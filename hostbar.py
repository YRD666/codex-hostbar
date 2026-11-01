#!/usr/bin/env python3
"""Codex Hostbar: two adjacent status rows in an isolated tmux session."""
import argparse
import os
from pathlib import Path
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import unicodedata

VERSION = '0.1.2'
NONINTERACTIVE = {
    'exec', 'e', 'review', 'login', 'logout', 'mcp', 'plugin', 'app-server',
    'remote-control', 'completion', 'update', 'doctor', 'sandbox', 'debug',
    'apply', 'a', 'queue', 'archive', 'delete', 'migrate-rollouts',
    'migrate-nfs-db', 'unarchive', 'cloud', 'exec-server', 'features', 'help',
}


def cells(text):
    """Terminal cells for ordinary text; complex emoji sequences are approximate."""
    return sum(0 if unicodedata.combining(c) else
               2 if unicodedata.east_asian_width(c) in ('W', 'F') else 1
               for c in text)


def fit(text, width):
    width = max(0, width)
    if cells(text) <= width:
        return text
    out, used = [], 0
    for char in text:
        size = cells(char)
        if used + size > width - 1:
            break
        out.append(char)
        used += size
    return ''.join(out) + '…' if width else ''


def safe_text(text):
    return ''.join(c for c in text if unicodedata.category(c)[0] != 'C')


def tmux_text(text):
    return safe_text(text).replace('#', '##')


def combine(rows, width):
    """Recognize only the fullscreen chat footer; unknown screens stay visible."""
    if len(rows) < 2:
        return None
    status, hints = (safe_text(line).strip() for line in rows[-2:])
    native_status = r'GPT-|gpt-|\bContext\b|\bweekly\b|\btokens\b|\bused\b'
    native_hints = r'for agents|for shortcuts|⚠\s*\d+\s+warnings?\b|esc to interrupt'
    if not status or not re.search(native_status, status):
        return None
    if re.search(native_hints, hints):
        pass
    elif not hints and any(re.match(r'^\s*›(?:\s|$)', line) for line in rows[:-2]):
        # Codex hides the hint row while the composer contains text. The blank
        # final row plus a nearby composer prompt distinguishes that state from
        # an arbitrary status-like line on an unknown screen.
        hints = ''
    else:
        return None
    warning = re.search(r'⚠\s*\d+\s+warnings?', hints)
    right = warning.group() + ' · f2' if warning else ''
    if right and cells(right) + 2 >= width:
        return fit(right, width)
    left = status
    if 'for agents' in hints and cells(left + ' · ← agents  ' + right) <= width:
        left += ' · ← agents'
    if right:
        return fit(left, width - cells(right) - 2) + '  ' + right
    return fit(left, width)


def compact_host(text, width):
    text = safe_text(text).strip()
    if cells(text) <= width:
        return text
    text = text.replace(' GiB', 'G')
    for label in ('内存', '根盘', '数据盘', 'RAM', 'Root', 'Data'):
        text = text.replace(label + ' ', label)
    if cells(text) <= width:
        return text
    text = text.replace('根盘', '根').replace('数据盘', '数据').replace(' | ', '|')
    return fit(text, width)


def memory_usage(path=Path('/proc/meminfo')):
    try:
        values = {line.split(':')[0]: int(line.split()[1])
                  for line in path.read_text().splitlines()}
        total, available = values['MemTotal'], values['MemAvailable']
        used = total - available
        return used / 1048576, total / 1048576, 100 * used / total
    except (OSError, KeyError, ValueError, IndexError, ZeroDivisionError):
        return None


def disk_text(label, path):
    try:
        st = os.statvfs(path)
        used = st.f_blocks - st.f_bfree
        # Match df: percentage excludes blocks reserved for the superuser.
        denominator = used + st.f_bavail
        percent = (100 * used + denominator - 1) // denominator if denominator else 0
        return f'{label} {used * st.f_frsize / 2**30:.1f}/{st.f_blocks * st.f_frsize / 2**30:.1f} GiB {percent}%'
    except OSError:
        return f'{label} N/A'


def host_text():
    zh = os.environ.get('CODEX_HOSTBAR_LANGUAGE', 'zh') == 'zh'
    ram, root, data = ('内存', '根盘', '数据盘') if zh else ('RAM', 'Root', 'Data')
    label = safe_text(os.environ.get('CODEX_HOSTBAR_LABEL', socket.gethostname()))
    memory = memory_usage()
    mem = (f'{ram} {memory[0]:.1f}/{memory[1]:.1f} GiB {memory[2]:.0f}%'
           if memory else f'{ram} N/A')
    parts = [label, mem, disk_text(root, '/')]
    data_path = os.environ.get('CODEX_HOSTBAR_DATA_PATH')
    if data_path is None and os.path.ismount('/srv'):
        data_path = '/srv'
    if data_path:
        parts.append(disk_text(data, data_path))
    return ' | '.join(parts)


def tmux(sock, *args):
    return subprocess.check_output(['tmux', '-S', sock, *args], text=True,
                                   stderr=subprocess.DEVNULL, timeout=2)


def render_footer(args):
    sock, pane, height, width = args
    height, width = int(height), int(width)
    state = tmux(sock, 'display-message', '-p', '-t', pane,
                 '#{pane_height} #{pane_width} #{pane_in_mode}').split()
    pane_height, pane_width, in_mode = map(int, state)
    rows = tmux(sock, 'capture-pane', '-p', '-t', pane,
                '-S', str(max(0, pane_height - 12))).splitlines()
    header = None
    if not in_mode and height >= 10 and width >= 35:
        header = combine(rows, width - 2)
    desired = max(1, height if header is not None else height - 2)
    if (pane_height, pane_width) != (desired, width):
        tmux(sock, 'resize-window', '-t', pane, '-x', str(max(1, width)), '-y', str(desired))
    return ' ' + tmux_text(header if header is not None else fit('Codex', width - 1))


def tmux_config():
    # Paths are expanded from quoted environment variables by the status shell.
    # They are never interpolated as shell code or tmux format strings.
    return '''set -g status 2
set -g status-position bottom
set -g status-interval 1
set -g status-style 'fg=white,bg=default,nobold'
set -g pane-colours[179] white
set -g status-left ''
set -g status-right ''
set -g status-format[0] '#("$CODEX_HOSTBAR_PYTHON" "$CODEX_HOSTBAR_SCRIPT" --internal-footer "#{socket_path}" "#{pane_id}" "#{client_height}" "#{client_width}")'
set -g status-format[1] '#("$CODEX_HOSTBAR_PYTHON" "$CODEX_HOSTBAR_SCRIPT" --internal-host "#{client_width}")'
set -g history-limit 50000
set -g mouse off
set -g default-terminal 'tmux-256color'
set -g allow-rename off
set -g set-titles off
set -g destroy-unattached on
set -g detach-on-destroy on
set -as terminal-overrides ',xterm*:smcup@:rmcup@'
bind -n S-PageUp send-keys C-t
bind -n C-z detach-client
bind -T copy-mode q send-keys -X cancel
bind -T copy-mode-vi q send-keys -X cancel
'''


def interactive_args(args):
    return not (args and (args[0] in NONINTERACTIVE or
                         args[0] in ('-h', '--help', '-V', '--version')))


def launch(args):
    parser = argparse.ArgumentParser(description=__doc__,
        epilog='Pass Codex arguments after --. Example: codex-hostbar -- resume --last')
    parser.add_argument('--version', action='version', version=VERSION)
    parser.add_argument('--codex', default=os.environ.get('CODEX_HOSTBAR_CODEX', 'codex'),
                        help='Codex executable or existing wrapper (default: codex on PATH)')
    parser.add_argument('--host-label', default=os.environ.get('CODEX_HOSTBAR_LABEL'))
    parser.add_argument('--data-path', default=os.environ.get('CODEX_HOSTBAR_DATA_PATH'),
                        help='Data filesystem path; empty string hides it')
    parser.add_argument('--language', choices=('zh', 'en'),
                        default=os.environ.get('CODEX_HOSTBAR_LANGUAGE', 'zh'))
    parser.add_argument('codex_args', nargs=argparse.REMAINDER)
    options = parser.parse_args(args)
    forwarded = options.codex_args
    if forwarded[:1] == ['--']:
        forwarded = forwarded[1:]
    executable = shutil.which(options.codex)
    if not executable:
        parser.error('Codex executable not found; set --codex /path/to/codex')
    if Path(executable).resolve() == Path(__file__).resolve():
        parser.error('--codex resolves to Hostbar itself; select the original Codex executable')
    enabled = (os.environ.get('CODEX_HOSTBAR', '1') != '0' and
               sys.stdin.isatty() and sys.stdout.isatty() and
               not os.environ.get('TMUX') and os.environ.get('TERM', 'dumb') != 'dumb' and
               interactive_args(forwarded))
    if not enabled:
        os.execv(executable, [executable, *forwarded])
    if sys.platform != 'linux':
        parser.error('Hostbar currently supports Linux only; use Codex directly on other systems')
    if not shutil.which('tmux'):
        parser.error('tmux >= 3.4 is required for interactive Hostbar')
    version = subprocess.check_output(['tmux', '-V'], text=True)
    match = re.search(r'(\d+)\.(\d+)', version)
    if not match or tuple(map(int, match.groups())) < (3, 4):
        parser.error('tmux >= 3.4 is required')
    env = os.environ.copy()
    env['CODEX_HOSTBAR_SCRIPT'] = str(Path(__file__).resolve())
    env['CODEX_HOSTBAR_PYTHON'] = sys.executable
    env['CODEX_HOSTBAR_LANGUAGE'] = options.language
    for key, value in [('CODEX_HOSTBAR_LABEL', options.host_label),
                       ('CODEX_HOSTBAR_DATA_PATH', options.data_path)]:
        if value is not None:
            env[key] = value
    overrides = ['-c', 'tui.fullscreen_transcript=true',
                 '-c', 'tui.alternate_screen="always"',
                 '-c', 'tui.raw_output_mode=false',
                 '-c', 'tui.status_line_use_colors=false',
                 '-c', 'tui.theme="github"',
                 '-c', 'tui.status_line=["model-with-reasoning","weekly-limit","context-remaining","used-tokens"]']
    # Private socket and config disappear after this client's session ends.
    with tempfile.TemporaryDirectory(prefix=f'codex-hostbar-{os.getuid()}-', dir='/tmp') as tmp:
        config = Path(tmp) / 'tmux.conf'
        config.write_text(tmux_config())
        sock = str(Path(tmp) / 'tmux.sock')
        command = ['tmux', '-u', '-S', sock, '-f', str(config), 'new-session',
                   '-s', 'codex', '-n', 'codex', '-c', os.getcwd(), '--',
                   executable, *overrides, *forwarded]
        try:
            return subprocess.call(command, env=env)
        finally:
            # This is only our private server, including interrupted launches.
            subprocess.run(['tmux', '-S', sock, 'kill-server'],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def main():
    args = sys.argv[1:]
    if args[:1] in (['--internal-footer'], ['--internal-host']):
        try:
            if args[0] == '--internal-host':
                print(' ' + tmux_text(compact_host(host_text(), max(0, int(args[1]) - 1))))
            else:
                print(render_footer(args[1:]))
            return 0
        except (ValueError, IndexError, OSError, subprocess.SubprocessError):
            print(' Codex · status temporarily unavailable')
            return 0
    return launch(args)


if __name__ == '__main__':
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(130)
