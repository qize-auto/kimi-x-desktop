#!/usr/bin/env python3
"""
Kimi-X Desktop — 桌面快捷方式创建器
运行一次即可在桌面生成双击启动图标
"""
import sys
import os
from pathlib import Path

def create_desktop_shortcut():
    project_dir = Path(__file__).parent.resolve()
    main_py = project_dir / "main.py"

    if not main_py.exists():
        print(f"错误: 找不到 {main_py}")
        sys.exit(1)

    # 找到 pythonw.exe（无控制台窗口版本）
    python_exe = Path(sys.executable).resolve()
    pythonw = python_exe.parent / "pythonw.exe"
    if not pythonw.exists():
        print(f"错误: 找不到 pythonw.exe ({pythonw})")
        print("请使用 Python 3.x 的 pythonw.exe 来避免黑窗")
        sys.exit(1)

    # 桌面路径
    desktop = Path.home() / "Desktop"
    if not desktop.exists():
        desktop = Path.home() / "OneDrive" / "Desktop"
    if not desktop.exists():
        print("错误: 找不到桌面文件夹")
        sys.exit(1)

    shortcut_path = desktop / "Kimi-X Desktop.lnk"

    # 用 pywin32 创建快捷方式
    try:
        from win32com.client import Dispatch
    except ImportError:
        print("错误: 需要 pywin32 (pip install pywin32)")
        sys.exit(1)

    shell = Dispatch("WScript.Shell")
    shortcut = shell.CreateShortCut(str(shortcut_path))
    shortcut.TargetPath = str(pythonw)
    shortcut.Arguments = f'"{main_py}"'
    shortcut.WorkingDirectory = str(project_dir)
    shortcut.Description = "Kimi-X Desktop — DeepIntent v2.1 共生桌面壳"
    # WindowStyle: 7 = 最小化启动, 1 = 正常, 3 = 最大化
    shortcut.WindowStyle = 1
    shortcut.IconLocation = str(pythonw) + ",0"
    shortcut.Save()

    print(f"[OK] 快捷方式已创建: {shortcut_path}")
    print(f"     目标: {pythonw}")
    print(f"     参数: \"{main_py}\"")
    print(f"     工作目录: {project_dir}")
    print()
    print("双击桌面 [Kimi-X Desktop] 即可启动（无黑窗）")

    # 同时创建 launch.vbs 备用（更彻底的无黑窗方案）
    vbs_path = project_dir / "launch.vbs"
    vbs_content = (
        f'Set WshShell = CreateObject("WScript.Shell")\n'
        f'WshShell.Run "\"{pythonw}\" \"{main_py}\"" , 0, False\n'
        f'Set WshShell = Nothing\n'
    )
    vbs_path.write_text(vbs_content, encoding="utf-8")
    print(f"[OK] 备用启动器: {vbs_path}（完全隐藏窗口）")


if __name__ == "__main__":
    create_desktop_shortcut()
