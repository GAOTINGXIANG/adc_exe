"""数据导出管理：CSV 导出、缓存清空。"""
import csv
import os
from datetime import datetime

from PyQt5.QtWidgets import QMessageBox, QFileDialog


class ExportManager:
    def __init__(self, state, signals, parent_widget):
        self.state = state
        self.sig = signals
        self.parent = parent_widget

    def clear_cache(self):
        """清空内存中缓存的待导出数据。"""
        self.state.clear_save_data()
        self.sig.log.emit("已清空待导出缓存数据")

    def export_to_csv(self):
        """将缓存数据导出为 CSV 文件。"""
        data = self.state.get_save_data()
        if not data:
            QMessageBox.information(self.parent, "提示", "暂无可导出数据！")
            return
        file_path, _ = QFileDialog.getSaveFileName(
            self.parent, "保存数据",
            f"传感器数据_{datetime.now().strftime('%Y%m%d%H%M%S')}.csv",
            "CSV文件(*.csv);;所有文件(*)"
        )
        if not file_path:
            return
        try:
            with open(file_path, "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.writer(f)
                writer.writerow(["时间", "T1", "T2", "M1", "M2", "温度(℃)", "湿度(%RH)"])
                writer.writerows(data)
            self.sig.log.emit(f"数据导出成功：{os.path.basename(file_path)}")
            QMessageBox.information(self.parent, "成功", "数据导出完成！")
        except Exception as e:
            self.sig.log.emit(f"导出失败：{str(e)}")
            QMessageBox.warning(self.parent, "错误", f"导出失败：{str(e)}")
