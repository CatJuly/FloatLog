# FloatLog

Windows 桌面悬浮框工具：保存服务器连接信息，一键调用本地 Claude Code 无头（headless）分析服务器错误日志，并把结果回显到悬浮框。

> FloatLog 本身不连接服务器、也不读日志。它只做三件事：存储服务器信息、拼装成提示词、调用本地 `claude` CLI 并把结果展示出来。真正的连接与分析由 Claude Code 完成。

## 背景

服务由 docker-compose 启动，没有独立日志文件，只能进入部署目录用 `docker-compose logs` 看日志。手动 SSH 上去翻日志、再把信息喂给 AI 很麻烦，所以做了这个悬浮框：填一次服务器信息，之后勾选服务器 + 输入一句话，就能让 Claude Code 上去看日志并只返回分析结论。

为安全起见，应用内置了「只读」约束：只让 Claude Code 查日志、分析、报告，禁止写文件、改配置、改数据库，并配合 `--disallowedTools` 禁用写文件的工具。

## 功能特性

- 悬浮窗：无边框、可置顶、可拖动、关闭即收进系统托盘
- 多台服务器管理：添加 / 编辑 / 删除，支持多选批量分析
- 只读日志分析：自动拼装 docker-compose 日志分析提示词，限制 Claude Code 只读不写
- 多轮对话：同一话题可持续追问（自动续接上一会话），也可一键「新对话」从头开始
- 结果回显 + 一键复制

## 依赖

- Python 3.12+
- 本地已安装并登录 [Claude Code](https://claude.com/claude-code) CLI，且 `claude` 在 PATH 中可用
- 依赖包见 `requirements.txt`（PySide6 等）

## 安装与运行（源码方式）

```bash
# 1. 创建虚拟环境并安装依赖
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt

# 2. 运行
.venv\Scripts\python.exe main.py
```

## 打成 exe（绿色便携，目标机器无需 Python）

```bash
# 1. 安装打包工具（PyInstaller + 生成图标用的 Pillow）
pip install pyinstaller pillow

# 2.（可选）重新生成图标，仓库已带 FloatLog.ico，可跳过
python make_icon.py

# 3. 用仓库里的 spec 打包
pyinstaller FloatLog.spec
```

产物在 `dist\FloatLog.exe`：单文件、无控制台黑窗口、带图标。因为 PyInstaller 把 Python 运行时一并打包，双击即可运行，无需在目标机器安装任何环境。

等价的手动命令：`pyinstaller --onefile --windowed --icon FloatLog.ico main.py`

## 使用流程

1. 点「添加服务器」，填名称、主机、端口、用户名、认证方式（密码或私钥）、部署位置（docker-compose 目录）
2. 在列表里勾选要分析的一台或多台服务器
3. 输入提示词（例如「分析今天的错误日志」）
4. 点「发送分析」，结果回显在下方
5. 想追问就继续发送（自动续接同一对话）；点「新对话」则清空上下文重新开始

## 数据存储与隐私

- 所有数据保存在本机 `%APPDATA%\FloatLog\`：
  - `servers.json`：服务器列表
  - `config.json`：应用设置
  - `session.json`：当前对话的 session id
  - `workspace\`：Claude Code 的工作目录
- 服务器密码为明文存储，仅当前 Windows 用户可读；建议优先使用密钥（私钥路径）方式登录
- 分析时会把服务器信息（含密码或私钥路径）拼进提示词，发送给本地 Claude Code，并由其 SSH 连接服务器
- 应用只在本机运行，不向任何外部服务上传数据

## 测试

```bash
.venv\Scripts\python.exe -m pytest
```

## 项目结构

```
main.py            入口（悬浮窗 + 系统托盘）
models.py          数据模型（Server / AppConfig）
storage.py         JSON 读写（服务器 / 配置 / 会话 id）
claude_client.py   提示词拼装 + 调用 claude CLI
ui/                界面（主窗口 / 服务器对话框 / 设置对话框）
tests/             pytest 测试
make_icon.py       图标生成脚本
FloatLog.spec      PyInstaller 打包配置
FloatLog.ico       应用图标
```
