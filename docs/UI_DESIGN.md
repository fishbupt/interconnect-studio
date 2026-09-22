# UI_DESIGN.md

# 1. Purpose

定义 Interconnect Studio 的 GUI 外壳与布局系统。

本轮范围**只覆盖外壳与布局**：窗口分区、视图网格、停靠、导航树层级、选中态、单位显示与主要交互约定。这些与具体领域类型无关，现在确定不会返工。

**不在本轮范围**：功能面板（Marker 编辑、Limit Line 编辑、串扰矩阵视图、眼图视图等）。这些依赖尚未实现的领域类型（`PortGroup`、`MixedModeNetwork`、质量检查结果），待对应类型落地后再设计，避免对着想象中的数据画界面。

# 2. Technology Decisions

- **纯 Python UI**，不使用 Qt Designer `.ui` 文件。停靠与多视图网格本就是动态布局；且 `.ui` 是机器生成的 XML，diff 不可读，与 `AGENTS.md` §12 要求的自查 git diff 相冲突。
- **pyqtgraph** 作为交互绘图主力：内建降采样应对 20k 点平滑缩放，`GraphicsLayout` 原生支持多面板网格，直接对应 4 象限与 N×N 矩阵视图。
- **matplotlib** 仅用于报告导出（V1.1），不进入交互路径。
- Smith 圆图与眼图使用 pyqtgraph 自定义 item 绘制——这两样在任何绘图库中都需自绘。
- 现有 `plot_widget.py`（QPainter 自绘）在迁移后废弃。`PlotModel` / `Trace` 抽象不受影响。

# 3. Window Layout

```text
┌─────────────────────────────────────────────────┐
│ Menu Bar / Tool Bar                             │
├───────────┬─────────────────────────┬───────────┤
│           │                         │           │
│ Project   │   View Area             │ Property  │
│ Tree      │   （固定网格）           │ Panel     │
│ (dock)    │                         │ (dock)    │
│           │                         │           │
├───────────┴─────────────────────────┴───────────┤
│ Log Panel (dock)                                │
├─────────────────────────────────────────────────┤
│ Status Bar                                      │
└─────────────────────────────────────────────────┘
```

约定：

- **View Area 使用固定网格**（行 × 列），不可手动拖拽分割。
- **外围面板使用 Qt dock**，可浮动、关闭、重排。
- 中央 View Area 不是 dock，不可关闭。

# 4. View Layout

```python
@dataclass(frozen=True, slots=True)
class ViewLayout:
    rows: int
    cols: int
    plots: tuple[PlotModel, ...]   # 长度 == rows * cols，行优先
```

约定：

- 典型值：1×1、1×2、2×1、2×2；N×N 用于矩阵视图。
- `plots` 按**行优先**顺序排列，与 Touchstone ≥3 端口的行主序一致。
- 空槽位用空 `PlotModel` 表示，不用 `None`。
- `ViewLayout` 不可变，变更返回新对象。
- 不依赖 PyQt6 或 pyqtgraph。

# 5. Plot Axes

单个 `PlotModel` 最多两个 Y 轴（左 / 右）。

- 每条 Trace 声明挂左轴还是右轴。
- **同一轴内仍强制 `y_unit` 一致**；跨轴可以不同。
- 所有 Trace 的 `x_unit` 必须一致（单 X 轴）。
- 典型用法：幅度（左，dB）+ 相位（右，degree）同屏。

# 6. Project Tree

层级：

```text
Project
└── Measurement          （一个导入的数据集）
    └── Parameter        （S11 / S21 / SDD21 ...）
        └── Trace        （某个显示格式的曲线）
```

- Measurement 是导入的单位，携带来源文件、名称、导入时间等元数据。
- Trace 携带所属 Measurement 的标识，用于图例区分与叠加对比。
- 树使用 `QAbstractItemModel` 适配领域对象，放在 `ui/models/`。

# 7. Selection Model

任一时刻存在三个"当前对象"：

```text
current_measurement
current_plot        （View Area 中被选中的格子）
current_trace
```

约定：

- 新建 Trace 进入 `current_plot`。
- 选中态属于 UI 状态，不写入领域对象，不持久化到 Project 文件（布局本身持久化，选中态不）。

# 8. Units Display

- 领域层一律 SI（Hz、秒），见 `AGENTS.md` §6。
- UI 层负责友好单位（GHz、ps、mm）与端口号 0-based → 1-based 的转换。
- 转换只在 UI 边界发生，不下沉到 Service 或算法层。
- 轴标签必须显式标注单位。

# 9. Interaction

- 缩放 / 平移：鼠标滚轮与拖拽，目标 30 fps（见 `PRODUCT.md` §6）。
- Autoscale：单图与全局两种触发。
- 多图联动（共享 X 轴缩放）为可选项，默认关闭。
- 长任务不得阻塞主线程超过 200 ms，超过走后台 Worker（`AGENTS.md` §8）。

# 10. Directory Layout

```text
src/interconnect_studio/ui/
├── main_window.py
├── views/       视图容器与网格编排
├── widgets/     可复用基础控件
├── panels/      外围停靠面板
├── models/      Qt model-view 适配
└── dialogs/
```

`main_window.py` 只做装配与信号连接，不实现具体视图逻辑（`AGENTS.md` §5.8）。

# 11. Open Decisions

- [ ] 布局状态在 Project 文件中的序列化格式（待 Project 格式决策）
- [ ] 多图联动的默认行为
- [ ] 主题 / 配色方案
