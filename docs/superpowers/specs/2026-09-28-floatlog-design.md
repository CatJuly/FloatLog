# FloatLog 设计文档

日期：2026-09-28
状态：待评审

## 1. 项目概述

FloatLog 是一个 Windows 桌面悬浮框应用，用于「保存服务器信息 + 服务部署位置/日志目录」，帮助用户一键把信息组装成提示词，交给本地的 Claude Code 去 SSH 连接服务器、分析错误日志。

**核心定位**：FloatLog 本身不连接服务器。它只负责存储信息、拼装提示词、调用本地 `claude` CLI 并把结果回显到悬浮框。真正的连接与分析由 Claude Code 完成。

## 2. 技术栈

- Python 3.12
- PySide6（Qt 官方绑定，LGPL 许可）
- 数据存储：本地 JSON 文件，明文
- 打包：PyInstaller → exe（`FloatLog.spec`，单文件、无控制台窗口）

## 3. 模块架构

| 模块 | 职责 |
|------|------|
| `main.py` | 入口：QApplication、悬浮窗、系统托盘、窗口生命周期 |
| `models.py` | `Server`、`AppConfig` 数据类 |
| `storage.py` | 服务器列表与配置的 JSON 读写（增删改查、持久化） |
| `claude_client.py` | 拼装提示词 → 解析/启动本地 `claude` CLI → 返回结果 |
| `ui/` | 主悬浮窗、添加/编辑服务器对话框、设置对话框 |

各模块单一职责，通过清晰接口通信：
- `ui` 只依赖 `models`、`storage`、`claude_client` 的公开函数
- `claude_client` 不依赖 `ui`，可独立测试

## 4. 悬浮框 UI

- 无边框窗口（`Qt.FramelessWindowHint`）、可置顶（可开关）、可拖动，约 360×520
- 顶部标题栏：标题 + 最小化/关闭按钮（**关闭 = 收进系统托盘，不退出进程**）
- 服务器列表：显示名称；**支持多选**（选中项进入分析上下文，默认选中当前高亮项）；右键菜单（添加/编辑/删除）；双击编辑
- 「+ 添加服务器」按钮
- 提示词输入框（多行）
- 「发送分析」按钮 + 「停止」按钮（终止正在运行的 claude 进程）+ 「新对话」按钮（清空会话，下次从头开始）
- 结果展示区（只读，带「运行中…」状态 + 复制结果按钮）
- 设置入口（工作目录、claude 命令路径、权限模式、超时等）

## 5. 数据模型

```python
@dataclass
class Server:
    name: str         # 名称/别名
    host: str         # 主机地址 (IP/域名)
    port: int = 22    # 端口
    username: str     # 登录用户名
    auth_type: str    # "password" | "key"
    secret: str       # password: 明文密码; key: 私钥路径
    deploy_dir: str   # 服务部署位置
    log_dir: str      # 日志目录
    note: str = ""    # 备注（可选）

@dataclass
class AppConfig:
    workspace_dir: str   # Claude Code 本地工作目录 (cwd)
    claude_command: str = "claude"   # claude 可执行命令
    permission_mode: str = "bypassPermissions"  # 传给 claude 的 --permission-mode 值；默认特权模式（无头 SSH 分析需要）
    timeout_seconds: int = 600
```

## 6. 存储

- 目录：`%APPDATA%/FloatLog/`
  - `servers.json`：服务器列表
  - `config.json`：应用配置
  - `session.json`：当前多轮对话的 session id（「新对话」时清除）
  - `workspace/`：Claude Code 工作目录（首次启动自动创建）
- `%APPDATA%` 取 `os.environ["APPDATA"]`，缺失时回退到 `Path.home()`
- 读写失败时弹窗提示并写日志，不崩溃

## 7. Claude Code 调用机制（关键）

参考 OpenOPC 的 `claude_code.py` / `base.py` 适配器实现，完整流程：

1. **解析二进制**：`shutil.which(claude_command)` 在 PATH 中解析
2. **Windows `.cmd` 外壳**：若解析到 `.cmd`/`.bat`（npm 安装的 claude 即如此），用 `cmd.exe /d /s /c <resolved> <args...>` 包装（`COMSPEC`）；否则直接 spawn 会失败
3. **工作目录**：`subprocess` 以 `cwd=<workspace_dir>` 启动
4. **非交互式命令**：
   ```
   claude --print --output-format text --input-format text --add-dir <workspace_dir> --disallowedTools Write,Edit,NotebookEdit --permission-mode <permission_mode>
   ```
   多轮对话：首次调用追加 `--session-id <uuid>` 开新会话，之后追加 `--resume <uuid>` 续接；界面提供「新对话」按钮清空会话。
5. **多行提示词走 stdin**：拼装结果必然多行，走 argv 会被 cmd.exe 截断，因此提示词通过 stdin 管道写入（`--input-format text` 配合管道）
6. **超时**：默认 600s，可配
7. **判定**：返回码 0 = 成功，否则回显 stderr + stdout

### 拼装提示词模板

选中一台或多台服务器时，拼装一段「只读日志分析」提示词（每台服务器一段，顺序与选中顺序一致），核心约束：

- **只读日志**：服务由 docker-compose 启动、没有独立日志文件，只允许进入「部署位置」目录用 `docker-compose logs`（或 `docker compose logs`）查看容器日志
- **只读不写**：禁止创建/修改/删除任何文件，禁止把密码、密钥写入文件
- **只报告不行动**：只输出分析结论，不执行修复、改配置、重启等操作

每台服务器信息包含：名称、主机:端口、用户、认证（密码或私钥路径）、部署位置（docker-compose 目录）、日志目录（可选）。

未选中任何服务器时，禁止发送并提示「请先选择至少一台服务器」。

## 8. 错误处理

- `claude` 找不到 → 提示「未找到 claude 命令，请先安装 Claude Code 或在设置里指定路径」
- 运行超时 → 提示超时，可调大超时
- 非零退出码 → 回显 stderr
- JSON 文件读写失败 → 弹窗 + 日志

## 9. 测试

- `storage`：读写往返、字段序列化、目录自动创建
- `claude_client`：提示词拼装模板测试；mock subprocess 测试成功/失败/超时/未找到四种路径
- 用 pytest，保持轻量

## 10. 安全注意

- 用户选择明文存储密码。文件放 `%APPDATA%/FloatLog/servers.json`，仅当前用户可读。
- 提示词中会包含认证信息（密码或私钥路径），会随 `claude` 进程发送。
- 认证方式可配：`password` 存明文，`key` 存私钥路径（推荐密钥方式，更安全且更易让 Claude Code 无交互连接）。
- 提示词内置「只读」硬约束 + `--disallowedTools Write,Edit,NotebookEdit`，限制 Claude Code 只查日志、不写文件、不改配置。

## 11. 待验证假设（实现阶段确认）

1. `bypassPermissions` 为无头 SSH 分析的必要权限模式（已定为默认值），其安全含义：Claude Code 在本机与目标服务器上拥有较高权限，需信任其行为。
2. SSH 认证：密码无法无交互传给 `ssh`，密钥方式才能让 Claude Code 顺利连接。若用户用密码，可能需要在服务器侧配置 sshpass 或改用密钥。
