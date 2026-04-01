"""
主线程分步执行器
完全避免 QThread，用 QTimer 逐步执行搜索
"""

import numpy as np
from PyQt6.QtCore import QObject, QTimer, pyqtSignal
from scipy.integrate import odeint


class MainThreadSearchRunner(QObject):
    """在主线程中逐步执行刚度搜索"""

    progress_updated = pyqtSignal(int, str)
    search_finished = pyqtSignal(list)
    error_occurred = pyqtSignal(str)

    def __init__(self, base_params, k_values, parent=None):
        super().__init__(parent)
        self.base_params = base_params.copy()
        self.k_values = list(k_values)
        self.results = []
        self.current_idx = 0
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._step)

    def start(self):
        self.current_idx = 0
        self.results = []

        from core.models import RoadExcitation, SevenDOFModel
        self._RoadExcitation = RoadExcitation
        self._SevenDOFModel = SevenDOFModel

        p = self.base_params
        duration_road = p.get('duration', 10) + 3
        np.random.seed(42)
        self._road = RoadExcitation(
            p.get('road_class', 'C'),
            p.get('vehicle_speed', 20),
            duration_road, n_samples=8000
        )
        self._roads = {
            'A': self._road, 'B': self._road,
            'C': self._road, 'D': self._road
        }

        # 每步间隔10ms，让Qt事件循环有喘息空间
        self.timer.start(10)

    def stop(self):
        self.timer.stop()

    def _step(self):
        """执行一步计算"""
        if self.current_idx >= len(self.k_values):
            self.timer.stop()
            self.search_finished.emit(self.results)
            return

        idx = self.current_idx
        k_s = self.k_values[idx]
        total = len(self.k_values)

        self.progress_updated.emit(
            int((idx / total) * 95),
            f"计算 {idx+1}/{total}  k={k_s:.0f} N/m"
        )

        p = self.base_params.copy()
        p['k_sA'] = p['k_sB'] = p['k_sC'] = p['k_sD'] = float(k_s)

        try:
            model = self._SevenDOFModel(p, self._roads)
            duration = p.get('duration', 10)
            n_points = int(duration * 300)
            t = np.linspace(0, duration, n_points)
            y0 = np.zeros(14)

            solution = odeint(
                model, y0, t,
                rtol=1e-4, atol=1e-4, mxstep=5000
            )

            skip = int(n_points * 0.15)
            a_body = np.zeros(n_points - skip)
            for i in range(skip, n_points):
                deriv = model(solution[i], t[i])
                a_body[i - skip] = deriv[7]

            rms = float(np.sqrt(np.mean(a_body ** 2)))
            m_b = p.get('m_b', 1380)
            f_body = float(np.sqrt(4 * k_s / m_b) / (2 * np.pi))

            self.results.append({
                'k_s': float(k_s),
                'f_body': f_body,
                'rms': rms,
            })
        except Exception as e:
            print(f"[WARN] k={k_s:.0f} 失败: {e}")

        self.current_idx += 1