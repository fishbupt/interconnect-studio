# ARCHITECTURE.md

# 1. Architecture Goals

Interconnect Studio 架构目标：

- GUI 与算法彻底解耦
- 数值算法可独立运行与验证
- 支持 AI Agent 分模块开发
- 支持 Golden Regression
- 支持未来仪器控制、Batch、插件化

# 2. High-Level Architecture

```text
PyQt6 UI
   ↓
Application / Services
   ↓
Core Domain ─ Algorithms ─ IO ─ Instruments
```

# 3. Repository Layout

下图是**目标结构**。标注 `<planned>` 的目录当前尚未创建，由对应 Roadmap Phase 落地时再新建。

```text
interconnect-studio/
├── AGENTS.md
├── pyproject.toml
├── src/interconnect_studio/
│   ├── app/
│   ├── ui/
│   │   ├── views/              <planned>  视图容器与网格编排
│   │   ├── widgets/
│   │   ├── panels/
│   │   ├── models/             <planned>  Qt model-view 适配
│   │   └── dialogs/
│   ├── core/
│   ├── algorithms/
│   │   ├── network/
│   │   ├── quality.py          （在 network/ 下，已实现）
│   │   ├── mixed_mode/
│   │   ├── time_domain/        <planned>  V1.0
│   │   ├── gating/             <planned>  V1.0
│   │   ├── crosstalk/          <planned>  V1.0
│   │   ├── si_metrics/         <planned>  V1.0
│   │   ├── rlcg/               <planned>  V1.1  传输线参数提取
│   │   ├── deembedding/        <planned>  V1.0
│   │   └── afr/                <planned>  V1.1
│   ├── io/
│   ├── compliance/             <planned>  V1.0  Limit Line / Mask / Pass-Fail
│   ├── report/                 <planned>  V1.1
│   ├── services/
│   └── instruments/            <planned>  待决策，是否实现未定
├── tests/
├── golden_data/
├── docs/
└── scripts/
```

## 3.1 一条记录在案的例外：`io` → `algorithms`

`io/touchstone2.py` 导入 `algorithms.mixed_mode.to_single_ended`。

Touchstone 2.0 的 `[Mixed-Mode Order]` 文件存的是混合模式矩阵，而下游的一切
（DUT Configuration、Balanced 视图、trace）都以单端 `Network` 为输入。读的时候
就换回单端，这个文件从此就是一份普通测量，没有任何地方需要判断「数据从哪来」。
换算本身是 `Mᵀ S_mm M`，属于算法，不应该在 `io` 里再抄一份。

§5 的禁止清单是明确的三条（`Algorithms → UI`、`Core → UI`、`IO → UI`），这条边
不在其中。记在这里是为了让它成为一个决定，而不是悄悄长出来的依赖。

# 4. Layer Responsibilities

## UI

负责 Widget、View、用户输入和显示状态。禁止实现核心算法。

外壳结构、视图网格、导航树层级与交互约定见 `docs/UI_DESIGN.md`。

## Services

负责 Use Case、Workflow、任务编排和 Project 状态协调。

## Core

负责稳定领域对象：Network、Trace、PortMap、Project、Fixture、Result。

## Algorithms

- Pure Python / NumPy
- 无 PyQt6 依赖
- 输入输出明确
- 可独立 benchmark / regression

## IO

Touchstone、Project 文件、Export、Config。

## Instruments

仪器连接与自动测量**当前不实现**，是否实现留待后续决策。校准（ECal / SOLT / TRL）同此——只有在自己控制仪器采数时才有意义，读已校准的 Touchstone 不需要。

若将来实现：接口按「测量源」而非「VNA」抽象，使 TDR 采样示波器等非 VNA 仪器能够接入；具体驱动不得侵入 UI。

# 5. Threading Model

```text
Qt Main Thread
     ↓ submit
Task Runner / Worker
     ↓ result/error/progress
Qt Main Thread
```

禁止 Worker 直接更新 Widget。

实现：`ui/task_runner.py` 的 `TaskRunner`（`QThreadPool` + `QRunnable`），全项目共用一个，
不为每个功能各起一条线程。

- 放在 `ui/` 而不是 `services/`：它是 Qt 管道，放进 `services/` 会让该包依赖 PyQt6，
  而 services 不依赖 GUI 正是它可测的前提。**被运行的是一个普通 callable**，
  真正的工作仍然留在 Core / Algorithms / IO，可以脱离 Qt 直接测。
- 结果与错误经 signal 回到提交它的线程；异常只把一行消息给用户，完整 traceback 进 `logging`。
- `TaskHandle.cancel()` **不能**中断已经进入 NumPy 的运算，它只是不再投递结果——
  这正是「用户关掉对话框」需要的语义，docstring 里写明了，不假装能中断。

判据不是「感觉慢」而是实测：无源性检查是逐频点 SVD，4 端口 1601 点 11 ms，
32 端口 16001 点约 4 s，64 端口 32001 点 35 s。后两者都是合法文件。

# 6. Typical Data Flow

```text
Touchstone File
  ↓
TouchstoneReader
  ↓
Network
  ↓
Service
  ↓
Algorithm
  ↓
AnalysisResult
  ↓
Plot Model
  ↓
UI
```

# 7. Dependency Rules

允许：

```text
ui → services
services → core / algorithms / io / instruments
algorithms → core
io → core
```

禁止：

```text
core → ui
algorithms → ui
io → ui
```

# 8. Planned Extensions

- Eye / PAM4 / COM、多通道仿真（V2.0）
- RLCG 提取与模型导出（V1.1）
- Delta-L（V1.0）
- Batch Processing
- CLI / Script API
- MCP Integration
- Plugin System

待决策（是否实现未定）：Calibration、VNA / TDR 仪器自动化、CSV / MATLAB 导出。

明确排除：COM 对象模型、功能分级授权。

# 9. Architecture Decision Records

建议：

```text
docs/adr/
0001-network-data-shape.md
0002-plot-library.md
0003-task-executor.md
0004-project-file-format.md
```

# 10. Open Decisions

- [x] 绘图库：pyqtgraph 用于交互视图，matplotlib 仅用于报告导出。第一版的 QPainter 自绘在对标 PLTS 后重新评估并推翻——矩阵视图、眼图、20k 点 30 fps 缩放所需的工作量不成比例
- [x] 纯 Python UI，不使用 Qt Designer `.ui`
- [x] Project 文件格式（`.icproj` v1，JSON + NPY ZIP，含布局/曲线/数据；见 `FILE_WORKFLOW.md`）
- [ ] 是否采用 pydantic
- [ ] Plugin 机制


## First GUI Flow

> 本节描述的是**当前已实现**的单文件单图流程，将在 GUI 框架落地时被 `docs/UI_DESIGN.md` 的外壳与视图网格取代。其中的分层约束（MainWindow 不解析 Touchstone、Plot Widget 只消费 PlotModel）继续有效。

首个端到端 UI 流程：

```text
MainWindow
  ↓
File / Open Touchstone
  ↓
TouchstonePlotService
  ↓
read_touchstone()
  ↓
Network
  ↓
create_s_parameter_trace(S11/S21, LogMag)
  ↓
PlotModel
  ↓
CartesianPlotWidget
```

约束：

- MainWindow 不直接解析 Touchstone。
- UI 不直接执行 S 参数格式转换。
- Service 负责编排 IO 与算法。
- Plot Widget 只消费 PlotModel。

## 文件流程实现

`ui/file_workflow.py` 组合 MainWindow 的文件菜单、脏状态与最近文件；
`services/export_service.py` 编排范围截取、端口重排与明确的阻抗转换；
`io/network_writers.py` / `io/project_file.py` 负责写出/读取，`io/atomic.py` 负责原子替换。
工程对象位于 `core/project.py`，全局偏好使用 `ui/settings.py` 的 QSettings。
GUI 文件操作使用同一 TaskRunner，Worker 只处理预先收集的纯数据与服务调用。

## 频域交互

`core/marker.py` 与 `PlotModel.markers` 保存纯领域状态；
`services/frequency_analysis.py` 负责测量点吸附、搜索、Delta、曲线管理及 CSV。
`ui/frequency_workflow.py` 组合 MainWindow，管理停靠面板、对比选择和导出入口；
绘图 Widget 只发出拖动位置，通过服务生成新模型。数据表使用 QAbstractTableModel 虚拟读取。
Qt 图形渲染在 GUI 线程，CSV 和图片文件写入使用 TaskRunner。

TaskRunner 的内部完成信号先到 QObject 绑定的 GUI slot，再检查取消状态并投递公开结果。
因此工作已完成但结果仍在排队时，取消也会丢弃回调；销毁 runner 会断开排队的接收 slot。
TaskHandle 在投递结束前保留临时 runner，避免调用者仅传入临时对象时过早析构线程池。
