import asyncio
import atexit
import hashlib
import json
import os
import subprocess
import sys
import time

import psutil
import uiautomation as auto
import win32con
import win32gui
import win32process


def on_exit():
    print("🛑 程序真的退出了")


atexit.register(on_exit)
last_thumb_set = set()

setting = json.load(open("setting.json", "r", encoding="utf-8"))
notify = json.load(open("notify.json", "r", encoding="utf-8"))

UIAMODE = setting.get("UIAMode", False)
ISWIN11 = sys.getwindowsversion().build >= 22000
SCAN_INTERVAL = 0.5
COOLDOWN = 3

seen = {}
active_toasts = set()
last_file_mtime = {}

important_persons = setting["Important_Persons"]
important_keywords = setting["Important_Keywords"]

Thumb = (
    setting["Tencent_Files_Path"]
    + "\\"
    + setting["User_QQ"]
    + "\\nt_qq\\nt_data\\Pic\\"
    + time.strftime("%Y-%m")
    + "\\Thumb"
)

print("📂 Thumb目录:", Thumb)


def find_new_thumb(timeout=setting["Max_Wait_Thumb_Time"]):
    global last_file_mtime

    start_time = time.time()

    while time.time() - start_time < timeout:
        if not os.path.exists(Thumb):
            time.sleep(0.3)
            continue

        for f in os.listdir(Thumb):
            if not f.lower().endswith((".jpg", ".png", ".webp")):
                continue

            full = os.path.join(Thumb, f)
            mtime = os.path.getmtime(full)

            # 新文件 或 被修改
            if f not in last_file_mtime or last_file_mtime[f] != mtime:
                last_file_mtime[f] = mtime
                print("🟢 检测到新/更新缩略图:", full)
                return full

        time.sleep(0.3)

    print("⚠️ 等待超时，没有新缩略图")
    return None


def find_recent_thumb(seconds=5):
    try:
        if not os.path.exists(Thumb):
            print("❌ Thumb目录不存在")
            return None

        files = [
            os.path.join(Thumb, f)
            for f in os.listdir(Thumb)
            if f.lower().endswith((".jpg", ".png"))
        ]

        if not files:
            print("⚠️ 目录里没有图片")
            return None

        latest = max(files, key=os.path.getmtime)

        age = time.time() - os.path.getmtime(latest)

        print(f"🕒 最新文件: {latest}")
        print(f"🕒 距今: {age:.2f} 秒")

        if age <= seconds:
            return latest

    except Exception as e:
        print("❌ 查找缩略图失败:", e)

    return None


# ==============================
# QQ窗口激活
# ==============================


def activate_qq():
    qq_pids = []
    for p in psutil.process_iter(["name"]):
        if p.info["name"] and "QQ.exe" in p.info["name"]:
            qq_pids.append(p.pid)

    def callback(hwnd, _):
        if not win32gui.IsWindowVisible(hwnd):
            return True

        _, pid = win32process.GetWindowThreadProcessId(hwnd)

        if pid in qq_pids:
            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
            win32gui.SetForegroundWindow(hwnd)
            print("✅ 已激活 QQ 窗口")
            return False

        return True

    win32gui.EnumWindows(callback, None)


# ==============================
# 通知处理核心
# ==============================


def process_notification(texts):
    global seen, active_toasts

    norm = [" ".join(t.split()) for t in texts]
    key = hashlib.md5("|".join(norm).encode("utf-8")).hexdigest()
    now = time.time()

    if key in active_toasts:
        return

    if key in seen and now - seen[key] < COOLDOWN:
        return

    seen[key] = now
    active_toasts.add(key)
    important = False
    if any(p in texts[0] for p in important_persons) or any(
        k in "\n".join(texts[1:]) for k in important_keywords
    ):
        temp = setting.get("Duration_Important", 10000)
        important = True
    else:
        temp = setting.get("Duration_Everyone", 5000)
    notify["Duration"] = temp

    notify["icon_ok"] = "asset/icon_ok.png"
    notify["icon_file"] = "asset/pdf.png"
    notify["icon_cancel"] = "asset/icon_cancel.png"

    notify["Sender"] = texts[0]
    notify["Message"] = "\n".join(texts[1:])
    notify["Priority"] = 0 if important else 1

    # ==============================
    # ⭐ 图片分支（时间戳版本）
    # ==============================
    notify.pop("Pic_Path", None)
    if "[图片]" in notify["Message"] and setting["Thumb"]:
        print("🟡 进入图片分支")

        activate_qq()

        pic_path = find_new_thumb(timeout=8)

        if pic_path:
            notify["Pic_Path"] = pic_path
            print("🟢 图片已捕获")
        else:
            print("⚠️ 未找到新缩略图")

    # 写入通知文件
    try:
        with open("notify.json", "w", encoding="utf-8") as f:
            json.dump(notify, f, ensure_ascii=False, indent=4)

        subprocess.Popen([sys.executable, "notify.py"])
        print(f"🔔 通知触发: {texts[0]}")

    except Exception as e:
        print("❌ 弹窗失败:", e)


# ==============================
# UIA模式
# ==============================


def get_uia_toasts():
    desktop = auto.GetRootControl()
    texts_list = []

    if not ISWIN11:
        for pane in desktop.GetChildren():
            if pane.ClassName == "Windows.UI.Core.CoreWindow":
                for win in pane.GetChildren():
                    if win.ControlTypeName == "WindowControl":
                        childs = win.GetChildren()
                        texts = [
                            c.Name
                            for c in childs
                            if c.ControlTypeName == "TextControl" and c.Name
                        ]
                        if len(texts) >= 2:
                            texts_list.append(texts)
    else:
        container = auto.WindowControl(
            searchDepth=1,
            ClassName="Windows.UI.Core.CoreWindow",
            Name="新通知",
        )
        if container.Exists(0):
            for toast, _ in auto.WalkControl(container, maxDepth=3):
                if toast.ClassName == "FlexibleToastView":
                    childs = toast.GetChildren()
                    texts = [
                        c.Name
                        for c in childs
                        if c.ControlTypeName == "TextControl"
                        and c.Name
                        and len(c.Name) > 1
                    ]
                    if len(texts) >= 2:
                        texts_list.append(texts)

    return texts_list


async def run_uia_mode():
    global active_toasts
    print("🚀 UIA 模式启动...")

    while True:
        try:
            current_found_keys = set()
            toasts = get_uia_toasts()

            for texts in toasts:
                norm = [" ".join(t.split()) for t in texts]
                key = hashlib.md5("|".join(norm).encode("utf-8")).hexdigest()
                current_found_keys.add(key)
                process_notification(texts)

            active_toasts = {k for k in active_toasts if k in current_found_keys}

        except Exception as e:
            print("⚠️ UIA异常:", e)

        await asyncio.sleep(SCAN_INTERVAL)


# ==============================
# WinSDK模式
# ==============================


async def run_winsdk_mode():
    import winsdk.windows.ui.notifications as notifications
    import winsdk.windows.ui.notifications.management as mgmt

    listener = mgmt.UserNotificationListener.current
    status = await listener.request_access_async()

    if status != mgmt.UserNotificationListenerAccessStatus.ALLOWED:
        print("❌ 没权限")
        return

    print("🚀 WinSDK 模式启动")

    known_ids = set()
    initial_notifs = await listener.get_notifications_async(
        notifications.NotificationKinds.TOAST
    )
    known_ids = {n.id for n in initial_notifs}
    while True:
        try:
            notifs = await listener.get_notifications_async(
                notifications.NotificationKinds.TOAST
            )

            current_ids = {n.id for n in notifs}

            for n in notifs:
                if n.id not in known_ids:
                    try:
                        visual = n.notification.visual
                        texts = []

                        for b in visual.bindings:
                            texts.extend(
                                [
                                    t.text.strip()
                                    for t in b.get_text_elements()
                                    if t.text
                                ]
                            )

                        if texts:
                            process_notification(texts)

                    except:
                        pass

                    known_ids.add(n.id)

            known_ids &= current_ids

        except Exception as e:
            print("⚠️ WinSDK异常:", e)

        await asyncio.sleep(0.8)


# ==============================
# 主入口
# ==============================


async def main():
    if UIAMODE:
        await run_uia_mode()
    else:
        await run_winsdk_mode()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nEnd")
