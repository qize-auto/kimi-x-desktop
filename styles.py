"""
Kimi-X Desktop 深色主题样式
=======================
配色参考 GitHub Dark / VS Code Dark+
"""

# ── 颜色常量 ──
COLORS = {
    "bg_primary": "#0d1117",
    "bg_secondary": "#161b22",
    "bg_tertiary": "#21262d",
    "bg_hover": "#1f242c",
    "border": "#30363d",
    "border_light": "#484f58",
    "text_primary": "#c9d1d9",
    "text_secondary": "#8b949e",
    "text_muted": "#6e7681",
    "accent": "#58a6ff",
    "accent_hover": "#79c0ff",
    "success": "#3fb950",
    "warning": "#d29922",
    "danger": "#f85149",
    "info": "#58a6ff",
    "card_shadow": "rgba(0,0,0,0.4)",
}

MAIN_STYLE = """
/* ── 全局 ── */
QMainWindow {
    background-color: #0d1117;
    border: none;
}

QWidget {
    background-color: #0d1117;
    color: #c9d1d9;
    font-family: "Segoe UI", "Microsoft YaHei", sans-serif;
    font-size: 13px;
}

/* ── 滚动条 ── */
QScrollArea {
    border: none;
    background-color: #0d1117;
}

QScrollBar:vertical {
    background-color: #161b22;
    width: 8px;
    border-radius: 4px;
}
QScrollBar::handle:vertical {
    background-color: #30363d;
    border-radius: 4px;
    min-height: 30px;
}
QScrollBar::handle:vertical:hover {
    background-color: #484f58;
}
QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical {
    height: 0px;
}

/* ── 左侧边栏 ── */
#SidebarPanel {
    background-color: #161b22;
    border-right: 1px solid #30363d;
}

/* ── 卡片容器 ── */
#CardFrame {
    background-color: #21262d;
    border: 1px solid #30363d;
    border-radius: 8px;
}

/* ── 标题标签 ── */
#TitleLabel {
    color: #c9d1d9;
    font-size: 16px;
    font-weight: bold;
    padding: 4px 0;
}

#SubtitleLabel {
    color: #8b949e;
    font-size: 11px;
    padding: 2px 0;
}

/* ── 状态标签 ── */
#StatusLabel {
    color: #8b949e;
    font-size: 12px;
    padding: 3px 0;
}

#StatusValue {
    color: #c9d1d9;
    font-size: 12px;
    font-weight: 500;
    padding: 3px 0;
}

/* ── 健康指示器 ── */
#HealthIndicator {
    font-size: 13px;
    font-weight: bold;
    padding: 6px 10px;
    border-radius: 6px;
    background-color: #21262d;
    border: 1px solid #30363d;
}

/* ── 按钮 ── */
QPushButton {
    background-color: #21262d;
    color: #c9d1d9;
    border: 1px solid #30363d;
    border-radius: 6px;
    padding: 8px 14px;
    font-size: 12px;
    font-weight: 500;
}
QPushButton:hover {
    background-color: #30363d;
    border-color: #484f58;
}
QPushButton:pressed {
    background-color: #484f58;
}
QPushButton:disabled {
    background-color: #161b22;
    color: #6e7681;
    border-color: #21262d;
}

#PrimaryButton {
    background-color: #238636;
    color: #ffffff;
    border: 1px solid #238636;
}
#PrimaryButton:hover {
    background-color: #2ea043;
    border-color: #2ea043;
}
#PrimaryButton:pressed {
    background-color: #3fb950;
}

#AccentButton {
    background-color: #1f6feb;
    color: #ffffff;
    border: 1px solid #1f6feb;
}
#AccentButton:hover {
    background-color: #388bfd;
    border-color: #388bfd;
}

/* ── 分割线 ── */
#Divider {
    background-color: #30363d;
    max-height: 1px;
}

/* ── 分组框 ── */
QGroupBox {
    background-color: transparent;
    color: #8b949e;
    font-size: 11px;
    font-weight: bold;
    text-transform: uppercase;
    border: none;
    margin-top: 12px;
    padding-top: 8px;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 0px;
    padding: 0 4px 0 0;
}

/* ── 进度条 ── */
QProgressBar {
    background-color: #21262d;
    border: 1px solid #30363d;
    border-radius: 4px;
    height: 6px;
    text-align: center;
}
QProgressBar::chunk {
    background-color: #238636;
    border-radius: 4px;
}

/* ── Splitter ── */
QSplitter::handle {
    background-color: #30363d;
    width: 1px;
}
QSplitter::handle:hover {
    background-color: #58a6ff;
}

/* ── 工具提示 ── */
QToolTip {
    background-color: #21262d;
    color: #c9d1d9;
    border: 1px solid #30363d;
    border-radius: 6px;
    padding: 6px 10px;
    font-size: 12px;
}
"""
