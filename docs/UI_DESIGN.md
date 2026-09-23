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
- 主题：浅色默认、深色可切换，见 §9.5。

# 2.5 Reference

面板体系与 window 约束依据 Keysight PLTS 在线帮助 "The PLTS Screen" 与 "Working with Windows, Plots, and Traces"。

**功能对标 PLTS，视觉风格不对标**（见 §9.5）。

# 3. Window Layout

对标 PLTS 的面板体系（依据 Keysight PLTS 在线帮助 "The PLTS Screen"）。

```text
┌─────────────────────────────────────────────────┐
│ Menu Bar / Tool Bar                             │
├───────────────┬─────────────────────────────────┤
│ Data Browser  │                                 │
│ （Upper Pane）│                                 │
│               │        View Area                │
├───────────────┤        （固定网格）              │
│ Parameter /   │                                 │
│ Format        │                                 │
│ （Lower Pane）│                                 │
├───────────────┴─────────────────────────────────┤
│ Status Bar（含可展开的消息面板，默认折叠）        │
└─────────────────────────────────────────────────┘
```

约定：

- 左侧分 **Upper Pane** 与 **Lower Pane** 两个停靠区，与 PLTS 一致。
- **View Area 使用固定网格**（行 × 列），不可手动拖拽分割。
- 停靠面板可浮动、关闭、重排；中央 View Area 不是 dock，不可关闭。

## 与现有实现的差异

PLTS 没有 Property Panel 和 Log Panel，现有 `main_window.py` 中的这两个面板按如下方式处理：

- **Property Panel → 由 Parameter / Format 面板取代**。PLTS 中对应职责由该面板承担。
- **Log Panel → 收进状态栏**，配可展开的消息面板，默认折叠。保留诊断能力，但不占常驻空间。

## 面板清单

本轮实现：

| 面板 | 位置 | 职责 |
|---|---|---|
| Data Browser | Upper Pane | 数据层级导航 |
| Parameter / Format | Lower Pane | 开新 plot、向现有 plot 加 trace、为每个 plot 选格式、数据质量检查入口 |

后续功能面板（本轮只预留停靠位，不实现）：Marker（Math Definition）、Limit Lines / Eye Mask、当前 plot 的表格数据（Tabular Trace Data）、Equations、DUT Configuration、DUT Files、眼图测量结果（Parameter Measurement Result）。均为 PLTS 默认面板，见 `PLTS_REFERENCE.md` §3.1。

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
- **上限 144 个 plot**（12×12），与 PLTS 对齐。
- `plots` 按**行优先**顺序排列，与 Touchstone ≥3 端口的行主序一致。
- 空槽位用空 `PlotModel` 表示，不用 `None`。
- `ViewLayout` 不可变，变更返回新对象。
- 不依赖 PyQt6 或 pyqtgraph。

## Window 约束

对标 PLTS：**一个 window 只承载单个数据文件、单一分析类型**。

比较不同文件或不同分析类型需要开多个 window，而不是在同一个网格里混放。这条约束决定了 `ViewLayout` 归属于 window 而非全局。

# 5. Plot Axes

单个 `PlotModel` 只有一个 X 轴和**一个 Y 轴**。

- 一个 plot 承载一种显示格式，其中所有 Trace 共用该格式，与 PLTS 一致（*Data Format and Scale*：「Each plot can have a different format, and all traces within the plot have the same format」）。
- 因此同一 plot 内所有 Trace 的 `x_unit` 与 `y_unit` 都必须一致。
- 要同屏比较不同单位的量（如幅度与相位），开两个 plot，而不是加第二个 Y 轴。

> 曾短暂实现过左右双 Y 轴，依据是「PLTS 常态是幅度+相位同屏」——该前提有误，已按上述规范回退。

# 6. Data Browser

对标 PLTS 的三层结构（领域模型见 `DOMAIN_MODEL.md` §9，原文依据见 `PLTS_REFERENCE.md` §3.7）：

```text
Data Analysis
├── Time Domain (Differential)
├── Time Domain (Single-Ended)
├── Frequency Domain (Balanced)
├── Frequency Domain (Single-Ended)
│   └── dut.s2p : 1          ← 已打开的 window（文件名 : window 序号）
├── Eye Diagram (Differential)
└── Eye Diagram (Single-Ended)
RLCG
├── RLCG (Differential)
├── RLCG (Common)
├── RLCG (W-Element)
└── RLCG (Self/Mutual)
Calibration
├── Error Terms
└── Measured Standards
Template View
├── Create New
└── Create New for Multi-data
```

- **层级固定为三层**：分类 → 视图类型 → window。分类与视图类型是预置目录，始终显示；只有 window 随打开 / 关闭变化。
- 叶子是 window（`ViewWindow`），显示为「文件名 : window 序号」；选中 window 即选中其 `DataFile`。
- 有 window 的视图类型自动展开，其余折叠，与 PLTS 一致。
- 图标仿 Windows 资源管理器：分类与视图类型为黄色文件夹，展开时显示为打开的文件夹、折叠时为关闭的文件夹；分类文件夹带放大镜角标（同 PLTS），并以粗体显示；window 为文档图标。图标在代码中绘制（`ui/icons.py`），两套主题同色，不引入图片资源；置灰行的图标由 Qt 自动生成禁用态。
- 尚未实现的视图类型照样列出、置灰并提示 "Not available yet"，保持与 PLTS 相同的布局；目前只有 Frequency Domain (Single-Ended) 可用，打开文件即在其下新建一个 window。
- 参数与显示格式的选择**不在树里**，由 Parameter / Format 面板承担（PLTS 即如此）。
- 树使用 `QAbstractItemModel` 适配领域对象，放在 `ui/models/`。
- 选中 window 即切换视图区：每个 window 各自保存 plot 网格（`ViewLayout`）、选中格与数据文件（`ui/window_session.py`），切走时保存、切回时恢复；主窗口标题显示「文件名 - 分析类型 : 序号」（PLTS 标题栏同样显示文件名与分析类型）。新 window 沿用当前网格尺寸，默认 plot 放在第一格。
- window 右键菜单（同 PLTS）：
  - **Close View**：关闭该 window；
  - **Close File**：关闭该数据文件的所有 window；
  - **Copy File Name**：把文件显示名复制到剪贴板；
  - **Rename File**：输入新显示名，该文件的所有 window、参数面板、标题栏以及以旧文件名为标题的 plot 同步改名；文件 `id` 不变。空名、未改名或取消均不动作。
  - 关闭的是当前显示的 window 时，切换到剩余序号最大的 window；全部关闭后视图区清空为 1×1 空网格，Add Trace 置灰。
  - 面板只发出请求信号（`close_view_requested` / `close_file_requested` / `rename_file_requested`），由主窗口更新 `DataBrowserTree` 与各 window 的会话。
- 点击视图类型（同 PLTS）：为活动文件（当前显示 window 的数据文件）在该视图类型下新开一个空白 window，沿用当前网格尺寸，所有格为空 plot，并立即切换过去。新 window 与原 window 共享同一 `DataFile`（同一 `id`），因此 Close File / Rename File 同时作用于两者。未打开任何文件或视图类型置灰时不动作。面板发出 `open_view_requested(ViewType)`，由主窗口 `open_view` 执行。
- window 右键另有 **Save Template As...**（分隔线后）：输入名称，把该 window 的网格、plot 标题与 trace（参数 + 格式）存为 template；同名时先确认是否覆盖。
- Template View 在 Create New / Create New for Multi-data 之后按名称列出已保存 template，显示为「名称 (Np)」，N 为保存时文件的端口数；启动时读取，保存后刷新。
- 点击 template：用它为活动文件新开 window，列在该 template 节点下，标题栏显示「文件名 - template 名 : 序号」；文件端口不够时在状态栏提示并不打开。template 被删除后，其 window 改列在所属视图类型下。

# 7. Selection Model

任一时刻存在三个"当前对象"：

```text
current_file        （Data Browser 中选中 window 的 DataFile）
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

# 9.5 Visual Style

**功能对标 PLTS，视觉不对标**——PLTS 的界面是上一代 Windows 桌面风格，这里要更现代。

主题：

- **浅色为默认**（产品决策），深色可在 View → Dark Theme 切换。浅色与 PLTS 及 Windows 桌面习惯一致，截图入报告、打印可直接使用。
- 深色主题用于长时间看曲线的场景：深底上多条彩色 trace 区分度高。
- 两套主题都必须完整覆盖，不允许只调深色、浅色放任默认。

原则：

- 扁平化，避免拟物渐变与厚重边框；以留白和分隔线划分区域，而不是凹凸边框。
- 降低装饰性色彩，**颜色优先用于承载信息**（trace 配色、pass/fail 状态、越界标记）。
- trace 配色需在两套主题下都满足可区分度，并考虑色觉障碍（不以红绿单独区分 pass/fail）。
- 信息密度向工程工具靠拢：紧凑但不拥挤，控件尺寸与间距全局统一。
- 图标统一一套线性图标，不混用风格。
- pyqtgraph 的默认样式偏旧，必须统一主题化（背景、网格、坐标轴、字体），不得直接使用默认外观。

## Trace 配色

固定 8 槽分类配色，按槽位顺序分配，**不用生成器循环取色**。深浅两套同色相、各自分级，实现在 `ui/theme.py`。

两套均通过验证（CVD 分离度、正常视觉分离度、色度下限、明度带）：

| | 深色 | 浅色 |
|---|---|---|
| 最差相邻 CVD ΔE | 8.4 | 9.1 |
| 最差相邻正常视觉 ΔE | 19.3 | 19.6 |
| 表面对比度 | 全部 ≥ 3:1 | 3 个槽位低于 3:1 |

浅色主题下 aqua / yellow / magenta 三个槽位对比度不足 3:1，因此**trace 身份不得仅靠颜色**——图例必须始终列出每条 trace 的名称。超过 8 条 trace 时槽位回绕，此时只能靠图例区分。

字体与间距规范待后续确定。

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
- [ ] 字体与间距规范
- [x] Data Browser 层级：按 PLTS 改为分类 → 视图类型 → window（见 §6）
