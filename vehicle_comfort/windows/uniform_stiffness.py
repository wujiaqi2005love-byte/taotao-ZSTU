"""
四轮统一刚度搜索窗口（完整版）
Uniform Stiffness Search Window - Full Version
"""

import numpy as np
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QGroupBox,
    QLabel, QLineEdit, QComboBox, QPushButton, QProgressBar,
    QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox, QFrame
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor

from utils.window_base import DEFAULT_VEHICLE_PARAMS
from utils.calculators import (
    calc_body_frequency_uniform,
    calc_tire_frequency,
    calc_stiffness_range_from_frequency
)
from threads.simulation_threads import UniformStiffnessSearchThread


class UniformStiffnessWindow(QMainWindow):
    """四轮统一刚度搜索窗口"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("弹簧刚度求解器(频率约束) | Stiffness Finder with Frequency Constraints")
        self.setMinimumSize(1200, 800)

        # 默认参数
        self.default_params = DEFAULT_VEHICLE_PARAMS.copy()
        self.param_inputs = {}
        self.tire_freq_labels = {}
        self.calculated_k_range = None

        self.setup_ui()
        self.apply_styles()
        self.update_calculated_values()

    def setup_ui(self):
        """创建UI"""
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)

        # 标题
        title = QLabel("弹簧刚度求解器 (频率约束)")
        title.setObjectName("title")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        subtitle = QLabel("根据车身固有频率约束自动计算刚度搜索范围，扫描RMS")
        subtitle.setObjectName("subtitle")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(subtitle)

        # 参数区域
        params_layout = QHBoxLayout()

        # 左侧：车身参数
        vehicle_group = self.create_vehicle_params()
        params_layout.addWidget(vehicle_group)

        # 轮胎参数
        tire_group = self.create_tire_params()
        params_layout.addWidget(tire_group)

        # 中间：频率约束
        freq_group = self.create_frequency_params()
        params_layout.addWidget(freq_group)

        # 右侧：仿真参数
        sim_group = self.create_sim_params()
        params_layout.addWidget(sim_group)

        layout.addLayout(params_layout)

        # 计算结果显示
        calc_group = QGroupBox("约束计算结果")
        calc_layout = QGridLayout(calc_group)

        calc_layout.addWidget(QLabel("弹簧刚度范围:"), 0, 0)
        self.k_range_label = QLabel("-- ~ -- N/m")
        self.k_range_label.setObjectName("calcResult")
        calc_layout.addWidget(self.k_range_label, 0, 1)

        self.tire_warning_label = QLabel("")
        self.tire_warning_label.setObjectName("warning")
        calc_layout.addWidget(self.tire_warning_label, 0, 2, 1, 2)

        layout.addWidget(calc_group)

        # 按钮
        btn_layout = QHBoxLayout()

        self.calc_btn = QPushButton("计算刚度范围")
        self.calc_btn.setObjectName("calcButton")
        self.calc_btn.clicked.connect(self.update_calculated_values)
        btn_layout.addWidget(self.calc_btn)

        self.search_btn = QPushButton("开始扫描RMS")
        self.search_btn.setObjectName("searchButton")
        self.search_btn.clicked.connect(self.start_search)
        btn_layout.addWidget(self.search_btn)

        self.clear_btn = QPushButton("清空结果")
        self.clear_btn.setObjectName("clearButton")
        self.clear_btn.clicked.connect(self.clear_results)
        btn_layout.addWidget(self.clear_btn)

        layout.addLayout(btn_layout)

        # 进度
        progress_layout = QHBoxLayout()
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        progress_layout.addWidget(self.progress_bar)

        self.status_label = QLabel("就绪")
        self.status_label.setObjectName("status")
        self.status_label.setFixedWidth(220)
        progress_layout.addWidget(self.status_label)
        layout.addLayout(progress_layout)

        # 结果表格
        results_group = QGroupBox("扫描结果 - 刚度与RMS对应关系")
        results_layout = QVBoxLayout(results_group)

        self.results_table = QTableWidget()
        self.results_table.setColumnCount(4)
        self.results_table.setHorizontalHeaderLabels([
            "弹簧刚度 k_s (N/m)", "车身频率 (Hz)",
            "质心加速度 RMS (m/s²)", "舒适性评价"
        ])
        self.results_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.results_table.setAlternatingRowColors(True)
        results_layout.addWidget(self.results_table)

        self.summary_label = QLabel("")
        self.summary_label.setObjectName("summary")
        results_layout.addWidget(self.summary_label)

        layout.addWidget(results_group)

    def create_vehicle_params(self):
        """车身参数组"""
        group = QGroupBox("车身参数")
        group.setMinimumHeight(320)
        layout = QGridLayout(group)

        params = [
            ('m_b', '车身质量', 'kg'),
            ('I_p', '俯仰惯量', 'kg·m²'),
            ('I_r', '侧倾惯量', 'kg·m²'),
            ('a', '前轴距离', 'm'),
            ('b', '后轴距离', 'm'),
            ('B_f', '前轮距', 'm'),
            ('B_r', '后轮距', 'm'),
            ('C_s', '悬架阻尼', 'N·s/m'),
            ('lever_ratio_f', '前悬架杠杆比', ''),
            ('lever_ratio_r', '后悬架杠杆比', ''),
        ]

        for i, (key, label, unit) in enumerate(params):
            layout.addWidget(QLabel(label), i, 0)
            if key == 'C_s':
                default_val = 1500
            elif key == 'lever_ratio_f':
                default_val = 1.0
            elif key == 'lever_ratio_r':
                default_val = 1.0
            else:
                default_val = self.default_params.get(key, '')

            edit = QLineEdit(str(default_val))
            edit.setFixedWidth(80)
            edit.setAlignment(Qt.AlignmentFlag.AlignRight)
            edit.textChanged.connect(self.update_calculated_values)
            self.param_inputs[key] = edit
            layout.addWidget(edit, i, 1)

            unit_lbl = QLabel(unit)
            unit_lbl.setObjectName("unit")
            layout.addWidget(unit_lbl, i, 2)

        return group

    def create_tire_params(self):
        """轮胎参数组"""
        group = QGroupBox("轮胎参数 (非簧载)")
        group.setMinimumHeight(300)
        layout = QGridLayout(group)

        # 表头
        layout.addWidget(QLabel(""), 0, 0)
        header_m = QLabel("质量(kg)")
        header_m.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(header_m, 0, 1)
        header_k = QLabel("刚度(N/m)")
        header_k.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(header_k, 0, 2)
        header_f = QLabel("频率(Hz)")
        header_f.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(header_f, 0, 3)

        wheels = [
            ('A', '前左', 40, 200000),
            ('B', '前右', 40, 200000),
            ('C', '后左', 45, 200000),
            ('D', '后右', 45, 200000),
        ]

        for i, (suffix, label, m_default, k_default) in enumerate(wheels):
            layout.addWidget(QLabel(label), i + 1, 0)

            # 质量
            m_edit = QLineEdit(str(m_default))
            m_edit.setFixedWidth(65)
            m_edit.setAlignment(Qt.AlignmentFlag.AlignRight)
            m_edit.textChanged.connect(self.update_calculated_values)
            self.param_inputs[f'm_w{suffix}'] = m_edit
            layout.addWidget(m_edit, i + 1, 1)

            # 刚度
            k_edit = QLineEdit(str(k_default))
            k_edit.setFixedWidth(65)
            k_edit.setAlignment(Qt.AlignmentFlag.AlignRight)
            k_edit.textChanged.connect(self.update_calculated_values)
            self.param_inputs[f'k_t{suffix}'] = k_edit
            layout.addWidget(k_edit, i + 1, 2)

            # 频率显示
            freq_lbl = QLabel("--")
            freq_lbl.setObjectName("tireFreq")
            freq_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.tire_freq_labels[suffix] = freq_lbl
            layout.addWidget(freq_lbl, i + 1, 3)

        return group

    def create_frequency_params(self):
        """频率约束参数组"""
        group = QGroupBox("频率约束")
        layout = QGridLayout(group)

        # 车身频率约束
        layout.addWidget(QLabel("车身频率最小"), 0, 0)
        self.f_body_min = QLineEdit("1.0")
        self.f_body_min.setFixedWidth(80)
        self.f_body_min.textChanged.connect(self.update_calculated_values)
        layout.addWidget(self.f_body_min, 0, 1)
        layout.addWidget(QLabel("Hz"), 0, 2)

        layout.addWidget(QLabel("车身频率最大"), 1, 0)
        self.f_body_max = QLineEdit("1.5")
        self.f_body_max.setFixedWidth(80)
        self.f_body_max.textChanged.connect(self.update_calculated_values)
        layout.addWidget(self.f_body_max, 1, 1)
        layout.addWidget(QLabel("Hz"), 1, 2)

        # 分隔
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setObjectName("separator")
        layout.addWidget(line, 2, 0, 1, 3)

        # 轮胎频率约束（用于验证）
        layout.addWidget(QLabel("轮胎频率最小"), 3, 0)
        self.f_tire_min = QLineEdit("10")
        self.f_tire_min.setFixedWidth(80)
        self.f_tire_min.textChanged.connect(self.update_calculated_values)
        layout.addWidget(self.f_tire_min, 3, 1)
        layout.addWidget(QLabel("Hz"), 3, 2)

        layout.addWidget(QLabel("轮胎频率最大"), 4, 0)
        self.f_tire_max = QLineEdit("15")
        self.f_tire_max.setFixedWidth(80)
        self.f_tire_max.textChanged.connect(self.update_calculated_values)
        layout.addWidget(self.f_tire_max, 4, 1)
        layout.addWidget(QLabel("Hz"), 4, 2)

        # 搜索点数
        layout.addWidget(QLabel("搜索点数"), 5, 0)
        self.n_points = QLineEdit("15")
        self.n_points.setFixedWidth(80)
        layout.addWidget(self.n_points, 5, 1)

        return group

    def create_sim_params(self):
        """仿真参数组"""
        group = QGroupBox("仿真参数")
        layout = QGridLayout(group)

        layout.addWidget(QLabel("车速"), 0, 0)
        self.speed_input = QLineEdit("20")
        self.speed_input.setFixedWidth(80)
        layout.addWidget(self.speed_input, 0, 1)
        layout.addWidget(QLabel("m/s"), 0, 2)

        layout.addWidget(QLabel("路面等级"), 1, 0)
        self.road_combo = QComboBox()
        self.road_combo.addItems(['A', 'B', 'C', 'D', 'E'])
        self.road_combo.setCurrentText('C')
        self.road_combo.setFixedWidth(80)
        layout.addWidget(self.road_combo, 1, 1)

        layout.addWidget(QLabel("仿真时长"), 2, 0)
        self.duration_input = QLineEdit("8")
        self.duration_input.setFixedWidth(80)
        layout.addWidget(self.duration_input, 2, 1)
        layout.addWidget(QLabel("s"), 2, 2)

        # 说明
        info = QLabel(
            "车身频率 1-1.5Hz: 舒适性\n"
            "轮胎频率 10-15Hz: 抓地力\n"
            "路面: A优 B良 C一般 D差\n"
            "杠杆比: >1放大 =1直连 <1缩小"
        )
        info.setObjectName("info")
        layout.addWidget(info, 3, 0, 1, 3)

        return group

    def apply_styles(self):
        """应用样式"""
        self.setStyleSheet("""
            QMainWindow { background-color: #1a1f2e; }
            QWidget { color: #e0e6f0; font-family: "Microsoft YaHei", sans-serif; }
            QLabel#title { font-size: 22px; font-weight: bold; color: #60a5fa; padding: 10px; }
            QLabel#subtitle { font-size: 12px; color: #64748b; padding-bottom: 10px; }
            QLabel#unit { color: #64748b; font-size: 11px; }
            QLabel#info { color: #64748b; font-size: 10px; }
            QLabel#status { color: #94a3b8; font-size: 11px; }
            QLabel#calcResult { color: #4ade80; font-size: 13px; font-weight: bold; }
            QLabel#warning { color: #f87171; font-size: 12px; }
            QLabel#tireFreq { color: #4ade80; font-size: 11px; font-family: "Consolas", monospace; }
            QLabel#summary { color: #4ade80; font-size: 13px; font-weight: bold; padding: 10px; }
            QGroupBox {
                font-size: 13px; font-weight: bold; color: #a78bfa;
                border: 1px solid #3b4252; border-radius: 8px;
                margin-top: 12px; padding: 15px; background-color: #2d3548;
            }
            QGroupBox::title {
                subcontrol-origin: margin; left: 12px; padding: 0 8px;
            }
            QLineEdit {
                background-color: #0f172a; border: 1px solid #3b4252;
                border-radius: 4px; padding: 6px; color: #e0e6f0;
                font-size: 12px; font-family: "Consolas", monospace;
            }
            QLineEdit:focus { border-color: #60a5fa; }
            QComboBox {
                background-color: #1e293b; border: 1px solid #3b4252;
                border-radius: 4px; padding: 6px; color: #e0e6f0;
            }
            QComboBox QAbstractItemView { background-color: #1e293b; color: #e0e6f0; }
            QPushButton#searchButton, QPushButton#calcButton {
                background-color: #3b82f6; border: none; border-radius: 6px;
                padding: 12px 25px; font-size: 13px; font-weight: bold; color: white;
            }
            QPushButton#searchButton:hover, QPushButton#calcButton:hover { background-color: #2563eb; }
            QPushButton#searchButton:disabled, QPushButton#calcButton:disabled { background-color: #475569; }
            QPushButton#clearButton {
                background-color: #475569; border: none; border-radius: 6px;
                padding: 12px 20px; font-size: 13px; color: white;
            }
            QPushButton#clearButton:hover { background-color: #64748b; }
            QProgressBar {
                border: none; border-radius: 4px; background-color: #1e293b; height: 20px;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #3b82f6, stop:1 #8b5cf6);
                border-radius: 4px;
            }
            QTableWidget {
                background-color: #1e293b; border: 1px solid #3b4252;
                gridline-color: #3b4252; color: #e0e6f0;
            }
            QTableWidget::item { padding: 8px; }
            QTableWidget::item:selected { background-color: #3b82f6; }
            QHeaderView::section {
                background-color: #2d3548; color: #a78bfa;
                padding: 8px; border: none; font-weight: bold;
            }
            QFrame#separator { background-color: #475569; max-height: 1px; margin: 8px 0; }
        """)

    def update_calculated_values(self):
        """更新计算结果"""
        try:
            m_b = float(self.param_inputs['m_b'].text())
            f_body_min = float(self.f_body_min.text())
            f_body_max = float(self.f_body_max.text())
            f_tire_min = float(self.f_tire_min.text())
            f_tire_max = float(self.f_tire_max.text())

            # 计算刚度范围
            k_min, k_max = calc_stiffness_range_from_frequency(m_b, f_body_min, f_body_max)
            self.k_range_label.setText(f"{k_min:.0f} ~ {k_max:.0f} N/m")

            # 计算每个轮胎的频率
            all_valid = True
            invalid_wheels = []

            for suffix in ['A', 'B', 'C', 'D']:
                try:
                    m_w = float(self.param_inputs[f'm_w{suffix}'].text())
                    k_t = float(self.param_inputs[f'k_t{suffix}'].text())
                    f_tire = calc_tire_frequency(m_w, k_t)
                    self.tire_freq_labels[suffix].setText(f"{f_tire:.1f}")

                    if not (f_tire_min <= f_tire <= f_tire_max):
                        all_valid = False
                        invalid_wheels.append(f"{suffix}({f_tire:.1f}Hz)")
                        self.tire_freq_labels[suffix].setStyleSheet("color: #f87171;")
                    else:
                        self.tire_freq_labels[suffix].setStyleSheet("color: #4ade80;")
                except ValueError:
                    self.tire_freq_labels[suffix].setText("--")
                    all_valid = False

            # 更新警告
            if all_valid:
                self.tire_warning_label.setText("✓ 所有轮胎频率满足约束")
                self.tire_warning_label.setStyleSheet("color: #4ade80;")
            else:
                self.tire_warning_label.setText(f"⚠ 轮胎频率超出范围: {', '.join(invalid_wheels)}")
                self.tire_warning_label.setStyleSheet("color: #f87171;")

            # 保存计算结果
            self.calculated_k_range = (k_min, k_max)

        except ValueError:
            self.k_range_label.setText("输入无效")
            self.tire_warning_label.setText("")
            self.calculated_k_range = None

    def get_base_params(self):
        """获取基础参数"""
        params = self.default_params.copy()

        for key, widget in self.param_inputs.items():
            try:
                val = float(widget.text())
                if key == 'C_s':
                    params['C_sA'] = params['C_sB'] = params['C_sC'] = params['C_sD'] = val
                elif key in ['m_wA', 'm_wB', 'm_wC', 'm_wD', 'k_tA', 'k_tB', 'k_tC', 'k_tD']:
                    params[key] = val
                elif key in ['lever_ratio_f', 'lever_ratio_r']:
                    params[key] = val
                else:
                    params[key] = val
            except ValueError:
                pass

        try:
            params['vehicle_speed'] = float(self.speed_input.text())
            params['duration'] = float(self.duration_input.text())
        except ValueError:
            pass
        params['road_class'] = self.road_combo.currentText()

        return params

    def start_search(self):
        """开始搜索"""
        if self.calculated_k_range is None:
            QMessageBox.warning(self, "错误", "请先正确输入参数计算刚度范围")
            return

        try:
            n_points = int(self.n_points.text())
        except ValueError:
            QMessageBox.warning(self, "输入错误", "搜索点数必须为整数")
            return

        self.search_btn.setEnabled(False)
        self.search_btn.setText("扫描中...")
        self.results_table.setRowCount(0)
        self.summary_label.setText("")

        base_params = self.get_base_params()

        self.search_thread = UniformStiffnessSearchThread(
            base_params, self.calculated_k_range, n_points
        )
        self.search_thread.progress_updated.connect(self.update_progress)
        self.search_thread.search_finished.connect(self.display_results)
        self.search_thread.error_occurred.connect(self.handle_error)
        self.search_thread.start()

    def update_progress(self, value, status):
        """更新进度"""
        self.progress_bar.setValue(value)
        self.status_label.setText(status)

    def display_results(self, results):
        """显示结果"""
        self.results_table.setRowCount(len(results))

        for i, r in enumerate(results):
            # k_s
            item_k = QTableWidgetItem(f"{r['k_s']:.0f}")
            item_k.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.results_table.setItem(i, 0, item_k)

            # 车身频率
            item_f = QTableWidgetItem(f"{r['f_body']:.3f}")
            item_f.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.results_table.setItem(i, 1, item_f)

            # RMS
            item_rms = QTableWidgetItem(f"{r['rms']:.4f}")
            item_rms.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.results_table.setItem(i, 2, item_rms)

            # 舒适性评价
            rms = r['rms']
            if rms < 0.315:
                rating, color = "舒适", QColor("#4ade80")
            elif rms < 0.63:
                rating, color = "稍不舒适", QColor("#a3e635")
            elif rms < 1.0:
                rating, color = "不舒适", QColor("#fbbf24")
            elif rms < 1.6:
                rating, color = "很不舒适", QColor("#fb923c")
            else:
                rating, color = "非常不舒适", QColor("#f87171")

            item_rating = QTableWidgetItem(rating)
            item_rating.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            item_rating.setForeground(color)
            self.results_table.setItem(i, 3, item_rating)

        # 统计
        if results:
            rms_vals = [r['rms'] for r in results]
            k_vals = [r['k_s'] for r in results]
            min_rms_idx = np.argmin(rms_vals)

            self.summary_label.setText(
                f"扫描完成 | RMS范围: {min(rms_vals):.3f} ~ {max(rms_vals):.3f} m/s² | "
                f"最优: k_s={k_vals[min_rms_idx]:.0f}N/m 时 RMS={rms_vals[min_rms_idx]:.3f}m/s²"
            )
            self.summary_label.setStyleSheet("color: #4ade80;")
        else:
            self.summary_label.setText("未获得有效结果")
            self.summary_label.setStyleSheet("color: #f87171;")

        self.search_btn.setEnabled(True)
        self.search_btn.setText("开始扫描RMS")
        self.status_label.setText("扫描完成")

    def handle_error(self, error_msg):
        """处理错误"""
        QMessageBox.critical(self, "错误", f"扫描出错: {error_msg}")
        self.search_btn.setEnabled(True)
        self.search_btn.setText("开始扫描RMS")

    def clear_results(self):
        """清空结果"""
        self.results_table.setRowCount(0)
        self.summary_label.setText("")
        self.progress_bar.setValue(0)
        self.status_label.setText("就绪")