import sys
import os
import time
import shlex
import subprocess
import win32gui
import win32con
from PyQt5.QtCore import QObject, pyqtSignal

class WindowFinderWorker(QObject):
    found = pyqtSignal(int)
    failed = pyqtSignal(str)

    def __init__(self, title_substring, process):
        super().__init__()
        self.title_substring = title_substring
        self.process = process
        self.is_running = True

    def run(self):
        start_time = time.time()
        target_hwnd = 0
        timeout = 60

        while self.is_running and not target_hwnd and (time.time() - start_time < timeout):
            if self.process.poll() is not None:
                self.failed.emit(f"프로세스 종료됨 (Exit Code: {self.process.returncode})")
                return

            def enum_windows_callback(hwnd, _):
                if win32gui.IsWindowVisible(hwnd) and win32gui.GetParent(hwnd) == 0:
                    try:
                        title = win32gui.GetWindowText(hwnd)
                        if self.title_substring in title:
                            nonlocal target_hwnd
                            target_hwnd = hwnd
                    except Exception:
                        pass

            try:
                win32gui.EnumWindows(enum_windows_callback, None)
            except Exception:
                pass

            if target_hwnd:
                break
            time.sleep(0.5)

        if self.is_running:
            if target_hwnd:
                self.found.emit(target_hwnd)
            else:
                self.failed.emit("지정한 윈도우 타이틀을 가진 창을 찾을 수 없습니다.")

    def stop(self):
        self.is_running = False


class ScriptRunner:
    @staticmethod
    def launch(script_path, args_str):
        if not script_path or not os.path.exists(script_path):
            raise FileNotFoundError(f"스크립트 경로를 확인해주세요: {script_path}")

        cmd = [sys.executable, script_path]
        if args_str and args_str.strip():
            cmd.extend(shlex.split(args_str))

        return subprocess.Popen(
            cmd,
            cwd=os.path.dirname(os.path.abspath(script_path)),
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP
        )

    @staticmethod
    def embed_hwnd(hwnd, container_win_id, width, height):
        if not hwnd or not win32gui.IsWindow(hwnd):
            return False

        win32gui.SetParent(hwnd, int(container_win_id))
        style = win32gui.GetWindowLong(hwnd, win32con.GWL_STYLE)
        style = style & ~win32con.WS_CAPTION & ~win32con.WS_THICKFRAME | win32con.WS_CHILD
        win32gui.SetWindowLong(hwnd, win32con.GWL_STYLE, style)
        win32gui.MoveWindow(hwnd, 0, 0, width, height, True)
        win32gui.ShowWindow(hwnd, win32con.SW_SHOWMAXIMIZED)
        return True

    @staticmethod
    def release_and_terminate(proc, hwnd):
        if hwnd and win32gui.IsWindow(hwnd):
            try:
                win32gui.SetParent(hwnd, 0)
            except Exception:
                pass

        if proc and proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=3)
            except Exception:
                proc.kill()