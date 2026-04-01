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


class Spring3DWidget(QWidget):
    """弹簧3D可视化组件"""

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)

        self.fig = Figure(figsize=(6, 5), dpi=100)
        self.fig.patch.set_facecolor('#0f172a')
        self.canvas = FigureCanvas(self.fig)
        layout.addWidget(self.canvas)

    def plot_spring(self, d, D, Na, end_coeff=1.0):
        """绘制弹簧3D模型"""
        self.fig.clear()
        ax = self.fig.add_subplot(111, projection='3d')
        ax.set_facecolor('#1e293b')

        R = D / 2
        pitch_normal = D * 0.8
        pitch_end = pitch_normal * (1 - end_coeff)

        theta = np.linspace(0, 2 * np.pi * (Na + 2), 800)
        z = np.zeros_like(theta)

        m1 = theta <= 2 * np.pi * 0.5
        z[m1] = pitch_end * theta[m1] / (2 * np.pi)

        m2 = (theta > 2 * np.pi * 0.5) & (theta <= 2 * np.pi * (0.5 + Na))
        z[m2] = (pitch_end * 0.5
                 + pitch_normal * (theta[m2] - 2 * np.pi * 0.5) / (2 * np.pi))

        m3 = theta > 2 * np.pi * (0.5 + Na)
        z[m3] = (pitch_end * 0.5 + pitch_normal * Na
                 + pitch_end * (theta[m3] - 2 * np.pi * (0.5 + Na)) / (2 * np.pi))

        x = R * np.cos(theta)
        y = R * np.sin(theta)

        ax.plot(x, y, z, color='#58a6ff', linewidth=2.5)
        ax.set_xlabel('X (mm)', color='#94a3b8', fontsize=8)
        ax.set_ylabel('Y (mm)', color='#94a3b8', fontsize=8)
        ax.set_zlabel('Z (mm)', color='#94a3b8', fontsize=8)
        ax.set_title(
            f'弹簧3D预览  d={d}mm  D={D}mm  Na={Na}',
            color='#e0e6f0', fontsize=10
        )
        ax.tick_params(colors='#64748b', labelsize=7)
        ax.view_init(elev=25, azim=45)

        self.canvas.draw()


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
            "Spring Selection System | 基于七自由度舒适度分析结果"
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
        self.mass_edit = QLineEdit("50")
        sys_layout.addWidget(self.mass_edit, 0, 1)

        sys_layout.addWidget(QLabel("阻尼比 ζ (0.25~0.4)"), 1, 0)
        self.zeta_edit = QLineEdit("0.3")
        sys_layout.addWidget(self.zeta_edit, 1, 1)

        sys_layout.addWidget(QLabel("最大压缩量 (mm)"), 2, 0)
        self.delta_edit = QLineEdit("50")
        sys_layout.addWidget(self.delta_edit, 2, 1)


        sys_layout.addWidget(QLabel("端部密圈系数"), 3, 0)
        self.end_coeff_edit = QLineEdit("1.0")
        self.end_coeff_edit.setPlaceholderText("0.6~1.0")
        sys_layout.addWidget(self.end_coeff_edit, 3, 1)

        # ── 预压缩量输入 ──
        pre_group = QGroupBox("四方位弹簧预压缩量 (mm)")
        pre_layout = QGridLayout(pre_group)
        self.preload_edits = {}
        pos_labels = ["左前", "右前", "左后", "右后"]
        for i, label in enumerate(pos_labels):
            pre_layout.addWidget(QLabel(label), i, 0)
            edit = QLineEdit("0")
            edit.setPlaceholderText("请输入预压缩量")
            pre_layout.addWidget(edit, i, 1)
            self.preload_edits[label] = edit
        layout.addWidget(pre_group)

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
        self.result_table.setColumnCount(11)
        self.result_table.setHorizontalHeaderLabels([
            "序号", "线径d(mm)", "中径D(mm)", "旋绕比C",
            "有效圈Na", "总圈数", "实际刚度(N/mm)",
            "刚度偏差%", "剪应力(MPa)", "应力裕度%", "阻尼c(N·s/m)"
        ])
        self.result_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        self.result_table.setAlternatingRowColors(True)
        self.result_table.setSelectionBehavior(
            QTableWidget.SelectionBehavior.SelectRows
        )
        self.result_table.itemSelectionChanged.connect(self._on_table_select)
        table_layout.addWidget(self.result_table)

        self.tab_widget.addTab(self.tab_table, "📊 完整参数表")

        # Tab3: 可视化
        self.tab_visual = QWidget()
        visual_layout = QVBoxLayout(self.tab_visual)

        chart_bar = QHBoxLayout()
        chart_bar.addWidget(QLabel("图表类型："))
        self.chart_combo = QComboBox()
        self.chart_combo.addItems([
            "刚度对比", "应力分布", "阻尼系数趋势", "刚度偏差率"
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

        # Tab4: 3D预览
        self.tab_3d = QWidget()
        tab3d_layout = QVBoxLayout(self.tab_3d)
        self.spring_3d = Spring3DWidget()
        tab3d_layout.addWidget(self.spring_3d)
        self.tab_3d_info = QLabel("选中表格中的方案以预览3D模型")
        self.tab_3d_info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.tab_3d_info.setStyleSheet("color: #64748b;")
        tab3d_layout.addWidget(self.tab_3d_info)
        self.tab_widget.addTab(self.tab_3d, "🔩 3D预览")

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
        if shared_state.vehicle_mass:
            # 单个悬架的等效质量 ≈ 车身质量 / 4
            self.mass_edit.setText(
                f"{shared_state.vehicle_mass / 4:.1f}"
            )

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
            mass = float(self.mass_edit.text())
            zeta = float(self.zeta_edit.text())
            end_coeff = float(self.end_coeff_edit.text())

            # 读取四方位预压缩量
            preload_values = {}
            for pos, edit in self.preload_edits.items():
                val = float(edit.text())
                preload_values[pos] = val

            if not (0.1 <= zeta <= 0.7):
                raise ValueError("阻尼比建议范围 0.1 ~ 0.7")
            if not (0.6 <= end_coeff <= 1.0):
                raise ValueError("密圈系数范围 0.6 ~ 1.0")

            mat_id = self.mat_group_btn.checkedId()
            G, tau_allow = self._material_data[mat_id]

        except ValueError as e:
            QMessageBox.warning(self, "输入错误", str(e))
            return

        self.target_k_nmm = target_k
        # 预压缩量可在此传递给后续计算或保存
        self.preload_values = preload_values
        self.candidates = calc_spring_candidates(
            target_k_nmm=target_k,
            delta_max_mm=delta_max,
            mass_kg=mass,
            zeta=zeta,
            end_coeff=end_coeff,
            G=G,
            tau_allow=tau_allow
            # 如需传递预压缩量，可在此添加参数
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
                f"实际刚度 = {c['actual_k']} N/mm（偏差 {c['k_deviation']}%）",
                f"剪应力 = {c['tau']} MPa　　应力裕度 = {c['margin_pct']}%",
                f"推荐阻尼系数 c = {c['c_damper']} N·s/m",
            ]
            param_colors = [
                "#e0e6f0", "#94a3b8", "#60a5fa",
                "#4ade80" if c['margin_pct'] > 30 else "#fbbf24",
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
                str(c['total_coils']), str(c['actual_k']),
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

        ax.set_title(chart_type, color='#e0e6f0', fontsize=12)
        ax.tick_params(colors='#64748b', labelsize=9)
        ax.set_xlabel('方案', color='#94a3b8')
        for spine in ax.spines.values():
            spine.set_edgecolor('#3b4252')

        self.chart_fig.tight_layout()
        self.chart_canvas.draw()

    def _on_table_select(self):
        """表格选中行 → 更新3D预览"""
        rows = self.result_table.selectedItems()
        if not rows:
            return
        row = self.result_table.currentRow()
        if row < len(self.candidates):
            c = self.candidates[row]
            self.spring_3d.plot_spring(
                c['d'], c['D'], c['Na'], c['end_coeff']
            )
            self.tab_3d_info.setText(
                f"d={c['d']}mm  D={c['D']}mm  "
                f"Na={c['Na']}  刚度={c['actual_k']}N/mm"
            )
            self.tab_3d_info.setStyleSheet("color: #4ade80; font-size: 12px;")

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
        self.mass_edit.setText("50")
        self.zeta_edit.setText("0.3")
        self.delta_edit.setText("50")
        self.end_coeff_edit.setText("1.0")
        self.mat_group_btn.button(0).setChecked(True)
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