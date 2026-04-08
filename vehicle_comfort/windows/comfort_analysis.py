"""
舒适度分析窗口
Comfort Analysis Window
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QGroupBox,
    QLabel, QLineEdit, QComboBox, QPushButton, QProgressBar, QMessageBox
)
from PyQt6.QtCore import Qt

from utils.window_base import BaseWindow, DEFAULT_VEHICLE_PARAMS
from utils.calculators import get_comfort_rating
from threads.simulation_threads import ComfortAnalysisThread


class ComfortAnalysisWindow(BaseWindow):
    """舒适度分析主窗口"""

    def __init__(self):
        super().__init__("七自由度整车舒适性仿真")
        self.default_params = DEFAULT_VEHICLE_PARAMS.copy()
        self.param_inputs = {}
        self.result_labels = {}
        self.setup_ui()

    def setup_ui(self):
        """创建UI"""
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)

        # 标题
        title_layout = self.create_title_section(
            "七自由度整车舒适性仿真",
            "7-DOF Vehicle Comfort Analysis | ISO 2631评价"
        )
        for i in range(title_layout.count()):
            layout.addLayout(title_layout) if i == 0 else None

        # 参数区域（水平布局）
        params_layout = QHBoxLayout()
        
        # 车身参数
        vehicle_group = self.create_vehicle_params()
        params_layout.addWidget(vehicle_group)
        
        # 悬架参数
        suspension_group = self.create_suspension_params()
        params_layout.addWidget(suspension_group)
        
        # 仿真参数
        sim_group = self.create_simulation_params()
        params_layout.addWidget(sim_group)
        
        layout.addLayout(params_layout)

        # 按钮和进度
        btn_layout = QHBoxLayout()
        
        self.sim_btn = QPushButton("▶ 开始仿真")
        self.sim_btn.clicked.connect(self.start_simulation)
        btn_layout.addWidget(self.sim_btn)
        
        self.reset_btn = QPushButton("重置参数")
        self.reset_btn.setObjectName("resetButton")
        self.reset_btn.clicked.connect(self.reset_params)
        btn_layout.addWidget(self.reset_btn)
        
        layout.addLayout(btn_layout)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)

        # 结果显示
        results_group = self.create_results_display()
        layout.addWidget(results_group)

    def create_vehicle_params(self):
        """创建车身参数组"""
        group = QGroupBox("车身参数")
        layout = QGridLayout(group)
        
        params = [
            ('m_b', '车身质量 (kg)', 0, 0),
            ('I_p', '俯仰惯量 (kg·m²)', 1, 0),
            ('I_r', '侧倾惯量 (kg·m²)', 2, 0),
            ('a', '质心-前轴 (m)', 3, 0),
            ('b', '质心-后轴 (m)', 4, 0),
            ('B_f', '前轮距 (m)', 5, 0),
            ('B_r', '后轮距 (m)', 6, 0),
        ]
        
        for key, label, row, col in params:
            layout.addWidget(QLabel(label), row, col)
            edit = QLineEdit(str(self.default_params[key]))
            self.param_inputs[key] = edit
            layout.addWidget(edit, row, col + 1)
        
        return group

    def create_suspension_params(self):
        """创建悬架参数组"""
        group = QGroupBox("悬架参数 (前左/前右/后左/后右)")
        layout = QGridLayout(group)
        
        # 弹簧刚度
        layout.addWidget(QLabel("弹簧刚度 (N/mm)"), 0, 0)
        for i, suffix in enumerate(['A', 'B', 'C', 'D']):
            key = f'k_s{suffix}'
            edit = QLineEdit(str(self.default_params[key] / 1000))
            self.param_inputs[key] = edit
            layout.addWidget(edit, 0, i + 1)
        
        # 阻尼系数
        layout.addWidget(QLabel("阻尼系数 (N·s/mm)"), 1, 0)
        for i, suffix in enumerate(['A', 'B', 'C', 'D']):
            key = f'C_s{suffix}'
            edit = QLineEdit(str(self.default_params[key]/1000))
            self.param_inputs[key] = edit
            layout.addWidget(edit, 1, i + 1)
        
        # 轮胎质量
        layout.addWidget(QLabel("轮胎质量 (kg)"), 2, 0)
        for i, suffix in enumerate(['A', 'B', 'C', 'D']):
            key = f'm_w{suffix}'
            edit = QLineEdit(str(self.default_params[key]))
            self.param_inputs[key] = edit
            layout.addWidget(edit, 2, i + 1)
        
        # 轮胎刚度
        layout.addWidget(QLabel("轮胎刚度 (N/mm)"), 3, 0)
        for i, suffix in enumerate(['A', 'B', 'C', 'D']):
            key = f'k_t{suffix}'
            edit = QLineEdit(str(self.default_params[key]/1000))
            self.param_inputs[key] = edit
            layout.addWidget(edit, 3, i + 1)
        
        # 杠杆比
        layout.addWidget(QLabel("杠杆比 (前/后)"), 4, 0)
        for i, suffix in enumerate(['f', 'r']):
            key = f'lever_ratio_{suffix}'
            edit = QLineEdit(str(self.default_params[key]))
            self.param_inputs[key] = edit
            layout.addWidget(edit, 4, i + 1)
        
        return group

    def create_simulation_params(self):
        """创建仿真参数组"""
        group = QGroupBox("仿真参数")
        layout = QGridLayout(group)
        
        layout.addWidget(QLabel("车速 (m/s)"), 0, 0) #车速默认值设置为5m/s，即18km/h
        speed_edit = QLineEdit(str(self.default_params['vehicle_speed']))#默认值设置为5m/s，即18km/h
        self.param_inputs['vehicle_speed'] = speed_edit
        layout.addWidget(speed_edit, 0, 1)
        
        layout.addWidget(QLabel("仿真时长 (s)"), 1, 0)
        duration_edit = QLineEdit(str(self.default_params['duration']))
        self.param_inputs['duration'] = duration_edit
        layout.addWidget(duration_edit, 1, 1)
        
        layout.addWidget(QLabel("路面等级"), 2, 0)
        road_combo = QComboBox()
        road_combo.addItems(['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H'])
        road_combo.setCurrentText(self.default_params['road_class'])
        self.param_inputs['road_class'] = road_combo
        layout.addWidget(road_combo, 2, 1)
        
        layout.addWidget(QLabel("随机种子"), 3, 0)
        seed_edit = QLineEdit("")
        self.param_inputs['random_seed'] = seed_edit
        layout.addWidget(seed_edit, 3, 1)
        
        return group

    def create_results_display(self):
        """创建结果显示区域"""
        group = QGroupBox("仿真结果")
        layout = QGridLayout(group)
        
        # 四个座位
        seats = [
            ('bA', '前左座位', 0, 0),
            ('bB', '前右座位', 0, 1),
            ('bC', '后左座位', 1, 0),
            ('bD', '后右座位', 1, 1)
        ]
        
        for key, title, row, col in seats:
            label = QLabel(f"{title}\nz: --  a: --")
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.result_labels[key] = label
            layout.addWidget(label, row, col)
        
        # 质心
        center_label = QLabel("质心加速度\na: -- m/s²")
        center_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.result_labels['center'] = center_label
        layout.addWidget(center_label, 2, 0, 1, 2)
        
        # 舒适性评价
        self.comfort_label = QLabel("舒适性评价: --")
        self.comfort_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.comfort_label, 3, 0, 1, 2)
        
        return group

    def get_params(self):
        """获取参数"""
        params = {}
        for key, widget in self.param_inputs.items():
            if isinstance(widget, QComboBox):
                params[key] = widget.currentText()
            else:
                try:
                    if key == 'random_seed':
                        text = widget.text().strip()
                        params[key] = int(text) if text else None
                    else:
                        params[key] = float(widget.text())
                except ValueError:
                    params[key] = self.default_params.get(key, 0)
        for key in list(params.keys()):
            if key.startswith('k_s') or key.startswith('k_t') or key.startswith('C_s'):
                if isinstance(params[key], (int, float)):
                    params[key] = params[key] * 1000
        return params

    def reset_params(self):
        """重置参数"""
        for key, widget in self.param_inputs.items():
            if isinstance(widget, QComboBox):
                widget.setCurrentText(str(self.default_params.get(key, 'C')))
            else:
                widget.setText(str(self.default_params.get(key, '')))

    def start_simulation(self):
        """开始仿真"""
        self.sim_btn.setEnabled(False)
        self.sim_btn.setText("仿真计算中...")
        self.progress_bar.setValue(0)

        params = self.get_params()

        self.sim_thread = ComfortAnalysisThread(params)
        self.sim_thread.progress_updated.connect(self.update_progress)
        self.sim_thread.simulation_finished.connect(self.display_results)
        self.sim_thread.error_occurred.connect(self.handle_error)
        self.sim_thread.start()

    def update_progress(self, value):
        """更新进度"""
        self.progress_bar.setValue(value)

    def display_results(self, results):
        """显示结果"""
        # 更新座位结果
        for pos in ['bA', 'bB', 'bC', 'bD']:
            text = f"{pos[1:]}座位\nz: {results[f'z_{pos}']:.2f}mm  a: {results[f'a_{pos}']:.3f}m/s²"
            self.result_labels[pos].setText(text)
        
        # 更新质心结果
        self.result_labels['center'].setText(f"质心加速度\na: {results['a_b']:.4f} m/s²")
        
        # 舒适性评价
        rating, color = get_comfort_rating(results['a_b'])
        self.comfort_label.setText(f"舒适性评价: {rating}")
        self.comfort_label.setStyleSheet(f"color: {color}; font-size: 14px; font-weight: bold;")

        self.sim_btn.setEnabled(True)
        self.sim_btn.setText("▶ 开始仿真")

    def handle_error(self, error_msg):
        """处理错误"""
        QMessageBox.critical(self, "仿真错误", f"仿真出错: {error_msg}")
        self.sim_btn.setEnabled(True)
        self.sim_btn.setText("▶ 开始仿真")
