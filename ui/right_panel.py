"""右侧面板：工具/控制/采样通道/温度百分比/加热台/温湿度/阻值/日志。"""
from PyQt5.QtWidgets import (
    QHBoxLayout, QVBoxLayout, QGroupBox,
    QLabel, QPushButton, QLineEdit, QSlider, QTextEdit,
    QCheckBox, QSpinBox, QWidget
)
from PyQt5.QtCore import Qt


class RightPanel:
    """构建右侧面板的所有 UI 控件。"""

    def __init__(self):
        # ---- 工具组 ----
        self.tool_group = QGroupBox("工具")
        self.help_btn = QPushButton("说明")
        self.source_btn = QPushButton("源码")
        self.export_btn = QPushButton("导出CSV数据")
        self.clear_data_btn = QPushButton("清空缓存数据")
        self._build_tool_group()

        # ---- 控制组 ----
        self.ctrl_group = QGroupBox("控制")
        self.sample_freq_label = QLabel("频率(HZ/S):")
        self.sample_freq_input = QLineEdit("1.0")
        self.sample_freq_input.setFixedWidth(60)
        self.sample_freq_apply_btn = QPushButton("应用")
        self.sample_freq_apply_btn.setFixedWidth(50)
        self._build_ctrl_group()

        # ---- 采样通道组 ----
        self.adc_ch_group = QGroupBox("采样通道")
        self.adc_ch_spins = {}       # {1..4: QSpinBox}
        self.adc_ch_labels = {}
        self.adc_range_low_spin = QSpinBox()
        self.adc_range_high_spin = QSpinBox()
        self.adc_delay_spin = QSpinBox()
        self.adc_auto_match_btn = QPushButton("自动匹配")
        self._build_adc_ch_group()

        # ---- 温度百分比组 ----
        self.adc_temp_group = QGroupBox("温度百分比")
        self.adc_temp_sliders = {}   # {1..4: QSlider}
        self.adc_temp_labels = {}    # {1..4: QLabel}
        self._build_adc_temp_group()

        # ---- 风扇与加热台组 ----
        self.heater_group = QGroupBox("风扇与加热台控制")
        self.heater_on_btn = QPushButton("开")
        self.heater_off_btn = QPushButton("关")
        self.fan_on_btn = QPushButton("开")
        self.fan_off_btn = QPushButton("关")
        self._build_heater_group()

        # ---- 温湿度组 ----
        self.env_group = QGroupBox("温湿度读取值")
        self.temp_label = QLabel("温度：0.00")
        self.humi_label = QLabel("湿度：0.00")
        self._build_env_group()

        # ---- 阻值计算组 ----
        self.res_calc_group = QGroupBox("阻值计算")
        self.res_labels = {}         # {1..4: QLabel}
        self._build_res_calc_group()

        # ---- 日志组 ----
        self.log_group = QGroupBox("实时日志")
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setStyleSheet("font-size: 11pt;")
        self.clear_log_btn = QPushButton("清空日志")
        self.auto_scroll_check = QCheckBox("自动滚动")
        self.auto_scroll_check.setChecked(True)
        self.log_pause_btn = QPushButton("日志 ▶")
        self.log_pause_btn.setCheckable(True)
        self.log_pause_btn.setChecked(False)
        self.log_pause_btn.setFixedWidth(70)
        self.log_pause_btn.setStyleSheet("background-color: #28a745; color: white;")
        self.log_max_lines_spin = QSpinBox()
        self._build_log_group()

    # ===================== 各分组构建 =====================

    def _build_tool_group(self):
        self.help_btn.setFixedSize(70, 26)
        self.source_btn.setFixedSize(70, 26)
        layout = QHBoxLayout()
        layout.addWidget(self.help_btn)
        layout.addWidget(self.source_btn)
        layout.addWidget(self.export_btn)
        layout.addWidget(self.clear_data_btn)
        self.tool_group.setLayout(layout)

    def _build_ctrl_group(self):
        layout = QHBoxLayout()
        layout.setSpacing(10)
        layout.addWidget(self.sample_freq_label)
        layout.addWidget(self.sample_freq_input)
        layout.addWidget(self.sample_freq_apply_btn)
        layout.addStretch()
        self.ctrl_group.setLayout(layout)

    def _build_adc_ch_group(self):
        channel_names = ["10K", "100K", "1M", "10M", "100M", "1G", "10G"]
        hw_names = {1: 'T1', 2: 'T2', 3: 'M1', 4: 'M2'}

        grid = QVBoxLayout()
        grid.setSpacing(6)

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
                label = QLabel(f"{hw_names[i]}:")
                self.adc_ch_spins[i] = spin
                self.adc_ch_labels[i] = label
                row_layout.addWidget(label)
                row_layout.addWidget(spin)
            row_layout.addStretch()
            grid.addLayout(row_layout)

        # 底部：范围/延迟/自动匹配
        match_row = QHBoxLayout()
        match_row.setSpacing(6)
        match_row.addWidget(QLabel("范围:"))
        self.adc_range_low_spin.setRange(0, 4095)
        self.adc_range_low_spin.setValue(100)
        self.adc_range_low_spin.setFixedWidth(65)
        match_row.addWidget(self.adc_range_low_spin)
        match_row.addWidget(QLabel("~"))
        self.adc_range_high_spin.setRange(0, 4095)
        self.adc_range_high_spin.setValue(4000)
        self.adc_range_high_spin.setFixedWidth(65)
        match_row.addWidget(self.adc_range_high_spin)
        match_row.addWidget(QLabel("  延迟:"))
        self.adc_delay_spin.setRange(10, 500)
        self.adc_delay_spin.setValue(20)
        self.adc_delay_spin.setSuffix("ms")
        self.adc_delay_spin.setFixedWidth(70)
        match_row.addWidget(self.adc_delay_spin)
        self.adc_auto_match_btn.setFixedWidth(80)
        match_row.addWidget(self.adc_auto_match_btn)
        match_row.addStretch()

        inner = QVBoxLayout()
        inner.addLayout(grid)
        inner.addLayout(match_row)
        self.adc_ch_group.setLayout(inner)

    def _build_adc_temp_group(self):
        hw_names = {1: 'T1', 2: 'T2', 3: 'M1', 4: 'M2'}
        layout = QVBoxLayout()
        layout.setSpacing(8)

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

                slider.valueChanged.connect(
                    lambda val, idx=i, lb=label: lb.setText(f"{hw_names[idx]}：{val} %")
                )
                # send_btn click will be wired by MainWindow

                col_layout.addWidget(slider)
                col_layout.addLayout(btn_row)

                self.adc_temp_sliders[i] = slider
                self.adc_temp_labels[i] = label
                row_layout.addWidget(col_widget)
            layout.addLayout(row_layout)

        self.adc_temp_group.setLayout(layout)

    def _build_heater_group(self):
        layout = QHBoxLayout()
        layout.setSpacing(10)
        self.heater_on_btn.setFixedWidth(50)
        self.heater_off_btn.setFixedWidth(50)
        self.fan_on_btn.setFixedWidth(50)
        self.fan_off_btn.setFixedWidth(50)

        layout.addWidget(QLabel("加热台:"))
        layout.addWidget(self.heater_on_btn)
        layout.addWidget(self.heater_off_btn)
        layout.addSpacing(15)
        layout.addWidget(QLabel("风扇:"))
        layout.addWidget(self.fan_on_btn)
        layout.addWidget(self.fan_off_btn)
        layout.addStretch()
        self.heater_group.setLayout(layout)

    def _build_env_group(self):
        font_env = self.temp_label.font()
        font_env.setPointSize(12)
        self.temp_label.setFont(font_env)
        self.humi_label.setFont(font_env)
        layout = QHBoxLayout()
        layout.addWidget(self.temp_label)
        layout.addWidget(self.humi_label)
        self.env_group.setLayout(layout)

    def _build_res_calc_group(self):
        hw_names = {1: 'T1', 2: 'T2', 3: 'M1', 4: 'M2'}
        layout = QVBoxLayout()
        layout.setSpacing(4)
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
            layout.addLayout(row_layout)
        self.res_calc_group.setLayout(layout)

    def _build_log_group(self):
        self.log_max_lines_spin.setRange(10, 10000)
        self.log_max_lines_spin.setValue(100)
        self.log_max_lines_spin.setFixedWidth(80)

        btn_layout = QHBoxLayout()
        btn_layout.addWidget(QLabel("日志缓存条数:"))
        btn_layout.addWidget(self.log_max_lines_spin)
        btn_layout.addStretch()
        btn_layout.addWidget(self.log_pause_btn)
        btn_layout.addWidget(self.auto_scroll_check)
        btn_layout.addWidget(self.clear_log_btn)

        layout = QVBoxLayout()
        layout.addWidget(self.log_text)
        layout.addLayout(btn_layout)
        self.log_group.setLayout(layout)

    def build_layout(self):
        """构建并返回右侧整体布局。"""
        layout = QVBoxLayout()
        layout.setSpacing(10)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.addWidget(self.tool_group)
        layout.addWidget(self.ctrl_group)
        layout.addWidget(self.adc_ch_group)
        layout.addWidget(self.adc_temp_group)
        layout.addWidget(self.heater_group)
        layout.addWidget(self.env_group)
        layout.addWidget(self.res_calc_group)
        layout.addWidget(self.log_group)
        return layout
