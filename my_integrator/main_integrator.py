import sys
import os
import json
from PyQt5.QtWidgets import QApplication
from qfluentwidgets import FluentWindow, FluentIcon, setTheme, Theme

from ui.fluent_container_tab import FluentScriptTab

CONFIG_FILE = "integrator_config.json"

class MainFluentIntegrator(FluentWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("거상 자동화 통합 컨트롤러 v2.0 (Fluent UI)")
        self.resize(1280, 850)

        self.config_data = {}
        self.tab_widgets = {}

        self._load_settings()
        self._init_navigation()

    def _load_settings(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    self.config_data = json.load(f)
            except Exception:
                self.config_data = {}

        default_tabs = ["자동 로그인", "자동 사냥"]
        for tab_name in default_tabs:
            if tab_name not in self.config_data:
                self.config_data[tab_name] = {"path": "", "window_title": "", "args": ""}

    def _save_settings(self):
        try:
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.config_data, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"설정 저장 중 오류: {e}")

    def _init_navigation(self):
        # qfluentwidgets 호환 표준 아이콘으로 변경
        icons = {
            "자동 로그인": FluentIcon.FINGERPRINT,
            "자동 사냥": FluentIcon.APPLICATION
        }

        for tab_title in ["자동 로그인", "자동 사냥"]:
            tab_widget = FluentScriptTab(
                title=tab_title,
                config_data=self.config_data,
                save_callback=self._save_settings,
                parent=self
            )
            tab_widget.setObjectName(tab_title.replace(" ", "_"))
            self.tab_widgets[tab_title] = tab_widget

            self.addSubInterface(
                interface=tab_widget,
                icon=icons.get(tab_title, FluentIcon.APPLICATION),
                text=tab_title
            )

    def resizeEvent(self, event):
        super().resizeEvent(event)
        for tab_widget in self.tab_widgets.values():
            tab_widget.resize_embedded_window()

    def closeEvent(self, event):
        for tab_widget in self.tab_widgets.values():
            tab_widget.stop_script()
        event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    setTheme(Theme.DARK)

    win = MainFluentIntegrator()
    win.show()
    sys.exit(app.exec_())