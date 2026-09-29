from models import Server, AppConfig
from storage import Storage


def test_list_servers_empty(tmp_path):
    assert Storage(tmp_path).list_servers() == []


def test_save_and_list_round_trip(tmp_path):
    s = Storage(tmp_path)
    servers = [Server(name="a", host="h1", username="u"),
               Server(name="b", host="h2", username="u", port=2200)]
    s.save_servers(servers)
    assert s.list_servers() == servers


def test_save_creates_data_dir(tmp_path):
    s = Storage(tmp_path / "nested" / "dir")
    s.save_servers([])
    assert (tmp_path / "nested" / "dir" / "servers.json").exists()


def test_load_config_default_when_missing(tmp_path):
    c = Storage(tmp_path).load_config()
    assert c.permission_mode == "bypassPermissions"
    assert c.timeout_seconds == 600


def test_save_and_load_config(tmp_path):
    s = Storage(tmp_path)
    c = AppConfig(workspace_dir="C:/ws", claude_command="myclaude",
                  permission_mode="plan", timeout_seconds=10)
    s.save_config(c)
    assert s.load_config() == c


def test_session_id_round_trip(tmp_path):
    s = Storage(tmp_path)
    assert s.load_session_id() is None
    sid = "44444444-4444-4444-4444-444444444444"
    s.save_session_id(sid)
    assert s.load_session_id() == sid


def test_session_id_clear(tmp_path):
    s = Storage(tmp_path)
    s.save_session_id("some-id")
    s.save_session_id(None)
    assert s.load_session_id() is None
    assert not (tmp_path / "session.json").exists()
