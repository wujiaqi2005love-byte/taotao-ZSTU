"""
弹簧选型窗口（PyQt6版）
Spring Selector Window - PyQt6 Version
整合自原 CustomTkinter 版本，接收共享状态刚度数据
"""

import math
import numpy as np

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QGroupBox,
    QLabel, QLineEdit, QComboBox, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView,
    QMessageBox, QTabWidget, QScrollArea, QFrame,
    QButtonGroup, QRadioButton, QFileDialog
)
from PyQt6.QtCore import Qt, pyqtSlot
from PyQt6.QtGui import QColor, QFont

import matplotlib
matplotlib.use('QtAgg')
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.pyplot as plt

plt.rcParams['font.family'] = 'SimHei'
plt.rcParams['axes.unicode_minus'] = False

from utils.window_base import BaseWindow, DARK_THEME_STYLE
from utils.shared_state import shared_state
from utils.calculators import calc_spring_candidates, wahl_factor


class SpringSelectorWindow(BaseWindow):
    """
    弹簧选型主窗口
    可独立打开，也可接收来自刚度搜索的数据
    """

    def __init__(self, parent=None):
        super().__init__("弹簧选型系统")
        self.setMinimumSize(1300, 850)

        self.candidates = []
        self.target_k_nmm = None
        self.k_min_nmm = None
        self.k_max_nmm = None

        self._setup_ui()

        # 连接共享状态信号
        shared_state.stiffness_updated.connect(self._on_stiffness_received)

        # 如果启动时已有数据，立即加载
        if shared_state.has_data():
            k_min, k_max, k_opt = shared_state.get_stiffness_nmm()
            self._apply_received_stiffness(k_min, k_max, k_opt,
                                           shared_state.source_description)

    # ==================== UI 构建 ====================

    def _setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setSpacing(10)
        root.setContentsMargins(15, 15, 15, 15)

        # 标题
        title_layout = self.create_title_section(
            "弹簧选型系统",
        )
        root.addLayout(title_layout)

        # 来源信息横幅
        self.source_banner = QLabel("📡 等待接收刚度数据...")
        self.source_banner.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.source_banner.setStyleSheet(
            "background-color: #1e3a5f; color: #60a5fa; "
            "padding: 8px; border-radius: 6px; font-size: 12px;"
        )
        root.addWidget(self.source_banner)

        # 主体：左参数 + 右结果
        body = QHBoxLayout()

        left_panel = self._build_left_panel()
        body.addWidget(left_panel, stretch=2)

        right_panel = self._build_right_panel()
        body.addWidget(right_panel, stretch=5)

        root.addLayout(body)

    def _build_left_panel(self) -> QWidget:
        """左侧参数面板"""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setSpacing(10)

        # ── 刚度信息 ──
        k_group = QGroupBox("刚度约束（来自舒适度分析）")
        k_layout = QGridLayout(k_group)

        k_layout.addWidget(QLabel("最小刚度 (N/mm)"), 0, 0)
        self.k_min_edit = QLineEdit("--")
        self.k_min_edit.setReadOnly(True)
        self.k_min_edit.setStyleSheet("color: #4ade80;")
        k_layout.addWidget(self.k_min_edit, 0, 1)

        k_layout.addWidget(QLabel("最大刚度 (N/mm)"), 1, 0)
        self.k_max_edit = QLineEdit("--")
        self.k_max_edit.setReadOnly(True)
        self.k_max_edit.setStyleSheet("color: #4ade80;")
        k_layout.addWidget(self.k_max_edit, 1, 1)

        k_layout.addWidget(QLabel("目标刚度 (N/mm)"), 2, 0)
        self.k_target_edit = QLineEdit("")
        self.k_target_edit.setPlaceholderText("自动填充或手动输入")
        k_layout.addWidget(self.k_target_edit, 2, 1)

        layout.addWidget(k_group)

        # ── 系统参数 ──
        sys_group = QGroupBox("系统参数")
        sys_layout = QGridLayout(sys_group)

        sys_layout.addWidget(QLabel("等效质量 (kg)"), 0, 0)
        self.mass_edit = QLineEdit("--")
        self.mass_edit.setFixedHeight(25)
        self.mass_edit.setReadOnly(True)
        self.mass_edit.setPlaceholderText("请先从刚度搜索导入车身质量")
        self.mass_edit.setStyleSheet("color: #94a3b8; background-color: #1f2937;")
        sys_layout.addWidget(self.mass_edit, 0, 1)

        sys_layout.addWidget(QLabel("阻尼比(0.25~0.4)"), 1, 0)
        self.zeta_edit = QLineEdit("0.3")
        self.zeta_edit.setFixedHeight(25)
        sys_layout.addWidget(self.zeta_edit, 1, 1)

        sys_layout.addWidget(QLabel("最大总行程 (mm)"), 2, 0)
        self.delta_edit = QLineEdit("50")
        self.delta_edit.setFixedHeight(25)
        self.delta_edit.setPlaceholderText("含预压缩后的总可压缩量")
        sys_layout.addWidget(self.delta_edit, 2, 1)

        sys_layout.addWidget(QLabel("预压缩 (mm)"), 3, 0)
        self.preload_edit = QLineEdit("5")
        self.preload_edit.setFixedHeight(25)
        self.preload_edit.setPlaceholderText("安装时弹簧预压缩量")
        sys_layout.addWidget(self.preload_edit, 3, 1)

        # 预压缩建议按钮
        self.suggest_preload_btn = QPushButton("💡 建议预压缩范围")
        self.suggest_preload_btn.setFixedHeight(34)
        self.suggest_preload_btn.setFixedWidth(170)
        self.suggest_preload_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:0,
                    stop:0 #2563eb, stop:1 #4338ca
                );
                color: white;
                border: none;
                border-radius: 6px;
                font-size: 12px;
                padding: 6px 10px;
            }
            QPushButton:hover {
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:0,
                    stop:0 #3b82f6, stop:1 #6366f1
                );
            }
        """)
        self.suggest_preload_btn.clicked.connect(self._suggest_preload)
        sys_layout.addWidget(self.suggest_preload_btn, 3, 2, 1, 1, Qt.AlignmentFlag.AlignVCenter)

        sys_layout.addWidget(QLabel("端部密圈系数"), 4, 0)
        self.end_coeff_edit = QLineEdit("1.0")
        self.end_coeff_edit.setFixedHeight(25)
        self.end_coeff_edit.setPlaceholderText("0.6~1.0")
        sys_layout.addWidget(self.end_coeff_edit, 4, 1)

        layout.addWidget(sys_group)

        # ── 材料选择 ──
        mat_group = QGroupBox("弹簧材料")
        mat_layout = QVBoxLayout(mat_group)

        self.mat_group_btn = QButtonGroup(self)
        materials = [
            ("普通碳弹簧钢  G=79000 τ=800", 0, 79000, 800),
            ("油回火弹簧钢  G=80000 τ=950", 1, 80000, 950),
            ("不锈钢弹簧丝  G=70000 τ=700", 2, 70000, 700),
        ]
        self._material_data = {}
        for text, idx, G, tau in materials:
            rb = QRadioButton(text)
            if idx == 0:
                rb.setChecked(True)
            self.mat_group_btn.addButton(rb, idx)
            mat_layout.addWidget(rb)
            self._material_data[idx] = (G, tau)

        # 自定义材料选项
        self.custom_rb = QRadioButton("自定义材料")
        self.mat_group_btn.addButton(self.custom_rb, 3)
        mat_layout.addWidget(self.custom_rb)

        custom_layout = QHBoxLayout() # 水平布局放置两个输入框
        custom_layout.addWidget(QLabel("剪切模量 G (MPa):"))
        self.custom_G_edit = QLineEdit("79000") # 默认值与普通碳弹簧钢相同
        self.custom_G_edit.setFixedHeight(25)
        self.custom_G_edit.setFixedWidth(70)
        self.custom_G_edit.setEnabled(False)
        custom_layout.addWidget(self.custom_G_edit)

        custom_layout.addWidget(QLabel("许用剪应力 τ (MPa):"))
        self.custom_tau_edit = QLineEdit("800") # 默认值与普通碳弹簧钢相同
        self.custom_tau_edit.setFixedHeight(25)
        self.custom_tau_edit.setFixedWidth(70)
        self.custom_tau_edit.setEnabled(False)
        custom_layout.addWidget(self.custom_tau_edit)

        mat_layout.addLayout(custom_layout)

        # 连接信号以启用/禁用自定义输入
        self.custom_rb.toggled.connect(self._toggle_custom_material)

        layout.addWidget(mat_group)

        # ── 操作按钮 ──
        self.calc_btn = QPushButton("▶ 计算最优弹簧方案")
        self.calc_btn.setMinimumHeight(45)
        self.calc_btn.clicked.connect(self._calculate)
        layout.addWidget(self.calc_btn)

        self.export_btn = QPushButton("📥 导出 Excel")
        self.export_btn.setMinimumHeight(38)
        self.export_btn.clicked.connect(self._export_excel)
        layout.addWidget(self.export_btn)

        self.reset_btn = QPushButton("↺ 重置参数")
        self.reset_btn.setObjectName("clearButton")
        self.reset_btn.setMinimumHeight(38)
        self.reset_btn.clicked.connect(self._reset)
        layout.addWidget(self.reset_btn)

        layout.addStretch()
        return panel

    def _toggle_custom_material(self, checked):
        """启用或禁用自定义材料输入"""
        self.custom_G_edit.setEnabled(checked)
        self.custom_tau_edit.setEnabled(checked)

    def _suggest_preload(self):
        """根据车辆参数建议预压缩范围"""
        try:
            mass = float(self.mass_edit.text())
            target_k_text = self.k_target_edit.text().strip()
            
            if mass <= 0:
                QMessageBox.warning(self, "输入错误", "车辆质量必须大于0")
                return
            
            # 计算静态负载力（单轮）
            static_force_per_wheel = (mass * 9.81) / 4  # N
            
            if target_k_text:
                # 如果有目标刚度，计算建议预压缩
                target_k = float(target_k_text)
                if target_k <= 0:
                    raise ValueError("目标刚度必须大于0")
                
                # 建议预压缩范围：基于静态负载的0.8-1.2倍
                preload_min = (static_force_per_wheel * 0.8) / target_k  # mm
                preload_max = (static_force_per_wheel * 1.2) / target_k  # mm
                
                suggested_range = f"{preload_min:.1f} ~ {preload_max:.1f} mm"
                self.preload_edit.setPlaceholderText(f"建议范围：{suggested_range}")
                QMessageBox.information(
                    self, "预压缩建议", 
                    f"基于车辆质量 {mass} kg 和目标刚度 {target_k} N/mm，\n"
                    f"建议预压缩范围：{suggested_range}\n\n"
                    f"（计算依据：静态负载×0.8~1.2 / 刚度）"
                )
            else:
                # 没有目标刚度，只显示静态负载信息
                QMessageBox.information(
                    self, "预压缩建议", 
                    f"车辆质量：{mass} kg\n"
                    f"单轮静态负载：{static_force_per_wheel:.1f} N\n\n"
                    f"请先输入目标刚度，然后重新点击此按钮获取具体范围。"
                )
                
        except ValueError as e:
            QMessageBox.warning(self, "输入错误", f"参数格式错误：{str(e)}")

    def _build_right_panel(self) -> QWidget:
        """右侧结果面板"""
        panel = QWidget()
        layout = QVBoxLayout(panel)

        self.tab_widget = QTabWidget()
        self.tab_widget.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #3b4252;
                border-radius: 6px;
                background-color: #1e293b;
            }
            QTabBar::tab {
                background-color: #2d3548;
                color: #94a3b8;
                padding: 8px 20px;
                border-radius: 4px 4px 0 0;
                margin-right: 2px;
            }
            QTabBar::tab:selected {
                background-color: #3b82f6;
                color: white;
            }
        """)

        # Tab1: 推荐方案
        self.tab_recommend = QScrollArea()
        self.tab_recommend.setWidgetResizable(True)
        self.recommend_content = QWidget()
        self.recommend_layout = QVBoxLayout(self.recommend_content)
        self.tab_recommend.setWidget(self.recommend_content)
        self.tab_widget.addTab(self.tab_recommend, "🏆 推荐方案")

        # Tab2: 完整参数表
        self.tab_table = QWidget()
        table_layout = QVBoxLayout(self.tab_table)

        # 排序控件
        sort_bar = QHBoxLayout()
        sort_bar.addWidget(QLabel("排序方式："))
        self.sort_combo = QComboBox()
        self.sort_combo.addItems(["刚度匹配度", "应力裕度", "阻尼系数"])
        self.sort_combo.currentTextChanged.connect(self._refresh_table)
        sort_bar.addWidget(self.sort_combo)
        sort_bar.addStretch()
        table_layout.addLayout(sort_bar)

        self.result_table = QTableWidget()
        self.result_table.setColumnCount(13)
        self.result_table.setHorizontalHeaderLabels([
            "序号", "线径d(mm)", "中径D(mm)", "旋绕比C",
            "有效圈Na", "总圈数", "预压缩(mm)", "剩余行程(mm)",
            "实际刚度(N/mm)", "刚度偏差%", "剪应力(MPa)",
            "应力裕度%", "阻尼c(N·s/m)"
        ])
        self.result_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        self.result_table.setAlternatingRowColors(False)
        self.result_table.setStyleSheet(
            "QTableWidget { background-color: #0f172a; alternate-background-color: #0f172a; }"
        )
        self.result_table.setSelectionBehavior(
            QTableWidget.SelectionBehavior.SelectRows
        )
        self.result_table.itemSelectionChanged.connect(self._refresh_chart)
        table_layout.addWidget(self.result_table)

        self.tab_widget.addTab(self.tab_table, "📊 完整参数表")

        # Tab3: 可视化
        self.tab_visual = QWidget()
        visual_layout = QVBoxLayout(self.tab_visual)

        chart_bar = QHBoxLayout()
        chart_bar.addWidget(QLabel("图表类型："))
        self.chart_combo = QComboBox()
        self.chart_combo.addItems([
            "刚度对比", "应力分布", "阻尼系数趋势", "刚度偏差率",
            "压缩后有效刚度曲线"
        ])
        self.chart_combo.currentTextChanged.connect(self._refresh_chart)
        chart_bar.addWidget(self.chart_combo)
        chart_bar.addStretch()
        visual_layout.addLayout(chart_bar)

        self.chart_fig = Figure(figsize=(8, 4), dpi=100)
        self.chart_fig.patch.set_facecolor('#0f172a')
        self.chart_canvas = FigureCanvas(self.chart_fig)
        visual_layout.addWidget(self.chart_canvas)

        self.tab_widget.addTab(self.tab_visual, "📈 可视化")

        layout.addWidget(self.tab_widget)

        # 汇总标签
        self.summary_label = QLabel("请先完成刚度搜索，再进行弹簧选型计算")
        self.summary_label.setStyleSheet(
            "color: #64748b; font-size: 12px; padding: 6px;"
        )
        layout.addWidget(self.summary_label)

        return panel

    # ==================== 信号响应 ====================

    @pyqtSlot(float, float, str)
    def _on_stiffness_received(self, k_min: float, k_max: float, source: str):
        """接收来自刚度搜索的信号"""
        k_min_mm = k_min / 1000
        k_max_mm = k_max / 1000
        k_opt_mm = shared_state.k_optimal / 1000

        self._apply_received_stiffness(k_min_mm, k_max_mm, k_opt_mm, source)

    def _apply_received_stiffness(
        self,
        k_min_mm: float,
        k_max_mm: float,
        k_opt_mm: float,
        source: str
    ):
        """将接收到的刚度写入UI"""
        self.k_min_nmm = k_min_mm
        self.k_max_nmm = k_max_mm
        self.target_k_nmm = k_opt_mm

        self.k_min_edit.setText(f"{k_min_mm:.3f}")
        self.k_max_edit.setText(f"{k_max_mm:.3f}")
        self.k_target_edit.setText(f"{k_opt_mm:.3f}")

        # 如果共享了车身质量，填入质量框
        if shared_state.vehicle_mass is not None:
            # 单个悬架的等效质量 ≈ 车身质量 / 4
            self.mass_edit.setText(f"{shared_state.vehicle_mass / 4:.1f}")
            self.mass_edit.setStyleSheet("color: #4ade80; background-color: #0f172a;")
        else:
            self.mass_edit.setText("--")
            self.mass_edit.setStyleSheet("color: #94a3b8; background-color: #1f2937;")

        self.source_banner.setText(
            f"✅ 已接收刚度数据  来源：{source}  "
            f"范围：{k_min_mm:.2f} ~ {k_max_mm:.2f} N/mm  "
            f"目标：{k_opt_mm:.2f} N/mm"
        )
        self.source_banner.setStyleSheet(
            "background-color: #14532d; color: #4ade80; "
            "padding: 8px; border-radius: 6px; font-size: 12px;"
        )

    # ==================== 计算逻辑 ====================

    def _calculate(self):
        """执行弹簧选型计算"""
        try:
            target_k = float(self.k_target_edit.text())
            delta_max = float(self.delta_edit.text())
            preload_mm = float(self.preload_edit.text())
            mass_text = self.mass_edit.text().strip()
            if not mass_text or mass_text == "--":
                raise ValueError("请先从刚度搜索导入车身质量后再进行计算")
            mass = float(mass_text)
            zeta = float(self.zeta_edit.text())
            end_coeff = float(self.end_coeff_edit.text())

            if not (0.1 <= zeta <= 0.7):
                raise ValueError("阻尼比建议范围 0.1 ~ 0.7")
            if not (0.6 <= end_coeff <= 1.0):
                raise ValueError("密圈系数范围 0.6 ~ 1.0")
            if preload_mm < 0:
                raise ValueError("预压缩应为非负值")
            if preload_mm >= delta_max:
                raise ValueError("预压缩应小于最大总行程")

            mat_id = self.mat_group_btn.checkedId()
            if mat_id == 3:  # 自定义材料
                G = float(self.custom_G_edit.text())
                tau_allow = float(self.custom_tau_edit.text())
            else:
                G, tau_allow = self._material_data[mat_id]

        except ValueError as e:
            QMessageBox.warning(self, "输入错误", str(e))
            return

        self.target_k_nmm = target_k
        self.candidates = calc_spring_candidates(
            target_k_nmm=target_k,
            delta_max_mm=delta_max,
            preload_mm=preload_mm,
            mass_kg=mass,
            zeta=zeta,
            end_coeff=end_coeff,
            G=G,
            tau_allow=tau_allow
        )

        if not self.candidates:
            QMessageBox.warning(self, "无结果", "未找到满足条件的弹簧方案，请调整参数")
            return

        self._sort_candidates()
        self._update_recommend_tab()
        self._refresh_table()
        self._refresh_chart()

        self.summary_label.setText(
            f"✅ 共找到 {len(self.candidates)} 个方案  "
            f"目标刚度：{target_k} N/mm  "
            f"最优方案：d={self.candidates[0]['d']}mm  "
            f"D={self.candidates[0]['D']}mm  "
            f"偏差 {self.candidates[0]['k_deviation']}%"
        )
        self.summary_label.setStyleSheet("color: #4ade80; font-size: 12px; padding: 6px;")

    def _sort_candidates(self):
        """按当前排序方式排序候选方案"""
        mode = self.sort_combo.currentText()
        if mode == "刚度匹配度":
            self.candidates.sort(key=lambda x: x['k_deviation'])
        elif mode == "应力裕度":
            self.candidates.sort(key=lambda x: -x['margin_pct'])
        elif mode == "阻尼系数":
            self.candidates.sort(key=lambda x: x['c_damper'])

    def _update_recommend_tab(self):
        """刷新推荐方案标签页"""
        # 清空旧内容
        while self.recommend_layout.count():
            item = self.recommend_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        colors = ["#f59e0b", "#94a3b8", "#b45309", "#60a5fa", "#a78bfa"]

        for i, c in enumerate(self.candidates[:5]):
            card = QFrame()
            card.setStyleSheet(
                "QFrame { background-color: #1e293b; border: 1px solid #3b4252; "
                "border-radius: 8px; margin: 4px; }"
            )
            card_layout = QVBoxLayout(card)

            # 标题行
            title_row = QHBoxLayout()
            rank_label = QLabel(f"方案 {i + 1}")
            rank_label.setStyleSheet(
                f"color: {colors[i % len(colors)]}; "
                f"font-weight: bold; font-size: 14px;"
            )
            title_row.addWidget(rank_label)

            # 应力状态指示灯
            dot_color = (
                "#4ade80" if c['margin_pct'] > 40
                else "#fbbf24" if c['margin_pct'] > 15
                else "#f87171"
            )
            dot = QLabel("●")
            dot.setStyleSheet(f"color: {dot_color}; font-size: 16px;")
            title_row.addStretch()
            title_row.addWidget(dot)
            card_layout.addLayout(title_row)

            # 参数行
            params_text = [
                f"线径 d = {c['d']} mm　　中径 D = {c['D']} mm　　旋绕比 C = {c['winding_ratio']}",
                f"有效圈 Na = {c['Na']}　　总圈数 = {c['total_coils']}　　密圈系数 = {c['end_coeff']}",
                f"预压缩 = {c['preload_mm']} mm　预压缩力 = {c['preload_force']} N",
                f"剩余可动行程 = {c['remaining_travel']} mm　实际刚度 = {c['actual_k']} N/mm",
                f"剪应力 = {c['tau']} MPa　　应力裕度 = {c['margin_pct']}%",
                f"推荐阻尼系数 c = {c['c_damper']} N·s/mm",
            ]
            param_colors = [
                "#e0e6f0", "#94a3b8", "#60a5fa",
                "#60a5fa", "#4ade80" if c['margin_pct'] > 30 else "#fbbf24",
                "#60a5fa"
            ]
            for text, color in zip(params_text, param_colors):
                lbl = QLabel(text)
                lbl.setStyleSheet(f"color: {color}; font-size: 12px;")
                card_layout.addWidget(lbl)

            self.recommend_layout.addWidget(card)

        self.recommend_layout.addStretch()

    def _refresh_table(self):
        """刷新完整参数表"""
        if not self.candidates:
            return

        self._sort_candidates()
        display = self.candidates[:30]
        self.result_table.setRowCount(len(display))

        for i, c in enumerate(display):
            values = [
                str(i + 1), str(c['d']), str(c['D']),
                str(c['winding_ratio']), str(c['Na']),
                str(c['total_coils']), str(c['preload_mm']),
                str(c['remaining_travel']), str(c['actual_k']),
                str(c['k_deviation']), str(c['tau']),
                str(c['margin_pct']), str(c['c_damper'])
            ]
            for col, val in enumerate(values):
                item = QTableWidgetItem(val)
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                # 应力裕度着色
                if col == 9:
                    margin = c['margin_pct']
                    color = (
                        QColor("#4ade80") if margin > 40
                        else QColor("#fbbf24") if margin > 15
                        else QColor("#f87171")
                    )
                    item.setForeground(color)
                self.result_table.setItem(i, col, item)

    def _refresh_chart(self):
        """刷新可视化图表"""
        if not self.candidates:
            return

        self.chart_fig.clear()
        ax = self.chart_fig.add_subplot(111)
        ax.set_facecolor('#1e293b')

        top = self.candidates[:10]
        xs = [f"方案{i + 1}" for i in range(len(top))]
        chart_type = self.chart_combo.currentText()

        if chart_type == "刚度对比":
            ax.plot(xs, [self.target_k_nmm] * len(top),
                    'o--', color='#fbbf24', label='目标刚度', linewidth=2)
            ax.plot(xs, [c['actual_k'] for c in top],
                    's-', color='#4ade80', label='实际刚度', linewidth=2)
            ax.set_ylabel('刚度 (N/mm)', color='#94a3b8')
            ax.legend(facecolor='#1e293b', edgecolor='#3b4252',
                      labelcolor='#e0e6f0')

        elif chart_type == "应力分布":
            mat_id = self.mat_group_btn.checkedId()
            if mat_id == 3:  # 自定义材料
                tau_allow = float(self.custom_tau_edit.text())
            else:
                _, tau_allow = self._material_data[mat_id]
            bars = ax.bar(xs, [c['tau'] for c in top],
                          color='#3b82f6', alpha=0.8)
            ax.axhline(tau_allow / 1.25, color='#f87171',
                       linestyle='--', linewidth=2, label='许用应力')
            ax.set_ylabel('剪应力 (MPa)', color='#94a3b8')
            ax.legend(facecolor='#1e293b', edgecolor='#3b4252',
                      labelcolor='#e0e6f0')

        elif chart_type == "阻尼系数趋势":
            ax.plot(xs, [c['c_damper'] for c in top],
                    'o-', color='#a78bfa', linewidth=2, markersize=6)
            ax.set_ylabel('阻尼系数 (N·s/m)', color='#94a3b8')

        elif chart_type == "压缩后有效刚度曲线":
            row = self.result_table.currentRow()
            if row < 0 or row >= len(self.candidates):
                c = self.candidates[0]
                selected_index = 1
            else:
                c = self.candidates[row]
                selected_index = row + 1

            xs = np.linspace(0, max(c['remaining_travel'], 0.1), 50)
            ys = c['preload_force'] + c['actual_k'] * xs
            ax.plot(xs, ys, '-', color='#4ade80', linewidth=2)
            ax.fill_between(xs, ys, color='#4ade80', alpha=0.2)
            ax.set_ylabel('力 (N)', color='#94a3b8')
            ax.set_xlabel('附加压缩量 (mm)', color='#94a3b8')
            ax.set_title(
                f"方案 {selected_index}：压缩后力-位移曲线",
                color='#e0e6f0', fontsize=12
            )
            ax.text(0.02, 0.88,
                    f"预压缩={c['preload_mm']}mm  预压缩力={c['preload_force']}N  k={c['actual_k']}N/mm",
                    transform=ax.transAxes,
                    color='#cbd5e1', fontsize=9,
                    bbox=dict(facecolor='#1e293b', alpha=0.7, edgecolor='none'))

        elif chart_type == "刚度偏差率":
            colors_bar = [
                '#4ade80' if c['k_deviation'] < 5
                else '#fbbf24' if c['k_deviation'] < 10
                else '#f87171'
                for c in top
            ]
            ax.bar(xs, [c['k_deviation'] for c in top],
                   color=colors_bar, alpha=0.85)
            ax.axhline(5, color='#f87171', linestyle='--',
                       linewidth=1.5, label='5%警戒线')
            ax.set_ylabel('偏差率 (%)', color='#94a3b8')
            ax.legend(facecolor='#1e293b', edgecolor='#3b4252',
                      labelcolor='#e0e6f0')

        if chart_type != "压缩后有效刚度曲线":
            ax.set_title(chart_type, color='#e0e6f0', fontsize=12)
            ax.set_xlabel('方案', color='#94a3b8')
        ax.tick_params(colors='#64748b', labelsize=9)
        for spine in ax.spines.values():
            spine.set_edgecolor('#3b4252')

        self.chart_fig.tight_layout()
        self.chart_canvas.draw()

    def _export_excel(self):
        """导出结果到 Excel"""
        if not self.candidates:
            QMessageBox.warning(self, "无数据", "请先完成计算")
            return
        try:
            import pandas as pd
            path, _ = QFileDialog.getSaveFileName(
                self, "保存Excel", "弹簧选型结果.xlsx",
                "Excel文件 (*.xlsx)"
            )
            if not path:
                return
            df = pd.DataFrame(self.candidates)
            df.insert(0, '方案序号', range(1, len(df) + 1))

            # 中文列名映射
            column_mapping = {
                'd': '线径(mm)',
                'D': '中径(mm)',
                'Na': '有效圈数',
                'actual_k': '实际刚度(N/mm)',
                'tau': '剪应力(MPa)',
                'margin_pct': '应力裕度(%)',
                'c_damper': '阻尼系数(N·s/m)',
                'k_deviation': '刚度偏差(%)',
                'end_coeff': '端部密圈系数',
                'total_coils': '总圈数',
                'winding_ratio': '旋绕比',
                'preload_mm': '预压缩(mm)',
                'remaining_travel': '剩余行程(mm)',
                'preload_force': '预压缩力(N)'
            }
            df.rename(columns=column_mapping, inplace=True)

            df.to_excel(path, index=False)
            QMessageBox.information(self, "导出成功", f"已保存至：{path}")
        except ImportError:
            QMessageBox.warning(self, "缺少依赖", "请安装 pandas 和 openpyxl")
        except Exception as e:
            QMessageBox.critical(self, "导出失败", str(e))

    def _reset(self):
        """重置输入参数"""
        self.k_min_edit.setText("--")
        self.k_max_edit.setText("--")
        self.k_target_edit.clear()
        self.mass_edit.setText("--")
        self.mass_edit.setStyleSheet("color: #94a3b8; background-color: #1f2937;")
        self.zeta_edit.setText("0.3")
        self.delta_edit.setText("50")
        self.end_coeff_edit.setText("1.0")
        self.preload_edit.setText("5")
        self.preload_edit.setPlaceholderText("安装时弹簧预压缩量")
        self.mat_group_btn.button(0).setChecked(True)
        self.custom_G_edit.setText("79000")
        self.custom_tau_edit.setText("800")
        self.candidates = []
        self.result_table.setRowCount(0)
        while self.recommend_layout.count():
            item = self.recommend_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self.source_banner.setText("📡 等待接收刚度数据...")
        self.source_banner.setStyleSheet(
            "background-color: #1e3a5f; color: #60a5fa; "
            "padding: 8px; border-radius: 6px; font-size: 12px;"
        )
        self.summary_label.setText("参数已重置")
        self.summary_label.setStyleSheet("color: #64748b; font-size: 12px; padding: 6px;")