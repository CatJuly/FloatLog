import sys

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon, QPixmap, QPainter, QColor, QAction
from PySide6.QtWidgets import QApplication, QSystemTrayIcon, QMenu, QMessageBox

from models import default_config
from storage import Storage
from ui.main_window import MainWindow


def make_icon() -> QIcon:
    pm = QPixmap(64, 64)
    pm.fill(Qt.transparent)
    painter = QPainter(pm)
    painter.setRenderHint(QPainter.Antialiasing)
    painter.setBrush(QColor("#3b82f6"))
    painter.setPen(Qt.NoPen)
    painter.drawRoundedRect(6, 6, 52, 52, 12, 12)
    painter.setPen(QColor("white"))
    font = painter.font()
    font.setBold(True)
    font.setPixelSize(28)
    painter.setFont(font)
    painter.drawText(pm.rect(), Qt.AlignCenter, "L")
    painter.end()
    return QIcon(pm)


def main() -> int:
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    storage = Storage()
    storage.ensure_dirs()

    try:
        config = storage.load_config()
    except Exception:
        config = default_config()
        QMessageBox.warning(None, "提示", "配置文件读取失败，已使用默认设置")

    try:
        storage.list_servers()
    except Exception:
        storage.save_servers([])
        QMessageBox.warning(None, "提示", "服务器列表读取失败，已重置为空列表")

    window = MainWindow(storage, config)

    tray = QSystemTrayIcon(make_icon(), app)
    menu = QMenu()
    show_action = QAction("显示")
    show_action.triggered.connect(window.show)
    quit_action = QAction("退出")
    quit_action.triggered.connect(app.quit)
    menu.addAction(show_action)
    menu.addAction(quit_action)
    tray.setContextMenu(menu)
    tray.activated.connect(
        lambda reason: window.show() if reason == QSystemTrayIcon.Trigger else None
    )
    tray.show()

    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
