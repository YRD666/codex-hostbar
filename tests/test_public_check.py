import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location('guard', Path(__file__).resolve().parents[1] / 'scripts/check_public.py')
guard = importlib.util.module_from_spec(spec)
spec.loader.exec_module(guard)


class PublicCheckTests(unittest.TestCase):
    def test_secret_patterns(self):
        for value in ('ghp_' + 'a' * 36, 'sk-' + 'b' * 32,
                      '-----BEGIN ' + 'OPENSSH PRIVATE KEY-----'):
            self.assertTrue(guard.check_text(value))

    def test_sensitive_paths(self):
        for path in ('.env', '.ssh/id_ed25519', '.codex/auth.json', 'backup/key.pem'):
            self.assertTrue(guard.check_path(path))
        self.assertFalse(guard.check_path('README.md'))

    def test_safe_examples(self):
        self.assertFalse(guard.check_text('demo-server · weekly 80% left · Python 3.12'))


if __name__ == '__main__':
    unittest.main()
