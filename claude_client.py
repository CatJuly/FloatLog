from __future__ import annotations

import os
import shutil
from dataclasses import dataclass
from pathlib import Path

from models import Server, AppConfig


@dataclass
class ClaudeResult:
    status: str  # "success" | "not_found" | "timeout" | "error"
    output: str
    error: str = ""

    @property
    def ok(self) -> bool:
        return self.status == "success"


def _auth_desc(server: Server) -> str:
    if server.auth_type == "key":
        return f"私钥路径: {server.secret}"
    return f"密码: {server.secret}"


def build_prompt(servers: list[Server], user_prompt: str) -> str:
    parts = ["请连接下面这些服务器，查看错误日志并分析：", ""]
    for i, server in enumerate(servers, start=1):
        parts.append(f"服务器 {i}：")
        parts.append(f"- 名称: {server.name}")
        parts.append(f"- 主机: {server.host}:{server.port}")
        parts.append(f"- 用户: {server.username}")
        parts.append(f"- 认证: {_auth_desc(server)}")
        if server.deploy_dir:
            parts.append(f"- 部署位置: {server.deploy_dir}")
        if server.log_dir:
            parts.append(f"- 日志目录: {server.log_dir}")
        parts.append("")
    parts.append(f"用户需求: {user_prompt}")
    return "\n".join(parts).rstrip() + "\n"


def resolve_binary(command: str) -> str | None:
    return shutil.which(command)


def _resolve_windows_shim(resolved: str) -> str:
    if os.path.splitext(resolved)[1]:
        return resolved
    for ext in (".exe", ".com", ".cmd", ".bat"):
        sibling = f"{resolved}{ext}"
        if os.path.isfile(sibling):
            return sibling
    return resolved


def build_command(config: AppConfig) -> list[str]:
    return [
        config.claude_command,
        "--print",
        "--output-format", "text",
        "--input-format", "text",
        "--add-dir", config.workspace_dir,
        "--permission-mode", config.permission_mode,
    ]


def launch_command(cmd: list[str]) -> list[str]:
    executable = cmd[0]
    resolved = shutil.which(executable)
    if not resolved:
        return cmd
    if os.name == "nt":
        resolved = _resolve_windows_shim(resolved)
        if os.path.splitext(resolved)[1].lower() in {".cmd", ".bat"}:
            comspec = os.environ.get("COMSPEC") or shutil.which("cmd.exe") or "cmd.exe"
            return [comspec, "/d", "/s", "/c", resolved, *cmd[1:]]
    if resolved == executable:
        return cmd
    return [resolved, *cmd[1:]]
