import os

from loguru import logger
from PySide6.QtCore import Qt, QObject, Signal
from PySide6.QtGui import QAction, QCursor, QIcon, QPixmap
from PySide6.QtWidgets import QMenu, QSystemTrayIcon

from src.core.settings import get_settings


class TrayIcon(QObject):
    """系统托盘图标管理 - Qt实现"""

    show_settings_signal = Signal()
    exit_signal = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.settings = get_settings()
        self._tray_icon: QSystemTrayIcon = None
        self._menu: QMenu = None

    def create(self) -> bool:
        """创建托盘图标"""
        try:
            # 创建托盘图标
            self._tray_icon = QSystemTrayIcon(self)
            # 加载图标，如果文件不存在则用内存图标
            if os.path.exists("icon.ico"):
                icon = QIcon("icon.ico")
            else:
                icon = QIcon()
                pm = QPixmap(16, 16)
                pm.fill(Qt.blue)
                icon.addPixmap(pm)
            self._tray_icon.setIcon(icon)
            self._tray_icon.setToolTip("QQListener")

            # 创建右键菜单
            self._menu = QMenu()

            # 设置动作
            settings_action = QAction("设置", self)
            settings_action.triggered.connect(self.show_settings_signal.emit)
            self._menu.addAction(settings_action)

            # 分隔线
            self._menu.addSeparator()

            # 退出动作
            exit_action = QAction("退出", self)
            exit_action.triggered.connect(self.exit_signal.emit)
            self._menu.addAction(exit_action)

            # 连接托盘图标激活信号
            self._tray_icon.activated.connect(self._on_activated)

            # 显示托盘图标
            self._tray_icon.show()

            return True

        except Exception:
            logger.exception("创建托盘图标失败")
            return False

    def _on_activated(self, reason):
        """托盘图标被激活时的处理"""
        # QSystemTrayIcon.Context 表示右键点击
        if reason == QSystemTrayIcon.Context:
            self._menu.popup(QCursor.pos())

    def destroy(self):
        """销毁托盘"""
        if self._tray_icon:
            self._tray_icon.hide()
            self._tray_icon = None

    def run_message_loop(self):
        """Qt实现不需要单独的消息循环，此函数保留用于兼容性"""
        pass
