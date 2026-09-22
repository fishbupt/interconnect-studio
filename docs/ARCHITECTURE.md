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
│   ├── core/
│   ├── algorithms/
│   │   ├── network/
│   │   ├── quality/            <planned>  V0.2  数据质量检查
│   │   ├── mixed_mode/         <planned>  V0.2
│   │   ├── time_domain/        <planned>  V1.0
│   │   ├── gating/             <planned>  V1.0
│   │   ├── crosstalk/          <planned>  V1.0
│   │   ├── si_metrics/         <planned>  V1.0
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

# 4. Layer Responsibilities

## UI

负责 Widget、View、用户输入和显示状态。禁止实现核心算法。

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

- Eye / PAM4 / COM（V2.0）
- Batch Processing
- CLI / Script API
- MCP Integration
- Plugin System

待决策（是否实现未定）：Calibration、VNA / TDR 仪器自动化、CSV / MATLAB 导出、宽带 SPICE 子电路导出。

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

- [x] 第一版 Cartesian Plot 使用 PyQt6 QPainter 自绘；后续是否迁移 pyqtgraph / matplotlib 仍可独立评估
- [ ] Qt Designer `.ui` 或纯 Python UI
- [ ] Project 文件格式
- [ ] 是否采用 pydantic
- [ ] Plugin 机制


## First GUI Flow

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
- 第一版 Plot Widget 使用 PyQt6 QPainter，不引入第三方绘图库。
