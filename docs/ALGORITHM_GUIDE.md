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

测试：pure differential / pure common / mode conversion / round trip；1-3/2-4 与 1-2/3-4 两种配对各覆盖一次。

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
