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

波量定义：`<TODO: power-wave / pseudo-wave / other>`

测试覆盖：

- 50 → 75 Ω
- 75 → 50 Ω
- unequal port impedance
- round trip

# 12. Mixed Mode

定义 pair、polarity、normalization、matrix transform。

测试：pure differential / pure common / mode conversion / round trip。

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
