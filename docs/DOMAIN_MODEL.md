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

# 3. Port Convention

- Python 内部：0-based
- UI：1-based
- 端口转换必须在明确边界发生

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

# 6. Trace

```python
@dataclass
class Trace:
    name: str
    x: NDArray
    y: NDArray
    x_unit: str
    y_unit: str
```

显示格式与 Trace 的关系：`<TODO>`

# 7. Mixed Mode

必须定义：

- pair mapping
- polarity
- logical ordering
- normalization

默认差分端口映射：`<TODO>`

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

# 9. Project

Project 保存用户工程状态，不保存 QWidget 实例。

```python
@dataclass
class Project:
    networks: ...
    traces: ...
    fixtures: ...
    settings: ...
```

# 10. Analysis Results

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

# 11. Error Model

建议：

- InputValidationError
- DataFormatError
- AlgorithmError
- InstrumentError
- ProjectError

# 12. Mutability

已确定：`Network` 采用不可变语义。构造时复制输入数组并将内部数组设置为只读；算法默认返回新对象，不隐式修改原始测量数据。

# 13. Serialization

Network：Touchstone / NPZ（测试）/ `<TODO>`  
Project：JSON+binary / HDF5 / ZIP project / `<TODO>`

# 14. Decisions To Finalize

- [x] `z0` model: one scalar reference impedance per Network
- [x] Network mutability: immutable semantics with owned read-only arrays
- [ ] metadata schema
- [ ] Mixed-Mode mapping convention
- [ ] Project format
