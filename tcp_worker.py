import threading
import socket

from signals import Signals
from data_state import DataState
from data_parser import DataParser


class TcpWorker:
    """TCP 客户端通信：连接、收发、数据解析。"""

    def __init__(self, signals: Signals, state: DataState):
        self.signals = signals
        self.state = state
        self.client = None
        self.is_connected = False
        self.lock = threading.Lock()

    def open(self, ip, port, status_cb):
        try:
            self.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.client.settimeout(3)
            self.client.connect((ip, port))
            self.client.setblocking(False)
            self.is_connected = True
            status_cb(f"状态：网络已连接 {ip}:{port}")
            self.signals.log.emit(f"网络连接成功：{ip}:{port}")
            threading.Thread(target=self._recv_loop, daemon=True).start()
            return True
        except Exception:
            status_cb("状态：TCP 连接失败")
            self.signals.log.emit("TCP 连接失败，请检查 IP/端口/服务器")
            return False

    def close(self):
        self.is_connected = False
        if self.client:
            try:
                self.client.close()
            except Exception:
                pass
        self.client = None

    def send(self, data_str):
        """发送字符串，成功返回 True，失败返回 False。"""
        if not (self.is_connected and self.client):
            return False
        try:
            with self.lock:
                self.client.send(data_str.encode('utf-8'))
            return True
        except Exception:
            return False

    def _recv_loop(self):
        buffer = b""
        while self.is_connected:
            try:
                with self.lock:
                    if not self.client:
                        break
                    try:
                        chunk = self.client.recv(1024)
                    except BlockingIOError:
                        continue
                    if not chunk:
                        break
                    buffer += chunk
                    while b"\n" in buffer:
                        line, buffer = buffer.split(b"\n", 1)
                        data = line.decode('utf-8', 'ignore').strip()
                        if not data:
                            continue
                        self._handle_data(data)
            except Exception:
                continue
        self.signals.log.emit("网络连接断开")
        self.close()

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
