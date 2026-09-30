# 文件工作流程

当前版本提供频域数据的导入、分析、工程保存/恢复和统一导出。

## 操作入口

| 操作 | 菜单 / 快捷键 | 行为 |
| --- | --- | --- |
| 新建工程 | File → 新建工程 / Ctrl+N | 处理未保存修改后，打开空工作区 |
| 导入测量 | File → Import / Ctrl+O | 单文件、多文件组装或配置文件组装 |
| 打开工程 | File → 打开工程 / Ctrl+Shift+O | 恢复 `.icproj` 中的测量和视图 |
| 保存工程 | File → 保存工程 / Ctrl+S | 保存所有打开的数据文件与窗口 |
| 工程另存为 | File → 工程另存为 / Ctrl+Shift+S | 指定新的工程路径 |
| 导出数据 | File → 导出数据 / Ctrl+E | 为任一打开的数据文件选择输出格式 |
| 最近文件 | File → 最近文件 | 最近 4 个成功打开的测量/工程，去重；支持清空 |
| 关闭文件 | File / Data Browser 右键 | 关闭当前数据文件的全部视图 |
| 关闭所有文件 | File → 关闭所有文件 | 一次处理所有未保存修改，结束当前工程会话 |
| 常用设置 | 设置 → 常用设置 | 默认目录、主题、导出类型/单位、曲线线宽和布局记忆 |

导入、组装、工程读写与数据导出的 GUI 操作使用统一 TaskRunner，并显示模态进度。
写入过程中不提供中断按钮；只有写入完成才替换目标文件，失败时原文件仍在。

## 导出

| 格式 | 数值 / 单位 | 参考阻抗 |
| --- | --- | --- |
| Touchstone 1.x `.sNp` | RI / MA / DB；Hz / kHz / MHz / GHz | 正实数标量 |
| Touchstone 2.0 `.ts` | RI / MA / DB；Hz / kHz / MHz / GHz | 正实数标量，完整单端矩阵 |
| CITIfile `.cti` | RI；Hz | 50 Ω；非 50 Ω 必须明确勾选转换，否则拒绝导出 |
| 文本 `.csv` / `.txt` | RI；Hz / kHz / MHz / GHz | 自定义注释记录复数标量，供本软件重新导入 |

- 可选择全部频率或 Subset，Subset 只保留测量点，不插值、不改变频点。
- 端口顺序填写 **输出端口 → 原始端口** 的完整排列。例如 `3,1,4,2` 表示
  新端口 1 对应旧端口 3。行、列同时重排，原数据不变。
- 输出后缀由所选格式确定；覆盖确认针对实际输出路径，而不是用户填写的旧后缀。
- 多文件组装/配置组装窗口中的 Export 按钮也使用同一导出对话框。
- CITIfile 的 50 Ω 转换使用现有 pseudo-wave 重归一化，且只作用于导出副本。
- CSV 的多位端口列名（如 `S[12,3](real)`）按 CSV 规则加引号。
- 文本头 `! Reference Impedance <real> <imag>` 是本软件约定；第三方软件可能需要手动
  指定参考阻抗。没有该注释的旧文本仍默认 50 Ω；API 的显式 `z0` 参数优先。

当前不提供：混模矩阵写出、每参数一文件、时域/门控/平滑结果导出，以及导出重采样。
它们需要对应的领域能力和独立规格，不会在导出时自动猜测或改变数据。

## 工程格式 v1

`.icproj` 是 ZIP 容器，包含 UTF-8 `manifest.json` 和 `arrays/<index>.npy`。
manifest 标识：`format = interconnect-studio-project`、`version = 1`。

保存内容：

- 每个数据文件的稳定 ID、显示名称、来源路径和导入时间。
- 频率（Hz）、完整复数 S 矩阵、复数标量 z0，以及 Network 端口名称。
- DUT 配置、逻辑分组、极性和端口标签。
- 每个窗口的分析类型、窗口编号、模板名称、网格和全部 plot/trace。
- Trace 的名称、单位、实际 x/y 数组、来源 ID 和已有的计算配方。
- 坐标范围及自动缩放标志；主窗口几何和停靠布局。

数据和实际曲线均嵌入工程，原测量文件移动或删除后仍能恢复。
模板名称用于恢复窗口标识，不修改用户的模板目录。
选中窗口/选中格不持久化（沿用 UI_DESIGN 的决定），恢复后选中第一个窗口的第一格。
只承诺恢复当前已实现的单端/平衡频域 Cartesian 视图，不宣称兼容 PLTS `.dut` / `.dsta`。

读取时先验证整个工程，失败不替换当前工作区。未知版本、重复 ID/窗口、缺失数据引用、
非法布局/数组和不支持的视图会明确报错。NumPy 数组禁用 pickle，不解压文件到磁盘。
单成员上限 512 MiB、总解压大小上限 2 GiB、manifest 上限 16 MiB。
保存也检查同样的容量边界；超限不替换已有工程。

## 未保存修改

导入数据、重命名、添加曲线、调整网格、手动缩放和增删视图会标记工程已修改。
选择窗口/格子、数据质量检查和修改全局偏好不会标记测量已修改。
状态栏中的 `*` 表示未保存修改。

新建、打开另一个工程、关闭未保存文件、关闭所有文件和退出均提供
**保存 / 放弃 / 取消**。选择保存时，只有实际写入成功才继续关闭；取消路径选择、
覆盖被拒绝、写入失败都会保留当前工作区。关闭所有文件只询问一次。
关闭全部数据结束当前工程会话，避免退出时用空工作区覆盖刚保存的工程。
导出测量数据不会代替工程保存，也不会清除视图的未保存状态。

## API

```python
from interconnect_studio.io import read_project, write_project, write_touchstone2, write_citifile
from interconnect_studio.services import ExportFileType, ExportOptions, ExportService, FrequencyRange

options = ExportOptions(
    file_type=ExportFileType.TOUCHSTONE2,
    data_format="ri",
    frequency_unit="ghz",
    frequency_range=FrequencyRange(1e9, 20e9),
    port_order=(2, 0, 3, 1),
)
output = ExportService().export(network, "channel.ts", options)
```

`ProjectSnapshot` / `ProjectFile` / `ProjectWindow` 为纯 Python 领域对象；IO 不依赖 Qt。
脚本调用写出 API 时由调用者决定是否覆盖；GUI 在写入前询问实际目标文件。

设置通过 QSettings 保存；`.icprefs` 是可导入/导出的版本化 JSON，支持多套偏好文件
及恢复默认值。它与工程分开，不包含测量数据。
