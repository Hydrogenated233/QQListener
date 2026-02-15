import json
import os
import subprocess
import sys

import pygame
from PySide6.QtCore import (
    QEasingCurve,
    QPropertyAnimation,
    Qt,
    QThread,
    QTimer,
    QUrl,
    Signal,
)
from PySide6.QtGui import QColor, QDesktopServices, QFont, QFontDatabase, QIcon, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

setting = json.load(open("setting.json", "r", encoding="utf-8"))

JSON_FILE = "notify.json"

PRIORITY_STYLES = {
    0: {
        "bg_color": "rgba(67, 53, 25, 255)",
        "text_color": "white",
        "overlay": "rgba(0, 0, 0, 120)",
    },
    1: {
        "bg_color": "rgba(43, 43, 43, 255)",
        "text_color": "white",
        "overlay": "rgba(0, 0, 0, 80)",
    },
    2: {
        "bg_color": "rgba(43, 43, 43, 255)",
        "text_color": "white",
        "overlay": "rgba(0, 0, 0, 0)",
    },
}


class FilePreview(QFrame):
    """文件附件预览控件 - 优化了交互逻辑"""

    def __init__(self, file_path, icon_path=None):
        super().__init__()
        self.file_path = file_path
        self.setFixedHeight(50)
        self.setCursor(Qt.PointingHandCursor)
        self.setStyleSheet("""
            #FileBox {
                background-color: rgba(255, 255, 255, 40);
                border-radius: 4px;
                border: 1px solid rgba(255, 255, 255, 20);
            }
            #FileBox:hover {
                background-color: rgba(255, 255, 255, 60);
            }
            QLabel { background: transparent; border: none; }
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(15, 5, 15, 5)
        self.setObjectName("FileBox")
        # 图标逻辑
        self.icon_label = QLabel()
        if icon_path and os.path.exists(icon_path):
            self.icon_label.setPixmap(
                QPixmap(icon_path).scaled(
                    24, 24, Qt.KeepAspectRatio, Qt.SmoothTransformation
                )
            )
        else:
            self.icon_label.setText("📄")
            self.icon_label.setStyleSheet("font-size: 18px; color: white;")

        # 文件名逻辑
        self.file_label = QLabel(os.path.basename(file_path))
        self.file_label.setFont(QFont("Segoe UI Variable", 11))
        self.file_label.setStyleSheet("color: white; background: transparent;")

        layout.addWidget(self.icon_label)
        layout.addWidget(self.file_label)
        layout.addStretch()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            QDesktopServices.openUrl(QUrl.fromLocalFile(self.file_path))
        super().mousePressEvent(event)


class ThumbPreview(QFrame):
    """QQ缩略图预览控件"""

    print("notify.py 启动")

    def __init__(self, file_path):
        print("当前 Pic_Path:", file_path)
        super().__init__()
        self.file_path = file_path
        self.original_pixmap = None

        self.setCursor(Qt.PointingHandCursor)
        self.setStyleSheet("""
            #ThumbBox {
                background-color: rgba(255, 255, 255, 40);
                border-radius: 4px;
                border: 1px solid rgba(255, 255, 255, 20);
            }
            QLabel { background: transparent; border: none; }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 5, 15, 5)
        self.setObjectName("ThumbBox")

        self.thumb_label = QLabel()
        self.thumb_label.setAlignment(Qt.AlignCenter)
        self.thumb_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

        if file_path and os.path.exists(file_path):
            self.original_pixmap = QPixmap(file_path)
            self.update_pixmap()

        layout.addWidget(self.thumb_label)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.update_pixmap()

    def update_pixmap(self):
        if not self.original_pixmap:
            return

        max_width = 440
        max_height = 300  # ⭐ 限制最大高度

        scaled = self.original_pixmap.scaled(
            max_width,
            max_height,
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation,
        )

        self.thumb_label.setPixmap(scaled)
        self.setFixedHeight(scaled.height() + 10)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            QDesktopServices.openUrl(QUrl.fromLocalFile(self.file_path))
        super().mousePressEvent(event)


class FluentNotifyWindow(QWidget):
    def __init__(self, data: dict):
        super().__init__()
        self.data = data
        self.duration = data.get("Duration", 5000)
        self.animations = []
        self.font_cache = {}

        def load_font(path, fallback="Segoe UI"):
            if not os.path.exists(path):
                print(f"[WARN] 字体文件不存在: {path}")
                return fallback
            font_id = QFontDatabase.addApplicationFont(path)
            if font_id != -1:
                family = QFontDatabase.applicationFontFamilies(font_id)[0]
                print(f"[INFO] 字体加载成功: {family}")
                return family
            else:
                print(f"[WARN] 字体加载失败: {path}")
                return fallback

        self.title_family = load_font(
            self.data.get(
                "Notify_Title_Font", "asset/Font/HARMONYOS_SANS_SC_REGULAR.TTF"
            )
        )
        self.msg_family = load_font(
            self.data.get(
                "Notify_Message_Font", "asset/Font/HARMONYOS_SANS_SC_REGULAR.TTF"
            )
        )

        self.init_ui()
        if setting.get("Notify_Animation", True):
            self.init_animation()
        else:
            self.setWindowOpacity(1)

    def init_ui(self):
        # 1. 基础窗口设置
        if self.data.get("Always_On_Top", True):
            self.setWindowFlags(
                Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool
            )
        else:
            self.setWindowFlags(Qt.FramelessWindowHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground, True)

        # 获取屏幕尺寸，全屏覆盖但背景透明
        screen_geo = QApplication.primaryScreen().geometry()
        self.setGeometry(screen_geo)

        style = PRIORITY_STYLES.get(self.data.get("Priority", 2))

        # 2. 遮罩层（全屏蒙版）
        if style.get("overlay"):
            self.overlay = QWidget(self)
            self.overlay.setGeometry(0, 0, self.width(), self.height())
            self.overlay.setStyleSheet(f"background-color: {style['overlay']};")

        # 3. 消息容器（动态高度）
        self.bg_widget = QWidget(self)
        self.bg_widget.setFixedWidth(500)
        self.bg_widget.setStyleSheet(f"""
            QWidget {{
                background-color: {style["bg_color"]};
                border-radius: 4px;
                border: 1px solid rgba(58, 58, 58, 255);
            }}
        """)

        self.main_layout = QVBoxLayout(self.bg_widget)
        self.main_layout.setContentsMargins(30, 30, 30, 30)
        self.main_layout.setSpacing(15)

        # 发送人
        label_sender = QLabel(f"{self.data.get('Sender', '系统通知')}")
        label_sender.setFont(
            QFont(
                self.title_family,
                18,
                QFont.Bold,
            )
        )
        label_sender.setStyleSheet(
            "color: white; border: none; background: transparent;"
        )
        self.main_layout.addWidget(label_sender)

        # 消息内容
        label_msg = QLabel(self.data.get("Message", ""))
        label_msg.setFont(self.load_font(self.msg_family, 13))

        label_msg.setStyleSheet("color: white; border: none; background: transparent;")
        label_msg.setWordWrap(True)
        # 允许内容根据文字自动延展
        label_msg.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Minimum)
        self.main_layout.addWidget(label_msg)

        file_path = self.data.get("file")
        if file_path and os.path.exists(file_path):
            self.file_preview = FilePreview(file_path, self.data.get("icon_file"))
            self.main_layout.addWidget(self.file_preview)
        elif file_path:
            print(f"[WARN] 附件路径未找到: {file_path}")

        file_path = self.data.get("Pic_Path")
        if file_path and os.path.exists(file_path):
            self.thumb_preview = ThumbPreview(file_path)
            self.main_layout.addWidget(self.thumb_preview)
        elif file_path:
            print(f"[WARN] 附件路径未找到: {file_path}")

        # 按钮组
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)

        self.btn_ok = self.create_button(
            setting.get("OK_btn", "确认"), setting.get("icon_ok")
        )
        self.btn_cancel = self.create_button(
            setting.get("Cancel_btn", "关闭"), setting.get("icon_cancel")
        )

        btn_layout.addWidget(self.btn_ok)
        btn_layout.addWidget(self.btn_cancel)
        self.main_layout.addLayout(btn_layout)
        # 提示文本
        if setting["Notify_Label"]:
            notify_label = QLabel(setting["Notify_Label"])
            notify_label.setStyleSheet(
                "font-size: 12px; color: rgba(255, 255, 255, 100); background: none; border: none;"
            )
            self.main_layout.addWidget(notify_label)
        # 让容器根据内容自动调整大小
        self.bg_widget.adjustSize()

        # 居中定位
        self.bg_widget.move(
            (self.width() - self.bg_widget.width()) // 2,
            (self.height() - self.bg_widget.height()) // 2,
        )

        self.btn_ok.clicked.connect(self.on_ok)
        self.btn_cancel.clicked.connect(self.close_animation)

    def load_font(self, path, size, weight=QFont.Normal):
        if not path or not os.path.exists(path):
            return QFont(QApplication.font().family(), size, weight)

        if path not in self.font_cache:
            font_id = QFontDatabase.addApplicationFont(path)
            if font_id != -1:
                family = QFontDatabase.applicationFontFamilies(font_id)[0]
            else:
                family = QApplication.font().family()
            self.font_cache[path] = family

        return QFont(self.font_cache[path], size, weight)

    def create_button(self, text, icon_path):
        btn = QPushButton(text)
        if icon_path and os.path.exists(icon_path):
            btn.setIcon(QIcon(icon_path))
        btn.setFixedHeight(38)
        btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 255, 255, 30);
                border: solid rgba(35, 35, 35, 255) 1px;
                color: white;
                border-radius: 4px;
                font-size: 14px;
                font-weight: 500;
                border: none;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 50);
            }
            QPushButton:pressed {
                background-color: rgba(255, 255, 255, 20);
            }
        """)
        return btn

    def init_animation(self):
        self.setWindowOpacity(0)
        # 淡入
        anim_opacity = QPropertyAnimation(self, b"windowOpacity")
        anim_opacity.setDuration(500)
        anim_opacity.setStartValue(0)
        anim_opacity.setEndValue(1)
        anim_opacity.setEasingCurve(QEasingCurve.OutExpo)
        anim_opacity.start()
        self.animations.append(anim_opacity)

        # 缩放/滑动效果
        start_pos = self.bg_widget.pos()
        self.bg_widget.move(start_pos.x(), start_pos.y() + 50)
        anim_move = QPropertyAnimation(self.bg_widget, b"pos")
        anim_move.setDuration(600)
        anim_move.setStartValue(self.bg_widget.pos())
        anim_move.setEndValue(start_pos)
        anim_move.setEasingCurve(QEasingCurve.OutBack)
        anim_move.start()
        self.animations.append(anim_move)

        # 自动关闭时钟
        if self.duration > 0:
            QTimer.singleShot(self.duration, self.close_animation)

    def close_animation(self):
        pygame.mixer.music.stop()
        anim = QPropertyAnimation(self, b"windowOpacity")
        anim.setDuration(300)
        anim.setStartValue(self.windowOpacity())
        anim.setEndValue(0)
        anim.finished.connect(self.close)
        anim.start()
        self.animations.append(anim)
        anim.finished.connect(QApplication.instance().quit)

    def override_qss(self, qss):
        with open(qss, "r", encoding="utf-8") as f:
            qss = f.read()
        self.setStyleSheet(qss)

    def on_ok(self):
        print(f"用户点击了确认: {self.data.get('Sender')}")
        self.close_animation()


class TTSThread(QThread):
    finished_signal = Signal(str)

    def __init__(self, text):
        super().__init__()
        self.text = text

    def run(self):
        try:
            OUTPUT_FILE = "tts_temp.mp3"

            VOICE = setting.get("Edge_Voice", "zh-CN-XiaoyiNeural")
            RATE = setting.get("Edge_Rate", "+0%")
            PITCH = setting.get("Edge_Pitch", "+0Hz")
            VOLUME = setting.get("Edge_Volume", "+0%")

            safe_text = self.text.replace('"', "'")

            cmd = (
                f"edge-tts "
                f'--voice "{VOICE}" '
                f'--rate "{RATE}" '
                f'--pitch "{PITCH}" '
                f'--volume "{VOLUME}" '
                f'--text "{safe_text}" '
                f'--write-media "{OUTPUT_FILE}"'
            )

            subprocess.run(cmd, shell=True, check=True)

            self.finished_signal.emit(OUTPUT_FILE)

        except Exception as e:
            print("Edge TTS 线程错误:", e)


if __name__ == "__main__":

    def play_tts():
        if not setting.get("TTS", False):
            return

        text = config_data.get("Message", "")

        if setting.get("Edge_TTS", False):
            win.tts_thread = TTSThread(text)

            def on_tts_ready(file_path):
                tts_sound = pygame.mixer.Sound(file_path)
                tts_sound.play()

            win.tts_thread.finished_signal.connect(on_tts_ready)
            win.tts_thread.start()

    app = QApplication(sys.argv)
    base_path = os.path.dirname(os.path.abspath(__file__))
    json_path = os.path.join(base_path, JSON_FILE)
    with open(json_path, "r", encoding="utf-8") as f:
        config_data = json.load(f)
    win = FluentNotifyWindow(config_data)
    if setting.get("Notify_Shadow", True):
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(50)
        shadow.setXOffset(0)
        shadow.setYOffset(0)
        shadow.setColor(QColor(0, 0, 0, 200))

        win.bg_widget.setGraphicsEffect(shadow)
    pygame.mixer.init()
    win.show()
    QTimer.singleShot(0, play_tts)
    if config_data.get("Calling"):
        pygame.mixer.music.load(setting["Sound_Calling"])
        pygame.mixer.music.play(-1)
    else:
        if config_data.get("Priority") == 0:
            pygame.mixer.music.load(setting["Sound_Effect_Important"])
        else:
            pygame.mixer.music.load(setting["Sound_Effect_Normal"])
        pygame.mixer.music.play()

    sys.exit(app.exec())
