#!/usr/bin/env python3
"""Install only the public Hostbar files; never modify Codex or shell config."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys

FILES = ('hostbar.py', 'README.md', 'README.en.md', 'LICENSE')
MARKER = 'INSTALL-MANIFEST.json'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prefix', type=Path, default=Path.home() / '.local')
    parser.add_argument('--uninstall', action='store_true')
    options = parser.parse_args()
    prefix = options.prefix.expanduser().absolute()
    target = prefix / 'share/codex-hostbar'
    command = prefix / 'bin/codex-hostbar'
    source = Path(__file__).resolve().parent
    if options.uninstall:
        if target.is_symlink() or not (target / MARKER).is_file():
            parser.error('No owned Hostbar installation at this prefix')
        manifest = json.loads((target / MARKER).read_text())
        if set(manifest) != set(FILES):
            parser.error('Unexpected install manifest; nothing removed')
        if not command.is_symlink() or os.readlink(command) != str(target / 'hostbar.py'):
            parser.error('Launcher was changed; nothing removed')
        for name, expected in manifest.items():
            path = target / name
            if path.is_symlink() or not path.is_file() or digest(path) != expected:
                parser.error(f'{name} was changed; nothing removed')
        command.unlink()
        for name in (*FILES, MARKER):
            (target / name).unlink()
        if not any(target.iterdir()):
            target.rmdir()
        print('Removed Hostbar. Original Codex and configuration were not modified.')
        return
    if target.exists() or target.is_symlink() or command.exists() or command.is_symlink():
        parser.error('Install destination exists; use a different prefix or uninstall first')
    for name in FILES:
        if not (source / name).is_file():
            parser.error(f'Missing release file: {name}')
    target.mkdir(parents=True)
    command.parent.mkdir(parents=True, exist_ok=True)
    try:
        for name in FILES:
            shutil.copyfile(source / name, target / name)
        (target / 'hostbar.py').chmod(0o755)
        manifest = {name: digest(target / name) for name in FILES}
        (target / MARKER).write_text(json.dumps(manifest, indent=2) + '\n')
        command.symlink_to(target / 'hostbar.py')
    except OSError:
        for name in (*FILES, MARKER):
            (target / name).unlink(missing_ok=True)
        target.rmdir()
        raise
    print(f'Installed: {command}\nRun this path directly, or add {command.parent} to PATH.')


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError) as error:
        print(f'Hostbar installation failed: {error}', file=sys.stderr)
        sys.exit(1)
