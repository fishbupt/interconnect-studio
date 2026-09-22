# PRODUCT.md

# 1. Product Vision

**Interconnect Studio** 是一款基于 Python + PyQt6 的 VNA / 高速互联数据分析与夹具去嵌软件。

目标用户：

- VNA 研发工程师
- RF/Microwave 测试工程师
- 高速互联 / SI 工程师
- 仪器算法研发工程师

# 2. Core Product Goals

- Touchstone 数据导入/导出
- S 参数显示与分析
- Smith / Polar / LogMag / Phase / Real / Imag
- Port Mapping
- Renormalization
- Mixed-Mode
- Frequency ↔ Time Domain
- TDR / TDT
- Gating
- Fixture De-embedding
- 2X-Thru / AFR
- 后续 Eye / NRZ / PAM4 / COM
- 后续 VNA 控制与自动测量

# 3. Product Principles

1. 数值正确性优先。
2. 结果可追溯。
3. UI 与算法解耦。
4. 高级功能模块化。
5. 自动测试和 Golden Regression 是发布门槛。
6. 参考商业软件行为，但不复制第三方专有实现。

# 4. User Scenarios

## 4.1 Touchstone Analysis

用户可加载 `.s1p/.s2p/.s4p/...`，选择参数和显示格式，添加 Marker，并导出结果。

## 4.2 Time Domain

用户可设置 Window、DC Extrapolation、Impulse/Step、Reference Shift，并查看 TDR/TDT。

## 4.3 Fixture De-embedding

用户可加载 Fixture / DUT 数据并执行已知夹具去嵌。

## 4.4 AFR

用户可加载 2X-Thru，配置夹具条件，提取 Fixture A/B，并对 DUT 去嵌。

# 5. Functional Requirements Template

## FR-001 Touchstone

- Reader / Writer：支持
- 支持版本：Touchstone 1.x
- 支持端口数：1 / 2 / 4
- RI / MA / DB：支持
- Hz / kHz / MHz / GHz：支持

## FR-002 Plot

- LogMag
- Phase
- Real
- Imag
- Smith
- Polar
- Group Delay
- Impedance

## FR-003 Mixed Mode

- differential pair mapping
- polarity
- SDD / SDC / SCD / SCC

## FR-004 Time Domain

- Low Pass Impulse
- Low Pass Step
- Band Pass
- Window
- DC Extrapolation
- Reference Shift

## FR-005 Gating

- Bandpass Gate
- Notch Gate
- Window / Transition
- Compensation

## FR-006 De-embedding

- Known Fixture
- 2X-Thru
- AFR

# 6. Non-functional Requirements

## Performance

硬规则（验收条件，适用于所有版本）：

- 任何操作阻塞 GUI 主线程不得超过 **200 ms**；超过必须进后台 Worker 并提供进度反馈。

参考值（仅进 nightly benchmark，不作 PR 门禁；受机器影响大，profiling 后修订）：

| 场景 | 参考值 |
|---|---|
| Touchstone 加载 4-port × 20k 点 | < 1 s |
| Touchstone 加载 16-port × 10k 点 | < 3 s |
| 首次绘图（单 trace，20k 点） | < 200 ms |
| 交互重绘（pan / zoom） | < 33 ms（30 fps 底线） |
| 时域变换（20k 点） | < 200 ms |
| AFR（4-port，10k 点） | < 5 s |

## Stability

- 长任务不得导致 GUI 无响应
- 后台任务支持错误反馈，必要时支持取消
- 异常输入不得导致应用无提示崩溃

## Reproducibility

- 算法 deterministic
- 关键结果记录参数与算法版本

# 7. UX Principles

- 测量工程师工作流优先
- 高级参数逐层展开
- 单位明确
- 原始数据与派生结果可追溯
- 重要操作可撤销/重做：`<后续决策>`

# 8. Version Scope

## V0.1 — Touchstone 查看器

- Network 核心模型
- Touchstone 1.x 读写（1 / 2 / 4 端口）
- Port Mapping
- Cartesian 绘图与现有显示格式
- MainWindow / Open / Add Trace

Exit：单元测试通过，且**首批 analytical golden case 已建立**（理想传输线、理想负载等可解析求解的结构）。在 Renormalization 与 Mixed-Mode 之前必须有数值基线——这两个模块最容易出约定性错误，且错了不会报错。

## V0.2 — 可用的 S 参数分析器

- Interpolation
- Renormalization
- Mixed-Mode
- Smith / Polar
- Marker / Autoscale / Multi Plot
- Recent Files / Settings

## V1.0 — 时域与基础去嵌（Roadmap Phase 4 ~ 6）

- 时域变换 / TDR / TDT
- Gating
- Cascade / Decascade / Known Fixture 去嵌
- Project 文件格式
- 完整 golden regression 套件

## V1.1 — 2X-Thru / AFR

Roadmap Phase 7 整体。AFR 是路线中最难、最易反复的部分，独立成版本以免拖延 V1.0 发布。

## V1.x+

仪器控制（Phase 8）、自动化（Phase 9）、Eye / PAM4 / COM（Phase 10）。
