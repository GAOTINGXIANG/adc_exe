import csv
import os
from datetime import datetime

import pyqtgraph as pg
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QGroupBox, QRadioButton, QLabel, QComboBox, QPushButton, QLineEdit,
    QSlider, QTextEdit, QCheckBox, QDialog, QMessageBox, QFileDialog,
    QSpinBox
)
from PyQt5.QtCore import QTimer, Qt, QUrl
from PyQt5.QtGui import QDesktopServices

from config import (
    BAUD_RATE, MAX_DATA_POINTS_DEFAULT, MAX_LOG_LINES,
    TCP_SERVER_IP, TCP_SERVER_PORT
)
from signals import Signals
from data_state import DataState
from serial_worker import SerialWorker
from tcp_worker import TcpWorker


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("氨气检测-ESP32")
        self.setGeometry(100, 100, 1200, 720)

        # 图表参数
        self.max_data_points = MAX_DATA_POINTS_DEFAULT

        # 图表数据 - 4路ADC
        self.data_x = list(range(self.max_data_points))
        self.data_y1 = [0] * self.max_data_points
        self.data_y2 = [0] * self.max_data_points
        self.data_y3 = [0] * self.max_data_points
        self.data_y4 = [0] * self.max_data_points

        # 图表数据 - 4路阻值（用于阻值视图）
        self.data_r1 = [0] * self.max_data_points
        self.data_r2 = [0] * self.max_data_points
        self.data_r3 = [0] * self.max_data_points
        self.data_r4 = [0] * self.max_data_points

        # 视图模式：False=ADC视图, True=阻值视图
        self.resistance_view = False

        # 曲线显示状态，默认全部显示
        self.adc1_visible = True
        self.adc2_visible = True
        self.adc3_visible = True
        self.adc4_visible = True

        # 自动滚动状态
        self.plot_auto_scroll = False

        # 采样频率（Hz），默认1Hz
        self.sample_freq = 1.0
        self.sample_timer = None
        self.chart_paused = False  # 图表暂停标志
        self.log_paused = False    # 日志暂停标志

        # 共享状态与信号
        self.sig = Signals()
        self.state = DataState()

        # 串口/网络工作线程
        self.serial_worker = SerialWorker(self.sig, self.state)
        self.tcp_worker = TcpWorker(self.sig, self.state)

        # 日志自动滚动标记，默认开启
        self.auto_scroll_log = True
        # 日志最大缓存条数
        self.max_log_lines = MAX_LOG_LINES

        # ADC通道自动匹配状态
        self.adc_match_running = False
        self.adc_match_timer = QTimer()
        self.adc_match_timer.timeout.connect(self._adc_match_tick)
        self.match_state = {}

        # 信号连接
        self.sig.log.connect(self.safe_add_log)
        self.sig.serial_lost.connect(self._on_serial_lost)

        # UI
        self.init_ui()

        # 刷新图表定时器
        self.plot_timer = QTimer()
        self.plot_timer.timeout.connect(self.update_plot)
        self.plot_timer.start(50)

        # 采样定时器（按设定频率读取ADC并刷新曲线/日志）
        self.sample_timer = QTimer()
        self.sample_timer.timeout.connect(self.on_sample_tick)
        self.sample_timer.start(int(1000 / self.sample_freq))

        # 模拟温湿度刷新定时器
        self.env_timer = QTimer()
        self.env_timer.timeout.connect(self.update_temp_humi_ui)
        self.env_timer.start(1000)

    # ===================== 打开源码地址 =====================
    def open_source_url(self):
        QDesktopServices.openUrl(QUrl("https://gitee.com/GAOTINGXIANG/adc_exe"))

    # ===================== 帮助弹窗 =====================
    def show_help_dialog(self):
        help_text = """
ESP32 双模式上位机 使用说明

1. 连接模式
   • 串口接收：选择COM口，点击连接，波特率115200
   • 网络接收：输入服务器IP和端口，点击连接

2. 数据显示
   • 实时波形：显示4路传感器 0~4095采样值曲线（红/蓝/紫/绿）
   • 温湿度：自动解析TEM/HUM数据并显示
   • 日志区：显示接收、发送、连接状态信息

3. 图表控制
   • 采样点数：调整横轴数据总量，调整时保留已有数据的连续性
   • 曲线选择：点击按钮切换显示/隐藏对应曲线（T1=红色, T2=蓝色, M1=紫色, M2=绿色）
   • 自动滚动：开启后曲线随新数据自动向右滚动
   • 自动匹配：点击一次，自动调整X/Y轴范围以适配当前数据
   • 清除图表：清空图表中所有历史数据

4. 控制功能
   • 采样频率：设置上位机采样刷新频率（HZ/S），默认1Hz
   • 风扇控制：点击开/关，通过串口发送指令
   • 采样通道：每路传感器可选0-6通道，对应电阻：10K/100K/1M/10M/100M/1G/10G
   • 温度百分比：每路传感器独立设置0~100%，点击发送
   • 加热台控制：点击开/关，通过串口发送指令

5. 数据格式（设备端需发送）
   • ADC1:1234
   • ADC2:1234
   • ADC3:1234
   • ADC4:1234
   • TEM:25.5
   • HUM:60.2

6. 日志功能
   • 清空日志：一键清理所有日志
   • 自动滚动：开启时新日志自动滚动到底部，关闭可翻阅历史

7. 数据功能
   • 导出CSV：保存采集的时间、4路传感器、温湿度数据
8. 答疑邮箱
    1913000981@qq.com
9.开源网址
    https://gitee.com/GAOTINGXIANG/adc_exe
        """
        dialog = QDialog(self)
        dialog.setWindowTitle("使用帮助")
        dialog.setFixedSize(550, 450)
        layout = QVBoxLayout()
        text_edit = QTextEdit()
        text_edit.setReadOnly(True)
        text_edit.setText(help_text)
        text_edit.setStyleSheet("font-size: 11pt;")
        close_btn = QPushButton("关闭")
        close_btn.clicked.connect(dialog.close)
        layout.addWidget(text_edit)
        layout.addWidget(close_btn)
        dialog.setLayout(layout)
        dialog.exec_()

    # ===================== 图表参数应用（保留数据连续性） =====================
    def apply_all_plot_setting(self):
        try:
            x_points = int(self.x_point_input.text())
            if x_points < 10:
                QMessageBox.warning(self, "参数错误", "采样点数不能小于10！")
                return

            old_n = self.max_data_points
            new_n = x_points

            if new_n > old_n:
                # 新点数更大：前面补零，旧数据保留在末尾（保证最新数据位置不变）
                prepend_n = new_n - old_n
                self.data_y1 = [0] * prepend_n + self.data_y1
                self.data_y2 = [0] * prepend_n + self.data_y2
                self.data_y3 = [0] * prepend_n + self.data_y3
                self.data_y4 = [0] * prepend_n + self.data_y4
                self.data_r1 = [0] * prepend_n + self.data_r1
                self.data_r2 = [0] * prepend_n + self.data_r2
                self.data_r3 = [0] * prepend_n + self.data_r3
                self.data_r4 = [0] * prepend_n + self.data_r4
            elif new_n < old_n:
                # 新点数更小：保留末尾最新的数据
                self.data_y1 = self.data_y1[-new_n:]
                self.data_y2 = self.data_y2[-new_n:]
                self.data_y3 = self.data_y3[-new_n:]
                self.data_y4 = self.data_y4[-new_n:]
                self.data_r1 = self.data_r1[-new_n:]
                self.data_r2 = self.data_r2[-new_n:]
                self.data_r3 = self.data_r3[-new_n:]
                self.data_r4 = self.data_r4[-new_n:]

            # 重新生成X轴坐标，保持连续整数
            self.data_x = list(range(new_n))
            self.max_data_points = new_n

            self.update_plot()
            self.sig.log.emit(f"图表设置已生效 | X点数:{x_points}")
        except ValueError:
            QMessageBox.warning(self, "输入错误", "请输入合法数字！")

    # ===================== ADC显示切换 =====================
    def toggle_adc1_display(self):
        self.adc1_visible = not self.adc1_visible
        self.adc1_btn.setChecked(self.adc1_visible)
        self.curve1.setVisible(self.adc1_visible)

    def toggle_adc2_display(self):
        self.adc2_visible = not self.adc2_visible
        self.adc2_btn.setChecked(self.adc2_visible)
        self.curve2.setVisible(self.adc2_visible)

    def toggle_adc3_display(self):
        self.adc3_visible = not self.adc3_visible
        self.adc3_btn.setChecked(self.adc3_visible)
        self.curve3.setVisible(self.adc3_visible)

    def toggle_adc4_display(self):
        self.adc4_visible = not self.adc4_visible
        self.adc4_btn.setChecked(self.adc4_visible)
        self.curve4.setVisible(self.adc4_visible)

    # ===================== 视图切换 =====================
    def _on_view_changed(self, index):
        """切换ADC视图/阻值视图"""
        self.resistance_view = (index == 1)
        if self.resistance_view:
            self.plot_widget.setLabel("left", "Resistance")
            self.plot_widget.setYRange(0, 1)  # 先重置，自动匹配后可调整
            self.curve1.setData(self.data_x, self.data_r1)
            self.curve2.setData(self.data_x, self.data_r2)
            self.curve3.setData(self.data_x, self.data_r3)
            self.curve4.setData(self.data_x, self.data_r4)
            self.sig.log.emit("已切换至阻值视图")
        else:
            self.plot_widget.setLabel("left", "ADC Value")
            self.plot_widget.setYRange(0, 4095)
            self.curve1.setData(self.data_x, self.data_y1)
            self.curve2.setData(self.data_x, self.data_y2)
            self.curve3.setData(self.data_x, self.data_y3)
            self.curve4.setData(self.data_x, self.data_y4)
            self.sig.log.emit("已切换至ADC视图")
        self.adjust_axis()

    # ===================== 自动滚动切换 =====================
    def toggle_plot_auto_scroll(self):
        self.plot_auto_scroll = not self.plot_auto_scroll
        self.auto_scroll_btn.setChecked(self.plot_auto_scroll)
        if self.plot_auto_scroll:
            self.sig.log.emit("图表自动滚动已开启")
        else:
            self.sig.log.emit("图表自动滚动已关闭")

    # ===================== 自动匹配（单次点击触发） =====================
    def do_auto_match(self):
        self.adjust_axis()
        self.sig.log.emit("已执行图表自动匹配")

    # ===================== 图表/日志独立暂停 =====================
    def toggle_chart_pause(self, checked):
        """暂停/恢复图表曲线刷新"""
        if checked:
            self.chart_paused = True
            self.chart_pause_btn.setText("图表 ⏸")
            self.chart_pause_btn.setStyleSheet("background-color: #dc3545; color: white;")
            self.sig.log.emit("⏸ 图表已暂停")
        else:
            self.chart_paused = False
            self.chart_pause_btn.setText("图表 ▶")
            self.chart_pause_btn.setStyleSheet("background-color: #28a745; color: white;")
            self.sig.log.emit("▶ 图表已恢复")

    def toggle_log_pause(self, checked):
        """暂停/恢复日志输出"""
        if checked:
            self.log_paused = True
            self.log_pause_btn.setText("日志 ⏸")
            self.log_pause_btn.setStyleSheet("background-color: #dc3545; color: white;")
            self.sig.log.emit("⏸ 日志已暂停（手动操作日志除外）")
        else:
            self.log_paused = False
            self.log_pause_btn.setText("日志 ▶")
            self.log_pause_btn.setStyleSheet("background-color: #28a745; color: white;")
            self.sig.log.emit("▶ 日志已恢复")

    # ===================== X/Y轴自动匹配（以最新数据为焦点） =====================
    def adjust_axis(self):
        n = self.max_data_points
        if n == 0:
            return

        # 从末尾向前找最后一个有实际数据（非零）的位置
        last_data_idx = -1
        for i in range(n - 1, -1, -1):
            v1 = self.data_y1[i] if self.adc1_visible else 0
            v2 = self.data_y2[i] if self.adc2_visible else 0
            v3 = self.data_y3[i] if self.adc3_visible else 0
            v4 = self.data_y4[i] if self.adc4_visible else 0
            if v1 != 0 or v2 != 0 or v3 != 0 or v4 != 0:
                last_data_idx = i
                break

        if last_data_idx < 0:
            return

        # 以最新数据为焦点，取最近窗口的 data 个点进行Y轴幅值匹配
        window_start = max(0, last_data_idx - self.max_data_points + 1)
        visible_data = []
        for i in range(window_start, last_data_idx + 1):
            if self.adc1_visible:
                visible_data.append(self.data_y1[i])
            if self.adc2_visible:
                visible_data.append(self.data_y2[i])
            if self.adc3_visible:
                visible_data.append(self.data_y3[i])
            if self.adc4_visible:
                visible_data.append(self.data_y4[i])

        if not visible_data:
            return

        # Y轴自动匹配幅值
        min_val = min(visible_data)
        max_val = max(visible_data)
        range_val = max_val - min_val

        margin = range_val * 0.1 if range_val > 0 else 100
        y_min = max(0, min_val - margin)
        y_max = min(4095, max_val + margin)

        if y_min == y_max:
            y_min = max(0, y_min - 100)
            y_max = min(4095, y_max + 100)

        self.plot_widget.setYRange(y_min, y_max)

        # X轴自动匹配步长：以最新数据为右端点，展示最近窗口
        # 从第一个有数据的点开始到最新数据点
        first_data_idx = -1
        for i in range(n):
            v1 = self.data_y1[i] if self.adc1_visible else 0
            v2 = self.data_y2[i] if self.adc2_visible else 0
            v3 = self.data_y3[i] if self.adc3_visible else 0
            v4 = self.data_y4[i] if self.adc4_visible else 0
            if v1 != 0 or v2 != 0 or v3 != 0 or v4 != 0:
                first_data_idx = i
                break

        if first_data_idx >= 0 and first_data_idx < last_data_idx:
            x_min = self.data_x[first_data_idx]
            x_max = self.data_x[last_data_idx]
            # 两边各留一点余量
            span = x_max - x_min
            margin_x = span * 0.02
            self.plot_widget.setXRange(x_min - margin_x, x_max + margin_x)

    # ===================== 日志自动滚动 =====================
    def toggle_auto_scroll(self, checked):
        self.auto_scroll_log = checked

    def _on_log_max_lines_changed(self, val):
        """日志缓存条数变更"""
        self.max_log_lines = val
        # 立即裁剪当前日志
        lines = self.log_text.toPlainText().splitlines()
        if len(lines) > val:
            lines = lines[-val:]
            self.log_text.setPlainText("\n".join(lines))

    # ===================== UI 初始化 =====================
    def init_ui(self):
        # ========== 顶部整体水平布局：帮助按钮 + 接收模式组 ==========
        top_total_layout = QHBoxLayout()
        top_total_layout.setContentsMargins(0, 0, 0, 0)
        top_total_layout.setSpacing(15)

        # 接收模式组
        self.mode_group = QGroupBox("接收模式")
        self.net_radio = QRadioButton("网络接收")
        self.uart_radio = QRadioButton("串口接收")
        self.uart_radio.setChecked(True)

        self.port_label = QLabel("COM口:")
        self.port_combo = QComboBox()
        self.refresh_btn = QPushButton("刷新串口")
        self.connect_btn = QPushButton("连接")
        self.disconnect_btn = QPushButton("断开")

        # 网络模式 IP 端口输入
        self.ip_label = QLabel("服务器IP:")
        self.ip_input = QLineEdit(TCP_SERVER_IP)
        self.port_tcp_label = QLabel("端口:")
        self.port_tcp_input = QLineEdit(str(TCP_SERVER_PORT))

        self.refresh_btn.clicked.connect(self.refresh_ports)
        self.connect_btn.clicked.connect(self.open_connection)
        self.disconnect_btn.clicked.connect(self.close_all)
        self.net_radio.toggled.connect(self.switch_mode_ui)

        # 模式行布局压缩紧凑
        mode_layout = QHBoxLayout()
        mode_layout.setContentsMargins(8, 6, 8, 6)
        mode_layout.setSpacing(8)
        mode_layout.addWidget(self.net_radio)
        mode_layout.addWidget(self.uart_radio)
        mode_layout.addWidget(self.port_label)
        mode_layout.addWidget(self.port_combo)
        mode_layout.addWidget(self.ip_label)
        mode_layout.addWidget(self.ip_input)
        mode_layout.addWidget(self.port_tcp_label)
        mode_layout.addWidget(self.port_tcp_input)
        mode_layout.addWidget(self.refresh_btn)
        mode_layout.addWidget(self.connect_btn)
        mode_layout.addWidget(self.disconnect_btn)
        self.mode_group.setLayout(mode_layout)

        top_total_layout.addWidget(self.mode_group)

        # ========== 状态标签 ==========
        self.status_label = QLabel("状态：未连接")
        font = self.status_label.font()
        font.setPointSize(11)
        self.status_label.setFont(font)

        # ========== 图表控制区域（采样点数 + ADC选择 + 自动滚动 + 自动匹配） ==========
        plot_control_group = QGroupBox("图表控制")
        plot_control_layout = QHBoxLayout()
        plot_control_layout.setContentsMargins(10, 5, 10, 5)
        plot_control_layout.setSpacing(10)

        # 采样点数
        plot_control_layout.addWidget(QLabel("采样点数:"))
        self.x_point_input = QLineEdit(str(self.max_data_points))
        self.x_point_input.setFixedWidth(60)
        plot_control_layout.addWidget(self.x_point_input)

        self.apply_plot_btn = QPushButton("应用设置")
        self.apply_plot_btn.setFixedWidth(80)
        self.apply_plot_btn.clicked.connect(self.apply_all_plot_setting)
        plot_control_layout.addWidget(self.apply_plot_btn)

        plot_control_layout.addSpacing(20)

        # 曲线选择按钮
        self.adc1_btn = QPushButton("T1")
        self.adc1_btn.setCheckable(True)
        self.adc1_btn.setChecked(True)
        self.adc1_btn.setStyleSheet("background-color: red; color: white;")
        self.adc1_btn.clicked.connect(self.toggle_adc1_display)

        self.adc2_btn = QPushButton("T2")
        self.adc2_btn.setCheckable(True)
        self.adc2_btn.setChecked(True)
        self.adc2_btn.setStyleSheet("background-color: blue; color: white;")
        self.adc2_btn.clicked.connect(self.toggle_adc2_display)

        self.adc3_btn = QPushButton("M1")
        self.adc3_btn.setCheckable(True)
        self.adc3_btn.setChecked(True)
        self.adc3_btn.setStyleSheet("background-color: purple; color: white;")
        self.adc3_btn.clicked.connect(self.toggle_adc3_display)

        self.adc4_btn = QPushButton("M2")
        self.adc4_btn.setCheckable(True)
        self.adc4_btn.setChecked(True)
        self.adc4_btn.setStyleSheet("background-color: green; color: white;")
        self.adc4_btn.clicked.connect(self.toggle_adc4_display)

        plot_control_layout.addWidget(QLabel("曲线选择:"))
        plot_control_layout.addWidget(self.adc1_btn)
        plot_control_layout.addWidget(self.adc2_btn)
        plot_control_layout.addWidget(self.adc3_btn)
        plot_control_layout.addWidget(self.adc4_btn)

        plot_control_layout.addStretch()

        # 视图切换
        plot_control_layout.addWidget(QLabel("视图:"))
        self.view_combo = QComboBox()
        self.view_combo.addItems(["ADC视图", "阻值视图"])
        self.view_combo.setFixedWidth(90)
        self.view_combo.currentIndexChanged.connect(self._on_view_changed)
        plot_control_layout.addWidget(self.view_combo)

        # 自动滚动按钮
        self.auto_scroll_btn = QPushButton("自动滚动")
        self.auto_scroll_btn.setCheckable(True)
        self.auto_scroll_btn.setChecked(False)
        self.auto_scroll_btn.setFixedWidth(80)
        self.auto_scroll_btn.clicked.connect(self.toggle_plot_auto_scroll)
        plot_control_layout.addWidget(self.auto_scroll_btn)

        # 自动匹配按钮
        self.auto_match_btn = QPushButton("自动匹配")
        self.auto_match_btn.setFixedWidth(80)
        self.auto_match_btn.clicked.connect(self.do_auto_match)
        plot_control_layout.addWidget(self.auto_match_btn)

        # 图表暂停按钮（绿色=运行中）
        self.chart_pause_btn = QPushButton("图表 ▶")
        self.chart_pause_btn.setCheckable(True)
        self.chart_pause_btn.setChecked(False)
        self.chart_pause_btn.setFixedWidth(70)
        self.chart_pause_btn.setStyleSheet("background-color: #28a745; color: white;")
        self.chart_pause_btn.clicked.connect(self.toggle_chart_pause)
        plot_control_layout.addWidget(self.chart_pause_btn)

        # 清除图表按钮
        self.clear_plot_btn = QPushButton("清除图表")
        self.clear_plot_btn.setFixedWidth(80)
        self.clear_plot_btn.clicked.connect(self.clear_plot_data)
        plot_control_layout.addWidget(self.clear_plot_btn)

        # 网格按钮
        self.grid_btn = QPushButton("网格")
        self.grid_btn.setCheckable(True)
        self.grid_btn.setChecked(False)
        self.grid_btn.setFixedWidth(60)
        self.grid_btn.clicked.connect(self.toggle_grid)
        plot_control_layout.addWidget(self.grid_btn)

        plot_control_group.setLayout(plot_control_layout)

        # ========== 波形图 ==========
        self.plot_widget = pg.PlotWidget()
        self.plot_widget.setTitle("实时波形", color="w", size="14pt")
        self.plot_widget.setLabel("left", "ADC Value")
        self.plot_widget.setLabel("bottom", "Points")
        self.plot_widget.setYRange(0, 4095)

        # 4条曲线，颜色分别为红色、蓝色、紫色、绿色
        self.curve1 = self.plot_widget.plot(
            self.data_x, self.data_y1,
            pen=pg.mkPen(color="red", width=2),
            symbol="o", symbolSize=4, symbolBrush="red",
            name="T1"
        )
        self.curve2 = self.plot_widget.plot(
            self.data_x, self.data_y2,
            pen=pg.mkPen(color="blue", width=2),
            symbol="o", symbolSize=4, symbolBrush="blue",
            name="T2"
        )
        self.curve3 = self.plot_widget.plot(
            self.data_x, self.data_y3,
            pen=pg.mkPen(color="purple", width=2),
            symbol="o", symbolSize=4, symbolBrush="purple",
            name="M1"
        )
        self.curve4 = self.plot_widget.plot(
            self.data_x, self.data_y4,
            pen=pg.mkPen(color="green", width=2),
            symbol="o", symbolSize=4, symbolBrush="green",
            name="M2"
        )

        # 添加图例
        self.plot_widget.addLegend()

        # ========== 右侧布局 ==========
        self.right_layout = QVBoxLayout()
        self.right_layout.setSpacing(10)
        self.right_layout.setContentsMargins(5, 5, 5, 5)

        # 工具组
        self.tool_group = QGroupBox("工具")
        self.help_btn = QPushButton("说明")
        self.source_btn = QPushButton("源码")
        self.export_btn = QPushButton("导出CSV数据")
        self.clear_data_btn = QPushButton("清空缓存数据")

        self.help_btn.setFixedSize(70, 26)
        self.source_btn.setFixedSize(70, 26)
        self.help_btn.clicked.connect(self.show_help_dialog)
        self.source_btn.clicked.connect(self.open_source_url)
        self.export_btn.clicked.connect(self.export_data_to_csv)
        self.clear_data_btn.clicked.connect(self.clear_save_data)

        tool_layout = QHBoxLayout()
        tool_layout.addWidget(self.help_btn)
        tool_layout.addWidget(self.source_btn)
        tool_layout.addWidget(self.export_btn)
        tool_layout.addWidget(self.clear_data_btn)
        self.tool_group.setLayout(tool_layout)

        # 1. 控制（采样频率 + 风扇，同一行）
        self.ctrl_group = QGroupBox("控制")
        ctrl_layout = QHBoxLayout()
        ctrl_layout.setSpacing(10)

        # 采样频率
        self.sample_freq_label = QLabel("频率(HZ/S):")
        self.sample_freq_input = QLineEdit()
        self.sample_freq_input.setText("1.0")
        self.sample_freq_input.setFixedWidth(60)
        self.sample_freq_apply_btn = QPushButton("应用")
        self.sample_freq_apply_btn.setFixedWidth(50)
        self.sample_freq_apply_btn.clicked.connect(self.apply_sample_freq)

        ctrl_layout.addWidget(self.sample_freq_label)
        ctrl_layout.addWidget(self.sample_freq_input)
        ctrl_layout.addWidget(self.sample_freq_apply_btn)
        ctrl_layout.addStretch()

        self.ctrl_group.setLayout(ctrl_layout)

        # 2. 采样通道选择（2x2布局）+ 自动匹配
        self.adc_ch_group = QGroupBox("采样通道")
        self.adc_ch_labels = {}
        self.adc_ch_spins = {}
        channel_names = ["10K", "100K", "1M", "10M", "100M", "1G", "10G"]
        hw_names = {1: 'T1', 2: 'T2', 3: 'M1', 4: 'M2'}

        # 左侧：ADC通道选择网格
        adc_ch_grid = QVBoxLayout()
        adc_ch_grid.setSpacing(6)

        for row in range(2):
            row_layout = QHBoxLayout()
            row_layout.setSpacing(10)
            for col in range(2):
                i = row * 2 + col + 1
                spin = QSpinBox()
                spin.setRange(0, 6)
                spin.setValue(0)
                spin.setFixedWidth(100)
                spin.setSuffix(f"  ({channel_names[0]})")
                spin.valueChanged.connect(lambda val, idx=i, sp=spin: self._on_adc_ch_changed(idx, val, sp))
                label = QLabel(f"{hw_names[i]}:")
                self.adc_ch_spins[i] = spin
                self.adc_ch_labels[i] = label
                row_layout.addWidget(label)
                row_layout.addWidget(spin)
            row_layout.addStretch()
            adc_ch_grid.addLayout(row_layout)

        # 底部：ADC范围 + 自动匹配按钮（与四路通道对齐）
        adc_match_row = QHBoxLayout()
        adc_match_row.setSpacing(6)
        adc_match_row.addWidget(QLabel("范围:"))
        self.adc_range_low_spin = QSpinBox()
        self.adc_range_low_spin.setRange(0, 4095)
        self.adc_range_low_spin.setValue(100)
        self.adc_range_low_spin.setFixedWidth(65)
        adc_match_row.addWidget(self.adc_range_low_spin)
        adc_match_row.addWidget(QLabel("~"))
        self.adc_range_high_spin = QSpinBox()
        self.adc_range_high_spin.setRange(0, 4095)
        self.adc_range_high_spin.setValue(4000)
        self.adc_range_high_spin.setFixedWidth(65)
        adc_match_row.addWidget(self.adc_range_high_spin)
        adc_match_row.addWidget(QLabel("  延迟:"))
        self.adc_delay_spin = QSpinBox()
        self.adc_delay_spin.setRange(10, 500)
        self.adc_delay_spin.setValue(20)
        self.adc_delay_spin.setSuffix("ms")
        self.adc_delay_spin.setFixedWidth(70)
        adc_match_row.addWidget(self.adc_delay_spin)
        self.adc_auto_match_btn = QPushButton("自动匹配")
        self.adc_auto_match_btn.setFixedWidth(80)
        self.adc_auto_match_btn.clicked.connect(self._on_adc_auto_match_start)
        adc_match_row.addWidget(self.adc_auto_match_btn)
        adc_match_row.addStretch()

        # 分组框内部垂直排列：上方通道网格 + 下方匹配控件行
        adc_ch_inner = QVBoxLayout()
        adc_ch_inner.addLayout(adc_ch_grid)
        adc_ch_inner.addLayout(adc_match_row)
        self.adc_ch_group.setLayout(adc_ch_inner)

        # 3. 温度百分比控制（2x2布局）
        self.adc_temp_group = QGroupBox("温度百分比")
        self.adc_temp_sliders = {}
        self.adc_temp_labels = {}
        adc_temp_layout = QVBoxLayout()
        adc_temp_layout.setSpacing(8)

        for row in range(2):
            row_layout = QHBoxLayout()
            row_layout.setSpacing(10)
            for col in range(2):
                i = row * 2 + col + 1
                col_widget = QWidget()
                col_layout = QVBoxLayout(col_widget)
                col_layout.setContentsMargins(0, 0, 0, 0)
                col_layout.setSpacing(2)

                slider = QSlider(Qt.Horizontal)
                slider.setRange(0, 100)
                slider.setValue(50)
                label = QLabel(f"{hw_names[i]}：50 %")

                btn_row = QHBoxLayout()
                btn_row.addWidget(label)
                btn_row.addStretch()
                send_btn = QPushButton("发送")
                send_btn.setFixedSize(55, 22)
                send_btn.setStyleSheet("font-size:9pt; padding:1px;")
                send_btn.clicked.connect(lambda checked=False, idx=i, sl=slider: self.send_adc_temp_percent(idx, sl))
                btn_row.addWidget(send_btn)

                slider.valueChanged.connect(lambda val, idx=i, lb=label: lb.setText(f"{hw_names[idx]}：{val} %"))

                col_layout.addWidget(slider)
                col_layout.addLayout(btn_row)

                self.adc_temp_sliders[i] = slider
                self.adc_temp_labels[i] = label
                row_layout.addWidget(col_widget)
            adc_temp_layout.addLayout(row_layout)

        self.adc_temp_group.setLayout(adc_temp_layout)

        # 4. 风扇与加热台开关
        self.heater_group = QGroupBox("风扇与加热台控制")
        heater_layout = QHBoxLayout()
        heater_layout.setSpacing(10)

        self.heater_label = QLabel("加热台:")
        self.heater_on_btn = QPushButton("开")
        self.heater_off_btn = QPushButton("关")
        self.heater_on_btn.setFixedWidth(50)
        self.heater_off_btn.setFixedWidth(50)
        self.heater_on_btn.clicked.connect(lambda: self.send_heater_cmd(1))
        self.heater_off_btn.clicked.connect(lambda: self.send_heater_cmd(0))

        self.fan_label = QLabel("风扇:")
        self.fan_on_btn = QPushButton("开")
        self.fan_off_btn = QPushButton("关")
        self.fan_on_btn.setFixedWidth(50)
        self.fan_off_btn.setFixedWidth(50)
        self.fan_on_btn.clicked.connect(lambda: self.send_fan_cmd(1))
        self.fan_off_btn.clicked.connect(lambda: self.send_fan_cmd(0))

        heater_layout.addWidget(self.heater_label)
        heater_layout.addWidget(self.heater_on_btn)
        heater_layout.addWidget(self.heater_off_btn)
        heater_layout.addSpacing(15)
        heater_layout.addWidget(self.fan_label)
        heater_layout.addWidget(self.fan_on_btn)
        heater_layout.addWidget(self.fan_off_btn)
        heater_layout.addStretch()
        self.heater_group.setLayout(heater_layout)

        # 4. 温湿度
        self.env_group = QGroupBox("温湿度读取值")
        self.temp_label = QLabel("温度：0.00")
        self.humi_label = QLabel("湿度：0.00")
        font_env = self.temp_label.font()
        font_env.setPointSize(12)
        self.temp_label.setFont(font_env)
        self.humi_label.setFont(font_env)
        env_layout = QHBoxLayout()
        env_layout.addWidget(self.temp_label)
        env_layout.addWidget(self.humi_label)
        self.env_group.setLayout(env_layout)

        # 4.5 阻值计算
        self.res_calc_group = QGroupBox("阻值计算")
        self.res_labels = {}
        res_calc_layout = QVBoxLayout()
        res_calc_layout.setSpacing(4)
        for row in range(2):
            row_layout = QHBoxLayout()
            row_layout.setSpacing(15)
            for col in range(2):
                i = row * 2 + col + 1
                label = QLabel(f"{hw_names[i]}：--- Ω")
                font_res = label.font()
                font_res.setPointSize(11)
                label.setFont(font_res)
                self.res_labels[i] = label
                row_layout.addWidget(label)
            row_layout.addStretch()
            res_calc_layout.addLayout(row_layout)
        self.res_calc_group.setLayout(res_calc_layout)

        # 5. 日志区域（自动滚动复选框）
        self.log_group = QGroupBox("实时日志")
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setStyleSheet("font-size: 11pt;")
        self.clear_log_btn = QPushButton("清空日志")
        self.clear_log_btn.clicked.connect(self.clear_log_text)

        self.auto_scroll_check = QCheckBox("自动滚动")
        self.auto_scroll_check.setChecked(True)
        self.auto_scroll_check.toggled.connect(self.toggle_auto_scroll)

        # 日志暂停按钮（绿色=运行中）
        self.log_pause_btn = QPushButton("日志 ▶")
        self.log_pause_btn.setCheckable(True)
        self.log_pause_btn.setChecked(False)
        self.log_pause_btn.setFixedWidth(70)
        self.log_pause_btn.setStyleSheet("background-color: #28a745; color: white;")
        self.log_pause_btn.clicked.connect(self.toggle_log_pause)

        log_btn_layout = QHBoxLayout()
        log_btn_layout.addWidget(QLabel("日志缓存条数:"))
        self.log_max_lines_spin = QSpinBox()
        self.log_max_lines_spin.setRange(10, 10000)
        self.log_max_lines_spin.setValue(self.max_log_lines)
        self.log_max_lines_spin.setFixedWidth(80)
        self.log_max_lines_spin.valueChanged.connect(self._on_log_max_lines_changed)
        log_btn_layout.addWidget(self.log_max_lines_spin)
        log_btn_layout.addStretch()
        log_btn_layout.addWidget(self.log_pause_btn)
        log_btn_layout.addWidget(self.auto_scroll_check)
        log_btn_layout.addWidget(self.clear_log_btn)

        log_layout = QVBoxLayout()
        log_layout.addWidget(self.log_text)
        log_layout.addLayout(log_btn_layout)
        self.log_group.setLayout(log_layout)

        # 右侧控件加载
        self.right_layout.addWidget(self.tool_group)
        self.right_layout.addWidget(self.ctrl_group)
        self.right_layout.addWidget(self.adc_ch_group)
        self.right_layout.addWidget(self.adc_temp_group)
        self.right_layout.addWidget(self.heater_group)
        self.right_layout.addWidget(self.env_group)
        self.right_layout.addWidget(self.res_calc_group)
        self.right_layout.addWidget(self.log_group)

        # ========== 左侧布局 ==========
        left_layout = QVBoxLayout()
        left_layout.setContentsMargins(8, 8, 8, 8)
        left_layout.setSpacing(12)
        left_layout.addLayout(top_total_layout)
        left_layout.addWidget(self.status_label)
        left_layout.addWidget(plot_control_group)
        left_layout.addWidget(self.plot_widget)

        # ========== 主布局 ==========
        main_layout = QHBoxLayout()
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(15)
        main_layout.addLayout(left_layout, stretch=5)
        main_layout.addLayout(self.right_layout, stretch=2)

        central = QWidget()
        central.setLayout(main_layout)
        self.setCentralWidget(central)

        self.refresh_ports()
        self.switch_mode_ui()

    # ===================== 日志相关 =====================
    def clear_log_text(self):
        self.log_text.clear()
        self.sig.log.emit("已手动清空日志")

    def safe_add_log(self, msg):
        # 保存当前滚动条位置
        scrollbar = self.log_text.verticalScrollBar()
        saved_pos = scrollbar.value() if scrollbar else 0

        lines = self.log_text.toPlainText().splitlines()
        if len(lines) >= self.max_log_lines:
            lines = lines[-self.max_log_lines + 1:]
            self.log_text.setPlainText("\n".join(lines))
        now = datetime.now().strftime("%H:%M:%S")
        self.log_text.append(f"[{now}] {msg}")

        if self.auto_scroll_log:
            cursor = self.log_text.textCursor()
            cursor.movePosition(cursor.End)
            self.log_text.setTextCursor(cursor)
        else:
            # 恢复滚动位置，避免日志自动跳到顶部
            if scrollbar:
                scrollbar.setValue(saved_pos)

    # ===================== 数据缓存/导出 =====================
    def clear_save_data(self):
        self.state.clear_save_data()
        self.sig.log.emit("已清空待导出缓存数据")

    def export_data_to_csv(self):
        data = self.state.get_save_data()
        if not data:
            QMessageBox.information(self, "提示", "暂无可导出数据！")
            return
        file_path, _ = QFileDialog.getSaveFileName(
            self, "保存数据", f"传感器数据_{datetime.now().strftime('%Y%m%d%H%M%S')}.csv",
            "CSV文件(*.csv);;所有文件(*)"
        )
        if not file_path:
            return
        try:
            with open(file_path, "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.writer(f)
                writer.writerow(["时间", "T1", "T2", "M1", "M2", "温度(℃)", "湿度(%RH)"])
                writer.writerows(data)
            self.sig.log.emit(f"数据导出成功：{os.path.basename(file_path)}")
            QMessageBox.information(self, "成功", "数据导出完成！")
        except Exception as e:
            self.sig.log.emit(f"导出失败：{str(e)}")
            QMessageBox.warning(self, "错误", f"导出失败：{str(e)}")

    # ===================== 收发模式切换 =====================
    def switch_mode_ui(self):
        is_net = self.net_radio.isChecked()
        self.port_label.setVisible(not is_net)
        self.port_combo.setVisible(not is_net)
        self.refresh_btn.setVisible(not is_net)
        self.ip_label.setVisible(is_net)
        self.ip_input.setVisible(is_net)
        self.port_tcp_label.setVisible(is_net)
        self.port_tcp_input.setVisible(is_net)

    # ===================== ADC通道选择 =====================
    def _on_adc_ch_changed(self, adc_idx, val, spin):
        """ADC通道选择变更时：更新后缀显示，发送指令 ADCx:y"""
        channel_names = ["10K", "100K", "1M", "10M", "100M", "1G", "10G"]
        spin.setSuffix(f"  ({channel_names[val]})")

        send_str = f"CHANNEL{adc_idx}:{val}\n"

        if self.uart_radio.isChecked() and self.serial_worker.is_connected:
            if self.serial_worker.send(send_str):
                self.sig.log.emit(f"[串口] 已发送：{send_str.strip()}")
            else:
                self.sig.log.emit("❌ 串口发送失败")
        elif self.net_radio.isChecked() and self.tcp_worker.is_connected:
            if self.tcp_worker.send(send_str):
                self.sig.log.emit(f"[网络] 已发送：{send_str.strip()}")
            else:
                self.sig.log.emit("❌ 网络发送失败")
        else:
            self.sig.log.emit("❌ 未连接，无法发送通道指令")

    # ===================== ADC通道自动匹配 =====================
    def _on_adc_auto_match_start(self):
        """开始ADC通道自动匹配（四路并行）"""
        if self.adc_match_running:
            return
        if not self.serial_worker.is_connected and not self.tcp_worker.is_connected:
            self.sig.log.emit("❌ 未连接，无法执行自动匹配")
            return

        self.adc_match_running = True
        self.adc_auto_match_btn.setEnabled(False)
        self.adc_range_low_spin.setEnabled(False)
        self.adc_range_high_spin.setEnabled(False)
        self.adc_delay_spin.setEnabled(False)
        # 保存原始通道值
        self._saved_channels = {i: self.adc_ch_spins[i].value() for i in range(1, 5)}

        range_low = self.adc_range_low_spin.value()
        range_high = self.adc_range_high_spin.value()
        delay_ms = self.adc_delay_spin.value()
        # 每个ADC独立的并行状态
        self.match_state = {
            1: {'channel': 6, 'phase': 'send', 'ticks': 0},
            2: {'channel': 6, 'phase': 'send', 'ticks': 0},
            3: {'channel': 6, 'phase': 'send', 'ticks': 0},
            4: {'channel': 6, 'phase': 'send', 'ticks': 0},
            'results': {},       # {adc_idx: channel_or_None}
        }
        self.sig.log.emit(f"=== 开始自动匹配（四路并行），范围：[{range_low} ~ {range_high}]，延迟：{delay_ms}ms ===")
        self.adc_match_timer.start(delay_ms)

    def _adc_match_tick(self):
        """自动匹配定时器回调（四路并行，每路独立状态机）"""
        range_low = self.adc_range_low_spin.value()
        range_high = self.adc_range_high_spin.value()
        delay_ms = self.adc_delay_spin.value()
        ch_names = ["10K", "100K", "1M", "10M", "100M", "1G", "10G"]
        hw = {1: 'T1', 2: 'T2', 3: 'M1', 4: 'M2'}

        # 一次性读取四路ADC值
        adc1, adc2, adc3, adc4 = self.state.get_adc_values()
        vals = {1: adc1, 2: adc2, 3: adc3, 4: adc4}

        all_done = True
        for adc in range(1, 5):
            st = self.match_state[adc]
            if st is None:
                continue  # 该ADC已完成
            all_done = False

            ch = st['channel']
            phase = st['phase']
            ch_name = ch_names[ch]

            if phase == 'send':
                send_str = f"CHANNEL{adc}:{ch}\n"
                sent = False
                if self.uart_radio.isChecked() and self.serial_worker.is_connected:
                    sent = self.serial_worker.send(send_str)
                elif self.net_radio.isChecked() and self.tcp_worker.is_connected:
                    sent = self.tcp_worker.send(send_str)
                if sent:
                    self.sig.log.emit(f"{hw[adc]}: → 通道{ch}({ch_name}) 已发送切换指令，等待{delay_ms}ms读取...")
                    st['phase'] = 'wait'
                    st['ticks'] = 0

            elif phase == 'wait':
                st['ticks'] += 1
                if st['ticks'] >= 1:
                    val = vals[adc]

                    if range_low <= val <= range_high:
                        # 匹配成功
                        self.match_state['results'][adc] = ch
                        self.sig.log.emit(f"{hw[adc]}: 通道{ch}({ch_name}) ✅ 匹配成功 (值={val} 在范围[{range_low}~{range_high}])")
                        spin = self.adc_ch_spins[adc]
                        spin.blockSignals(True)
                        spin.setValue(ch)
                        spin.setSuffix(f"  ({ch_name})")
                        spin.blockSignals(False)
                        self.match_state[adc] = None  # 标记完成
                    else:
                        # 未匹配，切换下一通道
                        st['channel'] -= 1
                        if st['channel'] < 0:
                            # 所有通道均未匹配
                            self.match_state['results'][adc] = None
                            self.sig.log.emit(f"{hw[adc]}: 通道{ch}({ch_name}) 值={val} 不在范围[{range_low}~{range_high}]，已是最后一个通道")
                            self.sig.log.emit(f"{hw[adc]}: ❌ 所有通道(6→0)均未匹配成功（范围=[{range_low}~{range_high}]）")
                            self.match_state[adc] = None  # 标记完成
                        else:
                            next_ch = st['channel']
                            next_name = ch_names[next_ch]
                            self.sig.log.emit(f"{hw[adc]}: 通道{ch}({ch_name}) 值={val} 不在范围[{range_low}~{range_high}]，→ 通道{next_ch}({next_name})")
                            st['phase'] = 'send'
                            st['ticks'] = 0

        if all_done:
            self._adc_match_done()

    def _adc_match_done(self):
        """匹配完成，恢复状态"""
        self.adc_match_timer.stop()
        self.adc_match_running = False
        self.adc_auto_match_btn.setEnabled(True)
        self.adc_range_low_spin.setEnabled(True)
        self.adc_range_high_spin.setEnabled(True)
        self.adc_delay_spin.setEnabled(True)

        results = self.match_state.get('results', {})
        matched = {k: v for k, v in results.items() if v is not None}
        failed = {k for k, v in results.items() if v is None}
        hw = {1: 'T1', 2: 'T2', 3: 'M1', 4: 'M2'}
        self.sig.log.emit(f"=== 自动匹配完成 成功:{len(matched)}/4 ===")
        for adc, ch in matched.items():
            ch_name = ["10K", "100K", "1M", "10M", "100M", "1G", "10G"][ch]
            self.sig.log.emit(f"{hw[adc]} → 通道{ch}({ch_name})")
        for adc in failed:
            self.sig.log.emit(f"{hw[adc]} → 未匹配成功")

    # ===================== ADC温度百分比发送 =====================
    def send_adc_temp_percent(self, adc_idx, slider):
        val = slider.value()
        send_str = f"PERCENT{adc_idx}:{val}\n"

        if self.uart_radio.isChecked() and self.serial_worker.is_connected:
            if self.serial_worker.send(send_str):
                self.sig.log.emit(f"[串口] 已发送：{send_str.strip()}")
            else:
                self.sig.log.emit("❌ 串口发送失败")
        elif self.net_radio.isChecked() and self.tcp_worker.is_connected:
            if self.tcp_worker.send(send_str):
                self.sig.log.emit(f"[网络] 已发送：{send_str.strip()}")
            else:
                self.sig.log.emit("❌ 网络发送失败")
        else:
            self.sig.log.emit("❌ 未连接，无法发送")

    # ===================== 加热台开关指令 =====================
    def send_heater_cmd(self, cmd):
        send_str = f"HEATER:{cmd}\n"
        if self.uart_radio.isChecked() and self.serial_worker.is_connected:
            if self.serial_worker.send(send_str):
                self.sig.log.emit(f"[串口] 已发送加热台指令：{send_str.strip()}")
            else:
                self.sig.log.emit("❌ 加热台指令发送失败")
        elif self.net_radio.isChecked() and self.tcp_worker.is_connected:
            if self.tcp_worker.send(send_str):
                self.sig.log.emit(f"[网络] 已发送加热台指令：{send_str.strip()}")
            else:
                self.sig.log.emit("❌ 加热台指令发送失败")
        else:
            self.sig.log.emit("❌ 未连接，无法发送加热台指令")

    # ===================== 风扇指令 =====================
    def send_fan_cmd(self, cmd):
        send_str = f"FAN:{cmd}\n"
        if self.uart_radio.isChecked() and self.serial_worker.is_connected:
            if self.serial_worker.send(send_str):
                self.sig.log.emit(f"[串口] 已发送风扇指令：{send_str.strip()}")
            else:
                self.sig.log.emit("❌ 风扇指令发送失败")
        else:
            self.sig.log.emit("❌ 串口未连接，无法发送风扇指令")

    # ===================== 温湿度UI刷新 =====================
    def update_temp_humi_ui(self):
        temp, humi = self.state.get_temp_humi()
        try:
            self.temp_label.setText(f"温度：{temp:.2f} ℃")
            self.humi_label.setText(f"湿度：{humi:.2f} %RH")
        except Exception:
            pass

    # ===================== 阻值计算UI刷新 =====================
    def update_resistance_ui(self, adc1, adc2, adc3, adc4):
        """根据ADC值和当前采样电阻通道计算并显示阻值"""
        channel_res = [10000, 100000, 1000000, 10000000, 100000000, 1000000000, 10000000000]
        adc_vals = {1: adc1, 2: adc2, 3: adc3, 4: adc4}
        hw = {1: 'T1', 2: 'T2', 3: 'M1', 4: 'M2'}

        for i in range(1, 5):
            adc = adc_vals[i]
            ch = self.adc_ch_spins[i].value()
            R = channel_res[ch]

            if adc >= 4095:
                self.res_labels[i].setText(f"{hw[i]}：∞ Ω")
            elif adc == 0:
                self.res_labels[i].setText(f"{hw[i]}：0 Ω")
            else:
                r = R * adc / (4095 - adc)
                # 自动选择合适的单位
                if r >= 1e9:
                    self.res_labels[i].setText(f"{hw[i]}：{r/1e9:.2f} GΩ")
                elif r >= 1e6:
                    self.res_labels[i].setText(f"{hw[i]}：{r/1e6:.2f} MΩ")
                elif r >= 1e3:
                    self.res_labels[i].setText(f"{hw[i]}：{r/1e3:.2f} KΩ")
                else:
                    self.res_labels[i].setText(f"{hw[i]}：{r:.1f} Ω")

    # ===================== 串口列表刷新 =====================
    def refresh_ports(self):
        self.port_combo.clear()
        for p in SerialWorker.list_ports():
            self.port_combo.addItem(p)

    # ===================== 连接/断开 =====================
    def open_connection(self):
        self.close_all()
        if self.uart_radio.isChecked():
            port = self.port_combo.currentText()
            self.serial_worker.open(port, BAUD_RATE, self.status_label.setText)
            if self.serial_worker.is_connected:
                QTimer.singleShot(500, self._send_channel_init)
        else:
            ip = self.ip_input.text().strip()
            try:
                port = int(self.port_tcp_input.text().strip())
            except ValueError:
                port = TCP_SERVER_PORT
            self.tcp_worker.open(ip, port, self.status_label.setText)
            if self.tcp_worker.is_connected:
                QTimer.singleShot(500, self._send_channel_init)

    def _send_channel_init(self):
        """初始化四路采样通道，发送当前上位机界面中显示的通道值"""
        for i in range(1, 5):
            ch = self.adc_ch_spins[i].value()
            send_str = f"CHANNEL{i}:{ch}\n"
            if self.uart_radio.isChecked() and self.serial_worker.is_connected:
                self.serial_worker.send(send_str)
            elif self.net_radio.isChecked() and self.tcp_worker.is_connected:
                self.tcp_worker.send(send_str)
        self.sig.log.emit("已发送四路采样通道初始化指令（当前界面通道值）")

    def close_all(self):
        self.serial_worker.close()
        self.tcp_worker.close()
        self.status_label.setText("状态：已断开")
        self.sig.log.emit("已断开所有连接")

    def _on_serial_lost(self):
        """串口设备丢失回调"""
        self.status_label.setText("状态：串口丢失")
        self.serial_worker.close()

    # ===================== 数据更新与绘图 =====================
    def on_sample_tick(self):
        """采样定时器回调：按设定频率读取最新ADC值，更新曲线和日志"""
        if not self.serial_worker.is_connected and not self.tcp_worker.is_connected:
            return

        adc1, adc2, adc3, adc4 = self.state.get_adc_values()

        if not self.chart_paused:
            self.update_data(1, adc1)
            self.update_data(2, adc2)
            self.update_data(3, adc3)
            self.update_data(4, adc4)
            self.state.add_save_record()
            self.update_resistance_ui(adc1, adc2, adc3, adc4)

        if not self.log_paused:
            self.sig.log.emit(f"T1={adc1:4d}  T2={adc2:4d}  M1={adc3:4d}  M2={adc4:4d}")

    def apply_sample_freq(self):
        try:
            freq = float(self.sample_freq_input.text())
            if freq <= 0:
                QMessageBox.warning(self, "参数错误", "采样频率必须大于0！")
                return
            if freq > 1000:
                QMessageBox.warning(self, "参数错误", "采样频率不能超过1000Hz！")
                return

            self.sample_freq = freq
            interval_ms = int(1000 / freq)
            if self.sample_timer is not None:
                self.sample_timer.setInterval(interval_ms)
            self.sig.log.emit(f"采样频率已设置为 {freq} Hz")
        except ValueError:
            QMessageBox.warning(self, "输入错误", "请输入合法数字！")

    def update_data(self, channel, val):
        # 计算阻值
        channel_res = [10000, 100000, 1000000, 10000000, 100000000, 1000000000, 10000000000]
        ch = self.adc_ch_spins[channel].value()
        R = channel_res[ch]
        if val >= 4095:
            r = float('inf')
        elif val == 0:
            r = 0.0
        else:
            r = R * val / (4095 - val)

        if channel == 1:
            self.data_y1.pop(0)
            self.data_y1.append(val)
            self.data_r1.pop(0)
            self.data_r1.append(r)
        elif channel == 2:
            self.data_y2.pop(0)
            self.data_y2.append(val)
            self.data_r2.pop(0)
            self.data_r2.append(r)
        elif channel == 3:
            self.data_y3.pop(0)
            self.data_y3.append(val)
            self.data_r3.pop(0)
            self.data_r3.append(r)
        elif channel == 4:
            self.data_y4.pop(0)
            self.data_y4.append(val)
            self.data_r4.pop(0)
            self.data_r4.append(r)

        if self.plot_auto_scroll:
            self.data_x.pop(0)
            self.data_x.append(self.data_x[-1] + 1)

    def update_plot(self):
        if self.resistance_view:
            self.curve1.setData(self.data_x, self.data_r1)
            self.curve2.setData(self.data_x, self.data_r2)
            self.curve3.setData(self.data_x, self.data_r3)
            self.curve4.setData(self.data_x, self.data_r4)
        else:
            self.curve1.setData(self.data_x, self.data_y1)
            self.curve2.setData(self.data_x, self.data_y2)
            self.curve3.setData(self.data_x, self.data_y3)
            self.curve4.setData(self.data_x, self.data_y4)

        if self.plot_auto_scroll and len(self.data_x) > 0:
            x_max = self.data_x[-1]
            view_range = self.plot_widget.viewRange()
            x_span = view_range[0][1] - view_range[0][0]
            x_min = x_max - x_span
            self.plot_widget.setXRange(x_min, x_max, padding=0)

    # ===================== 网格背景切换 =====================
    def toggle_grid(self):
        checked = self.grid_btn.isChecked()
        self.plot_widget.showGrid(x=checked, y=checked)
        if checked:
            self.sig.log.emit("图表网格已开启")
        else:
            self.sig.log.emit("图表网格已关闭")

    # ===================== 清除图表数据 =====================
    def clear_plot_data(self):
        self.data_x = list(range(self.max_data_points))
        self.data_y1 = [0] * self.max_data_points
        self.data_y2 = [0] * self.max_data_points
        self.data_y3 = [0] * self.max_data_points
        self.data_y4 = [0] * self.max_data_points
        self.data_r1 = [0] * self.max_data_points
        self.data_r2 = [0] * self.max_data_points
        self.data_r3 = [0] * self.max_data_points
        self.data_r4 = [0] * self.max_data_points
        self.update_plot()
        self.sig.log.emit("图表数据已清空")

    # ===================== 窗口关闭事件 =====================
    def closeEvent(self, event):
        self.close_all()
        self.plot_timer.stop()
        self.env_timer.stop()
        if self.sample_timer is not None:
            self.sample_timer.stop()
        event.accept()
