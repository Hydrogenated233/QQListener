import os
import sys

from loguru import logger
from PySide6.QtCore import QTimer, QTranslator
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication, QMessageBox

from src.core.logging import setup_logging
from src.core.settings import get_settings
from src.core.signals import get_signals
from src.core.worker import NotificationWorker
from src.ui.notify_manager import get_notify_manager
from src.ui.settings_window import SettingsWindow
from src.ui.tray_icon import TrayIcon

# 懒加载pygame，避免导入即崩溃
try:
    import pygame
    _HAS_PYGAME = True
except ImportError:
    _HAS_PYGAME = False
    pygame = None


class QQListenerApp:
    def __init__(self):
        self.app: QApplication | None = None
        self.settings = get_settings()
        self.signals = get_signals()
        self.worker: NotificationWorker | None = None
        self.settings_window: SettingsWindow | None = None
        self.tray_icon: TrayIcon | None = None
        self.translator: QTranslator | None = None
        self.notify_manager = get_notify_manager()
        self._running = True

    def initialize(self) -> bool:
        setup_logging()

        if _HAS_PYGAME:
            try:
                pygame.mixer.init()
            except Exception:
                logger.exception("初始化音频失败")
        else:
            logger.warning("pygame未安装，跳过音频初始化")

        self.app = QApplication(sys.argv)
        self.app.setQuitOnLastWindowClosed(False)

        self._load_translator()

        self._connect_signals()

        self.worker = NotificationWorker()
        self.worker.notification_ready.connect(self._on_notification_ready)

        self.tray_icon = TrayIcon()
        self.tray_icon.show_settings_signal.connect(self.show_settings)
        self.tray_icon.exit_signal.connect(self.exit)

        if not self.tray_icon.create():
            logger.error("创建托盘图标失败")
            QMessageBox.warning(
                None, "QQListener",
                "系统托盘图标创建失败，程序可能在后台运行但没有可见图标。\n请重启电脑或检查系统托盘设置。"
            )
        else:
            logger.info("托盘图标创建成功")

        # 看门狗：每5秒检查 worker 线程是否还在运行
        self._watchdog = QTimer()
        self._watchdog.timeout.connect(self._watchdog_check)
        self._watchdog.start(5000)

        return True

    def _watchdog_check(self):
        """检查 worker 是否存活"""
        if self.worker and not self.worker.isRunning() and self._running:
            logger.warning("worker线程已停止，尝试重启...")
            try:
                self.worker = NotificationWorker()
                self.worker.notification_ready.connect(self._on_notification_ready)
                self.worker.start()
                logger.info("worker线程重启成功")
            except Exception:
                logger.exception("worker线程重启失败")

    def _load_translator(self):
        lang = self.settings.language
        if lang != "zh_CN" and self.app:
            self.translator = QTranslator()
            if self.translator.load(f"translations/{lang}.qm"):
                self.app.installTranslator(self.translator)

    def _connect_signals(self):
        self.signals.show_settings.connect(self.show_settings)
        self.signals.exit_app.connect(self.exit)

    def run(self):
        if not self.initialize():
            logger.error("初始化失败")
            sys.exit(1)

        # 固定弹设置窗口，确保能看到界面（诊断用）
        self.show_settings()
        if self.worker:
            self.worker.start()
        exit_code = self.app.exec() if self.app else 1
        self.cleanup()
        sys.exit(exit_code)

    def show_settings(self):
        if self.settings_window is None or not self.settings_window.isVisible():
            self.settings_window = SettingsWindow()
            if os.path.exists("icon.ico"):
                self.settings_window.setWindowIcon(QIcon("icon.ico"))
            self.settings_window.show()
        else:
            self.settings_window.raise_()
            self.settings_window.activateWindow()

    def _on_notification_ready(self, data: dict):
        self.push_notification(data)

    def push_notification(self, data: dict):
        try:
            self.notify_manager.show_notification(data)
        except Exception:
            logger.exception("推送通知失败")

    def exit(self):
        self.cleanup()
        if self.app:
            self.app.quit()

    def cleanup(self):
        self._running = False
        if self._watchdog:
            self._watchdog.stop()
        self.notify_manager.close_all_notifications()
        if self.worker and self.worker.isRunning():
            self.worker.stop()

        if self.tray_icon:
            self.tray_icon.destroy()
        if self.settings_window:
            self.settings_window.close()
            self.settings_window = None


def run_app():
    app = QQListenerApp()
    app.run()
