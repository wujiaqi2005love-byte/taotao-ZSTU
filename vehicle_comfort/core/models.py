"""
七自由度整车动力学核心模型
7-DOF Vehicle Dynamics Core Models
"""

import numpy as np
import os
os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['MKL_NUM_THREADS'] = '1'
os.environ['OMP_NUM_THREADS'] = '1'

class RoadExcitation:
    """ISO 8608 随机路面激励生成器"""

    def __init__(self, road_class, vehicle_speed, duration, n_samples=20000, seed=None):
        self.u = vehicle_speed
        self.time_arr = np.linspace(0, duration, n_samples)

        # ISO 8608: Gq(n0) values (10^-6 m^3)
        iso_map = {
            'A': 16, 'B': 64, 'C': 256, 'D': 1024,
            'E': 4096, 'F': 16384, 'G': 65536, 'H': 262144
        }
        Gq_n0 = iso_map.get(road_class, 256) * 1e-6

        self.z_interp, self.zd_interp = self._generate_iso_profile(
            Gq_n0, duration, vehicle_speed, n_samples, seed
        )

    def _generate_iso_profile(self, Gq_n0, T, u, N, seed=None):
        n0 = 0.1  # reference spatial frequency (cycles/m)
        f_min = 0.5
        f_max = 100.0
        df = 0.05
        freqs = np.arange(f_min, f_max, df)

        n = freqs / u
        Gd_n = Gq_n0 * (n / n0) ** (-2)
        Gd_f = Gd_n / u
        amplitude = np.sqrt(2 * Gd_f * df)
        
        if seed is not None:
            np.random.seed(seed)
        phase = 2 * np.pi * np.random.rand(len(freqs))

        t = np.linspace(0, T, N)
        omega = 2 * np.pi * freqs

        args = omega[:, None] * t[None, :] + phase[:, None]
        z = np.sum(amplitude[:, None] * np.sin(args), axis=0)
        z_dot = np.sum(amplitude[:, None] * omega[:, None] * np.cos(args), axis=0)

        scale = 0.87
        return z * scale, z_dot * scale

    def get_displacement(self, t):
        return np.interp(t, self.time_arr, self.z_interp)

    def get_velocity(self, t):
        return np.interp(t, self.time_arr, self.zd_interp)


class SevenDOFModel:
    """七自由度整车动力学模型"""

    def __init__(self, params, roads):
        self.p = params
        self.roads = roads

    def __call__(self, state, t):
        p = self.p

        z_b, theta_b, phi = state[0:3]
        z_wA, z_wB, z_wC, z_wD = state[3:7]
        z_b_dot, theta_b_dot, phi_dot = state[7:10]
        z_wA_dot, z_wB_dot, z_wC_dot, z_wD_dot = state[10:14]

        # 车身四角位移
        z_bA = z_b - p['a'] * theta_b - 0.5 * p['B_f'] * phi
        z_bB = z_b - p['a'] * theta_b + 0.5 * p['B_f'] * phi
        z_bC = z_b + p['b'] * theta_b - 0.5 * p['B_r'] * phi
        z_bD = z_b + p['b'] * theta_b + 0.5 * p['B_r'] * phi

        # 车身四角速度
        z_bA_dot = z_b_dot - p['a'] * theta_b_dot - 0.5 * p['B_f'] * phi_dot
        z_bB_dot = z_b_dot - p['a'] * theta_b_dot + 0.5 * p['B_f'] * phi_dot
        z_bC_dot = z_b_dot + p['b'] * theta_b_dot - 0.5 * p['B_r'] * phi_dot
        z_bD_dot = z_b_dot + p['b'] * theta_b_dot + 0.5 * p['B_r'] * phi_dot

        # 路面激励
        delay = (p['a'] + p['b']) / p['vehicle_speed']
        z_gA = self.roads['A'].get_displacement(t)
        z_gB = self.roads['B'].get_displacement(t)
        z_gC = self.roads['C'].get_displacement(max(0, t - delay))
        z_gD = self.roads['D'].get_displacement(max(0, t - delay))

        # 杠杆比
        i_f = p.get('lever_ratio_f', 1.0)
        i_r = p.get('lever_ratio_r', 1.0)

        # 悬架力（考虑杠杆比）
        F_sA = (i_f ** 2) * (p['C_sA'] * (z_wA_dot - z_bA_dot) + p['k_sA'] * (z_wA - z_bA))
        F_sB = (i_f ** 2) * (p['C_sB'] * (z_wB_dot - z_bB_dot) + p['k_sB'] * (z_wB - z_bB))
        F_sC = (i_r ** 2) * (p['C_sC'] * (z_wC_dot - z_bC_dot) + p['k_sC'] * (z_wC - z_bC))
        F_sD = (i_r ** 2) * (p['C_sD'] * (z_wD_dot - z_bD_dot) + p['k_sD'] * (z_wD - z_bD))

        # 轮胎力
        F_tA = p['k_tA'] * (z_gA - z_wA)
        F_tB = p['k_tB'] * (z_gB - z_wB)
        F_tC = p['k_tC'] * (z_gC - z_wC)
        F_tD = p['k_tD'] * (z_gD - z_wD)

        # 加速度
        z_b_ddot = (F_sA + F_sB + F_sC + F_sD) / p['m_b']
        theta_b_ddot = ((F_sC + F_sD) * p['b'] - (F_sA + F_sB) * p['a']) / p['I_p']
        phi_ddot = ((F_sB - F_sA) * p['B_f'] / 2 + (F_sD - F_sC) * p['B_r'] / 2) / p['I_r']

        z_wA_ddot = (F_tA - F_sA) / p['m_wA']
        z_wB_ddot = (F_tB - F_sB) / p['m_wB']
        z_wC_ddot = (F_tC - F_sC) / p['m_wC']
        z_wD_ddot = (F_tD - F_sD) / p['m_wD']

        return [
            z_b_dot, theta_b_dot, phi_dot, 
            z_wA_dot, z_wB_dot, z_wC_dot, z_wD_dot,
            z_b_ddot, theta_b_ddot, phi_ddot, 
            z_wA_ddot, z_wB_ddot, z_wC_ddot, z_wD_ddot
        ]
