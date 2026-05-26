"""
Kimi-X Desktop — DeepIntent v2.1 共生桌面客户端
===============================================
双击运行，单一窗口内嵌 DeepIntent 状态面板 + Kimi Web UI
面板通过本地 HTML 渲染，状态通过 runJavaScript 实时注入
"""
from __future__ import annotations
import sys
import os
import subprocess
import time
import json
from pathlib import Path

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QSystemTrayIcon, QMenu,
)
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import QWebEnginePage, QWebEngineSettings
from PyQt6.QtWebChannel import QWebChannel
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QUrl, QObject, pyqtSlot
from PyQt6.QtGui import QFont, QIcon, QAction, QPixmap, QColor, QPalette

from deepintent_worker import DeepIntentWorker
from logger import get_logger, log_exception
from config import KimiXConfig
from hardware_profiler import HardwareProfile


# ═══════════════════════════════════════════════════════════════
# JS ↔ Python 桥接（供前端面板调用）
# ═══════════════════════════════════════════════════════════════

class KimiXBridge(QObject):
    """暴露给前端 JS 的方法，用于对话学习和反馈"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._window = parent
        self.logger = get_logger("KimiXBridge")

    @pyqtSlot(str, result=str)
    def learnInput(self, text: str) -> str:
        """前端调用：将用户输入传给 DeepIntentCore 学习"""
        self.logger.info(f"Learn input: {text[:50]}")
        if self._window and self._window.di_worker.core:
            try:
                result = self._window.di_worker.process_user_input(text)
                return json.dumps({"ok": True, "probes": len(result.get("probes", []))})
            except Exception as e:
                self.logger.warning(f"learnInput failed: {e}")
                return json.dumps({"ok": False, "error": str(e)})
        return json.dumps({"ok": False, "error": "Core not ready"})

    @pyqtSlot(bool, str, result=str)
    def feedback(self, is_positive: bool, text: str = "") -> str:
        """前端调用：👍/👎 反馈"""
        label = "👍" if is_positive else "👎"
        self.logger.info(f"Feedback: {label} {text[:50]}")
        if self._window and self._window.di_worker.core:
            try:
                result = self._window.di_worker.receive_feedback(text, is_positive)
                return json.dumps({"ok": True, "status": result.get("status", "?")})
            except Exception as e:
                self.logger.warning(f"feedback failed: {e}")
                return json.dumps({"ok": False, "error": str(e)})
        return json.dumps({"ok": False, "error": "Core not ready"})


class KimiXWebPage(QWebEnginePage):
    """自定义 WebPage：重写 javaScriptConsoleMessage 捕获前端 console.log"""

    def __init__(self, parent=None, window=None):
        super().__init__(parent)
        self._window = window
        self.logger = get_logger("KimiXWebPage")

    def javaScriptConsoleMessage(self, level, message, lineNumber, sourceID):
        """PyQt6 虚方法：捕获前端 console.log"""
        if message and message.startswith("KIMIX_") and self._window:
            self._window._on_js_console(level, message, lineNumber, sourceID)
        # 仍然输出到标准日志（调试用）
        super().javaScriptConsoleMessage(level, message, lineNumber, sourceID)


# ═══════════════════════════════════════════════════════════════
# Kimi Web 启动器（后台线程）
# ═══════════════════════════════════════════════════════════════

class KimiWebLauncher(QThread):
    """后台线程：检测 kimi web，可选自动启动，支持断线重连"""
    started = pyqtSignal(str)       # 返回访问 URL
    error = pyqtSignal(str)         # 错误信息
    status = pyqtSignal(str)        # 状态更新（供 UI 显示）

    def __init__(self, port: int = 5494, auto_start: bool = True):
        super().__init__()
        self.port = port
        self.auto_start = auto_start
        self._running = True
        self._kimi_process: subprocess.Popen | None = None
        self.logger = get_logger("KimiWebLauncher")

    def _scan_kimi_port(self, base: int = 5494, max_scan: int = 10) -> int | None:
        """扫描 kimi web 实际监听的端口"""
        import socket
        for p in range(base, base + max_scan):
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(0.3)
                s.connect(("127.0.0.1", p))
                s.close()
                return p
            except Exception:
                continue
        return None

    def _try_start_kimi_web(self, port: int) -> int | None:
        """尝试自动启动 kimi web（Windows 编码安全）
        
        Returns:
            实际监听的端口号，或 None（启动失败）
        """
        try:
            self.logger.info(f"Attempting to start kimi web on port {port}...")
            env = os.environ.copy()
            env["PYTHONIOENCODING"] = "utf-8"
            # 直接调用 kimi 命令（无窗口模式，丢弃输出避免编码崩溃）
            self._kimi_process = subprocess.Popen(
                ["kimi", "web", "--no-open", "--port", str(port)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                env=env,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
            # 等待启动 —— 扫描全部端口，因为 kimi 可能因占用自动跳到相邻端口
            for _ in range(40):  # 最多 20 秒
                time.sleep(0.5)
                if self._kimi_process.poll() is not None:
                    self.logger.warning("kimi web process exited early")
                    return None
                actual_port = self._scan_kimi_port(base=self.port, max_scan=10)
                if actual_port:
                    self.logger.info(f"kimi web started on port {actual_port}")
                    return actual_port
            self.logger.warning("kimi web start timeout")
            return None
        except Exception as e:
            self.logger.warning(f"Failed to start kimi web: {e}")
            return None

    def run(self):
        self.logger.info("KimiWebLauncher started")
        import socket
        while self._running:
            try:
                port = self._scan_kimi_port(self.port, max_scan=10)
                if port:
                    url = f"http://127.0.0.1:{port}"
                    self.logger.info(f"Detected kimi web on {url}")
                    self.status.emit(f"已连接: {url}")
                    self.started.emit(url)
                    # 持续监控，如果断开则重连
                    while self._running and self._scan_kimi_port(port, max_scan=1):
                        time.sleep(3)
                    if self._running:
                        self.logger.warning("kimi web disconnected, retrying...")
                        self.status.emit("连接断开，正在重连...")
                    continue

                # 未检测到
                if self.auto_start:
                    self.status.emit("正在启动 kimi web...")
                    actual_port = self._try_start_kimi_web(self.port)
                    if actual_port:
                        url = f"http://127.0.0.1:{actual_port}"
                        self.logger.info(f"Auto-started kimi web on {url}")
                        self.status.emit(f"已连接: {url}")
                        self.started.emit(url)
                        # 进入监控循环
                        while self._running and self._scan_kimi_port(actual_port, max_scan=1):
                            time.sleep(3)
                        if self._running:
                            self.logger.warning("kimi web disconnected, retrying...")
                            self.status.emit("连接断开，正在重连...")
                        continue

                msg = "未检测到 kimi web 运行。\n请在终端运行：kimi web --no-open"
                self.logger.warning(msg.replace("\n", " | "))
                self.error.emit(msg)
                # 每 5 秒重试一次
                for _ in range(10):
                    if not self._running:
                        return
                    time.sleep(0.5)
            except Exception as e:
                log_exception(self.logger, f"Launcher loop error: {e}")
                time.sleep(2)

    def stop(self):
        self._running = False
        if self._kimi_process and self._kimi_process.poll() is None:
            try:
                self._kimi_process.terminate()
                self._kimi_process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                self._kimi_process.kill()
            except Exception as e:
                self.logger.debug(f"Stop process error: {e}")


# ═══════════════════════════════════════════════════════════════
# 主窗口
# ═══════════════════════════════════════════════════════════════

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Kimi-X Desktop")
        self.logger = get_logger("MainWindow")
        self.logger.info("=" * 50)
        self.logger.info("MainWindow initializing")

        # ── 加载配置（换电脑时复制 ~/.kimi/kimi-x-config.json 即可）──
        self.config = KimiXConfig()

        # ── 扫描硬件档案（低配电脑自动适配）──
        self.hw_profile = HardwareProfile()
        self.config.hardware_profile = self.hw_profile.to_dict()
        hw_warn = self.hw_profile.get_warning()
        if hw_warn:
            self.logger.warning(f"[Hardware] {hw_warn}")

        # ── 恢复窗口位置 ──
        geo = self.config.window_geometry
        self.setGeometry(*geo)

        # ── 防止多实例 ──
        if not self._check_single_instance():
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(
                self, "Kimi-X 已在运行",
                "检测到另一个 Kimi-X Desktop 实例正在运行。\n"
                "为避免进程膨胀，当前实例将退出。"
            )
            QApplication.quit()
            return

        # ── 首次运行向导 ──
        if self.config.first_run:
            self._show_first_run_wizard()
            self.config.first_run = False

        # ── 项目根目录（配置优先）──
        self.project_root = Path(self.config.project_root)
        if not (self.project_root / "src" / "deep_intent" / "__init__.py").exists():
            self.project_root = self._detect_project_root()
            self.config.project_root = self.project_root

        # 单一 QWebEngineView 加载本地 HTML 外壳
        self.webview = QWebEngineView()
        # 使用自定义 WebPage 捕获 console.log
        self._webpage = KimiXWebPage(self.webview, window=self)
        self.webview.setPage(self._webpage)
        # 允许本地文件访问远程 URL（iframe 加载 http://127.0.0.1:5494）
        settings = self.webview.settings()
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.AllowRunningInsecureContent, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessFileUrls, True)
        self.setCentralWidget(self.webview)

        # 设置 WebChannel（供前端 JS 调用 Python 方法）
        self._bridge = KimiXBridge(self)
        self._channel = QWebChannel()
        self._channel.registerObject("kimiX", self._bridge)
        self.webview.page().setWebChannel(self._channel)

        # 加载本地 web_ui/index.html
        html_path = Path(__file__).parent / "web_ui" / "index.html"
        self.webview.setUrl(QUrl.fromLocalFile(str(html_path.resolve())))

        # 页面加载完成后记录状态
        self._page_loaded = False
        self._pending_di_result: dict | None = None
        self._pending_kimi_url: str | None = None
        self._pending_memory: dict | None = None
        self.webview.loadFinished.connect(self._on_page_loaded)

        # 系统托盘
        self._setup_tray()

        # 启动流水线
        self._start_pipeline()

    def _detect_project_root(self) -> Path:
        """自动检测 DeepIntent 项目根目录"""
        if len(sys.argv) > 1:
            p = Path(sys.argv[1])
            if p.exists():
                return p
        cwd = Path.cwd()
        if (cwd / "src" / "deep_intent" / "__init__.py").exists():
            return cwd
        fallback = Path.home() / "kimi-workspace" / "deep-intent"
        if fallback.exists():
            return fallback
        return cwd

    def _setup_tray(self):
        """系统托盘图标"""
        self.tray = QSystemTrayIcon(self)
        self.tray.setToolTip("Kimi-X Desktop")
        pixmap = QPixmap(32, 32)
        pixmap.fill(QColor("#58a6ff"))
        self.tray.setIcon(QIcon(pixmap))
        menu = QMenu()
        show_action = QAction("显示窗口", self)
        show_action.triggered.connect(self.show)
        settings_action = QAction("设置...", self)
        settings_action.triggered.connect(self._show_settings_dialog)
        quit_action = QAction("退出", self)
        quit_action.triggered.connect(self._on_quit)
        menu.addAction(show_action)
        menu.addAction(settings_action)
        menu.addSeparator()
        menu.addAction(quit_action)
        self.tray.setContextMenu(menu)
        self.tray.activated.connect(self._on_tray_activated)
        self.tray.show()

    def _on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.show()
            self.raise_()
            self.activateWindow()

    def _on_quit(self):
        self._shutdown()
        QApplication.quit()

    def _start_pipeline(self):
        """启动全自动流水线"""
        # 步骤 0: 加载会话记忆
        self._load_session_memory()

        # 步骤 1: DeepIntent 初始化（后台，携带硬件档案做适配）
        self.di_worker = DeepIntentWorker(
            self.project_root,
            hw_profile=self.hw_profile,
        )
        self.di_worker.status_update.connect(self._on_di_status)
        self.di_worker.init_complete.connect(self._on_di_complete)
        self.di_worker.error.connect(self._on_di_error)
        self.di_worker.start()

        # 步骤 2: kimi web（后台，自动启动+重连）
        self.web_launcher = KimiWebLauncher(
            port=self.config.get("kimi_web_port", 5494),
            auto_start=self.config.auto_start_kimi_web,
        )
        self.web_launcher.started.connect(self._on_web_started)
        self.web_launcher.error.connect(self._on_web_error)
        self.web_launcher.status.connect(self._on_web_status)
        self.web_launcher.start()

    def _on_page_loaded(self, ok: bool):
        """本地 HTML 页面加载完成"""
        self.logger.info(f"Local HTML loaded: ok={ok}")
        self._page_loaded = True
        if self._pending_di_result is not None:
            self.logger.debug("Flushing pending DI result")
            self._inject_di_status(self._pending_di_result)
            self._pending_di_result = None
        if self._pending_kimi_url is not None:
            self.logger.debug("Flushing pending kimi URL")
            self._inject_kimi_url(self._pending_kimi_url)
            self._pending_kimi_url = None
        if self._pending_memory is not None:
            self.logger.debug("Flushing pending memory")
            self._inject_memory(self._pending_memory)
            self._pending_memory = None

    def _on_di_status(self, message: str, level: str):
        self.logger.info(f"[DI] [{level}] {message}")

    def _on_di_complete(self, result: dict):
        """DeepIntent 初始化完成 -> 注入到 HTML 面板 + 保存记忆"""
        self.logger.info("DeepIntent init complete, injecting to panel")
        self._write_context_file(result)
        self._save_session_memory(result)  # 保存会话记忆
        if self._page_loaded:
            self._inject_di_status(result)
        else:
            self.logger.debug("Page not loaded yet, queueing DI result")
            self._pending_di_result = result

    def _inject_di_status(self, result: dict):
        """通过 runJavaScript 更新 HTML 面板状态"""
        try:
            js_data = json.dumps(result, ensure_ascii=False)
            self.webview.page().runJavaScript(f"updateDeepIntent({js_data})")
            self.logger.debug("DI status injected to web panel")
        except Exception as e:
            log_exception(self.logger, f"_inject_di_status() failed: {e}")

    def _on_di_error(self, error: str):
        self.logger.error(f"DeepIntentWorker error: {error}")

    def _on_web_started(self, url: str):
        """kimi web 启动成功 -> 更新 iframe URL"""
        self.logger.info(f"Kimi web detected: {url}")
        if self._page_loaded:
            self._inject_kimi_url(url)
        else:
            self.logger.debug("Page not loaded yet, queueing kimi URL")
            self._pending_kimi_url = url

    def _inject_kimi_url(self, url: str):
        """通过 runJavaScript 更新 iframe src"""
        try:
            safe_url = json.dumps(url)
            js = f"""
                var frame = document.getElementById('kimi-frame');
                if (frame && frame.src !== {safe_url}) {{
                    frame.src = {safe_url};
                }}
            """
            self.webview.page().runJavaScript(js)
            self.logger.debug(f"iframe src updated to {url}")
        except Exception as e:
            log_exception(self.logger, f"_inject_kimi_url() failed: {e}")

    def _on_web_status(self, status: str):
        self.logger.info(f"[WebLauncher] {status}")

    def _on_js_console(self, level, message: str, lineNumber: int, sourceId: str):
        """捕获前端 console.log，处理对话学习和反馈"""
        if not message or not message.startswith("KIMIX_"):
            return
        try:
            if message.startswith("KIMIX_LEARN:"):
                text = message[12:]
                self.logger.info(f"[JS Bridge] Learn: {text[:50]}")
                if self.di_worker and self.di_worker.core:
                    result = self.di_worker.process_user_input(text)
                    if result:
                        self.logger.debug(f"Learn result: {len(result.get('probes', []))} probes")
            elif message.startswith("KIMIX_FEEDBACK:"):
                is_positive = message[15:] == "1"
                label = "👍" if is_positive else "👎"
                self.logger.info(f"[JS Bridge] Feedback: {label}")
                if self.di_worker and self.di_worker.core:
                    self.di_worker.receive_feedback("panel_feedback", is_positive)
            elif message.startswith("KIMIX_APIKEY:"):
                key = message[13:]
                if key == "CLEAR":
                    self.config.set_api_key("default", "")
                    self.logger.info("[JS Bridge] API key cleared")
                else:
                    self.config.set_api_key("default", key)
                    self.logger.info("[JS Bridge] API key saved")
        except Exception as e:
            self.logger.warning(f"[JS Bridge] Failed: {e}")

    def _on_web_error(self, error: str):
        self.logger.warning(f"Kimi web detection: {error}")
        # 通过 JS 在 iframe 中显示提示（带一键启动按钮）
        if self._page_loaded:
            js = """
                var frame = document.getElementById('kimi-frame');
                if (frame) {
                    frame.srcdoc = `<html><body style="background:#0d1117;color:#c9d1d9;font-family:sans-serif;
                    display:flex;justify-content:center;align-items:center;height:100vh;margin:0;flex-direction:column;">
                    <h2>Kimi Web UI 未连接</h2>
                    <p style="color:#8b949e;margin:8px 0;">Kimi-X 正在尝试自动启动...</p>
                    <p style="color:#6e7681;font-size:12px;margin-top:12px;">如果长时间未连接，请在终端运行：</p>
                    <code style="background:#21262d;padding:6px 12px;border-radius:4px;border:1px solid #30363d;">kimi web --no-open</code>
                    </body></html>`;
                }
            """
            self.webview.page().runJavaScript(js)

    # ── 会话记忆：解决"失忆"问题 ──

    MEMORY_FILE = Path.home() / ".kimi" / "kimi-x-memory.json"

    def _load_session_memory(self):
        """启动时加载上次会话记忆，显示欢迎回来信息"""
        try:
            if self.MEMORY_FILE.exists():
                data = json.loads(self.MEMORY_FILE.read_text(encoding="utf-8"))
                last_time = data.get("last_session", "未知时间")
                di_status = data.get("deepintent_status", {})
                todos = data.get("todos", [])
                summary = data.get("summary", "")
                self.logger.info(f"Session memory loaded: last session {last_time}")
                # 通过 JS 注入到前端
                if self._page_loaded:
                    self._inject_memory(data)
                else:
                    self._pending_memory = data
            else:
                self.logger.info("No session memory found (first run?)")
                self._pending_memory = None
        except Exception as e:
            self.logger.warning(f"Failed to load session memory: {e}")
            self._pending_memory = None

    def _save_session_memory(self, result: dict | None = None):
        """保存当前会话状态，供下次恢复"""
        try:
            data = {
                "last_session": time.strftime('%Y-%m-%d %H:%M:%S'),
                "deepintent_status": result or {},
                "project_root": str(self.project_root),
                "summary": "Kimi-X Desktop 运行中",
            }
            self.MEMORY_FILE.parent.mkdir(parents=True, exist_ok=True)
            self.MEMORY_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
            self.logger.info("Session memory saved")
        except Exception as e:
            self.logger.warning(f"Failed to save session memory: {e}")

    def _inject_memory(self, data: dict):
        """将记忆注入到前端面板"""
        try:
            js_data = json.dumps(data, ensure_ascii=False)
            js = f"""if (typeof updateMemory === 'function') updateMemory({js_data});"""
            self.webview.page().runJavaScript(js)
        except Exception as e:
            self.logger.debug(f"Memory injection failed: {e}")

    def _write_context_file(self, result: dict):
        """将 DeepIntent 上下文写入项目目录，供 Kimi AI 读取"""
        try:
            ctx_dir = self.project_root / ".kimi" / "auto-context"
            ctx_dir.mkdir(parents=True, exist_ok=True)
            reg = result.get("regulator", {})
            ctx_file = ctx_dir / "deepintent-live.md"
            content = f"""# DeepIntent v2.1 实时上下文（Kimi-X 自动生成）

> 生成时间: {time.strftime('%Y-%m-%d %H:%M:%S')}
> 项目路径: `{self.project_root}`

## 系统状态
| 指标 | 状态 |
|------|------|
| 项目检测 | DeepIntent v2.1 |
| 模块导入 | {'OK' if result.get('import_ok') else 'FAIL'} v{result.get('version', '?')} |
| 单元测试 | {'OK' if result.get('tests_ok') else 'FAIL'} {result.get('tests_summary', '--')} |
| Core 实例 | {'OK' if result.get('core_initialized') else 'FAIL'} |
| Regulator | {reg.get('mode', '?').upper()} 模式 (CPU {reg.get('current_load_pct', '?')}%) |

## 当前防护阈值（实际生效值）
```python
METHOD_TIMEOUT_SECONDS = 3.0      # 方法运行超时
MAX_INPUT_LENGTH = 8_000          # 单次输入字符限制
MAX_PENDING_MEMORIES = 2_000      # SoftDeletionBuffer 上限
MAX_USERS = 5_000                 # MetaLearningValidator 上限
MAX_TURNS_PER_SESSION = 50        # 单会话轮数上限
```

## 核心入口代码（常驻模式）
```python
from deep_intent import DeepIntentCore, CPURegulator
core = DeepIntentCore(persist_dir="./data/deep_intent")

# 处理用户输入（学习偏好）
result = core.process_user_turn("用户请求文本")

# 接收反馈（驱动进化）
core.receive_user_feedback("用户回复", is_positive=True)

# 查看状态
status = core.get_regulator_status()

# 手动保存（每60秒自动保存）
core.persist()

# 退出时关闭
core.shutdown()
```

## 用户偏好学习（由 Kimi-X 面板交互驱动）
- 在 Kimi-X 左侧面板输入"本次对话主题" → Core 学习用户意图
- 点击 👍/👎 → Core 接收奖惩信号，更新偏好维度
- 所有学习状态每 60 秒自动保存到磁盘
- Core 常驻运行，CPU 占用实测为 0%

## 5 个闭环验证器状态
- **Gap1 RetrievalValidator** — 检索调整后是否真有帮助
- **Gap2 FixTracker** — 修复后是否真解决问题
- **Gap3 SoftDeletionBufferV2** — 删除前确认无隐式使用
- **Gap4 MetaLearningValidator** — 先验真加速收敛吗
- **Gap5 ProxyValidator** — 短期信号能预测长期吗

运行 `core.get_closed_loop_report()` 查看详细统计。

## 重要约束
- **已删除 autoresearch 子模块**（递归 pytest 会导致 CPU 满载卡死）
- **不要同时跑多个 DeepIntentCore 实例**（4 核 CPU 容易满载）
- **persist_dir 在 C 盘 SSD 上**，IO 性能良好
- **82GB 内存充裕**，pending/users 缓存上限可放心使用

## 组件速查
| 组件 | 功能 | 关键类 |
|------|------|--------|
| TemporalMemory | 时间衰减+选择性遗忘 | TemporalDecayEngine, SoftDeletionBufferV2 |
| SelfReflection | 错误修复闭环 | SelfReflectionEngine, ErrorPattern |
| RewardPunishment | 奖惩信号驱动学习 | RewardPunishmentEngine, RewardSignal |
| EvolutionEngine | 全系统参数进化 | EvolutionEngine, ComponentFeedback |
| ActiveExploration | A/B 探针探测偏好 | ActiveExplorationEngine, ExplorationProbe |
| AssociationEngine | 任务扩展图 | ActiveAssociationEngine, AssociationNode |
| PredictionExtractor | 股票/预测提取 | PredictionExtractor（类方法为主） |
| PredictionTracker | 预测准确率跟踪 | PredictionTracker, Prediction |

## 最近持久化统计
{chr(10).join(f"- `{k}`: {v}" for k, v in result.get('persistence_stats', {}).items())}
"""
            ctx_file.write_text(content, encoding="utf-8")
            self.logger.info(f"Context file written: {ctx_file}")
        except Exception as e:
            log_exception(self.logger, f"_write_context_file() failed: {e}")

    # ── 设置与向导 ──

    def _show_first_run_wizard(self):
        """首次运行：静默检测路径，不弹窗打扰；密钥放到 Web UI 面板输入"""
        from PyQt6.QtWidgets import QMessageBox
        # 自动检测项目路径（不弹窗）
        detected = self._detect_project_root()
        if detected and (detected / "src" / "deep_intent" / "__init__.py").exists():
            self.config.project_root = detected
            self.project_root = detected
            self.logger.info(f"Auto-detected project root: {detected}")
        else:
            self.logger.warning("Could not auto-detect DeepIntent project")

        # 硬件报告（只弹一次，简洁）
        QMessageBox.information(
            self, "Kimi-X Desktop",
            f"首次启动\n\n"
            f"硬件: {self.hw_profile.cpu_cores}核/{self.hw_profile.cpu_threads}线程, "
            f"{self.hw_profile.memory_gb:.1f}GB 内存\n"
            f"等级: {self.hw_profile.profile_name.upper()}\n\n"
            f"API 密钥可在左侧面板随时输入。"
        )

    def _show_settings_dialog(self):
        """设置对话框：修改项目路径、API 密钥、导出配置"""
        from PyQt6.QtWidgets import (
            QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
            QPushButton, QFileDialog, QMessageBox, QCheckBox,
        )
        dlg = QDialog(self)
        dlg.setWindowTitle("Kimi-X 设置")
        dlg.setMinimumWidth(420)
        layout = QVBoxLayout(dlg)
        layout.setSpacing(12)

        # 项目路径
        layout.addWidget(QLabel("DeepIntent 项目路径:"))
        row = QHBoxLayout()
        path_edit = QLineEdit(str(self.config.project_root))
        row.addWidget(path_edit)
        btn_browse = QPushButton("浏览...")
        def _browse():
            p = QFileDialog.getExistingDirectory(dlg, "选择项目目录", path_edit.text())
            if p:
                path_edit.setText(p)
        btn_browse.clicked.connect(_browse)
        row.addWidget(btn_browse)
        layout.addLayout(row)

        # API 密钥
        layout.addWidget(QLabel("API 密钥（可选）:"))
        key_edit = QLineEdit(self.config.get_api_key("default"))
        key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addWidget(key_edit)

        # 自动启动 kimi web
        auto_cb = QCheckBox("自动启动 kimi web（推荐）")
        auto_cb.setChecked(self.config.auto_start_kimi_web)
        layout.addWidget(auto_cb)

        # 硬件信息
        hw = self.config.hardware_profile or {}
        layout.addWidget(QLabel(
            f"硬件档案: {hw.get('cpu_cores','?')}C/{hw.get('cpu_threads','?')}T, "
            f"{hw.get('memory_gb','?')}GB, {hw.get('profile_name','?')}"
        ))

        # 按钮行
        btn_row = QHBoxLayout()
        btn_save = QPushButton("保存")
        btn_export = QPushButton("导出配置（换电脑用）")
        btn_cancel = QPushButton("取消")
        btn_row.addWidget(btn_save)
        btn_row.addWidget(btn_export)
        btn_row.addStretch()
        btn_row.addWidget(btn_cancel)
        layout.addLayout(btn_row)

        def do_save():
            self.config.project_root = Path(path_edit.text())
            self.config.set_api_key("default", key_edit.text())
            self.config.auto_start_kimi_web = auto_cb.isChecked()
            self.project_root = Path(path_edit.text())
            self.logger.info("Settings saved")
            dlg.accept()

        def do_export():
            from PyQt6.QtWidgets import QFileDialog
            path, _ = QFileDialog.getSaveFileName(
                dlg, "导出配置", str(Path.home() / "kimi-x-config-backup.json"),
                "JSON (*.json)"
            )
            if path:
                self.config.export_for_migration(path)
                QMessageBox.information(dlg, "导出成功", f"配置已保存到:\n{path}")

        btn_save.clicked.connect(do_save)
        btn_export.clicked.connect(do_export)
        btn_cancel.clicked.connect(dlg.reject)
        dlg.exec()

    def closeEvent(self, event):
        self._shutdown()
        event.accept()

    def _shutdown(self):
        """优雅关闭 — 先保存 Core 学习状态，再清理自己的资源，绝不碰 kimi 进程"""
        self.logger.info("Shutdown sequence started")
        # 1. 保存 DeepIntentCore 学习状态
        if hasattr(self, 'di_worker') and self.di_worker.core:
            self.logger.info("Persisting DeepIntentCore before exit...")
            try:
                self.di_worker.core.persist()
            except Exception as e:
                self.logger.warning(f"Final persist failed: {e}")
            self.di_worker.shutdown_core()

        # 2. 等待 worker 线程结束
        if hasattr(self, 'di_worker') and self.di_worker.isRunning():
            self.di_worker.terminate()
            self.di_worker.wait(3000)

        # 3. 停止 web_launcher
        if hasattr(self, 'web_launcher') and self.web_launcher.isRunning():
            self.web_launcher.stop()
            self.web_launcher.wait(3000)

        # 4. 保存窗口位置
        try:
            self.config.window_geometry = [
                self.x(), self.y(), self.width(), self.height()
            ]
        except Exception as e:
            self.logger.debug(f"Save geometry failed: {e}")

        # 5. 删除 PID 文件
        self._remove_pid_file()
        self.logger.info("Shutdown complete — Core persisted, kimi untouched")

    def _cleanup_ports(self):
        """[已弃用] 不再扫描并关闭端口，避免误杀 kimi web"""
        self.logger.debug("_cleanup_ports: skipped (no longer killing external ports)")

    def _cleanup_kimi_processes(self):
        """[已弃用] 不再关闭 kimi.exe，避免中断用户对话"""
        self.logger.debug("_cleanup_kimi_processes: skipped (no longer killing kimi)")

    # ── PID 文件管理：防止多实例膨胀 ──

    PID_FILE = Path.home() / ".kimi" / "kimi-x.pid"

    def _check_single_instance(self) -> bool:
        """检查是否已有实例在运行，防止进程膨胀"""
        try:
            if self.PID_FILE.exists():
                pid = int(self.PID_FILE.read_text(encoding="utf-8").strip())
                # Windows: 检查进程是否存在
                result = subprocess.run(
                    ["tasklist", "/FI", f"PID eq {pid}", "/NH"],
                    capture_output=True, text=True,
                    creationflags=subprocess.CREATE_NO_WINDOW,
                )
                if str(pid) in result.stdout:
                    self.logger.warning(f"Another Kimi-X instance already running (PID {pid})")
                    return False
                else:
                    self.logger.info(f"Stale PID file found ({pid}), removing")
                    self.PID_FILE.unlink()
            self.PID_FILE.parent.mkdir(parents=True, exist_ok=True)
            self.PID_FILE.write_text(str(os.getpid()), encoding="utf-8")
            return True
        except Exception as e:
            self.logger.warning(f"PID check failed: {e}")
            return True  # 如果检查失败，允许启动

    def _remove_pid_file(self):
        try:
            if self.PID_FILE.exists():
                self.PID_FILE.unlink()
                self.logger.debug("PID file removed")
        except Exception as e:
            self.logger.debug(f"PID remove failed: {e}")


# ═══════════════════════════════════════════════════════════════
# 入口
# ═══════════════════════════════════════════════════════════════

def main():
    # Windows 控制台 UTF-8 编码修复（pythonw.exe 无控制台时跳过）
    import io
    if sys.platform == "win32":
        if sys.stdout is not None and hasattr(sys.stdout, 'buffer'):
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        if sys.stderr is not None and hasattr(sys.stderr, 'buffer'):
            sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

    logger = get_logger("main")
    logger.info("Application starting")

    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    # 启动画面（双击后立即反馈）
    from PyQt6.QtWidgets import QSplashScreen
    splash_pix = QPixmap(420, 220)
    splash_pix.fill(QColor("#0d1117"))
    splash = QSplashScreen(splash_pix)
    splash.setStyleSheet("QSplashScreen { border: 2px solid #30363d; border-radius: 8px; }")
    splash.showMessage(
        "\n\n\n  Kimi-X Desktop\n"
        "  DeepIntent v2.1 共生壳\n\n"
        "  正在启动...",
        alignment=Qt.AlignmentFlag.AlignCenter,
        color=QColor("#58a6ff"),
    )
    splash.show()
    app.processEvents()

    # 全局字体
    font = QFont("Segoe UI", 10)
    if not QFont(font).exactMatch():
        font = QFont("Microsoft YaHei", 10)
    app.setFont(font)

    # 调色板（深色）
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor("#0d1117"))
    palette.setColor(QPalette.ColorRole.WindowText, QColor("#c9d1d9"))
    palette.setColor(QPalette.ColorRole.Base, QColor("#161b22"))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor("#21262d"))
    palette.setColor(QPalette.ColorRole.ToolTipBase, QColor("#21262d"))
    palette.setColor(QPalette.ColorRole.ToolTipText, QColor("#c9d1d9"))
    palette.setColor(QPalette.ColorRole.Text, QColor("#c9d1d9"))
    palette.setColor(QPalette.ColorRole.Button, QColor("#21262d"))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor("#c9d1d9"))
    palette.setColor(QPalette.ColorRole.Highlight, QColor("#1f6feb"))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor("#ffffff"))
    app.setPalette(palette)

    window = MainWindow()
    window.show()
    splash.finish(window)
    logger.info("MainWindow shown, splash finished")

    # 确保任何退出方式（包括系统托盘）都会执行清理
    app.aboutToQuit.connect(window._shutdown)

    logger.info("Entering event loop")
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
