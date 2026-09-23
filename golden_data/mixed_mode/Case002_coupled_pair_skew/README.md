# Case002 — Coupled differential pair with 2 ps intra-pair skew

## Purpose

在**存在模式转换**的情况下验证 SDD21。Case001 的线对完全对称，
SCD21 恒为 0；真实走线总有线内偏斜，SDD21 必须在 SCD21 非零时仍然正确。

## Source

`ANALYTICAL`。与 Case001 同一模型，在端口 4（线 B 远端）串入一段
理想匹配、延时 `tau = 2 ps` 的传输线，相当于把 S 的第 4 行与第 4 列
乘以 `a = exp(-j*2*pi*f*tau)`。展开混合模式组合得到闭式解：

```text
Sdd21 = Sodd21  (1 + a) / 2        Scd21 = Sodd21  (1 - a) / 2
Scc21 = Seven21 (1 + a) / 2        Sdc21 = Seven21 (1 - a) / 2
Sdd11 = Sodd11                     Scc11 = Seven11        （端口 1 侧不受影响）
```

参考同样**不经过被测的混合模式变换**。推导见生成脚本的模块 docstring。

## Software / Instrument Version

不适用：无第三方软件、无仪器。参考为解析解。

## Configuration

与 Case001 相同，另加 `skew_s = 2e-12`。完整参数见 `config.json`。

## Expected Behavior

- SDD21 与 Case001 同形，额外带 `(1+a)/2` 的轻微下压。
- `|SCD21| / |SDD21| = |tan(pi * f * tau)|`，随频率上升：
  20 GHz 处约 0.126，即比 SDD21 低约 18 dB。
- SDD11、SCC11 与 Case001 逐点相同。
- Tolerance：`rtol = 1e-9`，`atol = 1e-12`。实测见 `metrics.json`。

## Notes

- 偏斜建模为单端口延时，是对布线长度差的一阶近似；它不改变耦合，
  因此不能用来标定耦合不对称引起的模式转换。
- 同 Case001：不要手工编辑 `input/` 与 `reference/`。
