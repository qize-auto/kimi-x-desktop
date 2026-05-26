"""Batch patch main.py to use logger instead of print"""
import re

with open("main.py", "r", encoding="utf-8") as f:
    content = f.read()

# 1. 添加 logger 导入
content = content.replace(
    "from deepintent_worker import DeepIntentWorker",
    "from deepintent_worker import DeepIntentWorker\nfrom logger import get_logger, log_exception"
)

# 2. KimiWebLauncher 添加 logger
content = content.replace(
    '    def __init__(self, port: int = 5494):\n        super().__init__()\n        self.port = port\n\n    def _scan_kimi_port',
    '    def __init__(self, port: int = 5494):\n        super().__init__()\n        self.port = port\n        self.logger = get_logger("KimiWebLauncher")\n\n    def _scan_kimi_port'
)

# 3. KimiWebLauncher.run() 添加日志
old = '''    def run(self):
        try:
            port = self._scan_kimi_port(self.port, max_scan=10)
            if port:
                self.started.emit(f"http://127.0.0.1:{port}")
                return
            self.error.emit(
                "未检测到 kimi web 运行 (端口 5494-5503)。\\n"
                "请手动启动：kimi web --no-open\\n"
                "启动后 Kimi-X 会自动连接。"
            )
        except Exception as e:
            self.error.emit(f"检测异常: {e}")'''
new = '''    def run(self):
        self.logger.info("Scanning ports 5494-5503 for kimi web...")
        try:
            port = self._scan_kimi_port(self.port, max_scan=10)
            if port:
                url = f"http://127.0.0.1:{port}"
                self.logger.info(f"Detected kimi web on {url}")
                self.started.emit(url)
                return
            msg = "未检测到 kimi web 运行 (端口 5494-5503)。\\n请手动启动：kimi web --no-open\\n启动后 Kimi-X 会自动连接。"
            self.logger.warning(msg.replace("\\n", " | "))
            self.error.emit(msg)
        except Exception as e:
            log_exception(self.logger, f"Port scan failed: {e}")
            self.error.emit(f"检测异常: {e}")'''
content = content.replace(old, new)

# 4. MainWindow.__init__ 添加 logger + 替换 print
old = '''class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Kimi-X Desktop")
        self.setGeometry(80, 60, 1480, 900)

        # 启动时兜底清理：上次崩溃/异常退出留下的残留
        print("[startup] 清理上次残留的端口和进程...")
        self._cleanup_ports()
        self._cleanup_kimi_processes()'''
new = '''class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Kimi-X Desktop")
        self.setGeometry(80, 60, 1480, 900)
        self.logger = get_logger("MainWindow")
        self.logger.info("=" * 50)
        self.logger.info("MainWindow initializing")

        # 启动时兜底清理：上次崩溃/异常退出留下的残留
        self.logger.info("[startup] 清理上次残留的端口和进程...")
        self._cleanup_ports()
        self._cleanup_kimi_processes()'''
content = content.replace(old, new)

# 5. _on_page_loaded
old = '''    def _on_page_loaded(self, ok: bool):
        """本地 HTML 页面加载完成"""
        self._page_loaded = True
        # 执行pending的更新
        if self._pending_di_result is not None:
            self._inject_di_status(self._pending_di_result)
            self._pending_di_result = None
        if self._pending_kimi_url is not None:
            self._inject_kimi_url(self._pending_kimi_url)
            self._pending_kimi_url = None'''
new = '''    def _on_page_loaded(self, ok: bool):
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
            self._pending_kimi_url = None'''
content = content.replace(old, new)

# 6. _on_di_status
content = content.replace(
    '    def _on_di_status(self, message: str, level: str):\n        print(f"[{level}] {message}")',
    '    def _on_di_status(self, message: str, level: str):\n        self.logger.info(f"[DI] [{level}] {message}")'
)

# 7. _on_di_complete
old = '''    def _on_di_complete(self, result: dict):
        """DeepIntent 初始化完成 -> 注入到 HTML 面板"""
        self._write_context_file(result)
        if self._page_loaded:
            self._inject_di_status(result)
        else:
            self._pending_di_result = result'''
new = '''    def _on_di_complete(self, result: dict):
        """DeepIntent 初始化完成 -> 注入到 HTML 面板"""
        self.logger.info("DeepIntent init complete, injecting to panel")
        self._write_context_file(result)
        if self._page_loaded:
            self._inject_di_status(result)
        else:
            self.logger.debug("Page not loaded yet, queueing DI result")
            self._pending_di_result = result'''
content = content.replace(old, new)

# 8. _inject_di_status
old = '''    def _inject_di_status(self, result: dict):
        """通过 runJavaScript 更新 HTML 面板状态"""
        try:
            js_data = json.dumps(result, ensure_ascii=False)
            self.webview.page().runJavaScript(f"updateDeepIntent({js_data})")
        except Exception as e:
            print(f"注入状态失败: {e}")'''
new = '''    def _inject_di_status(self, result: dict):
        """通过 runJavaScript 更新 HTML 面板状态"""
        try:
            js_data = json.dumps(result, ensure_ascii=False)
            self.webview.page().runJavaScript(f"updateDeepIntent({js_data})")
            self.logger.debug("DI status injected to web panel")
        except Exception as e:
            log_exception(self.logger, f"_inject_di_status() failed: {e}")'''
content = content.replace(old, new)

# 9. _on_di_error
content = content.replace(
    '    def _on_di_error(self, error: str):\n        print(f"DeepIntent 错误: {error}")',
    '    def _on_di_error(self, error: str):\n        self.logger.error(f"DeepIntentWorker error: {error}")'
)

# 10. _on_web_started
old = '''    def _on_web_started(self, url: str):
        """kimi web 启动成功 -> 更新 iframe URL"""
        print(f"Kimi Web UI: {url}")
        if self._page_loaded:
            self._inject_kimi_url(url)
        else:
            self._pending_kimi_url = url'''
new = '''    def _on_web_started(self, url: str):
        """kimi web 启动成功 -> 更新 iframe URL"""
        self.logger.info(f"Kimi web detected: {url}")
        if self._page_loaded:
            self._inject_kimi_url(url)
        else:
            self.logger.debug("Page not loaded yet, queueing kimi URL")
            self._pending_kimi_url = url'''
content = content.replace(old, new)

# 11. _inject_kimi_url
old = '''    def _inject_kimi_url(self, url: str):
        """通过 runJavaScript 更新 iframe src"""
        try:
            safe_url = json.dumps(url)
            js = f"""
                var frame = document.getElementById(\'kimi-frame\');
                if (frame && frame.src !== {safe_url}) {{
                    frame.src = {safe_url};
                }}
            """
            self.webview.page().runJavaScript(js)
        except Exception as e:
            print(f"更新 iframe URL 失败: {e}")'''
new = '''    def _inject_kimi_url(self, url: str):
        """通过 runJavaScript 更新 iframe src"""
        try:
            safe_url = json.dumps(url)
            js = f"""
                var frame = document.getElementById(\'kimi-frame\');
                if (frame && frame.src !== {safe_url}) {{
                    frame.src = {safe_url};
                }}
            """
            self.webview.page().runJavaScript(js)
            self.logger.debug(f"iframe src updated to {url}")
        except Exception as e:
            log_exception(self.logger, f"_inject_kimi_url() failed: {e}")'''
content = content.replace(old, new)

# 12. _on_web_error
content = content.replace(
    '    def _on_web_error(self, error: str):\n        print(f"Kimi Web: {error}")',
    '    def _on_web_error(self, error: str):\n        self.logger.warning(f"Kimi web detection: {error}")'
)

# 13. _write_context_file
old = '''            ctx_file.write_text(content, encoding="utf-8")
            print(f"上下文已写入: {ctx_file}")
        except Exception as e:
            print(f"写入上下文失败: {e}")'''
new = '''            ctx_file.write_text(content, encoding="utf-8")
            self.logger.info(f"Context file written: {ctx_file}")
        except Exception as e:
            log_exception(self.logger, f"_write_context_file() failed: {e}")'''
content = content.replace(old, new)

# 14. _shutdown
old = '''    def _shutdown(self):
        """优雅关闭 + 彻底清理 kimi web 残留"""
        # 1. 等待 DeepIntentWorker
        if hasattr(self, \'di_worker\') and self.di_worker.isRunning():
            self.di_worker.terminate()
            self.di_worker.wait(3000)

        # 2. 清理占用 5494-5503 端口的所有进程
        self._cleanup_ports()

        # 3. 清理所有 kimi.exe 进程
        self._cleanup_kimi_processes()'''
new = '''    def _shutdown(self):
        """优雅关闭 + 彻底清理 kimi web 残留"""
        self.logger.info("Shutdown sequence started")
        # 1. 等待 DeepIntentWorker
        if hasattr(self, \'di_worker\') and self.di_worker.isRunning():
            self.logger.info("Terminating DeepIntentWorker...")
            self.di_worker.terminate()
            self.di_worker.wait(3000)

        # 2. 清理占用 5494-5503 端口的所有进程
        self.logger.info("Cleaning up ports 5494-5503...")
        self._cleanup_ports()

        # 3. 清理所有 kimi.exe 进程
        self.logger.info("Cleaning up kimi.exe processes...")
        self._cleanup_kimi_processes()
        self.logger.info("Shutdown complete")'''
content = content.replace(old, new)

# 15. _cleanup_ports
old = '''    def _cleanup_ports(self):
        """扫描并关闭占用 5494-5503 端口的进程"""
        import socket
        for port in range(5494, 5504):
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(0.3)
                s.connect(("127.0.0.1", port))
                s.close()
                # 端口被占用，尝试查找并关闭进程
                self._kill_port_process(port)
            except Exception:
                pass'''
new = '''    def _cleanup_ports(self):
        """扫描并关闭占用 5494-5503 端口的进程"""
        import socket
        killed = 0
        for port in range(5494, 5504):
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(0.3)
                s.connect(("127.0.0.1", port))
                s.close()
                self._kill_port_process(port)
                killed += 1
            except Exception:
                pass
        if killed:
            self.logger.info(f"Cleaned up {killed} occupied port(s)")
        else:
            self.logger.debug("No occupied ports found")'''
content = content.replace(old, new)

# 16. _kill_port_process
old = '''                    subprocess.run(
                        ["taskkill", "/F", "/PID", pid],
                        capture_output=True, timeout=5,
                        creationflags=subprocess.CREATE_NO_WINDOW,
                    )
                    print(f"[cleanup] Killed PID {pid} on port {port}")
        except Exception as e:
            print(f"[cleanup] Port {port}: {e}")'''
new = '''                    subprocess.run(
                        ["taskkill", "/F", "/PID", pid],
                        capture_output=True, timeout=5,
                        creationflags=subprocess.CREATE_NO_WINDOW,
                    )
                    self.logger.info(f"[cleanup] Killed PID {pid} on port {port}")
        except Exception as e:
            self.logger.warning(f"[cleanup] Port {port}: {e}")'''
content = content.replace(old, new)

# 17. _cleanup_kimi_processes
old = '''    def _cleanup_kimi_processes(self):
        """关闭所有 kimi.exe 进程"""
        for name in ("kimi.exe",):
            try:
                subprocess.run(
                    ["taskkill", "/F", "/IM", name],
                    capture_output=True, timeout=5,
                    creationflags=subprocess.CREATE_NO_WINDOW,
                )
            except Exception:
                pass'''
new = '''    def _cleanup_kimi_processes(self):
        """关闭所有 kimi.exe 进程"""
        for name in ("kimi.exe",):
            try:
                result = subprocess.run(
                    ["taskkill", "/F", "/IM", name],
                    capture_output=True, timeout=5,
                    creationflags=subprocess.CREATE_NO_WINDOW,
                )
                if result.returncode == 0:
                    self.logger.info(f"[cleanup] Killed all {name} processes")
            except Exception as e:
                self.logger.debug(f"[cleanup] {name}: {e}")'''
content = content.replace(old, new)

# 18. main() 开头添加日志
old = '''def main():
    # Windows 控制台 UTF-8 编码修复
    import io
    if sys.platform == "win32":
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding=\'utf-8\', errors=\'replace\')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding=\'utf-8\', errors=\'replace\')

    app = QApplication(sys.argv)
    app.setStyle("Fusion")'''
new = '''def main():
    # Windows 控制台 UTF-8 编码修复
    import io
    if sys.platform == "win32":
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding=\'utf-8\', errors=\'replace\')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding=\'utf-8\', errors=\'replace\')

    logger = get_logger("main")
    logger.info("Application starting")

    app = QApplication(sys.argv)
    app.setStyle("Fusion")'''
content = content.replace(old, new)

# 19. main() 结束添加日志
old = '''    window = MainWindow()
    window.show()
    splash.finish(window)

    # 确保任何退出方式（包括系统托盘）都会执行清理
    app.aboutToQuit.connect(window._shutdown)

    sys.exit(app.exec())'''
new = '''    window = MainWindow()
    window.show()
    splash.finish(window)
    logger.info("MainWindow shown, splash finished")

    # 确保任何退出方式（包括系统托盘）都会执行清理
    app.aboutToQuit.connect(window._shutdown)

    logger.info("Entering event loop")
    sys.exit(app.exec())'''
content = content.replace(old, new)

with open("main.py", "w", encoding="utf-8") as f:
    f.write(content)

print("main.py updated successfully")
