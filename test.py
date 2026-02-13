import time

import uiautomation as auto
from PySide6.QtWidgets import QApplication, QStyleFactory

root = auto.GetRootControl()

app = QApplication([])
print(QStyleFactory.keys())


def walk(ctrl, depth=0, max_depth=5):
    if depth > max_depth:
        return
    indent = "  " * depth
    print(
        f"{indent}- {ctrl.ControlTypeName} | Name='{ctrl.Name}' | Class='{ctrl.ClassName}'"
    )

    for c in ctrl.GetChildren():
        walk(c, depth + 1, max_depth)


time.sleep(2)
walk(root)
