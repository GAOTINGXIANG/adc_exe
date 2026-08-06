# adc_exe 项目结构分析与重构方案

## 一、现状分析

### 1.1 当前文件结构

```
adc_exe/
├── main.py              # 入口，3行有效代码
├── main_window.py       # 主窗口，1317行，严重臃肿 ⚠️
├── config.py            # 全局配置，10行
├── data_parser.py       # 数据解析，50行
├── data_state.py        # 数据状态管理，72行
├── serial_worker.py     # 串口通信，99行
├── tcp_worker.py        # TCP通信，97行
├── signals.py           # 信号定义，6行
├── localtest/           # 本地测试目录
├── 功能介绍.txt          # 需求文档（散落根目录）
├── 新增需求.txt          # 需求文档（散落根目录）
├── 交付版本裁剪说明.txt   # 交付说明（散落根目录）
├── README.md
├── README.en.md
├── LICENSE
└── __pycache__/         # 缓存文件
```

### 1.2 核心问题

| 问题 | 严重程度 | 说明 |
|---|---|---|
| `main_window.py` 单一文件过大 | 🔴 严重 | 1317行，包含UI构建、业务逻辑、设备控制、数据管理等所有内容 |
| 根目录文件杂乱 | 🟡 中等 | Python源文件、文本文档、本地测试目录混杂在一起 |
| 缺少分层架构 | 🔴 严重 | 无模块划分，所有代码平铺在根目录 |
| UI与逻辑耦合 | 🟡 中等 | UI构建代码与业务逻辑方法混在同一个类中 |
| 文档散落 | 🟢 轻微 | 功能介绍、需求文档以txt形式放在根目录 |

### 1.3 main_window.py 功能拆解（1317行）

```
┌─ MainWindow (1317行) ─────────────────────────────────────────────┐
│                                                                    │
│  📍 __init__ (80行)      ← 初始化、数据创建、信号连接、定时器        │
│                                                                    │
│  🖥️ init_ui (477行)       ← 整个UI构建，占全文件36% ⚠️              │
│     ├── 接收模式组 (串口/网络切换)                                   │
│     ├── 状态标签                                                   │
│     ├── 图表控制组 (采样点数/曲线选择/视图/滚动/匹配/暂停/网格/清除)  │
│     ├── 波形图 (pyqtgraph, 4条曲线+图例)                            │
│     ├── 工具组 (帮助/源码/导出/清缓存)                               │
│     ├── 控制组 (采样频率)                                           │
│     ├── 采样通道组 (4路选择器+自动匹配)                              │
│     ├── 温度百分比组 (4路滑块)                                      │
│     ├── 风扇与加热台组                                              │
│     ├── 温湿度组                                                   │
│     ├── 阻值计算组                                                  │
│     └── 日志组 (文本框+控制栏)                                      │
│                                                                    │
│  📡 连接管理 (~80行)                                                │
│     refresh_ports, open_connection, close_all,                    │
│     _send_channel_init, switch_mode_ui, _on_serial_lost           │
│                                                                    │
│  📊 图表管理 (~200行)                                               │
│     apply_all_plot_setting, toggle_adc1~4_display,                │
│     _on_view_changed, toggle_plot_auto_scroll, do_auto_match,     │
│     adjust_axis, toggle_chart_pause, toggle_grid,                  │
│     clear_plot_data, update_data, update_plot                     │
│                                                                    │
│  🔄 ADC通道匹配 (~140行)                                            │
│     _on_adc_ch_changed, _on_adc_auto_match_start,                 │
│     _adc_match_tick, _adc_match_done                              │
│                                                                    │
│  🎮 设备控制 (~55行)                                                │
│     send_adc_temp_percent, send_heater_cmd, send_fan_cmd,         │
│     apply_sample_freq                                             │
│                                                                    │
│  📝 日志管理 (~60行)                                                │
│     safe_add_log, clear_log_text, toggle_auto_scroll,             │
│     _on_log_max_lines_changed, toggle_log_pause                   │
│                                                                    │
│  💾 数据导出 (~35行)                                                │
│     export_data_to_csv, clear_save_data                           │
│                                                                    │
│  🔧 其他 (~55行)                                                   │
│     open_source_url, show_help_dialog, update_temp_humi_ui,       │
│     update_resistance_ui, on_sample_tick, closeEvent              │
└────────────────────────────────────────────────────────────────────┘
```

## 二、重构目标结构

### 2.1 新文件结构

```
adc_exe/
├── main.py                    # 程序入口（不变）
├── config.py                  # 全局配置（不变）
├── README.md
├── README.en.md
├── LICENSE
├── .gitignore
│
├── DOC/                       # 📁 文档目录
│   ├── architecture_analysis.md   # 本分析报告
│   ├── 功能介绍.md             # 从 功能介绍.txt 整理
│   ├── 新增需求.md             # 从 新增需求.txt 整理
│   └── 交付版本裁剪说明.md      # 从 交付版本裁剪说明.txt 整理
│
├── core/                      # 📁 核心基础设施层
│   ├── __init__.py
│   ├── signals.py             # Qt 信号定义（从根目录移入）
│   ├── data_state.py          # 线程安全数据状态管理（从根目录移入）
│   └── data_parser.py         # 数据帧解析器（从根目录移入）
│
├── workers/                   # 📁 通信工作线程层
│   ├── __init__.py
│   ├── serial_worker.py       # 串口收发线程（从根目录移入）
│   └── tcp_worker.py          # TCP 收发线程（从根目录移入）
│
├── connection/                # 📁 连接管理层
│   ├── __init__.py
│   └── connection_manager.py  # 连接/断开/模式切换/端口刷新
│
├── chart/                     # 📁 图表管理层
│   ├── __init__.py
│   └── chart_manager.py       # 曲线数据/视图切换/轴匹配/滚动/暂停/网格
│
├── device/                    # 📁 设备控制层
│   ├── __init__.py
│   ├── channel_matcher.py     # ADC采样通道四路并行自动匹配
│   └── device_controller.py   # 指令发送（温控/加热台/风扇/通道切换）
│
├── data/                      # 📁 数据管理层
│   ├── __init__.py
│   └── export_manager.py      # CSV导出 / 缓存清空
│
├── log/                       # 📁 日志管理层
│   ├── __init__.py
│   └── log_manager.py         # 日志追加/清空/暂停/缓存裁剪/滚动
│
├── ui/                        # 📁 UI 构建层
│   ├── __init__.py
│   ├── main_window.py         # 主窗口（精简至 ~150行，仅作协调器）
│   ├── left_panel.py          # 左侧面板构建（接收模式/图表控制/波形图）
│   ├── right_panel.py         # 右侧面板构建（工具/控制/通道/温控/加热台/温湿度/阻值/日志）
│   └── help_dialog.py         # 帮助弹窗组件
│
└── localtest/                 # 📁 本地测试（不变）
    └── .keep
```

### 2.2 分层架构图

```
┌──────────────────────────────────────────────────────────────────┐
│                         ui/  (UI 构建层)                          │
│  main_window.py  ←→  left_panel.py  ←→  right_panel.py          │
│                       help_dialog.py                             │
└──────────────┬───────────────────────────────────────────────────┘
               │ 使用
┌──────────────▼───────────────────────────────────────────────────┐
│    chart/        connection/      device/      data/     log/    │
│  (图表管理)      (连接管理)     (设备控制)   (数据导出)  (日志)    │
└──────────────┬───────────────────────────────────────────────────┘
               │ 依赖
┌──────────────▼───────────────────────────────────────────────────┐
│                      workers/  (通信线程层)                        │
│           serial_worker.py  ←→  tcp_worker.py                    │
└──────────────┬───────────────────────────────────────────────────┘
               │ 使用
┌──────────────▼───────────────────────────────────────────────────┐
│                       core/  (核心基础设施)                        │
│     signals.py  ←→  data_state.py  ←→  data_parser.py           │
└──────────────┬───────────────────────────────────────────────────┘
               │ 配置
┌──────────────▼───────────────────────────────────────────────────┐
│                      config.py  (全局配置)                         │
└──────────────────────────────────────────────────────────────────┘
```

**依赖规则**：上层可依赖下层，下层不依赖上层。同层模块可互相引用。

### 2.3 各模块职责与接口

#### `core/` — 核心基础设施层（不变，仅移动）

| 文件 | 原路径 | 职责 |
|---|---|---|
| `signals.py` | 根目录 | `Signals(QObject)` — 定义 `log` 和 `serial_lost` 两个信号 |
| `data_state.py` | 根目录 | `DataState` — 线程安全的状态存储，提供 `get/set` API |
| `data_parser.py` | 根目录 | `DataParser` — 静态方法解析 `ADC1:1234` 等文本帧 |

#### `workers/` — 通信线程层（不变，仅移动）

| 文件 | 职责 |
|---|---|
| `serial_worker.py` | `SerialWorker` — 串口连接/收发/断线检测，依赖 `Signals` + `DataState` + `DataParser` |
| `tcp_worker.py` | `TcpWorker` — TCP连接/收发，依赖 `Signals` + `DataState` + `DataParser` |

#### `connection/connection_manager.py` — 连接管理（新增）

**拆出方法**：`refresh_ports`, `open_connection`, `close_all`, `_send_channel_init`, `switch_mode_ui`, `_on_serial_lost`

**对外接口**：
```python
class ConnectionManager:
    def __init__(self, signals, state, serial_worker, tcp_worker, status_cb, ...)
    def refresh_ports() -> list
    def open_connection(is_uart, port, ip, port_tcp)
    def close_all()
    def is_connected() -> bool
    def get_mode() -> str  # 'uart' | 'net'
    def send_command(cmd_str) -> bool
```

#### `chart/chart_manager.py` — 图表管理（新增）

**拆出方法**：图表数据管理 + 图表控制 + 采样刷新

**对外接口**：
```python
class ChartManager:
    def __init__(self, signals, state, plot_widget, curves, ...)
    def update_data(channel, val)
    def update_plot()
    def clear_data()
    def set_view_mode(mode)  # 'adc' | 'resistance'
    def toggle_curve(idx, visible)
    def set_auto_scroll(enabled)
    def auto_match_axis()
    def toggle_grid(enabled)
    def set_paused(paused)
    def apply_point_count(n)
    def get_resistance_values() -> tuple  # 供右面板阻值显示
```

#### `device/channel_matcher.py` — 通道匹配（新增）

**拆出方法**：`_on_adc_ch_changed`, `_on_adc_auto_match_start`, `_adc_match_tick`, `_adc_match_done`

**对外接口**：
```python
class ChannelMatcher:
    def __init__(self, signals, state, send_callback, ...)
    def on_channel_changed(adc_idx, channel_val)
    def start_auto_match(range_low, range_high, delay_ms)
    def stop()
    def is_running() -> bool
```

#### `device/device_controller.py` — 设备控制（新增）

**对外接口**：
```python
class DeviceController:
    def __init__(self, connection_manager)
    def send_temp_percent(adc_idx, percent)
    def send_heater_cmd(on_off)
    def send_fan_cmd(on_off)
    def send_channel_cmd(adc_idx, channel)
```

#### `data/export_manager.py` — 数据导出（新增）

**对外接口**：
```python
class ExportManager:
    def __init__(self, state, signals, parent_widget)
    def export_to_csv()
    def clear_cache()
```

#### `log/log_manager.py` — 日志管理（新增）

**对外接口**：
```python
class LogManager:
    def __init__(self, signals, log_text_widget)
    def add_log(msg)
    def clear()
    def set_auto_scroll(enabled)
    def set_max_lines(n)
    def set_paused(paused)
```

#### `ui/left_panel.py` — 左侧面板（新增）

构建以下 UI 组件并返回 layout/widget：
- 接收模式组 (mode_group)：串口/网络 Radio、COM口下拉、IP/端口输入、连接/断开按钮
- 状态标签 (status_label)
- 图表控制组 (plot_control_group)：采样点数、曲线选择按钮(T1/T2/M1/M2)、视图切换、自动滚动、自动匹配、暂停、清除、网格
- 波形图 (plot_widget)：pyqtgraph PlotWidget + 4条曲线 + 图例

#### `ui/right_panel.py` — 右侧面板（新增）

构建以下 UI 组件并返回 layout/widget：
- 工具组：帮助、源码、导出CSV、清空缓存
- 控制组：采样频率输入
- 采样通道组：4路 SpinBox (0-6) + 范围/延迟/自动匹配按钮
- 温度百分比组：4路 Slider (0-100%) + 发送按钮
- 风扇与加热台组：开关按钮
- 温湿度组：标签显示
- 阻值计算组：4路阻值标签
- 日志组：QTextEdit + 控制栏（缓存条数/暂停/自动滚动/清空）

#### `ui/help_dialog.py` — 帮助弹窗（新增）

独立的 `HelpDialog(QDialog)` 类。

#### `ui/main_window.py` — 主窗口（精简重构）

```python
class MainWindow(QMainWindow):
    def __init__(self):
        # 1. 核心层初始化
        self.sig = Signals()
        self.state = DataState()
        
        # 2. 通信层初始化
        self.serial_worker = SerialWorker(self.sig, self.state)
        self.tcp_worker = TcpWorker(self.sig, self.state)
        
        # 3. 管理层初始化（依赖核心层 + 通信层）
        self.conn_mgr = ConnectionManager(...)
        self.chart_mgr = ChartManager(...)
        self.device_ctrl = DeviceController(self.conn_mgr)
        self.channel_matcher = ChannelMatcher(...)
        self.log_mgr = LogManager(...)
        self.export_mgr = ExportManager(...)
        
        # 4. UI 层初始化（依赖管理层）
        left = LeftPanelBuilder.build(self, ...)
        right = RightPanelBuilder.build(self, ...)
        
        # 5. 组合布局
        main_layout = QHBoxLayout()
        main_layout.addLayout(left, stretch=5)
        main_layout.addLayout(right, stretch=2)
        
        # 6. 定时器
        self.setup_timers()
    
    # 仅保留跨模块协调方法：
    def on_sample_tick(self)       # 采样回调 → chart_mgr + log_mgr
    def update_temp_humi_ui(self)  # 温湿度刷新
    def update_resistance_ui(self) # 阻值刷新
    def closeEvent(self, event)    # 窗口关闭清理
```

## 三、模块依赖矩阵

```
                     core    workers  conn  chart  device  data  log   ui
core/signals          -        ✓       ✓     ✓      ✓      ✓     ✓    ✓
core/data_state       -        ✓       -     ✓      ✓      ✓     -    -
core/data_parser      -        ✓       -     -      -      -     -    -
workers/*             ✓        -       ✓     -      -      -     -    -
connection/           ✓        ✓       -     -      ✓      -     -    ✓
chart/                ✓        -       -     -      -      -     -    ✓
device/channel_match  ✓        -       ✓     -      -      -     -    ✓
device/ctrl           -        -       ✓     -      -      -     -    ✓
data/export           ✓        -       -     -      -      -     -    ✓
log/                  ✓        -       -     -      -      -     -    ✓
ui/*                  ✓        -       ✓     ✓      ✓      ✓     ✓    -
```

## 四、迁移步骤

### 阶段一：基础文件移动（零风险）
1. 移动 `signals.py` → `core/signals.py`
2. 移动 `data_state.py` → `core/data_state.py`
3. 移动 `data_parser.py` → `core/data_parser.py`
4. 移动 `serial_worker.py` → `workers/serial_worker.py`
5. 移动 `tcp_worker.py` → `workers/tcp_worker.py`
6. 整理文档到 `DOC/` 目录
7. 验证：运行 `python main.py` 确认程序正常

### 阶段二：功能模块拆分（逐个提取）
8. 创建 `log/log_manager.py`
9. 创建 `data/export_manager.py`
10. 创建 `device/device_controller.py`
11. 创建 `device/channel_matcher.py`
12. 创建 `chart/chart_manager.py`
13. 创建 `connection/connection_manager.py`

### 阶段三：UI 拆分（最后一步）
14. 创建 `ui/help_dialog.py`
15. 创建 `ui/left_panel.py`
16. 创建 `ui/right_panel.py`
17. 重构 `ui/main_window.py` 集成所有模块

### 阶段四：入口更新
18. 更新 `main.py` 的 import 路径
19. 最终验证：全功能测试

## 五、风险评估与注意事项

| 风险 | 缓解措施 |
|---|---|
| PyQt5 信号连接断裂 | 重构后逐一测试每个按钮/控件的响应 |
| 循环导入 | 遵循分层依赖规则，上层导入下层 |
| 线程安全问题 | DataState 已有 `threading.Lock`，保持不变 |
| UI 控件引用丢失 | LeftPanel/RightPanel 通过返回值暴露控件引用 |

### 重构原则
1. **功能不变**：纯结构重构，不修改任何业务逻辑
2. **逐模块验证**：每完成一个模块立即 `python main.py` 验证
3. **保持 git 历史**：使用 `git mv` 移动文件
4. **import 兼容**：统一使用 `from core.xxx import YYY` 风格的绝对导入
