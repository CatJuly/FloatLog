# FloatLog

Windows 桌面悬浮框工具：保存服务器信息，一键拼装提示词调用本地 Claude Code 无头分析错误日志。

## 使用

1. 安装依赖：`python -m venv .venv && .venv\Scripts\activate && pip install -r requirements.txt`
2. 运行：`.venv\Scripts\python.exe main.py`
3. 添加服务器 → 多选 → 输入提示词 → 发送分析 → 结果回显

## 配置

数据存于 `%APPDATA%/FloatLog/`（`servers.json` 服务器、`config.json` 设置、`workspace/` 工作目录）。
首次运行自动创建。设置里可改工作目录、claude 命令、权限模式、超时。

## 测试

`.venv\Scripts\python.exe -m pytest`
