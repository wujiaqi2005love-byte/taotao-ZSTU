"""
全局共享状态管理器
Global Shared State Manager
负责在舒适度分析系统与弹簧选型系统之间传递数据

修复：将单例实现从 QObject 子类改为普通 Python 类 + 独立信号发射器
避免 QObject.__init__ 与 __new__ 的执行顺序冲突
"""

from PyQt6.QtCore import QObject, pyqtSignal


class _StiffnessSignalEmitter(QObject):
    """
    独立的信号发射器
    将 QObject 信号与单例状态管理器解耦
    """
    stiffness_updated = pyqtSignal(float, float, str)
    # 参数：k_min(N/m), k_max(N/m), 来源描述


class SharedState:
    """
    单例共享状态管理器（纯 Python 类，不继承 QObject）
    通过内部 _emitter 发射 Qt 信号
    """

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._setup()
        return cls._instance

    def _setup(self):
        """
        真正的初始化，只执行一次
        在 QApplication 创建后调用才安全
        """
        # 信号发射器（需要 QApplication 已存在）
        self._emitter = _StiffnessSignalEmitter()

        # 对外暴露信号（方便外部直接 connect）
        self.stiffness_updated = self._emitter.stiffness_updated

        # 共享数据
        self.k_min: float = None            # 最小刚度 N/m
        self.k_max: float = None            # 最大刚度 N/m
        self.k_optimal: float = None        # 最优刚度 N/m
        self.source_description: str = ""   # 来源描述
        self.vehicle_mass: float = None     # 车身质量 kg
        self.road_class: str = "C"          # 路面等级
        self.vehicle_speed: float = 20.0    # 车速 m/s

    def set_stiffness(
        self,
        k_min: float,
        k_max: float,
        k_optimal: float = None,
        source: str = "",
        vehicle_mass: float = None,
        road_class: str = "C",
        vehicle_speed: float = 20.0
    ):
        """
        设置刚度数据并广播信号

        Args:
            k_min        : 最小刚度 (N/m)
            k_max        : 最大刚度 (N/m)
            k_optimal    : 最优刚度 (N/m)，None 时取中值
            source       : 数据来源描述字符串
            vehicle_mass : 车身质量 (kg)，用于自动填充等效质量
            road_class   : 路面等级
            vehicle_speed: 车速 (m/s)
        """
        self.k_min = float(k_min)
        self.k_max = float(k_max)
        self.k_optimal = (
            float(k_optimal) if k_optimal is not None
            else (self.k_min + self.k_max) / 2.0
        )
        self.source_description = source
        self.vehicle_mass = vehicle_mass
        self.road_class = road_class
        self.vehicle_speed = vehicle_speed

        # 广播信号
        self._emitter.stiffness_updated.emit(
            self.k_min, self.k_max, self.source_description
        )

    def get_stiffness_nmm(self):
        """
        返回 N/mm 单位的刚度三元组

        Returns:
            (k_min_nmm, k_max_nmm, k_optimal_nmm)
            数据不存在时返回 (None, None, None)
        """
        if self.k_min is None:
            return None, None, None
        return (
            self.k_min / 1000.0,
            self.k_max / 1000.0,
            self.k_optimal / 1000.0
        )

    def has_data(self) -> bool:
        """是否已有有效刚度数据"""
        return self.k_min is not None and self.k_max is not None

    def clear(self):
        """清空所有共享数据"""
        self.k_min = None
        self.k_max = None
        self.k_optimal = None
        self.source_description = ""
        self.vehicle_mass = None
        self.road_class = "C"
        self.vehicle_speed = 20.0

    def __repr__(self):
        if self.has_data():
            return (
                f"SharedState("
                f"k_min={self.k_min:.1f}N/m, "
                f"k_max={self.k_max:.1f}N/m, "
                f"k_optimal={self.k_optimal:.1f}N/m, "
                f"source='{self.source_description[:30]}')"
            )
        return "SharedState(空)"


# ─────────────────────────────────────────────
# 注意：此处不立即实例化
# shared_state 在 main.py 中 QApplication 创建后才初始化
# 各模块通过 get_shared_state() 获取单例
# ─────────────────────────────────────────────

def get_shared_state() -> SharedState:
    """
    获取全局单例（延迟初始化）
    在 QApplication 创建后调用才安全

    Returns:
        SharedState 单例
    """
    return SharedState()


# 为了兼容已有的 `from utils.shared_state import shared_state` 写法
# 提供一个模块级占位符，真正的实例在首次调用时创建
shared_state = get_shared_state()