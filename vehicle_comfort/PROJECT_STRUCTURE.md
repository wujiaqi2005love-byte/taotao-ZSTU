# 七自由度汽车舒适度分析系统 - 项目结构说明

## 文件组织

```
vehicle_comfort_app/
│
├── main.py                          # 主程序入口，包含主菜单界面
│
├── core/                            # 核心计算模块
│   ├── __init__.py                 # 模块初始化
│   └── models.py                   # 动力学模型（RoadExcitation, SevenDOFModel）
│
├── utils/                           # 工具模块
│   ├── __init__.py                 # 模块初始化
│   ├── calculators.py              # 计算工具（频率、RMS、舒适性评价）
│   └── window_base.py              # 窗口基类、默认参数、样式主题
│
├── threads/                         # 线程模块
│   ├── __init__.py                 # 模块初始化
│   └── simulation_threads.py       # 仿真计算线程
│       ├── ComfortAnalysisThread           # 舒适度分析线程
│       ├── UniformStiffnessSearchThread    # 四轮统一刚度搜索线程
│       └── SeparateStiffnessSearchThread   # 前后分离刚度搜索线程
│
├── windows/                         # 窗口界面模块
│   ├── __init__.py                 # 模块初始化
│   ├── comfort_analysis.py         # 舒适度分析窗口
│   ├── uniform_stiffness.py        # 四轮统一刚度搜索窗口
│   └── separate_stiffness.py       # 前后分离刚度搜索窗口
│
├── README.md                        # 项目说明文档
└── requirements.txt                 # 依赖包列表

```

## 模块说明

### 1. main.py - 主程序入口
- `MainMenuWindow`: 主菜单窗口类
- `main()`: 程序入口函数

功能：
- 提供统一的启动界面
- 导航到三个功能模块
- 应用全局样式和字体设置

### 2. core/models.py - 核心动力学模型
- `RoadExcitation`: ISO 8608随机路面激励生成器
- `SevenDOFModel`: 七自由度整车动力学模型

功能：
- 生成符合ISO 8608标准的路面激励
- 计算车辆运动方程
- 支持杠杆比、时间延迟等高级特性

### 3. utils/calculators.py - 计算工具
提供的函数：
- `calc_body_frequency_uniform()`: 计算车身固有频率（四轮统一）
- `calc_body_frequency_separate()`: 计算车身固有频率（前后分离）
- `calc_tire_frequency()`: 计算轮胎固有频率
- `calc_stiffness_range_from_frequency()`: 根据频率计算刚度范围
- `calc_total_stiffness_range()`: 计算总刚度范围
- `calc_rms_for_uniform_stiffness()`: 计算RMS（四轮统一）
- `calc_rms_for_separate_stiffness()`: 计算RMS（前后分离）
- `get_comfort_rating()`: 获取ISO 2631舒适性评价

### 4. utils/window_base.py - 窗口基类
- `DEFAULT_VEHICLE_PARAMS`: 默认车辆参数字典
- `DARK_THEME_STYLE`: 深色主题样式表
- `BaseWindow`: 窗口基类

功能：
- 提供统一的窗口基类
- 定义共享的默认参数
- 统一的UI样式主题

### 5. threads/simulation_threads.py - 仿真线程
- `ComfortAnalysisThread`: 舒适度分析仿真线程
- `UniformStiffnessSearchThread`: 四轮统一刚度搜索线程
- `SeparateStiffnessSearchThread`: 前后分离刚度搜索线程

功能：
- 在后台线程执行耗时计算
- 实时更新进度条
- 完成后发送结果信号

### 6. windows/ - 三个功能窗口
#### comfort_analysis.py - 舒适度分析
- 完整的车辆参数输入
- 实时仿真计算
- 显示四个座位和质心的加速度
- ISO 2631舒适性评价

#### uniform_stiffness.py - 四轮统一刚度搜索
- 根据频率约束计算刚度范围
- 扫描不同刚度值下的RMS
- 表格显示所有结果
- 自动寻找最优值

#### separate_stiffness.py - 前后分离刚度搜索
- 前后轮独立优化
- 二维参数空间搜索
- 支持前后刚度比例约束
- 结果按RMS排序

## 代码改进点

### 相比原代码的优势：

1. **模块化** 
   - 每个模块职责单一明确
   - 便于维护和扩展

2. **代码复用**
   - 共享的计算函数避免重复
   - 统一的窗口基类减少冗余

3. **可读性**
   - 清晰的文件组织
   - 详细的函数说明
   - 统一的命名规范

4. **可扩展性**
   - 易于添加新的分析模块
   - 便于修改UI样式
   - 方便集成新的计算方法

5. **用户体验**
   - 统一的主菜单入口
   - 一致的界面风格
   - 清晰的功能分类

## 使用方法

1. 安装依赖：
```bash
pip install -r requirements.txt
```

2. 运行程序：
```bash
python main.py
```

3. 从主菜单选择需要的功能模块

## 扩展建议

如果需要添加新功能：

1. 在 `utils/calculators.py` 添加计算函数
2. 在 `threads/simulation_threads.py` 添加对应的线程类
3. 在 `windows/` 创建新的窗口类
4. 在 `main.py` 的主菜单添加入口按钮

## 技术栈

- Python 3.8+
- PyQt6 (GUI框架)
- NumPy (数值计算)
- SciPy (科学计算，ODE求解)
