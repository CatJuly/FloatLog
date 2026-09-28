from __future__ import annotations

import os
from dataclasses import dataclass, fields, asdict
from pathlib import Path


@dataclass
class Server:
    name: str
    host: str
    username: str
    auth_type: str = "password"  # "password" | "key"
    secret: str = ""
    port: int = 22
    deploy_dir: str = ""
    log_dir: str = ""
    note: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "Server":
        names = {f.name for f in fields(cls)}
        return cls(**{k: v for k, v in data.items() if k in names})


@dataclass
class AppConfig:
    workspace_dir: str
    claude_command: str = "claude"
    permission_mode: str = "bypassPermissions"
    timeout_seconds: int = 600

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "AppConfig":
        defaults = default_config()
        merged = {**defaults.to_dict(), **data}
        names = {f.name for f in fields(cls)}
        return cls(**{k: merged[k] for k in names})


def default_data_dir() -> Path:
    base = os.environ.get("APPDATA") or str(Path.home())
    return Path(base) / "FloatLog"


def default_workspace_dir() -> Path:
    return default_data_dir() / "workspace"


def default_config() -> AppConfig:
    return AppConfig(workspace_dir=str(default_workspace_dir()))
