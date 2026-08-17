from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QFileDialog
from PyQt5.QtCore import QThread, pyqtSlot
from qfluentwidgets import (PrimaryPushButton, PushButton, LineEdit, 
                            CaptionLabel, InfoBar, InfoBarPosition, CardWidget)
import win32gui

from core.process_manager import ScriptRunner, WindowFinderWorker

class FluentScriptTab(QWidget):
    def __init__(self, title, config_data, save_callback, parent=None):
        super().__init__(parent)
        self.tab_title = title
        self.config_data = config_data
        self.save_callback = save_callback

        self.process = None
        self.embedded_hwnd = None
        self.worker_thread = None

        self._init_ui()
        self._load_config()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(12)

        card = CardWidget(self)
        card_layout = QVBoxLayout(card)

        # 1. 스크립트 경로
        path_layout = QHBoxLayout()
        self.path_input = LineEdit()
        self.path_input.setReadOnly(True)
        self.path_btn = PushButton("경로 선택")
        path_layout.addWidget(CaptionLabel("스크립트 경로:"))
        path_layout.addWidget(self.path_input, 1)
        path_layout.addWidget(self.path_btn)

        # 2. 윈도우 타이틀 & 인수
        settings_layout = QHBoxLayout()
        self.title_input = LineEdit()
        self.args_input = LineEdit()

        settings_layout.addWidget(CaptionLabel("윈도우 타이틀:"))
        settings_layout.addWidget(self.title_input, 1)
        settings_layout.addWidget(CaptionLabel("실행 인수:"))
        settings_layout.addWidget(self.args_input, 1)

        # 3. 제어 버튼
        btn_layout = QHBoxLayout()
        self.run_btn = PrimaryPushButton("▶️ 실행")
        self.stop_btn = PushButton("⏹️ 종료")
        self.stop_btn.setEnabled(False)
        self.refresh_btn = PushButton("🔄 화면 맞춤")

        btn_layout.addWidget(self.run_btn)
        btn_layout.addWidget(self.stop_btn)
        btn_layout.addWidget(self.refresh_btn)
        btn_layout.addStretch(1)

        card_layout.addLayout(path_layout)
        card_layout.addLayout(settings_layout)
        card_layout.addLayout(btn_layout)

        # 하단 프로그램 임베딩 컨테이너
        self.container_widget = QWidget(self)
        self.container_widget.setStyleSheet("background-color: #1c1c1c; border-radius: 8px; border: 1px solid #333;")

        main_layout.addWidget(card)
        main_layout.addWidget(self.container_widget, 1)

        # 이벤트 연결
        self.path_btn.clicked.connect(self._select_path)
        self.title_input.textChanged.connect(self._on_config_changed)
        self.args_input.textChanged.connect(self._on_config_changed)

        self.run_btn.clicked.connect(self.start_script)
        self.stop_btn.clicked.connect(self.stop_script)
        self.refresh_btn.clicked.connect(self.resize_embedded_window)

    def _select_path(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "스크립트 선택", "", "Python (*.py)")
        if file_path:
            self.path_input.setText(file_path)
            self._on_config_changed()

    def _on_config_changed(self):
        self.config_data[self.tab_title] = {
            "path": self.path_input.text(),
            "window_title": self.title_input.text(),
            "args": self.args_input.text()
        }
        self.save_callback()

    def _load_config(self):
        cfg = self.config_data.get(self.tab_title, {})
        self.path_input.setText(cfg.get("path", ""))
        self.title_input.setText(cfg.get("window_title", ""))
        self.args_input.setText(cfg.get("args", ""))

    def start_script(self):
        script_path = self.path_input.text()
        window_title = self.title_input.text()
        args_str = self.args_input.text()

        if not script_path or not window_title:
            InfoBar.warning("입력 오류", "경로와 윈도우 타이틀을 설정해주세요.", parent=self, position=InfoBarPosition.TOP)
            return

        try:
            self.process = ScriptRunner.launch(script_path, args_str)
        except Exception as e:
            InfoBar.error("실행 오류", f"프로세스 실행 실패: {e}", parent=self, position=InfoBarPosition.TOP)
            return

        self.worker_thread = QThread()
        self.worker = WindowFinderWorker(window_title, self.process)
        self.worker.moveToThread(self.worker_thread)

        self.worker_thread.started.connect(self.worker.run)
        self.worker.found.connect(self._on_window_found)
        self.worker.failed.connect(self._on_window_failed)

        self.worker.found.connect(self.worker_thread.quit)
        self.worker.failed.connect(self.worker_thread.quit)
        self.worker.found.connect(self.worker.deleteLater)
        self.worker.failed.connect(self.worker.deleteLater)
        self.worker_thread.finished.connect(self.worker_thread.deleteLater)

        self.worker_thread.start()
        self.run_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)

    @pyqtSlot(int)
    def _on_window_found(self, hwnd):
        self.embedded_hwnd = hwnd
        success = ScriptRunner.embed_hwnd(
            hwnd,
            self.container_widget.winId(),
            self.container_widget.width(),
            self.container_widget.height()
        )
        if success:
            InfoBar.success("임베딩 성공", f"'{self.tab_title}' 창을 연결했습니다.", parent=self, position=InfoBarPosition.TOP_RIGHT)
        else:
            InfoBar.error("연결 실패", "창을 바인딩하지 못했습니다.", parent=self, position=InfoBarPosition.TOP)
            self.stop_script()

    @pyqtSlot(str)
    def _on_window_failed(self, error_msg):
        InfoBar.error("탐색 실패", error_msg, parent=self, position=InfoBarPosition.TOP)
        self.stop_script()

    def stop_script(self):
        ScriptRunner.release_and_terminate(self.process, self.embedded_hwnd)
        self.process = None
        self.embedded_hwnd = None

        self.run_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)

    def resize_embedded_window(self):
        if self.embedded_hwnd and win32gui.IsWindow(self.embedded_hwnd):
            win32gui.MoveWindow(
                self.embedded_hwnd, 0, 0,
                self.container_widget.width(), self.container_widget.height(), True
            )