"""连接管理：串口/网络模式切换、连接/断开、端口刷新、通道初始化。"""
from PyQt5.QtCore import QTimer

from config import BAUD_RATE, TCP_SERVER_IP, TCP_SERVER_PORT
from workers.serial_worker import SerialWorker


class ConnectionManager:
    def __init__(self, signals, state, serial_worker, tcp_worker):
        self.sig = signals
        self.state = state
        self.serial_worker = serial_worker
        self.tcp_worker = tcp_worker

        # UI 控件（外部注入）
        self.uart_radio = None
        self.net_radio = None
        self.port_combo = None
        self.port_label = None
        self.refresh_btn = None
        self.ip_label = None
        self.ip_input = None
        self.port_tcp_label = None
        self.port_tcp_input = None
        self.connect_btn = None
        self.disconnect_btn = None
        self.status_label = None

        # 通道旋钮引用（用于初始化时发送）
        self.adc_ch_spins = {}

    def set_ui_widgets(self, uart_radio, net_radio, port_combo, port_label,
                       refresh_btn, ip_label, ip_input, port_tcp_label,
                       port_tcp_input, connect_btn, disconnect_btn, status_label):
        self.uart_radio = uart_radio
        self.net_radio = net_radio
        self.port_combo = port_combo
        self.port_label = port_label
        self.refresh_btn = refresh_btn
        self.ip_label = ip_label
        self.ip_input = ip_input
        self.port_tcp_label = port_tcp_label
        self.port_tcp_input = port_tcp_input
        self.connect_btn = connect_btn
        self.disconnect_btn = disconnect_btn
        self.status_label = status_label

    def set_adc_ch_spins(self, spins):
        self.adc_ch_spins = spins

    # ===================== 模式切换 =====================
    def switch_mode_ui(self):
        """根据当前选中的收发模式显示/隐藏对应控件。"""
        is_net = self.net_radio.isChecked() if self.net_radio else False
        if self.port_label:
            self.port_label.setVisible(not is_net)
        if self.port_combo:
            self.port_combo.setVisible(not is_net)
        if self.refresh_btn:
            self.refresh_btn.setVisible(not is_net)
        if self.ip_label:
            self.ip_label.setVisible(is_net)
        if self.ip_input:
            self.ip_input.setVisible(is_net)
        if self.port_tcp_label:
            self.port_tcp_label.setVisible(is_net)
        if self.port_tcp_input:
            self.port_tcp_input.setVisible(is_net)

    # ===================== 端口刷新 =====================
    def refresh_ports(self):
        """刷新串口列表。"""
        if self.port_combo:
            self.port_combo.clear()
            for p in SerialWorker.list_ports():
                self.port_combo.addItem(p)

    # ===================== 连接 / 断开 =====================
    def open_connection(self):
        """根据当前模式建立连接。"""
        self.close_all()
        if self.uart_radio and self.uart_radio.isChecked():
            port = self.port_combo.currentText() if self.port_combo else ""
            self.serial_worker.open(port, BAUD_RATE, self._set_status)
            if self.serial_worker.is_connected:
                QTimer.singleShot(500, self._send_channel_init)
        else:
            ip = self.ip_input.text().strip() if self.ip_input else TCP_SERVER_IP
            try:
                port = int(self.port_tcp_input.text().strip()) if self.port_tcp_input else TCP_SERVER_PORT
            except ValueError:
                port = TCP_SERVER_PORT
            self.tcp_worker.open(ip, port, self._set_status)
            if self.tcp_worker.is_connected:
                QTimer.singleShot(500, self._send_channel_init)

    def close_all(self):
        """断开所有连接。"""
        self.serial_worker.close()
        self.tcp_worker.close()
        self._set_status("状态：已断开")
        self.sig.log.emit("已断开所有连接")

    def _set_status(self, text):
        if self.status_label:
            self.status_label.setText(text)

    def _send_channel_init(self):
        """连接后同步当前界面的采样通道值到设备。"""
        for i in range(1, 5):
            spin = self.adc_ch_spins.get(i)
            if spin is None:
                continue
            ch = spin.value()
            send_str = f"CHANNEL{i}:{ch}\n"
            if self.uart_radio and self.uart_radio.isChecked():
                if self.serial_worker.is_connected:
                    self.serial_worker.send(send_str)
            else:
                if self.tcp_worker.is_connected:
                    self.tcp_worker.send(send_str)
        self.sig.log.emit("已发送四路采样通道初始化指令（当前界面通道值）")

    # ===================== 断线处理 =====================
    def on_serial_lost(self):
        """串口设备丢失回调。"""
        self._set_status("状态：串口丢失")
        self.serial_worker.close()

    # ===================== 状态查询 =====================
    def is_connected(self):
        return self.serial_worker.is_connected or self.tcp_worker.is_connected

    def is_uart(self):
        return self.uart_radio.isChecked() if self.uart_radio else True

    def get_mode(self):
        return 'uart' if self.is_uart() else 'net'
