import threading

import serial
import serial.tools.list_ports

from signals import Signals
from data_state import DataState
from data_parser import DataParser


class SerialWorker:
    """串口通信：连接、收发、数据解析。"""

    def __init__(self, signals: Signals, state: DataState):
        self.signals = signals
        self.state = state
        self.ser = None
        self.is_connected = False
        self.lock = threading.Lock()

    @staticmethod
    def list_ports():
        return [p.device for p in serial.tools.list_ports.comports()]

    def open(self, port, baud_rate, status_cb):
        if not port:
            status_cb("状态：请选择COM口")
            self.signals.log.emit("错误：未选择COM口")
            return False
        try:
            self.ser = serial.Serial(port, baud_rate, timeout=0.1)
            self.is_connected = True
            status_cb(f"状态：串口已连接 {port}")
            self.signals.log.emit(f"串口连接成功：{port}")
            threading.Thread(target=self._recv_loop, daemon=True).start()
            return True
        except Exception:
            status_cb("状态：串口打开失败")
            self.signals.log.emit("串口打开失败")
            return False

    def close(self):
        self.is_connected = False
        if self.ser:
            try:
                with self.lock:
                    self.ser.close()
            except Exception:
                pass
        self.ser = None

    def send(self, data_str):
        """发送字符串，成功返回 True，失败返回 False。"""
        if not (self.is_connected and self.ser):
            return False
        try:
            with self.lock:
                self.ser.write(data_str.encode('utf-8'))
            return True
        except Exception:
            return False

    def _recv_loop(self):
        while self.is_connected:
            try:
                with self.lock:
                    if not self.ser or not self.ser.in_waiting:
                        continue
                    data = self.ser.readline().decode('utf-8', 'ignore').strip()
                if not data:
                    continue
                self._handle_data(data)
            except (serial.SerialException, OSError):
                if self.is_connected:
                    self.is_connected = False
                    self.signals.log.emit("❌ 串口设备丢失，连接已断开")
                    self.signals.serial_lost.emit()
                return
            except Exception:
                continue

    def _handle_data(self, data):
        parsed = DataParser.parse(data)
        if parsed is None:
            return
        kind, val = parsed
        if kind == 'adc1':
            self.state.set_adc_value(1, val)
        elif kind == 'adc2':
            self.state.set_adc_value(2, val)
        elif kind == 'adc3':
            self.state.set_adc_value(3, val)
        elif kind == 'adc4':
            self.state.set_adc_value(4, val)
        elif kind == 'temp':
            self.state.update_temp(val)
        elif kind == 'humi':
            self.state.update_humi(val)
