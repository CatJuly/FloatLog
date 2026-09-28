from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog, QFormLayout, QLineEdit, QSpinBox, QComboBox,
    QDialogButtonBox, QVBoxLayout, QHBoxLayout, QWidget, QPushButton,
    QFileDialog,
)

from models import AppConfig


class SettingsDialog(QDialog):
    PERMISSION_MODES = [
        ("特权（bypassPermissions）", "bypassPermissions"),
        ("默认（default）", "default"),
        ("只读规划（plan）", "plan"),
        ("自动批准编辑（acceptEdits）", "acceptEdits"),
    ]

    def __init__(self, parent=None, config: AppConfig | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("设置")

        form = QFormLayout()

        self.workspace_edit = QLineEdit()
        ws_browse = QPushButton("浏览…")
        ws_browse.clicked.connect(self._browse_workspace)
        ws_row = QWidget()
        ws_lay = QHBoxLayout(ws_row)
        ws_lay.setContentsMargins(0, 0, 0, 0)
        ws_lay.addWidget(self.workspace_edit)
        ws_lay.addWidget(ws_browse)
        form.addRow("工作目录", ws_row)

        self.command_edit = QLineEdit()
        form.addRow("claude 命令", self.command_edit)

        self.mode_combo = QComboBox()
        for label, value in self.PERMISSION_MODES:
            self.mode_combo.addItem(label, value)
        form.addRow("权限模式", self.mode_combo)

        self.timeout_spin = QSpinBox()
        self.timeout_spin.setRange(10, 3600)
        self.timeout_spin.setValue(600)
        self.timeout_spin.setSuffix(" 秒")
        form.addRow("超时", self.timeout_spin)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(buttons)

        if config is not None:
            self._load(config)

    def _browse_workspace(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "选择工作目录")
        if path:
            self.workspace_edit.setText(path)

    def _load(self, config: AppConfig) -> None:
        self.workspace_edit.setText(config.workspace_dir)
        self.command_edit.setText(config.claude_command)
        idx = self.mode_combo.findData(config.permission_mode)
        if idx >= 0:
            self.mode_combo.setCurrentIndex(idx)
        self.timeout_spin.setValue(config.timeout_seconds)

    def result_config(self) -> AppConfig:
        return AppConfig(
            workspace_dir=self.workspace_edit.text().strip(),
            claude_command=self.command_edit.text().strip() or "claude",
            permission_mode=self.mode_combo.currentData(),
            timeout_seconds=self.timeout_spin.value(),
        )
