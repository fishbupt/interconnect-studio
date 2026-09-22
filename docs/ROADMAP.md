# ROADMAP.md

# Interconnect Studio Roadmap

## Phase 0 — Agent-ready Repository

- [ ] 创建 `interconnect-studio`
- [ ] 包名 `interconnect_studio`
- [ ] pyproject.toml / uv
- [ ] src layout
- [ ] pytest / pytest-qt
- [ ] ruff / mypy
- [ ] GitHub Actions
- [x] AGENTS.md
- [x] docs
- [ ] Issue / PR templates

Exit：Agent 可独立完成小型 Issue → 测试 → CI → PR。

## Phase 1 — Network Core

- [x] Network
- [x] Touchstone Reader
- [x] Touchstone Writer
- [x] Port Mapping
- [x] Network 基础 S 参数访问接口
- [ ] Interpolation
- [ ] Renormalization
- [ ] Mixed Mode

Exit：完整 Unit Test + 基础 Golden Data + 无 GUI 依赖。

## Phase 2 — PyQt6 Application Shell

- [ ] Main Window
- [ ] Project Tree
- [ ] Plot Area
- [ ] Property Panel
- [ ] Log Panel
- [ ] File Open
- [ ] Recent Files
- [ ] Settings

## Phase 3 — Visualization

- [ ] Trace
- [x] LogMag / Phase / Real / Imag
- [x] Linear Mag / Unwrapped Phase / Group Delay / SWR / Impedance formats
- [ ] Smith / Polar
- [ ] Marker
- [ ] Autoscale
- [ ] Multi Plot

## Phase 4 — Time Domain

- [ ] Frequency preprocessing
- [ ] DC extrapolation
- [ ] Window
- [ ] Low Pass Impulse
- [ ] Low Pass Step
- [ ] Band Pass
- [ ] TDR/TDT
- [ ] Reference Shift

Exit：PLTS / Analytical Golden Regression。

## Phase 5 — Gating

- [ ] Bandpass Gate
- [ ] Notch Gate
- [ ] Window / Transition
- [ ] Compensation
- [ ] Frequency reconstruction

## Phase 6 — Basic De-embedding

- [ ] Cascade / Decascade
- [ ] Known Fixture
- [ ] Fixture Port Mapping

## Phase 7 — 2X-Thru / AFR

- [ ] Preprocess
- [ ] Fixture Length
- [ ] Fixture Z0
- [ ] Reflection Extraction
- [ ] Transmission Extraction
- [ ] Fixture Split
- [ ] Match Correction
- [ ] Length Correction
- [ ] Impedance Iteration
- [ ] Quality Metrics

## Phase 8 — Instrument Control

- [ ] SCPI abstraction
- [ ] VNA interface
- [ ] Connection manager
- [ ] Sweep config
- [ ] Acquisition
- [ ] Save measurement

Targets：自研 VNA / Keysight PNA-X / R&S ZNA。

## Phase 9 — Automation

- [ ] Batch Processing
- [ ] Script API
- [ ] CLI
- [ ] Report Generation
- [ ] MCP Integration

## Phase 10 — High-Speed Interconnect

- [ ] Eye Diagram
- [ ] NRZ
- [ ] PAM4
- [ ] Equalization
- [ ] Mask
- [ ] Jitter
- [ ] COM

# Agent Maturity

```text
L0 Chat
L1 Function generation
L2 Repository edits
L3 Complete Issue
L4 Build + Test + Fix
L5 PR
L6 Golden Regression
L7 PLTS/VNA automated validation
L8 Multi-Agent
L9 Mostly autonomous daily development
```

近期目标：L4 → L6。

# First Recommended Agent Issues

1. 创建标准 src layout
2. 建立 CI
3. 实现 Network
4. 实现 Touchstone Reader
5. 实现 Touchstone Writer
6. 实现 Port Mapping
7. 实现 LogMag/Phase calculation
8. 实现 Plot Model
9. 实现首个 PyQt6 MainWindow
10. 建立首批 Golden Case
