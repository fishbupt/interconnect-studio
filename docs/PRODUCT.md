# PRODUCT.md

# 1. Product Vision

**Interconnect Studio** 是一款基于 Python + PyQt6 的 VNA / 高速互联数据分析与夹具去嵌软件。

最终功能目标为**全面对标 Keysight PLTS**（数据分析侧）。对标指功能覆盖与数值可比，不复制其专有实现（见 §3.6）。

目标用户：

- VNA 研发工程师
- RF/Microwave 测试工程师
- 高速互联 / SI 工程师
- 仪器算法研发工程师

# 2. Core Product Goals

- Touchstone 1.x / 2.0、CITIfile 导入导出；文本（tab / 逗号分隔）导入
- S 参数显示与分析（承诺指标到 32 端口；PLTS 的参考面调整支持到 64 端口，上限是否上调待定）
- Smith / Polar / LogMag / Phase / Real / Imag
- Marker / Limit Line / Mask / Pass-Fail
- 数据质量检查与强制修正（Passivity / Causality / Reciprocity）
- Port Mapping
- Renormalization
- Mixed-Mode
- 串扰分析（NEXT / FEXT / PSNEXT / PSFEXT / ICN / ICR）
- SI 指标（Skew、传播延迟/电长度、ILD/ILfit、有效 Dk/Df）
- Frequency ↔ Time Domain
- TDR / TDT
- Gating
- Trace Smoothing
- 参考面调整（批量 / N 端口）
- RLCG 传输线参数提取与模型导出
- Delta-L
- Fixture De-embedding
- 2X-Thru / AFR
- 报告生成
- 后续 Eye / NRZ / PAM4 / COM、多通道仿真

不在当前范围（是否实现留待后续决策）：

- 仪器连接与自动测量
- 校准（ECal / SOLT / TRL、差分串扰 TRL、Calibration & Measurement Wizard）
- CSV / MATLAB 导出

明确排除：

- COM 对象模型（Windows 专有；自动化走 SCPI / Script API / CLI）
- 功能分级授权（Licensing）

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

## FR-001 File Formats

Touchstone 1.x：

- Reader / Writer：支持
- 支持端口数：通用 N 端口；**承诺测试并满足性能指标的上限为 32 端口**，更大端口数可读但不承诺指标
- RI / MA / DB：支持
- Hz / kHz / MHz / GHz：支持
- 数据排列约定见 `ALGORITHM_GUIDE.md`「Touchstone Data Ordering」

Touchstone 2.0（`.ts`）：

- Reader / Writer：支持
- per-port z0：**要求各端口一致**，不一致则抛 `DataFormatError`（`Network` 为单标量 z0，见 `DOMAIN_MODEL.md` §5）

CITIfile：

- Reader / Writer：支持（Keysight 仪器原生格式）

文本：

- Reader：tab 或逗号分隔

导出（模型与仿真工具）：

- HSPICE W-Element、ADS ML2CTL（RLCG 模型）
- TDA MeasureXtractor

导入多文件时支持单端 → 差分参数映射。

## FR-002 Plot

- LogMag
- Phase
- Real
- Imag
- Smith
- Polar
- Group Delay
- Impedance
- Marker（含 marker math 与 readout 排序）
- Limit Line / Mask（Smith / Polar 格式下不适用）
- Trace Smoothing

**一个 plot 承载一种显示格式，其中所有 Trace 共用该格式，因此只有一个 Y 轴**（对标 PLTS）。不同单位的量通过多个 plot 比较。

窗口与工具栏：多窗口 Tile / Cascade / Maximize / Minimize；可停靠的 marker bar；scaling bar；View → Toolbars 各项开关。

Template / Multi-Data Template：Data Browser 中的独立节点，用于多数据集同屏对比。

眼图等二维密度显示需要独立的数据模型，不通过扩展 `Trace` 实现（见 `DOMAIN_MODEL.md` §6）。

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
- 参考面调整（批量 / N 端口）
- TDR 阻抗 Flatten Slope（TC9）

变换算法：PLTS 使用 inverse chirp-Z Fourier transform，不是普通 IFFT；上升时间定义见 `ALGORITHM_GUIDE.md`。

## FR-005 Gating

- Bandpass Gate
- Notch Gate
- Window / Transition
- Compensation

## FR-006 De-embedding

- Known Fixture
- 2X-Thru
- AFR

## FR-007 Data Quality

检查为只读，不修改数据、不自动修正、不在 `Network` 上留质量标记：

- `check_passivity`
- `check_causality`
- `check_reciprocity`

返回指标与越界频点。**Enforcement**（强制无源 / 因果并写出修正后的文件）作为独立的显式算法，必须返回新对象并在 metadata 标注已修正，不得就地改写原始测量数据。

## FR-008 Crosstalk

- NEXT / FEXT
- PSNEXT / PSFEXT
- ICN / ICR

依赖 `DOMAIN_MODEL.md` 的 Port Group 模型定义 victim / aggressor 与近端 / 远端关系。

## FR-009 SI Metrics

- Skew：intra-pair / inter-pair
- 传播延迟 / 电长度
- ILD / ILfit
- 有效 Dk / Df

## FR-010 Compliance & Report

- Limit Line / Mask：通用机制
- Pass-Fail 判定
- 具体标准（USB / PCIe / DDR / IEEE 802.3 等）为**外部可加载配置文件**，不内置于软件
- 报告生成：排在合规机制之后，建议 HTML（无第三方依赖，可打印为 PDF）

## FR-011 RLCG 与模型导出

- RLCG 传输线参数提取，含 W-Element 模式
- 拟合结果导出为 HSPICE W-Element / ADS ML2CTL

## FR-012 Delta-L

PCB 损耗方法学，用于评估走线损耗。

# 6. Non-functional Requirements

## Performance

硬规则（验收条件，适用于所有版本）：

- 任何操作阻塞 GUI 主线程不得超过 **200 ms**；超过必须进后台 Worker 并提供进度反馈。

参考值（仅进 nightly benchmark，不作 PR 门禁；受机器影响大，profiling 后修订）：

| 场景 | 参考值 |
|---|---|
| Touchstone 加载 4-port × 20k 点 | < 1 s |
| Touchstone 加载 16-port × 10k 点 | < 3 s |
| Touchstone 加载 32-port × 5k 点 | < 10 s |
| 首次绘图（单 trace，20k 点） | < 200 ms |
| 交互重绘（pan / zoom） | < 33 ms（30 fps 底线） |
| 时域变换（20k 点） | < 200 ms |
| AFR（4-port，10k 点） | < 5 s |

## Memory

32 端口 × 20k 点的 S 矩阵本身即约 328 MB（`complex128`）。

- 加载峰值内存不得超过该数据量的 **3 倍**。
- 注意 `Network` 构造时复制输入数组、`Trace` 再复制一次；大端口数下这两次复制是主要压力来源。

## Stability

- 长任务不得导致 GUI 无响应
- 后台任务支持错误反馈，必要时支持取消
- 异常输入不得导致应用无提示崩溃

## Reproducibility

- 算法 deterministic
- 关键结果记录参数与算法版本

# 7. UX Principles

界面结构、视图网格与交互约定见 `docs/UI_DESIGN.md`。

- 测量工程师工作流优先
- 高级参数逐层展开
- 单位明确
- 原始数据与派生结果可追溯
- 重要操作可撤销/重做：`<后续决策>`

# 8. Version Scope

## V0.1 — Touchstone 查看器

- Network 核心模型
- Touchstone 1.x 读写，**通用 N 端口**
- Port Mapping
- Cartesian 绘图与现有显示格式
- MainWindow / Open / Add Trace

Exit：单元测试通过，且**首批 analytical golden case 已建立**（理想传输线、理想负载等可解析求解的结构）。在 Renormalization 与 Mixed-Mode 之前必须有数值基线——这两个模块最容易出约定性错误，且错了不会报错。

## V0.2 — 可用的 S 参数分析器

- Touchstone 2.0 / CITIfile
- 数据质量检查与强制修正（Passivity / Causality / Reciprocity）
- Port Group 模型
- Interpolation
- Renormalization
- Mixed-Mode
- 文本导入、导入时单端 → 差分映射
- Smith / Polar
- Marker（含 marker math、marker bar）/ Autoscale / Multi Plot
- Scaling bar 与工具栏开关
- Trace Smoothing
- 多窗口管理（Tile / Cascade / Maximize / Minimize）
- Template / Multi-Data Template
- Recent Files / Settings

数据质量检查排在 Renormalization / Mixed-Mode 之前：它是发现自身算法错误的主要工具。

## V1.0 — 时域、去嵌与合规

- 时域变换 / TDR / TDT
- Gating
- Cascade / Decascade / Known Fixture 去嵌
- 串扰分析（NEXT / FEXT / PSNEXT / PSFEXT / ICN / ICR）
- SI 指标（Skew、传播延迟/电长度、ILD/ILfit、有效 Dk/Df）
- Limit Line / Mask / Pass-Fail
- 参考面调整（批量 / N 端口）、TDR Flatten Slope
- Delta-L
- Project 文件格式
- 完整 golden regression 套件

## V1.1 — AFR、RLCG 与报告

- 2X-Thru / AFR（Roadmap Phase 7 整体）
- RLCG 提取与 HSPICE W-Element / ADS ML2CTL 导出
- TDA MeasureXtractor 导出
- 报告生成

AFR 是路线中最难、最易反复的部分，独立成版本以免拖延 V1.0 发布。

## V2.0 — 高速互联

Eye / NRZ / PAM4 / COM、多通道仿真（TX / 串扰源 + RX 的 FFE/DFE 均衡）、由方程合成眼图。

需要独立的二维数据模型（见 `DOMAIN_MODEL.md` §6）。

## 待决策（不在版本计划内）

仪器连接与自动测量、校准（ECal / SOLT / TRL、差分串扰 TRL、Calibration & Measurement Wizard）、CSV / MATLAB 导出。是否实现留待后续决定。

明确排除：COM 对象模型、功能分级授权。

注：RLCG 的模型导出（V1.1）已使「宽带 SPICE 子电路导出」这一早先的排除决定失效，两者是否合并为同一模块待定。
