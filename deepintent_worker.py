"""
DeepIntent v2.1 后台初始化线程
==============================
在 QThread 中自动完成检测 → 验证 → 实例化 → 状态读取
不阻塞 UI 主线程
"""
from __future__ import annotations
import os
import sys
import json
import time
import subprocess
from pathlib import Path
from PyQt6.QtCore import QThread, pyqtSignal

from logger import get_logger, log_exception


class DeepIntentWorker(QThread):
    """后台线程：初始化 DeepIntent v2.1 并常驻运行"""

    status_update = pyqtSignal(str, str)   # (message, level)
    init_complete = pyqtSignal(dict)       # 完整初始化结果
    core_ready = pyqtSignal(object)        # Core 实例已常驻
    error = pyqtSignal(str)                # 错误信息

    def __init__(self, project_root: str | Path | None = None, hw_profile=None):
        super().__init__()
        self.project_root = Path(project_root) if project_root else Path.cwd()
        self.hw_profile = hw_profile
        self.result: dict = {"detected": False}
        self.core: object | None = None      # 常驻的 DeepIntentCore
        self._running = True
        self.logger = get_logger("DeepIntentWorker")
        self.logger.info(f"Worker initialized, project_root={self.project_root}")
        if hw_profile:
            self.logger.info(f"Hardware profile: {hw_profile.profile_name}")

    def run(self):
        try:
            self._run_init()
            if self.core:
                self._resident_loop()
        except Exception as e:
            log_exception(self.logger, f"run() 未捕获异常: {e}")
            self.error.emit(f"初始化异常: {e}")
            self.init_complete.emit(self.result)

    def process_user_input(self, text: str) -> dict | None:
        """主线程调用：让 Core 处理用户输入"""
        if self.core is None:
            return None
        try:
            return self.core.process_user_turn(text)
        except Exception as e:
            self.logger.warning(f"process_user_turn failed: {e}")
            return None

    def receive_feedback(self, text: str, is_positive: bool) -> dict | None:
        """主线程调用：向 Core 反馈用户评价，并持久化到磁盘"""
        result = None
        if self.core is not None:
            try:
                result = self.core.receive_user_feedback(text, is_positive=is_positive)
            except Exception as e:
                self.logger.warning(f"core.receive_user_feedback failed: {e}")
        # ── P1: 反馈持久化 ──
        try:
            self._persist_feedback(text, is_positive)
        except Exception as e:
            self.logger.warning(f"feedback persistence failed: {e}")
        return result

    def _persist_feedback(self, text: str, is_positive: bool):
        """将反馈追加写入 ~/.kimi/kimi-x-desktop/feedback/<project>.jsonl"""
        feedback_dir = Path.home() / ".kimi" / "kimi-x-desktop" / "feedback"
        feedback_dir.mkdir(parents=True, exist_ok=True)
        # 用 project_root 的目录名作为文件名
        project_name = self.project_root.name or "default"
        safe_name = "".join(c if c.isalnum() or c in "-_" else "_" for c in project_name)
        file_path = feedback_dir / f"{safe_name}.jsonl"
        record = {
            "timestamp": time.time(),
            "text": text,
            "is_positive": is_positive,
            "project_root": str(self.project_root),
        }
        with open(file_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
        self.logger.info(f"Feedback persisted: {file_path.name} ({'+' if is_positive else '-'}) text={text[:30]}")

    def shutdown_core(self):
        """主线程调用：优雅关闭常驻 Core"""
        self._running = False
        if self.core:
            try:
                self.core.shutdown()
                self.logger.info("DeepIntentCore shutdown by request")
            except Exception as e:
                self.logger.warning(f"shutdown_core error: {e}")
            self.core = None

    def _run_init(self):
        self.logger.info("Step 1/7: 检测项目结构")
        self.status_update.emit("[info] 检测 DeepIntent v2.1 项目结构...", "info")

        init_file = self.project_root / "src" / "deep_intent" / "__init__.py"
        if not init_file.exists():
            self.logger.error(f"init_file not found: {init_file}")
            self.status_update.emit("[error] 未检测到 DeepIntent 项目", "error")
            self.result["detected"] = False
            self.init_complete.emit(self.result)
            return

        content = init_file.read_text(encoding="utf-8")
        if '__version__ = "2.1.0"' not in content:
            self.logger.warning(f"Version mismatch in {init_file}")
            self.status_update.emit("[warn] 检测到 deep_intent 但版本不是 v2.1.0", "warn")
            self.result["detected"] = False
            self.init_complete.emit(self.result)
            return

        self.result["detected"] = True
        self.logger.info("Project detected: DeepIntent v2.1")
        self.status_update.emit("[ok] 检测到 DeepIntent v2.1", "success")

        # ── 2. 运行 pytest ──
        self.logger.info("Step 2/7: 运行 pytest")
        self.status_update.emit("[info] 运行 pytest 验证完整性...", "info")
        self._run_pytest()

        # ── 3. 导入并实例化 Core ──
        self.logger.info("Step 3/7: 导入并实例化 Core")
        self.status_update.emit("[info] 导入 deep_intent 模块...", "info")

        old_path = sys.path.copy()
        try:
            src_path = str(self.project_root / "src")
            if src_path not in sys.path:
                sys.path.insert(0, src_path)

            import deep_intent
            self.result["import_ok"] = True
            self.result["version"] = getattr(deep_intent, "__version__", "unknown")
            self.status_update.emit(f"[ok] 导入成功 (v{self.result['version']})", "success")

            persist_dir = self.project_root / "data" / "deep_intent"
            hw_params = self.hw_profile.get_deepintent_params() if self.hw_profile else {}
            self.core = deep_intent.DeepIntentCore(
                persist_dir=str(persist_dir),
                hw_profile=hw_params,
            )
            self.result["core_initialized"] = True
            self.status_update.emit("[ok] DeepIntentCore 已启动（常驻模式）", "success")
            self.logger.info("DeepIntentCore initialized in resident mode")

            # 读取状态
            self._read_core_status()

            # 发射信号：Core 已准备好接收输入
            self.core_ready.emit(self.core)

        except Exception as e:
            self.result["import_ok"] = False
            log_exception(self.logger, f"Import or instantiation failed: {e}")
            self.status_update.emit(f"[error] 导入失败: {e}", "error")
        finally:
            sys.path = old_path

        self.result["project_root"] = str(self.project_root)
        self.init_complete.emit(self.result)

    def _run_pytest(self):
        tests_dir = self.project_root / "tests"
        if not tests_dir.exists():
            self.result["tests_ok"] = False
            return
        try:
            pytest_ini = self.project_root / "pytest.ini"
            pytest_ini_created = False
            if not pytest_ini.exists():
                pytest_ini.write_text("[pytest]\npythonpath = src\n", encoding="utf-8")
                pytest_ini_created = True

            proc = subprocess.run(
                [sys.executable, "-m", "pytest", "tests/", "-v", "--tb=short"],
                cwd=self.project_root, capture_output=True, text=True, timeout=60,
            )
            if pytest_ini_created and pytest_ini.exists():
                pytest_ini.unlink()

            self.result["tests_returncode"] = proc.returncode
            self.result["tests_stdout"] = proc.stdout
            self.result["tests_stderr"] = proc.stderr

            if proc.returncode == 0:
                last_line = [l for l in proc.stdout.splitlines() if "passed" in l][-1]
                self.result["tests_summary"] = last_line.strip()
                self.result["tests_ok"] = True
                self.status_update.emit(f"[ok] {last_line.strip()}", "success")
            else:
                self.result["tests_ok"] = False
                self.status_update.emit("[warn] 测试有失败", "warn")
        except Exception as e:
            self.result["tests_ok"] = False
            self.status_update.emit(f"[warn] 测试异常: {e}", "warn")

    def _read_core_status(self):
        try:
            reg_status = self.core.get_regulator_status()
            self.result["regulator"] = reg_status
            self.status_update.emit(
                f"[info] Regulator: {reg_status.get('mode', '?')} "
                f"(CPU {reg_status.get('current_load_pct', '?')}%)", "info"
            )
        except Exception as e:
            self.result["regulator"] = None

        try:
            loop_report = self.core.get_closed_loop_report()
            self.result["closed_loop"] = loop_report
            self.status_update.emit("[ok] 5 个闭环验证器状态已读取", "success")
        except Exception as e:
            self.result["closed_loop"] = None

        try:
            stats = {}
            for json_file in (self.project_root / "data" / "deep_intent").glob("*.json"):
                try:
                    data = json.loads(json_file.read_text(encoding="utf-8"))
                    stats[json_file.stem] = self._summarize_json(data)
                except Exception:
                    pass
            self.result["persistence_stats"] = stats
        except Exception:
            self.result["persistence_stats"] = {}

        # ── P0: 读取项目记忆 ──
        try:
            pm_file = self.project_root / ".kimi-x" / "PROJECT.md"
            if pm_file.exists():
                self.result["project_memory"] = pm_file.read_text(encoding="utf-8")
                self.result["has_project_memory"] = True
                self.status_update.emit("[ok] 项目记忆已加载", "success")
            else:
                self.result["has_project_memory"] = False
        except Exception as e:
            self.result["has_project_memory"] = False
            self.logger.warning(f"Project memory read failed: {e}")

    def _resident_loop(self):
        """常驻守护循环：每 60 秒自动保存一次，CPU 占用几乎为零"""
        self.logger.info("Entering resident loop (auto-save every 60s)")
        save_counter = 0
        while self._running:
            time.sleep(5)
            save_counter += 5
            if save_counter >= 60:
                save_counter = 0
                try:
                    if self.core:
                        self.core.persist()
                        self.logger.debug("Auto-save completed")
                except Exception as e:
                    self.logger.debug(f"Auto-save failed: {e}")
        self.logger.info("Resident loop exited")

    @staticmethod
    def _summarize_json(data) -> dict:
        if isinstance(data, dict):
            return {k: len(v) if isinstance(v, (list, dict)) else type(v).__name__
                    for k, v in data.items()}
        elif isinstance(data, list):
            return {"count": len(data)}
        return {"type": type(data).__name__}
