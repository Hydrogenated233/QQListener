import hashlib
import json
import os
import sys
import time

import psutil
import pygame
import uiautomation as auto
import win32con
import win32gui
import win32process
from PySide6.QtCore import (
    QEasingCurve,
    QObject,
    QProcess,
    QPropertyAnimation,
    Qt,
    QTimer,
    Signal,
)
from PySide6.QtGui import QFont, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QLabel,
    QVBoxLayout,
    QWidget,
)

# =========================
# 初始化
# =========================

setting = json.load(open("setting.json", "r", encoding="utf-8"))

pygame.mixer.init()
app = QApplication(sys.argv)

UIAMODE = setting.get("UIAMode", False)
ISWIN11 = sys.getwindowsversion().build >= 22000
SCAN_INTERVAL = 800  # 毫秒
COOLDOWN = 3

seen = {}
last_file_mtime = {}

important_persons = setting["Important_Persons"]
important_keywords = setting["Important_Keywords"]

Thumb = (
    setting["Tencent_Files_Path"]
    + "\\"
    + setting["User_QQ"]
    + "\\nt_qq\\nt_data\\Pic\\"
    + time.strftime("%Y-%m")
    + "\\Thumb"
)

# =========================
# 通知管理器
# =========================


class NotifyManager(QObject):
    show_signal = Signal(dict)

    def __init__(self):
        super().__init__()
        self.window = None
        self.show_signal.connect(self.show_notify)

    def show_notify(self, data):
        if self.window:
            self.window.close()
            self.window.deleteLater()

        self.window = FluentNotifyWindow(data)
        self.window.show()

        # 播放音效
        if data.get("Priority") == 0:
            pygame.mixer.music.load(setting["Sound_Effect_Important"])
        else:
            pygame.mixer.music.load(setting["Sound_Effect_Normal"])
        pygame.mixer.music.play()

        # TTS
        if setting.get("TTS"):
            self.run_tts(data.get("Message", ""))

    def run_tts(self, text):
        self.process = QProcess()
        OUTPUT_FILE = "tts_temp.mp3"

        cmd = [
            "edge-tts",
            "--voice",
            setting.get("Edge_Voice", "zh-CN-XiaoyiNeural"),
            "--text",
            text,
            "--write-media",
            OUTPUT_FILE,
        ]

        self.process.finished.connect(lambda: pygame.mixer.Sound(OUTPUT_FILE).play())

        self.process.start(cmd[0], cmd[1:])


notify_manager = NotifyManager()

# =========================
# QQ激活
# =========================


def activate_qq():
    qq_pids = []
    for p in psutil.process_iter(["name"]):
        if p.info["name"] and "QQ.exe" in p.info["name"]:
            qq_pids.append(p.pid)

    def callback(hwnd, _):
        if not win32gui.IsWindowVisible(hwnd):
            return True

        _, pid = win32process.GetWindowThreadProcessId(hwnd)

        if pid in qq_pids:
            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
            win32gui.SetForegroundWindow(hwnd)
            return False

        return True

    win32gui.EnumWindows(callback, None)


# =========================
# 缩略图检测
# =========================


def find_new_thumb(timeout=5):
    start_time = time.time()

    while time.time() - start_time < timeout:
        if not os.path.exists(Thumb):
            time.sleep(0.2)
            continue

        for f in os.listdir(Thumb):
            if not f.lower().endswith((".jpg", ".png", ".webp")):
                continue

            full = os.path.join(Thumb, f)
            mtime = os.path.getmtime(full)

            if f not in last_file_mtime or last_file_mtime[f] != mtime:
                last_file_mtime[f] = mtime
                return full

        time.sleep(0.2)

    return None


# =========================
# 通知处理
# =========================


def process_notification(texts):
    norm = [" ".join(t.split()) for t in texts]
    key = hashlib.md5("|".join(norm).encode("utf-8")).hexdigest()
    now = time.time()

    if key in seen and now - seen[key] < COOLDOWN:
        return

    seen[key] = now

    important = False
    if any(p in texts[0] for p in important_persons) or any(
        k in "\n".join(texts[1:]) for k in important_keywords
    ):
        duration = setting.get("Duration_Important", 10000)
        important = True
    else:
        duration = setting.get("Duration_Everyone", 5000)

    data = {
        "Sender": texts[0],
        "Message": "\n".join(texts[1:]),
        "Duration": duration,
        "Priority": 0 if important else 1,
    }

    if "[图片]" in data["Message"] and setting.get("Thumb"):
        activate_qq()
        pic_path = find_new_thumb()
        if pic_path:
            data["Pic_Path"] = pic_path

    notify_manager.show_signal.emit(data)


# =========================
# UIA模式
# =========================


def check_uia():
    try:
        desktop = auto.GetRootControl()
        for pane in desktop.GetChildren():
            if pane.ClassName == "Windows.UI.Core.CoreWindow":
                for win in pane.GetChildren():
                    childs = win.GetChildren()
                    texts = [
                        c.Name
                        for c in childs
                        if c.ControlTypeName == "TextControl" and c.Name
                    ]
                    if len(texts) >= 2:
                        process_notification(texts)
    except:
        pass


# =========================
# WinSDK模式（同步轮询）
# =========================

if not UIAMODE:
    import winsdk.windows.ui.notifications as notifications
    import winsdk.windows.ui.notifications.management as mgmt

    listener = mgmt.UserNotificationListener.current
    known_ids = set()

    listener.request_access_async()


def check_winsdk():
    global known_ids
    try:
        notifs = listener.get_notifications_async(
            notifications.NotificationKinds.TOAST
        ).get_results()

        current_ids = {n.id for n in notifs}

        for n in notifs:
            if n.id not in known_ids:
                visual = n.notification.visual
                texts = []

                for b in visual.bindings:
                    texts.extend(
                        [t.text.strip() for t in b.get_text_elements() if t.text]
                    )

                if texts:
                    process_notification(texts)

                known_ids.add(n.id)

        known_ids &= current_ids
    except Exception:
        pass


# =========================
# 通知窗口
# =========================


class FluentNotifyWindow(QWidget):
    def __init__(self, data):
        super().__init__()
        self.data = data
        self.duration = data.get("Duration", 5000)
        self.init_ui()
        self.init_animation()

    def init_ui(self):
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground, True)

        screen_geo = QApplication.primaryScreen().geometry()
        self.setGeometry(screen_geo)

        self.bg = QWidget(self)
        self.bg.setFixedWidth(500)
        self.bg.setStyleSheet("background:#2b2b2b;border-radius:6px;")

        layout = QVBoxLayout(self.bg)
        layout.setContentsMargins(30, 30, 30, 30)

        sender = QLabel(self.data.get("Sender"))
        sender.setFont(QFont("Segoe UI Variable", 18, QFont.Bold))
        sender.setStyleSheet("color:white;")
        layout.addWidget(sender)

        msg = QLabel(self.data.get("Message"))
        msg.setWordWrap(True)
        msg.setFont(QFont("Segoe UI Variable", 13))
        msg.setStyleSheet("color:white;")
        layout.addWidget(msg)

        if self.data.get("Pic_Path"):
            pic = QLabel()
            pix = QPixmap(self.data["Pic_Path"]).scaled(
                440, 300, Qt.KeepAspectRatio, Qt.SmoothTransformation
            )
            pic.setPixmap(pix)
            layout.addWidget(pic)

        self.bg.adjustSize()
        self.bg.move(
            (self.width() - self.bg.width()) // 2,
            (self.height() - self.bg.height()) // 2,
        )

    def init_animation(self):
        self.setWindowOpacity(0)
        anim = QPropertyAnimation(self, b"windowOpacity")
        anim.setDuration(400)
        anim.setStartValue(0)
        anim.setEndValue(1)
        anim.setEasingCurve(QEasingCurve.OutExpo)
        anim.start()

        QTimer.singleShot(self.duration, self.close_animation)

    def close_animation(self):
        anim = QPropertyAnimation(self, b"windowOpacity")
        anim.setDuration(300)
        anim.setStartValue(1)
        anim.setEndValue(0)
        anim.finished.connect(self.close)
        anim.start()


# =========================
# 主入口
# =========================

if __name__ == "__main__":
    timer = QTimer()

    if UIAMODE:
        timer.timeout.connect(check_uia)
    else:
        timer.timeout.connect(check_winsdk)

    timer.start(SCAN_INTERVAL)

    sys.exit(app.exec())
