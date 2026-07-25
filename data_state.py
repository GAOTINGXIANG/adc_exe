import threading
from datetime import datetime


class DataState:
    """线程安全的数据状态管理：保存最新 4路ADC/温湿度及待导出数据缓存。"""

    def __init__(self):
        self._lock = threading.Lock()
        self.last_adc1 = 0
        self.last_adc2 = 0
        self.last_adc3 = 0
        self.last_adc4 = 0
        self.last_temp = 0.0
        self.last_humi = 0.0
        self.save_data_list = []

    def update_adc(self, channel, val):
        with self._lock:
            if channel == 1:
                self.last_adc1 = val
            elif channel == 2:
                self.last_adc2 = val
            elif channel == 3:
                self.last_adc3 = val
            elif channel == 4:
                self.last_adc4 = val
            now_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.save_data_list.append([now_time, self.last_adc1, self.last_adc2, self.last_adc3, self.last_adc4, self.last_temp, self.last_humi])

    def set_adc_value(self, channel, val):
        """只更新最新ADC值，不写入历史记录（用于高频接收时降采样）"""
        with self._lock:
            if channel == 1:
                self.last_adc1 = val
            elif channel == 2:
                self.last_adc2 = val
            elif channel == 3:
                self.last_adc3 = val
            elif channel == 4:
                self.last_adc4 = val

    def get_adc_values(self):
        with self._lock:
            return self.last_adc1, self.last_adc2, self.last_adc3, self.last_adc4

    def add_save_record(self):
        """将当前最新值作为一条记录写入历史（由采样定时器调用）"""
        with self._lock:
            now_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.save_data_list.append([now_time, self.last_adc1, self.last_adc2, self.last_adc3, self.last_adc4, self.last_temp, self.last_humi])

    def update_temp(self, val):
        with self._lock:
            self.last_temp = val

    def update_humi(self, val):
        with self._lock:
            self.last_humi = val

    def get_temp_humi(self):
        with self._lock:
            return self.last_temp, self.last_humi

    def clear_save_data(self):
        with self._lock:
            self.save_data_list.clear()

    def get_save_data(self):
        with self._lock:
            return list(self.save_data_list)
