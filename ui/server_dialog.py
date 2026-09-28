from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog, QFormLayout, QLineEdit, QSpinBox, QComboBox,
    QPlainTextEdit, QDialogButtonBox, QVBoxLayout, QHBoxLayout,
    QPushButton, QFileDialog, QWidget,
)

from models import Server


class ServerDialog(QDialog):
    def __init__(self, parent=None, server: Server | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("编辑服务器" if server else "添加服务器")

        form = QFormLayout()

        self.name_edit = QLineEdit()
        form.addRow("名称", self.name_edit)

        self.host_edit = QLineEdit()
        form.addRow("主机地址", self.host_edit)

        self.port_spin = QSpinBox()
        self.port_spin.setRange(1, 65535)
        self.port_spin.setValue(22)
        form.addRow("端口", self.port_spin)

        self.user_edit = QLineEdit()
        form.addRow("用户名", self.user_edit)

        self.auth_combo = QComboBox()
        self.auth_combo.addItem("密码", "password")
        self.auth_combo.addItem("私钥", "key")
        form.addRow("认证方式", self.auth_combo)

        self.secret_edit = QLineEdit()
        self.secret_edit.setEchoMode(QLineEdit.Password)
        self._secret_browse = QPushButton("浏览…")
        self._secret_browse.clicked.connect(self._browse_key)
        secret_row = QWidget()
        secret_lay = QHBoxLayout(secret_row)
        secret_lay.setContentsMargins(0, 0, 0, 0)
        secret_lay.addWidget(self.secret_edit)
        secret_lay.addWidget(self._secret_browse)
        form.addRow("密码/私钥", secret_row)

        self.deploy_edit = QLineEdit()
        form.addRow("部署位置", self.deploy_edit)

        self.log_edit = QLineEdit()
        form.addRow("日志目录", self.log_edit)

        self.note_edit = QPlainTextEdit()
        self.note_edit.setFixedHeight(60)
        form.addRow("备注", self.note_edit)

        self.auth_combo.currentIndexChanged.connect(self._sync_auth_ui)
        self._sync_auth_ui()

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(buttons)

        if server is not None:
            self._load(server)

    def _sync_auth_ui(self) -> None:
        is_key = self.auth_combo.currentData() == "key"
        self.secret_edit.setEchoMode(QLineEdit.Normal if is_key else QLineEdit.Password)
        self._secret_browse.setVisible(is_key)

    def _browse_key(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "选择私钥文件")
        if path:
            self.secret_edit.setText(path)

    def _load(self, server: Server) -> None:
        self.name_edit.setText(server.name)
        self.host_edit.setText(server.host)
        self.port_spin.setValue(server.port)
        self.user_edit.setText(server.username)
        idx = self.auth_combo.findData(server.auth_type)
        if idx >= 0:
            self.auth_combo.setCurrentIndex(idx)
        self.secret_edit.setText(server.secret)
        self.deploy_edit.setText(server.deploy_dir)
        self.log_edit.setText(server.log_dir)
        self.note_edit.setPlainText(server.note)

    def result_server(self) -> Server:
        return Server(
            name=self.name_edit.text().strip(),
            host=self.host_edit.text().strip(),
            username=self.user_edit.text().strip(),
            auth_type=self.auth_combo.currentData(),
            secret=self.secret_edit.text(),
            port=self.port_spin.value(),
            deploy_dir=self.deploy_edit.text().strip(),
            log_dir=self.log_edit.text().strip(),
            note=self.note_edit.toPlainText(),
        )
