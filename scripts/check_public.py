#!/usr/bin/env python3
"""Heuristic public-source guard. Reports locations, never matched secret values."""
import ipaddress
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
PATTERNS = {
    'private key': re.compile(r'-----BEGIN [A-Z ]*PRIVATE KEY-----'),
    'GitHub token': re.compile(r'\b(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{30,})'),
    'API key': re.compile(r'\bsk-[A-Za-z0-9_-]{20,}'),
    'AWS access key': re.compile(r'\b(?:AKIA|ASIA)[A-Z0-9]{16}\b'),
    'SSH public key': re.compile(r'\bssh-(?:rsa|ed25519)\s+[A-Za-z0-9+/]{40,}'),
    'credential URL': re.compile(r'https?://[^\s/:]+:[^\s/@]+@'),
    'JWT': re.compile(r'\beyJ[A-Za-z0-9_-]{15,}\.[A-Za-z0-9_-]{15,}\.[A-Za-z0-9_-]{15,}'),
}
IPV4 = re.compile(r'(?<![\d.])(?:\d{1,3}\.){3}\d{1,3}(?![\d.])')
EXCLUDED = {'.git', '__pycache__', '.venv', 'dist'}


def check_text(text):
    findings = [name for name, pattern in PATTERNS.items() if pattern.search(text)]
    for value in IPV4.findall(text):
        try:
            address = ipaddress.ip_address(value)
            if not (address.is_loopback or address.is_unspecified):
                findings.append('literal IP address (review for host leakage)')
                break
        except ValueError:
            pass
    return findings


def check_path(path):
    name = Path(path).name
    return (name.startswith('.env') or name in ('auth.json', 'config.toml', 'known_hosts')
            or name.endswith(('.pem', '.key', '.log'))
            or any(part in ('.ssh', '.codex') for part in Path(path).parts))


def git(*args):
    return subprocess.check_output(['git', '-C', str(ROOT), *args], stderr=subprocess.DEVNULL)


def main():
    errors = []
    count = 0
    for path in sorted(ROOT.rglob('*')):
        relative = path.relative_to(ROOT)
        if any(part in EXCLUDED for part in relative.parts):
            continue
        if path.is_symlink():
            errors.append(f'{relative}: symlink requires manual review')
        elif path.is_file():
            count += 1
            if check_path(relative):
                errors.append(f'{relative}: sensitive filename')
            for finding in check_text(path.read_text(errors='replace')):
                errors.append(f'{relative}: {finding}')
    objects = 0
    try:
        history = git('rev-list', '--objects', '--all').decode().splitlines()
    except subprocess.CalledProcessError:
        history = []
    for entry in history:
        oid, _, path = entry.partition(' ')
        kind = git('cat-file', '-t', oid).strip()
        if kind in (b'blob', b'commit'):
            objects += 1
            if path and check_path(path):
                errors.append(f'history {oid[:12]}: sensitive filename')
            for finding in check_text(git('cat-file', '-p', oid).decode(errors='replace')):
                errors.append(f'history {oid[:12]} {path}: {finding}')
    if errors:
        print('\n'.join(errors), file=sys.stderr)
        return 1
    print(f'Public-source heuristic check passed: {count} files, {objects} history objects. Manual review still required.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
