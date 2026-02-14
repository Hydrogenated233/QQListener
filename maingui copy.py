import json
import os
import subprocess
import sys
import time

import pygame
import pyttsx3
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QMessageBox,
    QPushButton,
    QSlider,
    QSpinBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)
from qt_material import apply_stylesheet

SETTING_FILE = "setting.json"


# ==============================
# 主窗口
# ==============================
class SettingsWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("QQ Listener - 设置")
        self.resize(720, 600)
        self.setMinimumSize(680, 500)

        self.data = {}
        self.load_settings()
        self.init_ui()

    # ==============================
    # 加载
    # ==============================
    def load_settings(self):
        if os.path.exists(SETTING_FILE):
            with open(SETTING_FILE, "r", encoding="utf-8") as f:
                self.data = json.load(f)
        else:
            self.data = {}

    # ==============================
    # 保存
    # ==============================
    def save_settings(self):
        self.data.update(
            {
                "ScanInterval": self.scan_interval.value(),
                "Cooldown": self.cooldown.value(),
                "Tencent_Files_Path": self.tencent_path.text(),
                "User_QQ": self.user_qq.text(),
                "UIAMode": self.uia_mode.isChecked(),
                "Important_Persons": self.get_list(self.list_persons),
                "Important_Keywords": self.get_list(self.list_keywords),
                "BlackList": self.get_list(self.list_black),
                "Sound_Effect_Normal": self.sound_normal.text(),
                "Sound_Effect_Important": self.sound_important.text(),
                "Auto_Show_Thumb": self.auto_thumb.isChecked(),
                "Always_On_Top": self.always_on_top.isChecked(),
                "Max_Wait_Thumb_Time": self.max_wait.value(),
                "Duration_Everyone": self.duration_everyone.value(),
                "Duration_Important": self.duration_important.value(),
                "Theme_Setting_Combo": self.theme_setting_combo.currentText(),
            }
        )

        with open(SETTING_FILE, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=4, ensure_ascii=False)

        QMessageBox.information(self, "成功", "设置已保存")

    def get_list(self, container):
        list_widget = container.list_widget
        return [list_widget.item(i).text() for i in range(list_widget.count())]

    # ==============================
    # UI
    # ==============================
    def init_ui(self):
        layout = QVBoxLayout(self)

        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)

        self.tabs.addTab(self.create_basic_tab(), "基本")
        self.tabs.addTab(self.create_rule_tab(), "规则")
        self.tabs.addTab(self.create_appearance_tab(), "外观")
        self.tabs.addTab(self.create_notify_tab(), "通知")
        self.tabs.addTab(self.create_calling_tab(), "呼叫")
        self.tabs.addTab(self.create_sound_tab(), "声音")
        self.tabs.addTab(self.create_about_tab(), "关于")

        btn_save = QPushButton("保存设置")
        btn_test = QPushButton("测试弹窗")
        buttom_layout = QHBoxLayout()
        buttom_layout.addWidget(btn_save)
        buttom_layout.addWidget(btn_test)
        btn_save.clicked.connect(self.save_settings)
        layout.addLayout(buttom_layout)

    # ==============================
    # 基本
    # ==============================
    def create_basic_tab(self):
        widget = QWidget()
        form = QFormLayout(widget)

        self.scan_interval = QDoubleSpinBox()
        self.scan_interval.setRange(0.1, 10)
        self.scan_interval.setValue(self.data.get("ScanInterval", 0.3))

        self.cooldown = QSpinBox()
        self.cooldown.setRange(0, 60)
        self.cooldown.setValue(self.data.get("Cooldown", 3))

        self.user_qq = QLineEdit(self.data.get("User_QQ", ""))

        self.tencent_path = QLineEdit(self.data.get("Tencent_Files_Path", ""))
        btn_path = QPushButton("浏览")
        btn_path.clicked.connect(self.select_path)

        path_row = QHBoxLayout()
        path_row.addWidget(self.tencent_path)
        path_row.addWidget(btn_path)

        self.uia_mode = QCheckBox("启用 UIA 模式")
        self.uia_mode.setChecked(self.data.get("UIAMode", False))
        uia_row = QHBoxLayout()
        uia_row.addWidget(self.uia_mode)
        uia_row.addWidget(
            QLabel("UI Automation（UIA）模式识别准确率较低，性能较差，非必要勿勾选")
        )

        self.whereis_tencentfile = QLabel("我的聊天信息保存在哪里？")
        self.whereis_tencentfile.mousePressEvent = lambda event: (
            QMessageBox.information(
                self,
                "提示",
                "打开 QQ 主面板，点击左下角设置，在存储设置选项卡中显示“聊天消息默认保存到...”",
            )
        )

        self.language_combo = QComboBox()
        self.language_combo.addItems(["English", "日本語", "简体中文"])
        self.language_combo.currentIndexChanged.connect(
            lambda: self.on_language_changed(self.language_combo)
        )
        form.addRow("扫描间隔 (秒)", self.scan_interval)
        form.addRow("冷却时间 (秒)", self.cooldown)
        form.addRow("QQ 号", self.user_qq)
        form.addRow("聊天信息保存文件夹", path_row)
        form.addRow(self.whereis_tencentfile)
        form.addRow(uia_row)

        return widget

    # ==============================
    # 规则
    # ==============================
    def create_rule_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)

        layout.addWidget(QLabel("重要人物"))
        self.list_persons = self.create_list(self.data.get("Important_Persons", []))
        layout.addWidget(self.list_persons)

        layout.addWidget(QLabel("重要关键词"))
        self.list_keywords = self.create_list(self.data.get("Important_Keywords", []))
        layout.addWidget(self.list_keywords)

        layout.addWidget(QLabel("黑名单"))
        self.list_black = self.create_list(self.data.get("BlackList", []))
        layout.addWidget(self.list_black)

        self.someone_at_me = QCheckBox("当 [有人@我] 时将通知优先级设为最高")
        self.someone_at_me.setChecked(self.data.get("Someone_At_Me", True))
        layout.addWidget(self.someone_at_me)
        return widget

    # ==============================
    # 外观
    # ==============================
    def create_appearance_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)

        layout.addWidget(QLabel("设置界面主题"))
        self.theme_setting_combo = QComboBox()
        self.theme_setting_combo.addItems(
            [
                "Fusion",
                "Windows9x",
                "Windows11",
                "dark_amber.xml",
                "dark_blue.xml",
                "dark_cyan.xml",
                "dark_lightgreen.xml",
                "dark_pink.xml",
                "dark_purple.xml",
                "dark_red.xml",
                "dark_teal.xml",
                "dark_yellow.xml",
                "light_amber.xml",
                "light_blue.xml",
                "light_cyan.xml",
                "light_cyan_500.xml",
                "light_lightgreen.xml",
                "light_pink.xml",
                "light_purple.xml",
                "light_red.xml",
                "light_teal.xml",
                "light_yellow.xml",
            ]
        )
        self.theme_setting_combo.setCurrentText(
            self.data.get("Theme_Setting_Combo", "Fusion")
        )
        self.theme_setting_combo.currentIndexChanged.connect(
            lambda: self.on_setting_theme_changed(self.theme_setting_combo)
        )
        layout.addWidget(self.theme_setting_combo)
        layout.addWidget(QLabel("通知样式"))
        self.theme_notify_combo = QComboBox()
        self.theme_notify_combo.addItems(["FluentDark", "FluentLight", "Material"])
        self.theme_notify_combo.setCurrentText(
            self.data.get("Theme_Notify_Combo", "FluentDark")
        )

        self.notify_shadow = QCheckBox("通知窗口启用阴影")
        self.notify_shadow.setChecked(self.data.get("Notify_Shadow", True))
        self.notify_animation = QCheckBox("通知窗口启用动画")
        self.notify_animation.setChecked(self.data.get("Notify_Animation", True))
        self.notify_label = QLineEdit(
            self.data.get("Notify_Label", "xxtsoft QQListener")
        )
        layout.addWidget(self.notify_shadow)
        layout.addWidget(self.notify_animation)
        layout.addWidget(self.theme_notify_combo)
        layout.addWidget(QLabel("通知下方显示文本（可留空）"))
        layout.addWidget(self.notify_label)
        layout.addStretch()
        return widget

    # ==============================
    # 通知
    # ==============================
    def create_notify_tab(self):
        widget = QWidget()
        form = QFormLayout(widget)

        self.auto_thumb = QCheckBox("自动显示缩略图")
        self.auto_thumb.setChecked(self.data.get("Auto_Show_Thumb", True))

        self.always_on_top = QCheckBox("通知始终置顶")
        self.always_on_top.setChecked(self.data.get("Always_On_Top", True))

        self.max_wait = QSpinBox()
        self.max_wait.setRange(1, 20)
        self.max_wait.setValue(self.data.get("Max_Wait_Thumb_Time", 5))

        self.duration_everyone = QSpinBox()
        self.duration_everyone.setRange(1000, 20000)
        self.duration_everyone.setValue(self.data.get("Duration_Everyone", 5000))

        self.duration_important = QSpinBox()
        self.duration_important.setRange(1000, 30000)
        self.duration_important.setValue(self.data.get("Duration_Important", 10000))

        self.tts = QCheckBox("全局 TTS（语音播报） 开关")
        self.tts.setChecked(self.data.get("TTS", True))
        self.tts.checkStateChanged.connect(self.on_tts_changed)
        self.edge_tts = QCheckBox("使用新版 EdgeTTS")
        self.edge_tts.setChecked(self.data.get("Edge_TTS", True))
        self.edge_voice = QComboBox()
        self.edge_voice.setEditable(True)
        voices = [
            "zh-CN-XiaoxiaoNeural",
            "zh-CN-YunxiNeural",
            "zh-CN-YunjianNeural",
            "ja-JP-NanamiNeural",
            "ja-JP-KeitaNeural",
            "en-US-JennyNeural",
        ]

        self.edge_voice.addItems(voices)
        current_voice = self.data.get("Edge_Voice", "zh-CN-XiaoxiaoNeural")
        if current_voice not in voices:
            self.edge_voice.addItem(current_voice)
        self.edge_voice.setCurrentText(current_voice)
        self.edge_voice.setEnabled(self.edge_tts.isChecked())
        self.edge_rate = QSlider(Qt.Horizontal)
        self.edge_rate.setRange(-100, 100)

        rate_str = self.data.get("Edge_Rate", "+0%")
        rate_value = int(rate_str.replace("%", "").replace("+", ""))
        self.edge_rate.setValue(rate_value)

        self.edge_rate.setEnabled(self.edge_tts.isChecked())
        self.edge_pitch = QSlider(Qt.Horizontal)
        self.edge_pitch.setRange(-100, 100)

        pitch_str = self.data.get("Edge_Pitch", "+0Hz")
        pitch_value = int(pitch_str.replace("Hz", "").replace("+", ""))
        self.edge_pitch.setValue(pitch_value)

        self.edge_pitch.setEnabled(self.edge_tts.isChecked())

        self.edge_volume = QSlider(Qt.Horizontal)
        self.edge_volume.setRange(-100, 100)

        vol_str = self.data.get("Edge_Volume", "+0%")
        vol_value = int(vol_str.replace("%", "").replace("+", ""))
        self.edge_volume.setValue(vol_value)

        self.edge_volume.setEnabled(self.edge_tts.isChecked())

        self.edge_test_text = QLineEdit("你好呀，这里是 EdgeTTS 酱哦~")
        self.edge_test_layout = QHBoxLayout()
        self.edge_test_btn = QPushButton("试听")
        self.edge_test_btn.clicked.connect(self.on_edge_test)
        self.edge_test_layout.addWidget(self.edge_test_text)
        self.edge_test_layout.addWidget(self.edge_test_btn)

        form.addRow(self.auto_thumb)
        form.addRow(self.always_on_top)
        form.addRow("最大等待缩略图时间", self.max_wait)
        form.addRow("普通通知时长(ms)", self.duration_everyone)
        form.addRow("重要通知时长(ms)", self.duration_important)
        form.addRow(self.tts)
        form.addRow(
            self.edge_tts,
            QLabel("EdgeTTS 需要联网，但可自定义效果，若不勾选使用系统自带 TTS"),
        )
        form.addRow("EdgeTTS 音色", self.edge_voice)
        form.addRow("EdgeTTS 语速", self.edge_rate)
        form.addRow("EdgeTTS 音高", self.edge_pitch)
        form.addRow("EdgeTTS 音量", self.edge_volume)
        form.addRow("测试 TTS", self.edge_test_layout)
        return widget

    # ==============================
    # 呼叫
    # ==============================
    def create_calling_tab(self):
        widget = QWidget()
        form = QFormLayout(widget)
        self.calling = QCheckBox("允许老师呼叫")
        self.calling_keyword = QLineEdit("呼叫")
        self.calling_during = QSpinBox()
        self.calling_during.setRange(0, 999999)
        form.addRow(
            "当老师按一定格式（例如 呼叫XXX，来办公室搬下作业）呼叫，弹出窗口将持续更长时间，并且循环播放铃声直到有人响应。",
            self.calling,
        )
        form.addRow("呼叫关键词", self.calling_keyword)
        form.addRow("呼叫窗口弹出时间", self.calling_during)
        return widget

    # ==============================
    # 声音
    # ==============================
    def create_sound_tab(self):
        widget = QWidget()
        form = QFormLayout(widget)

        self.sound_normal = QLineEdit(self.data.get("Sound_Effect_Normal", ""))
        btn1 = QPushButton("浏览")
        btn1.clicked.connect(lambda: self.select_file(self.sound_normal))
        btn3 = QPushButton("试听")
        btn3.clicked.connect(lambda: self.test_file(self.sound_normal))

        row1 = QHBoxLayout()
        row1.addWidget(self.sound_normal)
        row1.addWidget(btn1)
        row1.addWidget(btn3)

        self.sound_important = QLineEdit(self.data.get("Sound_Effect_Important", ""))
        btn2 = QPushButton("浏览")
        btn2.clicked.connect(lambda: self.select_file(self.sound_important))
        btn4 = QPushButton("试听")
        btn4.clicked.connect(lambda: self.test_file(self.sound_important))

        row2 = QHBoxLayout()
        row2.addWidget(self.sound_important)
        row2.addWidget(btn2)
        row2.addWidget(btn4)

        self.sound_calling = QLineEdit(self.data.get("Sound_Calling", ""))
        btn5 = QPushButton("浏览")
        btn5.clicked.connect(lambda: self.select_file(self.sound_calling))
        btn6 = QPushButton("试听")
        btn6.clicked.connect(lambda: self.test_file(self.sound_calling))

        row3 = QHBoxLayout()
        row3.addWidget(self.sound_calling)
        row3.addWidget(btn5)
        row3.addWidget(btn6)
        form.addRow("普通提示音", row1)
        form.addRow("重要提示音", row2)
        form.addRow("呼叫提示音", row3)
        return widget

    # ==============================
    # 关于
    # ==============================
    def create_about_tab(self):
        widget = QWidget()
        form = QFormLayout(widget)

        self.title = QLabel("QQListener")
        self.title.setStyleSheet("font-size: 24px; font-weight: 600;")
        self.subtitle = QLabel("最好的QQ通知监控软件 - 班级群监控神器")
        self.subtitle.setStyleSheet("font-size: 18px")
        self.author_title = QLabel(
            "作者：株洲市南方中学 xxt8582753（https://xxtsoft.top）"
        )
        self.author_title.setStyleSheet("font-size: 18px")
        form.addRow(self.title)
        form.addRow(self.subtitle)
        form.addRow(self.author_title)

        return widget

    # ==============================
    # 列表组件
    # ==============================
    def create_list(self, items):
        container = QWidget()
        layout = QVBoxLayout(container)

        list_widget = QListWidget()
        for item in items:
            list_widget.addItem(item)

        input_line = QLineEdit()
        input_line.setPlaceholderText("输入后点击添加。也可使用回车键")
        input_line.returnPressed.connect(lambda: self.add_item(list_widget, input_line))
        btn_add = QPushButton("添加")
        btn_remove = QPushButton("删除选中")
        btn_add.clicked.connect(lambda: self.add_item(list_widget, input_line))
        btn_remove.clicked.connect(lambda: self.remove_item(list_widget))
        layout.addWidget(list_widget)
        layout.addWidget(input_line)
        btn_row = QHBoxLayout()
        btn_row.addWidget(btn_add)
        btn_row.addWidget(btn_remove)
        layout.addLayout(btn_row)
        container.list_widget = list_widget

        return container

    # ==============================
    # 文件选择
    # ==============================
    def select_path(self):
        path = QFileDialog.getExistingDirectory(self, "选择文件夹")
        if path:
            self.tencent_path.setText(path)

    def select_file(self, line):
        path, _ = QFileDialog.getOpenFileName(self, "选择文件")
        if path:
            line.setText(path)

    def test_file(self, line):
        path = line.text().strip()
        if path:
            pygame.mixer.music.load(path)
            pygame.mixer.music.play()

    def add_item(self, widget, line):
        text = line.text().strip()

        if not text:
            return
        for i in range(widget.count()):
            if widget.item(i).text() == text:
                QMessageBox.information(self, "提示", "该项已存在")
                line.clear()
                return
        widget.addItem(text)

    def remove_item(self, widget):
        selected = widget.selectedItems()
        for item in selected:
            widget.takeItem(widget.row(item))

    def on_setting_theme_changed(self, widget):
        selected = widget.currentText()
        if selected == "Fusion":
            app.setStyle("Fusion")
        elif selected == "Windows11":
            app.setStyle("windows11")
        elif selected == "Windows9x":
            app.setStyle("windows")
        else:
            apply_stylesheet(app, theme=selected)

    def on_language_changed(self, widget):
        selected = widget.currentText()
        print(selected)
        # TODO 语言切换功能（学了半年日语小李还没出机场）

    def on_edge_test(self):
        if self.edge_tts.isChecked:
            """
            self.data["Edge_Voice"] = self.edge_voice.currentText()
self.data["Edge_Rate"] = f"{self.edge_rate.value():+d}%"
self.data["Edge_Volume"] = f"{self.edge_volume.value():+d}%"
self.data["Edge_Pitch"] = f"{self.edge_pitch.value():+d}Hz"

            """
            self.edge_tts_engine(
                TEXT=self.edge_test_text.text(),
                VOICE=self.edge_voice.currentText(),
                PITCH=f"{self.edge_pitch.value():+d}Hz",
                VOLUME=f"{self.edge_volume.value():+d}%",
                RATE=f"{self.edge_rate.value():+d}%",
            )
        else:
            engine = pyttsx3.init()
            engine.setProperty(
                "voice",
                r"HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Speech\Voices\Tokens\TTS_MS_ZH-CN_HUIHUI_11.0",
            )
            engine.setProperty("volume", 1)
            engine.say(self.edge_test_text.text())
            engine.runAndWait()

    def on_tts_changed(self, state):
        current = state == Qt.Checked

        self.edge_tts.setEnabled(current)
        self.edge_pitch.setEnabled(current)
        self.edge_rate.setEnabled(current)
        self.edge_test_btn.setEnabled(current)
        self.edge_test_text.setEnabled(current)

    def edge_tts_engine(self, TEXT, VOICE, RATE, PITCH, VOLUME):
        OUTPUT_FILE = "tts_output.mp3"
        cmd = (
            f"edge-tts "
            f'--voice "{VOICE}" '
            f'--rate "{RATE}" '
            f'--pitch "{PITCH}" '
            f'--volume "{VOLUME}" '
            f'--text "{TEXT}" '
            f'--write-media "{OUTPUT_FILE}"'
        )

        subprocess.run(cmd, shell=True, check=True)
        pygame.mixer.init()
        pygame.mixer.music.load(OUTPUT_FILE)
        pygame.mixer.music.play()
        while pygame.mixer.music.get_busy():
            time.sleep(0.1)

        pygame.mixer.quit()
        print("播放完成 🎧")


if __name__ == "__main__":
    pygame.mixer.init()
    app = QApplication(sys.argv)

    win = SettingsWindow()
    selected = win.data.get("Theme_Setting_Combo")
    if selected == "Fusion":
        app.setStyle("Fusion")
    elif selected == "Windows11":
        app.setStyle("windows11")
    elif selected == "Windows9x":
        app.setStyle("windows")
    else:
        apply_stylesheet(app, theme=selected)
    win.show()
    sys.exit(app.exec())
