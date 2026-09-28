from __future__ import annotations

from PySide6.QtCore import Qt, QPoint, QThread, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QListWidget,
    QListWidgetItem, QPlainTextEdit, QCheckBox, QMessageBox, QAbstractItemView,
)

from models import Server, AppConfig
from storage import Storage
from claude_client import ClaudeResult, run as run_claude

from .server_dialog import ServerDialog
from .settings_dialog import SettingsDialog


class TitleBar(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._drag_pos: QPoint | None = None
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)

        title = QLabel("FloatLog")
        title.setStyleSheet("font-weight: bold;")

        self.pin_check = QCheckBox("置顶")
        self.pin_check.toggled.connect(self._toggle_pin)

        self.min_btn = QPushButton("—")
        self.min_btn.setFixedWidth(24)
        self.min_btn.clicked.connect(lambda: self.window().showMinimized())

        self.close_btn = QPushButton("×")
        self.close_btn.setFixedWidth(24)
        self.close_btn.clicked.connect(self._close_to_tray)

        layout.addWidget(title)
        layout.addStretch(1)
        layout.addWidget(self.pin_check)
        layout.addWidget(self.min_btn)
        layout.addWidget(self.close_btn)

    def _toggle_pin(self, on: bool) -> None:
        self.window().setWindowFlag(Qt.WindowStaysOnTopHint, on)
        self.window().show()

    def _close_to_tray(self) -> None:
        self.window().hide()

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.window().frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event) -> None:
        if self._drag_pos is not None and event.buttons() & Qt.LeftButton:
            self.window().move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()

    def mouseReleaseEvent(self, event) -> None:
        self._drag_pos = None


class MainWindow(QWidget):
    def __init__(self, storage: Storage, config: AppConfig) -> None:
        super().__init__()
        self.storage = storage
        self.config = config
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Tool)
        self.resize(380, 540)
        self.setWindowTitle("FloatLog")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(TitleBar(self))

        body = QVBoxLayout()
        body.setContentsMargins(8, 8, 8, 8)
        body.setSpacing(6)

        self.server_list = QListWidget()
        self.server_list.setSelectionMode(QAbstractItemView.ExtendedSelection)
        body.addWidget(self.server_list, stretch=3)

        list_btns = QHBoxLayout()
        add_btn = QPushButton("添加服务器")
        add_btn.clicked.connect(self.add_server)
        edit_btn = QPushButton("编辑")
        edit_btn.clicked.connect(self.edit_server)
        del_btn = QPushButton("删除")
        del_btn.clicked.connect(self.delete_server)
        settings_btn = QPushButton("设置")
        settings_btn.clicked.connect(self.open_settings)
        list_btns.addWidget(add_btn)
        list_btns.addWidget(edit_btn)
        list_btns.addWidget(del_btn)
        list_btns.addWidget(settings_btn)
        body.addLayout(list_btns)

        body.addWidget(QLabel("提示词（要 Claude Code 做什么）："))
        self.prompt_edit = QPlainTextEdit()
        self.prompt_edit.setFixedHeight(80)
        self.prompt_edit.setPlaceholderText("例如：分析今天的错误日志")
        body.addWidget(self.prompt_edit)

        self.send_btn = QPushButton("发送分析")
        self.send_btn.clicked.connect(self.send)
        body.addWidget(self.send_btn)

        body.addWidget(QLabel("结果："))
        self.result_view = QPlainTextEdit()
        self.result_view.setReadOnly(True)
        self.result_view.setPlaceholderText("分析结果将显示在这里")
        body.addWidget(self.result_view, stretch=4)

        copy_btn = QPushButton("复制结果")
        copy_btn.clicked.connect(self.copy_result)
        body.addWidget(copy_btn)

        layout.addLayout(body)

        self.refresh_list()

    # ── 服务器列表 ──────────────────────────────
    def refresh_list(self) -> None:
        self.server_list.clear()
        for server in self.storage.list_servers():
            item = QListWidgetItem(f"{server.name}  ({server.host}:{server.port})")
            item.setData(Qt.UserRole, server)
            self.server_list.addItem(item)

    def _selected_servers(self) -> list[Server]:
        return [it.data(Qt.UserRole) for it in self.server_list.selectedItems()]

    def add_server(self) -> None:
        dialog = ServerDialog(self)
        if dialog.exec():
            servers = self.storage.list_servers()
            servers.append(dialog.result_server())
            self.storage.save_servers(servers)
            self.refresh_list()

    def edit_server(self) -> None:
        items = self.server_list.selectedItems()
        if not items:
            QMessageBox.information(self, "提示", "请先选择一台服务器")
            return
        current = items[0].data(Qt.UserRole)
        dialog = ServerDialog(self, current)
        if dialog.exec():
            new = dialog.result_server()
            servers = self.storage.list_servers()
            for i, s in enumerate(servers):
                if s == current:
                    servers[i] = new
                    break
            self.storage.save_servers(servers)
            self.refresh_list()

    def delete_server(self) -> None:
        selected = self._selected_servers()
        if not selected:
            QMessageBox.information(self, "提示", "请先选择要删除的服务器")
            return
        if QMessageBox.question(self, "确认",
                                f"删除选中的 {len(selected)} 台服务器？") != QMessageBox.Yes:
            return
        servers = [s for s in self.storage.list_servers() if s not in selected]
        self.storage.save_servers(servers)
        self.refresh_list()

    def open_settings(self) -> None:
        dialog = SettingsDialog(self, self.config)
        if dialog.exec():
            self.config = dialog.result_config()
            self.storage.save_config(self.config)

    # ── 发送分析 ─────────────────────────────────
    def send(self) -> None:
        servers = self._selected_servers()
        if not servers:
            QMessageBox.warning(self, "提示", "请先选择至少一台服务器")
            return
        user_prompt = self.prompt_edit.toPlainText().strip()
        if not user_prompt:
            QMessageBox.warning(self, "提示", "请输入提示词")
            return

        self.send_btn.setEnabled(False)
        self.send_btn.setText("运行中…")
        self.result_view.setPlainText("正在分析，请稍候…")

        if getattr(self, "_worker", None) is not None and self._worker.isRunning():
            self._worker.wait()
        self._worker = Worker(self.config, servers, user_prompt)
        self._worker.finished.connect(self._on_finished)
        self._worker.start()

    def _on_finished(self, result) -> None:
        self.send_btn.setEnabled(True)
        self.send_btn.setText("发送分析")
        if result.ok:
            self.result_view.setPlainText(result.output or "(无输出)")
        else:
            self.result_view.setPlainText(f"[{result.status}] {result.error}")

    def copy_result(self) -> None:
        from PySide6.QtWidgets import QApplication
        QApplication.clipboard().setText(self.result_view.toPlainText())


class Worker(QThread):
    finished = Signal(object)

    def __init__(self, config: AppConfig, servers: list[Server], user_prompt: str) -> None:
        super().__init__()
        self._config = config
        self._servers = servers
        self._user_prompt = user_prompt

    def run(self) -> None:
        try:
            result = run_claude(self._config, self._servers, self._user_prompt)
        except Exception as exc:
            result = ClaudeResult(status="error", output="", error=str(exc))
        self.finished.emit(result)
