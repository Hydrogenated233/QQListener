import asyncio
import hashlib
import json
import os
import subprocess
import sys
import threading
import time

import psutil
import uiautomation as auto
import win32api
import win32con
import win32gui
import win32process

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
    return None


def find_recent_thumb(seconds=5):
    try:
        if not os.path.exists(Thumb):
            return None

        files = [
            os.path.join(Thumb, f)
            for f in os.listdir(Thumb)
            if f.lower().endswith((".jpg", ".png"))
        ]

        if not files:
            return None

        latest = max(files, key=os.path.getmtime)

        age = time.time() - os.path.getmtime(latest)
        if age <= seconds:
            return latest

    except Exception as e:
        print(e)

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
    calling = False
    if setting.get("Blacklist", False) and any(
        k in "\n".join(texts) for k in setting.get("BlackList", [])
    ):
        return
    if setting.get("Calling", False) and any(
        k in "\n".join(texts) for k in setting.get("Calling_Keyword", [])
    ):
        temp = setting.get("Calling_Duration", 600000)
        important = True
        calling = True
    else:
        if any(p in texts[0] for p in important_persons) or any(
            k in "\n".join(texts[1:]) for k in important_keywords
        ):
            temp = setting.get("Duration_Important", 10000)
            important = True
        else:
            if setting.get("Someone_At_Me", True) and any(
                p in texts[0] for p in ["有人@我"]
            ):
                temp = setting.get("Duration_Important", 10000)
                important = True
            else:
                temp = setting.get("Duration_Everyone", 5000)
    notify["Duration"] = temp

    notify["icon_file"] = "asset/pdf.png"

    notify["Sender"] = texts[0]
    notify["Message"] = "\n".join(texts[1:])
    notify["Priority"] = 0 if important else 1
    if calling:
        notify["Calling"] = True
    else:
        notify["Calling"] = False
    # ==============================
    # 图片分支（时间戳版本）
    # ==============================
    notify.pop("Pic_Path", None)
    if "[图片]" in notify["Message"] and setting["Auto_Show_Thumb"]:
        activate_qq()

        pic_path = find_new_thumb(timeout=8)

        if pic_path:
            notify["Pic_Path"] = pic_path
    # 写入通知文件
    try:
        with open("notify.json", "w", encoding="utf-8") as f:
            json.dump(notify, f, ensure_ascii=False, indent=4)

        subprocess.Popen(["notify.exe"])

    except Exception as e:
        print(e)


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
            print("UIA异常:", e)

        await asyncio.sleep(SCAN_INTERVAL)


async def run_winsdk_mode():
    import winsdk.windows.ui.notifications as notifications
    import winsdk.windows.ui.notifications.management as mgmt

    listener = mgmt.UserNotificationListener.current
    status = await listener.request_access_async()

    if status != mgmt.UserNotificationListenerAccessStatus.ALLOWED:
        return

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
                        if n.app_info.display_info.display_name != "QQ" and setting.get(
                            "QQ_Only", True
                        ):
                            continue
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
            print("WinSDK异常:", e)

        await asyncio.sleep(0.8)


async def main():
    if UIAMODE:
        await run_uia_mode()
    else:
        await run_winsdk_mode()


# 托盘相关常量
TRAY_NOTIFY = win32con.WM_USER + 1
ID_EXIT = 1023
ID_SETTINGS = 1024  # 新增：设置


def _wnd_proc(hwnd, msg, wparam, lparam):
    if msg == TRAY_NOTIFY:
        if lparam == win32con.WM_RBUTTONUP:
            _show_menu(hwnd)
        return 0
    elif msg == win32con.WM_COMMAND:
        id = win32api.LOWORD(wparam)
        if id == ID_EXIT:
            try:
                nid = (hwnd, 0)
                win32gui.Shell_NotifyIcon(win32gui.NIM_DELETE, nid)
            except Exception:
                pass
            os._exit(0)
        elif id == ID_SETTINGS:
            try:
                if os.path.exists("maingui2.exe"):
                    # 使用 os.startfile 在 Windows 上更自然地打开 exe
                    os.startfile("maingui2.exe")
            except Exception as e:
                print(e)
        return 0
    elif msg == win32con.WM_DESTROY:
        try:
            nid = (hwnd, 0)
            win32gui.Shell_NotifyIcon(win32gui.NIM_DELETE, nid)
        except Exception:
            pass
        win32gui.PostQuitMessage(0)
        return 0
    return win32gui.DefWindowProc(hwnd, msg, wparam, lparam)


def _show_menu(hwnd):
    menu = win32gui.CreatePopupMenu()
    # 先添加 设置，再添加 退出
    win32gui.AppendMenu(menu, win32con.MF_STRING, ID_SETTINGS, "设置")
    win32gui.AppendMenu(menu, win32con.MF_STRING, ID_EXIT, "退出")
    # 必须先设置前台窗口，否则菜单位置/失焦会异常
    win32gui.SetForegroundWindow(hwnd)
    pt = win32gui.GetCursorPos()
    # TrackPopupMenu 会阻塞直到选择或取消
    win32gui.TrackPopupMenu(menu, win32con.TPM_LEFTALIGN, pt[0], pt[1], 0, hwnd, None)
    win32gui.PostMessage(hwnd, win32con.WM_NULL, 0, 0)


def tray_thread():
    hinst = win32api.GetModuleHandle(None)
    class_name = "QQListenerTrayWindow"

    wndclass = win32gui.WNDCLASS()
    wndclass.hInstance = hinst
    wndclass.lpszClassName = class_name
    wndclass.lpfnWndProc = _wnd_proc
    try:
        atom = win32gui.RegisterClass(wndclass)
    except Exception:
        atom = None

    hwnd = win32gui.CreateWindowEx(
        0,
        class_name,
        "QQListenerTray",
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        hinst,
        None,
    )

    icon_path = "icon.ico"
    try:
        hicon = win32gui.LoadImage(
            None,
            icon_path,
            win32con.IMAGE_ICON,
            0,
            0,
            win32con.LR_LOADFROMFILE | win32con.LR_DEFAULTSIZE,
        )
    except Exception:
        hicon = 0

    nid = (
        hwnd,
        0,
        win32gui.NIF_ICON | win32gui.NIF_MESSAGE | win32gui.NIF_TIP,
        TRAY_NOTIFY,
        hicon,
        "QQListener",
    )
    try:
        win32gui.Shell_NotifyIcon(win32gui.NIM_ADD, nid)
    except Exception as e:
        print("添加托盘图标失败:", e)
        return

    # 进入消息循环
    try:
        win32gui.PumpMessages()
    except Exception:
        pass


if __name__ == "__main__":
    t = threading.Thread(target=tray_thread, daemon=True)
    t.start()
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nEnd")
