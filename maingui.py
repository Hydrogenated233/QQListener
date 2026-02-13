import sys

from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class GroupMonitorGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("班级QQ群通知监控配置")
        self.resize(600, 400)

        # 主界面
        main_widget = QWidget()
        self.setCentralWidget(main_widget)

        main_layout = QHBoxLayout()
        main_widget.setLayout(main_layout)

        # 左侧：分组列表
        self.group_list = QListWidget()
        self.group_list.addItems(["班主任", "老师", "同学"])
        self.group_list.currentItemChanged.connect(self.on_group_changed)
        main_layout.addWidget(self.group_list, 1)

        # 右侧：触发词管理
        right_widget = QWidget()
        right_layout = QVBoxLayout()
        right_widget.setLayout(right_layout)
        main_layout.addWidget(right_widget, 2)

        self.label_group = QLabel("当前分组: 班主任")
        right_layout.addWidget(self.label_group)

        # 触发词列表
        self.keyword_list = QListWidget()
        right_layout.addWidget(self.keyword_list)

        # 输入框 + 添加按钮
        input_layout = QHBoxLayout()
        self.input_keyword = QLineEdit()
        self.input_keyword.setPlaceholderText("输入触发词...")
        btn_add = QPushButton("添加")
        btn_add.clicked.connect(self.add_keyword)
        input_layout.addWidget(self.input_keyword)
        input_layout.addWidget(btn_add)
        right_layout.addLayout(input_layout)

        # 删除按钮
        btn_delete = QPushButton("删除选中")
        btn_delete.clicked.connect(self.delete_keyword)
        right_layout.addWidget(btn_delete)

        # 保存/导入/导出（占位）
        btn_save = QPushButton("保存配置")
        btn_save.clicked.connect(self.save_config)
        right_layout.addWidget(btn_save)

        # 数据结构：分组对应触发词
        self.group_keywords = {"班主任": [], "老师": [], "同学": []}
        self.group_list.setCurrentRow(0)

    def on_group_changed(self, current, previous):
        if current:
            group_name = current.text()
            self.label_group.setText(f"当前分组: {group_name}")
            self.refresh_keyword_list(group_name)

    def refresh_keyword_list(self, group_name):
        self.keyword_list.clear()
        for kw in self.group_keywords.get(group_name, []):
            self.keyword_list.addItem(kw)

    def add_keyword(self):
        kw = self.input_keyword.text().strip()
        if not kw:
            return
        group_name = self.group_list.currentItem().text()
        if kw not in self.group_keywords[group_name]:
            self.group_keywords[group_name].append(kw)
            self.refresh_keyword_list(group_name)
        self.input_keyword.clear()

    def delete_keyword(self):
        group_name = self.group_list.currentItem().text()
        for item in self.keyword_list.selectedItems():
            kw = item.text()
            self.group_keywords[group_name].remove(kw)
        self.refresh_keyword_list(group_name)

    def save_config(self):
        # 这里只是占位，你可以改为写入 json/txt 文件
        QMessageBox.information(
            self, "保存配置", "配置已保存！\n" + str(self.group_keywords)
        )


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = GroupMonitorGUI()
    window.show()
    sys.exit(app.exec())
