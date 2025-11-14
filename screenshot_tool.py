import ctypes
from ctypes import wintypes
import json
import os
import sys
from datetime import datetime
from enum import Enum, auto

from PyQt5.QtCore import QPoint, QRect, Qt, pyqtSignal, QTimer, QUrl, QSize
from PyQt5.QtGui import (
    QColor,
    QGuiApplication,
    QPainter,
    QPen,
    QPixmap,
    QFont,
    QIcon,
    QDesktopServices,
    QKeySequence,
)
from PyQt5.QtWidgets import (
    QAction,
    QApplication,
    QColorDialog,
    QFileDialog,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QDoubleSpinBox,
    QShortcut,
    QListWidget,
    QTabWidget,
    QStackedWidget,
    QToolBar,
    QVBoxLayout,
    QWidget,
    QDialog,
    QHBoxLayout,
    QFrame,
    QSizePolicy,
    QCheckBox,
)


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(BASE_DIR, "config.json")
DEFAULT_SAVE_DIR = os.path.join(BASE_DIR, "screenshots")
ICON_PATH = os.path.join(BASE_DIR, "favicon", "favicon.ico")
_APP_ICON = None
CLASSIC_COLORS = [
    "#F44336",
    "#FF9800",
    "#FFC107",
    "#4CAF50",
    "#2196F3",
    "#3F51B5",
    "#9C27B0",
    "#00BCD4",
    "#607D8B",
]

DEFAULT_MARKER_STYLE = {
    "fill": "#DC143C",
    "border": "#FFFFFFFF",
    "border_enabled": True,
    "size": 28,
    "font_ratio": 0.7,
}

DEFAULT_RECT_STYLE = {
    "fill": "#00000000",
    "border": "#FF7043",
    "border_enabled": True,
    "width": 3,
    "radius": 8,
}


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
    optionsUpdated = pyqtSignal()

    HANDLE_SIZE = 12
    MIN_RECT_SIZE = 8

    def __init__(self, pixmap: QPixmap):
        super().__init__()
        self.base_pixmap = pixmap
        self.setFixedSize(self.base_pixmap.size())
        self.setMouseTracking(True)
        self.rectangles = []
        self.markers = []
        self.tool = Tool.NONE
        self.marker_fill_color = QColor(DEFAULT_MARKER_STYLE["fill"])
        self.marker_border_color = QColor(DEFAULT_MARKER_STYLE["border"])
        self.marker_border_enabled = DEFAULT_MARKER_STYLE["border_enabled"]
        self.marker_size = DEFAULT_MARKER_STYLE["size"]
        self.marker_font_ratio = DEFAULT_MARKER_STYLE["font_ratio"]
        self.next_marker_number = DEFAULT_MARKER_STYLE.get("next_number", 1)
        self.dragging_marker_index = None
        self.selected_marker_index = None
        self.hover_marker_index = None
        self.markers_flattened = True
        self.rectangle_fill_color = QColor(DEFAULT_RECT_STYLE["fill"])
        self.rectangle_border_color = QColor(DEFAULT_RECT_STYLE["border"])
        self.rectangle_border_enabled = DEFAULT_RECT_STYLE["border_enabled"]
        self.rectangle_border_width = DEFAULT_RECT_STYLE["width"]
        self.rectangle_corner_radius = DEFAULT_RECT_STYLE["radius"]
        self.rectangles_flattened = True
        self.selected_rectangle_index = None
        self.rect_drag_mode = None
        self.rect_drag_handle = None
        self.rect_initial_rect = QRect()
        self.rect_drag_origin = QPoint()
        self.creating_new_rect = False

    def set_tool(self, tool: Tool):
        self.tool = tool
        self._reset_rect_drag()
        if tool == Tool.MARKER:
            self._update_cursor(Qt.CrossCursor)
            self.hover_marker_index = None
        elif tool == Tool.RECTANGLE:
            self._update_cursor(Qt.ArrowCursor)
        else:
            self._update_cursor(Qt.ArrowCursor)
            self.hover_marker_index = None

    def clear_annotations(self):
        self.rectangles.clear()
        self.markers.clear()
        self.next_marker_number = 1
        self.markers_flattened = True
        self.rectangles_flattened = True
        self.dragging_marker_index = None
        self.selected_marker_index = None
        self.hover_marker_index = None
        self.selected_rectangle_index = None
        self._reset_rect_drag()
        self.update()
        self.optionsUpdated.emit()

    def _has_active_marker(self):
        return (
            self.selected_marker_index is not None
            and not self.markers_flattened
            and 0 <= self.selected_marker_index < len(self.markers)
        )

    def set_marker_color(self, color: QColor):
        if color.isValid():
            self.marker_fill_color = color
            if self._has_active_marker():
                self.markers[self.selected_marker_index]['fill'] = QColor(color)
            self.update()
            self.optionsUpdated.emit()

    def set_marker_size(self, size: int):
        self.marker_size = max(10, min(120, size))
        if self._has_active_marker():
            self.markers[self.selected_marker_index]['size'] = self.marker_size
        self.update()
        self.optionsUpdated.emit()

    def set_next_marker_number(self, number: int):
        self.next_marker_number = max(1, number)
        self.optionsUpdated.emit()

    def set_current_marker_number(self, number: int):
        if self._has_active_marker():
            self.markers[self.selected_marker_index]['number'] = max(1, number)
            self.update()
            self.optionsUpdated.emit()

    def set_marker_border_enabled(self, enabled: bool):
        self.marker_border_enabled = enabled
        if self._has_active_marker():
            self.markers[self.selected_marker_index]['border_enabled'] = enabled
        self.update()
        self.optionsUpdated.emit()

    def set_marker_border_color(self, color: QColor):
        if color.isValid():
            self.marker_border_color = color
            if self._has_active_marker():
                self.markers[self.selected_marker_index]['border_color'] = QColor(color)
            self.update()
            self.optionsUpdated.emit()

    def set_marker_font_ratio(self, ratio: float):
        self.marker_font_ratio = max(0.3, min(1.2, ratio))
        if self._has_active_marker():
            self.markers[self.selected_marker_index]['font_ratio'] = self.marker_font_ratio
        self.update()
        self.optionsUpdated.emit()

    def flatten_markers(self):
        self.dragging_marker_index = None
        self.markers_flattened = True
        self.selected_marker_index = None
        self.hover_marker_index = None
        self.next_marker_number = 1
        self.optionsUpdated.emit()

    def duplicate_marker(self):
        if self._has_active_marker():
            marker = dict(self.markers[self.selected_marker_index])
            marker['pos'] = marker['pos'] + QPoint(12, 12)
            self.markers.append(marker)
            self.selected_marker_index = len(self.markers) - 1
            self.dragging_marker_index = self.selected_marker_index
            self.markers_flattened = False
            self.update()
            self.optionsUpdated.emit()

    def _has_active_rectangle(self):
        return (
            self.selected_rectangle_index is not None
            and not self.rectangles_flattened
            and 0 <= self.selected_rectangle_index < len(self.rectangles)
            and not self.rectangles[self.selected_rectangle_index]['flattened']
        )

    def set_rectangle_fill_color(self, color: QColor):
        if color.isValid():
            self.rectangle_fill_color = color
            if self._has_active_rectangle():
                self.rectangles[self.selected_rectangle_index]['fill'] = QColor(color)
            self.update()
            self.optionsUpdated.emit()

    def set_rectangle_border_color(self, color: QColor):
        if color.isValid():
            self.rectangle_border_color = color
            if self._has_active_rectangle():
                self.rectangles[self.selected_rectangle_index]['border'] = QColor(color)
            self.update()
            self.optionsUpdated.emit()

    def set_rectangle_border_width(self, width: int):
        self.rectangle_border_width = max(1, min(20, width))
        if self._has_active_rectangle():
            self.rectangles[self.selected_rectangle_index]['width'] = self.rectangle_border_width
        self.update()
        self.optionsUpdated.emit()

    def set_rectangle_corner_radius(self, radius: int):
        self.rectangle_corner_radius = max(0, min(60, radius))
        if self._has_active_rectangle():
            self.rectangles[self.selected_rectangle_index]['radius'] = self.rectangle_corner_radius
        self.update()
        self.optionsUpdated.emit()

    def set_rectangle_border_enabled(self, enabled: bool):
        self.rectangle_border_enabled = enabled
        if self._has_active_rectangle():
            self.rectangles[self.selected_rectangle_index]['border_enabled'] = enabled
        self.update()
        self.optionsUpdated.emit()

    def flatten_rectangle(self):
        if self._has_active_rectangle():
            self.rectangles[self.selected_rectangle_index]['flattened'] = True
            self.selected_rectangle_index = None
            if all(r['flattened'] for r in self.rectangles):
                self.rectangles_flattened = True
            self.update()
            self.optionsUpdated.emit()

    def duplicate_rectangle(self):
        if self._has_active_rectangle():
            info = dict(self.rectangles[self.selected_rectangle_index])
            info['rect'] = info['rect'].translated(12, 12)
            info['flattened'] = False
        self.rectangles.append(info)
        self.selected_rectangle_index = len(self.rectangles) - 1
        self.rectangles_flattened = False
        self.update()
        self.optionsUpdated.emit()

    def apply_style_defaults(self, marker_style, rect_style):
        if marker_style:
            self.marker_fill_color = QColor(marker_style.get("fill", DEFAULT_MARKER_STYLE["fill"]))
            self.marker_border_color = QColor(marker_style.get("border", DEFAULT_MARKER_STYLE["border"]))
            self.marker_border_enabled = marker_style.get("border_enabled", DEFAULT_MARKER_STYLE["border_enabled"])
            self.marker_size = marker_style.get("size", DEFAULT_MARKER_STYLE["size"])
            self.marker_font_ratio = marker_style.get("font_ratio", DEFAULT_MARKER_STYLE["font_ratio"])
        self.next_marker_number = 1
        if rect_style:
            self.rectangle_fill_color = QColor(rect_style.get("fill", DEFAULT_RECT_STYLE["fill"]))
            self.rectangle_border_color = QColor(rect_style.get("border", DEFAULT_RECT_STYLE["border"]))
            self.rectangle_border_enabled = rect_style.get("border_enabled", DEFAULT_RECT_STYLE["border_enabled"])
            self.rectangle_border_width = rect_style.get("width", DEFAULT_RECT_STYLE["width"])
            self.rectangle_corner_radius = rect_style.get("radius", DEFAULT_RECT_STYLE["radius"])

    def marker_style_state(self):
        return {
            "fill": self.marker_fill_color.name(QColor.HexArgb),
            "border": self.marker_border_color.name(QColor.HexArgb),
            "border_enabled": self.marker_border_enabled,
            "size": self.marker_size,
            "font_ratio": self.marker_font_ratio,
            "next_number": self.next_marker_number,
        }

    def rectangle_style_state(self):
        return {
            "fill": self.rectangle_fill_color.name(QColor.HexArgb),
            "border": self.rectangle_border_color.name(QColor.HexArgb),
            "border_enabled": self.rectangle_border_enabled,
            "width": self.rectangle_border_width,
            "radius": self.rectangle_corner_radius,
        }

    def delete_selected_shape(self):
        if self._has_active_marker():
            self.markers.pop(self.selected_marker_index)
            self.selected_marker_index = None
            self.hover_marker_index = None
            self.update()
            self.optionsUpdated.emit()
            return True
        if self._has_active_rectangle():
            self.rectangles.pop(self.selected_rectangle_index)
            self.selected_rectangle_index = None
            self.update()
            self.optionsUpdated.emit()
            return True
        return False

    def flatten_all_annotations(self):
        self.markers_flattened = True
        self.selected_marker_index = None
        self.dragging_marker_index = None
        self.hover_marker_index = None
        for marker in self.markers:
            marker['border_enabled'] = marker.get('border_enabled', True)
        for rect in self.rectangles:
            rect['flattened'] = True
        self.rectangles_flattened = True
        self.selected_rectangle_index = None
        self.optionsUpdated.emit()

    def undo_last_shape(self):
        if self.markers and not self.markers_flattened:
            self.markers.pop()
            self.selected_marker_index = None
            self.update()
            self.optionsUpdated.emit()
            return True
        if self.rectangles and not self.rectangles_flattened:
            self.rectangles.pop()
            self.selected_rectangle_index = None
            self.update()
            self.optionsUpdated.emit()
            return True
        return False

    def _reset_rect_drag(self):
        self.rect_drag_mode = None
        self.rect_drag_handle = None
        self.rect_initial_rect = QRect()
        self.rect_drag_origin = QPoint()
        self.creating_new_rect = False

    def mousePressEvent(self, event):
        if event.button() != Qt.LeftButton:
            return
        if self.tool == Tool.MARKER:
            self._handle_marker_press(event)
            return
        if self.tool == Tool.RECTANGLE:
            self._handle_rect_press(event)
            return

    def mouseMoveEvent(self, event):
        if self.tool == Tool.MARKER and self.dragging_marker_index is not None and not self.markers_flattened:
            self.markers[self.dragging_marker_index]['pos'] = event.pos()
            self.update()
            return
        if self.tool == Tool.MARKER and self.dragging_marker_index is None:
            self._update_marker_hover_cursor(event.pos())
        if self.tool == Tool.RECTANGLE and self.selected_rectangle_index is not None and self.rect_drag_mode:
            info = self.rectangles[self.selected_rectangle_index]
            rect = QRect(self.rect_initial_rect)
            delta = event.pos() - self.rect_drag_origin
            if self.rect_drag_mode == 'move':
                rect.translate(delta)
            else:
                rect = self._resize_rect(self.rect_initial_rect, self.rect_drag_handle, delta, event.modifiers())
            rect = rect.normalized()
            if rect.width() > 4 and rect.height() > 4:
                info['rect'] = rect
            self.update()
        else:
            self._update_hover_cursor(event.pos())

    def mouseReleaseEvent(self, event):
        if event.button() != Qt.LeftButton:
            return
        if self.tool == Tool.MARKER and self.dragging_marker_index is not None:
            self.dragging_marker_index = None
            self.update()
        if self.tool == Tool.RECTANGLE:
            if (
                self.creating_new_rect
                and self.selected_rectangle_index is not None
                and self.selected_rectangle_index < len(self.rectangles)
            ):
                rect = self.rectangles[self.selected_rectangle_index]['rect']
                if rect.width() < self.MIN_RECT_SIZE or rect.height() < self.MIN_RECT_SIZE:
                    self.rectangles.pop(self.selected_rectangle_index)
                    self.selected_rectangle_index = None
                    self.update()
                    self.optionsUpdated.emit()
            self._reset_rect_drag()
            self._update_cursor(Qt.ArrowCursor)

    def _handle_marker_press(self, event):
        idx = self._marker_hit_test(event.pos())
        if idx is not None and not self.markers_flattened:
            self.dragging_marker_index = idx
            self.selected_marker_index = idx
            self.optionsUpdated.emit()
        else:
            marker = {
                'pos': event.pos(),
                'number': self.next_marker_number,
                'fill': QColor(self.marker_fill_color),
                'size': self.marker_size,
                'border_enabled': self.marker_border_enabled,
                'border_color': QColor(self.marker_border_color),
                'font_ratio': self.marker_font_ratio,
            }
            self.markers.append(marker)
            self.selected_marker_index = len(self.markers) - 1
            self.dragging_marker_index = self.selected_marker_index
            self.markers_flattened = False
            self.next_marker_number += 1
            self.optionsUpdated.emit()
        self.update()

    def _handle_rect_press(self, event):
        idx, handle = self._rect_handle_hit_test(event.pos())
        if idx is not None:
            self.selected_rectangle_index = idx
            self.rect_drag_mode = 'resize'
            self.rect_drag_handle = handle
            self.rect_initial_rect = QRect(self.rectangles[idx]['rect'])
            self.rect_drag_origin = event.pos()
            self.rectangles_flattened = False
            self.optionsUpdated.emit()
            self.creating_new_rect = False
            if handle in ("top-left", "bottom-right"):
                self._update_cursor(Qt.SizeFDiagCursor)
            else:
                self._update_cursor(Qt.SizeBDiagCursor)
            return
        idx = self._rect_hit_test(event.pos())
        if idx is not None:
            self.selected_rectangle_index = idx
            self.rect_drag_mode = 'move'
            self.rect_initial_rect = QRect(self.rectangles[idx]['rect'])
            self.rect_drag_origin = event.pos()
            self.rectangles_flattened = False
            self.optionsUpdated.emit()
            self.creating_new_rect = False
            self._update_cursor(Qt.SizeAllCursor)
            return
        rect_info = {
            'rect': QRect(event.pos(), event.pos()),
            'fill': QColor(self.rectangle_fill_color),
            'border': QColor(self.rectangle_border_color),
            'border_enabled': self.rectangle_border_enabled,
            'width': self.rectangle_border_width,
            'radius': self.rectangle_corner_radius,
            'flattened': False,
        }
        self.rectangles.append(rect_info)
        self.selected_rectangle_index = len(self.rectangles) - 1
        self.rect_drag_mode = 'resize'
        self.rect_drag_handle = 'bottom-right'
        self.rect_initial_rect = QRect(rect_info['rect'])
        self.rect_drag_origin = event.pos()
        self.rectangles_flattened = False
        self.optionsUpdated.emit()
        self.creating_new_rect = True
        self._update_cursor(Qt.SizeFDiagCursor)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.drawPixmap(0, 0, self.base_pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        for idx, info in enumerate(self.rectangles):
            painter.setBrush(info['fill'])
            if info['border_enabled']:
                painter.setPen(QPen(info['border'], info['width']))
            else:
                painter.setPen(Qt.NoPen)
            painter.drawRoundedRect(info['rect'], info['radius'], info['radius'])
            if idx == self.selected_rectangle_index and not info['flattened']:
                painter.setPen(QPen(QColor(255, 255, 255), 1, Qt.DashLine))
                painter.setBrush(Qt.NoBrush)
                painter.drawRect(info['rect'])
                for handle_rect in self._handle_rects(info['rect']):
                    painter.fillRect(handle_rect, QColor(255, 235, 59))
        painter.setPen(Qt.NoPen)
        font = QFont()
        font.setBold(True)
        for idx, marker in enumerate(self.markers):
            radius = marker['size']
            font.setPixelSize(int(radius * marker['font_ratio']))
            painter.setFont(font)
            ellipse_rect = QRect(marker['pos'].x() - radius, marker['pos'].y() - radius, radius * 2, radius * 2)
            painter.setBrush(marker['fill'])
            painter.drawEllipse(ellipse_rect)
            if marker['border_enabled']:
                painter.setPen(QPen(marker['border_color'], max(2, radius * 0.2)))
                painter.setBrush(Qt.NoBrush)
                painter.drawEllipse(ellipse_rect)
                painter.setPen(Qt.NoPen)
            painter.setBrush(marker['fill'])
            painter.setPen(Qt.white)
            painter.drawText(ellipse_rect, Qt.AlignCenter, str(marker['number']))
            painter.setPen(Qt.NoPen)
            should_draw = (
                not self.markers_flattened
                and self.dragging_marker_index is None
                and (idx == self.selected_marker_index or idx == self.hover_marker_index)
            )
            if should_draw:
                painter.setPen(QPen(QColor(255, 255, 255), 2, Qt.DashLine))
                painter.setBrush(Qt.NoBrush)
                painter.drawRect(ellipse_rect.adjusted(-6, -6, 6, 6))
                painter.setPen(Qt.NoPen)
                painter.setBrush(marker['fill'])

    def export_pixmap(self):
        annotated = QPixmap(self.base_pixmap.size())
        annotated.fill(Qt.transparent)
        painter = QPainter(annotated)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.drawPixmap(0, 0, self.base_pixmap)
        for info in self.rectangles:
            painter.setBrush(info['fill'])
            if info['border_enabled']:
                painter.setPen(QPen(info['border'], info['width']))
            else:
                painter.setPen(Qt.NoPen)
            painter.drawRoundedRect(info['rect'], info['radius'], info['radius'])
        painter.setPen(Qt.NoPen)
        font = QFont()
        font.setBold(True)
        for marker in self.markers:
            radius = marker['size']
            font.setPixelSize(int(radius * marker['font_ratio']))
            painter.setFont(font)
            ellipse_rect = QRect(marker['pos'].x() - radius, marker['pos'].y() - radius, radius * 2, radius * 2)
            painter.setBrush(marker['fill'])
            painter.drawEllipse(ellipse_rect)
            if marker['border_enabled']:
                painter.setPen(QPen(marker['border_color'], max(2, radius * 0.2)))
                painter.setBrush(Qt.NoBrush)
                painter.drawEllipse(ellipse_rect)
                painter.setPen(Qt.NoPen)
            painter.setBrush(marker['fill'])
            painter.setPen(Qt.white)
            painter.drawText(ellipse_rect, Qt.AlignCenter, str(marker['number']))
            painter.setPen(Qt.NoPen)
        painter.end()
        return annotated

    def _marker_hit_test(self, pos: QPoint):
        for idx, marker in enumerate(self.markers):
            radius = marker['size']
            ellipse_rect = QRect(marker['pos'].x() - radius, marker['pos'].y() - radius, radius * 2, radius * 2)
            if ellipse_rect.contains(pos):
                return idx
        return None

    def _rect_hit_test(self, pos: QPoint):
        for idx in reversed(range(len(self.rectangles))):
            info = self.rectangles[idx]
            if info['rect'].contains(pos) and not info['flattened']:
                return idx
        return None

    def _handle_rects(self, rect: QRect):
        half = self.HANDLE_SIZE // 2
        points = [rect.topLeft(), rect.topRight(), rect.bottomLeft(), rect.bottomRight()]
        return [QRect(p.x() - half, p.y() - half, self.HANDLE_SIZE, self.HANDLE_SIZE) for p in points]

    def _rect_handle_hit_test(self, pos: QPoint):
        handles = ['top-left', 'top-right', 'bottom-left', 'bottom-right']
        for idx in reversed(range(len(self.rectangles))):
            info = self.rectangles[idx]
            if info['flattened']:
                continue
            for handle_name, handle_rect in zip(handles, self._handle_rects(info['rect'])):
                if handle_rect.contains(pos):
                    return idx, handle_name
        return None, None

    def _resize_rect(self, initial_rect: QRect, handle: str, delta: QPoint, modifiers):
        rect = QRect(initial_rect)
        dx, dy = delta.x(), delta.y()
        if handle == 'top-left':
            rect.setTopLeft(rect.topLeft() + delta)
        elif handle == 'top-right':
            rect.setTopRight(rect.topRight() + QPoint(dx, dy))
        elif handle == 'bottom-left':
            rect.setBottomLeft(rect.bottomLeft() + QPoint(dx, dy))
        else:
            rect.setBottomRight(rect.bottomRight() + delta)
        if modifiers & Qt.ControlModifier:
            width = rect.width()
            height = rect.height()
            size = min(abs(width), abs(height))
            if width < 0:
                rect.setLeft(rect.right() - size)
            else:
                rect.setRight(rect.left() + size)
            if height < 0:
                rect.setTop(rect.bottom() - size)
            else:
                rect.setBottom(rect.top() + size)
        return rect

    def _update_marker_hover_cursor(self, pos: QPoint):
        if self.tool != Tool.MARKER or self.markers_flattened:
            self.hover_marker_index = None
            self._update_cursor(Qt.CrossCursor if self.tool == Tool.MARKER else Qt.ArrowCursor)
            return
        idx = self._marker_hit_test(pos)
        if idx is not None:
            self.hover_marker_index = idx
            self._update_cursor(Qt.SizeAllCursor)
        else:
            self.hover_marker_index = None
            self._update_cursor(Qt.CrossCursor)

    def _update_hover_cursor(self, pos: QPoint):
        if self.tool != Tool.RECTANGLE:
            self._update_cursor(Qt.ArrowCursor)
            return
        idx, handle = self._rect_handle_hit_test(pos)
        if idx is not None and handle:
            if handle in ("top-left", "bottom-right"):
                self._update_cursor(Qt.SizeFDiagCursor)
            else:
                self._update_cursor(Qt.SizeBDiagCursor)
            return
        if self._rect_hit_test(pos) is not None:
            self._update_cursor(Qt.SizeAllCursor)
        else:
            self._update_cursor(Qt.ArrowCursor)

    def _update_cursor(self, cursor_shape):
        self.setCursor(cursor_shape if self.tool != Tool.NONE else Qt.ArrowCursor)

class AnnotationTab(QWidget):
    def __init__(self, pixmap: QPixmap, save_dir: str, style_state, style_callback):
        super().__init__()
        self.canvas = AnnotationCanvas(pixmap)
        self.canvas.apply_style_defaults(style_state.get("marker"), style_state.get("rectangle"))
        self.save_dir = save_dir
        self.auto_saved_path = self._auto_save_pixmap(pixmap)
        self.style_state = style_state
        self.style_callback = style_callback
        self.base_status_text = f"自动保存: {self.auto_saved_path}"
        self.dirty = False
        layout = QVBoxLayout()

        toolbar = QToolBar("工具")
        toolbar.setIconSize(QSize(20, 20))
        rect_action = QAction("标注框", self)
        rect_action.triggered.connect(lambda: self._set_tool(Tool.RECTANGLE))
        toolbar.addAction(rect_action)

        marker_action = QAction("顺序标记", self)
        marker_action.triggered.connect(lambda: self._set_tool(Tool.MARKER))
        toolbar.addAction(marker_action)

        clear_action = QAction("清除标注", self)
        clear_action.triggered.connect(self.canvas.clear_annotations)
        toolbar.addAction(clear_action)

        delete_action = QAction("删除选中", self)
        delete_action.triggered.connect(self._delete_selected)
        toolbar.addAction(delete_action)

        save_action = QAction("保存标注图", self)
        save_action.triggered.connect(self.save_annotated_image)
        toolbar.addAction(save_action)

        layout.addWidget(toolbar)

        self.marker_panel = MarkerOptionsPanel(self.canvas)
        self.marker_panel.setVisible(False)
        layout.addWidget(self.marker_panel)

        self.rectangle_panel = RectangleOptionsPanel(self.canvas)
        self.rectangle_panel.setVisible(False)
        layout.addWidget(self.rectangle_panel)

        scroll = QScrollArea()
        scroll.setWidget(self.canvas)
        layout.addWidget(scroll, 1)

        self.status_label = QLabel(f"自动保存: {self.auto_saved_path}")
        layout.addWidget(self.status_label)
        self.setLayout(layout)
        self.canvas.optionsUpdated.connect(self._mark_dirty)
        self._persist_style_defaults()

        self.undo_shortcut = QShortcut(QKeySequence("Ctrl+Z"), self)
        self.undo_shortcut.activated.connect(self._undo_last_action)
        self.copy_shortcut = QShortcut(QKeySequence("Ctrl+C"), self)
        self.copy_shortcut.activated.connect(self._copy_to_clipboard)
        self.delete_shortcut = QShortcut(QKeySequence("Delete"), self)
        self.delete_shortcut.activated.connect(self._delete_selected)

    def _auto_save_pixmap(self, pixmap: QPixmap):
        os.makedirs(self.save_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"screenshot_{timestamp}.png"
        path = os.path.join(self.save_dir, filename)
        pixmap.save(path, "PNG")
        return path

    def save_annotated_image(self):
        if self.canvas.markers and not self.canvas.markers_flattened:
            self.canvas.flatten_all_annotations()
        annotated = self.canvas.export_pixmap()
        base, ext = os.path.splitext(os.path.basename(self.auto_saved_path))
        annotated_path = os.path.join(self.save_dir, f"{base}_annotated{ext}")
        if annotated.save(annotated_path, "PNG"):
            self.status_label.setText(f"标注图已保存: {annotated_path}")
            self.dirty = False
            return True
        QMessageBox.warning(self, "保存失败", "无法写入标注截图，请检查保存路径。")
        return False

    def _set_tool(self, tool: Tool):
        self.canvas.set_tool(tool)
        self.marker_panel.setVisible(tool == Tool.MARKER)
        self.rectangle_panel.setVisible(tool == Tool.RECTANGLE)

    def _mark_dirty(self):
        self.dirty = True
        self.status_label.setText(f"{self.base_status_text} *未保存")
        self._persist_style_defaults()

    def _undo_last_action(self):
        if self.canvas.undo_last_shape():
            self.status_label.setText("已撤销上一次操作")
            self._mark_dirty()
        else:
            QMessageBox.information(self, "无法撤销", "当前没有可撤销的操作。")

    def _copy_to_clipboard(self):
        self.canvas.flatten_all_annotations()
        pix = self.canvas.export_pixmap()
        QApplication.clipboard().setPixmap(pix)
        self.status_label.setText("已平化并复制到剪贴板")
        self._mark_dirty()

    def _delete_selected(self):
        if self.canvas.delete_selected_shape():
            self.status_label.setText("已删除当前选择")
            self._mark_dirty()
        else:
            QApplication.beep()

    def _persist_style_defaults(self):
        if not self.style_callback:
            return
        marker_style = self.canvas.marker_style_state()
        rect_style = self.canvas.rectangle_style_state()
        self.style_callback("marker", marker_style)
        self.style_callback("rectangle", rect_style)

    def maybe_close(self):
        if not self.dirty:
            return True
        reply = QMessageBox.question(
            self,
            "保存截图",
            "当前截图有未保存的修改，是否保存？",
            QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel,
        )
        if reply == QMessageBox.Yes:
            return self.save_annotated_image()
        if reply == QMessageBox.Cancel:
            return False
        return True


class MarkerOptionsPanel(QFrame):
    def __init__(self, canvas: AnnotationCanvas):
        super().__init__()
        self.canvas = canvas
        self.setFrameShape(QFrame.StyledPanel)
        self.setStyleSheet("QFrame { background: #f7f7f7; border: 1px solid #dddddd; border-radius: 6px; }")
        layout = QVBoxLayout()

        palette_layout = QHBoxLayout()
        palette_label = QLabel("经典颜色:")
        palette_layout.addWidget(palette_label)
        for hex_color in CLASSIC_COLORS:
            btn = QPushButton()
            btn.setFixedSize(24, 24)
            btn.setStyleSheet(f"background-color: {hex_color}; border: 1px solid #777;")
            btn.clicked.connect(lambda _, c=QColor(hex_color): self._set_palette_color(c))
            palette_layout.addWidget(btn)
        palette_layout.addStretch()
        layout.addLayout(palette_layout)

        row = QHBoxLayout()
        color_label = QLabel("填充:")
        self.color_btn = QPushButton()
        self.color_btn.setFixedSize(40, 22)
        self.color_btn.clicked.connect(self._choose_color)

        border_label = QLabel("边框:")
        self.border_color_btn = QPushButton()
        self.border_color_btn.setFixedSize(40, 22)
        self.border_color_btn.clicked.connect(self._choose_border_color)

        self.border_checkbox = QCheckBox("启用白边")
        self.border_checkbox.toggled.connect(canvas.set_marker_border_enabled)

        row.addWidget(color_label)
        row.addWidget(self.color_btn)
        row.addSpacing(10)
        row.addWidget(border_label)
        row.addWidget(self.border_color_btn)
        row.addWidget(self.border_checkbox)
        row.addStretch()
        layout.addLayout(row)

        controls = QHBoxLayout()
        size_label = QLabel("大小:")
        self.size_spin = QSpinBox()
        self.size_spin.setRange(10, 120)
        self.size_spin.valueChanged.connect(canvas.set_marker_size)

        ratio_label = QLabel("字体比例:")
        self.font_ratio_spin = QDoubleSpinBox()
        self.font_ratio_spin.setRange(0.3, 1.2)
        self.font_ratio_spin.setSingleStep(0.05)
        self.font_ratio_spin.valueChanged.connect(canvas.set_marker_font_ratio)

        current_label = QLabel("当前编号:")
        self.current_number_spin = QSpinBox()
        self.current_number_spin.setRange(1, 999)
        self.current_number_spin.valueChanged.connect(canvas.set_current_marker_number)

        next_label = QLabel("下一个编号:")
        self.number_spin = QSpinBox()
        self.number_spin.setRange(1, 999)
        self.number_spin.valueChanged.connect(canvas.set_next_marker_number)

        duplicate_btn = QPushButton("重复")
        duplicate_btn.clicked.connect(canvas.duplicate_marker)

        flatten_btn = QPushButton("平化")
        flatten_btn.clicked.connect(canvas.flatten_markers)

        controls.addWidget(size_label)
        controls.addWidget(self.size_spin)
        controls.addSpacing(8)
        controls.addWidget(ratio_label)
        controls.addWidget(self.font_ratio_spin)
        controls.addSpacing(8)
        controls.addWidget(current_label)
        controls.addWidget(self.current_number_spin)
        controls.addSpacing(8)
        controls.addWidget(next_label)
        controls.addWidget(self.number_spin)
        controls.addStretch()
        controls.addWidget(duplicate_btn)
        controls.addWidget(flatten_btn)
        layout.addLayout(controls)

        self.setLayout(layout)

        self.canvas.optionsUpdated.connect(self.sync_from_canvas)
        self.sync_from_canvas()

    def _update_color_button(self):
        color = self.canvas.marker_fill_color
        self.color_btn.setStyleSheet(f"background-color: {color.name(QColor.HexArgb)}; border: 1px solid #777;")

    def _choose_color(self):
        color = QColorDialog.getColor(self.canvas.marker_fill_color, self, "选择顺序标记颜色")
        if color.isValid():
            self.canvas.set_marker_color(color)
            self._update_color_button()

    def _choose_border_color(self):
        color = QColorDialog.getColor(self.canvas.marker_border_color, self, "选择边框颜色")
        if color.isValid():
            self.canvas.set_marker_border_color(color)
            self._update_border_button()

    def _set_palette_color(self, color: QColor):
        self.canvas.set_marker_color(color)
        self._update_color_button()

    def _update_border_button(self):
        color = self.canvas.marker_border_color
        self.border_color_btn.setStyleSheet(f"background-color: {color.name(QColor.HexArgb)}; border: 1px solid #777;")

    def sync_from_canvas(self):
        self._update_color_button()
        self.size_spin.blockSignals(True)
        self.size_spin.setValue(self.canvas.marker_size)
        self.size_spin.blockSignals(False)
        self.number_spin.blockSignals(True)
        self.number_spin.setValue(self.canvas.next_marker_number)
        self.number_spin.blockSignals(False)
        self.font_ratio_spin.blockSignals(True)
        self.font_ratio_spin.setValue(self.canvas.marker_font_ratio)
        self.font_ratio_spin.blockSignals(False)
        self.border_checkbox.blockSignals(True)
        self.border_checkbox.setChecked(self.canvas.marker_border_enabled)
        self.border_checkbox.blockSignals(False)
        self._update_border_button()
        active = (
            self.canvas.selected_marker_index is not None
            and not self.canvas.markers_flattened
            and 0 <= self.canvas.selected_marker_index < len(self.canvas.markers)
        )
        self.current_number_spin.setEnabled(active)
        if active:
            self.current_number_spin.blockSignals(True)
            self.current_number_spin.setValue(self.canvas.markers[self.canvas.selected_marker_index]["number"])
            self.current_number_spin.blockSignals(False)
        else:
            self.current_number_spin.blockSignals(True)
            self.current_number_spin.setValue(self.canvas.next_marker_number)
            self.current_number_spin.blockSignals(False)


class RectangleOptionsPanel(QFrame):
    def __init__(self, canvas: AnnotationCanvas):
        super().__init__()
        self.canvas = canvas
        self.setFrameShape(QFrame.StyledPanel)
        self.setStyleSheet("QFrame { background: #f7f7f7; border: 1px solid #dddddd; border-radius: 6px; }")

        layout = QVBoxLayout()

        palette_layout = QHBoxLayout()
        palette_label = QLabel("经典颜色:")
        palette_layout.addWidget(palette_label)
        for hex_color in CLASSIC_COLORS:
            btn = QPushButton()
            btn.setFixedSize(24, 24)
            btn.setStyleSheet(f"background-color: {hex_color}; border: 1px solid #777;")
            btn.clicked.connect(lambda _, c=QColor(hex_color): self._apply_palette_color(c))
            palette_layout.addWidget(btn)
        palette_layout.addStretch()
        layout.addLayout(palette_layout)

        actions = QHBoxLayout()
        self.color_btn = QPushButton("选择边框颜色")
        self.color_btn.clicked.connect(self._choose_color)
        actions.addWidget(self.color_btn)

        width_label = QLabel("线宽:")
        self.width_spin = QSpinBox()
        self.width_spin.setRange(1, 20)
        self.width_spin.valueChanged.connect(canvas.set_rectangle_border_width)
        actions.addSpacing(10)
        actions.addWidget(width_label)
        actions.addWidget(self.width_spin)

        radius_label = QLabel("圆角:")
        self.radius_spin = QSpinBox()
        self.radius_spin.setRange(0, 60)
        self.radius_spin.valueChanged.connect(canvas.set_rectangle_corner_radius)
        actions.addSpacing(10)
        actions.addWidget(radius_label)
        actions.addWidget(self.radius_spin)

        self.square_btn = QPushButton("直角")
        self.square_btn.clicked.connect(lambda: self._set_radius_preset(0))
        self.round_btn = QPushButton("柔和圆角")
        self.round_btn.clicked.connect(lambda: self._set_radius_preset(8))
        actions.addWidget(self.square_btn)
        actions.addWidget(self.round_btn)

        self.duplicate_btn = QPushButton("复制")
        self.duplicate_btn.clicked.connect(canvas.duplicate_rectangle)
        actions.addSpacing(10)
        actions.addWidget(self.duplicate_btn)

        actions.addStretch()
        layout.addLayout(actions)

        self.setLayout(layout)
        self.canvas.optionsUpdated.connect(self.sync_from_canvas)
        self.sync_from_canvas()

    def _apply_palette_color(self, color: QColor):
        self.canvas.set_rectangle_border_color(color)
        self.sync_from_canvas()

    def _choose_color(self):
        color = QColorDialog.getColor(self.canvas.rectangle_border_color, self, "选择边框颜色")
        if color.isValid():
            self.canvas.set_rectangle_border_color(color)
            self.sync_from_canvas()

    def sync_from_canvas(self):
        color = self.canvas.rectangle_border_color
        self.color_btn.setStyleSheet(
            f"background-color: {color.name(QColor.HexArgb)}; border: 1px solid #777; padding: 6px;"
        )
        self.width_spin.blockSignals(True)
        self.width_spin.setValue(self.canvas.rectangle_border_width)
        self.width_spin.blockSignals(False)
        self.radius_spin.blockSignals(True)
        self.radius_spin.setValue(self.canvas.rectangle_corner_radius)
        self.radius_spin.blockSignals(False)
        self.duplicate_btn.setEnabled(self.canvas._has_active_rectangle())

    def _set_radius_preset(self, value: int):
        self.canvas.set_rectangle_corner_radius(value)
        self.sync_from_canvas()

class AnnotationWorkspacePage(QWidget):
    def __init__(self, open_settings_callback, style_state, style_callback):
        super().__init__()
        self._open_settings_callback = open_settings_callback
        self._style_state = style_state
        self._style_callback = style_callback
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
        tab = AnnotationTab(pixmap, save_dir, self._style_state, self._style_callback)
        label = os.path.basename(tab.auto_saved_path)
        self.tabs.addTab(tab, label)
        self.tabs.setCurrentWidget(tab)
        self._update_hint_visibility()

    def _close_tab(self, index):
        widget = self.tabs.widget(index)
        if widget:
            if hasattr(widget, "maybe_close") and not widget.maybe_close():
                return
            widget.deleteLater()
        self.tabs.removeTab(index)
        self._update_hint_visibility()

    def maybe_close_all(self):
        dirty_tabs = [
            self.tabs.widget(idx)
            for idx in range(self.tabs.count())
            if getattr(self.tabs.widget(idx), "dirty", False)
        ]
        if not dirty_tabs:
            return True
        reply = QMessageBox.question(
            self,
            "保存所有截图",
            "当前有未保存的截图，是否全部保存？",
            QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel,
        )
        if reply == QMessageBox.Cancel:
            return False
        if reply == QMessageBox.Yes:
            for tab in dirty_tabs:
                if tab and not tab.save_annotated_image():
                    return False
        return True


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
        self.marker_style = self.config.get("marker_style", DEFAULT_MARKER_STYLE.copy())
        self.rectangle_style = self.config.get("rectangle_style", DEFAULT_RECT_STYLE.copy())
        self.config.setdefault("marker_style", self.marker_style)
        self.config.setdefault("rectangle_style", self.rectangle_style)
        save_config(self.config)

        self.workspace_page = AnnotationWorkspacePage(
            lambda: self._open_settings_dialog(),
            {"marker": self.marker_style, "rectangle": self.rectangle_style},
            self._on_style_changed,
        )
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

    def _on_style_changed(self, style_type, data):
        if style_type == "marker":
            self.marker_style.update(data)
            self.config["marker_style"] = self.marker_style
        elif style_type == "rectangle":
            self.rectangle_style.update(data)
            self.config["rectangle_style"] = self.rectangle_style
        save_config(self.config)

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
        if not self.workspace_page.maybe_close_all():
            event.ignore()
            return
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
