# AGENTS.md

> 本文件定义 AI Coding Agent 在 **Interconnect Studio** 仓库中的工作规则。

## 1. Project Identity

- Product: **Interconnect Studio**
- Repository: `interconnect-studio`
- Python package: `interconnect_studio`
- GUI: PyQt6
- Runtime: Python >= 3.12

项目目标：构建面向 VNA 与高速互联分析的桌面软件，覆盖 Touchstone、S 参数、Mixed-Mode、时域、TDR/TDT、Gating、Fixture De-embedding、2X-Thru/AFR，并为 Eye/PAM4/COM 与仪器控制预留扩展能力。

## 2. Required Reading

开始任务前，根据任务范围阅读：

1. `docs/PRODUCT.md`
2. `docs/ARCHITECTURE.md`
3. `docs/DOMAIN_MODEL.md`
4. `docs/ALGORITHM_GUIDE.md`
5. `docs/TEST_STRATEGY.md`
6. `docs/GOLDEN_DATA.md`
7. `docs/CODING_GUIDELINES.md`
8. `docs/ROADMAP.md`

## 3. Technology Stack

- Python >= 3.12
- PyQt6
- NumPy / SciPy
- scikit-rf：只在架构允许的位置使用，不作为核心算法正确性的唯一依据
- pytest / pytest-qt
- uv
- ruff
- mypy
- GitHub Actions

## 4. Repository Structure

下图是**目标结构**。标注 `<planned>` 的目录当前尚未创建，需要时按本结构新建，不要假定它们已经存在。

```text
interconnect-studio/
├── AGENTS.md
├── pyproject.toml
├── src/
│   └── interconnect_studio/
│       ├── app/
│       ├── ui/
│       ├── core/
│       ├── algorithms/
│       ├── io/
│       ├── services/
│       └── instruments/        <planned>  Roadmap Phase 8
├── tests/
│   ├── unit/
│   ├── integration/            <planned>
│   ├── regression/             <planned>
│   ├── ui/
│   └── data/
├── golden_data/
├── docs/
└── scripts/
```

## 5. Architecture Rules

1. UI 不实现数值算法。
2. `algorithms` 不依赖 PyQt6。
3. `core` 不依赖 UI。
4. Widget 不直接解析 Touchstone。
5. Widget 不直接调用具体 SCPI Driver。
6. 高级算法必须有独立 API 和自动测试。
7. 影响数值结果的修改必须增加或更新 Regression Test。
8. 禁止为了赶进度形成 Giant Class / Giant Function。
9. 默认优先组合而不是继承。
10. 核心领域模型变化必须同步更新 `DOMAIN_MODEL.md`。

依赖方向：

```text
UI → Services → Core / Algorithms / IO / Instruments
```

禁止：

```text
Algorithms → UI
Core       → UI
IO         → UI
```

## 6. Numerical Conventions

除非对应算法规范明确另有定义：

- frequency: Hz, `float64`
- time: second, `float64`
- complex data: `complex128`
- S matrix shape: `(n_freq, n_port, n_port)`
- Python 内部端口号：0-based
- UI 显示端口号：1-based
- `z0` 是每个 Network 的单一标量参考阻抗，不得假定恒为 50 Ω
- 单位转换必须显式，不允许隐藏在不透明 API 中
- Touchstone 1.x 的矩阵排列：**2 端口是列主序特例，≥3 端口为行主序**；详见 `ALGORITHM_GUIDE.md`「Touchstone Data Ordering」

## 7. Coding Rules

必须：

- 使用 type hints
- 公共 API 有 docstring
- 使用 `pathlib.Path`
- 使用 `logging`
- 数组 API 注明单位和 shape
- 禁止裸 `except:`
- 避免全局可变状态

推荐：

```python
def renormalize(network: Network, new_z0: complex) -> Network:
    ...
```

不推荐：

```python
def calc(a, b, c):
    ...
```

## 8. PyQt6 Rules

- GUI 主线程只处理 UI。
- AFR、时域、大文件 IO、仪器操作不得长时间阻塞主线程。
- 后台任务使用统一 Worker / Task Runner。
- Worker 不直接访问 Widget。
- Worker 通过 signal 把结果返回 UI 线程。
- 可测试业务逻辑下沉到 Service/Core/Algorithms。

## 9. Algorithm Workflow

新增/修改算法时：

1. 明确输入、输出、单位、shape。
2. 明确 mathematical convention。
3. 明确 Reference。
4. 明确 tolerance / metrics。
5. 先增加测试或 Golden Case。
6. 实现最小变更。
7. 跑 Unit + Regression。
8. 检查 diff。

完成条件：

```text
Unit Test Pass
Regression Test Pass
Tolerance documented
No GUI dependency
No hidden unit conversion
```

## 10. Golden Data Rules

- Agent 不得自动覆盖 Golden Data。
- 不得通过删除 Golden Case 让测试通过。
- 不得通过无依据放宽 tolerance 让测试通过。
- Reference 必须标记来源：Analytical / PLTS / PNA / ZNA / Internal Approved。
- 更新 Golden Reference 必须由人工 Review。

## 11. Required Checks

提交任务前运行：

```bash
uv run ruff check .
uv run mypy src
uv run pytest
```

如存在完整回归脚本：

```bash
uv run python scripts/run_regression.py
```

## 12. Definition of Done

- [ ] 满足 Issue / Spec
- [ ] 无无关修改
- [ ] lint 通过
- [ ] type check 通过
- [ ] Unit Test 通过
- [ ] Regression Test 通过（如适用）
- [ ] 公共 API 文档已更新
- [ ] 未破坏依赖规则
- [ ] 已自查 Git diff

## 13. Stop / Ask Conditions

遇到以下情况不得自行猜测：

- 算法公式存在多种合理解释
- PLTS/PNA 行为不明确
- Golden Data 与文档冲突
- 需要修改核心 Network 数据模型
- 需要修改公共项目文件格式
- 需要替换 Golden Reference
- 要引入大型第三方依赖
- 数值误差明显恶化但测试仍通过
- 校准/波量定义/阻抗定义将发生变化

## 14. Forbidden Actions

禁止：

- 注释失败测试
- 硬编码测试结果
- 大量 `# type: ignore`
- 在 UI 中复制算法
- 未授权替换核心算法
- 提交密码、License、Token、仪器 IP 等敏感信息
