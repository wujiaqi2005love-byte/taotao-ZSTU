"""
整合主入口
Integrated Main Entry
确保 QApplication 在任何 QObject 子类实例化之前创建
"""

import sys
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QFont


def main():
    # ★ 第一步：先创建 QApplication
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    app.setFont(QFont("Microsoft YaHei", 10))

    # ★ 第二步：QApplication 存在后，再导入依赖 QObject 的模块
    from PyQt6.QtWidgets import (
        QMainWindow, QWidget, QVBoxLayout,
        QPushButton, QLabel, QFrame
    )
    from PyQt6.QtCore import Qt
    from PyQt6.QtGui import QFont as QFont2

    from windows.comfort_analysis import ComfortAnalysisWindow
    from windows.uniform_stiffness import UniformStiffnessWindow
    from windows.separate_stiffness import SeparateStiffnessWindow
    from windows.spring_selector import SpringSelectorWindow
    from utils.shared_state import shared_state

    class MainMenuWindow(QMainWindow):

        def __init__(self):
            super().__init__()
            self.setWindowTitle("车辆动力学分析与弹簧选型整合平台")
            self.setMinimumSize(750, 620)
            self._child_windows = {}
            self._setup_ui()
            self._apply_styles()

            # 监听全局刚度更新
            shared_state.stiffness_updated.connect(self._on_global_stiffness)

        def _setup_ui(self):
            central = QWidget()
            self.setCentralWidget(central)
            layout = QVBoxLayout(central)
            layout.setSpacing(18)
            layout.setContentsMargins(50, 35, 50, 35)

            # 标题
            title = QLabel("车辆动力学分析与弹簧选型整合平台")
            title.setObjectName("title")
            title.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(title)

            subtitle = QLabel(
                "Vehicle Dynamics Analysis & Spring Selection Integrated Platform\n"
                "ISO 8608 路面激励  ·  ISO 2631 舒适性评价  ·  七自由度动力学模型"
            )
            subtitle.setObjectName("subtitle")
            subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(subtitle)

            # 分隔线
            line = QFrame()
            line.setFrameShape(QFrame.Shape.HLine)
            line.setStyleSheet("background-color: #3b4252; max-height: 1px;")
            layout.addWidget(line)

            # 功能按钮配置
            buttons = [
                (
                    "    舒适度分析\n"
                    "    单次仿真 · ISO 2631 评价四座位加速度",
                    self._open_comfort
                ),
                (
                    "    四轮统一刚度搜索\n"
                    "    频率约束 + RMS扫描 · 一键发送到弹簧选型",
                    self._open_uniform
                ),
                (
                    "    前后分离刚度搜索\n"
                    "    二维参数空间优化 · 前后比例约束",
                    self._open_separate
                ),
                (
                    "    弹簧选型系统\n"
                    "    自动接收最优刚度 · 输出弹簧规格与3D预览",
                    self._open_spring
                ),
            ]

            for text, slot in buttons:
                btn = QPushButton(text)
                btn.setObjectName("menuButton")
                btn.setMinimumHeight(90)
                btn.clicked.connect(slot)
                layout.addWidget(btn)

            layout.addStretch()

            # 数据流说明
            flow = QLabel(
                "数据流向：  刚度搜索窗口  ──[ 📤 发送最优刚度 ]──▶  弹簧选型系统"
            )
            flow.setAlignment(Qt.AlignmentFlag.AlignCenter)
            flow.setStyleSheet("color: #475569; font-size: 11px;")
            layout.addWidget(flow)

            # 状态栏
            self.status_bar = QLabel("系统就绪 · 建议从刚度搜索开始")
            self.status_bar.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.status_bar.setObjectName("statusBar")
            layout.addWidget(self.status_bar)

        def _apply_styles(self):
            self.setStyleSheet("""
                QMainWindow { background-color: #0f172a; }
                QWidget { background-color: #0f172a; color: #e0e6f0; }
                QLabel#title {
                    color: #f0f9ff;
                    font-size: 20px;
                    font-weight: bold;
                    margin: 8px 0;
                }
                QLabel#subtitle {
                    color: #64748b;
                    font-size: 12px;
                    margin-bottom: 8px;
                }
                QLabel#statusBar {
                    color: #4ade80;
                    font-size: 12px;
                    background-color: #14532d;
                    border-radius: 6px;
                    padding: 6px;
                }
                QPushButton#menuButton {
                    background: qlineargradient(
                        x1:0, y1:0, x2:1, y2:0,
                        stop:0 #1e40af, stop:1 #4c1d95
                    );
                    border: 1px solid #3b4252;
                    border-radius: 10px;
                    color: white;
                    font-size: 13px;
                    font-weight: bold;
                    text-align: left;
                    padding: 15px 25px;
                }
                QPushButton#menuButton:hover {
                    background: qlineargradient(
                        x1:0, y1:0, x2:1, y2:0,
                        stop:0 #2563eb, stop:1 #7c3aed
                    );
                    border-color: #60a5fa;
                }
                QPushButton#menuButton:pressed {
                    background: qlineargradient(
                        x1:0, y1:0, x2:1, y2:0,
                        stop:0 #1e3a8a, stop:1 #3b0764
                    );
                }
            """)

        def _open_window(self, key: str, cls):
            """通用：复用已打开的子窗口实例"""
            win = self._child_windows.get(key)
            if win is None or not win.isVisible():
                self._child_windows[key] = cls()
                win = self._child_windows[key]
            win.show()
            win.raise_()
            win.activateWindow()

        def _open_comfort(self):
            self._open_window("comfort", ComfortAnalysisWindow)

        def _open_uniform(self):
            self._open_window("uniform", UniformStiffnessWindow)

        def _open_separate(self):
            self._open_window("separate", SeparateStiffnessWindow)

        def _open_spring(self):
            self._open_window("spring", SpringSelectorWindow)

        def _on_global_stiffness(self, k_min: float, k_max: float, source: str):
            """全局刚度更新：刷新状态栏 + 自动弹出弹簧选型"""
            self.status_bar.setText(
                f"✅ 刚度已更新：{k_min/1000:.2f} ~ {k_max/1000:.2f} N/mm  "
                f"| 来源：{source[:25]}..."
            )
            # 自动打开弹簧选型
            self._open_spring()

    # ★ 第三步：主窗口在 QApplication 之后创建
    window = MainMenuWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()