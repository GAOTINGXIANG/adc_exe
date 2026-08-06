"""左侧面板：接收模式组、状态标签、图表控制组、波形图。"""
import pyqtgraph as pg
from PyQt5.QtWidgets import (
    QHBoxLayout, QVBoxLayout, QGroupBox, QRadioButton,
    QLabel, QComboBox, QPushButton, QLineEdit
)
from PyQt5.QtCore import Qt

from config import MAX_DATA_POINTS_DEFAULT, TCP_SERVER_IP, TCP_SERVER_PORT


class LeftPanel:
    """构建左侧面板的所有 UI 控件。"""

    def __init__(self):
        # ---- 接收模式组 ----
        self.mode_group = QGroupBox("接收模式")
        self.net_radio = QRadioButton("网络接收")
        self.uart_radio = QRadioButton("串口接收")
        self.uart_radio.setChecked(True)

        self.port_label = QLabel("COM口:")
        self.port_combo = QComboBox()
        self.refresh_btn = QPushButton("刷新串口")
        self.connect_btn = QPushButton("连接")
        self.disconnect_btn = QPushButton("断开")

        self.ip_label = QLabel("服务器IP:")
        self.ip_input = QLineEdit(TCP_SERVER_IP)
        self.port_tcp_label = QLabel("端口:")
        self.port_tcp_input = QLineEdit(str(TCP_SERVER_PORT))

        self._build_mode_group()

        # ---- 状态标签 ----
        self.status_label = QLabel("状态：未连接")
        font = self.status_label.font()
        font.setPointSize(11)
        self.status_label.setFont(font)

        # ---- 图表控制组 ----
        self.plot_control_group = QGroupBox("图表控制")

        self.x_point_input = QLineEdit(str(MAX_DATA_POINTS_DEFAULT))
        self.x_point_input.setFixedWidth(60)
        self.apply_plot_btn = QPushButton("应用设置")
        self.apply_plot_btn.setFixedWidth(80)

        self.adc1_btn = QPushButton("T1")
        self.adc1_btn.setCheckable(True)
        self.adc1_btn.setChecked(True)
        self.adc1_btn.setStyleSheet("background-color: red; color: white;")

        self.adc2_btn = QPushButton("T2")
        self.adc2_btn.setCheckable(True)
        self.adc2_btn.setChecked(True)
        self.adc2_btn.setStyleSheet("background-color: blue; color: white;")

        self.adc3_btn = QPushButton("M1")
        self.adc3_btn.setCheckable(True)
        self.adc3_btn.setChecked(True)
        self.adc3_btn.setStyleSheet("background-color: purple; color: white;")

        self.adc4_btn = QPushButton("M2")
        self.adc4_btn.setCheckable(True)
        self.adc4_btn.setChecked(True)
        self.adc4_btn.setStyleSheet("background-color: green; color: white;")

        self.view_combo = QComboBox()
        self.view_combo.addItems(["ADC视图", "阻值视图"])
        self.view_combo.setFixedWidth(90)

        self.auto_scroll_btn = QPushButton("自动滚动")
        self.auto_scroll_btn.setCheckable(True)
        self.auto_scroll_btn.setChecked(False)
        self.auto_scroll_btn.setFixedWidth(80)

        self.auto_match_btn = QPushButton("自动匹配")
        self.auto_match_btn.setFixedWidth(80)

        self.chart_pause_btn = QPushButton("图表 ▶")
        self.chart_pause_btn.setCheckable(True)
        self.chart_pause_btn.setChecked(False)
        self.chart_pause_btn.setFixedWidth(70)
        self.chart_pause_btn.setStyleSheet("background-color: #28a745; color: white;")

        self.clear_plot_btn = QPushButton("清除图表")
        self.clear_plot_btn.setFixedWidth(80)

        self.grid_btn = QPushButton("网格")
        self.grid_btn.setCheckable(True)
        self.grid_btn.setChecked(False)
        self.grid_btn.setFixedWidth(60)

        self._build_plot_control_group()

        # ---- 波形图 ----
        self.plot_widget = pg.PlotWidget()
        self.plot_widget.setTitle("实时波形", color="w", size="14pt")
        self.plot_widget.setLabel("left", "ADC Value")
        self.plot_widget.setLabel("bottom", "Points")
        self.plot_widget.setYRange(0, 4095)

        self.curve1 = self.plot_widget.plot(
            [], [], pen=pg.mkPen(color="red", width=2),
            symbol="o", symbolSize=4, symbolBrush="red", name="T1"
        )
        self.curve2 = self.plot_widget.plot(
            [], [], pen=pg.mkPen(color="blue", width=2),
            symbol="o", symbolSize=4, symbolBrush="blue", name="T2"
        )
        self.curve3 = self.plot_widget.plot(
            [], [], pen=pg.mkPen(color="purple", width=2),
            symbol="o", symbolSize=4, symbolBrush="purple", name="M1"
        )
        self.curve4 = self.plot_widget.plot(
            [], [], pen=pg.mkPen(color="green", width=2),
            symbol="o", symbolSize=4, symbolBrush="green", name="M2"
        )
        self.plot_widget.addLegend()

    def _build_mode_group(self):
        layout = QHBoxLayout()
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(8)
        layout.addWidget(self.net_radio)
        layout.addWidget(self.uart_radio)
        layout.addWidget(self.port_label)
        layout.addWidget(self.port_combo)
        layout.addWidget(self.ip_label)
        layout.addWidget(self.ip_input)
        layout.addWidget(self.port_tcp_label)
        layout.addWidget(self.port_tcp_input)
        layout.addWidget(self.refresh_btn)
        layout.addWidget(self.connect_btn)
        layout.addWidget(self.disconnect_btn)
        self.mode_group.setLayout(layout)

    def _build_plot_control_group(self):
        layout = QHBoxLayout()
        layout.setContentsMargins(10, 5, 10, 5)
        layout.setSpacing(10)

        layout.addWidget(QLabel("采样点数:"))
        layout.addWidget(self.x_point_input)
        layout.addWidget(self.apply_plot_btn)
        layout.addSpacing(20)

        layout.addWidget(QLabel("曲线选择:"))
        layout.addWidget(self.adc1_btn)
        layout.addWidget(self.adc2_btn)
        layout.addWidget(self.adc3_btn)
        layout.addWidget(self.adc4_btn)
        layout.addStretch()

        layout.addWidget(QLabel("视图:"))
        layout.addWidget(self.view_combo)
        layout.addWidget(self.auto_scroll_btn)
        layout.addWidget(self.auto_match_btn)
        layout.addWidget(self.chart_pause_btn)
        layout.addWidget(self.clear_plot_btn)
        layout.addWidget(self.grid_btn)

        self.plot_control_group.setLayout(layout)

    def build_layout(self):
        """构建并返回左侧整体布局。"""
        top_layout = QHBoxLayout()
        top_layout.setContentsMargins(0, 0, 0, 0)
        top_layout.setSpacing(15)
        top_layout.addWidget(self.mode_group)

        left_layout = QVBoxLayout()
        left_layout.setContentsMargins(8, 8, 8, 8)
        left_layout.setSpacing(12)
        left_layout.addLayout(top_layout)
        left_layout.addWidget(self.status_label)
        left_layout.addWidget(self.plot_control_group)
        left_layout.addWidget(self.plot_widget)
        return left_layout
