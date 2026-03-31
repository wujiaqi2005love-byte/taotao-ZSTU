"""
计算工具模块
Calculation Utilities
"""

import numpy as np
from scipy.integrate import odeint
from core.models import RoadExcitation, SevenDOFModel


def calc_body_frequency_uniform(m_b, k_s):
    """
    计算车身固有频率（四轮统一刚度）
    
    Args:
        m_b: 车身质量 (kg)
        k_s: 单个弹簧刚度 (N/m)
    
    Returns:
        频率 (Hz)
    """
    return np.sqrt(4 * k_s / m_b) / (2 * np.pi)


def calc_body_frequency_separate(m_b, k_f, k_r):
    """
    计算车身固有频率（前后分离刚度）
    
    Args:
        m_b: 车身质量 (kg)
        k_f: 前轮弹簧刚度 (N/m)
        k_r: 后轮弹簧刚度 (N/m)
    
    Returns:
        频率 (Hz)
    """
    k_total = 2 * (k_f + k_r)
    return np.sqrt(k_total / m_b) / (2 * np.pi)


def calc_tire_frequency(m_w, k_t):
    """
    计算轮胎固有频率
    
    Args:
        m_w: 轮胎质量 (kg)
        k_t: 轮胎刚度 (N/m)
    
    Returns:
        频率 (Hz)
    """
    return np.sqrt(k_t / m_w) / (2 * np.pi)


def calc_stiffness_range_from_frequency(m_b, f_min, f_max):
    """
    根据车身固有频率范围计算弹簧刚度范围（四轮统一）
    
    简化公式: f = (1/2π) * sqrt(4*k_s / m_b)
    
    Args:
        m_b: 车身质量 (kg)
        f_min: 最小频率 (Hz)
        f_max: 最大频率 (Hz)
    
    Returns:
        (k_s_min, k_s_max) 弹簧刚度范围 (N/m)
    """
    k_s_min = (2 * np.pi * f_min) ** 2 * m_b / 4
    k_s_max = (2 * np.pi * f_max) ** 2 * m_b / 4
    return k_s_min, k_s_max


def calc_total_stiffness_range(m_b, f_min, f_max):
    """
    根据车身固有频率范围计算总弹簧刚度范围（前后分离）
    
    k_total = 2*(k_f + k_r)
    
    Args:
        m_b: 车身质量 (kg)
        f_min: 最小频率 (Hz)
        f_max: 最大频率 (Hz)
    
    Returns:
        (k_sum_min, k_sum_max): k_f + k_r 的范围 (N/m)
    """
    k_total_min = (2 * np.pi * f_min) ** 2 * m_b
    k_total_max = (2 * np.pi * f_max) ** 2 * m_b
    return k_total_min / 2, k_total_max / 2


def calc_rms_for_uniform_stiffness(base_params, k_s):
    """
    计算给定弹簧刚度下的质心加速度RMS（四轮统一刚度）
    
    Args:
        base_params: 基础参数字典
        k_s: 弹簧刚度 (N/m)
    
    Returns:
        RMS加速度 (m/s²)
    """
    p = base_params.copy()
    p['k_sA'] = p['k_sB'] = p['k_sC'] = p['k_sD'] = k_s

    # 生成路面
    duration = p['duration'] + 3
    road = RoadExcitation(p['road_class'], p['vehicle_speed'], duration, n_samples=8000)
    roads = {'A': road, 'B': road, 'C': road, 'D': road}

    # 求解ODE
    model = SevenDOFModel(p, roads)
    t = np.linspace(0, p['duration'], int(p['duration'] * 500))
    y0 = np.zeros(14)
    solution = odeint(model, y0, t)

    # 计算加速度
    skip = int(len(t) * 0.15)
    accelerations = []
    for i in range(skip, len(t)):
        derivs = model(solution[i], t[i])
        accelerations.append(derivs[7])

    return np.sqrt(np.mean(np.array(accelerations) ** 2))


def calc_rms_for_separate_stiffness(base_params, k_f, k_r):
    """
    计算给定弹簧刚度下的质心加速度RMS（前后分离刚度）
    
    Args:
        base_params: 基础参数字典
        k_f: 前轮弹簧刚度 (N/m)
        k_r: 后轮弹簧刚度 (N/m)
    
    Returns:
        RMS加速度 (m/s²)
    """
    p = base_params.copy()
    p['k_sA'] = p['k_sB'] = k_f
    p['k_sC'] = p['k_sD'] = k_r

    # 生成路面
    duration = p['duration'] + 3
    road = RoadExcitation(p['road_class'], p['vehicle_speed'], duration, n_samples=8000)
    roads = {'A': road, 'B': road, 'C': road, 'D': road}

    # 求解ODE
    model = SevenDOFModel(p, roads)
    t = np.linspace(0, p['duration'], int(p['duration'] * 500))
    y0 = np.zeros(14)
    solution = odeint(model, y0, t)

    # 计算加速度
    skip = int(len(t) * 0.15)
    accelerations = []
    for i in range(skip, len(t)):
        derivs = model(solution[i], t[i])
        accelerations.append(derivs[7])

    return np.sqrt(np.mean(np.array(accelerations) ** 2))


def get_comfort_rating(a_rms):
    """
    根据ISO 2631标准获取舒适性评价
    
    Args:
        a_rms: RMS加速度 (m/s²)
    
    Returns:
        (rating, color): 评价文本和颜色
    """
    if a_rms < 0.315:
        return "舒适 Comfortable", "#4ade80"
    elif a_rms < 0.63:
        return "稍不舒适 Slightly Uncomfortable", "#a3e635"
    elif a_rms < 1.0:
        return "不舒适 Fairly Uncomfortable", "#fbbf24"
    elif a_rms < 1.6:
        return "很不舒适 Uncomfortable", "#fb923c"
    elif a_rms < 2.5:
        return "非常不舒适 Very Uncomfortable", "#f87171"
    else:
        return "极不舒适 Extremely Uncomfortable", "#ef4444"
