# ALGORITHM_GUIDE.md

# 1. Purpose

定义 Interconnect Studio 的公共算法工程规范。具体算法公式应放到 `docs/algorithms/`。

# 2. Every Algorithm Must Define

1. Input
2. Output
3. Units
4. Array shape
5. Mathematical convention
6. Reference
7. Tolerance / metrics
8. Edge cases

# 2.5 Touchstone Data Ordering

Touchstone 1.x 的矩阵排列**因端口数而异**，是已知的易错点：

```text
1 端口：  freq  S11
2 端口：  freq  S11 S21 S12 S22          ← 列主序，是特例
≥3 端口： freq  S11 S12 S13 ...          ← 行主序，每行一个矩阵行
                S21 S22 S23 ...
                S31 S32 S33 ...
```

- **2 端口是唯一的列主序特例**，≥3 端口一律行主序。
- 把 2 端口规则套用到 4 端口会导致整个 S 矩阵转置。互易无源件 `S = Sᵀ`，该错误不可见；在 mode conversion、串扰与非互易器件上则是静默错误。
- 读写使用同一套错误约定时 round-trip 测试仍会通过，因此**必须用非对称矩阵的 fixture 验证**，且 fixture 的数值排列要独立于实现推导。

Touchstone 2.0 使用显式的 `[Network Data]` 段，≥3 端口为行主序；**2 端口的顺序由必填关键字 `[Two-Port Data Order]` 显式给出**：`12_21` 为行主序（S11 S12 S21 S22），`21_12` 与 1.x 相同（S11 S21 S12 S22）。`[Matrix Format] Lower / Upper` 只存下 / 上三角（行主序），读入时按对称补全。

# 2.6 Import

对标 PLTS *Importing Data* 的频域部分（`io/`、`algorithms/network/subset.py`、`algorithms/network/build.py`）。

**不重采样（产品决策）**：导入与多文件拼接都不改变频点，不做插值。

- Subset 只按 `[start_hz, stop_hz]` 保留测量点（闭区间），不能超出测量范围，至少保留一个点；Points / Step 仅显示、不可编辑，Interpolate 恒为关闭。
- 多文件拼接要求所有源文件频点一致（相对容差 `1e-9`）且 `z0` 相同，否则报错，而不是插值对齐。

多文件拼接（Build）语义：

- 每个 DUT 参数 `S[i, j]` 取自某一源文件的某一参数；按端口映射时，把文件端口 `(k, l)` 映到 DUT 端口 `(i, j)`，覆盖**两端都来自该文件**的所有参数对。
- 后做的映射覆盖先做的（PLTS：可改写）；所有 DUT 参数都有来源才能完成拼接。
- Build config CSV：首行 `folder,<路径>`（可相对配置文件）；其余每行 `序号, 文件名, [源端口], [目标端口]`，端口 1-based、按顺序配对。

文件格式约定：

- CITIfile：只读 `DATA S[i,j] RI` 数组（CITIfile 定义只有 RI），频率来自 `VAR_LIST` 或单段 `SEG_LIST`；格式无参考阻抗字段，**按 50 Ω 处理（假设，待与实际 PLTS / PNA 导出文件核对）**。多 package 文件拒绝。
- 文本（tab / 逗号）：PLTS 帮助只给出时域文本的格式，频域格式按其导出约定自定：`!` 注释，`! XDATA UNIT <单位>`（缺省 Hz），`BEGIN` / `END` 忽略；表头一行（可带 `%`），首列 `freq` / `freq(GHz)`，其余列为 `S21(real)`、`S21(imag)`（≥10 端口写 `S[12,3](real)`），列序任意但矩阵须完整；参考阻抗由调用方给定（默认 50 Ω）。
- Touchstone 2.0 混合模式数据（`[Mixed-Mode Order]`）暂不支持，待 Mixed-Mode 模块落地。

# 3. Precision

默认：

- `float64`
- `complex128`

# 4. Frequency Grid

每个算法必须明确：

- monotonic?
- uniform spacing?
- DC required?
- start frequency > 0?
- harmonic grid?

禁止隐藏 interpolation / extrapolation。

# 5. Interpolation

明确：

- complex interpolation method
- phase unwrap policy
- extrapolation policy

禁止对 wrapped phase 直接线性插值。

# 6. DC Extrapolation

候选：

- NONE
- LINEAR
- PNA_COMPATIBLE
- CUSTOM

每种方法单独测试。

# 7. Window

候选：Kaiser / Hann / Hamming / Rectangular / `<TODO>`。

必须定义参数、normalization 与使用位置。

# 8. Time Domain

区分：

- Low Pass Impulse
- Low Pass Step
- Band Pass Impulse

每种方法明确频谱构造、DC、FFT/IFFT convention、normalization、time axis。

## Rise Time

上升时间定义取 **20–80%** 为默认，同时支持 10–90%。

- 两种定义算出的结果差异显著，必须作为显式枚举参数传入，不得隐含。
- 结果 metadata 必须记录实际使用的定义。

# 9. TDR / Impedance

基础关系：

```text
Z = Z0 * (1 + rho) / (1 - rho)
```

必须定义 rho 来源、step normalization、singularity handling、complex/real policy。

# 10. Gating

定义：

- Gate type
- Start / Stop
- Window
- Transition
- Compensation
- Frequency reconstruction

Regression 至少关注 ripple、phase、pass/reject region。

# 11. Renormalization

波量定义：**pseudo wave / traveling wave**（Marks & Williams）。

```text
Gamma = (Z_L - Z0) / (Z_L + Z0)
Z_L   = Z0 * (1 + Gamma) / (1 - Gamma)
```

选择理由：

- 与已实现的 `format_s_parameter` 阻抗换算式一致（见本文 §9 与 S-Parameter Display Formats）。
- 复数特征阻抗场景（有损夹具、AFR `fixture_z0`）下是计量领域的标准选择。
- 实数 `z0` 下与 power wave 完全等价，因此不影响与 PLTS / PNA 的 50 Ω golden 对比。

实现约定：

- 波量定义作为显式枚举参数 `s_def` 暴露，默认 `PSEUDO`；后续可扩展 `POWER` 而不构成破坏性变更。
- power wave（Kurokawa）在复数 `z0` 下的对应式为 `Z_L = (Z0* + Gamma * Z0) / (1 - Gamma)`，两者仅在复数 `z0` 下不同。
- scikit-rf 默认 `s_def='power'`。复数 `z0` 下交叉对拍时必须显式传 `s_def='pseudo'`。

测试覆盖：

- 50 → 75 Ω
- 75 → 50 Ω
- 复数 `z0`（区分 pseudo 与 power 的唯一场景）
- round trip

注：`Network` 为单标量 `z0`（见 `DOMAIN_MODEL.md` §5），不存在 unequal port impedance 场景。

# 12. Mixed Mode

pair / polarity / ordering / normalization 的约定见 `DOMAIN_MODEL.md` §7，此处不重复定义。

要点：

- 配对由调用方显式传入，算法层不设默认值。
- 输出为 `MixedModeNetwork`，不是 `Network`（差分与共模参考阻抗不同）。
- 归一化使用 1/√2 功率不变变换。

测试：pure differential / pure common / mode conversion / round trip；三种四端口拓扑各覆盖一次。

解析基准为两条理想无耦合传输线：等长时无模式转换；不等长时 `Sdd21 = (ta+tb)/2`、`Scd21 = (ta-tb)/2`——后者正是钉住 1/√2 归一化与分块顺序的用例。

理想线只验证代数。物理形状的回归基准放在 `golden_data/mixed_mode/`：一对有损、有色散、偶奇模速度不同的耦合线（Case001 对称，Case002 带 2 ps 线内偏斜）。输入由四端口开路阻抗矩阵算出，参考由偶模 / 奇模二端口闭式解给出，**不经过被测变换**：

```text
Sdd11 = S11(z_odd,  theta_odd,  z0)      Sdd21 = S21(z_odd,  theta_odd,  z0)
Scc11 = S11(z_even, theta_even, z0)      Scc21 = S21(z_even, theta_even, z0)
```

差分模即奇模：电压 `2*v_odd`、电流 `i_odd`，故特征阻抗 `2*z_odd`、参考 `2*z0`，与单端比值相同。生成脚本 `scripts/generate_golden_mixed_mode.py` 保存完整推导。

## 显示与参考阻抗

混合模式参数复用单端路径的 `format_coefficient`，两者不会各自漂移。差别只在参考阻抗：

- 差分端口用 `2 * z0`，共模端口用 `z0 / 2`。
- **仅同模式同端口（SDD_ii、SCC_ii）算反射**，可用 SWR 与阻抗类格式。
- SDC_ii、SCD_ii 虽在同一端口，但关联两个模式，没有单一参考阻抗可言，故不提供阻抗类格式。

# 12.5 Data Quality

检查为只读：**不修改数据、不自动修正、不在 `Network` 上留质量标记**。修正是下面单独的 Enforcement 算法的职责。

```python
check_passivity(network)     # 奇异值 <= 1
check_reciprocity(network)   # S == S.T
check_causality(network)     # Kramers-Kronig / 希尔伯特变换一致性
```

约定：

- 返回量化指标与越界频点列表，由调用方决定如何呈现。
- 每项检查必须明确容差及其依据；测量数据永远不会精确满足这些条件。
- Enforcement（强制无源 / 因果，并可写出修正后的文件）是独立的显式算法：必须返回新对象并在 metadata 标注已修正，不得就地改写原始测量数据。修正方法不唯一，实现前须先定参考实现与容差。

该模块同时是发现自身算法错误的主要工具：去嵌结果出现有源（奇异值 > 1）通常意味着算法或输入有问题。

# 12.6 Crosstalk

基于 `DOMAIN_MODEL.md` §6.5 的 Port Group 模型：

- NEXT / FEXT
- PSNEXT / PSFEXT（功率和）
- ICN（integrated crosstalk noise）
- ICR（integrated crosstalk ratio）

要求：

- ICN / ICR 必须按所引用标准（IEEE 802.3 / OIF-CEI）的确切公式实现，并在 docstring 注明标准与版本。
- 积分区间、加权函数、单位必须显式，不得使用隐含默认值。

# 12.7 SI Metrics

- **Skew**：intra-pair / inter-pair。需明确从相位斜率还是时域峰位提取。
- **传播延迟 / 电长度**：需明确所用定义与介质假设。
- **ILD / ILfit**：按 IEEE 802.3 的拟合衰减与偏差定义；必须记录拟合阶数与频率区间。
- **有效 Dk / Df**：依赖几何参数输入，提取方法不唯一，必须在结果 metadata 记录所用模型假设。

# 13. De-embedding Development Order

```text
Cascade → Decascade → Known Fixture → 2X-Thru → AFR
```

# 14. AFR Module Structure

```text
src/interconnect_studio/algorithms/afr/
├── preprocess.py
├── fixture_length.py
├── fixture_z0.py
├── reflection.py
├── transmission.py
├── fixture_split.py
├── match_correction.py
├── length_correction.py
├── impedance_iteration.py
└── metrics.py
```

禁止形成单个巨型 `afr()`。

# 15. Result Metadata

建议记录：

- algorithm_name
- algorithm_version
- parameters
- reference_z0
- input_hash

# 16. Priority

```text
Correctness → Determinism → Maintainability → Performance
```

性能优化前必须 benchmark。


## S-Parameter Display Formats

Frequency-domain S-parameter format conversion is implemented in:

```python
format_s_parameter(network, response_port, source_port, data_format)
```

Supported formats:

- Log Mag
- Linear Mag
- Phase
- Unwrapped Phase
- Group Delay
- Real
- Imaginary
- Smith
- Polar
- SWR
- Impedance Real
- Impedance Imaginary
- Impedance Magnitude
- Impedance Imaginary Magnitude
- Impedance Angle
- Quality Factor
- Dissipation Factor

Conventions:

- Ports use the internal 0-based response/source convention.
- Log Mag = `20*log10(abs(S))`, in dB.
- Phase is wrapped phase in degrees.
- Unwrapped Phase is continuous phase in degrees.
- Group Delay = `-1/(2*pi) * d(phi)/df`, returned in seconds. Phase is unwrapped first; input frequency sampling must be dense enough to avoid ambiguous phase jumps.
- Smith and Polar retain the complex S-parameter coefficient; the plot layer determines geometry.
- SWR and impedance-derived formats are reflection-only.
- Reflection impedance uses `Z = z0 * (1 + Gamma) / (1 - Gamma)`.
- Quality Factor uses `abs(Im(Z)) / Re(Z)`.
- Dissipation Factor uses `Re(Z) / abs(Im(Z))`.

The format layer performs numerical conversion only and does not own plot scaling or UI rendering.
