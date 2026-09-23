# TEST_STRATEGY.md

# 1. Goals

- Agent 可自动判断代码是否正确
- 核心算法可数值回归
- GUI 关键流程可验证
- 重构不破坏数值结果

# 2. Test Layers

```text
UI Tests
Integration Tests
Unit Tests + Numerical Regression
```

# 3. Directory

下图是**目标结构**。标注 `<planned>` 的目录当前尚未创建，编写对应层级测试时再新建。

```text
tests/
├── unit/
├── integration/    <planned>
├── regression/
├── ui/
├── instruments/    <planned>
└── data/
```

# 4. Unit Tests

重点：Parser、Network、Port Map、Units、Interpolation、Renormalization、Mixed Mode、Window、Transform primitives。

要求：快、deterministic、不依赖 GUI、不依赖真实仪器。

# 5. Numerical Regression

每个重要算法记录：Reference、Input、Expected、Tolerance、Metrics。

示例：

```python
np.testing.assert_allclose(actual, expected, rtol=1e-8, atol=1e-10)
```

复杂算法同时统计：

- max_abs_error
- rms_error
- magnitude_error_db
- phase_error_deg
- peak_time_error
- impedance_error

# 6. Golden Regression Scope

- Time Domain
- TDR/TDT
- Gating
- Mixed Mode
- Renormalization
- De-embedding
- AFR

# 7. UI Tests

使用 `pytest-qt`。CI 已配置 `libegl1` 与 `QT_QPA_PLATFORM=offscreen`，UI 测试在 CI 上可运行。

## 边界

- **数值正确性一律不走 UI 测试**，下沉到 Service / Core / Algorithms 层。
- UI 测试只验证：用户动作是否触发了正确的 Service 调用、返回结果是否正确反映到界面状态、错误是否被呈现。
- 判据是**界面状态**（控件启用性、模型内容、布局结构），不是像素。

## 关键交互

至少覆盖：

- 打开文件 → 在 Data Browser 对应视图类型下新增 window
- 添加 Trace → 进入 current_plot
- 切换视图网格（1×1 / 2×2）→ PlotModel 不丢失
- 面板停靠、浮动、关闭后再打开
- 非法输入与 IO 失败的错误提示

## 布局状态

布局与停靠状态通过**序列化后比对**验证，不使用截图。

不引入截图 / 视觉回归：跨平台字体与渲染差异会产生大量假阳性，且与 `AGENTS.md` §10 禁止无依据放宽 tolerance 的规则容易冲突。

# 8. Threading Tests

验证：不阻塞 UI、错误正确反馈、取消机制（若支持）、Worker 不直接访问 Widget。

# 9. Instrument Tests

CI 使用 Mock。真实仪器测试标记：

```python
@pytest.mark.hardware
```

# 10. CI Levels

PR：ruff + mypy + unit + fast regression。  
Nightly/Manual：full regression + large data + benchmark + hardware。

# 11. Tolerance Policy

测试失败后不得直接放宽 tolerance。任何调整必须记录原因与 Reference。

# 12. Bug Rule

算法 Bug：先增加 failing test，再修复。

# 13. Naming

```text
test_<unit>_<condition>_<expected>
```
