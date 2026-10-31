import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class InstallTests(unittest.TestCase):
    def run_installer(self, prefix, *args):
        return subprocess.run([sys.executable, str(ROOT / 'install.py'),
                               '--prefix', str(prefix), *args], capture_output=True, text=True)

    def test_install_passthrough_and_uninstall_with_special_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            prefix = Path(tmp) / "a ' space $and#chars"
            result = self.run_installer(prefix)
            self.assertEqual(result.returncode, 0, result.stderr)
            command = prefix / 'bin/codex-hostbar'
            fake = Path(tmp) / 'fake codex'
            fake.write_text('#!/usr/bin/env python3\nimport sys,json\nprint(json.dumps(sys.argv[1:]))\n')
            fake.chmod(0o755)
            args = ['exec', 'a b', '$(do-not-execute)', '#{host}', "'quoted'"]
            output = subprocess.check_output([str(command), '--codex', str(fake), '--', *args], text=True)
            self.assertEqual(json.loads(output), args)
            self.assertEqual(self.run_installer(prefix, '--uninstall').returncode, 0)
            self.assertFalse(command.exists())
            self.assertFalse((prefix / 'share/codex-hostbar').exists())

    def test_does_not_replace_existing_command(self):
        with tempfile.TemporaryDirectory() as tmp:
            prefix = Path(tmp)
            (prefix / 'bin').mkdir()
            command = prefix / 'bin/codex-hostbar'
            command.write_text('keep me')
            self.assertNotEqual(self.run_installer(prefix).returncode, 0)
            self.assertEqual(command.read_text(), 'keep me')

    def test_modified_install_is_preserved(self):
        with tempfile.TemporaryDirectory() as tmp:
            prefix = Path(tmp)
            self.assertEqual(self.run_installer(prefix).returncode, 0)
            installed = prefix / 'share/codex-hostbar/hostbar.py'
            installed.write_text('user changed this')
            self.assertNotEqual(self.run_installer(prefix, '--uninstall').returncode, 0)
            self.assertTrue(installed.exists())

    def test_recursive_launch_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            prefix = Path(tmp)
            self.assertEqual(self.run_installer(prefix).returncode, 0)
            command = prefix / 'bin/codex-hostbar'
            result = subprocess.run([str(command), '--codex', str(command)], capture_output=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn(b'Hostbar itself', result.stderr)


if __name__ == '__main__':
    unittest.main()
