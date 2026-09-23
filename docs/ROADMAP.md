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
- [ ] 时域数据导入（文本 / Touchstone 时间轴，需给 FFT Stop Frequency）
- [ ] 导入 Subset（Start / Stop / Points / Step）与插值
- [ ] 导入多文件时的单端 → 差分映射
- [ ] 多文件拼接（Build：按参数或按端口映射；`.csv` 配置文件驱动）
- [ ] 只含平衡参数的数据反算单端参数
- [ ] DUT Configuration 模型（单端 / 差分拓扑、逻辑端口、端口标签、配置文件存取）
- [ ] 数据质量检查（Passivity / Causality / Reciprocity）
- [ ] 数据质量强制修正（Enforcement，写出修正后的文件）
- [ ] Port Group 模型
- [ ] Interpolation
- [ ] Renormalization
- [ ] Mixed Mode
- [ ] per-port / 差模共模参考阻抗的领域类型（对标 PLTS Port Reference Impedance、Diff/Com Port Reference Impedance；与单标量 `z0` 冲突，待决策）

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
  - 原文核对：PLTS 的 Data Browser 顶层是预置的分析类型（频域单端 / 平衡、时域单端 / 差分、眼图、RLCG 四种）与 Template View / Multi-data 节点，其下为已打开的 window；并非用户自建的 Group / Measurement。见 `PLTS_REFERENCE.md` §8，层级设计待重新决策
  - 文件右键：Close View / Close File / Copy File Name / Rename File
- [ ] Parameter / Format 面板
  - 数据来源文件下拉、S 参数 / 方程切换、New Plot / New Trace、ALL 与分组快捷（RL / IL / NEXT / FEXT、TDR / TDT、on One / on Many）
  - 多端口参数选择对话框（拖选、按名称批量输入、参数名列表存取）
  - 格式图标条、Data Integrity Check 入口
- [ ] Property Panel 由 Parameter / Format 取代，Log Panel 收进状态栏
- [ ] 选中态 / current 对象模型

- [ ] View → Panes 各面板开关、面板浮动 / 停靠、Reset 布局
- [ ] 状态栏指示灯（已去嵌、已改参考阻抗 / 端口旋转）

范围限定为**外壳与布局系统**；功能面板（Marker 编辑、Limit Line 编辑、串扰矩阵视图，以及 PLTS 的 Equations、DUT Configuration、DUT Files、Tabular Trace Data、Parameter Measurement Result 面板）待对应领域类型落地后再做。详见 `docs/UI_DESIGN.md`。

## Phase 2 — PyQt6 Application Shell

- [x] Main Window
- [x] Project Tree（Phase 1.5 重做为 Data Browser）
- [x] Plot Area
- [x] Property Panel（Phase 1.5 由 Parameter / Format 取代）
- [x] Log Panel（Phase 1.5 收进状态栏）
- [x] File Open
- [ ] Recent Files（PLTS 显示最近 4 个）
- [ ] Settings（对标 PLTS User Preferences：trace 颜色 / 线型 / 线宽、marker 有效位、轴小数位、Log X、PASS / FAIL 文字、单程时间、默认目录；多套偏好文件、恢复出厂）
- [ ] Close File / Close All Files，退出时批量处理未保存数据
- [ ] 批量打开 / 导入（同 DUT 配置、统一 Subset、可自动叠加到同一 plot）
- [ ] 导出对话框（Touchstone / CITIfile；Subset、点距 Linear / Log / Dec / Oct、端口重映射、每参数一文件或合一）
- [ ] 文本 / CSV 导出，含 plot 内全部 trace 一键存文本（PLTS Save Traces As）——待决策，见 `PRODUCT.md` §2 注
- [ ] 打印、打印预览、plot 图片导出（剪贴板 / 文件，分辨率可选）

## Phase 3 — Visualization

- [x] Trace
- [x] Plot Model
- [x] LogMag / Phase / Real / Imag
- [x] Linear Mag / Unwrapped Phase / Group Delay / SWR / Impedance formats
- [x] Add Trace / Format Selection
- [ ] Smith / Polar
- [ ] 阻抗各分量（Magnitude / Imag Magnitude / Angle）、Quality Factor、Dissipation Factor
- [ ] Marker（含 marker math、readout 排序、可停靠 marker bar）
  - [ ] 创建 / 删除 / 移动（滑块、键盘逐点、拖标签、Set At）
  - [ ] Marker Search：Min / Max / Target / 3 dB，Full / User Span
  - [ ] Delta marker、Coupled markers（coupling group）
  - [ ] Smith / Polar 读数（Mag + Phase / R + jX）
  - [ ] marker 表（显示开关、排序、过滤、导出图片）
  - [ ] Save State / Recall、导出到剪贴板；导出为文本（CSV，待决策）
  - [ ] Show LC Values（阻抗格式）
- [ ] Scaling bar（缩放工具栏；Ref Level + Units/Div 与 Min / Max 两种模式、自定义步进）
- [ ] View → Toolbars 各工具栏开关（Standard / Plot / Marker / Scaling / Quick Launch / Gating）
- [ ] Autoscale / Autoscale All、Reset Scale / Reset Scale All
- [ ] 框选 Zoom、Pan
- [ ] Copy / Paste Plot Format
- [ ] Log X 轴、轴小数位
- [ ] Multi Plot
- [ ] 活动 plot 高亮、双击单 plot 放大 / 还原、Delete 删除 plot
- [ ] plot 拖放重排、Copy to New Plot、Rename Plot
- [ ] Annotation（多行、字体颜色、拖动、跨 plot 复制）
- [ ] Trace：Rename / Delete / Refresh / Z-Order / Memory Trace / 来源文件悬停提示 / Legend
- [ ] Tabular Trace Data 面板
- [ ] Data Sharing（同一 plot 叠加不同文件的 trace；一键加到所有 plot）
- [ ] Trace Smoothing（平滑孔径：点数或跨度百分比；四种作用范围；导出平滑后数据）
- [ ] 多窗口管理：Tile / Cascade / Maximize / Minimize
- [ ] Template / Multi-Data Template（Data Browser 中的独立节点，多数据集同屏对比；导入导出 template）

## Phase 3.5 — Trace Math

对标 PLTS Math / Equations（见 `PLTS_REFERENCE.md` §4.4–§4.5）。

- [ ] Quick Math（两条 trace + − × ÷）
- [ ] Trace Statistics（Peak-to-Peak / Mean / Std Dev，Full / User Span）
- [ ] 统计 trace（均值、均值 ± σ/2，实时更新）
- [ ] 方程编辑器：多文件引用、频率 / 时间向量、端口阻抗变量、函数库、语法检查、输出单位
- [ ] 文件编号通配符与来源歧义解析
- [ ] 方程应用为 trace 或数值文本框；方程面板固定
- [ ] 方程存入工程 / 单独文件
- [ ] 带方程结果导出
- [ ] Python 脚本方程（对标 Collaborate with Python；MATLAB 接口待决策）

## Phase 4 — Time Domain

- [ ] Frequency preprocessing
- [ ] DC extrapolation（线性外推、圆外推、手动输入值或电阻；自带 DC 点时去除）
- [ ] Window（Exponential / Kaiser / Gaussian / Chebyshev / Hanning / Hamming / Blackman；宽度预设 Flat / Nominal / Fast Rise / Custom，可由上升时间或冲激宽度反设）
- [ ] Low Pass Impulse
- [ ] Low Pass Step
- [ ] Band Pass
- [ ] TDR/TDT（纵轴 Volts / Real / LogMag / Impedance，横轴时间 / 距离）
- [ ] 起止时间：Auto Optimize 与按参数手动设置
- [ ] Velocity Factor（Vf 或 εr）、单程时间 / 距离
- [ ] Reference Shift（PLTS 帮助未列此项，自有设计）
- [ ] 数据变更标识（重采样 / 插值 / 数据不足）
- [ ] 往返（FD → TD → FD）有效性校验
- [ ] 时域测量：Step Rise Time、Skew（百分比 / 电压参考、限值判定）、Trace Align、过剩 L / C、总 L 与 C
- [ ] Correct Impedance Profile（多次反射修正）
- [ ] Channel Loss Compensation
- [ ] 参考面调整（批量 / N 端口）
- [ ] TDR 阻抗 Flatten Slope（TC9）

变换算法：PLTS 使用 inverse chirp-Z Fourier transform，不是普通 IFFT。

Exit：PLTS / Analytical Golden Regression。

## Phase 5 — Gating

- [ ] Bandpass Gate
- [ ] Notch Gate
- [ ] 多 gate（PLTS 最多 10 个，按位置编号，可移动 / 删除）
- [ ] 作用范围：当前参数 / 全部反射参数
- [ ] Gating 视图：时域与频域并排，频域显示 gate 前后
- [ ] Impedance-Preserving Gating（PLTS 2026 U1）
- [ ] gate 后数据导出
- [ ] Window / Transition（PLTS 帮助未列出，自有设计）
- [ ] Compensation（PLTS 帮助未列出，自有设计）
- [ ] Frequency reconstruction

## Phase 6 — Basic De-embedding

- [ ] Cascade / Decascade
- [ ] Known Fixture
- [ ] Fixture Port Mapping（含按起始端口隔行分配多端口夹具文件）
- [ ] Embedding
- [ ] Reverse（镜像端口）
- [ ] Insertion Loss Only 去嵌
- [ ] Port Rotation / Extension
- [ ] Port Reference Impedance（per-port，依赖 Phase 1 新领域类型）
- [ ] Diff/Com Port Reference Impedance
- [ ] 调整可撤销，状态随工程保存
- [ ] 批量参考面调整（多文件、输出类型、文件名后缀、输出目录）

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

- [ ] NEXT / FEXT / PSNEXT / PSFEXT（PLTS 对应为 PSXT / MDNEXT 方程）
- [ ] ICN / ICR（PLTS 以方程形式提供，按 SAS 标准）
- [ ] IRL / IRLN
- [ ] Skew（intra-pair / inter-pair）
- [ ] 传播延迟 / 电长度
- [ ] ILD / ILfit
- [ ] 有效 Dk / Df
- [ ] Limit Line / Mask / Pass-Fail（Smith / Polar 格式下不适用）
  - [ ] 点表构造（Max / Min、目标 trace、颜色 / 线型、Connected、整体偏移）
  - [ ] Golden Trace 构造（由数据文件生成）
  - [ ] 方程构造
  - [ ] 复制到其他 plot、存取 limit 文件、从 `.txt` / `.csv` 导入
  - [ ] PASS / FAIL 显示与一键开关
- [ ] Report Generation（对标 Characterization Report Generator：页眉 / 内容项、plot 来源与尺寸、自定义模板标签）
- [ ] Delta-L（PCB 损耗方法学）

合规标准本身为外部可加载配置，不内置。

## Phase 7.6 — RLCG 与模型导出

- [ ] RLCG 传输线参数提取（W-Element / Differential / Common / Self-Mutual 四种模式；线长与最高提取频率）
- [ ] W-Element 显示：提取值 + 拟合值，或提取值 + 平滑值（按参数设平滑点数）
- [ ] HSPICE W-Element 导出
- [ ] HSPICE W-Element Tabular 导出（提取值 / 平滑值，可 Subset）
- [ ] ADS ML2CTL 导出
- [ ] ADS MDIF 导出（提取值 / 平滑值，自耦 / 互耦两个文件）
- [ ] TDA MeasureXtractor 导出
- [ ] Cadence Allegro PCB SI 导出

注：此前曾把宽带 SPICE 子电路导出排除在范围外；RLCG 的模型导出使该决定需要重新审视。

## Phase 8 — Instrument Control（待决策）

仪器连接与自动测量是否实现尚未决定。若实现，接口按「测量源」抽象以容纳 TDR 采样示波器。

PLTS 在此范围内的能力，供将来决策参考：Calibration & Measurement Wizard、ECal / SOLT / TRL、差分串扰 TRL 校准、适配器表征、Test Suite、Standard Test Wizard、Continuity Check、Measure 工具栏（快速重测）。

## Phase 9 — Automation

- [ ] Batch Processing
  - [ ] 批量格式转换（对标 Batched File Converter：不打开文件、频域 ↔ 时域）
  - [ ] Merge（两个频段合并，重叠取平均）
- [ ] Run Macro（运行脚本或 SCPI 命令列表，可挂到菜单）
- [ ] Script API
- [ ] CLI
- [ ] SCPI 命令接口
- [ ] MCP Integration

不含 COM 对象模型（Windows 专有）与功能分级授权。

## Phase 10 — High-Speed Interconnect

- [ ] Eye Diagram
- [ ] NRZ
- [ ] PAM4
- [ ] PAM3 / PAM6 / PAM8
- [ ] 统计眼图
- [ ] Bit Pattern：PRBS（含种子）/ ABS / K28.5 / 自定义编辑器 / 文件导入
- [ ] 眼图测量（PAM2 / PAM4 各项）、Color Grade、直方图、结果导出 CSV
- [ ] 眼图 marker
- [ ] Equalization（CTLE / FFE / DFE 及组合、自定义顺序、tap 文件）
- [ ] Mask（Eye Diagram Mask Test；点表 / 比例定义、DCA `.msk` 与 FlexDCA `.mskx` 导入、mask margin）
- [ ] Jitter（RJ / PJ / Dirac / F/2）、AWGN、预加重 / 去加重 / FIR
- [ ] COM（Channel Operating Margin）/ JCOM
- [ ] 多通道仿真（TX / 串扰源 + RX 均衡）
- [ ] IBIS-AMI 模型
- [ ] 由方程合成眼图

## Phase 11 — 材料表征（待定）

- [ ] PCB Material Characterization：Dk / Df / 表面粗糙度提取（Svensson-Djordjevic 介质模型、Huray / Cannonball 粗糙度模型、2D stripline 仿真；长短两线或单根 DUT；可选叠层参数）

对标 PLTS 选件 N19308B，是否实现待定。

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
