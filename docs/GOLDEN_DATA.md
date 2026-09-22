# GOLDEN_DATA.md

# 1. Purpose

Golden Data 用于验证 Interconnect Studio 数值正确性，并支撑 PLTS/PNA/ZNA/理论结果对比与 Agent 自动验收。

# 2. Directory

```text
golden_data/
├── network/
├── mixed_mode/
├── time_domain/
├── gating/
├── deembedding/
├── afr/
└── eye/
```

# 3. Case Structure

```text
Case001/
├── README.md
├── input/
│   └── input.s4p
├── reference/
│   ├── result.npz
│   └── result.s4p
├── config.json
└── metrics.json
```

# 4. README Fields

- Purpose
- Source
- Software / Instrument Version
- Configuration
- Expected Behavior
- Notes

# 5. Reference Types

- ANALYTICAL
- STANDARD
- PLTS
- PNA
- ZNA
- INTERNAL_APPROVED

第三方软件结果是重要 Reference，但不自动等同于数学真值。

# 6. Example Config

```json
{
  "algorithm": "low_pass_step",
  "reference": "PLTS",
  "reference_version": "<VERSION>",
  "parameters": {
    "window": "kaiser",
    "beta": 6.0
  }
}
```

# 7. Metrics

建议至少：

- max_abs_error
- rms_error
- magnitude_error_db
- phase_error_deg
- impedance_error_ohm
- time_error_s

# 8. Approval Rule

Agent 不得自动替换 Golden Data。

```text
New Reference → Human Review → Reason documented → Replace Golden
```

# 9. Large Data

大型数据考虑 Git LFS 或独立数据仓库，最终方案待 ADR 决策。

# 10. Reproducibility

建议保存：input_sha256、reference_sha256、algorithm_version、config。
