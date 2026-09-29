import os
import subprocess
import threading

import pytest

import claude_client
from claude_client import build_command, build_prompt, launch_command, run
from models import AppConfig, Server


def make_server(name="prod", host="1.2.3.4", **kw):
    defaults = dict(name=name, host=host, username="root",
                    auth_type="password", secret="s3cret")
    defaults.update(kw)
    return Server(**defaults)


def test_build_prompt_single_server():
    s = make_server(deploy_dir="/opt/app", log_dir="/var/log/app")
    p = build_prompt([s], "分析今天的错误日志")
    assert "prod" in p
    assert "1.2.3.4:22" in p
    assert "密码: s3cret" in p
    assert "/var/log/app" in p
    assert "用户需求: 分析今天的错误日志" in p


def test_build_prompt_multiple_servers_ordered():
    a = make_server(name="A", host="10.0.0.1")
    b = make_server(name="B", host="10.0.0.2")
    p = build_prompt([a, b], "对比两台服务器的错误")
    assert p.index("服务器 1") < p.index("服务器 2")
    assert p.index("A") < p.index("B")
    assert "10.0.0.1" in p and "10.0.0.2" in p


def test_build_prompt_key_auth():
    s = make_server(auth_type="key", secret="C:/Users/me/.ssh/id_rsa")
    p = build_prompt([s], "x")
    assert "私钥路径: C:/Users/me/.ssh/id_rsa" in p


def test_build_prompt_readonly_constraints():
    p = build_prompt([make_server()], "x")
    assert "只读日志" in p
    assert "docker-compose logs" in p
    assert "只读不写" in p
    assert "只报告不行动" in p
    assert "禁止把密码" in p
    assert "修复建议清单" in p


def test_build_command():
    c = AppConfig(workspace_dir="C:/ws", permission_mode="bypassPermissions")
    assert build_command(c) == [
        "claude", "--print", "--output-format", "text", "--input-format", "text",
        "--add-dir", "C:/ws",
        "--disallowedTools", "Write,Edit,NotebookEdit",
        "--permission-mode", "bypassPermissions",
    ]


def test_build_command_new_session():
    c = AppConfig(workspace_dir="C:/ws", permission_mode="bypassPermissions")
    sid = "11111111-1111-1111-1111-111111111111"
    cmd = build_command(c, session_id=sid, resume=False)
    assert cmd[-2:] == ["--session-id", sid]
    assert "--resume" not in cmd


def test_build_command_resume():
    c = AppConfig(workspace_dir="C:/ws")
    sid = "22222222-2222-2222-2222-222222222222"
    cmd = build_command(c, session_id=sid, resume=True)
    assert cmd[-2:] == ["--resume", sid]
    assert "--session-id" not in cmd


def test_resolve_binary_found(monkeypatch):
    monkeypatch.setattr(claude_client.shutil, "which", lambda cmd: "C:/tools/claude.cmd")
    assert claude_client.resolve_binary("claude") == "C:/tools/claude.cmd"


def test_resolve_binary_not_found(monkeypatch):
    monkeypatch.setattr(claude_client.shutil, "which", lambda cmd: None)
    assert claude_client.resolve_binary("claude") is None


@pytest.mark.skipif(os.name != "nt", reason="Windows-only .cmd wrapping")
def test_launch_command_wraps_cmd(monkeypatch):
    monkeypatch.setattr(claude_client.shutil, "which", lambda cmd: "C:/tools/claude.cmd")
    monkeypatch.setenv("COMSPEC", "C:/Windows/System32/cmd.exe")
    cmd = launch_command(["claude", "--print"])
    assert cmd[0] == "C:/Windows/System32/cmd.exe"
    assert cmd[1:4] == ["/d", "/s", "/c"]


class FakePopen:
    def __init__(self, stdout="ok", stderr="", returncode=0):
        self.stdout = stdout
        self.stderr = stderr
        self._returncode = returncode
        self.returncode = None  # 进程“运行中”，communicate 后才结束
        self.pid = 1234
        self.killed = False

    def poll(self):
        return self.returncode

    def communicate(self, input=None, timeout=None):
        self.input = input
        self.returncode = self._returncode
        return self.stdout, self.stderr

    def kill(self):
        self.killed = True
        self.returncode = -1


def test_run_not_found(monkeypatch):
    monkeypatch.setattr(claude_client, "resolve_binary", lambda cmd: None)
    r = run(AppConfig(workspace_dir="C:/ws"), [make_server()], "x")
    assert r.status == "not_found"


def test_run_not_found_no_session(monkeypatch):
    monkeypatch.setattr(claude_client, "resolve_binary", lambda cmd: None)
    r = run(AppConfig(workspace_dir="C:/ws"), [make_server()], "x",
            session_id="33333333-3333-3333-3333-333333333333")
    assert r.status == "not_found"
    assert r.session_id == ""


def test_run_success(monkeypatch, tmp_path):
    captured = {}
    proc_holder = {}

    def fake_popen(argv, **kwargs):
        captured["argv"] = argv
        captured["cwd"] = kwargs["cwd"]
        captured["creationflags"] = kwargs["creationflags"]
        proc = FakePopen("分析结果", "", returncode=0)
        proc_holder["proc"] = proc
        return proc

    monkeypatch.setattr(claude_client, "resolve_binary", lambda cmd: "C:/claude.cmd")
    monkeypatch.setattr(claude_client.subprocess, "Popen", fake_popen)
    ws = str(tmp_path / "ws")
    r = run(AppConfig(workspace_dir=ws), [make_server()], "x")
    assert r.status == "success"
    assert r.output == "分析结果"
    assert r.session_id
    assert "--session-id" in captured["argv"]
    assert "prod" in proc_holder["proc"].input
    assert captured["cwd"] == ws
    assert captured["creationflags"] == (subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)


def test_run_nonzero(monkeypatch, tmp_path):
    monkeypatch.setattr(claude_client, "resolve_binary", lambda cmd: "claude")
    monkeypatch.setattr(claude_client.subprocess, "Popen",
                        lambda argv, **kwargs: FakePopen("", "boom", returncode=1))
    r = run(AppConfig(workspace_dir=str(tmp_path)), [make_server()], "x")
    assert r.status == "error"
    assert "boom" in r.error


def test_run_timeout(monkeypatch, tmp_path):
    class TimeoutProc(FakePopen):
        def communicate(self, input=None, timeout=None):
            if timeout is not None and not getattr(self, "_raised", False):
                self._raised = True
                raise subprocess.TimeoutExpired(cmd=["claude"], timeout=timeout)
            return "partial", ""

    monkeypatch.setattr(claude_client, "resolve_binary", lambda cmd: "claude")
    monkeypatch.setattr(claude_client, "_kill_process", lambda proc: None)
    monkeypatch.setattr(claude_client.subprocess, "Popen",
                        lambda argv, **kwargs: TimeoutProc())
    r = run(AppConfig(workspace_dir=str(tmp_path)), [make_server()], "x")
    assert r.status == "timeout"


def test_run_new_session_generates_id(monkeypatch, tmp_path):
    monkeypatch.setattr(claude_client, "resolve_binary", lambda cmd: "claude")
    monkeypatch.setattr(claude_client.subprocess, "Popen",
                        lambda argv, **kwargs: FakePopen("ok", "", returncode=0))
    r = run(AppConfig(workspace_dir=str(tmp_path)), [make_server()], "x")
    assert r.status == "success"
    assert r.session_id


def test_run_resume_uses_resume_flag(monkeypatch, tmp_path):
    captured = {}

    def fake_popen(argv, **kwargs):
        captured["argv"] = argv
        return FakePopen("ok", "", returncode=0)

    monkeypatch.setattr(claude_client, "resolve_binary", lambda cmd: "claude")
    monkeypatch.setattr(claude_client.subprocess, "Popen", fake_popen)
    sid = "44444444-4444-4444-4444-444444444444"
    r = run(AppConfig(workspace_dir=str(tmp_path)), [make_server()], "x",
            session_id=sid)
    assert r.status == "success"
    assert r.session_id == sid
    assert "--resume" in captured["argv"]
    assert "--session-id" not in captured["argv"]


def test_run_cancelled(monkeypatch, tmp_path):
    monkeypatch.setattr(claude_client, "resolve_binary", lambda cmd: "claude")
    monkeypatch.setattr(claude_client, "_kill_process", lambda proc: None)
    monkeypatch.setattr(claude_client.subprocess, "Popen",
                        lambda argv, **kwargs: FakePopen("partial", "", returncode=0))
    cancel = threading.Event()
    cancel.set()
    r = run(AppConfig(workspace_dir=str(tmp_path)), [make_server()], "x",
            cancel_event=cancel)
    assert r.status == "cancelled"
