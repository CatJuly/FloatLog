from __future__ import annotations

import os
import shutil
import subprocess
import threading
import uuid
from dataclasses import dataclass
from pathlib import Path

from models import Server, AppConfig


@dataclass
class ClaudeResult:
    status: str  # "success" | "not_found" | "timeout" | "error" | "cancelled"
    output: str
    error: str = ""
    session_id: str = ""  # 本次对话的 session id（空串表示没有会话）

    @property
    def ok(self) -> bool:
        return self.status == "success"


def _auth_desc(server: Server) -> str:
    if server.auth_type == "key":
        return f"私钥路径: {server.secret}"
    return f"密码: {server.secret}"


def build_prompt(servers: list[Server], user_prompt: str) -> str:
    parts = [
        "你是只读的服务器日志分析助手，只做一件事：查看日志、分析并报告，不做其他任何操作。",
        "",
        "硬性约束（必须全部遵守）：",
        "1. 只读日志：服务是用 docker-compose 启动的，没有独立日志文件。只允许进入下面各服务器的「部署位置」目录，用 docker-compose logs（或 docker compose logs）查看容器日志；禁止读取、搜索、修改任何源代码、配置文件、数据库或其他非日志内容。",
        "2. 只读不写：禁止在本机或任何服务器上创建、修改、删除任何文件；禁止生成脚本、工具或临时文件；禁止把密码、密钥等凭据写入任何文件。",
        "3. 只报告不行动：只输出分析结论；禁止执行修复、改配置、重启服务、改数据库等操作；禁止在结尾问「要不要我帮你改 / 删 / 连其他服务器」之类的话。",
        "4. 不越界：不要安装软件，不要调用除查看日志以外的任何工具或命令。",
        "",
        "查看日志注意：日志可能很长，按用户需求的时间范围聚焦（必要时用 docker-compose logs --tail N 或 --since/--until 限定），重点找 ERROR / 异常 / 报错。",
        "",
        "输出格式（对每台服务器依次输出）：",
        "- 发现的错误：时间 + 级别 + 关键日志原文摘录",
        "- 原因：仅基于日志内容推断，不要读代码去佐证",
        "- 影响：影响了哪个功能",
        "最后用不超过 3 行给出总体结论。不要列「修复建议清单」，不要给出任何下一步操作。",
        "",
    ]
    for i, server in enumerate(servers, start=1):
        parts.append(f"服务器 {i}：")
        parts.append(f"- 名称: {server.name}")
        parts.append(f"- 主机: {server.host}:{server.port}")
        parts.append(f"- 用户: {server.username}")
        parts.append(f"- 认证: {_auth_desc(server)}")
        if server.deploy_dir:
            parts.append(f"- 部署位置（docker-compose 目录）: {server.deploy_dir}")
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


def build_command(config: AppConfig, *, session_id: str | None = None,
                  resume: bool = False) -> list[str]:
    cmd = [
        config.claude_command,
        "--print",
        "--output-format", "text",
        "--input-format", "text",
        "--add-dir", config.workspace_dir,
        "--disallowedTools", "Write,Edit,NotebookEdit",
        "--permission-mode", config.permission_mode,
    ]
    if session_id is not None:
        cmd += ["--resume" if resume else "--session-id", session_id]
    return cmd


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


def _kill_process(proc: subprocess.Popen) -> None:
    """终止正在运行的 claude 子进程（Windows 下连同其子进程树一起结束）。"""
    if proc.poll() is not None:
        return
    if os.name == "nt":
        subprocess.run(
            ["taskkill", "/T", "/F", "/PID", str(proc.pid)],
            capture_output=True,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
    else:
        proc.kill()


def run(config: AppConfig, servers: list[Server], user_prompt: str,
        session_id: str | None = None,
        cancel_event: threading.Event | None = None) -> ClaudeResult:
    if resolve_binary(config.claude_command) is None:
        return ClaudeResult(
            status="not_found",
            output="",
            error=f"未找到命令: {config.claude_command}",
        )

    # session_id 为空 → 新开一个会话（用固定 id，方便之后 --resume 续接）
    resume = session_id is not None
    sid = session_id or str(uuid.uuid4())

    prompt = build_prompt(servers, user_prompt)
    cmd = build_command(config, session_id=sid, resume=resume)
    launch = launch_command(cmd)

    workspace = Path(config.workspace_dir)
    workspace.mkdir(parents=True, exist_ok=True)

    try:
        proc = subprocess.Popen(
            launch,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            cwd=str(workspace),
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )
    except OSError as exc:
        return ClaudeResult(status="error", output="", error=str(exc), session_id=sid)

    # 取消监听：外部 set cancel_event 时，终止子进程
    if cancel_event is not None:
        def _watch() -> None:
            while proc.poll() is None and not cancel_event.wait(timeout=0.1):
                pass
            if proc.poll() is None:
                _kill_process(proc)
        threading.Thread(target=_watch, daemon=True).start()

    try:
        out, err = proc.communicate(input=prompt, timeout=config.timeout_seconds)
    except subprocess.TimeoutExpired:
        _kill_process(proc)
        out, err = proc.communicate()
        if cancel_event is not None and cancel_event.is_set():
            return ClaudeResult(status="cancelled", output="", error="已停止", session_id=sid)
        return ClaudeResult(
            status="timeout",
            output="",
            error=f"运行超时（{config.timeout_seconds} 秒）",
            session_id=sid,
        )

    if cancel_event is not None and cancel_event.is_set():
        return ClaudeResult(status="cancelled", output=out or "", error="已停止", session_id=sid)

    output = out or ""
    err = err or ""
    if proc.returncode == 0:
        return ClaudeResult(status="success", output=output, error=err, session_id=sid)
    return ClaudeResult(
        status="error",
        output=output,
        error=err or f"claude 退出码 {proc.returncode}",
        session_id=sid,
    )
