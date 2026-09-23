# PRODUCT.md

# 1. Product Vision

**Interconnect Studio** 是一款基于 Python + PyQt6 的 VNA / 高速互联数据分析与夹具去嵌软件。

最终功能目标为**全面对标 Keysight PLTS**（数据分析侧）。对标指功能覆盖与数值可比，不复制其专有实现（见 §3.6）。

PLTS 各功能与 UI 元素的原文核对清单见 `PLTS_REFERENCE.md`；本文件中「对标 PLTS」的条目均以其为依据。

目标用户：

- VNA 研发工程师
- RF/Microwave 测试工程师
- 高速互联 / SI 工程师
- 仪器算法研发工程师

# 2. Core Product Goals

- Touchstone 1.x / 2.0、CITIfile 导入导出；文本（tab / 逗号分隔）导入；时域数据导入
- 多文件拼接导入（Build）、批量打开 / 导入、批量格式转换、频段合并（Merge）
- S 参数显示与分析（承诺指标到 32 端口；PLTS 2018 起全局上限为 64 端口，导入本身不限端口数；我们的上限是否上调待定）
- 分析类型：频域（单端 / 平衡）、时域（单端 / 差分）、眼图（单端 / 差分）、RLCG（W-Element / Differential / Common / Self-Mutual）
- 频域格式：LogMag / LinMag / Phase / Unwrapped Phase / Group Delay / Smith / Polar / Real / Imag / SWR / 阻抗（Re / Im / |Z| / |Im Z| / ∠Z）/ Q / D
- Marker（搜索、耦合、Delta、marker math、保存 / 回调、导出）/ Limit Line / Mask / Pass-Fail
- Trace Math：方程编辑与应用、Quick Math、统计 trace（均值 / ±σ/2）、Trace Statistics
- 数据质量检查与强制修正（Passivity / Causality / Reciprocity）
- Port Mapping、DUT Configuration（单端 / 差分拓扑、逻辑端口）
- Renormalization（含 PLTS 的 per-port 参考阻抗与差模 / 共模参考阻抗，见 §5 FR-006）
- Mixed-Mode
- 串扰分析（NEXT / FEXT、功率和串扰、ICN / ICR）
- SI 指标（Skew、上升时间、过剩 / 总 L 与 C、传播延迟 / 电长度、ILD / ILfit、有效 Dk / Df）
- Frequency ↔ Time Domain
- TDR / TDT
- Gating
- Trace Smoothing
- 参考面调整（批量 / N 端口，含 Embedding 与 Port Rotation）
- Channel Loss Compensation、Correct Impedance Profile（多次反射修正）
- RLCG 传输线参数提取与模型导出
- Delta-L
- Fixture De-embedding
- 2X-Thru / AFR
- Template / Multi-Data Template、State 文件
- 报告生成、打印与图片导出
- 后续 Eye / NRZ / PAM-N / COM、多通道仿真、PCB 材料表征（Dk / Df / 表面粗糙度）

不在当前范围（是否实现留待后续决策）：

- 仪器连接与自动测量（含 Test Suite、Continuity Check、Standard Test Wizard 等测量流程功能）
- 校准（ECal / SOLT / TRL、差分串扰 TRL、Calibration & Measurement Wizard、适配器表征）
- CSV / MATLAB 导出

注：原文核对表明，PLTS 的 Text（comma delimited）导出、plot 右键 Save Traces As、marker 导出都是 CSV，属于其数据分析侧的常规导出；PLTS 没有 MATLAB 导出格式，MATLAB 在 PLTS 中是方程计算接口（见 FR-013）。「CSV 导出」是否仍列待决策需重新确认。

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

- Reader：支持（`[Two-Port Data Order]`、`[Reference]`、`[Matrix Format]`；混合模式数据暂不支持）；Writer：待做
- per-port z0：**要求各端口一致**，不一致则抛 `DataFormatError`（`Network` 为单标量 z0，见 `DOMAIN_MODEL.md` §5）

CITIfile：

- Reader：支持（Keysight 仪器原生格式；无参考阻抗字段，按 50 Ω 处理，待核对）；Writer：待做

PLTS 对 Touchstone 2.0 / CITIfile 端口阻抗不一致的文件同样拒绝导入（*Importing Data*），行为一致。

文本：

- Reader：tab 或逗号分隔（频域格式见 `ALGORITHM_GUIDE.md` §2.6）
- 时域数据（文本 / Touchstone，横轴为时间）导入；需指定 FFT 用的 Stop Frequency（PLTS 默认 20 GHz）
- DCA XY Verbose 波形（`.txt` / `.csv`）

导入对话框（对标 PLTS Import a Single File）：

- Data Domain（频域 / 时域）、文件类型、DUT Configuration
- 数据范围：All / Subset（Start / Stop），Reset；**不改变频点、不插值**（产品决策：PLTS 的 Points / Step 修改与 Interpolate 不提供，Subset 只截取测量点）
- 只含平衡参数的数据可导入并反算单端参数
- 导入后弹出 Select Analysis View，选择打开的分析类型

多文件拼接（对标 PLTS Import Multiple Files / Build a File）：

- 按单个参数或按端口映射；映射类型单端 → 单端、差分 → 差分、单端 → 差分
- 以 `.csv` 配置文件描述拼接（Build with a Configuration File），结果可直接导出为 `.sNp`
- 各源文件须频点一致、`z0` 相同（不重采样）

已实现（频域部分）：Import a Single File（Citifile / Touchstone 1.x 任意端口 / Touchstone 2.0 / 文本 tab / 逗号，Subset）、Select Analysis View、Import Multiple Files（单端 → 单端，按参数 / 按端口）、Build with a Config File、拼接结果导出 `.sNp`。未实现：时域导入、DCA XY Verbose、DUT Configuration 对话框、差分与单端 → 差分映射、只含平衡参数的数据、Yes to All / No to All。

批量与合并：

- 批量打开 / 导入：同 DUT 配置、同数据域的多个文件一次打开，可统一 Subset，可自动叠加到同一 plot
- 批量格式转换（对标 Batched File Converter）：不打开文件、可频域 ↔ 时域、输出选项同导出
- Merge：两个频段不同、参数相同的文件合并；间隙插值，重叠频段取平均

导出（对标 PLTS Export Data）：

- 频域：CITIfile、Touchstone（MA / DB / RI）、文本（RI、LogMag、LinMag、Phase、Unwrapped Phase、Group Delay、VSWR、Z Re / Im）
- 时域：文本、Touchstone；Step / Impulse × Real / Volts / LogMag，以及 Step Impedance
- 数据范围：Subset，点距 Linear / Log / 每 Decade / 每 Octave，插值
- 端口重映射导出；可选导出 gate 后、平滑后的数据及外推的 DC 值；可多参数合一文件或每参数一文件
- 经去嵌 / AFR 的数据在文件头注明（PLTS：`!Deembedding/AFR applied`）
- 可选在 Touchstone 注释中写入端口号与端口标签
- plot 内全部 trace 一键存为文本（PLTS：Save Traces As `.csv`）
- 以上文本导出（tab / 逗号分隔）即 PLTS 的 CSV 导出，是否纳入取决于 §2「CSV 导出」的决策

导出（模型与仿真工具）：

- HSPICE W-Element、ADS ML2CTL（RLCG 拟合模型）
- HSPICE W-Element Tabular、ADS MDIF（RLCG 提取值 / 平滑值，逐频点）
- TDA MeasureXtractor
- Cadence Allegro PCB SI（dB / angle 的 `.sNp`）

State 文件：保存并回调当前全部分析设置（PLTS `.dsta`；不含 RLCG 与 Gating）。由 Project 文件格式承担（V1.0）。

导入多文件时支持单端 → 差分参数映射。

## FR-002 Plot

显示格式（频域）：

- LogMag
- LinMag
- Phase
- Unwrapped Phase
- Real
- Imag
- Smith
- Polar
- Group Delay
- SWR
- Impedance：Real / Imag / Magnitude / Imag Magnitude / Angle
- Quality Factor / Dissipation Factor（PLTS 的电源完整性格式）

显示格式（时域）：激励 Impulse / Step；纵轴 Volts / Real / LogMag / Impedance（Impedance 仅 Step 激励的反射参数）；横轴时间或距离（距离由 Velocity Factor 换算，可按 Vf 或 εr 输入）；反射参数可选单程时间 / 距离。

**一个 plot 承载一种显示格式，其中所有 Trace 共用该格式，因此只有一个 Y 轴**（对标 PLTS）。不同单位的量通过多个 plot 比较。

Scale：

- Scaling bar：横纵输入框支持步进箭头、滚轮、带单位键入、自定义步进；纵轴在 Ref Level + Units/Div 与 Min / Max 两种模式间切换
- 横轴不超出测量范围；Smith / Polar 不可改横轴
- Autoscale / Autoscale All、Reset Scale / Reset Scale All
- 框选 Zoom、Pan（Smith / Polar / 眼图不支持 Zoom）
- Copy / Paste Plot Format（格式与刻度一起复制）
- 频域 Log X 轴；X / Y 轴小数位

Marker：

- 创建 / 选择 / 删除：marker bar 或 plot 右键
- 移动：marker bar 滑块、键盘逐点、拖动标签、Set At（输入 X 值）
- Marker Search：Min / Max / Target（向右搜索、回绕）/ 3 dB 点（仅传输参数）；Full Span / User Span
- Delta marker（1、2 号）；Coupled markers（可建多个 coupling group）
- Smith / Polar 读数：Mag + Phase 或 R + jX
- marker math（两个 marker 的 X 或 Y 读数做运算）与 marker 表（显示开关、排序、过滤、导出为图片）
- Save State / Recall（同域回调）；导出为逗号分隔文本或剪贴板
- 读数有效位数可设（1–10）
- Show LC Values（阻抗格式下在 marker 处显示 L / C 值）

Plot 与 Trace 交互：

- 活动 plot 高亮；双击单 plot 放大 / 还原；Delete 删除 plot
- plot 拖放重排、Copy to New Plot、Rename Plot
- Annotation：多行、字体与颜色、可拖动、跨 plot 复制粘贴
- Trace：Rename、Delete、Refresh、Z-Order 调整、Memory Trace、悬停显示来源文件、Legend（文件名或全路径）
- 键盘上下键 / 滚轮在 trace、marker 间循环
- Trace 颜色 / 线型 / 线宽（PLTS 仅能全局按 trace 序号设置，2026 起可右键单独编辑）
- Tabular Trace Data：活动 plot 的数据表
- 数据变更图标：Resampled / Interpolated / Bad Data、单程时间、Correct Impedance Profile

Parameter / Format 面板（对标 PLTS Parameter Format Selection）：

- 数据来源文件下拉；S 参数 / 方程两种来源
- New Plot / New Trace；ALL；分组快捷（频域 RL / IL / NEXT / FEXT，时域 TDR / TDT）+ on One / on Many
- 多端口参数选择对话框：拖选、按名称批量输入、参数名列表存取
- Data Sharing：同一 plot 叠加不同文件的 trace；一键把所选文件加到所有已开 plot。PLTS 原文允许叠加不同分析类型的 trace，与「一个 plot 一种格式」如何共存待确认

其他：

- Limit Line / Mask（Smith / Polar 格式下不适用，见 FR-010）
- Trace Smoothing：孔径按点数或跨度百分比；作用范围可选当前 trace / 所有 plot 的同参数 / 当前 plot 全部 / 全部；可导出平滑后数据

窗口与工具栏：多窗口 Tile / Cascade / Maximize / Minimize；可停靠的 marker bar；scaling bar；View → Toolbars 各项开关（Standard / Plot / Marker / Scaling / Quick Launch / Gating）；View → Panes 各面板开关；面板停靠、浮动与 Reset 布局；状态栏指示灯（已去嵌、已改参考阻抗 / 端口旋转）。PLTS 上限：每 window 144 个 plot，每 plot 36 个 trace（偏好可设每 window 最多 16–144 个 plot）。

Template / Multi-Data Template：Data Browser 中的独立节点，用于多数据集同屏对比。Template 保存 marker、方程、刻度、plot 名、limit / mask 等分析设置，可导入导出；Multi-Data Template 以文件夹为数据源，可选「每参数一个 plot 汇总所有文件」或「每文件每参数一个 plot」。

眼图等二维密度显示需要独立的数据模型，不通过扩展 `Trace` 实现（见 `DOMAIN_MODEL.md` §6）。

## FR-003 Mixed Mode

- differential pair mapping
- polarity
- SDD / SDC / SCD / SCC
- DUT Configuration（对标 PLTS）：每端口单端 / 差分、逻辑端口编号、端口标签、常用拓扑快捷选择（2 / 3 / 4 / 6 / 8 端口）、配置文件存取。PLTS 原文强调：导入时改拓扑只影响差分运算，不重映射数据
- 只含平衡参数的数据可反算单端参数

## FR-004 Time Domain

变换与窗（对标 PLTS Time Domain Settings）：

- Low Pass Impulse
- Low Pass Step
- Band Pass（仅 Impulse）
- Window 类型：Exponential、Kaiser（β）、Gaussian、Chebyshev（r）、Hanning、Hamming、Blackman
- Window 宽度预设：Flat Response（0.80）、Nominal（0.50，默认）、Fast Rise Time（0.20）、Custom（0.20–0.80，或直接给 Step Rise Time / Impulse Width）；设置可存为默认
- 起止时间：Auto Optimize On / Off；Manual 按参数设起止
- DC Extrapolation：自动线性外推、圆外推（对应 PLTS「PNA method」，适合回损 ≤ −30 dB）、手动（每个反射参数给线性值或电阻 Ω）；数据自带 DC 点时变换前去除
- Reference Shift（PLTS 帮助未列此项；PLTS 的对应能力是起止时间设置与 Port Rotation / Extension，保留为自有设计项）
- 数据变更标识：重采样 / 插值 / 谐波相关点不足
- 有效性校验：频域 → 时域 → 频域往返对比

测量（对标 PLTS plot 右键 Measure）：

- Step Rise Time：指定 trace 或全部 trace 最大值；可设限值给出 Pass / Fail；10–90% 或 20–80%（PLTS 默认 10–90%，我们默认 20–80%，见 `ALGORITHM_GUIDE.md`）
- Skew：两条 trace 或全部 trace 最大值；参考点为幅度百分比或绝对电压；可设限值；符号相对第一条 trace
- Trace Align（按两个 marker 对齐 trace，可撤销）
- Excess Inductance / Capacitance（两 marker 之间）
- Total Inductance & Capacitance（阻抗格式，正值报 nH、负值报 fF）

其他：

- 参考面调整（批量 / N 端口，见 FR-006）
- TDR 阻抗 Flatten Slope（TC9）：两个可拖 marker 之间拉平
- Correct Impedance Profile：修正多次反射造成的阻抗剖面失真（全局开关，结果带标识）
- Channel Loss Compensation：补偿线损与色散以锐化 TDR 峰；可用参考 thru 或由 DUT 估计，需器件长度与 Velocity Factor
- System Z0：PLTS 中只改变时域显示的全局参考阻抗（与数据 Renormalization 不同，见 FR-006）

变换算法：PLTS 使用 inverse chirp-Z Fourier transform，不是普通 IFFT；上升时间定义见 `ALGORITHM_GUIDE.md`（PLTS：Tr = (1000 / Fmax[GHz]) × RTEC ps，RTEC 按窗宽 0.91 / 0.71 / 0.54）。

## FR-005 Gating

对标 PLTS Gating：

- Bandpass Gate
- Notch Gate
- 最多 10 个 gate，按位置从左到右编号；可移动、删除
- 作用范围：当前参数，或（反射参数）全部反射参数
- 时域与频域并排显示，频域同时显示 gate 前后
- 被 gate 掉的区段以同电延迟的理想传输线代替；另有 Impedance-Preserving Gating（PLTS 2026 U1）
- gate 后的数据可导出

自有设计项（PLTS 帮助未列出）：

- Window / Transition
- Compensation

## FR-006 De-embedding 与参考面调整

- Known Fixture
- 2X-Thru
- AFR

对标 PLTS Reference Plane Adjustment（2 / 4 端口、N 端口、批量）：

- De-embedding 与 Embedding（`.sNp` / CITIfile）；Reverse（镜像端口）；Insertion Loss Only（回损与串扰置理想）；按起始端口隔行分配多端口夹具文件
- Port Rotation / Extension（mm，同时显示 ps）
- Port Reference Impedance：**每端口可不同**（0–1000 Ω）
- Diff/Com Port Reference Impedance：每个差分端口独立设差模 / 共模参考阻抗，单端参数由混合模式反算
- 调整可撤销（还原到原始数据），调整状态随工程保存；状态栏标识已去嵌 / 已调参考阻抗
- 批量：任意数量文件，输出类型同导出，文件名后缀，输出目录

注：per-port 参考阻抗与 `DOMAIN_MODEL.md` §5 的单标量 `z0` 冲突，需新的领域类型承载，是否及何时支持待决策。

## FR-007 Data Quality

检查为只读，不修改数据、不自动修正、不在 `Network` 上留质量标记：

- `check_passivity`
- `check_causality`
- `check_reciprocity`

返回指标与越界频点。**Enforcement**（强制无源 / 因果并写出修正后的文件）作为独立的显式算法，必须返回新对象并在 metadata 标注已修正，不得就地改写原始测量数据。

对标 PLTS Data Integrity Check：

- 对整个文件检查；Reciprocity 与 Causality 容差可设，可恢复默认
- 报告：Passivity 的最大值及频点；Reciprocity 的首个不互易参数对及频点；Causality 的最大相对 / 绝对误差及所在参数
- Enforcement 可按项勾选，结果写出到文件

注：PLTS 原文的无源判据写作「特征值 ≤ 1」，我们用奇异值（见 `ALGORITHM_GUIDE.md`）；PLTS 的因果强制是 ADS 专有算法，按 §3 原则 6 不复制，数值不会与 PLTS 一致。

## FR-008 Crosstalk

- NEXT / FEXT
- 功率和串扰：PSNEXT / PSFEXT（我们的命名；PLTS 对应为 Python 方程 PSXT、MDNEXT）
- ICN / ICR（PLTS 以方程形式提供，按 SAS 标准，并配 MiniSAS 模板）
- IRL / IRLN（Integrated Return Loss / Noise，PLTS 2024）

依赖 `DOMAIN_MODEL.md` 的 Port Group 模型定义 victim / aggressor 与近端 / 远端关系。

## FR-009 SI Metrics

- Skew：intra-pair / inter-pair（时域测量见 FR-004）
- 上升时间、过剩 / 总 L 与 C（见 FR-004）
- 传播延迟 / 电长度
- ILD / ILfit
- 有效 Dk / Df

PCB Material Characterization（PLTS 选件 N19308B）是有效 Dk / Df 的完整版：2D stripline 仿真 + Svensson-Djordjevic 介质模型 + Huray / Cannonball 粗糙度模型，由长短两线或单根 DUT 拟合出 Dk、Df 与表面粗糙度，可选输入叠层参数；结果为 Dk / Df 随频率曲线、仿真与实测 SDD21 对比，可导出 CSV。排入 V2.0 之后，是否实现待定。

## FR-010 Compliance & Report

- Limit Line / Mask：通用机制
- Pass-Fail 判定
- 具体标准（USB / PCIe / DDR / IEEE 802.3 等）为**外部可加载配置文件**，不内置于软件
- 报告生成：排在合规机制之后，建议 HTML（无第三方依赖，可打印为 PDF）

Limit Line（对标 PLTS）：

- 三种构造：点表、Golden Trace（由已有数据文件生成）、方程
- 点表：每条线的名称、Max / Min、目标 trace、颜色、线型；点的 X / Y 与是否与前一点相连；整体偏移（+ − × ÷）
- 复制到其他 plot；全部 limit 存为文件并回调（回调到原参数）；从 `.txt` / `.csv` 导入
- 判定时对 trace 插值，limit 点不必与数据点对齐；Smith / Polar 不适用；允许重叠
- plot 上显示 PASS / FAIL（可关，可设字号）；一键开关 limit 与 PASS / FAIL
- 上升时间、Skew 的限值判定见 FR-004

报告（对标 PLTS Characterization Report）：

- 页眉信息、内容项、plot 来源（当前 view 或 template）、plot 尺寸、输出格式
- 自定义模板：以标签映射 plot 图片、trace 数据表、marker 表、limit / mask 结果、skew 结果、测量信息（PLTS 用 Word 内容控件；我们建议用 HTML 模板）

打印与图片：

- 打印活动 window、打印预览
- plot 图片导出到剪贴板或文件，分辨率可选（PLTS 默认 1920×1080）

## FR-011 RLCG 与模型导出

- RLCG 传输线参数提取，含 W-Element 模式
- 四种模式（对标 PLTS）：W-Element（R11 / L11 / C11 / G11 / R12 / L12 / C12 / G12）、Differential 与 Common（R / L / C / G / Zo 实虚部 / 衰减常数 / 相位常数）、Self-Mutual
- 适用范围：对称、均匀的耦合差分线（4 端口）；2 端口数据应明确报错
- 输入参数：线长、最高提取频率（PLTS 默认测量上限的 90%）
- 拟合：R = R0 + Rs·√f，L、C 为常数，G = G0 + GD·f；W-Element 默认同时显示提取值与拟合值，可改为提取值与平滑值（按参数设平滑点数）
- 拟合结果导出为 HSPICE W-Element / ADS ML2CTL
- 提取值或平滑值导出为 HSPICE W-Element Tabular / ADS MDIF，可取 Subset

## FR-012 Delta-L

PCB 损耗方法学，用于评估走线损耗。

对标 PLTS Delta-L+ 4.0（IPC-TM-650 2.5.5.14）：

- 1L / 2L / 3L 三种方法
- 输入 `.s4p`、端口顺序、线长（ft / in / mm）；2L / 3L 可启用 Enhance Mode（平滑，需设迭代点数）
- 输出：1L 为单位长度插损均值与标准差；2L / 3L 为 Eigen Value、Curve Fitted 与 Uncertainty

## FR-013 Trace Math

对标 PLTS Math / Equations：

- 方程编辑器：引用已打开文件的参数（一个方程最多 3 个文件）、频率 / 时间向量、端口阻抗变量 Z1…Zn；函数 Abs、Arg、Conj、Delta、Imag、Ln、Log10、Mag、Phase、PhaseUnwrap、Pow10、Real、Sqrt、XAxisIndex、XAxisValue、getNumOfPoints、fileSum、subset；语法检查；输出单位（无 / Ω / dB）
- 文件编号通配符；打开的文件与方程引用不对应时逐项指定来源
- 方程只能应用于同分析类型的 plot；结果作为 trace，或作为数值文本框显示在 plot
- 方程可存入工程或单独文件，可固定到方程面板快速取用
- Template 中的方程只能引用单个文件
- Quick Math：plot 内两条 trace 做 + − × ÷
- 统计 trace：对 plot 内全部 trace 逐点求均值与均值 ± σ/2，随 trace 增删实时更新
- Trace Statistics：Peak-to-Peak、Mean、Std Dev，全跨度或用户跨度（与 marker 搜索共用）
- 带方程结果的数据可导出
- 外部脚本方程（PLTS：Collaborate with MATLAB / Python）：把参数映射到脚本函数输入、取输出为 trace；可运行时输入参数；可输出单点值；可输出 X / Y 作为频段受限的 limit。我们的对应物为 Python 脚本方程，MATLAB 接口是否支持待决策

## FR-014 Eye / COM（V2.0）

对标 PLTS（详见 `PLTS_REFERENCE.md` §4.11–§4.13）：

- 眼图：时域冲激响应与码型卷积，仅传输参数；NRZ / PAM4，PLTS 2026 起 PAM3 / PAM6 / PAM8；统计眼图
- 码型：PRBS（至 2^31−1，可设种子）、ABS、K28.5、自定义（8–32 位编辑器）、从文件导入；速率、上升 / 下降时间、幅度
- 眼图测量：PAM2 与 PAM4 各项电平、眼高、眼宽、抖动、RLM 等；Color Grade、直方图；结果导出 CSV
- Eye Mask：点表 / 比例定义，导入 DCA `.msk` 与 FlexDCA `.mskx`，mask margin，PASS / FAIL 与失败点计数
- 多通道仿真：TX / XT TX / RX 组件；抖动（RJ / PJ / Dirac / F/2）、AWGN、预加重 / 去加重 / FIR；RX 均衡 CTLE、FFE、DFE 及组合与自定义顺序；tap 文件；配置存取
- IBIS-AMI 模型（PLTS 仅 bit-by-bit 模式）
- 由方程合成眼图
- COM / JCOM：外部标准配置文件驱动，THRU / FEXT / NEXT 端口指定，结果与中间量上 plot

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
- 文本导入、导入时单端 → 差分映射、导入 Subset（只截取测量点，不插值）
- DUT Configuration（单端 / 差分拓扑、逻辑端口、端口标签）
- 多文件拼接导入（Build）、批量打开 / 导入
- 数据导出（Touchstone / CITIfile，含 Subset 与端口重映射；文本 / CSV 导出待决策，见 §2 注）
- Smith / Polar 及其余频域格式（SWR、阻抗各分量、Q / D）
- Marker（含搜索、Delta、耦合、marker math 与 marker 表、marker bar、保存 / 回调、导出）/ Autoscale / Multi Plot
- Scaling bar（Ref / Div 与 Min / Max 两种模式）与工具栏开关、Zoom / Pan、Copy / Paste Plot Format
- Plot / Trace 交互：重排、复制、重命名、注释、legend、Z-order、Memory Trace、Tabular Trace Data
- Trace Smoothing
- Quick Math、Trace Statistics
- 多窗口管理（Tile / Cascade / Maximize / Minimize）
- Template / Multi-Data Template
- Recent Files / Settings（对标 PLTS User Preferences，含多套偏好文件）
- 打印与 plot 图片导出

数据质量检查排在 Renormalization / Mixed-Mode 之前：它是发现自身算法错误的主要工具。

## V1.0 — 时域、去嵌与合规

- 时域变换 / TDR / TDT（窗类型与宽度、DC 外推方式、按参数起止时间）
- 时域测量：上升时间、Skew（含限值判定）、Trace Align、过剩 / 总 L 与 C
- Correct Impedance Profile、Channel Loss Compensation
- Gating
- Cascade / Decascade / Known Fixture 去嵌、Embedding
- 串扰分析（NEXT / FEXT / PSNEXT / PSFEXT / ICN / ICR / IRL）
- SI 指标（Skew、传播延迟/电长度、ILD/ILfit、有效 Dk/Df）
- Trace Math（方程编辑器、统计 trace、带方程结果导出）
- Limit Line / Mask / Pass-Fail（点表、Golden Trace、方程三种构造）
- 参考面调整（批量 / N 端口，含 Port Rotation 与 per-port 参考阻抗，后者依赖新领域类型）、TDR Flatten Slope
- Delta-L
- Project 文件格式（PLTS 对应物：State 文件 `.dsta`，以及 `.dut` 中保存的方程、参考面调整、System Z0 等分析状态）
- 完整 golden regression 套件

## V1.1 — AFR、RLCG 与报告

- 2X-Thru / AFR（Roadmap Phase 7 整体）
- RLCG 提取（四种模式）与 HSPICE W-Element / W-Element Tabular、ADS ML2CTL / MDIF 导出
- TDA MeasureXtractor、Cadence Allegro PCB SI 导出
- 报告生成（含自定义模板）

AFR 是路线中最难、最易反复的部分，独立成版本以免拖延 V1.0 发布。

## V2.0 — 高速互联

Eye / NRZ / PAM4（及 PAM3 / PAM6 / PAM8）/ COM / JCOM、码型与 Eye Mask、多通道仿真（TX / 串扰源 + RX 的 CTLE / FFE / DFE 均衡）、IBIS-AMI、由方程合成眼图，见 FR-014。

需要独立的二维数据模型（见 `DOMAIN_MODEL.md` §6）。

PCB Material Characterization（Dk / Df / 表面粗糙度提取，FR-009）排在 V2.0 之后，是否实现待定。

## 待决策（不在版本计划内）

仪器连接与自动测量、校准（ECal / SOLT / TRL、差分串扰 TRL、Calibration & Measurement Wizard）、CSV / MATLAB 导出（见 §2 注）、外部 MATLAB 方程接口。是否实现留待后续决定。

明确排除：COM 对象模型、功能分级授权。

注：RLCG 的模型导出（V1.1）已使「宽带 SPICE 子电路导出」这一早先的排除决定失效，两者是否合并为同一模块待定。
