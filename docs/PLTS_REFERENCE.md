# PLTS_REFERENCE.md

# 1. Purpose

Keysight PLTS 数据分析侧功能与 UI 元素的**原文核对清单**，是 `PRODUCT.md` / `ROADMAP.md` 中「对标 PLTS」各条目的依据。

- 来源：PLTS 在线帮助 <https://helpfiles.keysight.com/csg/N1930xB/Home.htm>，2026 Update 1 版本，2026-09 抓取。
- 范围：Getting Started、Analyzing Data、File and Print Operations、Tools and Utilities 四章全部页面（按帮助 TOC 核对无遗漏）。仪器连接、校准、Licensing、Programming 章节未逐页核对。
- 每节标题后括号内为帮助页路径（相对上述 URL 根目录），便于回查原文。
- 本文件只记录 PLTS **有什么**；我们做不做、何时做，以 `PRODUCT.md` / `ROADMAP.md` 为准。
- 标注 `[仪器]` 的条目依赖测量硬件，属于 `PRODUCT.md` 中「仪器连接与自动测量」待决策范围，此处仅为完整性列出。

# 2. 与此前文档的差异（原文核对结论）

此前清单基于搜索摘要整理。逐页核对后的结论：

**已核实无误**

- 时域变换使用 inverse chirp-Z Fourier transform（*Analyzing Data in the Time Domain*）。
- Flatten TDR Impedance Slope 依据 TC9（同上）。
- 一个 plot 一种格式、plot 内所有 trace 共用格式（*Data Format and Scale*）。
- Limit Line 在 Smith / Polar 格式下不可用（*Limit Lines*）。
- Data Integrity Check 含 Passivity / Reciprocity / Causality 检查，并可把 enforce 后的数据写出到文件（*Data Integrity Check*）。
- Touchstone 2.0 / CITIfile 各端口参考阻抗不一致时 PLTS 拒绝导入（*Importing Data*），与我们「不一致抛 `DataFormatError`」一致。
- RLCG 导出 HSPICE W-Element 与 ADS ML2CTL；TDA MeasureXtractor 导出（*RLCG Data Formats*、*TDA MeasureXtractor*）。
- Delta-L、多通道仿真（TX / 串扰源 + RX FFE/DFE）、由方程合成眼图、Template / Multi-Data Template。

**需要修正**

| 此前表述 | 原文 |
|---|---|
| 「PLTS 的参考面调整支持到 64 端口」 | 64 端口是 PLTS 2018 起的**全局**上限（DUT Configuration、参数选择、导入、导出、参考面调整均为 64）；导入文件本身自 Rev 4.0 起端口数不限。 |
| 串扰「PSNEXT / PSFEXT / ICN / ICR」为内建分析 | PLTS 的 NEXT / FEXT 是参数面板的快捷分组；ICN / ICR / ILD 是 MATLAB 方程（按 SAS 标准，配 MiniSAS 模板）；功率和串扰为 Python 方程 **PSXT**（8 端口示例）及 Python 函数 **MDNEXT**、**sumDiff**。原文无「PSNEXT / PSFEXT」字样。另有 IRL / IRLN（2024 版本说明）。 |
| Gating 含「Window / Transition」「Compensation」 | Gating 页只有 Bandpass / Notch 两种模式、最多 10 个 gate、被 gate 掉的区段以同电延迟的理想传输线代替；无窗形 / 过渡带 / 补偿选项。2026 U1 另增 Impedance-Preserving Gating。 |
| 时域含「Reference Shift」 | 原文无此项。对应能力是 Tools → Time Domain Settings 的 Start / Stop Time 与 Reference Plane Adjustment 的 Port Rotation / Extension。 |
| 「Renormalization」 | PLTS 有三处：System Z0（所有端口同值，**只影响时域显示**）、Reference Plane Adjustment 的 Port Reference Impedance（**每端口可不同**，0–1000 Ω）、Diff/Com Port Reference Impedance（每个差分端口独立设差模 / 共模阻抗）。后两者产生 per-port 参考阻抗，与 `DOMAIN_MODEL.md` §5 单标量 `z0` 冲突，见 §8。 |
| 「CSV / MATLAB 导出」待决策 | PLTS 的 Export 含 Text（tab / comma delimited），即 CSV；plot 右键 Save Traces As 也直接存 `.csv`。原文没有 MATLAB 导出格式，MATLAB 在 PLTS 中是方程计算接口（Collaborate with MATLAB）。 |
| Data Browser 为 Group → Measurement → DataFile | 原文 Data Browser 顶层是**预置的 Data Analysis 类型**（见 §3.4）+ Template View + Multi-data 节点，其下是已打开的 window（按 `.dut` 文件）。见 §8。 |
| 有效 Dk / Df | PLTS 对应功能是 PCB Material Characterization（选件 N19308B），用 2D stripline 仿真 + Svensson-Djordjevic 介质模型 + Huray / Cannonball 粗糙度模型拟合出 Dk、Df、表面粗糙度，范围远大于「有效 Dk / Df」。 |

**此前清单完全遗漏的大项**：Trace Math / 方程系统、Quick Math、统计 trace、Trace Statistics、Marker 的搜索 / 耦合 / 保存 / 导出 / 表格、各种时域测量（上升时间、Skew、Trace Align、过剩 / 总 L 与 C、Correct Impedance Profile）、Channel Loss Compensation、System Z0、Velocity Factor、DUT Configuration、State 文件、Merge Manager、Batched File Converter、批量打开 / 导入、多文件 Build、打印与图片导出、User Preferences、Run Macro、PCB Material Characterization，以及大量 plot / trace 级交互（见 §3–§7）。

# 3. Getting Started

## 3.1 主界面（GettingStarted/The_PLTS_Screen.htm）

- Title Bar：显示活动 plot window 的文件名（已保存时）与分析类型；未保存时显示 `PLTS` + 分析类型 + 序号。
- Menu Bar：菜单随活动 window 的分析类型变化。
- Upper Pane 停靠区默认面板：Data Browser、Marker（Math Definition）、Limit Line / Eye Mask、Tabular Trace Data。
- Lower Pane 停靠区默认面板：Parameter / Format Selection、Equations、DUT Configuration、DUT Files、Parameter Measurement Result（眼图）、Data Integrity Check。
- Data Browser 文件右键：Close View、Close File、Copy File Name、Rename File。
- Tabular Trace Data 面板：活动 plot 的数据表。
- DUT Configuration 面板：当前数据的 DUT 拓扑图。DUT Files 面板：当前测量的文件信息（含 System Z0）。
- Marker Bar：在活动 plot 上开关、选择、拖动 marker；可拖到屏幕顶部，启动时总在底部；眼图与 Polar / Smith 下形态不同。
- Status Bar 指示灯：Measurement、Continuous sweep、De-Embedding（活动 plot 已去嵌）、Port Rotation（已应用参考阻抗 / 端口旋转）、Hardware。

## 3.2 View 菜单（GettingStarted/View_Menu.htm）

- Panes：逐个开关面板。
- 面板拖放：可停靠到 Upper / Lower 停靠区或 Plots 区，也可浮动；拖动时出现方向导航器。
- Reset Toolbars and Docking Panes：恢复默认布局（需重启）。
- Toolbars：
  - Gating Toolbar（启用 gating 时出现）
  - Marker Toolbar
  - Measurement Toolbar `[仪器]`
  - Plot Toolbar：Pan、Zoom、Limits / Eye Mask 开关、Marker Save / Recall、Re-order（plot 拖放重排）
  - Quick Launch Toolbar：Export Data、Import 单文件、Import 多文件、Apply Bit Pattern
  - Scaling Toolbar
  - Standard Toolbar：New、Open、Save、Copy（plot 到剪贴板）、Export Bitmap、Remove Plot、Print、About
- Status Bar 开关。
- Application Look：界面主题。

## 3.3 Window / Plot / Trace（GettingStarted/Working_with_Windows_Plots_and_Traces.htm、Plot_Annotation_and_Legends.htm）

Window：

- 一个 window 只含一个 DUT 文件、一种分析类型；Window 菜单 Maximize / Tile / Cascade / Minimize。
- 每个 window 最多 144 个 plot；满 144 时再加 plot 被忽略。
- 关闭：窗口 X，或 Data Browser 右键 Close View。

Plot：

- 活动 plot 以绿色方括号标示。
- 双击 plot 单独放大显示，再双击恢复全部。
- 选中 plot 按 Delete 删除；All Clear 删除全部可见 plot。
- 拖放重排（Plot Toolbar 的 Re-order）。
- 右键 Copy to New Plot（复制 plot 及其全部 trace，新 plot 换色）。
- 右键 Rename Plot（≤ 22 字符；默认名为首个参数名）。
- 右键 Add Annotation：多行文本、字体 / 字号 / 样式 / 颜色，可拖动，右键 Edit / Delete，Ctrl+C / Ctrl+V 复制到其他 plot；是否限制在绘图区内由偏好设置决定。

Trace：

- 每个 plot 最多 36 个 trace（旧版 16；2026 版本说明称「多文件到单 plot」上限由 36 提至 100）。
- Trace 名显示在 plot 右侧，颜色与 trace 一致；鼠标悬停显示所属文件名。
- 键盘上下键 / 滚轮在 trace 或 marker 间循环高亮。
- 右键 trace 名：Rename Trace（约显示前 25 字符）、Delete Trace（plot 内多于一条时）、Add Legend / Add All Legends（加文件路径与文件名）/ Delete Legend、Memory Trace。
- 右键 plot：Refresh Traces、Change Z-Order of Traces（对话框上下移动后 Apply）。
- Trace 颜色、线型、线宽只能在 User Preferences 全局设置（2026 U1 增加右键 trace 名编辑属性）。

Parameter / Format Selection 面板：

- DUT File 下拉：选取数据来源（已打开文件）。
- S 参数 / 公式（Equation）两种来源切换。
- New Plot / New Trace 模式；ALL 一键添加当前可见 16 个参数；横纵滚动条切换另一组 16 个参数。
- ALL 旁下拉：频域 RL / IL / NEXT / FEXT 分组，时域 TDR / TDT 分组，以及 on One（全部进一个 plot）/ on Many（每个一个 plot）。
- 点按已按下的参数按钮即从 plot 移除该 trace。
- Select Parameters 对话框（端口多时）：红（未绘）/ 绿（已绘）/ 蓝（待增删）按钮，拖选多个；逗号分隔输入参数名（DUT 端口 > 4），参数名列表 Save / Load `.txt`；快捷键列表；New Plot(s) / New Trace(s) / On One New Plot。
- 格式图标条：为活动 plot 选显示格式（与 Format 菜单等价）。
- Data Integrity Check 入口。

Data Sharing：

- 同一 plot 叠加不同文件的 trace，参数甚至分析类型可不同（原文示例：一个文件的 S11 与另一个文件的 TDD22 同 plot）。
- DUT File 下拉切换数据来源后点参数即加入活动 plot；All Data Sharing 把所选文件加入所有已开 plot。

## 3.4 分析类型（GettingStarted/TDR_Wizard.htm「Select Analysis View」、Analyzing 各页）

- Frequency Domain（Single-Ended）、Frequency Domain（Balanced）
- Time Domain（Single-Ended）、Time Domain（Differential）
- Eye Diagram（Single-Ended）、Eye Diagram（Differential）
- RLCG（W-Element）、RLCG（Differential）、RLCG（Common）、RLCG（Self/Mutual）

## 3.5 DUT Configuration（GettingStarted/DUT_Configuration.htm）

- DUT 端口数（PLTS 2018 起最多 64）。
- Quick Topologies：2 端口（SE-SE、Differential Reflection）、3 端口（Diff-SE、SE-SE）、4 端口（Diff-Diff、Diff-SE、SE-Diff、SE-SE）；另有 2 / 3 / 4 / 6 / 8 端口的图形化拓扑选择。
- 每个端口切换差分 / 单端；Uncouple Adjacent Differential Ports（默认输入输出联动）。
- Logical 端口编号（差分对由两个 DUT 端口组成）、DUT 端口重编号、端口标签（替代 `<<<<` / `>>>>` 箭头）、测量所用 VNA 端口 `[仪器]`。
- 配置文件 `.dcf` 的 Save As / Load；Reset 恢复默认。
- 导入单文件时从 Import 对话框的 Change 按钮进入；原文强调此处改拓扑**只影响差分运算，不重映射数据**。

## 3.6 其他

- Wizard 的 Load Measurement：直接选 DUT 文件进入分析（GettingStarted/PLTS_Wizard.htm）。
- Test Suite：保存 DUT 配置、测量设置、校准选择与 Template，`.xml` 导入导出 `[仪器]`（GettingStarted/Test_Suite_Wizard.htm）。
- F1 / 对话框 Help 按钮跳转上下文帮助（GettingStarted/About_PLTS_Help.htm）。

# 4. Analyzing Data

## 4.1 显示格式（Analyzing/Data_Format_and_Scale.htm）

频域：Log Mag（默认）、Linear Mag、Phase（±180° 折叠）、Unwrapped Phase、Group Delay、Smith、Polar、Real、Imaginary、SWR、Impedance Real、Impedance Imaginary、Impedance Magnitude、Impedance Imaginary Magnitude、Impedance Angle、Quality Factor、Dissipation Factor。后几项为电源完整性（PI）格式。

时域：

- Stimulus：Impulse / Step（默认）。
- 纵轴：Volts（默认；无响应显示为 200 mV，满幅 ±200 mV，模拟 DCA）、Real、Log Mag、Impedance（仅 Step 激励的反射参数）。
- 横轴：ns（默认）/ cm，距离换算依赖 Velocity Factor。

RLCG：电感单位 H、电阻单位 Ω；眼图与 RLCG 不可选格式。

## 4.2 Scale（同上）

- Scaling Bar：横纵各输入框支持上下箭头、滚轮、直接键入（可带单位）；可设步进；纵轴在「Ref Level + Units/Div」与「Min / Max」两种模式间切换。
- 横轴不能超出测量范围；Smith / Polar 不可改横轴。
- 右键 Autoscale（纵轴约占 80%）/ Autoscale All；Reset Scale / Reset Scale All。
- Plot Toolbar 的 Zoom（框选；眼图、Polar、Smith 不可用）、Pan（或 Shift + 拖动）。
- 右键 Copy Plot Format / Paste Plot Format（格式与刻度一起复制）。
- 偏好：新建 plot 时自动 Autoscale；频域 Log X 轴；X / Y 轴小数位。

## 4.3 Markers（Analyzing/Markers.htm）

- 创建：Marker Bar 选编号后 ON；或右键 Marker → Insert（Smith / Polar 不可用）。
- 选择：Marker Bar 或点击 marker。
- 移动：Marker Bar 滑块（选中后左右键逐点移动）、拖动 marker 标签、右键 Marker → Set At...（选单位后输入 X 值；Smith / Polar / 眼图不可用）、Marker Search。
- 读数：显示在 plot 右侧；有效位数由偏好设定（1–10）。
- Delta Marker：偏好「Add Delta Markers for First Added 2 Markers」，只对 1、2 号 marker。
- Coupled Markers：右键 Marker Coupling 对话框，勾选参与耦合的 plot，可建多个 Coupling Group（每个 plot 只属一组），Select All / Clear All。
- Marker Search：Full Span / User Span（与 Trace Statistics 共用）；Minimum、Maximum、Target Value（向右搜首个匹配，到头回绕，重复 Execute 继续搜）、Half-Power（3 dB）Point（仅传输参数）。
- Smith / Polar marker 读数：Mag + Phase 或 Impedance（R + jX）。
- 删除：Marker Bar OFF，或右键 Marker → Delete。
- Save State / Recall：保存整组 marker，只能回调到同域（频域 / 时域）。
- Export Data：逗号分隔 `.txt`；Export Data to Clipboard。
- Marker Math Definition 面板：选 marker、X 或 Y 读数、运算符、第二个 marker 与读数，Add 进 marker 表。
- Marker Table：Show / Hide 勾选决定哪些读数上 plot、全选、导出 plot + marker 表为 `.bmp` 或剪贴板、删除行、上下移动排序、文本过滤。
- Show LC Values：PI 格式（Zr、Zi、|Z|、|Zi|）下在 marker 处显示 L / C 值并画 LC 线，同时强制 Log X / Log Y。

## 4.4 Trace Math 与方程（Analyzing/Math.htm、MatLab_Equations.htm、Python_Equations.htm、Create_Phase_Equation_Example.htm）

Create Equations 对话框（Tools → Math → Design）：

- DUT File（一个方程最多引用 3 个文件）、Domain（频域单端 / 平衡、时域单端 / 差分）、Data 列表（带搜索）、Time Vector / Frequency Vector、Key Pad。
- Variables：各端口阻抗 Z1…Zn（不必为 50 Ω）。
- Functions：Abs、Arg、Conj、Delta、Imag、Ln、Log10、Mag、Phase、PhaseUnwrap、Pow10、Real、Sqrt、XAxisIndex、XAxisValue、getNumOfPoints、fileSum（对所有打开 view / multi-data template 同参数求和）、subset(param, f1, f2)（频段限制）。
- New Wildcard（`?` 代替文件编号）、Check（语法检查，错误标红）、Equation Name、Output Unit（无 / Ω / dB）。
- Save（存入内存）、Pin / Unpin to Equations Pane、Save Advanced（存入活动 `.DUT` 或导出 `.fml`）、Load `.fml`。

Choose Equation Traces to Display 对话框（Tools → Math → Apply）：

- 只列出与活动 trace 分析类型相同的方程。
- Apply to Trace、Apply to Text Box（结果以可编辑注释显示在 plot）、Remove Trace、Remove Text Box、Delete、Pin、Unpin All、Save Advanced、Import。
- Resolve Data Ambiguity 对话框：方程引用的文件编号与当前打开文件不对应时逐项指定；可选「本会话始终用活动文件」。

限制：Template 中的方程只能引用单个文件。

Quick Math：plot 内两条 trace 做 + − × ÷，结果作为新 trace；右键 Remove All Quick Math。

带数学结果的数据可导出（Export 的 Math 域）。

MATLAB / Python 方程（Tools → Math → Collaborate with MATLAB / Python）：

- 选 `.m` / `.py` 文件，把数据映射到输入变量、选输出变量；Output Unit；Wildcard；Config Python（解释器路径）。
- Allow assigning input variables at runtime（运行时输入参数）。
- Extended Domain X-Y（dB–mV rms、dB–dB，支持单点输出并设 marker 样式）。
- Equation Based Limits：输出 X、Y 两个变量，作为频段受限的限值线。
- 内置方程：ICN、ICR、ILD（SAS）、PSXT（Python，8 端口示例）、MDNEXT、sumDiff、PI 的 Series-Through / Shunt-Through 阻抗法。

## 4.5 统计（Analyzing/Statistical_Equation_Traces.htm、Trace_Statistics.htm）

- Statistical Equation Traces：对 plot 内全部 trace 逐点求 Mean、Upper（Mean + σ/2）、Lower（Mean − σ/2）；实时随 trace 增删更新，计入 trace 数上限。
- Trace Statistics：对选中 trace 显示 Peak-to-Peak、Mean、Std Dev；Full Span / User Span；数值很小时自动换单位。

## 4.6 Trace Smoothing（Analyzing/Trace_Smoothing.htm）

- 右键 Trace Smoothing；作用范围四选一：选中 plot 的选中参数 / 所有 plot 的该参数 / 选中 plot 的所有参数 / 全部。
- Smoothing ON；孔径按 Percent of Span 或 Points。
- Export Smoothed Data。

## 4.7 Limit Lines（Analyzing/Limit_Lines.htm）

- 三种构造方式：Limit Points、Golden Trace、Equation。Smith / Polar 不可用；允许重叠。
- Limit Mask Definition 面板 → Points：
  - Line Properties 表：Add、Name、Type（Max / Min）、Target（trace）、Color、Offset（选 + − × ÷ 与数值，每点一次叠加一次）、Delete。
  - Points 表：X、Y、Connected（是否与前一点连线）；Add 插在选中行下方。
  - Apply；Copy To Other Plots；Save / Load 全部 limit 文件（回调时只作用于原参数）。
  - Import：`.txt` / `.csv`，频率须为 MHz，否则报错。
- Golden Trace：导入 `.txt` / `.csv` / `.cit` / `.sNp`，选参数、Stimulus / Response 列、Min / Max；可由频域数据算出时域 limit。
- Equation：方程 trace 在 Limit 面板 Equation 模式下「Set as Limit Line」为 Min_Limit / Max_Limit。
- PASS / FAIL 文字显示在 plot 顶部；Plot Toolbar 一键开关 limit 与文字；偏好单独开关文字及字号；判定时对 trace 插值，不要求 limit 点与数据点对齐。
- 版本说明：limit 线型 / 颜色可设（2023、2025）。

## 4.8 Data Integrity Check（Analyzing/Data_Integrity_Check.htm）

- 面板入口在 Parameter / Format Selection；检查对象是整个选中文件。
- 输入 Reciprocity、Causality 容差；Do Check；结果打印到文本框并记日志。
- Passivity：原文判据为「所有 S 矩阵特征值 ≤ 1」，报告最大特征值及其频点。Enforce：乘以缩放向量（无源点为 1、非无源点为 1/特征值），相位取幅度的 Hilbert 变换以保持因果。
- Reciprocity：|Snm − Smn| 小于容差；报告首个非互易参数对与频点。Enforce：非互易点令两者相等。
- Causality：Kramers-Kronig（实部 Hilbert 变换对比虚部）；报告 maxRelErr、maxAbsErr 与所在参数。Enforce：ADS 专有算法（4 阶多项式把实部外推到 Nyquist 再求虚部）。
- Enforcement：勾选要修正的项、指定输出文件、Apply；Reset 清空结果并恢复默认容差。

## 4.9 Templates（Analyzing/Templates.htm）

- Template 保存 marker、方程、刻度、plot 名、limit / eye mask 等全部分析设置。
- Data Browser 的 Template View 节点：Create New（当前文件进入 Create New 节点，设好后右键 Save Template As）；点 template 名即用它打开活动文件；右键 Save Template / Save Template As / Export Template；Template View 右键 Import Template（同名提示覆盖）。
- 修改 template 后，已用它打开的其他 view 不自动更新。
- 内置样例 template，含 COM template、MiniSAS（32p）template。
- Multi-Data Template：
  - 指定文件夹，其中全部 `.dut` / `.snp` / `.cti` 一起打开。
  - Create 对话框：显示方式（每参数一个 plot 汇总所有文件 / 每个文件每个参数各一个 plot）、文件类型、参数左右列表（按域过滤）、Set as Default。
  - Load 对话框：已建 template 只能换文件夹与文件类型，不能改参数。

## 4.10 时域（Analyzing/Analyzing_Data_in_the_Time_Domain.html）

Time Domain Settings 对话框（Tools → Time Domain Settings）：

- Windowing 页：
  - Window Type：Exponential（原 PLTS 窗）、Kaiser（β）、Gaussian、Chebyshev（r）、Hanning、Hamming、Blackman。
  - Window Mode：Lowpass（默认；Impulse 与 Step；Step 需可外推到 DC）/ Bandpass（仅 Impulse；可在偏好中设为默认）。
  - Window Bandwidth：Flat Response（0.80，RTEC 0.91）、Nominal（0.50，RTEC 0.71，默认）、Fast Rise Time（0.20，RTEC 0.54）、Custom（0.20–0.80，或直接给 Step Rise Time / Impulse Width）。Tr = (1000 / Fmax[GHz]) × RTEC（ps）。
  - Kaiser 窗可设比滤波器更慢的上升时间，此时截断部分频率数据并提示。
  - Save As Default；2025 U1 增加 reset。
- Start and Stop Time 页：Auto Optimize On / Off（默认值可在偏好设）；Manual 模式按参数设起止时间（参数在 Available / Selected 列表间移动，含 Diff TDR / SE TDR / Diff TDT / SE TDT 批量按钮），改动即时生效。自动起止算法依据 SDD21 峰值位置。
- DC Point 页：Auto（线性外推）、Auto Using PNA method（圆外推，适合回损 ≤ −30 dB）、Auto Using ENA-TDR method、Manual（每个反射参数输入线性值或电阻 Ω）。
- 含 DC 值的数据变换时自动去除 DC 点（PLTS 2021 起）。

右键 Measure：

- Step Rise Time：单条 trace 或全部 trace 最大值；可设限值给出 PASS / FAIL；10–90% 或 20–80%（偏好）。
- Skew：两条 trace 或全部 trace 中最大值；参考为幅度百分比或绝对电压；可设限值 PASS / FAIL；符号相对第一条 trace；基于 Step 响应。
- Excess Inductance / Capacitance：两个可拖 marker，可拖的读数标签。
- Total Inductance & Capacitance：须为 Impedance 格式；正幅值报 nH，负幅值报 fF。

其他：

- Flatten Slope（TC9）：右键，自动出现两个可拖 marker，之间的阻抗斜率被拉平。
- Trace Align（deskew）：选 trace、原 marker、目标 marker，Apply / Undo。
- Correct Impedance Profile（Tools 菜单开关）：修正多次反射，时域反射 plot 右上角显示黄色图标（即偏好中的「Peeling」）。
- 数据变更图标：Resampled、Interpolated、Bad Data（谐波相关点少于 10 个）。
- 有效性校验：频域 → 时域 → 频域往返比较。
- 分辨率说明：响应分辨率约 1.25 / BW。
- 偏好：反射参数按单程时间 / 距离显示（带图标）。

## 4.11 眼图（Analyzing/Analyzing_Data_using_Eye_Diagrams.html、Eye_Diagram_Bit_Patterns.htm、Eye_Diagram_Mask_Test.htm）

- 构造：时域冲激响应与合成码型卷积；只显示传输参数。
- PAM2（NRZ）/ PAM4；2026 起 PAM3 / PAM6 / PAM8；统计眼图（2025）。
- 首次打开时弹出 Choose Bit Pattern；纵轴可用 Scaling Toolbar 缩放（右键 Reset）。
- 眼图 marker：X、Y 两条十字线，只能用 Marker Bar 滑块移动。
- Parameter Measurement Result 面板：重新测量、Color Grade（密度着色）、各测量项直方图（Amplitude / Height / Width / Jitter / Rise / Fall，PAM4 无）、Configure Eye Measurements、Export Eye Measurement Result（`.csv`）。
- PAM2 结果：Level Zero / One / Mean、Amplitude、Height（mV、dB）、Width、Opening Factor、SNR、Duty Cycle Distortion（时间与 %）、Rise Time（20–80）、Fall Time（80–20）、Jitter（PP、RMS）。
- PAM4 结果：Level 0–3 及其 RMS / Peak-Peak / Skew，Eye 0/1、1/2、2/3 的 Level / Skew / Height / Width，Linearity（RLM），RN 0–3 RMS，TJ RMS。
- Configure：PAM2 的 Sample Window Boundaries；偏好（禁用 3σ buffer、计算完成前不刷新、按实测幅度缩放比例 mask）；PAM4 的 Receiver Sample Timing、Eye Center Location、Eye Level Width（1–25%）、Time of Level、Time Units（s / UI）、Amplitude Units。
- Bit Pattern（Tools → Bit Pattern）：
  - Apply：ABS、K28.5、PRBS（2^5−1 至 2^23−1；2026 U1 加 PRBS31 与自定义种子）、Statistical、用户码型；Data Rate、Rise / Fall Time、Pattern Length、S.E. Amplitude High / Low（差分眼图加倍）、Bit-by-bit（PRBS 自定位数）。
  - Import：DUAL / HEX `.txt`、`.bin`、`.ptrn`、`.dat`、`.ptn`（≤ 64 KB），设名称与默认速率、上升时间。
  - Design：8–32 位钢琴键编辑器、进制显示、保存。
- Eye Mask：
  - Plot Toolbar 一键开关 mask 与 PASS / FAIL；Meas 面板累计采样数与失败数；落入失败区的点标红。
  - Limit Mask Definition 面板（`.xml` / DCA `.msk`）：Create / Import / Delete / Save / Apply；Scaling（Position、Delta T、Logic 0 / 1 Level）；Tolerance（Jitter ΔT、Slope ΔT、One Y1、Zero Y2、Eye Height）。
  - FlexDCA `.mskx`（NRZ 与 PAM4）模式：Delta T、水平 / 垂直对齐自动或手动、Mask Test Margins（−100% 至 +100%）。
  - Define Eye Mask 对话框（Tools）：按比例或按时间 / 电压定义；Top / Middle（4 或 6 顶点，可水平对称）/ Bottom 区；按比例或按时间电压保存 `.xml`。
  - mask 只能经 Limit Mask 面板 Import 应用；导入后自动对齐到首个过零点。
  - 自带 FlexDCA mask 库；2026 U1 加 PAM-N mask 定义。

## 4.12 多通道仿真、AMI、方程眼图（Analyzing/Multi-channel_Simulation.htm、About_AMI.htm、Synthesize_Eye_Diagram_from_Equations.htm、PreDeEmphasisExample.htm）

- Multi-channel Simulation 对话框（Tools）：把 TX、RX、XT TX、Diff Tx/Rx AMI 组件拖到端口槽，右键 Edit / Delete；Draw Eye（至少一个 TX + 一个 RX；结果 plot 追加到当前眼图 window）。
- 配置随 DUT 配置匹配；Add / Delete / Rename / Save（可多选）/ Load。
- TX / XT TX 设置：
  - Show：在各节点额外画只含该效应的眼图。
  - Bit Pattern：XT 相对 TX 的相位、Same as TX；Symbol Rate（GBd）；Pattern Format NRZ / PAM3 / PAM4 / PAM6 / PAM8；PAMn 发送滤波（Bessel4 / Butterworth1–4 + 带宽）；Pattern Length、Loop Count、Rise / Fall、幅度、Samples per bit。
  - Jitter：NRZ 为 RJ（σ）、多分量正弦 PJ（幅度 / 频率 / 相位）、Dirac（延迟 / 概率）；PAM4 为 RJ、F/2 jitter。
  - AWGN：Symbol SNR（NRZ）或噪声电平 mV / µV / nV（PAM4）。
  - Emphasis：None、Pre-emphasis dB、De-emphasis dB（自动 2-tap FIR）、FIR taps、M-script。
- RX 均衡：No Equalization、CTLE（2026 新界面；Legacy 为 2 / 3 极点、DC 增益、零极点频率，可存 preset）、FFE（Optimized 指定 tap 数 / tap 文件 / 手动编辑）、DFE（自动 tap 数或手动 tap 值，Advanced 设 tap 上下限）、CTLE ⇒ DFE、FFE ⇒ DFE、M-script、Customized Assembly（自定义 CTLE / FFE / DFE 顺序，`.xml` 导入导出）；Show RX signal before equalization；`.tap` 文件输入输出。
- IBIS-AMI：加载 `.ibs`（自动带 `.ami` 与 DLL）、View、Corner（Typ / Min / Max）、参数树编辑（Reserved / Model_Specific，In / InOut 可改）、RX 可显示输入波形。仅支持 IBIS 5.1 兼容模型与 bit-by-bit 模式，不支持统计模式。
- 查看增强码型波形（眼图 / 波形切换按钮）。
- Equation Eye Diagram（Tools）：以 PLTS 或 MATLAB 方程结果为数据源，同样配置 TX / RX 后 Draw Eye。
- 计算依赖 MATLAB runtime。

## 4.13 COM / JCOM（Analyzing/Channel_Operating_Margin_(COM).htm）

- Tools → Channel Operating Margin：COM 版本 1.54 / 1.65 / 2.28 / 3.70（2026 U1 加 4.14.0）或 JCOM。
- Remove DC point；MATLAB 配置（exe 路径、编译 DLL 或 `.m` 文件、测试后关闭命令窗、隐藏图窗）。
- 参数配置：COM 选 IEEE Excel config 文件；JCOM 选文件或手填参数；ONLY S4P ERL / ONLY S2P ERL。
- THRU / FEXT / NEXT 端口槽拖放 TX / RX / XT TX；支持通用端口配置。
- Run 后显示 COM 值与 PASS / FAIL；More 显示明细（IL fit 参数、阻抗 trace、状态参数、RX 滤波 tap、增益、ERL、PTDR）；JCOM 分 case 查看。
- Add to Text Box / Configure Text Box；New Plot / New Trace / Remove Trace 绘出中间结果；Manager 把 COM 输出的 `.txt` 映射为 trace（FrequencyMHz / TimeNs，Trace / List）。
- 存为 template 后打开新 DUT 自动重跑；运行时界面不阻塞。

## 4.14 RLCG（Analyzing/Analyzing_Transmission_Line_Parameters.html）

- 仅适用于对称耦合差分线（4 端口、均匀、无不连续）；导入 2 端口文件选 RLCG 会报错；为选件功能。
- 四种分析类型及参数：
  - W-Element：R11、L11、C11、G11、R12、L12、C12、G12
  - Differential：Rd、Ld、Cd、Gd、Zor、Zoi、Ad（衰减常数）、Bd（相位常数）
  - Common：Rc、Lc、Cc、Gc、Zor、Zoi、Ac、Bc
  - Self/Mutual：Rs、Ls、Cs、Gs、Rm、Lm、Cm、Gm
- 拟合模型：R = R0 + Rs·√f，L、C 为常数（提取值平均），G = G0 + GD·f。
- T-Line Characteristics 对话框（选 RLCG 参数时弹出，也可从 Tools 打开）：线长（m）、Highest Extracted Frequency（MHz，默认测量上限的 90%）。
- W-Element 每个 plot 默认两条 trace：Extracted（蓝）+ Fitted（红）；Tools → W-Element Display Configuration 可改为 Extracted + Smoothed，按参数设平滑点数（奇数），Apply 实时预览。
- 传播常数与特性阻抗可用 Mag / Phase、dB / Phase、线性或对数频率显示。

# 5. File and Print Operations

## 5.1 文件类型与打开保存（FilePrint/File_Save_and_Open.htm）

- `.dsta` State 文件：保存当前全部设置，之后回调（不含 RLCG、Gating、原始校准数据）。
- `.dut`：测量数据 + 计算得到的时域与平衡模式数据 + 测量与校准信息；也保存方程、参考面调整状态、System Z0。
- `.fml` 方程、`.txs` 适配器、`.dcf` DUT 配置；`.cal` / `.tdr` / `.wzd` / `.mkt` 与校准相关 `[仪器]`。
- Save / Save As；同一时间只允许一个未保存的 plot window。
- File → Open 可多选；Recent Files 显示最近 4 个；Data Browser 右键 Close File；File → Close All Files；退出时 Apply for All 批量处理未保存文件。

## 5.2 导入（FilePrint/Importing_Data.htm、Batched_File_Open_Import.htm）

- 不支持功率扫描数据；Rev 4.0 起端口数不限。
- 支持导入时域文本数据与 DCA XY Verbose 波形（`.txt` / `.csv`）；导入时域数据时需给 FFT 用的 Stop Frequency（默认 20 GHz）。
- 只有平衡参数的数据可导入并反算单端参数（数据不足时提示）。
- Touchstone 2.0 / CITIfile 端口阻抗不一致时拒绝导入（AFR 与去嵌功能除外）。
- Import a Single File：Data Domain（Frequency / Time）、File Type（Citifile、Touchstone、Text tab、Text comma）、Browse、DUT Configuration Change（2026 起含 Quick Topologies）、Limit Data Range（All / Subset：Start、Stop、Points、Step（仅线性）、Interpolate（需要时自动勾选）、Reset）。
- Import Multiple Files（Build a File）：多个文件拼成一个 DUT 文件；映射方式 Individual parameters 或 Ports；映射类型 Single-Ended、Differential、Single-Ended to Differential；网格全部填满才能 OK；Subset；Export；2026 加 Yes to All / No to All。
- Build with a Configuration File：`.csv` 描述各源文件与端口（绝对或相对路径），Export 为 `.snp`。
- Batched File Open / Import：Data Domain；按类型添加文件（`.dut` 为 Open，`.sNp` / `.cti` / `.cit` / `.txt` / `.csv` 为 Import）；要求相同 DUT 配置；Subset + Interpolate；2025 U1 可自动叠加到同一 plot；2026 可按文件属性排序。

## 5.3 导出（FilePrint/Export_Data.html、Text_Files.htm、SnP_File_Format.htm、CITIfile_Format.htm、RLCG_Data_Formats.htm、TDA_MeasureXtractor.htm）

- plot 右键 Save Traces As：plot 内全部 trace 存为 `.csv`。
- File → Export 对话框（按编号顺序填写，后项依赖前项）：
  - Export Data from File、Data Domain（Frequency / Time / RLCG / Plots / Math，另有 Mixed Mode）、File Type、Format、DUT Configuration、Data to Export、Independent Units、Limit Data Range（Subset：Start / Stop / Points / Step，Spacing Linear / Log / Dec / Oct，Interpolate，Reset）、输出路径（多文件时自动命名）。
  - Apply（不关闭）/ Export（关闭）。
  - 去嵌或 AFR 后导出的文件头加 `!Deembedding/AFR applied`。
- 频域：CitiFile（RI）、Touchstone（MA / DB / RI）、TDA MeasureXtractor（dB / angle，4 端口 sNp）、Cadence Allegro PCB SI 630（dB / angle sNp）、Text tab / comma（RI、Log Mag、Linear、Phase、Unwrapped Phase、Group Delay、VSWR、Z Real、Z Imag）；单位 MHz / GHz。
- 时域：Text tab / comma、Touchstone；Step / Impulse × Real / Volts / Log Mag，以及 Step Impedance；单位 ns。
- RLCG：HSPICE W-Element（4 端口 Fitted）、HSPICE W-Element Tabular（Extracted / Smoothed）、ADS MDIF（Extracted / Smoothed / Differential / Common；自耦与互耦分两个文件）、ADS ML2CTL（Fitted；C / ε0、L / μ0、Rs / √GHz）。Tabular / MDIF 支持 Subset（含 Log / Dec / Oct）。
- Plots：图片到剪贴板或 `.bmp` / `.jpg` / `.tga`，分辨率可选（默认 1920×1080，另有 1280×720）。
- Math：方程 trace 导出为 Text tab / comma。
- Select Measurement Parameters（Advanced，文本 / CITI / 时域）：Export Gated Parameters、Export All Data in One File（否则每个参数一个文件，文件名加参数后缀）。
- Advanced Data Selection（Touchstone / TDA / Allegro）：导出端口重映射表、Export Gated Parameters、Export Smoothed Parameters、Export DC Values。
- 偏好：导出 Touchstone 时写入端口号与端口标签注释（如 `!1:<<<<<<`）。
- 文本文件头：`! NAME`、`! DATA`、`! RESPONSE`、`! XDATA UNIT`、`! YDATA UNIT`、`BEGIN`、`%` 列说明。
- Touchstone：支持 1.0 与 2.0（`.ts`，含混合模式）；时域 Touchstone 以时间为横轴；原文称每文件最多 16,000 个数据点。
- CITIfile：可含多个 package；标准 package 名 RAW_DATA / DATA / FORMATTED / MEMORY。

## 5.4 批处理与合并（FilePrint/Merge_Data_Files.htm、BatchFileConverter.htm）

- Merge Manager（File 菜单）：两个频段不同、参数相同的文件（类型可不同）合并为 Touchstone / Text / CITIfile；默认取最小起点、最大终点、最小步进；可 Subset；间隙与步进不同处插值；重叠频段取平均。
- Batched File Converter（File 菜单）：不打开文件即批量转换；支持频域 ↔ 时域（给 FFT Stop Frequency）；文件须同 DUT 配置、同域；Add / Remove / 文件计数；Time Domain Settings（2026）；DUT Configuration；输出类型与格式同 Export；Advanced 参数选择、端口重映射、gated、DC 值；Subset / Spacing / Interpolate；输出目录自动命名；多线程。

## 5.5 报告与打印（ToolsAndUtilities/Characterization_Report_Generator.htm、Customizing_a_Characterization_Report.htm、Printing.htm）

- Characterization Report（File 菜单）：Report Header 项（标题、页眉页脚、公司、DUT 名等）、Report Content 项（仪器配置、校准与测量信息）、Plots From Current View / From View Template、Plot Size、输出 `.html` / `.pdf` / `.doc`。
- 自定义报告（PLTS 2016 起）：以 Word 文档为模板，用内容控件 + PLTS 标签映射数据；标签覆盖用户输入信息、版本、仪器与测量设置、DUT 配置、view 名、plot 名与图片、X 轴范围 / 单位 / 分辨率 / 点数、眼图码型信息、marker 表与单个 marker 值、limit / mask 测试结果、skew 结果、trace 数据表。
- Print Setup / Print Preview（单双页、缩放；第二页列出已打开 DUT 文件）/ Print（活动 plot window，可打印到文件）。

# 6. Tools and Utilities

## 6.1 菜单总览（ToolsAndUtilities/Using_Analysis_Tools_and_Utilities.html）

- Tools：Math、Collaborate with MATLAB、Collaborate with Python、Bit Pattern、Define Eye Mask、Multi-channel Simulation、Equation Eye Diagram、T-Line Characteristics、W-Element Display Configuration、Velocity Factor、Time Domain Settings、Correct Impedance Profile、Improved TDR Cal Correction `[仪器]`、User Preferences、License Preferences、Channel Loss Compensation、Channel Operating Margin。
- Utilities：Characterize Adapters `[仪器]`、Edit Cal Kits `[仪器]`、Reference Plane Adjustment、Batched Reference Plane Adjustment、N-port Reference Plane Adjustment、Gating、Auto Fixture Removal、Delta-L、PCB Material Characterization、Continuity Check `[仪器]`、System Z0。
- Run：Run Macro。
- 独立工具：File Converter（`.dut` / `.cit` / `.s2p` → `.txs` 适配器文件）、Multi-Version Launcher。

## 6.2 User Preferences（ToolsAndUtilities/User_Preferences.htm）

- General：反射参数按单程时间 / 距离显示；插值 / Correct Impedance Profile / 单程图标显示开关；跳过硬件搜索 `[仪器]`；时域默认 Band Pass；20–80% 上升时间；内存阈值告警与内存用量监视器；方程歧义自动解析；Python 输出窗与解释器路径；多套偏好文件保存 / 切换；Factory Reset。
- Wizard Defaults、Measurement 中的测量项 `[仪器]`；Measurement 中与分析相关的：总是优化时域起止、Improved FFT extrapolation（起始频率大于步进时按步进外推到 DC）、眼图 3σ buffer、按实测幅度缩放 mask、Improved Precision of De-embedding、Run AFR in Offline Mode。
- Load/Save：打开 `.dut` 时重算时域 / S 参数；导出 Touchstone 写入端口号与标签。
- File Storage：各类文件默认目录；自动保存与文件名前缀。
- Plot：trace 颜色 / 线型 / 线宽（全局，按 trace 序号）；新建 plot 自动 Autoscale；注释限制在绘图区；Delta Marker；频域 Log X 轴；PASS / FAIL 文字与字号；眼图计算完成前不刷新；轴字号；Add All Legends（文件名或全路径）；单点 legend；marker 有效位 1–10；X / Y 轴小数位；每 window 最多 plot 数（16–144）。

## 6.3 System Z0 与 Velocity Factor（ToolsAndUtilities/System_Impedance.htm、Velocity_Factor.htm）

- System Z0：所有端口同一值；只改变时域 plot 的显示，不影响其他格式；随 `.sNp` 与 `.dut` 保存，导入的 `.sNp` 自带值优先；在状态栏与 DUT Files 面板显示。
- Enable Arbitrary Mixed Mode Impedance Conversion：每个平衡端口单独设差模阻抗（默认 Z1 + Z2）与共模阻抗（默认 Z1·Z2 / (Z1 + Z2)）。
- Velocity Factor 对话框：输入 Vf，或输入 εr 换算。

## 6.4 Gating（ToolsAndUtilities/Gating.htm）

- Utilities → Gating（Single-Ended / Balanced）。
- Gating window：左时域、右频域并排；频域红为原始、蓝为 gate 后；时域红段被 gate 掉、蓝段保留；一次只看一个参数；该 window 不能保存；两侧均可右键 Autoscale / Reset Scale。
- Gating 对话框（可浮动 / 停靠）：Start / Stop（滑块移动 M1 / M2 竖线）、Gating Mode（Bandpass / Notch）、Gating applies to（This Parameter Only / All Reflection Parameters，仅反射参数可选）、Add、Apply（覆盖当前 gate）、Move（整体平移）、Delete。
- 最多 10 个 gate，按从左到右重新编号。
- 被 gate 掉的区段以同电延迟的理想传输线代替。
- 可导出 gate 后的频域数据；2026 U1 增加 Impedance-Preserving Gating。

## 6.5 参考面调整（ToolsAndUtilities/Removing_Unwanted_Effects_from_the_Measurement.html、Reference_Plane_Adjustment.htm、Batched_and_Nport_Ref_Plane_Adj.htm）

- Reference Plane Adjustment（4 端口）：2-port De-embedding（`.txs` / `.s2p`）与 4-port De-embedding（`.s4p` / `.cit` / `.dut`）二选一、Port Rotation / Extension（mm，±50000，同时显示 ps）、Port Reference Impedance（0–1000 Ω，每端口可不同）；按端口分配，编号列表显示（1. 去嵌 / 2. 旋转 / 3. 阻抗），逐条移除、Clear；Reverse de-embed orientation；4 端口去嵌成对分配（SOLT 为 1-3 / 2-4，TRL / LRM / TDR 为 1-2 / 3-4）；Apply / Remove（还原）/ Close；状态保存在 `.dut`，状态栏 De-Embedding / Port Rotation 指示灯亮。
- N-port Reference Plane Adjustment（活动文件，≤ 64 端口）：
  - De-embedding / Embedding（`.sNp` / `.cit` / `.dut`）、Insertion Loss Only（回损与串扰置理想）、Reverse（镜像端口）、3 端口单端转差分器件。
  - 选起始端口后按隔行分配（6 端口文件从端口 2 起作用于 2、4、6）；文件端口多于 DUT 端口时报错。
  - Port Rotation / Extension、Port Reference Impedance（逐端口）、Diff/Com Port Reference Impedance（按差分端口 Dx / Cx 设阻抗，单端参数由混合模式反算）。
  - Add / Remove Specified Adjustment、Remove All、Apply、Close；File → Save 写入 `.dut`。
- Batched Reference Plane Adjustment：任意数量文件；输出类型 DUT / CITI / Touchstone 1.0 / 2.0 / TDA / Allegro / Text tab / comma 及对应格式；单端或差分输出；文件名后缀；输出目录或与输入同目录；多线程；若各端口阻抗相同，变换后 System Z0 设为该值。

## 6.6 Delta-L（ToolsAndUtilities/Delta-L.htm）

- Delta-L+ 4.0（IPC-TM-650 2.5.5.14），1L / 2L / 3L 三种方法。
- 输入 `.s4p`（可从已打开文件中选：Available / Selected 列表）、Port Order、Trace Length（ft / in / mm）；2L / 3L 有 Enhance Mode 与 Iteration Point（平滑）；Calculate。
- 输入后在 template view 预览 SDD21。
- 结果：1L 为单位长度插损的均值与标准差；2L / 3L 为 Eigen Value、Curve Fitted、Uncertainty。

## 6.7 Channel Loss Compensation（ToolsAndUtilities/Channel_Loss_Compensation.htm）

- 补偿传输线损耗与色散，使 TDR 峰更尖锐以定位不连续。
- Target Data File；Use Reference Thru Data（Load）或由 DUT 估计；Device Length；Velocity Factor 估计或给定；New Plot / New Trace；Draw。

## 6.8 PCB Material Characterization（ToolsAndUtilities/PCB_Material_Characterization.htm）

- 选件 N19308B。2D stripline 仿真 + Svensson-Djordjevic 介质模型 + Huray / Cannonball 粗糙度模型（或光滑导体），调参至仿真与测量吻合后提取 Dk、Df、SR。
- 面板：Trace Type（单端 / 差分 stripline）、Calculated From（2-Line：长短线去嵌 / DUT）、文件路径、Port Order、Truncation Frequency、DUT Length、Use PCB Stack-Up（Wt、Wb、Etch Factor、T、S、Ht、Hb、Conductivity；不用时只得粗略 Dk / Df、无 SR）、Calculate。
- Advanced：SD 模型 Low / High / Reference Frequency；Huray 球半径、面积、球数（可用户指定）；Cannonball（固定 14 球）；Export 到 CSV；显示仿真 S 参数；设置存取 `.xml`。
- 结果：参考频率下 Dk / Df 与粗糙度参数摘要，仿真与实测 SDD21（S21）叠加、Dk 与 Df 随频率曲线。

## 6.9 Run Macro（ToolsAndUtilities/Run_Macro.htm）

- Run → Run...：运行 MATLAB、Python、`.exe`、`.bat`，或 `.txt` SCPI 命令列表（首行 `#` + VISA 地址）。
- Save 后出现在 Run 菜单；Remove / Modify 页改名或删除。

# 7. 帮助其他章节中与分析相关的条目

未逐页核对，仅记录从本清单范围内页面链接到、或版本说明中出现的分析侧能力：

- Auto Fixture Removal（AFR）及 Batch AFR（VNACalAndMeas 章节）。
- iRL / iRLN（Integrated Return Loss / Noise）测试（2024 版本说明）。
- Segment sweep（2025 U1）`[仪器]`。
- 统计眼图（2025）。

# 8. 与现有设计冲突、需决策的点

1. **Data Browser 层级**：`DOMAIN_MODEL.md` §9 与 `UI_DESIGN.md` §6 以 Group → Measurement → DataFile 「对标 PLTS」，并有「待确认」注。原文中 Data Browser 顶层是预置、不可增删的分析类型（§3.4）以及 Template View / Multi-data 节点，其下是已打开的 window（以 `.dut` 文件标识）。即「预置分类」这一假设成立，但分类维度是**分析类型**，不是用户自建的 Group / Measurement。
2. **Per-port 参考阻抗**：PLTS 的 Port Reference Impedance 允许每个端口不同，Diff/Com Port Reference Impedance 允许每个差分端口独立设阻抗；`DOMAIN_MODEL.md` §5 的 `Network.z0` 是单标量。若要对标这两项，需要新的领域类型（§5 已预留「通过新的领域模型扩展」）。
3. **System Z0 语义**：PLTS 的 System Z0 只改变时域显示，是「显示设置」而非对数据做 renormalization；我们的 Renormalization 需与之区分。
4. **CSV 导出**：`PRODUCT.md` 把「CSV / MATLAB 导出」列为待决策，但 PLTS 的 Text（comma delimited）导出、Save Traces As、marker 导出都是 CSV。
5. **Passivity 判据**：原文写「所有 S 矩阵特征值 ≤ 1」；`ALGORITHM_GUIDE.md` 用奇异值 ≤ 1（严格的无源判据）。两者对非正规矩阵结果不同，与 PLTS 做 golden 对比时需注意。
6. **Causality Enforcement**：PLTS 使用 ADS 专有算法，按 `PRODUCT.md` 原则 6 不能复制，只能自选公开方法，数值不会与 PLTS 一致。
7. **上升时间默认值**：PLTS 时域上升时间默认 10–90%，偏好可改为 20–80%（眼图结果固定报 20–80%）；`ALGORITHM_GUIDE.md` 以 20–80% 为默认。与 PLTS 对比时需显式对齐百分比。
