# Case001 — Symmetric coupled differential pair

## Purpose

钉住混合模式变换在**物理形状的四端口数据**上的正确性，重点是 SDD21。
此前的混合模式测试都用抽象的理想线矩阵；本用例是一条有损、有色散、
偶奇模速度不同的耦合线对，和真实 PCB 差分走线同形。

它同时覆盖整条读入路径（Touchstone 行主序 → 拓扑 → 变换），
所以 Touchstone 排列回归在这里也会失败。

## Source

`ANALYTICAL`。输入与参考都由 `scripts/generate_golden_mixed_mode.py` 生成：

- **输入**：由对称耦合线的四端口开路阻抗矩阵（电路理论）算出，再转 S。
- **参考**：由偶模 / 奇模的二端口闭式解写出，**不经过被测的混合模式变换**。

差分模即奇模：电压 `2*v_odd`、电流 `i_odd`，故为特征阻抗 `2*z_odd`、
参考 `2*z0` 的二端口线；两者比值与单端相同，因此

```text
Sdd11 = S11(z_odd,  theta_odd,  z0)      Sdd21 = S21(z_odd,  theta_odd,  z0)
Scc11 = S11(z_even, theta_even, z0)      Scc21 = S21(z_even, theta_even, z0)
```

对称线对不产生模式转换，故 SCD21 = SDC21 = 0（精确 0，不是小量）。

推导写在生成脚本的模块 docstring 里。

## Software / Instrument Version

不适用：无第三方软件、无仪器。参考为解析解。

## Configuration

见 `config.json`。要点：

| 参数 | 值 |
| --- | --- |
| 长度 | 0.1524 m（6 inch） |
| `z_odd` / `z_even` | 46 Ω / 61 Ω（差分 92 Ω，共模 30.5 Ω） |
| `eps_eff_odd` / `eps_eff_even` | 3.20 / 3.55（微带：奇模更快） |
| 损耗 | `(0.43*sqrt(f_GHz) + 0.136*f_GHz)` Np/m，奇模 ×1.10、偶模 ×0.95 |
| 频率 | 0.1 – 20.0 GHz，0.1 GHz 步进，200 点 |
| `z0` | 50 Ω |
| 拓扑 | `through_1_2_3_4`（PLTS 默认） |

## Expected Behavior

- SDD21 是单调下降的插入损耗：0.1 GHz 约 −0.23 dB，20 GHz 约 −6.8 dB。
- SDD11 在 −27 dB 附近（92 Ω 走线对 100 Ω 参考的失配）。
- SCD21 = SDC21 = 0。
- 单端 S21 在 8–10 GHz 有深谷、FEXT 同时抬升——偶奇模速度不同的典型特征。
  这正是"单端看起来奇怪、差分却干净"的物理原因，也是本用例值得存在的理由。
- Tolerance：`rtol = 1e-9`，`atol = 1e-12`。实测见 `metrics.json`，
  SDD21 的最大绝对误差在 1e-15 量级。

## Notes

- 这是**解析模型**，不是实测数据。它验证的是变换与读入路径的数学正确性，
  不能替代与 PLTS / PNA 实测文件的对拍；后者需要单独的 `PLTS` / `PNA` 类用例。
- 不要手工编辑 `input/` 与 `reference/`。改模型请改生成脚本并重新生成，
  变更需按 `docs/GOLDEN_DATA.md` §8 人工 Review。
