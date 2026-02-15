import os
import sys

from PySide6.QtCore import QEasingCurve, QPoint, QPropertyAnimation
from PySide6.QtGui import QFont, QFontDatabase
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

# ============================
# 🌸 主题 QSS（粉蓝二次元风）
# ============================

STYLE = """
QWidget {
    background-color: #f6f8ff;
    font-family: "CustomFont";
    font-size: 14px;
    color: #444;
}

QFrame#Card {
    background-color: white;
    border-radius: 24px;
    border: 1px solid #e5e9ff;
}

QPushButton {
    border-radius: 16px;
    padding: 10px 22px;
    background-color: #e8ecff;
}

QPushButton:hover {
    background-color: #dde4ff;
}

QPushButton#Primary {
    color: white;
    background: qlineargradient(
        x1:0, y1:0, x2:1, y2:0,
        stop:0 #ff9acb,
        stop:1 #8ec5ff
    );
}

QPushButton#Primary:hover {
    background: qlineargradient(
        x1:0, y1:0, x2:1, y2:0,
        stop:0 #ff7fbf,
        stop:1 #6fb5ff
    );
}

QLineEdit {
    border-radius: 14px;
    padding: 8px;
    background-color: #f2f4ff;
    border: 1px solid #e0e5ff;
}

QListWidget {
    border-radius: 16px;
    background-color: #f2f4ff;
    border: 1px solid #e0e5ff;
}

QListWidget::item:selected {
    background-color: #ffd6eb;
}
"""

# ============================
# ✨ 动画Stack
# ============================


class AnimatedStack(QStackedWidget):
    def slide_to(self, index):
        if index == self.currentIndex():
            return

        current = self.currentWidget()
        next_w = self.widget(index)

        direction = 1 if index > self.currentIndex() else -1
        offset = self.width() * direction

        next_w.move(offset, 0)
        next_w.show()

        anim1 = QPropertyAnimation(current, b"pos")
        anim1.setDuration(250)
        anim1.setEndValue(QPoint(-offset, 0))
        anim1.setEasingCurve(QEasingCurve.OutCubic)

        anim2 = QPropertyAnimation(next_w, b"pos")
        anim2.setDuration(250)
        anim2.setEndValue(QPoint(0, 0))
        anim2.setEasingCurve(QEasingCurve.OutCubic)

        anim1.start()
        anim2.start()

        self.setCurrentIndex(index)


# ============================
# 🌷 主窗口
# ============================


class WelcomeWindow(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowTitle(self.tr("WelcomeTitle"))  # i18n
        self.resize(820, 520)

        self.tencent_path = ""
        self.selected_qq = ""

        main = QVBoxLayout(self)
        main.setContentsMargins(50, 40, 50, 40)
        main.setSpacing(20)

        # 标题
        title = QLabel(self.tr("WelcomeHeader"))
        title.setStyleSheet("font-size:30px;font-weight:600;")
        subtitle = QLabel(self.tr("WelcomeSubtitle"))
        subtitle.setStyleSheet("color:#888;")

        main.addWidget(title)
        main.addWidget(subtitle)

        # 卡片
        card = QFrame()
        card.setObjectName("Card")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(40, 40, 40, 40)

        self.stack = AnimatedStack()
        card_layout.addWidget(self.stack)

        main.addWidget(card)

        # 底部按钮
        bottom = QHBoxLayout()
        bottom.addStretch()

        self.btn_back = QPushButton(self.tr("BackButton"))
        self.btn_next = QPushButton(self.tr("NextButton"))
        self.btn_next.setObjectName("Primary")

        self.btn_back.clicked.connect(self.go_back)
        self.btn_next.clicked.connect(self.go_next)

        bottom.addWidget(self.btn_back)
        bottom.addWidget(self.btn_next)

        main.addLayout(bottom)

        # 页面
        self.stack.addWidget(self.page_intro())
        self.stack.addWidget(self.page_path())
        self.stack.addWidget(self.page_qq())
        self.stack.addWidget(self.page_finish())

        self.update_buttons()

    # =========================
    # 页面1
    # =========================

    def page_intro(self):
        w = QWidget()
        layout = QVBoxLayout(w)

        label = QLabel(self.tr("IntroText"))
        label.setWordWrap(True)

        layout.addStretch()
        layout.addWidget(label)
        layout.addStretch()

        return w

    # =========================
    # 页面2
    # =========================

    def page_path(self):
        w = QWidget()
        layout = QVBoxLayout(w)

        self.path_label = QLabel(self.tr("NoFolderSelected"))
        self.path_label.setStyleSheet("color:#999;")

        btn = QPushButton(self.tr("SelectFolderButton"))
        btn.setObjectName("Primary")
        btn.clicked.connect(self.choose_folder)

        layout.addStretch()
        layout.addWidget(btn)
        layout.addWidget(self.path_label)
        layout.addStretch()

        return w

    def choose_folder(self):
        path = QFileDialog.getExistingDirectory(self, self.tr("SelectFolderDialog"))
        if path:
            self.tencent_path = path
            self.path_label.setText(path)

    # =========================
    # 页面3
    # =========================

    def page_qq(self):
        w = QWidget()
        layout = QVBoxLayout(w)

        self.qq_list = QListWidget()
        self.qq_input = QLineEdit()
        self.qq_input.setPlaceholderText(self.tr("ManualQQPlaceholder"))

        layout.addWidget(QLabel(self.tr("DetectedQQLabel")))
        layout.addWidget(self.qq_list)
        layout.addWidget(QLabel(self.tr("ManualQQLabel")))
        layout.addWidget(self.qq_input)

        return w

    def scan_qq(self):
        self.qq_list.clear()
        if not self.tencent_path:
            return

        for name in os.listdir(self.tencent_path):
            if name.isdigit():
                self.qq_list.addItem(QListWidgetItem(name))

    # =========================
    # 页面4
    # =========================

    def page_finish(self):
        w = QWidget()
        layout = QVBoxLayout(w)

        self.finish_label = QLabel("")
        self.finish_label.setWordWrap(True)

        layout.addStretch()
        layout.addWidget(self.finish_label)
        layout.addStretch()

        return w

    # =========================
    # 逻辑
    # =========================

    def go_next(self):
        index = self.stack.currentIndex()

        if index == 1 and not self.tencent_path:
            return

        if index == 1:
            self.scan_qq()

        if index == 2:
            selected = self.qq_list.currentItem()
            self.selected_qq = (
                selected.text() if selected else self.qq_input.text().strip()
            )

            if not self.selected_qq:
                return

            self.finish_label.setText(
                self.tr("FinishText").format(
                    path=self.tencent_path, qq=self.selected_qq
                )
            )

        if index < self.stack.count() - 1:
            self.stack.slide_to(index + 1)
        else:
            self.close()

        self.update_buttons()

    def go_back(self):
        index = self.stack.currentIndex()
        if index > 0:
            self.stack.slide_to(index - 1)
        self.update_buttons()

    def update_buttons(self):
        index = self.stack.currentIndex()
        self.btn_back.setEnabled(index != 0)
        self.btn_next.setText(
            self.tr("FinishButton")
            if index == self.stack.count() - 1
            else self.tr("NextButton")
        )


# ============================
# 🚀 启动
# ============================

if __name__ == "__main__":
    app = QApplication(sys.argv)

    # 🌸 加载字体
    font_id = QFontDatabase.addApplicationFont("fonts/YourFont.ttf")
    if font_id != -1:
        family = QFontDatabase.applicationFontFamilies(font_id)[0]
        app.setFont(QFont(family))

    app.setStyleSheet(STYLE)

    w = WelcomeWindow()
    w.show()
    sys.exit(app.exec())
