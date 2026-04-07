"""
仿真计算模块（v6）
新增悬架动挠度约束过滤：|zs - zu|max <= defl_limit
"""

import os
import traceback

os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['MKL_NUM_THREADS'] = '1'
os.environ['OMP_NUM_THREADS'] = '1'
os.environ['NUMEXPR_NUM_THREADS'] = '1'

import numpy as np
from scipy.integrate import odeint
from PyQt6.QtCore import QObject, QTimer, pyqtSignal, QCoreApplication

from core.models import RoadExcitation, SevenDOFModel


def _create_road(road_class, speed, duration, n_samples=8000, seed=42):
    try:
        return RoadExcitation(road_class, speed, duration,
                              n_samples=n_samples, seed=seed)
    except TypeError:
        np.random.seed(seed)
        return RoadExcitation(road_class, speed, duration,
                              n_samples=n_samples)


def _solve_ode(params, roads):
    """
    ODE 求解，返回：
        rms        : 质心加速度 RMS (m/s²)
        max_defl   : 四角悬架最大动挠度 (m)，即 max|z_body_corner - z_wheel|
        solution, t, model, skip, n_points
    """
    p = params
    model = SevenDOFModel(p, roads)
    duration = p.get('duration', 10)
    n_points = int(duration * 300)
    t = np.linspace(0, duration, n_points)
    y0 = np.zeros(14)

    solution = odeint(model, y0, t,
                      rtol=1e-4, atol=1e-4, mxstep=5000)

    skip = int(n_points * 0.15)

    # ── 加速度 RMS ──
    a_body = np.zeros(n_points - skip)
    for i in range(skip, n_points):
        deriv = model(solution[i], t[i])
        a_body[i - skip] = deriv[7]
    rms = float(np.sqrt(np.mean(a_body ** 2)))

    # ── 悬架动挠度 ──
    a_val = p.get('a', 1.2)
    b_val = p.get('b', 1.5)
    Bf    = p.get('B_f', 1.48)
    Br    = p.get('B_r', 1.48)

    zb  = solution[skip:, 0]
    th  = solution[skip:, 1]
    phi = solution[skip:, 2]
    zwA = solution[skip:, 3]
    zwB = solution[skip:, 4]
    zwC = solution[skip:, 5]
    zwD = solution[skip:, 6]

    zbA = zb - a_val * th - 0.5 * Bf * phi
    zbB = zb - a_val * th + 0.5 * Bf * phi
    zbC = zb + b_val * th - 0.5 * Br * phi
    zbD = zb + b_val * th + 0.5 * Br * phi

    max_defl = float(max(
        np.max(np.abs(zbA - zwA)),
        np.max(np.abs(zbB - zwB)),
        np.max(np.abs(zbC - zwC)),
        np.max(np.abs(zbD - zwD)),
    ))

    return rms, max_defl, solution, t, model, skip, n_points


# ════════════════════════════════════════
#  舒适度分析（单次）
# ════════════════════════════════════════

class ComfortAnalysisThread(QObject):
    progress_updated  = pyqtSignal(int)
    simulation_finished = pyqtSignal(dict)
    error_occurred    = pyqtSignal(str)

    def __init__(self, params):
        super().__init__()
        self.params = params.copy()
        self._timer = QTimer()
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._run)

    def start(self):
        self.progress_updated.emit(5)
        self._timer.start(50)

    def _run(self):
        try:
            p = self.params

            QCoreApplication.processEvents()
            self.progress_updated.emit(10)
            QCoreApplication.processEvents()

            seed = p.get('random_seed') or 42
            duration_road = p.get('duration', 10) + 3
            road = _create_road(
                p.get('road_class', 'C'),
                p.get('vehicle_speed', 20),
                duration_road, n_samples=12000, seed=int(seed)
            )
            roads = {'A': road, 'B': road, 'C': road, 'D': road}

            self.progress_updated.emit(15)
            QCoreApplication.processEvents()

            model = SevenDOFModel(p, roads)
            duration = p.get('duration', 10)
            n_points = int(duration * 500)
            t = np.linspace(0, duration, n_points)
            y0 = np.zeros(14)

            self.progress_updated.emit(20)
            QCoreApplication.processEvents()

            solution = odeint(model, y0, t,
                              rtol=1e-4, atol=1e-4, mxstep=5000)

            self.progress_updated.emit(65)
            QCoreApplication.processEvents()

            skip = int(n_points * 0.1)
            a_val = p.get('a', 1.2)
            b_val = p.get('b', 1.5)
            Bf = p.get('B_f', 1.48)
            Br = p.get('B_r', 1.48)

            zb  = solution[skip:, 0]
            th  = solution[skip:, 1]
            phi = solution[skip:, 2]

            results = {}
            results['z_b']  = float(np.sqrt(np.mean((zb * 1000) ** 2)))
            results['z_bA'] = float(np.sqrt(np.mean(
                ((zb - a_val * th - 0.5 * Bf * phi) * 1000) ** 2)))
            results['z_bB'] = float(np.sqrt(np.mean(
                ((zb - a_val * th + 0.5 * Bf * phi) * 1000) ** 2)))
            results['z_bC'] = float(np.sqrt(np.mean(
                ((zb + b_val * th - 0.5 * Br * phi) * 1000) ** 2)))
            results['z_bD'] = float(np.sqrt(np.mean(
                ((zb + b_val * th + 0.5 * Br * phi) * 1000) ** 2)))

            self.progress_updated.emit(80)
            QCoreApplication.processEvents()

            derivs_arr = np.zeros((n_points - skip, 14))
            for i in range(skip, n_points):
                derivs_arr[i - skip] = model(solution[i], t[i])

            a_ddot   = derivs_arr[:, 7]
            th_ddot  = derivs_arr[:, 8]
            phi_ddot = derivs_arr[:, 9]

            results['a_b']  = float(np.sqrt(np.mean(a_ddot ** 2)))
            results['a_bA'] = float(np.sqrt(np.mean(
                (a_ddot - a_val * th_ddot - 0.5 * Bf * phi_ddot) ** 2)))
            results['a_bB'] = float(np.sqrt(np.mean(
                (a_ddot - a_val * th_ddot + 0.5 * Bf * phi_ddot) ** 2)))
            results['a_bC'] = float(np.sqrt(np.mean(
                (a_ddot + b_val * th_ddot - 0.5 * Br * phi_ddot) ** 2)))
            results['a_bD'] = float(np.sqrt(np.mean(
                (a_ddot + b_val * th_ddot + 0.5 * Br * phi_ddot) ** 2)))

            self.progress_updated.emit(100)
            self.simulation_finished.emit(results)

        except Exception:
            self.error_occurred.emit(traceback.format_exc())


# ════════════════════════════════════════
#  四轮统一刚度搜索
# ════════════════════════════════════════

class UniformStiffnessSearchThread(QObject):
    progress_updated = pyqtSignal(int, str)
    search_finished  = pyqtSignal(list)
    error_occurred   = pyqtSignal(str)

    def __init__(self, base_params, k_range, n_points, defl_limit=None):
        """
        defl_limit : 悬架动挠度上限 (m)，None 表示不约束
        """
        super().__init__()
        self.base_params = base_params.copy()
        self.k_range     = k_range
        self.n_points    = n_points
        self.defl_limit  = defl_limit  # ★ 新增

        self._results     = []
        self._k_values    = []
        self._current_idx = 0
        self._roads       = None
        self._discarded   = 0          # ★ 记录被过滤数量

        self._timer = QTimer()
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._step)

    def start(self):
        try:
            self._k_values    = np.linspace(self.k_range[0], self.k_range[1], self.n_points)
            self._results     = []
            self._current_idx = 0
            self._discarded   = 0

            p = self.base_params
            duration_road = p.get('duration', 10) + 3
            road = _create_road(p.get('road_class', 'C'),
                                p.get('vehicle_speed', 20),
                                duration_road, n_samples=8000, seed=42)
            self._roads = {'A': road, 'B': road, 'C': road, 'D': road}

            self.progress_updated.emit(0, "准备中...")
            QCoreApplication.processEvents()
            self._timer.start(20)

        except Exception:
            self.error_occurred.emit(traceback.format_exc())

    def _step(self):
        try:
            idx   = self._current_idx
            total = len(self._k_values)

            if idx >= total:
                self.progress_updated.emit(100, "扫描完成")
                self.search_finished.emit(self._results)
                return

            k_s = float(self._k_values[idx])
            self.progress_updated.emit(
                int(idx / total * 95),
                f"计算 {idx+1}/{total}  k={k_s:.0f} N/m"
            )
            QCoreApplication.processEvents()

            p = self.base_params.copy()
            p['k_sA'] = p['k_sB'] = p['k_sC'] = p['k_sD'] = k_s

            try:
                rms, max_defl, *_ = _solve_ode(p, self._roads)

                # ★ 悬架动挠度约束过滤
                if self.defl_limit is not None and max_defl > self.defl_limit:
                    self._discarded += 1
                else:
                    m_b    = p.get('m_b', 1380)
                    f_body = float(np.sqrt(4 * k_s / m_b) / (2 * np.pi))
                    self._results.append({
                        'k_s':      k_s,
                        'f_body':   f_body,
                        'rms':      rms,
                        'max_defl': max_defl,   # ★ 新增字段
                    })
            except Exception as e:
                print(f"[WARN] k={k_s:.0f} 失败: {e}")

            self._current_idx += 1
            self._timer.start(10)

        except Exception:
            self.error_occurred.emit(traceback.format_exc())


# ════════════════════════════════════════
#  前后分离刚度搜索
# ════════════════════════════════════════

class SeparateStiffnessSearchThread(QObject):
    progress_updated = pyqtSignal(int, str)
    search_finished  = pyqtSignal(list)
    error_occurred   = pyqtSignal(str)

    def __init__(self, base_params, k_sum_range, ratio_range, n_points, defl_limit=None):
        """
        defl_limit : 悬架动挠度上限 (m)，None 表示不约束
        """
        super().__init__()
        self.base_params  = base_params.copy()
        self.k_sum_range  = k_sum_range
        self.ratio_range  = ratio_range
        self.n_points     = n_points
        self.defl_limit   = defl_limit  # ★ 新增

        self._results     = []
        self._tasks       = []
        self._current_idx = 0
        self._roads       = None
        self._discarded   = 0

        self._timer = QTimer()
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._step)

    def start(self):
        try:
            k_sums  = np.linspace(self.k_sum_range[0], self.k_sum_range[1], self.n_points)
            ratios  = np.linspace(self.ratio_range[0],  self.ratio_range[1],  self.n_points)

            self._tasks = []
            for k_sum in k_sums:
                for ratio in ratios:
                    k_r = k_sum / (1.0 + ratio)
                    k_f = ratio * k_r
                    self._tasks.append((float(k_f), float(k_r), float(ratio)))

            self._results     = []
            self._current_idx = 0
            self._discarded   = 0

            p = self.base_params
            duration_road = p.get('duration', 10) + 3
            road = _create_road(p.get('road_class', 'C'),
                                p.get('vehicle_speed', 20),
                                duration_road, n_samples=8000, seed=42)
            self._roads = {'A': road, 'B': road, 'C': road, 'D': road}

            self.progress_updated.emit(0, "准备中...")
            QCoreApplication.processEvents()
            self._timer.start(20)

        except Exception:
            self.error_occurred.emit(traceback.format_exc())

    def _step(self):
        try:
            idx   = self._current_idx
            total = len(self._tasks)

            if idx >= total:
                self.progress_updated.emit(100, "扫描完成")
                self.search_finished.emit(self._results)
                return

            k_f, k_r, ratio = self._tasks[idx]
            self.progress_updated.emit(
                int(idx / total * 95),
                f"计算 {idx+1}/{total}  k_f={k_f:.0f} k_r={k_r:.0f}"
            )
            QCoreApplication.processEvents()

            p = self.base_params.copy()
            p['k_sA'] = p['k_sB'] = k_f
            p['k_sC'] = p['k_sD'] = k_r

            try:
                rms, max_defl, *_ = _solve_ode(p, self._roads)

                # ★ 悬架动挠度约束过滤
                if self.defl_limit is not None and max_defl > self.defl_limit:
                    self._discarded += 1
                else:
                    m_b     = p.get('m_b', 1380)
                    k_total = 2 * (k_f + k_r)
                    f_body  = float(np.sqrt(k_total / m_b) / (2 * np.pi))
                    self._results.append({
                        'k_f':      k_f,
                        'k_r':      k_r,
                        'ratio':    ratio,
                        'f_body':   f_body,
                        'rms':      rms,
                        'max_defl': max_defl,   # ★ 新增字段
                    })
            except Exception as e:
                print(f"[WARN] k_f={k_f:.0f} k_r={k_r:.0f} 失败: {e}")

            self._current_idx += 1
            self._timer.start(10)

        except Exception:
            self.error_occurred.emit(traceback.format_exc())