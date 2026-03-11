import sys

import pygame
from loguru import logger
from PySide6.QtCore import QTranslator
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication, QMessageBox

from src.core.logging import setup_logging
from src.core.settings import get_settings
from src.core.signals import get_signals
from src.core.worker import NotificationWorker
from src.ui.notify_manager import get_notify_manager
from src.ui.settings_window import SettingsWindow
from src.ui.tray_icon import TrayIcon


class QQListenerApp:
    """QQListener应用程序主类 - 单进程架构"""

    def __init__(self):
        self.app: QApplication | None = None
        self.settings = get_settings()
        self.signals = get_signals()
        self.worker: NotificationWorker | None = None
        self.settings_window: SettingsWindow | None = None
        self.tray_icon: TrayIcon | None = None
        self.translator: QTranslator | None = None
        self.notify_manager = get_notify_manager()

    def initialize(self) -> bool:
        """初始化应用程序"""
        setup_logging()

        # 初始化pygame混音器
        try:
            pygame.mixer.init()
        except Exception:
            logger.exception("初始化音频失败")

        # 创建Qt应用
        self.app = QApplication(sys.argv)
        self.app.setQuitOnLastWindowClosed(False)

        # 加载翻译
        self._load_translator()

        # 连接信号
        self._connect_signals()

        # 创建工作线程
        self.worker = NotificationWorker()
        self.worker.notification_ready.connect(self._on_notification_ready)

        # 创建托盘图标 (Qt实现，不需要单独线程)
        self.tray_icon = TrayIcon()
        self.tray_icon.show_settings_signal.connect(self.show_settings)
        self.tray_icon.exit_signal.connect(self.exit)

        if not self.tray_icon.create():
            logger.error("创建托盘图标失败")

        return True

    def _load_translator(self):
        """加载翻译文件"""
        lang = self.settings.language
        if lang != "zh_CN" and self.app:
            self.translator = QTranslator()
            if self.translator.load(f"translations/{lang}.qm"):
                self.app.installTranslator(self.translator)

    def _connect_signals(self):
        """连接信号槽"""
        self.signals.show_settings.connect(self.show_settings)
        self.signals.exit_app.connect(self.exit)

    def run(self):
        """运行应用程序"""
        if not self.initialize():
            logger.error("初始化失败")
            sys.exit(1)

        # 如果是首次运行，显示设置窗口
        if self.settings.is_first_run():
            if self.settings_window is None:
                self.settings_window = SettingsWindow()
            QMessageBox.information(
                self.settings_window,
                self.settings_window.tr("你是新来的吧？"),
                self.settings_window.tr(
                    '这个程序配置较为复杂，所以建议你先看了教程再来用喵~\n请点击"关于"选项卡并点击"查看教程"按钮\n第一次保存设置后这条消息将不再出现\n\n\n本程序免费开源，如果你是花钱买的那一定是被骗了！'
                ),
            )
            self.show_settings()

        # 启动工作线程
        if self.worker:
            self.worker.start()

        # 运行Qt事件循环
        exit_code = self.app.exec() if self.app else 1

        # 清理
        self.cleanup()

        sys.exit(exit_code)

    def show_settings(self):
        """显示设置窗口"""
        if self.settings_window is None or not self.settings_window.isVisible():
            self.settings_window = SettingsWindow()
            self.settings_window.setWindowIcon(QIcon("icon.ico"))
            self.settings_window.show()
        else:
            self.settings_window.raise_()
            self.settings_window.activateWindow()

    def _on_notification_ready(self, data: dict):
        """处理通知就绪信号 - 在同一进程中显示通知"""
        self.push_notification(data)

    def push_notification(self, data: dict):
        """推送通知 - 使用通知管理器在同一进程中创建窗口"""
        try:
            self.notify_manager.show_notification(data)
        except Exception:
            logger.exception("推送通知失败")

    def exit(self):
        """退出应用程序"""
        self.cleanup()
        if self.app:
            self.app.quit()

    def cleanup(self):
        """清理资源"""
        # 关闭所有通知窗口
        self.notify_manager.close_all_notifications()

        # 停止工作线程
        if self.worker and self.worker.isRunning():
            self.worker.stop()

        # 销毁托盘图标
        if self.tray_icon:
            self.tray_icon.destroy()

        # 关闭设置窗口
        if self.settings_window:
            self.settings_window.close()
            self.settings_window = None


def run_app():
    """应用程序入口"""
    app = QQListenerApp()
    app.run()
