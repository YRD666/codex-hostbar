#!/usr/bin/env python3
"""Synthetic terminal fixture. Does not call Codex or any network service."""
import os
import select
import signal
import subprocess
import sys
import tty

dialog = False
draft = False
transcript = False
wheel_scrolled = False


def draw(*_):
    width, height = os.get_terminal_size()
    out = '\x1b[2J\x1b[HFixture chat'
    if wheel_scrolled:
        out += '\x1b[2;1HOLDER HISTORY FROM MOUSE WHEEL'
    elif transcript:
        out += '\x1b[2;1H/ T R A N S C R I P T'
        out += '\x1b[4;1HOlder transcript line'
    elif dialog:
        out += f'\x1b[{height};1Hk keep & next · esc dismiss & close'
    elif draft:
        out += f'\x1b[{height-3};1H› 你好'
        out += f'\x1b[{height-1};1HGPT-Example high · weekly 80% left · Context 99% left'
        out += f'\x1b[{height-3};7H'
    else:
        out += f'\x1b[{height-3};1H> Draft input'
        out += f'\x1b[{height-1};1HGPT-Example high · weekly 80% left · Context 100% left'
        out += f'\x1b[{height};1H← for agents · ? for shortcuts  ⚠ 2 warnings · f2 to view'
        out += f'\x1b[{height-3};3H'
    sys.stdout.write(out)
    sys.stdout.flush()


tty.setraw(sys.stdin.fileno())
signal.signal(signal.SIGWINCH, draw)
mouse = subprocess.check_output(
    ['tmux', 'display-message', '-p', '#{mouse}'], text=True
).strip()
if mouse not in ('0', 'off'):
    sys.stdout.write('\x1b[?1000h\x1b[?1006h')
    sys.stdout.flush()
draw()
while True:
    char = os.read(sys.stdin.fileno(), 1)
    if char == b'\x1b':
        while select.select([sys.stdin.fileno()], [], [], 0.02)[0]:
            char += os.read(sys.stdin.fileno(), 64)
    if not char or char == b'q':
        break
    if char.startswith(b'\x1b[<64;') and char.endswith(b'M'):
        wheel_scrolled = True
    if char == b'\x14':
        transcript = True
        dialog = False
        draft = False
    if char == b'\x1b' and transcript:
        transcript = False
    if char == b'd':
        dialog = True
    if char == b'c':
        dialog = False
        draft = False
        transcript = False
        wheel_scrolled = False
    if char == b'i':
        dialog = False
        draft = True
    draw()
