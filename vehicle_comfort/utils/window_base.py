"""
窗口基类和共享样式
Window Base Class and Shared Styles
"""

from PyQt6.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QLabel
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont


# 默认车辆参数
DEFAULT_VEHICLE_PARAMS = {
    'm_b': 1380,  # 车身质量 (kg)
    'I_p': 2440,  # 俯仰转动惯量 (kg·m²)
    'I_r': 380,   # 侧倾转动惯量 (kg·m²)
    'a': 1.2,     # 质心到前轴距离 (m)
    'b': 1.5,     # 质心到后轴距离 (m)
    'B_f': 1.48,  # 前轮距 (m)
    'B_r': 1.48,  # 后轮距 (m)
    'm_wA': 40,   # 前左轮质量 (kg)
    'm_wB': 40,   # 前右轮质量 (kg)
    'm_wC': 45,   # 后左轮质量 (kg)
    'm_wD': 45,   # 后右轮质量 (kg)
    'C_sA': 1500, # 前左阻尼 (N·s/m)
    'C_sB': 1500, # 前右阻尼 (N·s/m)
    'C_sC': 1800, # 后左阻尼 (N·s/m)
    'C_sD': 1800, # 后右阻尼 (N·s/m)
    'k_sA': 18000,  # 前左刚度 (N/m)
    'k_sB': 18000,  # 前右刚度 (N/m)
    'k_sC': 20000,  # 后左刚度 (N/m)
    'k_sD': 20000,  # 后右刚度 (N/m)
    'k_tA': 200000, # 前左轮胎刚度 (N/m)
    'k_tB': 200000, # 前右轮胎刚度 (N/m)
    'k_tC': 200000, # 后左轮胎刚度 (N/m)
    'k_tD': 200000, # 后右轮胎刚度 (N/m)
    'lever_ratio_f': 1.0,  # 前悬架杠杆比
    'lever_ratio_r': 1.0,  # 后悬架杠杆比
    'vehicle_speed': 20,    # 车速 (m/s)
    'road_class': 'C',      # 路面等级
    'duration': 10,         # 仿真时长 (s)
    'random_seed': None,    # 随机种子
}


# 深色主题样式
DARK_THEME_STYLE = """
    QMainWindow {
        background-color: #0f172a;
    }
    QWidget {
        background-color: #0f172a;
        color: #e0e6f0;
        font-family: "Segoe UI", "Microsoft YaHei", sans-serif;
    }
    QLabel#title {
        font-size: 26px;
        font-weight: bold;
        color: #f0f9ff;
        margin: 10px 0;
    }
    QLabel#subtitle {
        font-size: 13px;
        color: #94a3b8;
        margin-bottom: 15px;
    }
    QGroupBox {
        font-weight: bold;
        font-size: 13px;
        border: 2px solid #3b4252;
        border-radius: 8px;
        margin-top: 12px;
        padding-top: 15px;
        color: #60a5fa;
    }
    QGroupBox::title {
        subcontrol-origin: margin;
        left: 12px;
        padding: 0 8px;
    }
    QLabel {
        font-size: 12px;
        color: #cbd5e1;
        padding: 2px;
    }
    QLineEdit {
        background-color: #1e293b;
        border: 1px solid #3b4252;
        border-radius: 4px;
        padding: 6px 8px;
        color: #e0e6f0;
        font-size: 12px;
        font-family: "Consolas", monospace;
    }
    QLineEdit:focus {
        border-color: #60a5fa;
    }
    QComboBox {
        background-color: #1e293b;
        border: 1px solid #3b4252;
        border-radius: 4px;
        padding: 6px;
        color: #e0e6f0;
    }
    QComboBox::drop-down {
        border: none;
    }
    QComboBox::down-arrow {
        image: none;
        border-left: 5px solid transparent;
        border-right: 5px solid transparent;
        border-top: 5px solid #64748b;
        margin-right: 8px;
    }
    QComboBox QAbstractItemView {
        background-color: #1e293b;
        color: #e0e6f0;
        selection-background-color: #3b82f6;
    }
    QPushButton {
        background-color: #3b82f6;
        border: none;
        border-radius: 6px;
        padding: 12px 30px;
        font-size: 13px;
        font-weight: bold;
        color: white;
    }
    QPushButton:hover {
        background-color: #2563eb;
    }
    QPushButton:disabled {
        background-color: #475569;
    }
    QPushButton#clearButton, QPushButton#resetButton {
        background-color: #475569;
        padding: 12px 20px;
    }
    QPushButton#clearButton:hover, QPushButton#resetButton:hover {
        background-color: #64748b;
    }
    QProgressBar {
        border: none;
        border-radius: 4px;
        background-color: #1e293b;
        height: 20px;
        text-align: center;
    }
    QProgressBar::chunk {
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
            stop:0 #3b82f6, stop:0.5 #8b5cf6, stop:1 #f472b6);
        border-radius: 4px;
    }
    QTableWidget {
        background-color: #1e293b;
        border: 1px solid #3b4252;
        gridline-color: #3b4252;
        color: #e0e6f0;
    }
    QTableWidget::item {
        padding: 8px;
    }
    QTableWidget::item:selected {
        background-color: #3b82f6;
    }
    QHeaderView::section {
        background-color: #2d3548;
        color: #a78bfa;
        padding: 8px;
        border: none;
        font-weight: bold;
    }
    QFrame#separator {
        background-color: #475569;
        max-height: 1px;
        margin: 8px 0;
    }
    QScrollArea {
        border: none;
    }
"""


class BaseWindow(QMainWindow):
    """窗口基类"""
    
    def __init__(self, title="Vehicle Comfort Analysis"):
        super().__init__()
        self.setWindowTitle(title)
        self.setMinimumSize(1100, 750)
        self.setStyleSheet(DARK_THEME_STYLE)
    
    def create_title_section(self, main_title, subtitle=""):
        """创建标题区域"""
        layout = QVBoxLayout()
        
        title = QLabel(main_title)
        title.setObjectName("title")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        if subtitle:
            sub = QLabel(subtitle)
            sub.setObjectName("subtitle")
            sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(sub)
        
        return layout
