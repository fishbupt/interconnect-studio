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

- 支持版本：`<TODO>`
- 支持端口数：`<TODO>`
- RI / MA / DB：`<TODO>`
- Hz / kHz / MHz / GHz：`<TODO>`

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

- 大型多端口 Touchstone 加载：`<TODO>`
- 首次绘图：`<TODO>`
- Time Domain：`<TODO>`
- AFR：`<TODO>`

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

## V0.1

`<TODO>`

## V0.2

`<TODO>`

## V1.0

`<TODO>`
