class DataParser:
    """解析设备发送的数据行，并计算采样电阻值。"""

    @staticmethod
    def parse(line):
        """
        解析一行数据。
        返回: (kind, value) 二元组，kind 为 'adc1'/'adc2'/'adc3'/'adc4'/'temp'/'humi'；
              解析失败返回 None。
        """
        if line.startswith("ADC1:"):
            try:
                return 'adc1', int(line.split(":")[1])
            except Exception:
                return None
        if line.startswith("ADC2:"):
            try:
                return 'adc2', int(line.split(":")[1])
            except Exception:
                return None
        if line.startswith("ADC3:"):
            try:
                return 'adc3', int(line.split(":")[1])
            except Exception:
                return None
        if line.startswith("ADC4:"):
            try:
                return 'adc4', int(line.split(":")[1])
            except Exception:
                return None
        if line.startswith("TEM:"):
            try:
                return 'temp', float(line.split(":")[1])
            except Exception:
                return None
        if line.startswith("HUM:"):
            try:
                return 'humi', float(line.split(":")[1])
            except Exception:
                return None
        return None

    @staticmethod
    def calc_resistance(adc_val, sample_r):
        """根据 ADC 值与采样电阻计算电阻值。"""
        try:
            return round(3.3 * adc_val * sample_r / (4095 * (5 - 3.3 * adc_val / 4095)), 3)
        except Exception:
            return 0.0
