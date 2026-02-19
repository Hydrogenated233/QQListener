from PySide6.QtCore import QObject, Signal


class AppSignals(QObject):
    """应用程序全局信号"""

    # 通知信号
    show_notification = Signal(dict)

    # 设置相关信号
    settings_changed = Signal()
    show_settings = Signal()

    # 托盘相关信号
    tray_icon_activated = Signal()
    exit_app = Signal()

    # 消息处理信号
    message_received = Signal(dict)


# 全局信号实例
app_signals = AppSignals()


def get_signals() -> AppSignals:
    """获取全局信号实例"""
    return app_signals
