# Kimi-X Desktop

DeepIntent v2.1 共生桌面客户端 —— 单一窗口内嵌 DeepIntent 状态面板 + Kimi Web UI。

## 功能

- **硬件自适应** — 自动扫描 CPU/内存/磁盘/GPU，生成硬件档案，DeepIntentCore 动态调整参数
- **跨会话记忆** — 会话状态持久化，重启后自动恢复上下文
- **对话学习** — 左侧面板输入学习文本，实时反馈给 DeepIntentCore
- **API 密钥配置** — 支持设置/保存/清除 API 密钥
- **自动启动 kimi web** — 内置 Kimi Web UI，iframe 自动连接
- **深色主题** — GitHub Dark 风格 QSS + CSS

## 依赖

```bash
pip install -r requirements.txt
```

## 运行

```bash
python main.py
```

或双击桌面快捷方式（运行 `setup_desktop.py` 生成）。

## 项目结构

```
kimi-x-desktop/
├── main.py              # PySide6 主应用
├── config.py            # 集中配置管理
├── hardware_profiler.py # 硬件扫描
├── deepintent_worker.py # DeepIntent 后台线程
├── logger.py            # 日志系统
├── styles.py            # QSS 样式
├── setup_desktop.py     # 桌面快捷方式创建器
├── web_ui/              # 前端 HTML/CSS/JS
│   ├── index.html
│   ├── panel.css
│   └── panel.js
└── requirements.txt
```

## 恢复配置

换电脑时复制 `~/.kimi/kimi-x-config.json` 即可恢复个人配置。
