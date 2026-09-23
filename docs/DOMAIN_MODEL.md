# DOMAIN_MODEL.md

# 1. Purpose

定义 Interconnect Studio 的稳定领域对象、单位、数组形状和端口约定。

# 2. Network

当前核心模型：

```python
@dataclass(frozen=True, slots=True, init=False)
class Network:
    frequencies_hz: NDArray[np.float64]
    s: NDArray[np.complex128]
    z0: complex
    port_names: tuple[str, ...] | None
```

约束：

```text
frequencies_hz.shape == (nfreq,)
s.shape == (nfreq, nport, nport)
```

`z0` 定义为该 `Network` 的单一参考阻抗标量。

约束：

```text
一个 Network 只有一个确定的 z0。
z0 对该 Network 的所有端口和所有频点一致。
```

## Network Invariants

- `frequencies_hz` 为一维、非空、有限、非负、严格递增。
- 允许第一个频点为 DC（0 Hz）。
- `s.shape == (n_freq, n_port, n_port)`，端口矩阵必须为方阵。
- S 参数必须全部有限。
- `z0` 为有限、非零的单一标量，可表示为 complex。
- `port_names` 若存在，必须与端口数一致、非空且唯一。
- Network 构造时复制输入数组；内部 `frequencies_hz` 与 `s` 设为只读。
- Network 采用不可变语义；后续算法默认返回新的 Network。

## S-parameter Access

`Network` 提供通用只读访问接口：

```python
network.s_parameter(response_port, source_port)
```

约定：

- 参数使用 Python 内部 0-based 端口索引。
- `S[i, j]` 表示端口 `j` 激励时在端口 `i` 的响应。
- 因此工程语义的 `S21` 对应 `s_parameter(1, 0)`。
- 返回 shape 为 `(n_freq,)` 的 `complex128` 只读视图。
- 越界、布尔值或非整数端口索引抛出 `InputValidationError`。
- 不为固定端口数定义大量 `s11/s21/...` 属性，避免限制多端口扩展。

# 3. Port Convention

- Python 内部：0-based
- UI：1-based
- 端口转换必须在明确边界发生

## Port Mapping

端口重排使用纯函数：

```python
remap_ports(network, port_order)
```

约定：

- `port_order` 使用 Python 内部 0-based 端口号。
- 语义为 `new port -> old port`。
- 例如 `(2, 0, 3, 1)` 表示新端口 0/1/2/3 分别对应原端口 2/0/3/1。
- `port_order` 必须是完整排列：长度等于端口数、无重复、无越界。
- S 参数矩阵的行和列必须同时重排。
- `port_names` 若存在，也必须同步重排。
- frequency 与 `z0` 保持不变。
- 返回新的不可变 `Network`，不得修改源对象。

# 4. Units

- Frequency: Hz
- Time: second
- Distance: SI 优先
- UI 层负责友好单位显示

# 5. Reference Impedance

每个 `Network` 只有一个确定的参考阻抗 `z0`，并对该网络的所有端口、所有频点统一生效。

- `z0` 是标量，不是数组。
- 默认值是否采用 50 Ω 由构造 API 决定，但算法不得隐式假设输入一定为 50 Ω。
- Renormalization 的结果应生成新的 `Network`，并更新为新的单一 `z0`。
- 如未来需要支持端口相关或频率相关参考阻抗，应通过新的领域模型扩展，而不是改变当前 `Network.z0` 语义。
- Touchstone 2.0 允许 per-port z0。读入时**要求各端口 z0 一致**，不一致抛 `DataFormatError`，不做隐式归一化。

# 6. Trace

`Trace` 是 UI 无关、不可变的一维绘图数据模型。

```python
Trace(
    name,
    x,
    y,
    x_unit="",
    y_unit="",
)
```

约定：

- `x` 为 `float64`、一维、非空、有限、严格递增。
- `y` 为一维，允许 `float64` 或 `complex128`。
- `x/y` 点数必须一致。
- 为兼容 LogMag(0)、SWR/阻抗奇点，`y` 允许出现 `inf/NaN`。
- 构造时复制输入数组并设为只读。
- `Smith/Polar` 使用 complex Trace；普通 Cartesian 格式使用 real Trace。
- S 参数到 Trace 的桥接由算法层 `create_s_parameter_trace(...)` 完成。
- Trace 携带所属 `DataFile` 的标识（`source_id`），用于多文件叠加时区分同名曲线（两个文件都有 S21 LogMag）与图例命名。

## Plot Model

`PlotModel` 是 UI 无关、不可变的单绘图区模型。

支持绘图类型：

- `PlotKind.CARTESIAN`
- `PlotKind.POLAR`
- `PlotKind.SMITH`

约定：

- 一个 PlotModel 保存零条或多条 Trace。
- Cartesian 只接受 real Trace。
- Polar / Smith 只接受 complex Trace。
- 单 X 轴、**单 Y 轴**：一个 plot 承载一种显示格式，其中所有 Trace 共用该格式（对标 PLTS）。因此同一 PlotModel 内所有 Trace 的 `x_unit` 与 `y_unit` 都必须一致。
- 不同单位的量需要开多个 plot 比较，不通过第二个 Y 轴叠加。
- 一屏多图的网格编排由 `ViewLayout` 承载，不属于 PlotModel（见 `UI_DESIGN.md` §4）。
- `add_trace()` / `remove_trace()` 返回新的 PlotModel，不修改原对象。
- PlotModel 不依赖 PyQt6 或具体绘图库。

## 二维数据（眼图 / 热图）

眼图是二维密度数据，**不满足** `Trace` 的一维、x 严格递增约束，也不属于现有三种 `PlotKind`。

约定：眼图、直方图、热图类显示必须使用独立的二维数据模型，**不得为此放宽 `Trace` 或 `PlotModel` 的现有不变量**。该模型在 V2.0 实际实现时定义。

## Marker

```python
@dataclass(frozen=True, slots=True)
class Marker:
    trace_name: str
    x: float
```

- Marker 保存 x 坐标，y 值由 Trace 实时求值，不冗余存储。
- 支持 delta marker（相对另一 Marker）。

## Limit Line / Mask

```python
@dataclass(frozen=True, slots=True)
class LimitSegment:
    x_start: float
    x_stop: float
    y_start: float
    y_stop: float
    kind: LimitKind   # UPPER | LOWER
```

- `Mask` 为若干 `LimitSegment` 的集合，附带名称与适用的 x/y 单位。
- 判定结果为 pass / fail 加越界点列表。
- **具体标准（USB / PCIe / DDR / IEEE 802.3 等）是外部可加载的配置文件，不内置于软件。**

# 6.5 Port Group

端口分组是 Mixed-Mode 与串扰分析**共用**的底层模型。两者描述的是同一件事——哪些端口属于同一条线、线的哪一端——因此不允许各自长出一套表示。

```python
@dataclass(frozen=True, slots=True)
class Line:
    """一条传输线（单端或差分）的两端端口。"""
    name: str
    near: tuple[int, ...]   # 单端 1 个；差分 2 个，顺序为 (正, 负)
    far: tuple[int, ...]

@dataclass(frozen=True, slots=True)
class PortGroup:
    lines: tuple[Line, ...]
```

约定：

- 端口号为 Python 内部 0-based。
- 同一 `PortGroup` 内所有端口号不重复。
- `near` 与 `far` 的长度必须一致（同一条线两端同构）。
- 差分线的正负顺序即 Mixed-Mode 的极性来源。

派生关系：

```text
Mixed-Mode pair mapping = 各 Line 的 near / far 按顺序展开
NEXT(victim, aggressor)  = 激励 aggressor.near，测 victim.near
FEXT(victim, aggressor)  = 激励 aggressor.near，测 victim.far
```

§7 的默认 1-3/2-4 配对在本模型中表示为：

```python
PortGroup(lines=(
    Line(name="Line1", near=(0, 2), far=(1, 3)),
))
```

# 7. Mixed Mode

## Pair Mapping

配对必须显式传入算法层，不设隐含默认值。错误配对不会报错，只会让 SDD/SCC 静默错位。

UI 预设默认为 **1-3 / 2-4**（PLTS / PNA 风格）：

```text
差分端口 1 = {0, 2}
差分端口 2 = {1, 3}
```

即 port 0 = 左侧正、port 2 = 左侧负、port 1 = 右侧正、port 3 = 右侧负，`1 → 2` 为 through。

同时内置 **1-2 / 3-4** 预设（IEEE / Bockelman 顺序，scikit-rf `se2gmm` 默认），用于与 scikit-rf 交叉对拍，以及导入按该顺序编号的文件。该顺序可平凡推广到 2N 端口：pair k = `{2k, 2k+1}`。

所选配对必须记入结果 metadata。

## Polarity

pair 内索引较小的端口为正端（+）。

## Logical Ordering

输出矩阵按**差分块在前、共模块在后**排列：

```text
[D1 .. Dn, C1 .. Cn]
```

得到标准分块形式：

```text
[[Sdd, Sdc],
 [Scd, Scc]]
```

取 SDD 即切左上角子块。

## Normalization

采用 1/√2 功率不变变换：

```text
a_d = (a1 - a2) / sqrt(2)
a_c = (a1 + a2) / sqrt(2)
```

由此差分端口参考阻抗为 `2 * z0`，共模端口为 `z0 / 2`。

## MixedModeNetwork

因为差分与共模端口的参考阻抗不同，Mixed-Mode 结果**不能**表示为 `Network`（见 §5：一个 Network 只有一个标量 z0）。

已确定：引入独立领域类型 `MixedModeNetwork` 承载该结果，保持 `Network` 现有不变量不变。

```python
@dataclass(frozen=True, slots=True)
class MixedModeNetwork:
    frequencies_hz: NDArray[np.float64]
    s: NDArray[np.complex128]     # (n_freq, 2*n_pair, 2*n_pair)，分块排序
    z0_differential: complex      # = 2 * z0
    z0_common: complex            # = z0 / 2
    pair_mapping: tuple[tuple[int, int], ...]
```

# 8. Fixture

```python
@dataclass
class FixturePair:
    left: Network | None
    right: Network | None
```

建议扩展 metadata：

- reference plane
- port mapping
- extraction method
- algorithm version

# 9. Data Hierarchy

对标 PLTS 的 Data Browser，**固定三层**：

```text
Group → Measurement → DataFile
```

```python
@dataclass(frozen=True, slots=True)
class DataFile:
    """叶子节点：一个导入的 .sNp 文件或算法产物。"""
    id: str                    # 稳定标识，Trace 通过它溯源
    name: str                  # 显示名，可由用户重命名
    network: Network
    source_path: Path | None   # 来源文件；算法产物为 None
    imported_at: datetime


@dataclass(frozen=True, slots=True)
class Measurement:
    name: str
    files: tuple[DataFile, ...]


@dataclass(frozen=True, slots=True)
class Group:
    name: str
    measurements: tuple[Measurement, ...]
```

约定：

- 层级固定为三层，不可嵌套更深，也不可跳层。
- `Group` 与 `Measurement` 是纯容器，条目由用户创建与命名。
- `DataFile.id` 在 Project 内唯一，且不随重命名改变。
- 去嵌、Mixed-Mode 等算法产物同样封装为 `DataFile`，并在 metadata 中记录来源与算法参数，使派生结果与导入数据在树中同构。
- 参数（S11/S21/...）与显示格式**不是树节点**，由 UI 的 Parameter / Format 面板承担（见 `UI_DESIGN.md` §3）。

> 待确认：`Group` / `Measurement` 目前按"层级固定、条目用户可增删"建模。若 PLTS 实际为预置不可增删的分类，此节需改为枚举。
>
> 原文核对（`PLTS_REFERENCE.md` §8）：PLTS Data Browser 顶层是预置、不可增删的**分析类型**（频域单端 / 平衡、时域单端 / 差分、眼图单端 / 差分、RLCG 四种）及 Template View / Multi-data 节点，其下为已打开的 window（以 `.dut` 文件标识）。是否据此修改本节待决策。

# 10. Project

Project 保存用户工程状态，不保存 QWidget 实例。

```python
@dataclass
class Project:
    groups: tuple[Group, ...]
    windows: tuple[Window, ...]     # 每个 window 持有自己的 ViewLayout
    fixtures: ...
    settings: ...
```

- 一个 window 只承载单个 `DataFile` 与单一分析类型（见 `UI_DESIGN.md` §4）。
- 布局（`ViewLayout`）持久化；选中态属于 UI 状态，不持久化。

# 11. Analysis Results

```python
@dataclass
class TimeDomainResult:
    time_s: NDArray[np.float64]
    values: NDArray[np.complex128]
```

```python
@dataclass
class AfrResult:
    fixture_a: Network
    fixture_b: Network
    metrics: AfrMetrics
```

# 12. Error Model

建议：

- InputValidationError
- DataFormatError
- AlgorithmError
- InstrumentError
- ProjectError

# 13. Mutability

已确定：`Network` 采用不可变语义。构造时复制输入数组并将内部数组设置为只读；算法默认返回新对象，不隐式修改原始测量数据。

# 14. Serialization

Network：Touchstone / NPZ（测试）/ `<TODO>`  
Project：JSON+binary / HDF5 / ZIP project / `<TODO>`

# 15. Decisions To Finalize

- [x] `z0` model: one scalar reference impedance per Network
- [x] Network mutability: immutable semantics with owned read-only arrays
- [x] Mixed-Mode mapping convention: 默认 1-3/2-4，分块排序，1/√2 归一化
- [x] Mixed-Mode 结果载体: 新增 `MixedModeNetwork`，不扩展 `Network.z0`
- [ ] metadata schema
- [ ] Project format
