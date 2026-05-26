"""
硬件档案扫描器
==============
启动时自动检测系统配置，防止低配电脑卡死
"""
from __future__ import annotations
import sys
import os
import subprocess
from pathlib import Path
from typing import Dict, Any

from logger import get_logger, log_exception

logger = get_logger("HardwareProfiler")

try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False
    logger.warning("psutil not installed, hardware detection will be limited")


class HardwareProfile:
    """系统硬件档案"""

    def __init__(self):
        self.cpu_cores: int = 1
        self.cpu_threads: int = 1
        self.memory_gb: float = 8.0
        self.memory_available_gb: float = 4.0
        self.is_ssd: bool = True
        self.gpu_available: bool = False
        self.gpu_name: str = ""
        self.os_name: str = sys.platform
        self.profile_name: str = "unknown"
        self._scan()

    def _scan(self):
        """扫描系统硬件"""
        # CPU
        if HAS_PSUTIL:
            self.cpu_cores = psutil.cpu_count(logical=False) or 1
            self.cpu_threads = psutil.cpu_count(logical=True) or 1
        else:
            self.cpu_cores = os.cpu_count() or 1
            self.cpu_threads = self.cpu_cores

        # 内存
        if HAS_PSUTIL:
            mem = psutil.virtual_memory()
            self.memory_gb = round(mem.total / (1024 ** 3), 1)
            self.memory_available_gb = round(mem.available / (1024 ** 3), 1)
        else:
            self.memory_gb = 8.0
            self.memory_available_gb = 4.0

        # 磁盘
        self.is_ssd = self._detect_ssd()

        # GPU
        self.gpu_available, self.gpu_name = self._detect_gpu()

        # 分级
        self.profile_name = self._classify()
        logger.info(
            f"Hardware: {self.cpu_cores}C/{self.cpu_threads}T, "
            f"{self.memory_gb:.1f}GB RAM, SSD={self.is_ssd}, "
            f"GPU={self.gpu_available}, Profile={self.profile_name}"
        )

    def _detect_ssd(self) -> bool:
        """检测系统盘是否为 SSD"""
        try:
            if sys.platform == "win32":
                # Windows: 使用 fsutil 检测
                result = subprocess.run(
                    ["fsutil", "behavior", "query", "DisableDeleteNotify"],
                    capture_output=True, text=True, timeout=5,
                    creationflags=subprocess.CREATE_NO_WINDOW,
                )
                # 0 表示 TRIM 启用，通常是 SSD
                return "0" in result.stdout
            elif sys.platform == "linux":
                # Linux: 检查 rotational
                sys_disk = "/sys/block/sda/queue/rotational"
                if Path(sys_disk).exists():
                    return Path(sys_disk).read_text().strip() == "0"
            elif sys.platform == "darwin":
                # macOS: 假设现代 Mac 都是 SSD
                return True
        except Exception as e:
            logger.debug(f"SSD detection failed: {e}")
        return True  # 默认假设 SSD

    def _detect_gpu(self) -> tuple[bool, str]:
        """检测是否有独立/集成显卡"""
        try:
            if sys.platform == "win32":
                result = subprocess.run(
                    ["wmic", "path", "win32_VideoController", "get", "name"],
                    capture_output=True, text=True, timeout=5,
                    creationflags=subprocess.CREATE_NO_WINDOW,
                )
                lines = [l.strip() for l in result.stdout.splitlines() if l.strip() and l.strip() != "Name"]
                if lines:
                    gpu = lines[0]
                    has_gpu = any(v in gpu for v in ["NVIDIA", "AMD", "Intel"])
                    return has_gpu, gpu
            elif sys.platform == "linux":
                result = subprocess.run(
                    ["lspci"], capture_output=True, text=True, timeout=5
                )
                if "VGA" in result.stdout or "3D" in result.stdout:
                    return True, "Linux GPU"
        except Exception as e:
            logger.debug(f"GPU detection failed: {e}")
        return False, ""

    def _classify(self) -> str:
        """根据硬件分级"""
        if self.cpu_threads <= 2 or self.memory_gb < 4:
            return "low"          # 双核或 4GB 以下
        elif self.cpu_threads <= 4 or self.memory_gb < 8:
            return "medium"       # 四核或 8GB 以下
        else:
            return "high"         # 八核+ 16GB+

    def to_dict(self) -> dict:
        return {
            "cpu_cores": self.cpu_cores,
            "cpu_threads": self.cpu_threads,
            "memory_gb": self.memory_gb,
            "memory_available_gb": self.memory_available_gb,
            "is_ssd": self.is_ssd,
            "gpu_available": self.gpu_available,
            "gpu_name": self.gpu_name,
            "os_name": self.os_name,
            "profile_name": self.profile_name,
        }

    def get_deepintent_params(self) -> dict:
        """根据硬件档案返回 DeepIntent 调整参数"""
        profiles = {
            "low": {
                "METHOD_TIMEOUT_SECONDS": 1.0,
                "MAX_INPUT_LENGTH": 2000,
                "MAX_PENDING_MEMORIES": 500,
                "MAX_USERS": 1000,
                "MAX_TURNS_PER_SESSION": 20,
                "check_interval": 2.0,
                "disable_gpu": True,
                "disable_animations": True,
                "webview_cache_mb": 50,
            },
            "medium": {
                "METHOD_TIMEOUT_SECONDS": 2.0,
                "MAX_INPUT_LENGTH": 5000,
                "MAX_PENDING_MEMORIES": 1000,
                "MAX_USERS": 3000,
                "MAX_TURNS_PER_SESSION": 35,
                "check_interval": 1.5,
                "disable_gpu": False,
                "disable_animations": False,
                "webview_cache_mb": 100,
            },
            "high": {
                "METHOD_TIMEOUT_SECONDS": 3.0,
                "MAX_INPUT_LENGTH": 8000,
                "MAX_PENDING_MEMORIES": 2000,
                "MAX_USERS": 5000,
                "MAX_TURNS_PER_SESSION": 50,
                "check_interval": 1.0,
                "disable_gpu": False,
                "disable_animations": False,
                "webview_cache_mb": 200,
            },
        }
        return profiles.get(self.profile_name, profiles["medium"])

    def get_pyqt_flags(self) -> list[str]:
        """返回 PyQt/WebEngine 启动参数（低配禁用 GPU）"""
        params = self.get_deepintent_params()
        flags = []
        if params["disable_gpu"]:
            flags.extend([
                "--disable-gpu",
                "--disable-gpu-compositing",
            ])
        return flags

    def get_warning(self) -> str | None:
        """如果硬件过低，返回警告信息"""
        warnings = []
        if self.cpu_threads <= 2:
            warnings.append(f"CPU 仅 {self.cpu_threads} 线程，已降低计算强度")
        if self.memory_gb < 4:
            warnings.append(f"内存仅 {self.memory_gb:.1f}GB，已降低缓存上限")
        if not self.is_ssd:
            warnings.append("检测到机械硬盘，IO 密集型操作已限制")
        return "；".join(warnings) if warnings else None
