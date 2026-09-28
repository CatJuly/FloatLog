import os

import pytest

import claude_client
from claude_client import build_command, build_prompt, launch_command
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


def test_build_command():
    c = AppConfig(workspace_dir="C:/ws", permission_mode="bypassPermissions")
    assert build_command(c) == [
        "claude", "--print", "--output-format", "text", "--input-format", "text",
        "--add-dir", "C:/ws", "--permission-mode", "bypassPermissions",
    ]


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
