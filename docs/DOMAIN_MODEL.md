# DOMAIN_MODEL.md

# 1. Purpose

定义 Interconnect Studio 的稳定领域对象、单位、数组形状和端口约定。

# 2. Network

建议初始模型：

```python
@dataclass
class Network:
    frequencies_hz: NDArray[np.float64]
    s: NDArray[np.complex128]
    z0: complex
    port_names: tuple[str, ...] | None = None
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

推荐：算法默认返回新对象，不隐式修改原始测量数据。

# 13. Serialization

Network：Touchstone / NPZ（测试）/ `<TODO>`  
Project：JSON+binary / HDF5 / ZIP project / `<TODO>`

# 14. Decisions To Finalize

- [x] `z0` model: one scalar reference impedance per Network
- [ ] metadata schema
- [ ] Mixed-Mode mapping convention
- [ ] Project format
