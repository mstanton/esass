import sys
import threading
from typing import Callable, Optional, List


# Conditional import for PTY support
try:
    if sys.platform == "win32":
        from winpty import PTY
    else:
        import ptyprocess
except ImportError:
    PTY = None
    ptyprocess = None


class ProcessManager:
    """
    Manages a subprocess within a pseudo-terminal (PTY) to maintain
    interactive features like colors and cursor movement.
    """

    def __init__(
        self,
        command: List[str],
        on_output: Callable[[str], None],
        on_exit: Optional[Callable[[int], None]] = None,
    ):
        self.command = command
        self.on_output = on_output
        self.on_exit = on_exit
        self.pty = None
        self.process = None
        self._stop_event = threading.Event()
        self._thread = None

    def start(self):
        """Start the subprocess in a PTY."""
        cmd_str = " ".join(self.command)

        if sys.platform == "win32":
            if PTY is None:
                raise ImportError("pywinpty is required for Windows PTY support.")
            # winpty requires the command to be a single string
            self.pty = PTY(80, 24)
            self.pty.spawn(cmd_str)
            self._thread = threading.Thread(target=self._read_loop_win32, daemon=True)
        else:
            if ptyprocess is None:
                raise ImportError("ptyprocess is required for POSIX PTY support.")
            self.process = ptyprocess.PtyProcessUnicode.spawn(self.command)
            self._thread = threading.Thread(target=self._read_loop_posix, daemon=True)

        self._thread.start()

    def stop(self):
        """Terminate the subprocess."""
        self._stop_event.set()
        if sys.platform == "win32" and self.pty:
            self.pty.close()
        elif self.process:
            self.process.terminate(force=True)

    def write(self, data: str):
        """Write input to the subprocess."""
        if sys.platform == "win32" and self.pty:
            self.pty.write(data)
        elif self.process:
            self.process.write(data)

    def resize(self, cols: int, rows: int):
        """Resize the PTY."""
        if sys.platform == "win32" and self.pty:
            self.pty.set_size(cols, rows)
        elif self.process:
            self.process.setwinsize(rows, cols)

    def _read_loop_win32(self):
        """Read output from Windows PTY."""
        while not self._stop_event.is_set():
            try:
                data = self.pty.read(1024)
                if data:
                    self.on_output(data)
                else:
                    break
            except Exception:
                break

        if self.on_exit:
            self.on_exit(0)  # Exit code retrieval is tricky with winpty basic usage

    def _read_loop_posix(self):
        """Read output from POSIX PTY."""
        while not self._stop_event.is_set():
            try:
                try:
                    data = self.process.read(1024)
                    if data:
                        self.on_output(data)
                except EOFError:
                    break
            except Exception:
                break

        if self.on_exit:
            self.process.wait()
            self.on_exit(self.process.exitstatus)
