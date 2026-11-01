import importlib.util
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('hostbar', ROOT / 'hostbar.py')
h = importlib.util.module_from_spec(spec)
spec.loader.exec_module(h)


class FooterTests(unittest.TestCase):
    rows = ['GPT-Example high · weekly 80% left · Context 100% left',
            '← for agents · ? for shortcuts    ⚠ 3 warnings · f2 to view']

    def test_two_rows_become_one(self):
        result = h.combine(self.rows, 100)
        for value in ('GPT-Example', 'weekly 80%', 'Context 100%', '3 warnings'):
            self.assertIn(value, result)
        self.assertNotIn('\n', result)
        self.assertNotIn('for shortcuts', result)

    def test_all_widths_are_bounded(self):
        for width in range(0, 160):
            with self.subTest(width=width):
                result = h.combine(self.rows, width)
                self.assertLessEqual(h.cells(result), width)

    def test_warning_has_priority(self):
        self.assertIn('3 warnings', h.combine(self.rows, 45))

    def test_unknown_dialog_and_inline_layout_are_preserved(self):
        for rows in (['Warning details', 'Esc to close'],
                     ['', 'k keep & next · esc dismiss & close · ^o copy'],
                     ['', 'GPT-Example high · ⚠ 2 warnings · f2 to view'],
                     ['Some chat content', '? for shortcuts']):
            self.assertIsNone(h.combine(rows, 100))

    def test_typed_composer_with_hidden_hint_row_is_folded(self):
        rows = ['› 你好', '',
                'GPT-Example high · weekly 80% left · Context 99% left · 10K used',
                '']
        result = h.combine(rows, 100)
        self.assertIsNotNone(result)
        self.assertIn('GPT-Example high', result)
        self.assertNotIn('Codex', result)

    def test_status_like_text_without_composer_is_not_folded(self):
        rows = ['unrelated screen', '',
                'GPT-Example high · weekly 80% left · Context 99% left', '']
        self.assertIsNone(h.combine(rows, 100))

    def test_draft_during_running_task_keeps_queue_hint_folded(self):
        for hints in ('tab to queue message', 'tab to queue'):
            rows = ['› 你好', '', self.rows[0], hints]
            result = h.combine(rows, 135)
            self.assertIsNotNone(result)
            self.assertIn('GPT-Example', result)
            self.assertIn(hints, result)
            for width in range(35, 136):
                self.assertLessEqual(h.cells(h.combine(rows, width)), width)
            self.assertIsNone(h.combine(['other screen', '', self.rows[0], hints], 135))

    def test_selection_and_scrollback_footer_keep_composer_folded(self):
        for hints in ('^c copy · enter copy & follow · esc clear',
                      'enter copy & follow · esc clear', 'esc clear',
                      'Earlier messages available.  esc latest',
                      'New activity · enter/esc latest',
                      'New activity · Earlier messages available.  enter/esc latest · ? shortcuts',
                      '↑ Loading earlier messages… · esc latest'):
            with self.subTest(hints=hints):
                rows = ['› draft', '', self.rows[0], hints]
                result = h.combine(rows, 180)
                self.assertIsNotNone(result)
                self.assertIn('GPT-Example', result)
                self.assertIn(hints, result)
                self.assertLessEqual(h.cells(result), 180)
                for width in (40, 80, 135):
                    self.assertLessEqual(h.cells(h.combine(rows, width)), width)
                self.assertIsNone(h.combine(['other screen', '', self.rows[0], hints], 135))

    def test_host_fits_80_columns(self):
        result = h.compact_host('demo | 内存 4.5/8.0 GiB 56% | 根盘 32.0/80.0 GiB 40% | 数据盘 75.0/100.0 GiB 75%', 79)
        for value in ('4.5/8.0', '32.0/80.0', '75.0/100.0'):
            self.assertIn(value, result)
        self.assertLessEqual(h.cells(result), 79)

    def test_unicode_width(self):
        self.assertEqual(h.cells('数据 e\u0301'), 6)
        self.assertEqual(h.fit('数据', 3), '数…')

    def test_sanitize_controls_and_escape_tmux(self):
        self.assertEqual(h.safe_text('a\nb\x1b[31m\tc'), 'ab[31mc')
        self.assertEqual(h.tmux_text('#(touch demo)'), '##(touch demo)')


class MetricsTests(unittest.TestCase):
    def test_linux_available_memory(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'meminfo'
            path.write_text('MemTotal: 8388608 kB\nMemAvailable: 3145728 kB\n')
            self.assertEqual(h.memory_usage(path), (5.0, 8.0, 62.5))

    def test_missing_memory_is_na(self):
        self.assertIsNone(h.memory_usage(Path('/nonexistent-hostbar-meminfo')))

    def test_noninteractive_commands_bypass_ui(self):
        for args in (['exec', 'hello'], ['--version'], ['login'], ['--help'], ['review']):
            self.assertFalse(h.interactive_args(args))
        for args in ([], ['resume', '--last'], ['-m', 'example'], ['hello world']):
            self.assertTrue(h.interactive_args(args))


if __name__ == '__main__':
    unittest.main()
