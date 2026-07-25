from PyQt5.QtCore import QObject, pyqtSignal


class Signals(QObject):
    log = pyqtSignal(str)
    serial_lost = pyqtSignal()
