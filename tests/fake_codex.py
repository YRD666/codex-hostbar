#!/usr/bin/env python3
"""Synthetic terminal fixture. Does not call Codex or any network service."""
import os
import signal
import sys
import tty

dialog = False
draft = False


def draw(*_):
    width, height = os.get_terminal_size()
    out = '\x1b[2J\x1b[HFixture chat'
    if dialog:
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
draw()
while True:
    char = os.read(sys.stdin.fileno(), 1)
    if not char or char == b'q':
        break
    if char == b'd':
        dialog = True
    if char == b'c':
        dialog = False
        draft = False
    if char == b'i':
        dialog = False
        draft = True
    draw()
