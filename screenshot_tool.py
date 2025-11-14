import ctypes
from ctypes import wintypes
import json
import os
import sys
from datetime import datetime
from enum import Enum, auto

from PyQt5.QtCore import QPoint, QRect, Qt, pyqtSignal, QTimer, QUrl, QSize
from PyQt5.QtGui import QColor, QGuiApplication, QPainter, QPen, QPixmap, QFont, QIcon, QDesktopServices
from PyQt5.QtWidgets import (
    QAction,
    QApplication,
    QFileDialog,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QTabWidget,
    QStackedWidget,
    QToolBar,
    QVBoxLayout,
    QWidget,
    QDialog,
    QHBoxLayout,
    QFrame,
    QSizePolicy,
)


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(BASE_DIR, "config.json")
DEFAULT_SAVE_DIR = os.path.join(BASE_DIR, "screenshots")
ICON_PATH = os.path.join(BASE_DIR, "favicon", "favicon.ico")
_APP_ICON = None


def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r", encoding="utf-8") as handle:
            try:
                return json.load(handle)
            except json.JSONDecodeError:
                return {}
    return {}


def save_config(data):
    with open(CONFIG_FILE, "w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2, ensure_ascii=False)


class Tool(Enum):
    NONE = auto()
    RECTANGLE = auto()
    MARKER = auto()

MODIFIER_ORDER = [
    (Qt.ControlModifier, "Ctrl"),
    (Qt.ShiftModifier, "Shift"),
    (Qt.AltModifier, "Alt"),
    (Qt.MetaModifier, "Win"),
]
MODIFIER_NAME_SET = {name for _, name in MODIFIER_ORDER}
SPECIAL_KEY_DISPLAY = {
    Qt.Key_Escape: "Esc",
    Qt.Key_Tab: "Tab",
    Qt.Key_Backspace: "Backspace",
    Qt.Key_Return: "Enter",
    Qt.Key_Enter: "Enter",
    Qt.Key_Insert: "Insert",
    Qt.Key_Delete: "Delete",
    Qt.Key_Home: "Home",
    Qt.Key_End: "End",
    Qt.Key_PageUp: "PageUp",
    Qt.Key_PageDown: "PageDown",
    Qt.Key_Left: "Left",
    Qt.Key_Right: "Right",
    Qt.Key_Up: "Up",
    Qt.Key_Down: "Down",
    Qt.Key_Space: "Space",
    Qt.Key_Print: "PrintScreen",
    Qt.Key_Plus: "+",
    Qt.Key_Minus: "-",
    Qt.Key_Slash: "/",
    Qt.Key_Backslash: "\\",
    Qt.Key_Comma: ",",
    Qt.Key_Period: ".",
    Qt.Key_Semicolon: ";",
    Qt.Key_Equal: "=",
    Qt.Key_BracketLeft: "[",
    Qt.Key_BracketRight: "]",
}
DISPLAY_NAME_OVERRIDES = {
    "ctrl": "Ctrl",
    "shift": "Shift",
    "alt": "Alt",
    "win": "Win",
    "meta": "Meta",
    "esc": "Esc",
    "tab": "Tab",
    "enter": "Enter",
    "delete": "Delete",
    "insert": "Insert",
    "home": "Home",
    "end": "End",
    "pageup": "PageUp",
    "pagedown": "PageDown",
    "left": "Left",
    "right": "Right",
    "up": "Up",
    "down": "Down",
    "space": "Space",
    "printscreen": "PrintScreen",
    "print": "PrintScreen",
    "+": "+",
    "-": "-",
    "/": "/",
    "\\": "\\",
    ",": ",",
    ".": ".",
    ";": ";",
    "=": "=",
    "[": "[",
    "]": "]",
}

HOTKEY_ACTIONS = [
    ("capture", "区域截图"),
    ("repeat_capture", "重复截图"),
]

WM_HOTKEY = 0x0312
MODIFIER_BITMASK = {
    "alt": 0x0001,
    "ctrl": 0x0002,
    "shift": 0x0004,
    "win": 0x0008,
}
VIRTUAL_KEY_MAP = {
    "esc": 0x1B,
    "tab": 0x09,
    "enter": 0x0D,
    "return": 0x0D,
    "space": 0x20,
    "backspace": 0x08,
    "insert": 0x2D,
    "delete": 0x2E,
    "home": 0x24,
    "end": 0x23,
    "pageup": 0x21,
    "pagedown": 0x22,
    "left": 0x25,
    "up": 0x26,
    "right": 0x27,
    "down": 0x28,
    "printscreen": 0x2C,
    "pause": 0x13,
    "capslock": 0x14,
    ";": 0xBA,
    ":": 0xBA,
    "=": 0xBB,
    "+": 0xBB,
    ",": 0xBC,
    "<": 0xBC,
    "-": 0xBD,
    "_": 0xBD,
    ".": 0xBE,
    ">": 0xBE,
    "/": 0xBF,
    "?": 0xBF,
    "`": 0xC0,
    "~": 0xC0,
    "[": 0xDB,
    "{": 0xDB,
    "]": 0xDD,
    "}": 0xDD,
    "\\": 0xDC,
    "|": 0xDC,
}


def _key_name_to_vk(name: str):
    if not name:
        return None
    name = name.lower()
    if name in VIRTUAL_KEY_MAP:
        return VIRTUAL_KEY_MAP[name]
    if name.startswith("f") and name[1:].isdigit():
        idx = int(name[1:])
        if 1 <= idx <= 24:
            return 0x70 + (idx - 1)
    if len(name) == 1:
        char = name.upper()
        if "A" <= char <= "Z" or "0" <= char <= "9":
            return ord(char)
    return None


def _shortcut_to_native(shortcut: str):
    if not shortcut:
        return None
    parts = [part.strip() for part in shortcut.split("+") if part.strip()]
    if not parts:
        return None
    modifiers = 0
    key_name = None
    for part in parts:
        lower = part.lower()
        if lower in MODIFIER_BITMASK:
            modifiers |= MODIFIER_BITMASK[lower]
        else:
            key_name = lower
    if not key_name:
        return None
    vk = _key_name_to_vk(key_name)
    if vk is None:
        return None
    return modifiers, vk


class GlobalHotkeyManager:
    def __init__(self, window):
        self._window = window
        self._user32 = ctypes.windll.user32
        self._next_id = 1
        self._action_to_id = {}
        self._id_to_action = {}

    def register(self, action_id, shortcut):
        self.unregister(action_id)
        native = _shortcut_to_native(shortcut)
        if not native:
            raise ValueError(f"无法识别快捷键: {shortcut}")
        modifiers, vk = native
        hotkey_id = self._next_id
        self._next_id += 1
        hwnd = int(self._window.winId())
        if not self._user32.RegisterHotKey(hwnd, hotkey_id, modifiers, vk):
            raise ctypes.WinError()
        self._action_to_id[action_id] = hotkey_id
        self._id_to_action[hotkey_id] = action_id

    def unregister(self, action_id):
        hotkey_id = self._action_to_id.pop(action_id, None)
        if hotkey_id is not None:
            self._user32.UnregisterHotKey(int(self._window.winId()), hotkey_id)
            self._id_to_action.pop(hotkey_id, None)

    def unregister_all(self):
        for action_id in list(self._action_to_id.keys()):
            self.unregister(action_id)

    def handle_message(self, hotkey_id):
        action_id = self._id_to_action.get(hotkey_id)
        if action_id:
            self._window._on_hotkey_trigger(action_id)


def get_app_icon():
    global _APP_ICON
    if _APP_ICON is None:
        if os.path.exists(ICON_PATH):
            _APP_ICON = QIcon(ICON_PATH)
        else:  # pragma: no cover - fallback branch
            _APP_ICON = QIcon()
    return _APP_ICON


def _modifier_names(modifiers):
    return [name for mask, name in MODIFIER_ORDER if modifiers & mask]


def _base_key_name(key):
    if Qt.Key_F1 <= key <= Qt.Key_F35:
        return f"F{key - Qt.Key_F1 + 1}"
    if Qt.Key_A <= key <= Qt.Key_Z:
        return chr(key)
    if Qt.Key_0 <= key <= Qt.Key_9:
        return chr(key)
    return SPECIAL_KEY_DISPLAY.get(key)


def _normalize_part(part):
    return (part or "").lower()


def _format_display_shortcut(normalized):
    if not normalized:
        return "未设置全局热键"
    parts = [part for part in normalized.split("+") if part]
    friendly = []
    for part in parts:
        friendly.append(DISPLAY_NAME_OVERRIDES.get(part, part.upper()))
    return "+".join(friendly)


class ShortcutRecorder(QLineEdit):
    shortcutRecorded = pyqtSignal(str, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setReadOnly(True)
        self.recording = False
        self.setPlaceholderText("按组合键录入快捷键")

    def start_recording(self):
        self.recording = True
        self.setText("正在录制，按下组合键...")
        self.grabKeyboard()
        self.setFocus(Qt.OtherFocusReason)

    def stop_recording(self):
        if self.recording:
            self.releaseKeyboard()
        self.recording = False

    def keyPressEvent(self, event):
        if not self.recording:
            super().keyPressEvent(event)
            return
        if event.key() == Qt.Key_Escape:
            self.setText("")
            self.stop_recording()
            return
        parts = _modifier_names(event.modifiers())
        key_name = _base_key_name(event.key())
        if not key_name:
            return
        if key_name not in MODIFIER_NAME_SET:
            parts.append(key_name)
        if not parts:
            return
        display_value = "+".join(parts)
        normalized = "+".join(_normalize_part(part) for part in parts)
        self.setText(display_value)
        self.shortcutRecorded.emit(display_value, normalized)
        self.stop_recording()


class ShortcutDialog(QDialog):
    shortcutSet = pyqtSignal(str, str)

    def __init__(self, parent=None, current_display=""):
        super().__init__(parent)
        self.setWindowTitle("设置全局截屏热键")
        self.setWindowIcon(get_app_icon())
        self._display_value = current_display
        self._normalized_value = ""

        self.recorder = ShortcutRecorder()
        self.recorder.shortcutRecorded.connect(self._on_recorded)

        instruction_text = "按住希望的快捷键组合，然后松开。"
        if current_display:
            instruction_text += f"\n当前热键: {current_display}"
        instruction = QLabel(instruction_text)
        self._retry_btn = QPushButton("重新录制")
        self._confirm_btn = QPushButton("确认")
        self._confirm_btn.setEnabled(False)
        cancel_btn = QPushButton("取消")

        self._retry_btn.clicked.connect(self._start_recording)
        self._confirm_btn.clicked.connect(self._on_confirm)
        cancel_btn.clicked.connect(self.reject)

        buttons = QHBoxLayout()
        buttons.addWidget(self._retry_btn)
        buttons.addWidget(self._confirm_btn)
        buttons.addWidget(cancel_btn)

        layout = QVBoxLayout()
        layout.addWidget(instruction)
        layout.addWidget(self.recorder)
        layout.addLayout(buttons)
        self.setLayout(layout)

        self._start_recording()

    def _start_recording(self):
        self._confirm_btn.setEnabled(False)
        self.recorder.start_recording()

    def _on_recorded(self, display, normalized):
        self._display_value = display
        self._normalized_value = normalized
        self._confirm_btn.setEnabled(True)

    def _on_confirm(self):
        if self._normalized_value:
            self.shortcutSet.emit(self._display_value, self._normalized_value)
            self.accept()


class GeneralSettingsPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout()
        title = QLabel("控制中心")
        title.setStyleSheet("font-size: 20px; font-weight: 600;")
        subtitle = QLabel("集中管理保存路径、快捷键以及未来的更多功能。")
        subtitle.setStyleSheet("color: #666666;")
        subtitle.setWordWrap(True)

        layout.addWidget(title)
        layout.addWidget(subtitle)

        roadmap = QLabel(
            "即将支持：\n"
            "• 多场景截图模式（窗口截图、滚动截图等）\n"
            "• 云端同步与团队共享\n"
            "• 高级标注与模板库\n"
            "• 自动化脚本与批量导出"
        )
        roadmap.setStyleSheet("line-height: 24px; color: #444444;")
        roadmap.setWordWrap(True)

        layout.addSpacing(20)
        layout.addWidget(roadmap)
        layout.addStretch()
        self.setLayout(layout)


class HotkeySettingsPage(QWidget):
    def __init__(self, hotkeys, parent=None):
        super().__init__(parent)
        self._working_hotkeys = {k: dict(v) for k, v in hotkeys.items()}
        layout = QVBoxLayout()

        header = QLabel("为不同操作设置全局快捷键")
        header.setStyleSheet("font-size: 18px; font-weight: 600;")
        layout.addWidget(header)
        desc = QLabel("设置后可以在任意窗口通过快捷键触发截图动作。您可以随时进行调整或清除。")
        desc.setWordWrap(True)
        layout.addWidget(desc)

        self._rows = {}
        for action_id, action_name in HOTKEY_ACTIONS:
            row_frame = QFrame()
            row_frame.setFrameShape(QFrame.StyledPanel)
            row_frame.setStyleSheet("QFrame { background: #fafafa; border: 1px solid #e5e5e5; border-radius: 6px; }")
            row_layout = QHBoxLayout(row_frame)
            label = QLabel(action_name)
            label.setStyleSheet("font-weight: 600;")
            shortcut_label = QLabel(self._format_hotkey_text(action_id))
            shortcut_label.setWordWrap(True)
            shortcut_label.setStyleSheet("color: #333333;")
            row_layout.addWidget(label)
            row_layout.addWidget(shortcut_label, 1)

            button_box = QHBoxLayout()
            set_btn = QPushButton("设置快捷键")
            clear_btn = QPushButton("清除")
            set_btn.clicked.connect(lambda _, act=action_id: self._open_shortcut_dialog(act))
            clear_btn.clicked.connect(lambda _, act=action_id: self._clear_hotkey(act))
            button_box.addWidget(set_btn)
            button_box.addWidget(clear_btn)
            row_layout.addLayout(button_box)

            layout.addWidget(row_frame)
            self._rows[action_id] = (shortcut_label, set_btn, clear_btn)

        self._status_label = QLabel()
        self._status_label.setWordWrap(True)
        self._status_label.setStyleSheet("color: #666666;")
        layout.addSpacing(10)
        layout.addWidget(self._status_label)
        layout.addStretch()
        self.setLayout(layout)
        self._refresh_rows()

    def _format_hotkey_text(self, action_id):
        hotkey = self._working_hotkeys.get(action_id, {})
        display = hotkey.get("display")
        shortcut = hotkey.get("shortcut")
        if display:
            return display
        if shortcut:
            return _format_display_shortcut(shortcut)
        return "未设置"

    def _refresh_rows(self):
        for action_id, (label, set_btn, clear_btn) in self._rows.items():
            label.setText(self._format_hotkey_text(action_id))
            has_hotkey = bool(self._working_hotkeys.get(action_id, {}).get("shortcut"))
            set_btn.setEnabled(True)
            clear_btn.setEnabled(has_hotkey)
        status_text = "快捷键依赖系统级注册，保存设置后立即生效。若注册失败会弹出提示，请更换组合或检查权限。"
        self._status_label.setText(status_text)

    def _open_shortcut_dialog(self, action_id):
        dialog = ShortcutDialog(self, current_display=self._format_hotkey_text(action_id))
        dialog.shortcutSet.connect(lambda display, normalized, act=action_id: self._apply_hotkey(act, display, normalized))
        dialog.exec_()

    def _apply_hotkey(self, action_id, display, normalized):
        self._working_hotkeys[action_id] = {"display": display, "shortcut": normalized}
        self._refresh_rows()

    def _clear_hotkey(self, action_id):
        if action_id in self._working_hotkeys:
            self._working_hotkeys.pop(action_id)
            self._refresh_rows()

    def get_hotkeys(self):
        return {k: v for k, v in self._working_hotkeys.items() if v.get("shortcut")}


class SettingsDialog(QDialog):
    def __init__(self, parent, config):
        super().__init__(parent)
        self.setWindowTitle("系统设置")
        self.setWindowIcon(get_app_icon())
        self.resize(880, 560)
        self._hotkey_result = config.get("hotkeys", {}).copy()
        layout = QVBoxLayout()

        header = QLabel("配置中心")
        header.setStyleSheet("font-size: 22px; font-weight: 600;")
        layout.addWidget(header)

        content_layout = QHBoxLayout()
        self.nav_list = QListWidget()
        self.nav_list.addItem("常规")
        self.nav_list.addItem("快捷键")
        self.nav_list.setFixedWidth(150)
        self.nav_list.setStyleSheet(
            "QListWidget { border: 1px solid #e0e0e0; } QListWidget::item { padding: 10px; } "
            "QListWidget::item:selected { background: #eef4ff; }"
        )
        content_layout.addWidget(self.nav_list)

        separator = QFrame()
        separator.setFrameShape(QFrame.VLine)
        separator.setFrameShadow(QFrame.Sunken)
        content_layout.addWidget(separator)

        self.stack = QStackedWidget()
        self.general_page = GeneralSettingsPage()
        self.hotkey_page = HotkeySettingsPage(config.get("hotkeys", {}))
        self.stack.addWidget(self.general_page)
        self.stack.addWidget(self.hotkey_page)
        content_layout.addWidget(self.stack, 1)

        layout.addLayout(content_layout)

        button_box = QHBoxLayout()
        button_box.addStretch()
        cancel_btn = QPushButton("取消")
        save_btn = QPushButton("保存设置")
        cancel_btn.clicked.connect(self.reject)
        save_btn.clicked.connect(self.accept)
        button_box.addWidget(cancel_btn)
        button_box.addWidget(save_btn)

        layout.addLayout(button_box)
        self.setLayout(layout)

        self.nav_list.currentRowChanged.connect(self.stack.setCurrentIndex)
        self.nav_list.setCurrentRow(0)

    def accept(self):
        self._hotkey_result = self.hotkey_page.get_hotkeys()
        super().accept()

    def get_hotkeys(self):
        return self._hotkey_result


class ActionButton(QPushButton):
    def __init__(self, title, subtitle="", callback=None, enabled=True):
        super().__init__()
        self.setCursor(Qt.PointingHandCursor)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setMinimumHeight(70)
        self.setText(f"{title}\n{subtitle}" if subtitle else title)
        self.setEnabled(enabled)
        self.setStyleSheet(
            "QPushButton { text-align: left; padding: 12px 16px; border: 1px solid #dfe3eb; border-radius: 8px; "
            "background: #ffffff; font-size: 14px; }"
            "QPushButton:hover { background: #f5f7fb; border-color: #a8c3ff; }"
            "QPushButton:disabled { color: #999999; border-style: dashed; }"
        )
        if callback:
            self.clicked.connect(callback)


class HomePage(QWidget):
    changeFolderRequested = pyqtSignal()
    openFolderRequested = pyqtSignal()
    captureRequested = pyqtSignal()
    repeatRequested = pyqtSignal()
    openSettingsRequested = pyqtSignal()
    openWorkspaceRequested = pyqtSignal()

    def __init__(self, save_dir):
        super().__init__()
        self._save_dir = save_dir
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout()
        title = QLabel("选择操作…")
        title.setStyleSheet("font-size: 24px; font-weight: 700; margin-bottom: 8px;")
        layout.addWidget(title)

        folder_frame = QFrame()
        folder_frame.setFrameShape(QFrame.StyledPanel)
        folder_frame.setStyleSheet("QFrame { background: #f4f6fb; border-radius: 10px; }")
        folder_layout = QHBoxLayout(folder_frame)
        info = QLabel("保存文件夹")
        info.setStyleSheet("font-weight: 600;")
        folder_layout.addWidget(info)
        self.path_display = QLineEdit(self._save_dir)
        self.path_display.setReadOnly(True)
        folder_layout.addWidget(self.path_display, 1)
        choose_btn = QPushButton("选择路径")
        choose_btn.clicked.connect(self.changeFolderRequested.emit)
        folder_layout.addWidget(choose_btn)
        open_btn = QPushButton("打开目录")
        open_btn.clicked.connect(self.openFolderRequested.emit)
        folder_layout.addWidget(open_btn)
        layout.addWidget(folder_frame)

        content_layout = QHBoxLayout()

        new_task_layout = QVBoxLayout()
        new_task_label = QLabel("新任务")
        new_task_label.setStyleSheet("font-size: 18px; font-weight: 600;")
        new_task_layout.addWidget(new_task_label)
        new_task_layout.addWidget(ActionButton("新建", "创建空白图像 (规划中)", enabled=False))
        new_task_layout.addWidget(ActionButton("打开", "打开已有文件 (规划中)", enabled=False))
        new_task_layout.addStretch()
        content_layout.addLayout(new_task_layout, 1)

        capture_layout = QVBoxLayout()
        capture_label = QLabel("截取屏幕")
        capture_label.setStyleSheet("font-size: 18px; font-weight: 600;")
        capture_layout.addWidget(capture_label)
        capture_layout.addWidget(ActionButton("区域截图", "选择屏幕区域", self.captureRequested.emit))
        self.repeat_button = ActionButton("重复上次截取", "使用上一次选择的矩形区域", self.repeatRequested.emit, enabled=False)
        capture_layout.addWidget(self.repeat_button)
        capture_layout.addWidget(ActionButton("全屏截取", "敬请期待", enabled=False))
        capture_layout.addWidget(ActionButton("窗口截取", "敬请期待", enabled=False))
        capture_layout.addWidget(ActionButton("滚动截取", "敬请期待", enabled=False))
        capture_layout.addStretch()
        content_layout.addLayout(capture_layout, 1)

        tools_layout = QVBoxLayout()
        tools_label = QLabel("实用工具")
        tools_label.setStyleSheet("font-size: 18px; font-weight: 600;")
        tools_layout.addWidget(tools_label)
        tools_layout.addWidget(ActionButton("系统设置", "热键、自定义流程", self.openSettingsRequested.emit))
        tools_layout.addWidget(ActionButton("标注工作台", "查看历史截图并继续标注", self.openWorkspaceRequested.emit))
        self.hotkey_summary_label = QLabel()
        self.hotkey_summary_label.setWordWrap(True)
        self.hotkey_summary_label.setStyleSheet("color: #5f6b7c; font-size: 12px;")
        tools_layout.addWidget(self.hotkey_summary_label)
        tools_layout.addWidget(ActionButton("颜色拾取器", "敬请期待", enabled=False))
        tools_layout.addWidget(ActionButton("放大镜", "敬请期待", enabled=False))
        tools_layout.addWidget(ActionButton("量角器", "敬请期待", enabled=False))
        tools_layout.addStretch()
        content_layout.addLayout(tools_layout, 1)

        layout.addLayout(content_layout)
        layout.addStretch()
        self.setLayout(layout)

    def set_save_dir(self, path):
        self._save_dir = path
        self.path_display.setText(path)

    def set_repeat_enabled(self, enabled):
        self.repeat_button.setEnabled(enabled)

    def set_hotkey_summary(self, text):
        self.hotkey_summary_label.setText(text)


class ComingSoonPage(QWidget):
    def __init__(self, title):
        super().__init__()
        layout = QVBoxLayout()
        label = QLabel(f"{title}\n\n该功能即将上线，敬请期待。")
        label.setAlignment(Qt.AlignCenter)
        label.setStyleSheet("font-size: 18px; color: #5f6b7c;")
        layout.addStretch()
        layout.addWidget(label)
        layout.addStretch()
        self.setLayout(layout)


class AnnotationCanvas(QWidget):
    def __init__(self, pixmap: QPixmap):
        super().__init__()
        self.base_pixmap = pixmap
        self.setFixedSize(self.base_pixmap.size())
        self.rectangles = []
        self.markers = []
        self.temp_rect = None
        self.tool = Tool.NONE
        self.marker_count = 0

    def set_tool(self, tool: Tool):
        self.tool = tool
        self.temp_rect = None
        self.setCursor(Qt.CrossCursor if tool != Tool.NONE else Qt.ArrowCursor)

    def clear_annotations(self):
        self.rectangles.clear()
        self.markers.clear()
        self.marker_count = 0
        self.temp_rect = None
        self.update()

    def mousePressEvent(self, event):
        if event.button() != Qt.LeftButton:
            return
        if self.tool == Tool.RECTANGLE:
            self.temp_rect = QRect(event.pos(), event.pos())
        elif self.tool == Tool.MARKER:
            self.marker_count += 1
            self.markers.append((event.pos(), self.marker_count))
            self.update()

    def mouseMoveEvent(self, event):
        if self.tool == Tool.RECTANGLE and self.temp_rect is not None:
            self.temp_rect.setBottomRight(event.pos())
            self.update()

    def mouseReleaseEvent(self, event):
        if event.button() != Qt.LeftButton:
            return
        if self.tool == Tool.RECTANGLE and self.temp_rect is not None:
            rect = self.temp_rect.normalized()
            if rect.width() > 3 and rect.height() > 3:
                self.rectangles.append(rect)
            self.temp_rect = None
            self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.drawPixmap(0, 0, self.base_pixmap)

        painter.setRenderHint(QPainter.Antialiasing)
        pen = QPen(QColor(255, 215, 0), 3)
        painter.setPen(pen)
        for rect in self.rectangles:
            painter.drawRect(rect)

        if self.temp_rect is not None:
            painter.setPen(QPen(QColor(135, 206, 250), 2, Qt.DashLine))
            painter.drawRect(self.temp_rect.normalized())

        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(220, 20, 60, 220))
        font = QFont()
        font.setBold(True)
        painter.setFont(font)
        for point, number in self.markers:
            radius = 14
            ellipse_rect = QRect(point.x() - radius, point.y() - radius, radius * 2, radius * 2)
            painter.drawEllipse(ellipse_rect)
            painter.setPen(Qt.white)
            painter.drawText(ellipse_rect, Qt.AlignCenter, str(number))
            painter.setPen(Qt.NoPen)

    def export_pixmap(self):
        annotated = QPixmap(self.base_pixmap.size())
        annotated.fill(Qt.transparent)
        painter = QPainter(annotated)
        painter.drawPixmap(0, 0, self.base_pixmap)

        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(QPen(QColor(255, 215, 0), 3))
        for rect in self.rectangles:
            painter.drawRect(rect)

        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(220, 20, 60, 220))
        font = QFont()
        font.setBold(True)
        painter.setFont(font)
        for point, number in self.markers:
            radius = 14
            ellipse_rect = QRect(point.x() - radius, point.y() - radius, radius * 2, radius * 2)
            painter.drawEllipse(ellipse_rect)
            painter.setPen(Qt.white)
            painter.drawText(ellipse_rect, Qt.AlignCenter, str(number))
            painter.setPen(Qt.NoPen)

        painter.end()
        return annotated


class AnnotationTab(QWidget):
    def __init__(self, pixmap: QPixmap, save_dir: str):
        super().__init__()
        self.canvas = AnnotationCanvas(pixmap)
        self.save_dir = save_dir
        self.auto_saved_path = self._auto_save_pixmap(pixmap)
        layout = QVBoxLayout()

        toolbar = QToolBar("工具")
        toolbar.setIconSize(QSize(20, 20))
        rect_action = QAction("标注框", self)
        rect_action.triggered.connect(lambda: self.canvas.set_tool(Tool.RECTANGLE))
        toolbar.addAction(rect_action)

        marker_action = QAction("顺序标记", self)
        marker_action.triggered.connect(lambda: self.canvas.set_tool(Tool.MARKER))
        toolbar.addAction(marker_action)

        clear_action = QAction("清除标注", self)
        clear_action.triggered.connect(self.canvas.clear_annotations)
        toolbar.addAction(clear_action)

        save_action = QAction("保存标注图", self)
        save_action.triggered.connect(self.save_annotated_image)
        toolbar.addAction(save_action)

        layout.addWidget(toolbar)

        scroll = QScrollArea()
        scroll.setWidget(self.canvas)
        layout.addWidget(scroll, 1)

        self.status_label = QLabel(f"自动保存: {self.auto_saved_path}")
        layout.addWidget(self.status_label)
        self.setLayout(layout)

    def _auto_save_pixmap(self, pixmap: QPixmap):
        os.makedirs(self.save_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"screenshot_{timestamp}.png"
        path = os.path.join(self.save_dir, filename)
        pixmap.save(path, "PNG")
        return path

    def save_annotated_image(self):
        annotated = self.canvas.export_pixmap()
        base, ext = os.path.splitext(os.path.basename(self.auto_saved_path))
        annotated_path = os.path.join(self.save_dir, f"{base}_annotated{ext}")
        if annotated.save(annotated_path, "PNG"):
            self.status_label.setText(f"标注图已保存: {annotated_path}")
        else:
            QMessageBox.warning(self, "保存失败", "无法写入标注截图，请检查保存路径。")


class AnnotationWorkspacePage(QWidget):
    def __init__(self, open_settings_callback):
        super().__init__()
        self._open_settings_callback = open_settings_callback
        layout = QVBoxLayout()

        toolbar = QToolBar()
        toolbar.setIconSize(QSize(18, 18))
        settings_action = QAction("系统设置", self)
        settings_action.triggered.connect(self._open_settings_callback)
        toolbar.addAction(settings_action)
        layout.addWidget(toolbar)

        self.tabs = QTabWidget()
        self.tabs.setTabsClosable(True)
        self.tabs.tabCloseRequested.connect(self._close_tab)
        layout.addWidget(self.tabs, 1)

        hint = QLabel("尚未添加截图，使用区域截取或重复截取后会在此显示。")
        hint.setAlignment(Qt.AlignCenter)
        hint.setStyleSheet("color: #777777;")
        self._empty_hint = hint
        layout.addWidget(hint)
        self.setLayout(layout)

        self._update_hint_visibility()

    def _update_hint_visibility(self):
        has_tabs = self.tabs.count() > 0
        self._empty_hint.setVisible(not has_tabs)
        self.tabs.setVisible(has_tabs)

    def add_capture(self, pixmap: QPixmap, save_dir: str):
        tab = AnnotationTab(pixmap, save_dir)
        label = os.path.basename(tab.auto_saved_path)
        self.tabs.addTab(tab, label)
        self.tabs.setCurrentWidget(tab)
        self._update_hint_visibility()

    def _close_tab(self, index):
        widget = self.tabs.widget(index)
        if widget:
            widget.deleteLater()
        self.tabs.removeTab(index)
        self._update_hint_visibility()


class CaptureOverlay(QWidget):
    selectionMade = pyqtSignal(QPixmap, QRect)
    canceled = pyqtSignal()

    def __init__(self, screenshot: QPixmap):
        super().__init__()
        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint)
        self.setWindowState(Qt.WindowFullScreen)
        self.setCursor(Qt.CrossCursor)
        self.screenshot = screenshot
        self.setFixedSize(self.screenshot.size())
        self.move(0, 0)
        self.selection = None
        self.origin = None
        self.setAttribute(Qt.WA_TranslucentBackground)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.drawPixmap(0, 0, self.screenshot)

        overlay_color = QColor(0, 0, 0, 120)
        painter.fillRect(self.rect(), overlay_color)

        if self.selection:
            painter.setCompositionMode(QPainter.CompositionMode_Clear)
            painter.fillRect(self.selection, Qt.transparent)
            painter.setCompositionMode(QPainter.CompositionMode_SourceOver)
            painter.setPen(QPen(QColor(30, 144, 255), 2))
            painter.drawRect(self.selection)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.origin = event.pos()
            self.selection = QRect(self.origin, self.origin)
            self.update()

    def mouseMoveEvent(self, event):
        if self.origin:
            self.selection = QRect(self.origin, event.pos()).normalized()
            self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self.selection:
            rect = self.selection.normalized()
            if rect.width() > 5 and rect.height() > 5:
                cropped = self.screenshot.copy(rect)
                self.selectionMade.emit(cropped, rect)
            self.close()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.canceled.emit()
            self.close()


class ScreenSnapApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Snapshot Studio - Windows 截图工具")
        self.setWindowIcon(get_app_icon())
        self.config = load_config()
        self.current_overlay = None
        self.workspace_page = AnnotationWorkspacePage(lambda: self._open_settings_dialog())
        self._hotkey_manager = GlobalHotkeyManager(self)
        self._last_selection_rect = None
        self._save_dir = self.config.get("save_dir", DEFAULT_SAVE_DIR)

        main_widget = QWidget()
        root_layout = QVBoxLayout(main_widget)

        self.nav_toolbar = QToolBar()
        self.nav_toolbar.setMovable(False)
        self.nav_toolbar.setIconSize(QSize(0, 0))
        self.nav_toolbar.setStyleSheet(
            "QToolBar { background: #0f4c97; border: none; padding: 8px; }"
            "QToolButton { color: white; font-size: 16px; padding: 6px 18px; border-radius: 6px; }"
            "QToolButton:checked { background: #1b68c3; }"
        )
        self.nav_toolbar.setContextMenuPolicy(Qt.PreventContextMenu)
        self.nav_actions = {}
        for text, key in [("主页", "home"), ("编辑图", "edit")]:
            action = QAction(text, self)
            action.setCheckable(True)
            action.triggered.connect(lambda _, k=key: self._switch_page(k))
            self.nav_toolbar.addAction(action)
            self.nav_actions[key] = action
        exit_action = QAction("退出", self)
        exit_action.triggered.connect(QApplication.instance().quit)
        self.nav_toolbar.addAction(exit_action)
        root_layout.addWidget(self.nav_toolbar)

        self.pages = QStackedWidget()
        self.home_page = HomePage(self._save_dir)
        self.pages.addWidget(self.home_page)
        self.pages.addWidget(self.workspace_page)
        self._pages = {"home": self.home_page, "edit": self.workspace_page}
        placeholder_titles = {
            "new": "新建",
            "open": "打开",
            "save": "保存",
            "save_as": "另存为",
            "print": "打印",
            "share": "分享",
            "close": "关闭",
            "about": "关于 Snapshot Studio",
        }
        for key, title in placeholder_titles.items():
            widget = ComingSoonPage(title)
            self._pages[key] = widget
            self.pages.addWidget(widget)
        root_layout.addWidget(self.pages, 1)

        self.home_page.changeFolderRequested.connect(self.choose_folder)
        self.home_page.openFolderRequested.connect(self._open_save_folder)
        self.home_page.captureRequested.connect(self.initiate_capture)
        self.home_page.repeatRequested.connect(self._repeat_capture)
        self.home_page.openSettingsRequested.connect(self._open_settings_dialog)
        self.home_page.openWorkspaceRequested.connect(self._open_workspace)
        self._current_page = "home"
        self._update_nav_state()

        self.setCentralWidget(main_widget)
        self.resize(960, 580)

        self.home_page.set_repeat_enabled(False)
        self._register_all_hotkeys()
        self._update_hotkey_summary()

    def _switch_page(self, key):
        if key not in self._pages:
            return
        self.pages.setCurrentWidget(self._pages[key])
        self._current_page = key
        self._update_nav_state()

    def _update_nav_state(self):
        for key, action in self.nav_actions.items():
            action.blockSignals(True)
            action.setChecked(key == self._current_page)
            action.blockSignals(False)

    def choose_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "选择保存文件夹", self._save_dir)
        if folder:
            self._save_dir = folder
            self.home_page.set_save_dir(folder)
            self.config["save_dir"] = folder
            save_config(self.config)

    def _open_save_folder(self):
        os.makedirs(self._save_dir, exist_ok=True)
        QDesktopServices.openUrl(QUrl.fromLocalFile(self._save_dir))

    def _open_workspace(self):
        self._switch_page("edit")

    def _focus_workspace(self):
        self._switch_page("edit")
        self.show()
        self.raise_()
        self.activateWindow()

    def initiate_capture(self):
        save_dir = self._save_dir or DEFAULT_SAVE_DIR
        os.makedirs(save_dir, exist_ok=True)
        self.config["save_dir"] = save_dir
        save_config(self.config)

        self.hide()
        QTimer.singleShot(200, self._start_overlay_capture)

    def _start_overlay_capture(self):
        screen = QGuiApplication.primaryScreen()
        if not screen:
            QMessageBox.critical(self, "错误", "找不到屏幕设备，无法截图。")
            self.show()
            return
        screenshot = screen.grabWindow(0)
        self.current_overlay = CaptureOverlay(screenshot)
        self.current_overlay.selectionMade.connect(self._on_selection)
        self.current_overlay.canceled.connect(self._on_capture_cancel)
        self.current_overlay.show()

    def _on_capture_cancel(self):
        self.show()
        self.current_overlay = None

    def _on_selection(self, pixmap: QPixmap, selection_rect: QRect):
        self.current_overlay = None
        self._last_selection_rect = QRect(selection_rect)
        self.workspace_page.add_capture(pixmap, self._save_dir)
        self.home_page.set_repeat_enabled(True)
        self._focus_workspace()

    def _hotkey_display_text(self, action_id):
        hotkey_info = self.config.get("hotkeys", {}).get(action_id, {})
        display = hotkey_info.get("display")
        shortcut = hotkey_info.get("shortcut")
        if not shortcut:
            return "未设置"
        if display:
            return display
        return _format_display_shortcut(shortcut)

    def _update_hotkey_summary(self):
        hotkeys = self.config.get("hotkeys", {})
        summary_lines = []
        for action_id, action_name in HOTKEY_ACTIONS:
            info = hotkeys.get(action_id, {})
            shortcut = info.get("shortcut")
            if shortcut:
                display = info.get("display") or _format_display_shortcut(shortcut)
            else:
                display = "未设置"
            summary_lines.append(f"{action_name}: {display}")
        summary_text = "\n".join(summary_lines) if summary_lines else "尚未配置快捷键。"
        if hasattr(self, "home_page"):
            self.home_page.set_hotkey_summary(summary_text)

    def _open_settings_dialog(self, parent=None):
        dialog = SettingsDialog(parent or self, self.config)
        if dialog.exec_() == QDialog.Accepted:
            self.config["hotkeys"] = dialog.get_hotkeys()
            save_config(self.config)
            self._register_all_hotkeys()
            self._update_hotkey_summary()

    def _register_all_hotkeys(self):
        self._hotkey_manager.unregister_all()
        hotkeys = self.config.get("hotkeys", {})
        for action_id, _ in HOTKEY_ACTIONS:
            shortcut = hotkeys.get(action_id, {}).get("shortcut")
            self._try_register_hotkey(action_id, shortcut)

    def _try_register_hotkey(self, action_id, shortcut):
        self._hotkey_manager.unregister(action_id)
        if not shortcut:
            return
        try:
            self._hotkey_manager.register(action_id, shortcut)
        except ValueError as exc:
            QMessageBox.warning(
                self,
                "热键无效",
                str(exc),
            )
        except OSError as exc:
            QMessageBox.warning(
                self,
                "热键注册失败",
                f"无法在系统中注册热键 ({shortcut})，请尝试更换组合或以管理员身份运行。\n\n系统信息: {exc}",
            )

    def _teardown_hotkeys(self):
        self._hotkey_manager.unregister_all()

    def _trigger_hotkey_action(self, action_id):
        if action_id == "capture":
            self.initiate_capture()
        elif action_id == "repeat_capture":
            self._repeat_capture()

    def _on_hotkey_trigger(self, action_id):
        if self.current_overlay:
            return
        QTimer.singleShot(0, lambda: self._trigger_hotkey_action(action_id))

    def nativeEvent(self, eventType, message):
        if eventType in ("windows_generic_MSG", "windows_dispatcher_MSG"):
            msg = wintypes.MSG.from_address(message.__int__())
            if msg.message == WM_HOTKEY:
                self._hotkey_manager.handle_message(msg.wParam)
                return True, 0
        return super().nativeEvent(eventType, message)

    def _repeat_capture(self):
        if not self._last_selection_rect:
            QMessageBox.information(self, "重复截图", "请先执行一次区域截图，才能使用重复截图热键。")
            return
        self.hide()
        QTimer.singleShot(200, self._do_repeat_capture)

    def _do_repeat_capture(self):
        screen = QGuiApplication.primaryScreen()
        if not screen:
            QMessageBox.critical(self, "错误", "找不到屏幕设备，无法截图。")
            self.show()
            return
        rect = QRect(self._last_selection_rect)
        if rect.width() < 5 or rect.height() < 5:
            QMessageBox.warning(self, "重复截图失败", "记录的区域尺寸无效，请重新截图。")
            self.show()
            return
        screenshot = screen.grabWindow(0)
        cropped = screenshot.copy(rect)
        self.workspace_page.add_capture(cropped, self._save_dir)
        self._focus_workspace()

    def closeEvent(self, event):
        self._teardown_hotkeys()
        super().closeEvent(event)


def main():
    app = QApplication(sys.argv)
    app.setStyleSheet(
        """
        QWidget { font-size: 15px; }
        QPushButton { font-size: 15px; }
        QListWidget { font-size: 15px; }
        QTabBar::tab { font-size: 14px; height: 34px; }
        QToolBar { font-size: 14px; }
        """
    )
    app.setWindowIcon(get_app_icon())
    window = ScreenSnapApp()
    window.showMaximized()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
