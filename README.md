<div align="center">

# 车辆舒适性分析与减震弹簧选型平台

**Vehicle Comfort Analysis & Spring Design Toolkit**

基于七自由度整车动力学模型的桌面分析工具，覆盖路面激励、乘坐舒适性评估、悬架刚度搜索与螺旋弹簧初步选型。

<br>

![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)
![PyQt6](https://img.shields.io/badge/UI-PyQt6-41CD52?logo=qt&logoColor=white)
![Numerical](https://img.shields.io/badge/Model-7--DOF-425B76)
![Standards](https://img.shields.io/badge/Reference-ISO%208608%20%7C%20ISO%202631-9A6B37)

</div>

---

## 项目简介

本项目将车辆垂向动力学仿真与悬架参数设计整合在一个 PyQt6 桌面应用中。用户可以从车辆与道路参数出发，运行舒适性分析或刚度搜索，并将选出的刚度范围传递到弹簧选型模块。

## 功能模块

| 模块 | 功能 |
| --- | --- |
| 车辆舒适度分析 | 构造 ISO 8608 随机路面输入，运行整车时域仿真并查看车身响应与 RMS 舒适性评价 |
| 四轮统一刚度搜索 | 在车身频率约束范围内搜索统一悬架刚度，并按仿真结果比较候选参数 |
| 前后分离刚度搜索 | 扫描前后轴刚度组合，查看刚度比例、车身频率和加速度 RMS |
| 弹簧选型系统 | 根据目标刚度、材料、预压缩量和工作行程计算候选弹簧，并支持结果可视化与表格导出 |

### 计算流程

```text
车辆 / 道路参数
       ↓
ISO 8608 路面输入 → 七自由度整车模型 → ISO 2631 舒适性指标
       ↓
统一 / 前后分离刚度搜索
       ↓
刚度范围传递 → 弹簧候选方案与选型结果
```

## 界面

启动后可从主菜单进入四个分析模块。主界面采用模块卡片布局；刚度搜索得到的参数可直接发送到弹簧选型窗口。

## 环境要求

- Python 3.10 或更新版本
- Windows、macOS 或 Linux 桌面环境
- 图形环境（PyQt6）

## 安装与运行

```bash
git clone https://github.com/wujiaqi2005love-byte/taotao-ZSTU.git
cd taotao-ZSTU
python -m venv .venv
```

激活虚拟环境后安装依赖并启动：

```bash
python -m pip install -r requirements.txt
cd vehicle_comfort
python main.py
```

macOS / Linux 激活环境：

```bash
source .venv/bin/activate
```

Windows PowerShell 激活环境：

```powershell
.venv\Scripts\Activate.ps1
```

## 项目结构

```text
taotao-ZSTU/
├── README.md
├── requirements.txt
└── vehicle_comfort/
    ├── main.py                 # 应用入口与主菜单
    ├── core/models.py          # 路面激励与七自由度模型
    ├── threads/                # 仿真与搜索任务
    ├── utils/                  # 参数、共享状态与计算工具
    └── windows/                # 分析、搜索和弹簧选型界面
```

## 模型范围

模型包含车身垂向、俯仰、侧倾以及四个车轮的垂向自由度。路面激励按 ISO 8608 空间功率谱密度等级生成，舒适性分级参考 ISO 2631。弹簧候选结果用于工程初步筛选；实际设计仍需结合具体车辆结构、制造规格、疲劳工况和试验验证。

## 技术栈

`Python` · `PyQt6` · `NumPy` · `SciPy` · `Matplotlib`

---

<div align="center">
浙江理工大学 · 数学建模与车辆动力学实践
</div>
