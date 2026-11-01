import fcntl
import base64
import importlib.util
import os
from pathlib import Path
import pty
import select
import shutil
import signal
import struct
import subprocess
import sys
import tempfile
import termios
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('hostbar', ROOT / 'hostbar.py')
h = importlib.util.module_from_spec(spec)
spec.loader.exec_module(h)


@unittest.skipUnless(sys.platform == 'linux' and shutil.which('tmux'), 'requires Linux and tmux')
class TerminalTests(unittest.TestCase):
    def test_history_inputs_reach_codex(self):
        config = h.tmux_config()
        self.assertIn('set -g mouse on', config)
        self.assertNotIn('set -g mouse off', config)
        self.assertIn("bind -n WheelUpPane if-shell -F '#{mouse_any_flag}' "
                      "'send-keys -M' 'send-keys PageUp'", config)
        self.assertIn("bind -n WheelDownPane if-shell -F '#{mouse_any_flag}' "
                      "'send-keys -M' 'send-keys PageDown'", config)
        self.assertIn('bind -n S-PageUp send-keys C-t', config)
        self.assertNotIn('bind -n S-PageUp copy-mode', config)

    def test_resize_dialog_copy_mode_and_ctrl_z(self):
        with tempfile.TemporaryDirectory() as tmp:
            # Paths and labels that must never be evaluated as shell/tmux code.
            folder = Path(tmp) / "a ' space $chars#here"
            folder.mkdir()
            script = folder / 'hostbar.py'
            shutil.copyfile(ROOT / 'hostbar.py', script)
            fake = folder / 'fake codex'
            shutil.copyfile(ROOT / 'tests/fake_codex.py', fake)
            fake.chmod(0o755)
            config = Path(tmp) / 'tmux.conf'
            config.write_text(h.tmux_config())
            sock = str(Path(tmp) / 'test.sock')
            master, slave = pty.openpty()
            fcntl.ioctl(slave, termios.TIOCSWINSZ, struct.pack('HHHH', 24, 80, 0, 0))
            env = os.environ.copy()
            env.pop('TMUX', None)
            env.update(TERM='xterm-256color', CODEX_HOSTBAR_PYTHON=sys.executable,
                       CODEX_HOSTBAR_SCRIPT=str(script),
                       CODEX_HOSTBAR_LABEL='demo #(touch NEVER) #{host}',
                       CODEX_HOSTBAR_DATA_PATH='', CODEX_HOSTBAR_LANGUAGE='en')
            proc = subprocess.Popen(['tmux', '-u', '-S', sock, '-f', str(config),
                                     'new-session', '-s', 'test', '--', str(fake), '--fixture'],
                                    stdin=slave, stdout=slave, stderr=slave,
                                    env=env, start_new_session=True)
            os.close(slave)
            output = bytearray()

            def drain():
                while select.select([master], [], [], 0)[0]:
                    try:
                        chunk = os.read(master, 65536)
                    except OSError:
                        break
                    if not chunk:
                        break
                    output.extend(chunk)

            def wait_for(check, description):
                deadline = time.monotonic() + 8
                while time.monotonic() < deadline:
                    drain()
                    try:
                        if check():
                            return
                    except (OSError, subprocess.SubprocessError, ValueError):
                        pass
                    time.sleep(0.05)
                self.fail(description + '\n' + output[-2000:].decode(errors='replace'))

            def state():
                result = subprocess.check_output(['tmux', '-S', sock, 'display-message',
                    '-p', '#{pane_width} #{pane_height} #{cursor_y}'], text=True,
                    stderr=subprocess.DEVNULL)
                return tuple(map(int, result.split()))

            def mouse_capture_active():
                result = subprocess.check_output(['tmux', '-S', sock, 'display-message',
                    '-p', '#{mouse_any_flag}'], text=True, stderr=subprocess.DEVNULL)
                return result.strip() == '1'

            def send(*args):
                subprocess.run(['tmux', '-S', sock, *args], check=True,
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

            def pane_text():
                return subprocess.check_output(['tmux', '-S', sock, 'capture-pane',
                    '-p', '-t', '%0'], stderr=subprocess.DEVNULL).decode()

            def folded(width, height):
                actual_width, actual_height, cursor = state()
                return (actual_width, actual_height) == (width, height) and cursor < height - 2

            try:
                wait_for(lambda: folded(80, 24), 'initial native footer was not folded')
                wait_for(lambda: b'RAM' in output and b'2 warnings' in output,
                         'status output missing')
                wait_for(mouse_capture_active, 'Codex mouse capture did not reach the client')
                os.write(master, b'\x1b[<64;10;10M')
                wait_for(lambda: 'OLDER HISTORY FROM MOUSE WHEEL' in pane_text(),
                         'mouse wheel did not reach Codex history')
                send('send-keys', '-l', 'c')
                wait_for(lambda: folded(80, 24), 'history fixture did not return to chat')
                for width, height in ((100, 32), (120, 40), (80, 24)):
                    fcntl.ioctl(master, termios.TIOCSWINSZ, struct.pack('HHHH', height, width, 0, 0))
                    # This test client has no controlling TTY; emulate its resize signal.
                    proc.send_signal(signal.SIGWINCH)
                    wait_for(lambda: folded(width, height), 'resize or composer redraw failed')
                send('send-keys', '-l', 'i')
                wait_for(lambda: '你好' in pane_text(), 'fixture did not enter typed composer state')
                typed_header = subprocess.check_output([
                    sys.executable, str(script), '--internal-footer', sock, '%0', '24', '80'],
                    env=env, text=True)
                self.assertIn('GPT-Example high', typed_header)
                self.assertTrue(folded(80, 24), 'typed composer footer was not folded')
                send('send-keys', '-l', 'r')
                wait_for(lambda: 'tab to queue message' in pane_text(), 'queue hint missing')
                # Exercise periodic status refresh, without manually calling the
                # renderer: typing during a running task must remain folded.
                stable_until = time.monotonic() + 3
                while time.monotonic() < stable_until:
                    drain()
                    self.assertTrue(folded(80, 24), 'running-task draft exposed a third row')
                    time.sleep(0.1)
                send('send-keys', '-l', 's')
                wait_for(lambda: 'enter copy & follow' in pane_text(), 'selection fixture missing')
                selected_header = subprocess.check_output([
                    sys.executable, str(script), '--internal-footer', sock, '%0', '24', '80'],
                    env=env, text=True)
                self.assertIn('GPT-Example high', selected_header)
                self.assertIn('esc clear', selected_header)
                self.assertTrue(folded(80, 24), 'selection resized the composer')
                send('send-keys', '-l', 'd')
                wait_for(lambda: state()[1] == 22, 'dialog viewport was cropped')
                send('send-keys', '-l', 'c')
                wait_for(lambda: state()[1] == 24, 'chat footer did not fold again')
                os.write(master, b'\x1b[5;2~')
                wait_for(lambda: '/ T R A N S C R I P T' in pane_text() and state()[1] == 22,
                         'Shift+PageUp did not open the Codex transcript at full viewport')
                send('send-keys', 'Escape')
                wait_for(lambda: state()[1] == 24, 'transcript exit failed')
                send('send-keys', '-l', 'm')
                wait_for(lambda: not mouse_capture_active(), 'fixture still captures mouse')
                for key_table in ('emacs', 'vi'):
                    send('set-window-option', 'mode-keys', key_table)
                    os.write(master, b'\x1b[<0;1;1M\x1b[<32;7;1M')

                    def selection_present():
                        return subprocess.check_output(['tmux', '-S', sock,
                            'display-message', '-p', '#{selection_present}'],
                            text=True).strip() == '1'

                    wait_for(selection_present, 'mouse drag did not select text')
                    # A periodic status refresh must not resize away the selection.
                    until = time.monotonic() + 2
                    while time.monotonic() < until:
                        drain()
                        self.assertTrue(selection_present(), 'refresh erased mouse selection')
                        self.assertEqual(state()[1], 24)
                        time.sleep(0.1)
                    os.write(master, b'\x1b[<0;7;1m')
                    time.sleep(0.2)
                    self.assertTrue(selection_present(), 'mouse release discarded selection')
                    output.clear()
                    os.write(master, b'\x03')
                    # tmux's emacs selection excludes the endpoint; vi includes it.
                    expected = b'Fixtur' if key_table == 'emacs' else b'Fixture'
                    encoded = base64.b64encode(expected)
                    wait_for(lambda: b'\x1b]52;' in output and encoded in output,
                             'Ctrl+C did not forward selected text to the terminal clipboard')
                    self.assertEqual(subprocess.check_output(
                        ['tmux', '-S', sock, 'show-buffer']), expected)
                    wait_for(lambda: folded(80, 24), 'copy exit changed the chat layout')
                os.write(master, b'\x1a')
                wait_for(lambda: proc.poll() is not None, 'Ctrl+Z did not detach')
                self.assertEqual(proc.returncode, 0)
                self.assertFalse((ROOT / 'NEVER').exists())
            finally:
                subprocess.run(['tmux', '-S', sock, 'kill-server'],
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                if proc.poll() is None:
                    proc.terminate()
                proc.wait(timeout=5)
                os.close(master)


if __name__ == '__main__':
    unittest.main()
