"""图表管理：曲线数据、视图切换、轴匹配、滚动、网格、暂停。"""


class ChartManager:
    CHANNEL_RES = [10000, 100000, 1000000, 10000000, 100000000, 1000000000, 10000000000]

    def __init__(self, signals, data_state, max_data_points=200):
        self.sig = signals
        self.state = data_state
        self.max_data_points = max_data_points

        # 数据数组
        self.data_x = list(range(max_data_points))
        self.data_y1 = [0] * max_data_points
        self.data_y2 = [0] * max_data_points
        self.data_y3 = [0] * max_data_points
        self.data_y4 = [0] * max_data_points
        self.data_r1 = [0] * max_data_points
        self.data_r2 = [0] * max_data_points
        self.data_r3 = [0] * max_data_points
        self.data_r4 = [0] * max_data_points

        # 视图状态
        self.resistance_view = False
        self.adc1_visible = True
        self.adc2_visible = True
        self.adc3_visible = True
        self.adc4_visible = True
        self.plot_auto_scroll = False
        self.chart_paused = False

        # UI 引用（由外部注入）
        self.plot_widget = None
        self.curves = {}          # {1..4: PlotDataItem}
        self.curve_btns = {}      # {1..4: QPushButton}
        self.view_combo = None
        self.auto_scroll_btn = None
        self.chart_pause_btn = None
        self.grid_btn = None
        self.x_point_input = None

        # 通道选择旋钮引用（用于阻值计算）
        self.adc_ch_spins = {}

    def set_ui_widgets(self, plot_widget, curves, curve_btns, view_combo,
                       auto_scroll_btn, chart_pause_btn, grid_btn, x_point_input):
        self.plot_widget = plot_widget
        self.curves = curves
        self.curve_btns = curve_btns
        self.view_combo = view_combo
        self.auto_scroll_btn = auto_scroll_btn
        self.chart_pause_btn = chart_pause_btn
        self.grid_btn = grid_btn
        self.x_point_input = x_point_input

    def set_adc_ch_spins(self, spins):
        self.adc_ch_spins = spins

    # ===================== 数据更新 =====================
    def update_data(self, channel, val):
        """追加一个采样点到指定通道。"""
        ch = self.adc_ch_spins.get(channel)
        ch_idx = ch.value() if ch else 0
        R = self.CHANNEL_RES[ch_idx]
        if val >= 4095:
            r = float('inf')
        elif val == 0:
            r = 0.0
        else:
            r = R * val / (4095 - val)

        y_arrays = {1: self.data_y1, 2: self.data_y2, 3: self.data_y3, 4: self.data_y4}
        r_arrays = {1: self.data_r1, 2: self.data_r2, 3: self.data_r3, 4: self.data_r4}

        y_arr = y_arrays.get(channel)
        r_arr = r_arrays.get(channel)
        if y_arr is not None:
            y_arr.pop(0)
            y_arr.append(val)
        if r_arr is not None:
            r_arr.pop(0)
            r_arr.append(r)

        if self.plot_auto_scroll:
            self.data_x.pop(0)
            self.data_x.append(self.data_x[-1] + 1)

    def update_plot(self):
        """刷新图表曲线（按当前视图模式与可见性）。"""
        if not self.plot_widget:
            return
        if self.resistance_view:
            r_map = {1: self.data_r1, 2: self.data_r2, 3: self.data_r3, 4: self.data_r4}
            for idx, curve in self.curves.items():
                curve.setData(self.data_x, r_map[idx])
        else:
            y_map = {1: self.data_y1, 2: self.data_y2, 3: self.data_y3, 4: self.data_y4}
            for idx, curve in self.curves.items():
                curve.setData(self.data_x, y_map[idx])

        if self.plot_auto_scroll and len(self.data_x) > 0:
            x_max = self.data_x[-1]
            view_range = self.plot_widget.viewRange()
            x_span = view_range[0][1] - view_range[0][0]
            x_min = x_max - x_span
            self.plot_widget.setXRange(x_min, x_max, padding=0)

    def clear_data(self):
        """清空所有曲线数据。"""
        n = self.max_data_points
        self.data_x = list(range(n))
        self.data_y1 = [0] * n
        self.data_y2 = [0] * n
        self.data_y3 = [0] * n
        self.data_y4 = [0] * n
        self.data_r1 = [0] * n
        self.data_r2 = [0] * n
        self.data_r3 = [0] * n
        self.data_r4 = [0] * n
        self.update_plot()
        self.sig.log.emit("图表数据已清空")

    # ===================== 曲线显示切换 =====================
    def toggle_curve(self, idx):
        """切换第 idx 条曲线的可见性。"""
        vis_attrs = {1: 'adc1_visible', 2: 'adc2_visible',
                     3: 'adc3_visible', 4: 'adc4_visible'}
        attr = vis_attrs.get(idx)
        if attr is None:
            return
        current = getattr(self, attr)
        setattr(self, attr, not current)
        btn = self.curve_btns.get(idx)
        if btn:
            btn.setChecked(not current)
        curve = self.curves.get(idx)
        if curve:
            curve.setVisible(not current)

    # ===================== 视图切换 =====================
    def set_view_mode(self, index):
        """index=0 → ADC视图, index=1 → 阻值视图。"""
        self.resistance_view = (index == 1)
        if self.resistance_view:
            if self.plot_widget:
                self.plot_widget.setLabel("left", "Resistance")
                self.plot_widget.setYRange(0, 1)
            r_map = {1: self.data_r1, 2: self.data_r2, 3: self.data_r3, 4: self.data_r4}
            for idx, curve in self.curves.items():
                curve.setData(self.data_x, r_map[idx])
            self.sig.log.emit("已切换至阻值视图")
        else:
            if self.plot_widget:
                self.plot_widget.setLabel("left", "ADC Value")
                self.plot_widget.setYRange(0, 4095)
            y_map = {1: self.data_y1, 2: self.data_y2, 3: self.data_y3, 4: self.data_y4}
            for idx, curve in self.curves.items():
                curve.setData(self.data_x, y_map[idx])
            self.sig.log.emit("已切换至ADC视图")
        self.auto_match_axis()

    # ===================== 自动滚动 =====================
    def toggle_auto_scroll(self):
        self.plot_auto_scroll = not self.plot_auto_scroll
        if self.auto_scroll_btn:
            self.auto_scroll_btn.setChecked(self.plot_auto_scroll)
        self.sig.log.emit(
            "图表自动滚动已开启" if self.plot_auto_scroll else "图表自动滚动已关闭"
        )

    # ===================== 暂停 =====================
    def toggle_pause(self, checked):
        self.chart_paused = checked
        if self.chart_pause_btn:
            if checked:
                self.chart_pause_btn.setText("图表 ⏸")
                self.chart_pause_btn.setStyleSheet("background-color: #dc3545; color: white;")
                self.sig.log.emit("⏸ 图表已暂停")
            else:
                self.chart_pause_btn.setText("图表 ▶")
                self.chart_pause_btn.setStyleSheet("background-color: #28a745; color: white;")
                self.sig.log.emit("▶ 图表已恢复")

    # ===================== 网格 =====================
    def toggle_grid(self):
        if not self.grid_btn or not self.plot_widget:
            return
        checked = self.grid_btn.isChecked()
        self.plot_widget.showGrid(x=checked, y=checked)
        self.sig.log.emit("图表网格已开启" if checked else "图表网格已关闭")

    # ===================== 自动匹配轴 =====================
    def auto_match_axis(self):
        """单次点击：根据可见曲线数据自动调整 X/Y 轴范围。"""
        n = self.max_data_points
        if n == 0:
            return

        # 找最后一个非零数据点
        last_data_idx = -1
        y_arrays = [self.data_y1, self.data_y2, self.data_y3, self.data_y4]
        vis_flags = [self.adc1_visible, self.adc2_visible, self.adc3_visible, self.adc4_visible]
        for i in range(n - 1, -1, -1):
            if any(y_arrays[j][i] != 0 and vis_flags[j] for j in range(4)):
                last_data_idx = i
                break
        if last_data_idx < 0:
            return

        # Y 轴范围
        window_start = max(0, last_data_idx - n + 1)
        visible_data = []
        for i in range(window_start, last_data_idx + 1):
            for j in range(4):
                if vis_flags[j]:
                    visible_data.append(y_arrays[j][i])
        if not visible_data:
            return

        min_val = min(visible_data)
        max_val = max(visible_data)
        range_val = max_val - min_val
        margin = range_val * 0.1 if range_val > 0 else 100
        y_min = max(0, min_val - margin)
        y_max = min(4095, max_val + margin)
        if y_min == y_max:
            y_min = max(0, y_min - 100)
            y_max = min(4095, y_max + 100)
        if self.plot_widget:
            self.plot_widget.setYRange(y_min, y_max)

        # X 轴范围
        first_data_idx = -1
        for i in range(n):
            if any(y_arrays[j][i] != 0 and vis_flags[j] for j in range(4)):
                first_data_idx = i
                break
        if first_data_idx >= 0 and first_data_idx < last_data_idx and self.plot_widget:
            x_min = self.data_x[first_data_idx]
            x_max = self.data_x[last_data_idx]
            span = x_max - x_min
            margin_x = span * 0.02
            self.plot_widget.setXRange(x_min - margin_x, x_max + margin_x)

    # ===================== 采样点数调整 =====================
    def apply_point_count(self, x_points):
        """调整数据点数，保留数据连续性。"""
        old_n = self.max_data_points
        new_n = x_points

        y_arrays = [self.data_y1, self.data_y2, self.data_y3, self.data_y4]
        r_arrays = [self.data_r1, self.data_r2, self.data_r3, self.data_r4]

        if new_n > old_n:
            prepend_n = new_n - old_n
            for i in range(4):
                y_arrays[i][:] = [0] * prepend_n + y_arrays[i]
                r_arrays[i][:] = [0] * prepend_n + r_arrays[i]
        elif new_n < old_n:
            for i in range(4):
                y_arrays[i][:] = y_arrays[i][-new_n:]
                r_arrays[i][:] = r_arrays[i][-new_n:]

        self.data_x = list(range(new_n))
        self.max_data_points = new_n
        self.update_plot()
        self.sig.log.emit(f"图表设置已生效 | X点数:{x_points}")

    # ===================== 阻值查询 =====================
    def get_resistance_values(self, adc1, adc2, adc3, adc4):
        """根据 ADC 值和当前采样电阻通道计算 4 路阻值文本。返回 {idx: str}"""
        adc_vals = {1: adc1, 2: adc2, 3: adc3, 4: adc4}
        hw = {1: 'T1', 2: 'T2', 3: 'M1', 4: 'M2'}
        results = {}
        for i in range(1, 5):
            adc = adc_vals[i]
            ch_spin = self.adc_ch_spins.get(i)
            ch = ch_spin.value() if ch_spin else 0
            R = self.CHANNEL_RES[ch]
            if adc >= 4095:
                results[i] = f"{hw[i]}：∞ Ω"
            elif adc == 0:
                results[i] = f"{hw[i]}：0 Ω"
            else:
                r = R * adc / (4095 - adc)
                if r >= 1e9:
                    results[i] = f"{hw[i]}：{r/1e9:.2f} GΩ"
                elif r >= 1e6:
                    results[i] = f"{hw[i]}：{r/1e6:.2f} MΩ"
                elif r >= 1e3:
                    results[i] = f"{hw[i]}：{r/1e3:.2f} KΩ"
                else:
                    results[i] = f"{hw[i]}：{r:.1f} Ω"
        return results
