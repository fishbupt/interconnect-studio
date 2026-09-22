# Interconnect Studio

Interconnect Studio 是一个基于 **Python + PyQt6** 的 VNA / 高速互联分析软件项目。

当前目标包括：

- Touchstone S 参数读写
- S 参数显示与分析
- Port Mapping / Renormalization / Mixed-Mode
- Frequency ↔ Time Domain
- TDR / TDT
- Gating
- Fixture De-embedding
- 2X-Thru / AFR
- 后续 Eye / PAM4 / COM
- 后续 VNA 仪器控制与自动测量

> 当前工程仍处于早期开发阶段。  
> 目前已经具备核心 `Network` 数据模型以及 Touchstone Reader / Writer，
> **PyQt6 图形界面入口尚未实现**。

---

## 1. 技术栈

- Python >= 3.12
- PyQt6
- NumPy
- SciPy
- uv
- pytest / pytest-qt
- ruff
- mypy
- GitHub Actions

---

## 2. Windows 本地开发环境

以下示例默认使用 **Windows PowerShell**。

### 2.1 安装 Git

如果本机还没有 Git，请先安装 Git for Windows，然后验证：

```powershell
git --version
```

### 2.2 安装 uv

推荐使用 uv 官方 Windows 安装脚本：

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

安装完成后重新打开 PowerShell，并验证：

```powershell
uv --version
```

也可以使用 WinGet：

```powershell
winget install --id=astral-sh.uv -e
```

---

## 3. Clone 工程

```powershell
git clone https://github.com/fishbupt/interconnect-studio.git
cd interconnect-studio
```

确认当前分支：

```powershell
git branch
```

---

## 4. 安装 Python 与项目依赖

项目要求 Python >= 3.12。

可以直接让 uv 安装 Python 3.12：

```powershell
uv python install 3.12
```

然后同步项目环境：

```powershell
uv sync --dev
```

uv 会在项目目录中创建：

```text
.venv/
```

无需手工创建 virtualenv。

---

## 5. 验证工程可以正常导入

```powershell
uv run python -c "import interconnect_studio; print(interconnect_studio.__version__)"
```

预期输出类似：

```text
0.1.0
```

---

## 6. 运行全部测试

```powershell
uv run pytest
```

显示更详细测试信息：

```powershell
uv run pytest -v
```

只运行 Network 测试：

```powershell
uv run pytest tests/unit/test_network.py -v
```

只运行 Touchstone 测试：

```powershell
uv run pytest tests/unit/test_touchstone.py -v
```

---

## 7. 运行代码质量检查

提交代码前建议完整执行：

### Ruff

```powershell
uv run ruff check .
```

### Mypy

```powershell
uv run mypy src
```

### Pytest

```powershell
uv run pytest
```

也就是：

```text
ruff
 ↓
mypy
 ↓
pytest
```

GitHub Actions 会执行同样的基础检查。

---

## 8. 可选：激活虚拟环境

通常推荐直接使用 `uv run`，不需要手工激活虚拟环境。

如果希望激活：

```powershell
.venv\Scripts\Activate.ps1
```

激活后可以直接运行：

```powershell
python
pytest
```

退出：

```powershell
deactivate
```

---

## 9. 当前代码结构

```text
interconnect-studio/
├── AGENTS.md
├── README.md
├── pyproject.toml
├── src/
│   └── interconnect_studio/
│       ├── core/
│       │   ├── errors.py
│       │   └── network.py
│       └── io/
│           └── touchstone.py
├── tests/
│   ├── unit/
│   └── data/
├── golden_data/
├── docs/
└── scripts/
```

---

## 10. Touchstone 快速示例

### 读取

```python
from interconnect_studio.io import read_touchstone

network = read_touchstone("example.s2p")

print(network.n_ports)
print(network.n_freq)
print(network.z0)
print(network.s.shape)
```

### 写入

```python
from interconnect_studio.io import read_touchstone, write_touchstone

network = read_touchstone("input.s2p")

write_touchstone(
    network,
    "output.s2p",
    data_format="ri",
    frequency_unit="ghz",
)
```

当前 Touchstone 1.x 支持：

- `.s1p`
- `.s2p`
- `.s4p`
- RI
- MA
- DB
- Hz / kHz / MHz / GHz

---

## 11. 当前如何“运行” Interconnect Studio

目前 PyQt6 Application Shell 尚未进入实现阶段，因此当前版本还没有：

```powershell
interconnect-studio
```

这样的 GUI 启动命令。

当前阶段本地开发主要通过：

```powershell
uv run pytest
```

以及 Python API 进行验证。

在后续完成 PyQt6 Application Shell 后，本 README 会补充正式的 GUI 启动方式。

---

## 12. 开发规范

开始开发前建议阅读：

- `AGENTS.md`
- `docs/PRODUCT.md`
- `docs/ARCHITECTURE.md`
- `docs/DOMAIN_MODEL.md`
- `docs/ALGORITHM_GUIDE.md`
- `docs/TEST_STRATEGY.md`
- `docs/GOLDEN_DATA.md`
- `docs/CODING_GUIDELINES.md`
- `docs/ROADMAP.md`

其中 `AGENTS.md` 同时是 OpenCode / Coding Agent 的项目级开发约束。

---

## 13. 常见 Windows 问题

### PowerShell 不允许执行 Activate.ps1

不需要修改系统策略，直接使用：

```powershell
uv run pytest
```

即可，不必激活 virtual environment。

### uv 找不到

安装 uv 后重新打开 PowerShell：

```powershell
uv --version
```

如果仍找不到，请检查 uv 安装目录是否已经加入用户 PATH。

### Python 版本不正确

执行：

```powershell
uv python install 3.12
uv sync --dev
```

然后检查：

```powershell
uv run python --version
```

---

## 14. 推荐的开发前检查

每次开始开发前：

```powershell
git pull
uv sync --dev
uv run pytest
```

提交前：

```powershell
uv run ruff check .
uv run mypy src
uv run pytest
```
