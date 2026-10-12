# ROADMAP.md

# Interconnect Studio Roadmap

本路线图以 [ARCHITECTURE.md §11](ARCHITECTURE.md#11-plts-核心概念规格与操作) 的 Window / Plot / Trace 语义为开发依据。状态核查日期：**2026-10-12**，文档核查基线：`5947f37`（下述 Window / Plot 状态已随 2026-10-12 实现更新）；依据为当前代码、已有测试和文件协议，不以目录存在或模型枚举存在代替端到端完成。

状态规则：`[x]` 表示该条描述范围已有实现与验证；`[ ]` 表示尚未完成。部分完成的工作拆成独立条目。阶段只有通过 Exit 才算完成，单个基础能力完成不代表整阶段完成。

范围边界：不开发独立 S 参数文件比较、A/B 页面、主动跨文件叠加、跨文件方程或 Multi-Data Template。旧工程中的多来源曲线仅保留读取、来源清理和导出兼容。多文件 Build、批量导入及夹具去嵌属于各自工作流，不等同于文件比较。

## 开发顺序与近期里程碑

| 顺序 | 工作包 | 优先级 | 依赖 | 交付目标 |
| --- | --- | --- | --- | --- |
| M1 | Phase 3.1–3.3：活动对象、Window、Plot | P0 | 已有 GUI / 文件流程 | 可创建、切换、增删和编排视图与图；New Plot 真正新增 |
| M2 | Phase 3.4：Trace | P0 | M1 | 同图同格式、稳定引用、容量和删除规则闭环 |
| M3 | Phase 3.5–3.6：Format / Scale、Marker | P1 | M2 | 完整频域显示、刻度及测量读数 |
| M4 | Phase 3.7–3.8：Math、图级信息、Template | P2 | M2；完整模板依赖 M3 | 同文件派生计算与完整显示配置复用 |
| 后续 | Phase 4–7.6：时域、Gating、去嵌、AFR、SI、RLCG | 后续 | 对应数值模型与 Golden Case；复用分析工作台 | 算法及 GUI 分层逐项交付 |
| 延后/待定 | Phase 8–11：仪器、自动化、高速互联、材料表征 | 后续/待决策 | 各阶段前置能力 | 不作为当前频域闭环的前置条件 |

工程保存/恢复、脏状态、后台任务有效性和测试贯穿 M1–M4，不集中到最后。这里只安排工作，本次不修改核心模型或工程格式；持久化字段变更需同步 `DOMAIN_MODEL.md`、`FILE_WORKFLOW.md` 与兼容性测试。

## 本次完成状态核查

| 工作 | 核查结论 | 代码 / 测试依据 |
| --- | --- | --- |
| Network、读写、Build、Subset、端口映射 | 基础实现完成；时域导入、混模未配对端口和导出重采样仍未完成 | `core/network.py`、`io/`、`algorithms/network/`；`test_import_readers.py`、`test_import_algorithms.py`、`test_network_writers.py` |
| DUT 配置与 Mixed Mode | 配置模型/对话框、变换及 Balanced 显示完成；混模 TraceRecipe、常驻配置面板仍未完成 | `core/dut.py`、`algorithms/mixed_mode/`；`test_dut_configuration.py`、`test_mixed_mode.py`、`test_main_window.py` |
| GUI 外壳 | pyqtgraph、docks、Parameter / Format 基础面板、底部可折叠日志、明暗主题已完成 | `ui/main_window.py`、`ui/theme.py`；`test_main_window.py`、`test_engineering_workspace.py` |
| 文件生命周期 | 多视图切换、关闭入口、未保存处理完成；最后一个 View 与文件生命周期已解耦，无窗口文件可保存/导出/重新开窗 | `FileWorkflow.request_close_view()`、`MainWindow._close_windows()`；`test_file_workflow.py` |
| 默认 s2p 显示 | Single-End 默认 2×2：S11/S12 上排，S21/S22 下排；切换及工程恢复有测试 | `test_two_port_import_uses_2x2_even_if_previous_grid_is_different`、`test_imported_two_port_matrix_layout_survives_window_switch_and_project_recall` |
| Plot 管理 | 活动图高亮、固定网格完成；New Plot 新增、显式替换、复制/删除/重排/放大已完成；完整活动对象身份待补 | `ui/views/plot_view_area.py`、`services/plot_layout.py`；`test_plot_view_area.py`、`test_window_plot_commands.py` |
| 频域格式 | 所有 Cartesian 格式，包括阻抗幅值/虚部幅值/角度、Q/D，已有算法与选择入口；Smith / Polar 只有模型与数据转换 | `algorithms/network/formats.py`、`ui/panels/parameter_format.py`；`test_s_parameter_formats.py`、`test_parameter_format_panel.py` |
| 刻度 | Y Min/Max、格式范围会话缓存、当前图/全部图 autoRange 完成；80% 纵向 Autoscale 与 Reset 语义仍需对齐 | `axis_range_controls.py`、`frequency_workflow.py`；`test_engineering_workspace.py`、`test_autoscale_all_enables_both_axes_and_empty_workspace_actions_disable` |
| Marker、Trace、数据表与导出 | 基础 Marker/Delta/Search、Trace 编辑、虚拟表、CSV/PNG 已完成；图级多曲线读数和高级 Marker 未完成 | `services/frequency_analysis.py`；`test_frequency_analysis.py`、`test_frequency_workflow.py` |
| Project 与偏好 | `.icproj` v2（读 v1）、最近文件、基础设置、`.icprefs` 导入导出完成；完整 PLTS 偏好未完成 | `io/project_file.py`、`ui/settings.py`；`test_project_file.py`、`test_file_workflow.py` |
| Template | 布局、标题、单端参数配方存取/列出/应用完成；完整模板及混模可复用配方未完成 | `core/template.py`、`io/template_file.py`、`services/template_service.py`；`test_template.py` |
| 数据质量与 Golden | Passivity / Reciprocity、pseudo-wave 阻抗转换、混模与导出 Golden 回归已有；Causality/Enforcement 未完成 | `quality.py`、`renormalize.py`、`tests/regression/` |
| 时域及后续算法 | 尚无时域、Gating、去嵌、AFR、RLCG、Eye 等对应实现；继续保留待办 | 当前算法目录仅有 `network/` 与 `mixed_mode/`，不将规划文档视为实现 |
| 文件比较 | 已移除并明确排除；旧工程兼容不是新的比较入口 | `test_workspace_has_analysis_controls_without_file_comparison`、`test_legacy_multi_source_plot_survives_recall_and_source_closing_removes_dependants` |

## Phase 0 — Agent-ready Repository

- [x] 仓库、包名、src layout、pyproject.toml / uv
- [x] pytest / pytest-qt、ruff / mypy、GitHub Actions
- [x] AGENTS.md 与架构/产品/领域/算法/测试文档
- [x] 首批耦合线对 Golden Case 与数值回归
- [ ] Issue template（可选工程维护工作）；当前按 AGENTS.md 直接提交 main，不以 PR template 作为开发门槛

Exit：按仓库规则完成实现、自查、质量检查与 main 提交；Golden Reference 不自动覆盖。

## Phase 1 — Network Core

- [x] Network
- [x] Touchstone Reader
- [x] Touchstone Writer
- [x] Port Mapping
- [x] Network 基础 S 参数访问接口
- [x] 通用 N 端口（去掉 1/2/4 限制）
- [x] Touchstone 2.0 / CITIfile 基础读写（2.0 写完整单端矩阵；CITIfile 明确使用 50 Ω）
- [x] 文本导入（tab / 逗号分隔）
- [ ] 时域数据导入（文本 / Touchstone 时间轴，需给 FFT Stop Frequency）
- [x] 导入 Subset（只截取 Start / Stop 范围内的测量点；不改变频点、不插值，产品决策）
- [ ] 导入多文件时的单端 → 差分映射
- [x] 多文件拼接（Build：按参数或按端口映射；`.csv` 配置文件驱动；单端 → 单端）
- [x] 只含平衡参数的数据反算单端参数（`to_single_ended`）
- [x] Touchstone 2.0 `[Mixed-Mode Order]` 读入，并据此预选 DUT Configuration
- [ ] Touchstone 2.0 `[Mixed-Mode Order]` 中的单端口描述符（`S<n>`）——需要`MixedModeNetwork` 容纳未配对端口，属核心模型变更
- [x] DUT Configuration 模型（单端 / 差分拓扑、逻辑端口、端口标签、`.dutcfg` 存取）
- [ ] 对照 PLTS 对话框核实 DUT 配置预设内部端口归属
- [x] DUT Configuration 接入 Import 对话框（任意端口数可选配置；导入结果携带`DutConfiguration`）
- [x] DUT Configuration 对话框的 Reset / Save As / Load
- [x] DUT Configuration 对话框内编辑端口标签（含逻辑端口与极性提示）
- [x] 端口标签接入 Parameter / Format 面板的 tooltip
- [ ] 端口标签在 trace 名、Tabular Trace Data、DUT Files 面板中的显示（当前 tooltip 已完成，不能据此勾选全部标签展示）
- [ ] DUT Configuration 面板（PLTS Lower Pane 的常驻面板）、DUT 端口重编号
- [x] 数据质量检查：Passivity / Reciprocity（只读，返回逐频点指标与越界频点）
- [ ] 数据质量检查：Causality——参考方法待决策，见 `ALGORITHM_GUIDE.md` §12.5
- [ ] 数据质量强制修正（Enforcement，写出修正后的文件）
- [x] Port Group 模型
- [ ] Interpolation
- [x] Renormalization（pseudo wave）
- [ ] Power-wave Renormalization（先明确波量与阻抗约定）
- [x] Mixed Mode（变换 + 拓扑 + 耦合线对 Golden Case）
- [ ] per-port / 差模共模参考阻抗的领域类型（对标 PLTS Port Reference Impedance、Diff/Com Port Reference Impedance；与单标量 `z0` 冲突，待决策）

Exit：完整 Unit Test + 基础 Golden Data + 无 GUI 依赖。

Passivity / Reciprocity、Renormalization 与 Mixed Mode 基础能力已完成；剩余工作涉及新的数值方法或领域模型时，需要先明确约定与 Golden Case。

## Phase 1.5 — GUI 框架与布局

本阶段基础外壳已落地；对象操作闭环安排在 Phase 3，避免继续把所有分析功能塞进“GUI 框架”。

- [x] pyqtgraph 交互绘图，`ui/` views / widgets / panels / models / dialogs 分层
- [x] ViewLayout 固定网格（Core 144 格上限；GUI 1×1、1×2、2×1、2×2）
- [x] Data Browser 分类 → 分析类型 → Window；未实现分析类型置灰
- [x] `BrowserCategory` / `ViewType` / `ViewWindow` / `DataFile` 基础层级
- [x] Window 独立网格、曲线、选中格、当前范围及会话格式范围缓存
- [x] 单端 TraceRecipe、稳定 source_id；历史多来源兼容
- [x] Parameter / Format 基础面板：参数矩阵、格式选择、Add Trace / New Plot 入口、Data Integrity Check、端口标签 tooltip
- [x] Property Panel 由 Parameter / Format 面板取代；底部消息 dock 默认折叠、状态栏按钮开关
- [x] View 菜单基础 dock 开关，面板浮动/停靠
- [x] 统一 TaskRunner、分析摘要与空状态、滚动配置区
- [x] 浅色工程主题、深色主题及菜单文字对比度修复
- [ ] 完整 View → Panes 分类与 Reset Layout（基础开关已完成，重置入口尚未完成）
- [ ] 多种工具栏及 View → Toolbars 开关体系
- [ ] 去嵌、参考阻抗修改、端口旋转状态指示（依赖相应业务）

Exit：外壳不执行数值算法；新增分析面板复用停靠体系与 TaskRunner。剩余工作不阻塞 M1。

## Phase 2 — 文件流程、工程与偏好

- [x] Main Window、Data Browser、Plot Area、基础参数面板及日志
- [x] 单文件导入、Multiple Files (Build a File)、配置文件 Build 三入口
- [x] Recent Files（最近 4 个测量/工程，去重、清空、失效路径提示）
- [x] Close File / Close All、退出与工程替换的保存/放弃/取消处理
- [x] `.icproj` v2 保存/恢复：嵌入测量、DUT 配置、窗口、曲线、Marker、当前范围与停靠状态；兼容 v1
- [x] 统一导出：Touchstone 1.x / 2.0、CITIfile、CSV / Tab；Subset、端口重映射、完整矩阵
- [x] 当前 Plot 曲线 CSV（来源、单位、独立频点长表）与 PNG / 剪贴板导出
- [x] 基础设置：目录、明暗主题、线宽、导出类型/单位、布局记忆、`.icprefs` 导入导出与默认值恢复
- [ ] 批量打开多个独立文件（统一 DUT 配置、Subset；不自动跨文件叠加）——现有 Multiple Files 是 Build，不是批量打开
- [ ] 导出重采样（Linear / Log / Dec / Oct）与每参数一文件
- [ ] 打印与打印预览
- [ ] 扩展全局偏好：按曲线序号配置颜色/线型/线宽、Marker 有效位、轴小数位、Log X、PASS/FAIL、单程时间及默认分析设置

Exit：文件失败不覆盖当前工程，写出原子化，Worker 不访问 Widget；各阶段新增对象状态均补保存恢复验证。

## Phase 3 — PLTS 核心对象与频域操作闭环

### Phase 3.1 — 活动对象与命令契约（P0）

- [x] 活动 Window、活动 Plot 及基础 Trace / Marker 选择入口
- [ ] 明确四级活动上下文，保存/恢复每个窗口的 Trace / Marker 选择；不只保存选中格
- [ ] 统一命令目标、菜单与按钮启用规则；删除后修复选择、Delta 与其他引用
- [ ] 为新增/删除/切换命令定义服务接口；后台结果检查目标会话仍有效
- [ ] 定义可持久化的 Plot / Trace 身份与引用迁移策略，避免重排破坏 Marker / 方程引用

Exit：选择与操作目标一致；空窗口/空图行为明确；切换或删除对象后无失效引用。对象身份方案先更新领域设计，再改代码。

### Phase 3.2 — Window 生命周期（P0）

- [x] 创建、激活、切换；同一文件打开多个视图
- [x] Close View / Close File、Rename File / Copy File Name 入口
- [x] 解耦 DataFile 与最后一个 Window 的生命周期；关闭最后一个 View 保留已加载文件及重新开视图入口
- [x] 将文件级保存/导出/脏状态从“是否有 Window”中解耦；补无窗口文件的恢复与关闭测试
- [x] 完善视图分析类型能力判断及关闭后的活动对象回退
- [x] Window 菜单、打开窗口列表与活动标记；Tile / Cascade / Maximize / Minimize / Restore / Close
- [x] 每窗口独立实时绘图区、手动移动/缩放、浮动至独立窗口与停靠回工作区

Exit：Close View 关闭视图，Close File 关闭文件及全部关联视图；数据与显示状态互不冒充。不能把 Plot 网格称为多窗口平铺。

### Phase 3.3 — Plot 集合与布局（P0）

- [x] 固定多图网格、活动 Plot 高亮
- [x] s2p Single-End 默认 2×2：S11/S12 上排、S21/S22 下排，切换/保存恢复保持顺序
- [x] Core 每 Window 最多 144 格校验
- [x] New Plot 真正新增；原“替换当前格子”拆为明确的 Replace Current Plot 操作
- [x] 新图插入活动图之后，定义空格复用、自动扩容及满额提示
- [x] Delete Plot、All Clear；缩小布局时不静默丢失有数据的图
- [ ] 参数批选：ALL、RL / IL / NEXT / FEXT、on One / on Many；TDR / TDT 分组随时域阶段接入
- [x] Copy to New Plot、Rename Plot（参考 22 字符限制）、拖动重排
- [x] 双击单图放大/还原；保持原布局与活动图
- [x] 图复制、删除和重排时同步处理刻度、Marker、曲线身份及工程脏状态

Exit：新增图保留原图，所有图管理操作可保存恢复；到达上限不丢失已有内容。

### Phase 3.4 — Trace 管理与格式约束（P0）

- [x] Trace / PlotModel、单端参数配方与来源绑定
- [x] Add Trace、Rename / Delete / Z-Order、基础 Legend 与所选曲线来源显示
- [ ] 显式图级格式契约：同图同格式；目前 Core 同单位校验不能保证同格式
- [ ] 不兼容格式的添加操作明确转为新图或提示，避免静默替换原图
- [ ] 每 Plot 36 条曲线边界及满额提示；删除最后一条保留空 Plot
- [ ] 混模 TraceRecipe：模式、端口、拓扑及参考阻抗语义，支持可复现刷新与模板应用
- [ ] Refresh Traces、标签来源悬停提示；显示名称不改变参数身份
- [ ] 多端口参数选择：拖选、按名称批量输入、参数名列表存取；基础单参数矩阵已完成
- [ ] Trace 数据更新后同步维护 Marker、派生配方与可见范围

Exit：容量、格式、来源和引用校验独立可测；曲线排序/重命名不破坏身份。单条任意样式不作为 PLTS 对齐项，样式配置走全局偏好。

### Phase 3.5 — Format 与 Scale（P1）

- [x] Log / Linear Mag、Phase / Unwrapped Phase、Group Delay、Real / Imaginary
- [x] SWR、阻抗 Real / Imaginary / Magnitude / Imaginary Magnitude / Angle、Q / D；反射参数适用性校验及 GUI 选择
- [x] Smith / Polar 数据转换与 Core PlotKind（不等于交互绘图完成）
- [x] 手动 Y Min/Max、格式范围会话缓存、当前图及全部图 autoRange
- [x] pyqtgraph 基础鼠标缩放/平移（不等于完整 PLTS Zoom / Pan 操作）
- [ ] Smith / Polar 绘制、刻度和交互；补充格式图标条
- [ ] Scaling bar：X/Y 范围、Ref Level + Units/Div、Min/Max、自定义步进
- [ ] PLTS 纵向约 80% Autoscale；核对 Autoscale All 的范围策略（现实现双轴自动范围）
- [ ] Reset Scale / Reset Scale All、明确框选 Zoom / Pan 模式及分析类型限制
- [ ] Copy / Paste Plot Format（格式与刻度，不复制数据）
- [ ] Log X、轴小数位；频率范围与测量区间约束

Exit：格式与原始参数分离；显示/单位转换不改 Network；不同分析类型提供正确的坐标行为。

### Phase 3.6 — Marker 测量体系（P1）

- [x] 创建/删除/拖动、左右键逐点、按 Hz 设置位置、测量点吸附
- [x] Min / Max / 最近测量 Target；Full / 当前可见 Span
- [x] 同图绝对 Marker 的 Delta 引用及工程保存恢复；基础停靠频域控制面板与读数
- [ ] 图级 Marker 位置与多 Trace 读数（当前 Marker 绑定单条曲线）
- [ ] 对齐向右首次目标/回绕/越界不移动的 Target Search；明确交点与吸附规则，保留最近 Y 点功能的独立名称
- [ ] 3 dB 搜索（传输参数）、自定义 User Span、位置滑块
- [ ] Coupling group（每图最多一组）、Marker Math
- [ ] Marker 表：显示开关、读数排序、过滤、有效位与图片导出
- [ ] 同分析域 Marker Set 保存/调用；独立 CSV/文本及剪贴板导出（普通曲线 CSV 已完成）
- [ ] Smith / Polar 读数、阻抗格式 Show LC Values

Exit：读数与搜索规则有独立服务测试；删除/重排曲线及联动后引用有效，Marker 状态可保存恢复。

### Phase 3.7 — Equation、Math 与派生 Trace（P2）

- [ ] 计算配方、输出单位、稳定引用、重算与失效策略
- [ ] 同 Plot Quick Math：加、减、乘、除；生成新 Trace
- [ ] Trace Statistics：Peak-to-Peak / Mean / Std Dev，Full / User Span
- [ ] 统计 Trace：均值、均值 ± σ/2，定义实时更新范围
- [ ] 同文件方程编辑器：频率/时间向量、端口阻抗变量、函数库、语法与单位校验
- [ ] 历史文件编号引用歧义解析至稳定来源 ID；不新增跨文件方程入口
- [ ] 方程应用为 Trace 或数值文本框、Equations 面板、工程/独立文件保存与结果导出
- [ ] Memory Trace：先核实官方冻结/刷新语义，再定义更新及持久化策略
- [ ] Python 脚本方程（延后；MATLAB 接口待决策）

Exit：计算可复现，同分析类型约束明确；重命名不破坏引用；删除输入后的处理可解释。禁止用显示标题作计算键。

### Phase 3.8 — 图级信息与单文件 Template（P2）

- [x] Template View 节点、保存/列出/应用布局、标题与单端参数/格式配方
- [x] JSON template 基础读写（当前后缀 `.json`）及覆盖保存服务（尚无完整独立 GUI 导入/导出流程）
- [x] 基础曲线 Legend；单文件统一蓝色实线
- [ ] Annotation：多条/多行、字体颜色、拖动、复制粘贴
- [ ] 完整图例配置：来源文件名/路径、显示控制；沿用单文件分析范围
- [ ] Save Template 覆盖当前模板、GUI Import / Export Template
- [ ] 模板纳入刻度、Marker、Equation；混模配方依赖 Phase 3.4
- [ ] Limit / Eye Mask 模板状态（分别依赖 Phase 7.5 / 10）
- [ ] 模板修改与已打开视图的更新边界；应用时重算目标文件曲线，不携带原始数据
- [ ] Trace Smoothing：孔径、作用范围、更新策略及平滑数据导出

Exit：模板与数据集/工程状态分离，单文件显示配置可复用；不实现 Multi-Data Template。

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

## 各里程碑统一验收

- 对象与状态变化同步更新架构/领域/文件协议文档；只改文档不自动改变公共格式。
- Unit / UI / 数值 Regression 按改动范围验证；提交前执行 AGENTS.md 要求的 Ruff、Mypy、Pytest。
- 新增持久化状态覆盖保存恢复、旧版读取、引用失效及失败不替换工作区。
- UI 不执行数值算法；耗时任务使用统一 TaskRunner；Worker 不访问 Widget。
- 保留原始 Network、显式单位与端口约定；Golden Reference 不自动覆盖。

## 下一轮推荐任务（M1 收尾 / M2）

1. 明确活动对象命令与稳定身份方案，更新领域设计。
2. 完善每个窗口的 Trace / Marker 活动选择恢复及后台命令有效性。
3. 完成同图同格式及不兼容格式的新图行为、曲线容量、混模配方。
4. 验收流程：导入 s2p 默认四图 → 新增图 → 添加曲线 → 复制/重排/删除图 → 切换视图 → 关闭最后一个视图后重新打开 → 保存并恢复工程。

Window / Plot 基础操作已落地；四级活动对象/稳定身份、批选参数、完整 Marker/Math/Template 和后续算法仍待实现。
