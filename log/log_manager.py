"""日志管理：格式化追加、清空、暂停/恢复、自动滚动、缓存条数限制。"""
from datetime import datetime


class LogManager:
    def __init__(self, log_text_widget, signals, max_log_lines=100):
        self.log_text = log_text_widget
        self.sig = signals
        self.max_log_lines = max_log_lines
        self.auto_scroll_log = True
        self.log_paused = False

    def add_log(self, msg):
        """格式化并追加一条日志（处理暂停与自动滚动）。"""
        if self.log_paused:
            return
        scrollbar = self.log_text.verticalScrollBar()
        saved_pos = scrollbar.value() if scrollbar else 0

        lines = self.log_text.toPlainText().splitlines()
        if len(lines) >= self.max_log_lines:
            lines = lines[-self.max_log_lines + 1:]
            self.log_text.setPlainText("\n".join(lines))
        now = datetime.now().strftime("%H:%M:%S")
        self.log_text.append(f"[{now}] {msg}")

        if self.auto_scroll_log:
            cursor = self.log_text.textCursor()
            cursor.movePosition(cursor.End)
            self.log_text.setTextCursor(cursor)
        else:
            if scrollbar:
                scrollbar.setValue(saved_pos)

    def clear(self):
        """清空日志文本框。"""
        self.log_text.clear()
        self.sig.log.emit("已手动清空日志")

    def set_auto_scroll(self, enabled):
        """设置自动滚动开关。"""
        self.auto_scroll_log = enabled

    def set_max_lines(self, val):
        """设置最大日志缓存条数并立即裁剪。"""
        self.max_log_lines = val
        lines = self.log_text.toPlainText().splitlines()
        if len(lines) > val:
            lines = lines[-val:]
            self.log_text.setPlainText("\n".join(lines))

    def set_paused(self, paused):
        """设置日志暂停/恢复。"""
        self.log_paused = paused
