#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
QQListener - QQ通知监控软件
重构版本入口文件
"""

import sys
import os

# 添加src目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.core.app import run_app

if __name__ == "__main__":
    run_app()
