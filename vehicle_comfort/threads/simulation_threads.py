"""
仿真计算线程模块
Simulation Threads
"""

import numpy as np
from scipy.integrate import odeint
from PyQt6.QtCore import QThread, pyqtSignal

from core.models import RoadExcitation, SevenDOFModel
from utils.calculators import (
    calc_body_frequency_uniform,
    calc_body_frequency_separate,
    calc_rms_for_uniform_stiffness,
    calc_rms_for_separate_stiffness
)


class ComfortAnalysisThread(QThread):
    """舒适性分析仿真线程"""
    progress_updated = pyqtSignal(int)
    simulation_finished = pyqtSignal(dict)
    error_occurred = pyqtSignal(str)

    def __init__(self, params):
        super().__init__()
        self.params = params

    def run(self):
        try:
            p = self.params

            # 生成路面激励
            self.progress_updated.emit(10)
            duration = p['duration'] + 5
            seed = p.get('random_seed', None)
            road_profile = RoadExcitation(p['road_class'], p['vehicle_speed'], duration, seed=seed)
            roads = {
                'A': road_profile,
                'B': road_profile,
                'C': road_profile,
                'D': road_profile,
            }

            # 求解ODE
            self.progress_updated.emit(30)
            model = SevenDOFModel(p, roads)
            t = np.linspace(0, p['duration'], int(p['duration'] * 1000))
            y0 = np.zeros(14)
            solution = odeint(model, y0, t)

            # 计算加速度
            self.progress_updated.emit(70)
            accelerations = np.zeros((len(t), 7))
            for i, ti in enumerate(t):
                derivs = model(solution[i], ti)
                accelerations[i] = derivs[7:14]

            # 车身四角加速度
            z_b_ddot = accelerations[:, 0]
            theta_b_ddot = accelerations[:, 1]
            phi_ddot = accelerations[:, 2]

            a_bA = z_b_ddot - p['a'] * theta_b_ddot - 0.5 * p['B_f'] * phi_ddot
            a_bB = z_b_ddot - p['a'] * theta_b_ddot + 0.5 * p['B_f'] * phi_ddot
            a_bC = z_b_ddot + p['b'] * theta_b_ddot - 0.5 * p['B_r'] * phi_ddot
            a_bD = z_b_ddot + p['b'] * theta_b_ddot + 0.5 * p['B_r'] * phi_ddot

            # 车身四角位移
            z_b = solution[:, 0]
            theta_b = solution[:, 1]
            phi = solution[:, 2]
            z_bA = z_b - p['a'] * theta_b - 0.5 * p['B_f'] * phi
            z_bB = z_b - p['a'] * theta_b + 0.5 * p['B_f'] * phi
            z_bC = z_b + p['b'] * theta_b - 0.5 * p['B_r'] * phi
            z_bD = z_b + p['b'] * theta_b + 0.5 * p['B_r'] * phi

            # RMS计算
            self.progress_updated.emit(90)
            skip = int(len(t) * 0.1)
            rms = lambda arr: np.sqrt(np.mean(arr[skip:] ** 2))

            results = {
                'z_b': rms(z_b) * 1000,
                'theta_b': rms(theta_b) * 1000,
                'phi': rms(phi) * 1000,
                'z_bA': rms(z_bA) * 1000,
                'z_bB': rms(z_bB) * 1000,
                'z_bC': rms(z_bC) * 1000,
                'z_bD': rms(z_bD) * 1000,
                'a_b': rms(z_b_ddot),
                'a_bA': rms(a_bA),
                'a_bB': rms(a_bB),
                'a_bC': rms(a_bC),
                'a_bD': rms(a_bD),
            }

            self.progress_updated.emit(100)
            self.simulation_finished.emit(results)

        except Exception as e:
            self.error_occurred.emit(str(e))


class UniformStiffnessSearchThread(QThread):
    """四轮统一刚度搜索线程"""
    progress_updated = pyqtSignal(int, str)
    search_finished = pyqtSignal(list)
    error_occurred = pyqtSignal(str)

    def __init__(self, base_params, k_range, n_points):
        super().__init__()
        self.base_params = base_params
        self.k_range = k_range
        self.n_points = n_points

    def run(self):
        try:
            k_values = np.linspace(self.k_range[0], self.k_range[1], self.n_points)
            results = []

            for i, k_s in enumerate(k_values):
                progress = int((i + 1) / len(k_values) * 100)
                f_body = calc_body_frequency_uniform(self.base_params['m_b'], k_s)
                self.progress_updated.emit(progress, f"k_s={k_s/1000:.1f}kN/m, f={f_body:.2f}Hz")

                try:
                    rms = calc_rms_for_uniform_stiffness(self.base_params, k_s)
                    results.append({
                        'k_s': k_s,
                        'f_body': f_body,
                        'rms': rms
                    })
                except Exception:
                    continue

            self.search_finished.emit(results)

        except Exception as e:
            self.error_occurred.emit(str(e))


class SeparateStiffnessSearchThread(QThread):
    """前后分离刚度搜索线程"""
    progress_updated = pyqtSignal(int, str)
    search_finished = pyqtSignal(list)
    error_occurred = pyqtSignal(str)

    def __init__(self, base_params, k_sum_range, ratio_range, n_points):
        super().__init__()
        self.base_params = base_params
        self.k_sum_range = k_sum_range
        self.ratio_range = ratio_range
        self.n_points = n_points

    def run(self):
        try:
            # 生成 k_f + k_r 的值
            k_sum_values = np.linspace(self.k_sum_range[0], self.k_sum_range[1], self.n_points)
            # 生成前后比例 k_f / k_r
            ratio_values = np.linspace(self.ratio_range[0], self.ratio_range[1], self.n_points)

            total = len(k_sum_values) * len(ratio_values)
            count = 0
            results = []

            for k_sum in k_sum_values:
                for ratio in ratio_values:
                    count += 1

                    # 根据总和与比例计算 k_f 和 k_r
                    k_r = k_sum / (1 + ratio)
                    k_f = ratio * k_r

                    progress = int(count / total * 100)
                    f_body = calc_body_frequency_separate(self.base_params['m_b'], k_f, k_r)
                    self.progress_updated.emit(
                        progress,
                        f"k_f={k_f/1000:.1f}, k_r={k_r/1000:.1f} kN/m"
                    )

                    try:
                        rms = calc_rms_for_separate_stiffness(self.base_params, k_f, k_r)
                        results.append({
                            'k_f': k_f,
                            'k_r': k_r,
                            'ratio': ratio,
                            'f_body': f_body,
                            'rms': rms
                        })
                    except Exception:
                        continue

            self.search_finished.emit(results)

        except Exception as e:
            self.error_occurred.emit(str(e))
