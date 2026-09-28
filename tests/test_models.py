import os
from pathlib import Path

from models import Server, AppConfig, default_config, default_data_dir, default_workspace_dir


def test_server_round_trip():
    s = Server(name="prod", host="1.2.3.4", username="root", auth_type="key",
               secret="/home/me/.ssh/id_rsa", port=2222, deploy_dir="/opt/app",
               log_dir="/var/log/app", note="生产")
    assert Server.from_dict(s.to_dict()) == s


def test_server_defaults():
    s = Server(name="x", host="h", username="u")
    assert s.port == 22
    assert s.auth_type == "password"


def test_appconfig_round_trip():
    c = AppConfig(workspace_dir="C:/tmp/ws", claude_command="claude",
                  permission_mode="plan", timeout_seconds=30)
    assert AppConfig.from_dict(c.to_dict()) == c


def test_appconfig_merges_defaults():
    c = AppConfig.from_dict({"timeout_seconds": 999})
    assert c.timeout_seconds == 999
    assert c.permission_mode == "bypassPermissions"
    assert c.claude_command == "claude"


def test_default_workspace_under_data_dir(monkeypatch):
    monkeypatch.setenv("APPDATA", "C:/Users/test/AppData/Roaming")
    assert default_workspace_dir() == Path("C:/Users/test/AppData/Roaming/FloatLog/workspace")


def test_default_data_dir_falls_back_home(monkeypatch):
    monkeypatch.delenv("APPDATA", raising=False)
    assert default_data_dir() == Path.home() / "FloatLog"
