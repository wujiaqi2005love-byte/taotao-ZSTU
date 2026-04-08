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

    from windows.comfort_analysis import ComfortAnalysisWindow
    from windows.uniform_stiffness import UniformStiffnessWindow
    from windows.separate_stiffness import SeparateStiffnessWindow
    from windows.spring_selector import SpringSelectorWindow
    from utils.shared_state import shared_state

    class MainMenuWindow(QMainWindow):

        def __init__(self):
            super().__init__()
            self.setWindowTitle("高尔夫球车舒适性分析与减震弹簧选型设计综合软件")
            self.setMinimumSize(850, 700)  # 稍微增大窗口，让布局更舒展
            self._child_windows = {}
            self._setup_ui()
            self._apply_styles()

            # 监听全局刚度更新
            shared_state.stiffness_updated.connect(self._on_global_stiffness)

        def _setup_ui(self):
            central = QWidget()
            self.setCentralWidget(central)
            layout = QVBoxLayout(central)
            layout.setSpacing(25)  # 增大间距，更透气
            layout.setContentsMargins(70, 50, 70, 50)  # 增大边距

            # 标题 - 更大更醒目
            title = QLabel("高尔夫球车舒适性分析与减震弹簧选型设计综合软件")
            title.setObjectName("title")
            title.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(title)

            # 分隔线 - 更纤细美观
            line = QFrame()
            line.setFrameShape(QFrame.Shape.HLine)
            line.setStyleSheet("background-color: #475569; max-height: 1px;")
            layout.addWidget(line)

            # 功能按钮配置
            buttons = [
                (
                    "舒适性分析",
                    "单次仿真 · ISO 2631 评价四座位加速度",
                    self._open_comfort
                ),
                (
                    "四轮统一刚度搜索",
                    "频率约束 + RMS扫描 · 一键发送到弹簧选型",
                    self._open_uniform
                ),
                (
                    "前后分离刚度搜索",
                    "二维参数空间优化 · 前后比例约束",
                    self._open_separate
                ),
                (
                    "弹簧选型系统",
                    "自动接收最优刚度 · 输出弹簧规格",
                    self._open_spring
                ),
            ]

            # ========== 【全新设计】完全透明的悬浮按钮 ==========
            for title_text, desc_text, slot in buttons:
                btn = QPushButton()
                btn.setObjectName("menuButton")
                btn.setMinimumHeight(100)  # 增大按钮尺寸
                btn.clicked.connect(slot)

                # 按钮内部布局
                v_layout = QVBoxLayout()
                v_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
                v_layout.setSpacing(6)  # 增大标题和描述的间距
                v_layout.setContentsMargins(0, 0, 0, 0)

                # 第一行：标题 - 更大更粗
                title_label = QLabel(title_text)
                title_label.setStyleSheet("""
                    font-size: 18px; 
                    font-weight: bold; 
                    color: #ffffff;
                """)
                title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

                # 第二行：描述 - 更精致
                desc_label = QLabel(desc_text)
                desc_label.setStyleSheet("""
                    font-size: 13px; 
                    color: #ffffff;
                """)
                desc_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

                v_layout.addWidget(title_label)
                v_layout.addWidget(desc_label)
                btn.setLayout(v_layout)

                layout.addWidget(btn)
            # ======================================================

            layout.addStretch(1)  # 增加弹性空间

            # 状态栏
            self.status_bar = QLabel("系统就绪 · 建议从刚度搜索开始")
            self.status_bar.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.status_bar.setObjectName("statusBar")
            layout.addWidget(self.status_bar)

        def _apply_styles(self):
            self.setStyleSheet("""
                /* 主背景 - 使用深蓝色背景 */
                QMainWindow { 
                    background-color: #0f172a; 
                }
                QWidget { 
                    background-color: #0f172a; 
                    color: #ffffff; 
                }

                /* 标题样式 */
                QLabel#title {
                    color: #ffffff;
                    font-size: 24px;  /* 更大的标题 */
                    font-weight: bold;
                    margin: 10px 0;
                }

                /* 副标题样式 */
                QLabel#subtitle {
                    color: #94a3b8;  /* 浅灰色，有层次感 */
                    font-size: 13px;
                    margin-bottom: 15px;
                }

                /* 【关键】透明悬浮按钮样式 */
                QPushButton#menuButton {
                    /* 默认状态：完全透明 */
                    background-color: transparent;
                    border: 2px solid transparent; /* 透明边框占位 */
                    border-radius: 12px; /* 圆角更现代 */
                    color: #ffffff;
                    text-align: center;
                }
                QPushButton#menuButton:hover {
                    /* 悬停状态：浮现背景和边框 */
                    background-color: rgba(30, 64, 175, 0.2); /* 半透明深蓝 */
                    border: 2px solid #3b82f6; /* 亮蓝色边框 */
                }
                QPushButton#menuButton:pressed {
                    /* 按下状态：背景加深 */
                    background-color: rgba(30, 64, 175, 0.4);
                }

                /* 状态栏样式 */
                QLabel#statusBar {
                    color: #ffffff;
                    font-size: 13px;
                    background-color: rgba(20, 83, 45, 0.3); /* 半透明绿色 */
                    border: 1px solid #10b981; /* 绿色边框 */
                    border-radius: 8px;
                    padding: 8px;
                    margin-top: 10px;
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
            self._open_spring()

    # ★ 第三步：主窗口在 QApplication 之后创建
    window = MainMenuWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()