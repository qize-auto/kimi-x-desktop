# Kimi-X Desktop

**DeepIntent v2.1 共生桌面客户端** —— 单一窗口内嵌 DeepIntent 状态面板 + Kimi Web UI。

仓库: `https://github.com/qize-auto/kimi-x-desktop`

---

## 一句话介绍

这是一个给 Kimi Code CLI 套上的桌面壳。双击启动后：
- 左侧是 DeepIntent 状态面板（健康检查、CPU 调速、闭环验证器、项目记忆）
- 右侧是 Kimi Web UI（iframe 内嵌，自动连接）
- 壳和 Kimi CLI 之间通过 `localStorage` 桥接，支持对话学习反馈

---

## 功能清单

| 功能 | 说明 |
|------|------|
| **硬件自适应** | 自动扫描 CPU/内存/磁盘/GPU，生成硬件档案，DeepIntentCore 动态调整参数 |
| **跨会话记忆** | 会话状态持久化到 `~/.kimi/kimi-x-memory.json`，重启后自动恢复上下文 |
| **对话学习** | 左侧面板输入学习文本，实时反馈给 DeepIntentCore |
| **👍👎 反馈** | 每次对话后可评价，反馈持久化到 `~/.kimi/kimi-x-desktop/feedback/` |
| **API 密钥** | 左侧面板可设置/保存/清除 API 密钥 |
| **项目记忆** | 自动读取项目根目录 `.kimi-x/PROJECT.md`，注入面板 |
| **GitHub 检测** | 启动时自动检测 `gh auth status`，配置保存在 `kimi-x-config.json` |
| **自动启动 kimi web** | 内置 Kimi Web UI，iframe 自动连接，断线自动重连 |
| **深色主题** | GitHub Dark 风格 QSS + CSS |

---

## 环境要求

- **Python** ≥ 3.12（推荐 3.13）
- **PySide6**（GUI 框架）
- **Kimi Code CLI**（必须，提供 `kimi web` 服务）
- **GitHub CLI**（可选，用于 GitHub 状态检测）
- **DeepIntent v2.1**（可选，提供 Core 常驻后台，项目地址见下方）

---

## 换电脑恢复指南（给 Kimi 的指令）

> 新电脑上安装完 Kimi Code CLI 后，把下面这段直接复制给 Kimi：

```
请帮我恢复 Kimi-X Desktop 桌面壳：
1. git clone https://github.com/qize-auto/kimi-x-desktop.git ~/kimi-workspace/kimi-x-desktop
2. cd ~/kimi-workspace/kimi-x-desktop && pip install -r requirements.txt
3. 如果旧电脑有 ~/.kimi/kimi-x-config.json 备份，复制过来
4. python setup_desktop.py 生成桌面快捷方式
5. python main.py 测试启动
```

### 详细步骤

#### 1. 安装 Kimi Code CLI

```bash
# Windows PowerShell
Invoke-RestMethod https://code.kimi.com/install.ps1 | Invoke-Expression

# 验证
kimi --version
```

#### 2. 克隆项目

```bash
mkdir -p ~/kimi-workspace
git clone https://github.com/qize-auto/kimi-x-desktop.git ~/kimi-workspace/kimi-x-desktop
cd ~/kimi-workspace/kimi-x-desktop
```

#### 3. 安装依赖

```bash
pip install -r requirements.txt
```

依赖列表（requirements.txt）：
```
PySide6>=6.8
```

#### 4. 恢复配置（如有备份）

```bash
# 旧电脑的 ~/.kimi/kimi-x-config.json 复制到新电脑相同位置
mkdir -p ~/.kimi
cp /path/to/backup/kimi-x-config.json ~/.kimi/

# 同时恢复反馈历史（可选）
cp -r /path/to/backup/kimi-x-desktop/ ~/.kimi/
```

#### 5. 生成桌面快捷方式

```bash
python setup_desktop.py
```

这会创建 `~/Desktop/Kimi-X Desktop.lnk`，双击即可启动。

#### 6. 首次启动

```bash
python main.py
```

首次启动会显示向导，选择 DeepIntent 项目根目录（默认 `~/kimi-workspace/deep-intent`）。

---

## 项目结构

```
kimi-x-desktop/
├── main.py              # PySide6 主应用（879 行）
│   ├── KimiXBridge      # JS ↔ Python 桥接（learnInput / feedback）
│   ├── KimiXWebPage     # 自定义 WebPage，捕获 console.log
│   ├── MainWindow       # 主窗口：UI + DeepIntent + kimi web 流水线
│   └── _detect_github() # 启动时检测 gh 认证状态
│
├── config.py            # 集中配置管理
│   └── ~/.kimi/kimi-x-config.json
│       ├── project_root         # DeepIntent 项目路径
│       ├── auto_start_kimi_web  # 是否自动启动 kimi web
│       ├── api_keys             # API 密钥
│       ├── github               # GitHub 认证信息
│       └── window_geometry      # 窗口位置
│
├── hardware_profiler.py # 硬件扫描（CPU/内存/磁盘/GPU）
├── deepintent_worker.py # DeepIntent 后台线程（QThread）
│   ├── _run_init()      # 检测 → pytest → 实例化 Core
│   ├── _resident_loop() # 每 60 秒自动保存
│   └── _persist_feedback() # 👍👎 反馈持久化
│
├── logger.py            # 日志系统（日志在 logs/ 目录）
├── styles.py            # QSS 样式（深色主题）
├── setup_desktop.py     # 桌面快捷方式创建器
├── requirements.txt     # 依赖
│
├── web_ui/              # 前端 HTML/CSS/JS
│   ├── index.html       # 面板布局（抽屉 + iframe）
│   ├── panel.css        # GitHub Dark 风格样式
│   └── panel.js         # 面板交互 + updateDeepIntent 注入
│
└── docs/
    └── reasonix-analysis.md  # DeepSeek-Reasonix 分析报告
```

---

## 配置说明

配置文件: `~/.kimi/kimi-x-config.json`

```json
{
  "version": "1.0",
  "project_root": "/c/Users/pc/kimi-workspace/deep-intent",
  "auto_start_kimi_web": true,
  "kimi_web_port": 5494,
  "theme": "dark",
  "api_keys": {},
  "github": {
    "username": "qize-auto",
    "authenticated": true,
    "default_org": null
  },
  "window_geometry": [80, 60, 1480, 900]
}
```

### 项目记忆文件

在项目根目录创建 `.kimi-x/PROJECT.md`，启动后会自动加载到面板：

```markdown
# 项目规范
- Python 3.12+, 使用 src/ 布局
- 测试: pytest tests/
- 核心模块: deep_intent.DeepIntentCore
- API Key 位置: ~/.kimi/kimi-x-config.json
```

---

## 反馈持久化

每次 👍/👎 会追加写入：

```
~/.kimi/kimi-x-desktop/feedback/<project-name>.jsonl
```

格式：
```jsonl
{"timestamp": 1716710400.123, "text": "panel_feedback", "is_positive": true, "project_root": "/c/Users/pc/kimi-workspace/deep-intent"}
```

---

## 开发与调试

```bash
# 查看日志
tail -f logs/kimi-x-$(date +%Y-%m-%d).log

# 手动启动 kimi web（如果自动启动失败）
kimi web --no-open --port 5494

# 重新生成桌面快捷方式
python setup_desktop.py
```

---

## 相关仓库

| 仓库 | 说明 |
|------|------|
| `qize-auto/kimi-x-desktop` | **本仓库** — 桌面壳 |
| `qize-auto/deep-intent` | DeepIntent v2.1 进化引擎 |
| `qize-auto/kimi-env-backup` | Kimi CLI 环境配置备份 |

---

*Last updated: 2026-05-26*
