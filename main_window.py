"""MainWindow 主控制器 — 协调 UI 面板与各功能模块。"""
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout,
    QMessageBox, QPushButton
)
from PyQt5.QtCore import QTimer, QUrl
from PyQt5.QtGui import QDesktopServices

from config import MAX_DATA_POINTS_DEFAULT, MAX_LOG_LINES
from core.signals import Signals
from core.data_state import DataState
from workers.serial_worker import SerialWorker
from workers.tcp_worker import TcpWorker

from connection.connection_manager import ConnectionManager
from chart.chart_manager import ChartManager
from device.device_controller import DeviceController
from device.channel_matcher import ChannelMatcher
from data.export_manager import ExportManager
from log.log_manager import LogManager

from ui.left_panel import LeftPanel
from ui.right_panel import RightPanel
from ui.help_dialog import HelpDialog


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("氨气检测-ESP32")
        self.setGeometry(100, 100, 1200, 720)

        # ===================== 1. 核心层 =====================
        self.sig = Signals()
        self.state = DataState()

        # ===================== 2. 通信层 =====================
        self.serial_worker = SerialWorker(self.sig, self.state)
        self.tcp_worker = TcpWorker(self.sig, self.state)

        # ===================== 3. UI 层 =====================
        self.left = LeftPanel()
        self.right = RightPanel()

        # ===================== 4. 管理层 =====================
        self.conn_mgr = ConnectionManager(
            self.sig, self.state, self.serial_worker, self.tcp_worker
        )
        self.chart_mgr = ChartManager(self.sig, self.state, MAX_DATA_POINTS_DEFAULT)
        self.device_ctrl = DeviceController(self.sig)
        self.channel_matcher = ChannelMatcher(self.sig, self.state, self.device_ctrl)
        self.log_mgr = LogManager(self.right.log_text, self.sig, MAX_LOG_LINES)
        self.export_mgr = ExportManager(self.state, self.sig, self)

        # ===================== 5. 注入 UI 引用到管理层 =====================
        self._inject_ui_refs()

        # ===================== 6. 组合布局 =====================
        left_layout = self.left.build_layout()
        right_layout = self.right.build_layout()

        main_layout = QHBoxLayout()
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(15)
        main_layout.addLayout(left_layout, stretch=5)
        main_layout.addLayout(right_layout, stretch=2)

        central = QWidget()
        central.setLayout(main_layout)
        self.setCentralWidget(central)

        # ===================== 7. 信号连接 =====================
        self._connect_signals()

        # ===================== 8. 定时器 =====================
        self._setup_timers()

        # ===================== 9. 初始化收尾 =====================
        self.conn_mgr.refresh_ports()
        self.conn_mgr.switch_mode_ui()

    # ===================== 注入 UI 引用 =====================
    def _inject_ui_refs(self):
        """将 UI 控件引用注入到各管理模块。"""
        L = self.left
        R = self.right

        # --- ConnectionManager ---
        self.conn_mgr.set_ui_widgets(
            uart_radio=L.uart_radio, net_radio=L.net_radio,
            port_combo=L.port_combo, port_label=L.port_label,
            refresh_btn=L.refresh_btn, ip_label=L.ip_label,
            ip_input=L.ip_input, port_tcp_label=L.port_tcp_label,
            port_tcp_input=L.port_tcp_input, connect_btn=L.connect_btn,
            disconnect_btn=L.disconnect_btn, status_label=L.status_label,
        )
        self.conn_mgr.set_adc_ch_spins(R.adc_ch_spins)

        # --- DeviceController ---
        self.device_ctrl.set_workers(self.serial_worker, self.tcp_worker)
        self.device_ctrl.set_mode_checker(lambda: L.uart_radio.isChecked())

        # --- ChartManager ---
        curves = {1: L.curve1, 2: L.curve2, 3: L.curve3, 4: L.curve4}
        curve_btns = {1: L.adc1_btn, 2: L.adc2_btn, 3: L.adc3_btn, 4: L.adc4_btn}
        self.chart_mgr.set_ui_widgets(
            plot_widget=L.plot_widget, curves=curves, curve_btns=curve_btns,
            view_combo=L.view_combo, auto_scroll_btn=L.auto_scroll_btn,
            chart_pause_btn=L.chart_pause_btn, grid_btn=L.grid_btn,
            x_point_input=L.x_point_input,
        )
        self.chart_mgr.set_adc_ch_spins(R.adc_ch_spins)

        # --- ChannelMatcher ---
        self.channel_matcher.set_ui_widgets(
            adc_ch_spins=R.adc_ch_spins,
            range_low_spin=R.adc_range_low_spin,
            range_high_spin=R.adc_range_high_spin,
            delay_spin=R.adc_delay_spin,
            auto_match_btn=R.adc_auto_match_btn,
        )

    # ===================== 信号连接 =====================
    def _connect_signals(self):
        L = self.left
        R = self.right

        # 日志信号
        self.sig.log.connect(self.log_mgr.add_log)
        self.sig.serial_lost.connect(self.conn_mgr.on_serial_lost)

        # 连接按钮
        L.refresh_btn.clicked.connect(self.conn_mgr.refresh_ports)
        L.connect_btn.clicked.connect(self.conn_mgr.open_connection)
        L.disconnect_btn.clicked.connect(self.conn_mgr.close_all)
        L.net_radio.toggled.connect(self.conn_mgr.switch_mode_ui)

        # 图表控制按钮
        L.apply_plot_btn.clicked.connect(self._on_apply_plot_setting)
        L.adc1_btn.clicked.connect(lambda: self.chart_mgr.toggle_curve(1))
        L.adc2_btn.clicked.connect(lambda: self.chart_mgr.toggle_curve(2))
        L.adc3_btn.clicked.connect(lambda: self.chart_mgr.toggle_curve(3))
        L.adc4_btn.clicked.connect(lambda: self.chart_mgr.toggle_curve(4))
        L.view_combo.currentIndexChanged.connect(self.chart_mgr.set_view_mode)
        L.auto_scroll_btn.clicked.connect(self.chart_mgr.toggle_auto_scroll)
        L.auto_match_btn.clicked.connect(self.chart_mgr.auto_match_axis)
        L.chart_pause_btn.clicked.connect(self.chart_mgr.toggle_pause)
        L.clear_plot_btn.clicked.connect(self.chart_mgr.clear_data)
        L.grid_btn.clicked.connect(self.chart_mgr.toggle_grid)

        # 采样频率
        R.sample_freq_apply_btn.clicked.connect(self._apply_sample_freq)

        # ADC 通道选择 → ChannelMatcher
        for i in range(1, 5):
            spin = R.adc_ch_spins[i]
            spin.valueChanged.connect(
                lambda val, idx=i, sp=spin: self.channel_matcher.on_channel_changed(idx, val)
            )
        R.adc_auto_match_btn.clicked.connect(self.channel_matcher.start_auto_match)

        # 温度百分比发送按钮
        for i in range(1, 5):
            slider = R.adc_temp_sliders[i]
            # 在 right_panel 中已连接 slider.valueChanged → label
            # 这里需要找到对应的 send_btn 并连接
            self._wire_temp_send_btn(i, slider)

        # 加热台 & 风扇
        R.heater_on_btn.clicked.connect(lambda: self.device_ctrl.send_heater_cmd(1))
        R.heater_off_btn.clicked.connect(lambda: self.device_ctrl.send_heater_cmd(0))
        R.fan_on_btn.clicked.connect(lambda: self.device_ctrl.send_fan_cmd(1))
        R.fan_off_btn.clicked.connect(lambda: self.device_ctrl.send_fan_cmd(0))

        # 日志控件
        R.clear_log_btn.clicked.connect(self.log_mgr.clear)
        R.auto_scroll_check.toggled.connect(self.log_mgr.set_auto_scroll)
        R.log_max_lines_spin.valueChanged.connect(self.log_mgr.set_max_lines)
        R.log_pause_btn.clicked.connect(self._on_log_pause_toggle)

        # 工具按钮
        R.help_btn.clicked.connect(self._show_help)
        R.source_btn.clicked.connect(self._open_source_url)
        R.export_btn.clicked.connect(self.export_mgr.export_to_csv)
        R.clear_data_btn.clicked.connect(self.export_mgr.clear_cache)

    def _wire_temp_send_btn(self, idx, slider):
        """找到温度百分比滑块对应的发送按钮并连接信号。"""
        # RightPanel 中每个 slider 的父布局结构:
        # col_widget → col_layout → [slider, (btn_row → [label, stretch, send_btn])]
        parent = slider.parent()  # col_widget
        if parent is None:
            return
        # 遍历子控件找到 QPushButton("发送")
        for child in parent.findChildren(QWidget):
            if isinstance(child, QPushButton) and child.text() == "发送":
                child.clicked.connect(
                    lambda checked=False, i=idx, sl=slider:
                    self.device_ctrl.send_temp_percent(i, sl.value())
                )
                break

    # ===================== 定时器 =====================
    def _setup_timers(self):
        # 图表刷新（50ms 高频）
        self.plot_timer = QTimer()
        self.plot_timer.timeout.connect(self.chart_mgr.update_plot)
        self.plot_timer.start(50)

        # 采样定时器（默认 1Hz）
        self.sample_freq = 1.0
        self.sample_timer = QTimer()
        self.sample_timer.timeout.connect(self._on_sample_tick)
        self.sample_timer.start(1000)

        # 温湿度 UI 刷新（1s）
        self.env_timer = QTimer()
        self.env_timer.timeout.connect(self._update_temp_humi_ui)
        self.env_timer.start(1000)

    # ===================== 采样回调 =====================
    def _on_sample_tick(self):
        """按设定频率读取 ADC 值，更新图表和日志。"""
        if not self.conn_mgr.is_connected():
            return

        adc1, adc2, adc3, adc4 = self.state.get_adc_values()

        if not self.chart_mgr.chart_paused:
            self.chart_mgr.update_data(1, adc1)
            self.chart_mgr.update_data(2, adc2)
            self.chart_mgr.update_data(3, adc3)
            self.chart_mgr.update_data(4, adc4)
            self.state.add_save_record()
            self._update_resistance_ui(adc1, adc2, adc3, adc4)

        if not self.log_mgr.log_paused:
            self.sig.log.emit(f"T1={adc1:4d}  T2={adc2:4d}  M1={adc3:4d}  M2={adc4:4d}")

    # ===================== 采样频率 =====================
    def _apply_sample_freq(self):
        try:
            freq = float(self.right.sample_freq_input.text())
            if freq <= 0:
                QMessageBox.warning(self, "参数错误", "采样频率必须大于0！")
                return
            if freq > 1000:
                QMessageBox.warning(self, "参数错误", "采样频率不能超过1000Hz！")
                return
            self.sample_freq = freq
            self.sample_timer.setInterval(int(1000 / freq))
            self.sig.log.emit(f"采样频率已设置为 {freq} Hz")
        except ValueError:
            QMessageBox.warning(self, "输入错误", "请输入合法数字！")

    # ===================== 图表参数 =====================
    def _on_apply_plot_setting(self):
        try:
            x_points = int(self.left.x_point_input.text())
            if x_points < 10:
                QMessageBox.warning(self, "参数错误", "采样点数不能小于10！")
                return
            self.chart_mgr.apply_point_count(x_points)
        except ValueError:
            QMessageBox.warning(self, "输入错误", "请输入合法数字！")

    # ===================== 日志暂停 =====================
    def _on_log_pause_toggle(self, checked):
        self.log_mgr.set_paused(checked)
        btn = self.right.log_pause_btn
        if checked:
            btn.setText("日志 ⏸")
            btn.setStyleSheet("background-color: #dc3545; color: white;")
            self.sig.log.emit("⏸ 日志已暂停（手动操作日志除外）")
        else:
            btn.setText("日志 ▶")
            btn.setStyleSheet("background-color: #28a745; color: white;")
            self.sig.log.emit("▶ 日志已恢复")

    # ===================== 温湿度 UI 刷新 =====================
    def _update_temp_humi_ui(self):
        temp, humi = self.state.get_temp_humi()
        try:
            self.right.temp_label.setText(f"温度：{temp:.2f} ℃")
            self.right.humi_label.setText(f"湿度：{humi:.2f} %RH")
        except Exception:
            pass

    # ===================== 阻值 UI 刷新 =====================
    def _update_resistance_ui(self, adc1, adc2, adc3, adc4):
        vals = self.chart_mgr.get_resistance_values(adc1, adc2, adc3, adc4)
        for i, text in vals.items():
            if i in self.right.res_labels:
                self.right.res_labels[i].setText(text)

    # ===================== 帮助弹窗 =====================
    def _show_help(self):
        dlg = HelpDialog(self)
        dlg.exec_()

    # ===================== 打开源码 =====================
    def _open_source_url(self):
        QDesktopServices.openUrl(QUrl("https://gitee.com/GAOTINGXIANG/adc_exe"))

    # ===================== 窗口关闭 =====================
    def closeEvent(self, event):
        self.conn_mgr.close_all()
        self.plot_timer.stop()
        self.env_timer.stop()
        self.sample_timer.stop()
        event.accept()
