"""ADC 采样通道自动匹配 — 四路并行状态机。"""
from PyQt5.QtCore import QTimer


class ChannelMatcher:
    CHANNEL_NAMES = ["10K", "100K", "1M", "10M", "100M", "1G", "10G"]
    HW_NAMES = {1: 'T1', 2: 'T2', 3: 'M1', 4: 'M2'}

    def __init__(self, signals, state, device_ctrl):
        self.sig = signals
        self.state = state
        self.device_ctrl = device_ctrl

        # UI 控件引用，由外部注入
        self.adc_ch_spins = {}     # {1..4: QSpinBox}
        self.range_low_spin = None
        self.range_high_spin = None
        self.delay_spin = None
        self.auto_match_btn = None

        # 内部状态
        self.running = False
        self.match_timer = QTimer()
        self.match_timer.timeout.connect(self._tick)
        self.match_state = {}

    def set_ui_widgets(self, adc_ch_spins, range_low_spin, range_high_spin,
                       delay_spin, auto_match_btn):
        self.adc_ch_spins = adc_ch_spins
        self.range_low_spin = range_low_spin
        self.range_high_spin = range_high_spin
        self.delay_spin = delay_spin
        self.auto_match_btn = auto_match_btn

    def on_channel_changed(self, adc_idx, val):
        """用户手动切换采样通道时触发：更新后缀并发送指令。"""
        spin = self.adc_ch_spins.get(adc_idx)
        if spin:
            spin.setSuffix(f"  ({self.CHANNEL_NAMES[val]})")
        self.device_ctrl.send_channel_cmd(adc_idx, val)

    def start_auto_match(self):
        """开始四路并行自动匹配。"""
        if self.running:
            return
        if not self.device_ctrl._send(""):
            self.sig.log.emit("❌ 未连接，无法执行自动匹配")
            return

        self.running = True
        if self.auto_match_btn:
            self.auto_match_btn.setEnabled(False)
        for w in [self.range_low_spin, self.range_high_spin, self.delay_spin]:
            if w:
                w.setEnabled(False)

        range_low = self.range_low_spin.value() if self.range_low_spin else 100
        range_high = self.range_high_spin.value() if self.range_high_spin else 4000
        delay_ms = self.delay_spin.value() if self.delay_spin else 20

        self.match_state = {
            1: {'channel': 6, 'phase': 'send', 'ticks': 0},
            2: {'channel': 6, 'phase': 'send', 'ticks': 0},
            3: {'channel': 6, 'phase': 'send', 'ticks': 0},
            4: {'channel': 6, 'phase': 'send', 'ticks': 0},
            'results': {},
        }
        self.sig.log.emit(
            f"=== 开始自动匹配（四路并行），范围：[{range_low} ~ {range_high}]，延迟：{delay_ms}ms ==="
        )
        self.match_timer.start(delay_ms)

    def _tick(self):
        """匹配定时器回调（每路独立状态机）。"""
        range_low = self.range_low_spin.value() if self.range_low_spin else 100
        range_high = self.range_high_spin.value() if self.range_high_spin else 4000
        delay_ms = self.delay_spin.value() if self.delay_spin else 20

        adc1, adc2, adc3, adc4 = self.state.get_adc_values()
        vals = {1: adc1, 2: adc2, 3: adc3, 4: adc4}

        all_done = True
        for adc in range(1, 5):
            st = self.match_state.get(adc)
            if st is None:
                continue
            all_done = False

            ch = st['channel']
            phase = st['phase']
            ch_name = self.CHANNEL_NAMES[ch]

            if phase == 'send':
                send_str = f"CHANNEL{adc}:{ch}\n"
                if self.device_ctrl._send(send_str):
                    self.sig.log.emit(
                        f"{self.HW_NAMES[adc]}: → 通道{ch}({ch_name}) 已发送切换指令，等待{delay_ms}ms读取..."
                    )
                    st['phase'] = 'wait'
                    st['ticks'] = 0

            elif phase == 'wait':
                st['ticks'] += 1
                if st['ticks'] >= 1:
                    val = vals[adc]
                    if range_low <= val <= range_high:
                        self.match_state['results'][adc] = ch
                        self.sig.log.emit(
                            f"{self.HW_NAMES[adc]}: 通道{ch}({ch_name}) ✅ 匹配成功 "
                            f"(值={val} 在范围[{range_low}~{range_high}])"
                        )
                        spin = self.adc_ch_spins.get(adc)
                        if spin:
                            spin.blockSignals(True)
                            spin.setValue(ch)
                            spin.setSuffix(f"  ({ch_name})")
                            spin.blockSignals(False)
                        self.match_state[adc] = None
                    else:
                        st['channel'] -= 1
                        if st['channel'] < 0:
                            self.match_state['results'][adc] = None
                            self.sig.log.emit(
                                f"{self.HW_NAMES[adc]}: 通道{ch}({ch_name}) 值={val} "
                                f"不在范围[{range_low}~{range_high}]，已是最后一个通道"
                            )
                            self.sig.log.emit(
                                f"{self.HW_NAMES[adc]}: ❌ 所有通道(6→0)均未匹配成功"
                            )
                            self.match_state[adc] = None
                        else:
                            next_ch = st['channel']
                            next_name = self.CHANNEL_NAMES[next_ch]
                            self.sig.log.emit(
                                f"{self.HW_NAMES[adc]}: 通道{ch}({ch_name}) 值={val} "
                                f"不在范围[{range_low}~{range_high}]，→ 通道{next_ch}({next_name})"
                            )
                            st['phase'] = 'send'
                            st['ticks'] = 0

        if all_done:
            self._done()

    def _done(self):
        """匹配完成，恢复 UI 状态并打印结果。"""
        self.match_timer.stop()
        self.running = False
        if self.auto_match_btn:
            self.auto_match_btn.setEnabled(True)
        for w in [self.range_low_spin, self.range_high_spin, self.delay_spin]:
            if w:
                w.setEnabled(True)

        results = self.match_state.get('results', {})
        matched = {k: v for k, v in results.items() if v is not None}
        failed = {k for k, v in results.items() if v is None}
        self.sig.log.emit(f"=== 自动匹配完成 成功:{len(matched)}/4 ===")
        for adc, ch in matched.items():
            self.sig.log.emit(f"{self.HW_NAMES[adc]} → 通道{ch}({self.CHANNEL_NAMES[ch]})")
        for adc in failed:
            self.sig.log.emit(f"{self.HW_NAMES[adc]} → 未匹配成功")

    def is_running(self):
        return self.running
