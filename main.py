import sys

from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import QIcon, QPixmap, QPainter, QColor, QAction, QLinearGradient, QBrush
from PySide6.QtWidgets import QApplication, QSystemTrayIcon, QMenu, QMessageBox

from models import default_config
from storage import Storage
from ui.main_window import MainWindow


def make_icon() -> QIcon:
    pm = QPixmap(256, 256)
    pm.fill(Qt.transparent)
    painter = QPainter(pm)
    painter.setRenderHint(QPainter.Antialiasing)

    # 渐变方片（蓝 400 → 蓝 700），与 FloatLog.ico 同款
    pad = 15
    corner = 56
    rect = QRectF(pad, pad, 256 - 2 * pad, 256 - 2 * pad)
    grad = QLinearGradient(rect.topLeft(), rect.bottomRight())
    grad.setColorAt(0.0, QColor("#60a5fa"))
    grad.setColorAt(1.0, QColor("#1d4ed8"))
    painter.setBrush(QBrush(grad))
    painter.setPen(Qt.NoPen)
    painter.drawRoundedRect(rect, corner, corner)

    # 三条白色圆角日志行（左对齐，宽度错落）
    painter.setBrush(QColor(255, 255, 255, 245))
    lx = 54
    line_h = 19
    avail = 256 - 2 * lx
    for wfrac, y in [(0.62, 77), (0.46, 118), (0.56, 159)]:
        painter.drawRoundedRect(
            QRectF(lx, y, wfrac * avail, line_h), line_h / 2, line_h / 2
        )

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
