"""
前后分离刚度搜索窗口（完整版）
Separate Stiffness Search Window - Full Version
单位说明：UI 输入/显示使用 N/mm 和 N·s/mm，内部计算自动换算为 N/m 和 N·s/m
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
from utils.calculators import calc_total_stiffness_range, calc_tire_frequency
from threads.simulation_threads import SeparateStiffnessSearchThread


class SeparateStiffnessWindow(QMainWindow):
    """前后分离刚度搜索窗口"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("弹簧刚度求解器-前后分离(频率约束) | Front/Rear Stiffness Finder")
        self.setMinimumSize(1300, 850)

        self.default_params = DEFAULT_VEHICLE_PARAMS.copy()
        self.param_inputs = {}
        self.tire_freq_labels = {}
        self.calculated_k_sum_range = None  # 内部始终存 N/m
        self._best_result = None

        self.setup_ui()
        self.apply_styles()
        self.update_calculated_values()

    def setup_ui(self):
        """创建UI"""
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setSpacing(12)
        layout.setContentsMargins(20, 15, 20, 15)

        title = QLabel("弹簧刚度求解器 - 前后分离 (频率约束)")
        title.setObjectName("title")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        subtitle = QLabel("根据车身频率约束计算 k_f + k_r 范围，通过前后比例扫描不同组合")
        subtitle.setObjectName("subtitle")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(subtitle)

        params_layout = QHBoxLayout()
        params_layout.addWidget(self.create_vehicle_params())
        params_layout.addWidget(self.create_tire_params())
        params_layout.addWidget(self.create_frequency_params())
        params_layout.addWidget(self.create_sim_params())
        layout.addLayout(params_layout)

        # 计算结果显示
        calc_group = QGroupBox("约束计算结果")
        calc_layout = QGridLayout(calc_group)
        calc_layout.addWidget(QLabel("前后刚度范围:"), 0, 0)
        self.k_sum_range_label = QLabel("-- ~ -- N/mm")    # ← N/mm
        self.k_sum_range_label.setObjectName("calcResult")
        calc_layout.addWidget(self.k_sum_range_label, 0, 1)
        self.tire_warning_label = QLabel("")
        self.tire_warning_label.setObjectName("warning")
        calc_layout.addWidget(self.tire_warning_label, 0, 2, 1, 2)
        layout.addWidget(calc_group)

        # 按钮
        btn_layout = QHBoxLayout()

        self.search_btn = QPushButton("开始扫描RMS")
        self.search_btn.setObjectName("searchButton")
        self.search_btn.clicked.connect(self.start_search)
        btn_layout.addWidget(self.search_btn)

        self.clear_btn = QPushButton("清空结果")
        self.clear_btn.setObjectName("clearButton")
        self.clear_btn.clicked.connect(self.clear_results)
        btn_layout.addWidget(self.clear_btn)

        self.send_btn = QPushButton("📤 发送最优刚度到弹簧选型")
        self.send_btn.setObjectName("sendButton")
        self.send_btn.setEnabled(False)
        self.send_btn.clicked.connect(self._send_to_spring_selector)
        btn_layout.addWidget(self.send_btn)
        layout.addLayout(btn_layout)

        progress_layout = QHBoxLayout()
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        progress_layout.addWidget(self.progress_bar)
        self.status_label = QLabel("就绪")
        self.status_label.setObjectName("status")
        self.status_label.setFixedWidth(250)
        progress_layout.addWidget(self.status_label)
        layout.addLayout(progress_layout)

        # 结果表格
        results_group = QGroupBox("扫描结果 - 前后刚度组合与RMS")
        results_layout = QVBoxLayout(results_group)
        self.results_table = QTableWidget()
        self.results_table.setColumnCount(7)
        self.results_table.setHorizontalHeaderLabels([
            "前刚度 (N/mm)", "后刚度 (N/mm)", "前后刚度比 ",  # ← N/mm
            "车身频率 (Hz)", "弹簧变化量峰值 (mm)", "质心加速度 RMS (m/s²)", "舒适性评价"
        ])
        self.results_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.results_table.setAlternatingRowColors(False)
        self.results_table.setStyleSheet(
            "QTableWidget { background-color: #0f172a; alternate-background-color: #0f172a; }"
        )
        self.results_table.setMinimumHeight(220)
        results_layout.addWidget(self.results_table)

        self.summary_label = QLabel("")
        self.summary_label.setObjectName("summary")
        results_layout.addWidget(self.summary_label)
        layout.addWidget(results_group)

    def _send_to_spring_selector(self):
        """将最优刚度发送到弹簧选型"""
        if self._best_result is None:
            return

        from utils.shared_state import shared_state
        base_params = self.get_base_params()
        best = self._best_result
        k_optimal = (best['k_f'] + best['k_r']) / 2  # N/m（内部值）

        shared_state.set_stiffness(
            k_min=self.calculated_k_sum_range[0] * 1000,
            k_max=self.calculated_k_sum_range[1] * 1000,
            k_optimal=k_optimal,
            source=f"前后分离搜索 | 路面{base_params['road_class']} | "
                   f"k_f={best['k_f']/1000:.3f} k_r={best['k_r']/1000:.3f} N/mm "  # ← N/mm
                   f"比例={best['ratio']:.2f} RMS={best['rms']:.3f}m/s²",
            vehicle_mass=base_params.get('m_b'),
            road_class=base_params['road_class'],
            vehicle_speed=base_params['vehicle_speed']
        )
        QMessageBox.information(
            self, "已发送",
            f"最优刚度组合已发送\n"
            f"k_f={best['k_f']/1000:.3f} N/mm  k_r={best['k_r']/1000:.3f} N/mm"  # ← N/mm
        )

    def create_vehicle_params(self):
        """车辆参数组"""
        group = QGroupBox("车身参数")
        group.setMinimumHeight(340)
        layout = QGridLayout(group)

        params = [
            ('m_b',          '车身质量',     'kg'),
            ('I_p',          '俯仰惯量',     'kg·m²'),
            ('I_r',          '侧倾惯量',     'kg·m²'),
            ('a',            '前轴距离',     'm'),
            ('b',            '后轴距离',     'm'),
            ('B_f',          '前轮距',       'm'),
            ('B_r',          '后轮距',       'm'),
            ('C_f',          '前悬架阻尼',   'N·s/mm'),  # ← N·s/mm
            ('C_r',          '后悬架阻尼',   'N·s/mm'),  # ← N·s/mm
            ('lever_ratio_f','前悬架杠杆比', ''),
            ('lever_ratio_r','后悬架杠杆比', ''),
        ]

        for i, (key, label, unit) in enumerate(params):
            layout.addWidget(QLabel(label), i, 0)
            if key == 'C_f':
                default_val = 1.5           # 1500 N·s/m → 1.5 N·s/mm
            elif key == 'C_r':
                default_val = 1.8           # 1800 N·s/m → 1.8 N·s/mm
            elif key in ('lever_ratio_f', 'lever_ratio_r'):
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
        group.setMinimumHeight(200)
        layout = QGridLayout(group)

        layout.setSpacing(12)
        layout.setHorizontalSpacing(20)
        layout.setVerticalSpacing(10)
        layout.setContentsMargins(20, 14, 20, 14)

        layout.addWidget(QLabel(""), 0, 0)
        header_m = QLabel("质量(kg)")
        header_m.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(header_m, 0, 1)
        header_k = QLabel("刚度(N/mm)")               # ← N/mm
        header_k.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(header_k, 0, 2)
        header_f = QLabel("频率(Hz)")
        header_f.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(header_f, 0, 3)

        wheels = [
            ('A', '前左', 40, 200),     # 200000 N/m → 200 N/mm
            ('B', '前右', 40, 200),
            ('C', '后左', 80, 200),
            ('D', '后右', 80, 200),
        ]

        for i, (suffix, label, m_default, k_default) in enumerate(wheels):
            layout.addWidget(QLabel(label), i + 1, 0)

            m_edit = QLineEdit(str(m_default))
            m_edit.setFixedWidth(70)
            m_edit.setAlignment(Qt.AlignmentFlag.AlignRight)
            m_edit.textChanged.connect(self.update_calculated_values)
            self.param_inputs[f'm_w{suffix}'] = m_edit
            layout.addWidget(m_edit, i + 1, 1)

            k_edit = QLineEdit(str(k_default))
            k_edit.setFixedWidth(65)
            k_edit.setAlignment(Qt.AlignmentFlag.AlignRight)
            k_edit.textChanged.connect(self.update_calculated_values)
            self.param_inputs[f'k_t{suffix}'] = k_edit
            layout.addWidget(k_edit, i + 1, 2)

            freq_lbl = QLabel("--")
            freq_lbl.setObjectName("tireFreq")
            freq_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.tire_freq_labels[suffix] = freq_lbl
            layout.addWidget(freq_lbl, i + 1, 3)

        return group

    def create_frequency_params(self):
        """频率约束参数组"""
        group = QGroupBox("频率约束与搜索")
        group.setMinimumWidth(290)
        group.setMinimumHeight(300)
        layout = QGridLayout(group)
        layout.setVerticalSpacing(8)
        layout.setColumnMinimumWidth(0, 120)
        layout.setColumnMinimumWidth(1, 90)

        def _freq_edit(default):
            e = QLineEdit(default)
            e.setMinimumWidth(90)
            e.textChanged.connect(self.update_calculated_values)
            return e

        layout.addWidget(QLabel("车身频率最小"), 0, 0)
        self.f_body_min = _freq_edit("1.0")
        layout.addWidget(self.f_body_min, 0, 1)
        layout.addWidget(QLabel("Hz"), 0, 2)

        layout.addWidget(QLabel("车身频率最大"), 1, 0)
        self.f_body_max = _freq_edit("1.5")
        layout.addWidget(self.f_body_max, 1, 1)
        layout.addWidget(QLabel("Hz"), 1, 2)

        line1 = QFrame()
        line1.setFrameShape(QFrame.Shape.HLine)
        line1.setObjectName("separator")
        layout.addWidget(line1, 2, 0, 1, 3)

        layout.addWidget(QLabel("轮胎频率最小"), 3, 0)
        self.f_tire_min = _freq_edit("5")
        layout.addWidget(self.f_tire_min, 3, 1)
        layout.addWidget(QLabel("Hz"), 3, 2)

        layout.addWidget(QLabel("轮胎频率最大"), 4, 0)
        self.f_tire_max = _freq_edit("15")
        layout.addWidget(self.f_tire_max, 4, 1)
        layout.addWidget(QLabel("Hz"), 4, 2)

        line2 = QFrame()
        line2.setFrameShape(QFrame.Shape.HLine)
        line2.setObjectName("separator")
        layout.addWidget(line2, 5, 0, 1, 3)

        layout.addWidget(QLabel("前后刚度比最小"), 6, 0)
        self.ratio_min = QLineEdit("1")
        self.ratio_min.setMinimumWidth(90)
        layout.addWidget(self.ratio_min, 6, 1)

        layout.addWidget(QLabel("前后刚度比最大"), 7, 0)
        self.ratio_max = QLineEdit("2")
        self.ratio_max.setMinimumWidth(90)
        layout.addWidget(self.ratio_max, 7, 1)

        layout.addWidget(QLabel("每轴搜索点数"), 8, 0)
        self.n_points = QLineEdit("12")
        self.n_points.setMinimumWidth(90)
        layout.addWidget(self.n_points, 8, 1)
        layout.addWidget(QLabel("(总计N²，全显)"), 8, 2)

        line3 = QFrame()
        line3.setFrameShape(QFrame.Shape.HLine)
        line3.setObjectName("separator")
        layout.addWidget(line3, 9, 0, 1, 3)

        from PyQt6.QtWidgets import QCheckBox
        self.defl_check = QCheckBox("启用弹簧变化量约束")
        self.defl_check.setChecked(True)
        self.defl_check.toggled.connect(lambda c: self.defl_limit_edit.setEnabled(c))
        layout.addWidget(self.defl_check, 10, 0, 1, 2)

        layout.addWidget(QLabel("弹簧变化量 ≤"), 11, 0)
        self.defl_limit_edit = QLineEdit("80")
        self.defl_limit_edit.setMinimumWidth(90)
        layout.addWidget(self.defl_limit_edit, 11, 1)
        layout.addWidget(QLabel("mm"), 11, 2)

        return group

    def create_sim_params(self):
        """仿真参数组"""
        group = QGroupBox("仿真参数")
        layout = QGridLayout(group)

        layout.addWidget(QLabel("车速"), 0, 0)
        self.speed_input = QLineEdit("5")
        self.speed_input.setFixedWidth(80)
        layout.addWidget(self.speed_input, 0, 1)
        layout.addWidget(QLabel("m/s"), 0, 2)

        layout.addWidget(QLabel("路面等级"), 1, 0)
        self.road_combo = QComboBox()
        self.road_combo.addItems(['A', 'B', 'C', 'D', 'E'])
        self.road_combo.setCurrentText('B')
        self.road_combo.setFixedWidth(80)
        layout.addWidget(self.road_combo, 1, 1)

        layout.addWidget(QLabel("仿真时长"), 2, 0)
        self.duration_input = QLineEdit("8")
        self.duration_input.setFixedWidth(80)
        layout.addWidget(self.duration_input, 2, 1)
        layout.addWidget(QLabel("s"), 2, 2)

        info = QLabel(
            "前后比说明:\n"
            " < 1: 后硬前软\n"
            " = 1: 前后相同\n"
            " > 1: 前硬后软\n\n"
            "杠杆比: >1放大 =1直连\n"
            "路面: A优 B良 C一般\n"
            "点数N时总计N²组"
        )
        info.setObjectName("info")
        layout.addWidget(info, 3, 0, 1, 3)

        return group

    def apply_styles(self):
        """应用样式"""
        self.setStyleSheet("""
            QMainWindow { background-color: #1a1f2e; }
            QWidget { color: #e0e6f0; font-family: "Microsoft YaHei", sans-serif; }
            QLabel#title { font-size: 20px; font-weight: bold; color: #60a5fa; padding: 8px; }
            QLabel#subtitle { font-size: 11px; color: #64748b; padding-bottom: 8px; }
            QLabel#unit { color: #64748b; font-size: 11px; }
            QLabel#info { color: #64748b; font-size: 10px; }
            QLabel#status { color: #94a3b8; font-size: 11px; }
            QLabel#calcResult { color: #4ade80; font-size: 13px; font-weight: bold; }
            QLabel#warning { color: #f87171; font-size: 11px; }
            QLabel#tireFreq { color: #4ade80; font-size: 11px; font-family: "Consolas", monospace; }
            QLabel#summary { color: #4ade80; font-size: 12px; font-weight: bold; padding: 8px; }
            QGroupBox {
                font-size: 12px; font-weight: bold; color: #a78bfa;
                border: 1px solid #3b4252; border-radius: 8px;
                margin-top: 10px; padding: 12px; background-color: #2d3548;
            }
            QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 6px; }
            QLineEdit {
                background-color: #0f172a; border: 1px solid #3b4252;
                border-radius: 4px; padding: 5px; color: #e0e6f0;
                font-size: 11px; font-family: "Consolas", monospace;
            }
            QLineEdit:focus { border-color: #60a5fa; }
            QComboBox {
                background-color: #1e293b; border: 1px solid #3b4252;
                border-radius: 4px; padding: 5px; color: #e0e6f0;
            }
            QComboBox QAbstractItemView { background-color: #1e293b; color: #e0e6f0; }
            QPushButton#searchButton, QPushButton#calcButton {
                background-color: #3b82f6; border: none; border-radius: 6px;
                padding: 10px 20px; font-size: 12px; font-weight: bold; color: white;
            }
            QPushButton#searchButton:hover, QPushButton#calcButton:hover { background-color: #2563eb; }
            QPushButton#searchButton:disabled, QPushButton#calcButton:disabled { background-color: #475569; }
            QPushButton#clearButton {
                background-color: #475569; border: none; border-radius: 6px;
                padding: 10px 18px; font-size: 12px; color: white;
            }
            QPushButton#clearButton:hover { background-color: #64748b; }
            QPushButton#sendButton {
                background-color: #059669; border: none; border-radius: 6px;
                padding: 10px 18px; font-size: 12px; font-weight: bold; color: white;
            }
            QPushButton#sendButton:hover { background-color: #047857; }
            QPushButton#sendButton:disabled { background-color: #475569; }
            QProgressBar {
                border: none; border-radius: 4px; background-color: #1e293b; height: 18px;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #3b82f6, stop:1 #8b5cf6);
                border-radius: 4px;
            }
            QTableWidget {
                background-color: #1e293b; border: 1px solid #3b4252;
                gridline-color: #3b4252; color: #e0e6f0; font-size: 11px;
            }
            QTableWidget::item { padding: 6px; }
            QTableWidget::item:selected { background-color: #3b82f6; }
            QHeaderView::section {
                background-color: #2d3548; color: #a78bfa;
                padding: 6px; border: none; font-weight: bold; font-size: 11px;
            }
            QFrame#separator { background-color: #475569; max-height: 1px; margin: 6px 0; }
        """)

    def update_calculated_values(self):
        """更新计算结果"""
        try:
            m_b        = float(self.param_inputs['m_b'].text())
            f_body_min = float(self.f_body_min.text())
            f_body_max = float(self.f_body_max.text())
            f_tire_min = float(self.f_tire_min.text())
            f_tire_max = float(self.f_tire_max.text())

            k_sum_min, k_sum_max = calc_total_stiffness_range(m_b, f_body_min, f_body_max)
            # ← 显示 N/mm（内部结果 N/m ÷ 1000）
            self.k_sum_range_label.setText(f"{k_sum_min/1000:.2f} ~ {k_sum_max/1000:.2f} N/mm")

            all_valid = True
            invalid_wheels = []

            for suffix in ['A', 'B', 'C', 'D']:
                try:
                    m_w = float(self.param_inputs[f'm_w{suffix}'].text())
                    # ← UI 输入 N/mm，calc_tire_frequency 需要 N/m，乘以 1000
                    k_t_nm = float(self.param_inputs[f'k_t{suffix}'].text()) * 1000
                    f_tire = calc_tire_frequency(m_w, k_t_nm)
                    self.tire_freq_labels[suffix].setText(f"{f_tire:.1f} Hz")

                    if not (f_tire_min <= f_tire <= f_tire_max):
                        all_valid = False
                        invalid_wheels.append(f"{suffix}({f_tire:.1f}Hz)")
                        self.tire_freq_labels[suffix].setStyleSheet("color: #f87171;")
                    else:
                        self.tire_freq_labels[suffix].setStyleSheet("color: #4ade80;")
                except ValueError:
                    self.tire_freq_labels[suffix].setText("--")
                    all_valid = False

            if all_valid:
                self.tire_warning_label.setText("✓ 所有轮胎频率满足约束")
                self.tire_warning_label.setStyleSheet("color: #4ade80;")
            else:
                self.tire_warning_label.setText(f"⚠ 轮胎频率超出范围: {', '.join(invalid_wheels)}")
                self.tire_warning_label.setStyleSheet("color: #f87171;")

            self.calculated_k_sum_range = (k_sum_min, k_sum_max)  # 内部存 N/m

        except ValueError:
            self.k_sum_range_label.setText("输入无效")
            self.tire_warning_label.setText("")
            self.calculated_k_sum_range = None

    def get_base_params(self):
        """获取基础参数，将 UI 的 N/mm、N·s/mm 换算回 N/m、N·s/m"""
        params = self.default_params.copy()

        for key, widget in self.param_inputs.items():
            try:
                val = float(widget.text())
                if key == 'C_f':
                    # N·s/mm → N·s/m （×1000）
                    params['C_sA'] = params['C_sB'] = val * 1000
                elif key == 'C_r':
                    # N·s/mm → N·s/m （×1000）
                    params['C_sC'] = params['C_sD'] = val * 1000
                elif key in ['m_wA', 'm_wB', 'm_wC', 'm_wD']:
                    params[key] = val
                elif key in ['k_tA', 'k_tB', 'k_tC', 'k_tD']:
                    params[key] = val * 1000   # N/mm → N/m
                elif key in ['lever_ratio_f', 'lever_ratio_r']:
                    params[key] = val
                else:
                    params[key] = val
            except ValueError:
                pass

        try:
            params['vehicle_speed'] = float(self.speed_input.text())
            params['duration']      = float(self.duration_input.text())
        except ValueError:
            pass
        params['road_class'] = self.road_combo.currentText()

        return params

    def start_search(self):
        """开始搜索"""
        if self.calculated_k_sum_range is None:
            QMessageBox.warning(self, "错误", "请先正确输入参数计算刚度范围")
            return

        try:
            n_points  = int(self.n_points.text())
            ratio_min = float(self.ratio_min.text())
            ratio_max = float(self.ratio_max.text())
            if n_points < 2:
                raise ValueError
        except ValueError:
            QMessageBox.warning(self, "输入错误", "请检查数值格式")
            return

        if ratio_min >= ratio_max:
            QMessageBox.warning(self, "输入错误", "前后比最小值必须小于最大值")
            return

        self.search_btn.setEnabled(False)
        self.search_btn.setText("扫描中...")
        self.results_table.setRowCount(0)
        self.summary_label.setText("")

        base_params = self.get_base_params()

        defl_limit = None
        if self.defl_check.isChecked():
            try:
                defl_limit = float(self.defl_limit_edit.text()) / 1000.0
            except ValueError:
                QMessageBox.warning(self, "输入错误", "弹簧变化量限制值无效")
                self.search_btn.setEnabled(True)
                self.search_btn.setText("开始扫描RMS")
                return

        self.search_thread = SeparateStiffnessSearchThread(
            base_params,
            self.calculated_k_sum_range,
            (ratio_min, ratio_max),
            n_points,
            defl_limit
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
        """显示结果，刚度列以 N/mm 显示，按RMS排序"""
        results.sort(key=lambda x: x['rms'])

        defl_limit = None
        if self.defl_check.isChecked():
            try:
                defl_limit = float(self.defl_limit_edit.text()) / 1000.0
            except ValueError:
                pass

        self.results_table.setRowCount(len(results))

        for i, r in enumerate(results):
            # ← k_f / k_r 由内部 N/m 转换为 N/mm 显示
            item_kf = QTableWidgetItem(f"{r['k_f']/1000:.3f}")
            item_kf.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.results_table.setItem(i, 0, item_kf)

            item_kr = QTableWidgetItem(f"{r['k_r']/1000:.3f}")
            item_kr.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.results_table.setItem(i, 1, item_kr)

            item_ratio = QTableWidgetItem(f"{r['ratio']:.3f}")
            item_ratio.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.results_table.setItem(i, 2, item_ratio)

            item_f = QTableWidgetItem(f"{r['f_body']:.3f}")
            item_f.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.results_table.setItem(i, 3, item_f)

            defl = r.get('max_defl', 0.0)
            item_d = QTableWidgetItem(f"{defl*1000:.1f} mm")
            item_d.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            if defl_limit:
                ratio_d = defl / defl_limit
                if ratio_d > 1.0:
                    item_d.setForeground(QColor("#f87171"))
                elif ratio_d > 0.85:
                    item_d.setForeground(QColor("#fbbf24"))
                else:
                    item_d.setForeground(QColor("#4ade80"))
            self.results_table.setItem(i, 4, item_d)

            item_rms = QTableWidgetItem(f"{r['rms']:.4f}")
            item_rms.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.results_table.setItem(i, 5, item_rms)

            rms = r['rms']
            if rms < 0.35:
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
            self.results_table.setItem(i, 6, item_rating)

        if results:
            self._best_result = results[0]   # 已按 RMS 升序排列
            self.send_btn.setEnabled(True)
            self.summary_label.setText("扫描完成")
            self.summary_label.setStyleSheet("color: #4ade80;")
        else:
            self.summary_label.setText("⚠ 所有方案均超出弹簧变化量限制，请放宽约束或调整刚度范围")
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