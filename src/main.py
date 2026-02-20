#!/usr/bin/env python3
"""
QQListener - QQ通知监控软件
重构版本
"""

import os
import sys

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.app import run_app

if __name__ == "__main__":
    run_app()
