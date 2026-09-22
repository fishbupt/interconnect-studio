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
│   │   ├── mixed_mode/
│   │   ├── time_domain/
│   │   ├── gating/
│   │   ├── deembedding/
│   │   └── afr/
│   ├── io/
│   ├── services/
│   └── instruments/
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

定义统一 VNA 抽象，不让具体驱动侵入 UI。

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

- Eye / PAM4 / COM
- Calibration
- VNA Automation
- Batch Processing
- CLI / Script API
- MCP Integration
- Plugin System

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

- [ ] pyqtgraph / matplotlib / custom plot
- [ ] Qt Designer `.ui` 或纯 Python UI
- [ ] Project 文件格式
- [ ] 是否采用 pydantic
- [ ] Plugin 机制
