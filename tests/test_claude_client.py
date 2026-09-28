from claude_client import build_prompt
from models import Server


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
