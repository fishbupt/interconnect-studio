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
- [ ] 通用 N 端口（去掉 1/2/4 限制）
- [ ] Touchstone 2.0 / CITIfile（读写）
- [ ] 文本导入（tab / 逗号分隔）
- [ ] 导入多文件时的单端 → 差分映射
- [ ] 数据质量检查（Passivity / Causality / Reciprocity）
- [ ] 数据质量强制修正（Enforcement，写出修正后的文件）
- [ ] Port Group 模型
- [ ] Interpolation
- [ ] Renormalization
- [ ] Mixed Mode

Exit：完整 Unit Test + 基础 Golden Data + 无 GUI 依赖。

数据质量检查排在 Renormalization / Mixed Mode 之前：它是发现自身算法错误的主要工具。

## Phase 1.5 — GUI 框架与布局

先于 Network Core 剩余部分落地。外壳与布局系统与具体领域类型无关，早定可避免按单文件单图设计的外壳在多测量、多视图场景下返工。

- [ ] 迁移到 pyqtgraph，废弃 QPainter 自绘 widget
- [ ] `ui/` 子结构：views / widgets / panels / models / dialogs
- [ ] ViewLayout（固定网格）与视图区
- [ ] 外围面板改为 Qt dock
- [ ] 数据层级模型（Group / Measurement / DataFile）与 Trace 溯源
- [ ] Data Browser（Group → Measurement → DataFile）
- [ ] Parameter / Format 面板
- [ ] Property Panel 由 Parameter / Format 取代，Log Panel 收进状态栏
- [ ] 选中态 / current 对象模型

范围限定为**外壳与布局系统**；功能面板（Marker 编辑、Limit Line 编辑、串扰矩阵视图）待对应领域类型落地后再做。详见 `docs/UI_DESIGN.md`。

## Phase 2 — PyQt6 Application Shell

- [x] Main Window
- [x] Project Tree（Phase 1.5 重做为 Data Browser）
- [x] Plot Area
- [x] Property Panel（Phase 1.5 由 Parameter / Format 取代）
- [x] Log Panel（Phase 1.5 收进状态栏）
- [x] File Open
- [ ] Recent Files
- [ ] Settings

## Phase 3 — Visualization

- [x] Trace
- [x] Plot Model
- [x] LogMag / Phase / Real / Imag
- [x] Linear Mag / Unwrapped Phase / Group Delay / SWR / Impedance formats
- [x] Add Trace / Format Selection
- [ ] Smith / Polar
- [ ] Marker（含 marker math、readout 排序、可停靠 marker bar）
- [ ] Scaling bar（缩放工具栏）
- [ ] View → Toolbars 各工具栏开关
- [ ] Autoscale
- [ ] Multi Plot
- [ ] Trace Smoothing（平滑孔径）
- [ ] 多窗口管理：Tile / Cascade / Maximize / Minimize
- [ ] Template / Multi-Data Template（Data Browser 中的独立节点，多数据集同屏对比）

## Phase 4 — Time Domain

- [ ] Frequency preprocessing
- [ ] DC extrapolation
- [ ] Window
- [ ] Low Pass Impulse
- [ ] Low Pass Step
- [ ] Band Pass
- [ ] TDR/TDT
- [ ] Reference Shift
- [ ] 参考面调整（批量 / N 端口）
- [ ] TDR 阻抗 Flatten Slope（TC9）

变换算法：PLTS 使用 inverse chirp-Z Fourier transform，不是普通 IFFT。

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

## Phase 7.5 — Crosstalk / SI Metrics / Compliance

- [ ] NEXT / FEXT / PSNEXT / PSFEXT
- [ ] ICN / ICR
- [ ] Skew（intra-pair / inter-pair）
- [ ] 传播延迟 / 电长度
- [ ] ILD / ILfit
- [ ] 有效 Dk / Df
- [ ] Limit Line / Mask / Pass-Fail（Smith / Polar 格式下不适用）
- [ ] Report Generation（对标 Characterization Report Generator）
- [ ] Delta-L（PCB 损耗方法学）

合规标准本身为外部可加载配置，不内置。

## Phase 7.6 — RLCG 与模型导出

- [ ] RLCG 传输线参数提取（含 W-Element 模式）
- [ ] HSPICE W-Element 导出
- [ ] ADS ML2CTL 导出
- [ ] TDA MeasureXtractor 导出

注：此前曾把宽带 SPICE 子电路导出排除在范围外；RLCG 的模型导出使该决定需要重新审视。

## Phase 8 — Instrument Control（待决策）

仪器连接与自动测量是否实现尚未决定。若实现，接口按「测量源」抽象以容纳 TDR 采样示波器。

PLTS 在此范围内的能力，供将来决策参考：Calibration & Measurement Wizard、ECal / SOLT / TRL、差分串扰 TRL 校准。

## Phase 9 — Automation

- [ ] Batch Processing
- [ ] Script API
- [ ] CLI
- [ ] SCPI 命令接口
- [ ] MCP Integration

不含 COM 对象模型（Windows 专有）与功能分级授权。

## Phase 10 — High-Speed Interconnect

- [ ] Eye Diagram
- [ ] NRZ
- [ ] PAM4
- [ ] Equalization（FFE / DFE）
- [ ] Mask（Eye Diagram Mask Test）
- [ ] Jitter
- [ ] COM（Channel Operating Margin）
- [ ] 多通道仿真（TX / 串扰源 + RX 均衡）
- [ ] 由方程合成眼图

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
8. 实现 Plot Model（已完成）
9. 实现首个 PyQt6 MainWindow
10. 建立首批 Golden Case
