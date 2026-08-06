"""设备控制指令发送：温度百分比、加热台、风扇、通道切换。"""


class DeviceController:
    def __init__(self, signals):
        self.sig = signals
        self._serial_worker = None
        self._tcp_worker = None
        self._is_uart = lambda: True

    def set_workers(self, serial_worker, tcp_worker):
        self._serial_worker = serial_worker
        self._tcp_worker = tcp_worker

    def set_mode_checker(self, is_uart_fn):
        self._is_uart = is_uart_fn

    def _send(self, send_str) -> bool:
        """根据当前模式选择发送通道，返回是否发送成功。"""
        if self._is_uart():
            if self._serial_worker and self._serial_worker.is_connected:
                return self._serial_worker.send(send_str)
        else:
            if self._tcp_worker and self._tcp_worker.is_connected:
                return self._tcp_worker.send(send_str)
        return False

    def send_channel_cmd(self, adc_idx, channel_val):
        """发送采样通道切换指令 CHANNELx:y"""
        mode = "串口" if self._is_uart() else "网络"
        send_str = f"CHANNEL{adc_idx}:{channel_val}\n"
        if self._send(send_str):
            self.sig.log.emit(f"[{mode}] 已发送：{send_str.strip()}")
        else:
            self.sig.log.emit("❌ 未连接，无法发送通道指令")

    def send_temp_percent(self, adc_idx, percent):
        """发送温度百分比指令 PERCENTx:y"""
        mode = "串口" if self._is_uart() else "网络"
        send_str = f"PERCENT{adc_idx}:{percent}\n"
        if self._send(send_str):
            self.sig.log.emit(f"[{mode}] 已发送：{send_str.strip()}")
        else:
            self.sig.log.emit("❌ 未连接，无法发送")

    def send_heater_cmd(self, on_off):
        """发送加热台开关指令 HEATER:0/1"""
        mode = "串口" if self._is_uart() else "网络"
        send_str = f"HEATER:{on_off}\n"
        if self._send(send_str):
            self.sig.log.emit(f"[{mode}] 已发送加热台指令：{send_str.strip()}")
        else:
            self.sig.log.emit("❌ 加热台指令发送失败")

    def send_fan_cmd(self, on_off):
        """发送风扇开关指令 FAN:0/1（仅串口支持）"""
        send_str = f"FAN:{on_off}\n"
        if self._is_uart() and self._serial_worker and self._serial_worker.is_connected:
            if self._serial_worker.send(send_str):
                self.sig.log.emit(f"[串口] 已发送风扇指令：{send_str.strip()}")
            else:
                self.sig.log.emit("❌ 风扇指令发送失败")
        else:
            self.sig.log.emit("❌ 串口未连接，无法发送风扇指令")
