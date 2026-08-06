"""帮助弹窗组件。"""
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QTextEdit, QPushButton


class HelpDialog(QDialog):
    HELP_TEXT = """
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

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("使用帮助")
        self.setFixedSize(550, 450)
        layout = QVBoxLayout()
        text_edit = QTextEdit()
        text_edit.setReadOnly(True)
        text_edit.setText(self.HELP_TEXT)
        text_edit.setStyleSheet("font-size: 11pt;")
        close_btn = QPushButton("关闭")
        close_btn.clicked.connect(self.close)
        layout.addWidget(text_edit)
        layout.addWidget(close_btn)
        self.setLayout(layout)
