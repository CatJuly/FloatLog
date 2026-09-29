from __future__ import annotations

import json
from pathlib import Path

from models import Server, AppConfig, default_config, default_data_dir


class Storage:
    def __init__(self, data_dir: Path | None = None) -> None:
        self.data_dir = Path(data_dir) if data_dir else default_data_dir()
        self.servers_path = self.data_dir / "servers.json"
        self.config_path = self.data_dir / "config.json"
        self.session_path = self.data_dir / "session.json"

    def ensure_dirs(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)

    def list_servers(self) -> list[Server]:
        if not self.servers_path.exists():
            return []
        raw = json.loads(self.servers_path.read_text(encoding="utf-8"))
        return [Server.from_dict(item) for item in raw]

    def save_servers(self, servers: list[Server]) -> None:
        self.ensure_dirs()
        data = [s.to_dict() for s in servers]
        self.servers_path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    def load_config(self) -> AppConfig:
        if not self.config_path.exists():
            return default_config()
        raw = json.loads(self.config_path.read_text(encoding="utf-8"))
        return AppConfig.from_dict(raw)

    def save_config(self, config: AppConfig) -> None:
        self.ensure_dirs()
        self.config_path.write_text(
            json.dumps(config.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8"
        )

    def load_session_id(self) -> str | None:
        """当前会话 id；没有或文件损坏时返回 None（表示下次新开会话）。"""
        if not self.session_path.exists():
            return None
        try:
            raw = json.loads(self.session_path.read_text(encoding="utf-8"))
        except Exception:
            return None
        return raw.get("session_id") or None

    def save_session_id(self, session_id: str | None) -> None:
        """保存会话 id；传 None 表示清空（删除会话文件）。"""
        if session_id:
            self.ensure_dirs()
            self.session_path.write_text(
                json.dumps({"session_id": session_id}, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        elif self.session_path.exists():
            self.session_path.unlink()
