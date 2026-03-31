"""
七自由度汽车舒适度分析系统主程序
7-DOF Vehicle Comfort Analysis System - Main Entry
"""

import sys
import os

# 添加当前目录到Python路径
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QFrame
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

# 导入窗口类
from windows.comfort_analysis import ComfortAnalysisWindow
from windows.uniform_stiffness import UniformStiffnessWindow
from windows.separate_stiffness import SeparateStiffnessWindow


class MainMenuWindow(QMainWindow):
    """主菜单窗口"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("七自由度汽车舒适度分析系统")
        self.setMinimumSize(700, 500)
        self.setup_ui()
        self.apply_styles()

    def setup_ui(self):
        """创建UI"""
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setSpacing(30)
        layout.setContentsMargins(40, 40, 40, 40)

        # 标题
        title = QLabel("七自由度汽车舒适度分析系统")
        title.setObjectName("title")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setFont(QFont("Microsoft YaHei", 24, QFont.Weight.Bold))
        layout.addWidget(title)

        subtitle = QLabel("7-DOF Vehicle Comfort Analysis System")
        subtitle.setObjectName("subtitle")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setFont(QFont("Segoe UI", 14))
        layout.addWidget(subtitle)

        # 分隔线
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        line.setStyleSheet("background-color: #3b4252;")
        layout.addWidget(line)

        # 功能按钮
        btn_layout = QVBoxLayout()
        btn_layout.setSpacing(20)

        # 舒适度分析按钮
        btn1 = QPushButton("舒适度分析\nComfort Analysis")
        btn1.setObjectName("menuButton")
        btn1.setMinimumHeight(80)
        btn1.clicked.connect(self.open_comfort_analysis)
        btn_layout.addWidget(btn1)

        # 四轮统一刚度搜索按钮
        btn2 = QPushButton("四轮统一刚度搜索\nUniform Stiffness Search")
        btn2.setObjectName("menuButton")
        btn2.setMinimumHeight(80)
        btn2.clicked.connect(self.open_uniform_stiffness)
        btn_layout.addWidget(btn2)

        # 前后分离刚度搜索按钮
        btn3 = QPushButton("前后分离刚度搜索\nSeparate Stiffness Search")
        btn3.setObjectName("menuButton")
        btn3.setMinimumHeight(80)
        btn3.clicked.connect(self.open_separate_stiffness)
        btn_layout.addWidget(btn3)

        layout.addLayout(btn_layout)

        # 底部信息
        layout.addStretch()
        info = QLabel("Based on ISO 8608 & ISO 2631 Standards")
        info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        info.setStyleSheet("color: #64748b; font-size: 11px;")
        layout.addWidget(info)

    def apply_styles(self):
        """应用样式"""
        self.setStyleSheet("""
            QMainWindow {
                background-color: #0f172a;
            }
            QWidget {
                background-color: #0f172a;
                color: #e0e6f0;
            }
            QLabel#title {
                color: #f0f9ff;
                margin: 20px 0;
            }
            QLabel#subtitle {
                color: #94a3b8;
                margin-bottom: 20px;
            }
            QPushButton#menuButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #3b82f6, stop:1 #8b5cf6);
                border: none;
                border-radius: 12px;
                color: white;
                font-size: 16px;
                font-weight: bold;
                padding: 20px;
            }
            QPushButton#menuButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #2563eb, stop:1 #7c3aed);
            }
            QPushButton#menuButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #1e40af, stop:1 #6d28d9);
            }
        """)

    def open_comfort_analysis(self):
        """打开舒适度分析窗口"""
        self.comfort_window = ComfortAnalysisWindow()
        self.comfort_window.show()

    def open_uniform_stiffness(self):
        """打开四轮统一刚度搜索窗口"""
        self.uniform_window = UniformStiffnessWindow()
        self.uniform_window.show()

    def open_separate_stiffness(self):
        """打开前后分离刚度搜索窗口"""
        self.separate_window = SeparateStiffnessWindow()
        self.separate_window.show()


def main():
    """主程序入口"""
    app = QApplication(sys.argv)
    app.setStyle('Fusion')

    # 设置应用程序字体
    font = QFont("Microsoft YaHei", 10)
    app.setFont(font)

    window = MainMenuWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()