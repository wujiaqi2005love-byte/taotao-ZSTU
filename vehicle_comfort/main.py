"""Application entry point for the vehicle comfort analysis platform."""

import sys

from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QApplication,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QVBoxLayout,
    QWidget,
)
from PyQt6.QtCore import Qt


APP_STYLE = """
QMainWindow, QWidget#centralWidget { background: #f4f7fb; color: #152238; }
QWidget { font-family: "PingFang SC", "Microsoft YaHei", "Segoe UI", sans-serif; }
QFrame#hero {
    background: #10243b; border: 0; border-radius: 20px;
}
QLabel#eyebrow { color: #8fb7dc; font-size: 11px; font-weight: 700; letter-spacing: 2px; }
QLabel#heroTitle { color: #ffffff; font-size: 25px; font-weight: 700; }
QLabel#heroDesc { color: #b6c9dc; font-size: 12px; line-height: 1.5; }
QLabel#heroMark {
    color: #d8f1ff; background: #1b3b58; border: 1px solid #315b7d;
    border-radius: 16px; font-size: 27px; font-weight: 700;
}
QLabel#sectionTitle { color: #152238; font-size: 15px; font-weight: 700; }
QLabel#sectionHint { color: #7c8ba0; font-size: 11px; }
QPushButton#moduleCard {
    text-align: left; background: #ffffff; color: #152238;
    border: 1px solid #e1e8f0; border-radius: 14px;
    padding: 18px 20px; font-size: 15px; font-weight: 700;
}
QPushButton#moduleCard:hover {
    background: #f8fbff; border: 1px solid #88b6e1;
}
QPushButton#moduleCard:pressed { background: #edf5fc; }
QLabel#cardMeta { color: #4382b7; font-size: 10px; font-weight: 700; letter-spacing: 1px; }
QLabel#cardTitle { color: #152238; font-size: 15px; font-weight: 700; }
QLabel#cardDesc { color: #75849a; font-size: 11px; font-weight: 400; }
QFrame#infoCard { background: #ffffff; border: 1px solid #e1e8f0; border-radius: 14px; }
QLabel#infoTitle { color: #152238; font-size: 12px; font-weight: 700; }
QLabel#infoText { color: #75849a; font-size: 11px; }
QLabel#statusBar {
    background: #e7f5ed; color: #247849; border-radius: 9px;
    padding: 9px 12px; font-size: 11px; font-weight: 600;
}
QLabel#footer { color: #96a2b2; font-size: 10px; }
"""


class ModuleCard(QPushButton):
    """A compact, keyboard-accessible launcher card."""

    def __init__(self, number: str, title: str, description: str, callback):
        super().__init__()
        self.setObjectName("moduleCard")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumHeight(128)
        self.setAccessibleName(title)
        self.clicked.connect(callback)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 14, 18, 12)
        layout.setSpacing(6)

        meta_row = QHBoxLayout()
        meta = QLabel(f"MODULE  {number}")
        meta.setObjectName("cardMeta")
        arrow = QLabel("↗")
        arrow.setObjectName("cardMeta")
        meta_row.addWidget(meta)
        meta_row.addStretch(1)
        meta_row.addWidget(arrow)
        title_label = QLabel(title)
        title_label.setObjectName("cardTitle")
        desc = QLabel(description)
        desc.setObjectName("cardDesc")
        desc.setWordWrap(True)
        for label in (meta, arrow, title_label, desc):
            label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        layout.addLayout(meta_row)
        layout.addWidget(title_label)
        layout.addWidget(desc)
        layout.addStretch(1)


class MainMenuWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("高尔夫球车舒适性分析平台")
        self.setMinimumSize(900, 700)
        self.resize(1040, 790)
        self._child_windows = {}
        self._setup_ui()
        self.setStyleSheet(APP_STYLE)

        # Import QObject-based modules only after QApplication is available.
        from utils.shared_state import shared_state

        shared_state.stiffness_updated.connect(self._on_global_stiffness)

    def _setup_ui(self):
        central = QWidget()
        central.setObjectName("centralWidget")
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(30, 26, 30, 22)
        root.setSpacing(19)

        hero = QFrame()
        hero.setObjectName("hero")
        hero_layout = QHBoxLayout(hero)
        hero_layout.setContentsMargins(27, 23, 25, 23)
        hero_layout.setSpacing(20)
        copy = QVBoxLayout()
        copy.setSpacing(8)
        eyebrow = QLabel("VEHICLE DYNAMICS  /  ENGINEERING TOOLKIT")
        eyebrow.setObjectName("eyebrow")
        title = QLabel("车辆舒适性分析与\n减震弹簧选型平台")
        title.setObjectName("heroTitle")
        desc = QLabel("从路面激励与整车动力学仿真，到刚度优化和弹簧参数设计。")
        desc.setObjectName("heroDesc")
        desc.setWordWrap(True)
        copy.addWidget(eyebrow)
        copy.addWidget(title)
        copy.addWidget(desc)
        hero_layout.addLayout(copy, 1)

        mark = QLabel("7\nDOF")
        mark.setObjectName("heroMark")
        mark.setAlignment(Qt.AlignmentFlag.AlignCenter)
        mark.setFixedSize(96, 96)
        hero_layout.addWidget(mark, 0, Qt.AlignmentFlag.AlignVCenter)
        root.addWidget(hero)

        section = QHBoxLayout()
        section_title = QLabel("分析工作台")
        section_title.setObjectName("sectionTitle")
        section_hint = QLabel("选择一个模块开始")
        section_hint.setObjectName("sectionHint")
        section.addWidget(section_title)
        section.addSpacing(10)
        section.addWidget(section_hint)
        section.addStretch(1)
        root.addLayout(section)

        modules = [
            ("01", "车辆舒适度分析", "生成 ISO 8608 随机路面，查看车身响应与 ISO 2631 舒适性指标。", self._open_comfort),
            ("02", "四轮统一刚度搜索", "在频率约束下搜索统一悬架刚度，比较候选方案的加速度 RMS。", self._open_uniform),
            ("03", "前后分离刚度搜索", "扫描前后轴刚度组合，分析刚度比例、频率和乘坐舒适性。", self._open_separate),
            ("04", "弹簧选型系统", "根据目标刚度、行程和材料参数筛选可行的螺旋弹簧方案。", self._open_spring),
        ]
        grid = QGridLayout()
        grid.setHorizontalSpacing(14)
        grid.setVerticalSpacing(14)
        for index, (number, name, description, callback) in enumerate(modules):
            grid.addWidget(ModuleCard(number, name, description, callback), index // 2, index % 2)
        root.addLayout(grid)

        info_row = QHBoxLayout()
        info_row.setSpacing(14)
        info_row.addWidget(self._info_card("计算流程", "参数设置  →  动力学仿真  →  刚度优化  →  弹簧选型"), 3)
        info_row.addWidget(self._info_card("模型与标准", "七自由度整车模型  ·  ISO 8608  ·  ISO 2631"), 2)
        root.addLayout(info_row)
        root.addStretch(1)

        self.status_bar = QLabel("系统就绪  ·  建议从舒适度分析或刚度搜索开始")
        self.status_bar.setObjectName("statusBar")
        root.addWidget(self.status_bar)
        footer = QLabel("VEHICLE COMFORT & SPRING DESIGN  ·  PYTHON / PYQT6")
        footer.setObjectName("footer")
        footer.setAlignment(Qt.AlignmentFlag.AlignRight)
        root.addWidget(footer)

    @staticmethod
    def _info_card(title: str, text: str) -> QFrame:
        frame = QFrame()
        frame.setObjectName("infoCard")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(17, 13, 17, 13)
        layout.setSpacing(5)
        title_label = QLabel(title)
        title_label.setObjectName("infoTitle")
        body = QLabel(text)
        body.setObjectName("infoText")
        body.setWordWrap(True)
        layout.addWidget(title_label)
        layout.addWidget(body)
        return frame

    def _open_window(self, key: str, cls):
        window = self._child_windows.get(key)
        if window is None or not window.isVisible():
            window = cls()
            self._child_windows[key] = window
        window.show()
        window.raise_()
        window.activateWindow()

    def _open_comfort(self):
        from windows.comfort_analysis import ComfortAnalysisWindow
        self._open_window("comfort", ComfortAnalysisWindow)

    def _open_uniform(self):
        from windows.uniform_stiffness import UniformStiffnessWindow
        self._open_window("uniform", UniformStiffnessWindow)

    def _open_separate(self):
        from windows.separate_stiffness import SeparateStiffnessWindow
        self._open_window("separate", SeparateStiffnessWindow)

    def _open_spring(self):
        from windows.spring_selector import SpringSelectorWindow
        self._open_window("spring", SpringSelectorWindow)

    def _on_global_stiffness(self, k_min: float, k_max: float, source: str):
        self.status_bar.setText(
            f"刚度参数已更新  ·  {k_min / 1000:.2f} – {k_max / 1000:.2f} N/mm  ·  {source[:35]}"
        )
        self._open_spring()


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setFont(QFont("PingFang SC", 10))
    window = MainMenuWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
