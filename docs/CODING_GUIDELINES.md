# CODING_GUIDELINES.md

# 1. Runtime

Python >= 3.12

# 2. Environment / Package

统一使用 `uv`。

```bash
uv sync
uv run pytest
uv run ruff check .
```

# 3. Style / Quality

- ruff check
- ruff format
- mypy
- 推荐 line length 100~120（最终固定一个值）

# 4. Naming

- Class: PascalCase
- function/variable: snake_case
- constants: UPPER_CASE
- 标准领域缩写可用：S11, TDR, VNA, AFR, DUT

# 5. API Design

推荐：

```python
def transform_low_pass_step(
    frequencies_hz: NDArray[np.float64],
    response: NDArray[np.complex128],
    config: TimeDomainConfig,
) -> TimeDomainResult:
    ...
```

避免模糊参数名和过长参数列表。

# 6. Units

名称体现单位：`frequencies_hz`, `time_s`, `gate_start_s`。

# 7. Mutation

默认不原地修改 Network。显式 in-place API 必须在名称中体现。

# 8. Logging

使用标准 `logging`，业务代码禁止大量 `print()`。

# 9. Exceptions

领域异常单独定义，禁止 `except: pass`。

# 10. PyQt6

- slot 不实现复杂算法
- 长任务后台执行
- Worker 通过 signal 返回结果
- 不跨线程直接更新 Widget

# 11. Dataclasses

领域结果优先考虑 dataclass；是否 frozen 由数据模型决策。

# 12. Config Objects

复杂参数优先使用明确 Config dataclass，避免十几个位置参数。

# 13. Docstrings

公共 API 说明 purpose、parameters、units、shape、return、raises；算法还需 assumptions/reference。

# 14. Dependencies

新增依赖评估 License、维护状态、Windows、打包兼容性、数值行为。

# 15. Performance

```text
Correctness → Profiling → Optimization
```

# 16. PR Quality

单一目标、小 diff、有测试、无无关格式化、文档同步。
