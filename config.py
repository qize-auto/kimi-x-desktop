"""
Kimi-X Desktop 配置管理
========================
配置文件: ~/.kimi/kimi-x-config.json
换电脑时复制此文件即可保留全部设置
"""
from __future__ import annotations
import json
import os
from pathlib import Path
from typing import Any


CONFIG_PATH = Path.home() / ".kimi" / "kimi-x-config.json"

DEFAULT_CONFIG = {
    "version": "1.0",
    "project_root": str(Path.home() / "kimi-workspace" / "deep-intent"),
    "auto_start_kimi_web": True,
    "kimi_web_port": 5494,
    "theme": "dark",
    "hardware_profile": None,
    "deepintent_adjusted": False,
    "api_keys": {},
    "window_geometry": [80, 60, 1480, 900],
    "first_run": True,
    "last_migration_check": None,
}


class KimiXConfig:
    """集中配置管理器"""

    def __init__(self):
        self._data: dict = {}
        self.load()

    def load(self):
        if CONFIG_PATH.exists():
            try:
                self._data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
                # 合并新版本默认值
                for k, v in DEFAULT_CONFIG.items():
                    if k not in self._data:
                        self._data[k] = v
            except Exception:
                self._data = DEFAULT_CONFIG.copy()
        else:
            self._data = DEFAULT_CONFIG.copy()
            self.save()

    def save(self):
        CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        CONFIG_PATH.write_text(
            json.dumps(self._data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def get(self, key: str, default=None) -> Any:
        return self._data.get(key, default)

    def set(self, key: str, value: Any):
        self._data[key] = value
        self.save()

    @property
    def first_run(self) -> bool:
        return self._data.get("first_run", True)

    @first_run.setter
    def first_run(self, value: bool):
        self._data["first_run"] = value
        self.save()

    @property
    def project_root(self) -> Path:
        return Path(self._data.get("project_root", DEFAULT_CONFIG["project_root"]))

    @project_root.setter
    def project_root(self, value: Path | str):
        self._data["project_root"] = str(Path(value))
        self.save()

    @property
    def auto_start_kimi_web(self) -> bool:
        return self._data.get("auto_start_kimi_web", True)

    @auto_start_kimi_web.setter
    def auto_start_kimi_web(self, value: bool):
        self._data["auto_start_kimi_web"] = value
        self.save()

    @property
    def api_keys(self) -> dict:
        return self._data.get("api_keys", {})

    def set_api_key(self, name: str, key: str):
        self._data.setdefault("api_keys", {})[name] = key
        self.save()

    def get_api_key(self, name: str) -> str:
        return self._data.get("api_keys", {}).get(name, "")

    @property
    def window_geometry(self) -> list:
        return self._data.get("window_geometry", DEFAULT_CONFIG["window_geometry"])

    @window_geometry.setter
    def window_geometry(self, value: list):
        self._data["window_geometry"] = list(value)
        self.save()

    @property
    def hardware_profile(self) -> dict | None:
        return self._data.get("hardware_profile")

    @hardware_profile.setter
    def hardware_profile(self, value: dict):
        self._data["hardware_profile"] = dict(value)
        self.save()

    @property
    def deepintent_adjusted(self) -> bool:
        return self._data.get("deepintent_adjusted", False)

    @deepintent_adjusted.setter
    def deepintent_adjusted(self, value: bool):
        self._data["deepintent_adjusted"] = value
        self.save()

    def export_for_migration(self, target_path: str | Path):
        """导出配置用于换电脑迁移"""
        export_data = {
            "kimi_x_version": "2.1",
            "exported_at": __import__("time").strftime("%Y-%m-%d %H:%M:%S"),
            "config": self._data,
            "note": "将此文件复制到新电脑的 ~/.kimi/ 目录并重命名为 kimi-x-config.json",
        }
        target = Path(target_path)
        target.write_text(json.dumps(export_data, ensure_ascii=False, indent=2), encoding="utf-8")
        return target
