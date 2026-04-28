#!/usr/bin/env python3
"""入口文件：以子进程方式启动应用，崩溃时自动重启"""

import logging
import os
import subprocess
import sys
import time
import tempfile

MODE = os.getenv("QQL_WORKER", "").strip()

if MODE == "child":
    # 子进程模式：启动实际应用
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from src.core.app import run_app
    run_app()
elif MODE == "parent" or not MODE:
    # 父进程模式：管理子进程，崩溃时自动重启
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-8s | %(message)s",
        filename=os.path.join(tempfile.gettempdir(), "QQListener_daemon.log"),
        filemode="a",
    )
    log = logging.getLogger("daemon")

    script = os.path.abspath(__file__)
    python = sys.executable
    env = os.environ.copy()
    env["QQL_WORKER"] = "child"

    max_restarts = 10
    for attempt in range(1, max_restarts + 1):
        log.info("启动子进程 (第%d次)", attempt)
        proc = subprocess.Popen([python, script], env=env)
        try:
            proc.wait()
        except KeyboardInterrupt:
            log.info("收到中断，正在退出...")
            proc.terminate()
            proc.wait(5)
            sys.exit(0)

        exit_code = proc.returncode
        log.info("子进程退出, code=%d", exit_code)
        if exit_code == 0:
            sys.exit(0)

        log.warning("子进程异常退出, 5秒后重启")
        time.sleep(5)

    log.error("子进程连续崩溃%d次, 停止重启", max_restarts)
    sys.exit(1)
