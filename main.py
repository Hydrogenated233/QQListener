import hashlib
import json
import os
import sys
import time

import uiautomation as auto

# watchdog 用来监控C:\Users\Administrator\Documents\Tencent Files\183xxxx529\nt_qq\nt_data\Pic\2026-02\Thumb 下的缩略图，如果发现新的缩略图就展示
# 需要注意的是，我们必须知道用户的QQ号以及当前时间

notify = json.load(open("notify.json", "r", encoding="utf-8"))
setting = json.load(open("setting.json", "r", encoding="utf-8"))
SCAN_INTERVAL = 0.3  # 扫描间隔
COOLDOWN = 3  # 冷却时间
ISWIN11 = (
    sys.getwindowsversion().build >= 22000
)  # fuck you win11, this is the WORST OS, It costs too much memory so DON'T UPDATE TO WIN11, just stay on 10 or 7 or xp or earlier
seen = {}
active_toasts = set()
important_persons = ["AbCd", "BSOD-MEMZ"]
important_keywords = ["电话", "作业", "答案"]
desktop = auto.GetRootControl()

print("🚀 Toast listener running...")
# 现在我们来拼凑路径
Thumb = (
    setting["Tencent_Files_Path"]
    + setting["User_QQ"]
    + "\\nt_qq\\nt_data\\Pic\\"
    + time.strftime("%Y-%m")
    + "\\Thumb"
)
print(Thumb)


def get_toast_texts():
    texts_list = []
    if not ISWIN11:
        try:
            for pane in desktop.GetChildren():
                # Toast 宿主
                if pane.ClassName != "Windows.UI.Core.CoreWindow":
                    continue

                # 下一层才是真正的内容窗口
                for win in pane.GetChildren():
                    if win.ControlTypeName != "WindowControl":
                        continue

                    texts = []
                    for c in win.GetChildren():
                        if c.ControlTypeName == "TextControl" and c.Name:
                            texts.append(c.Name)

                    if len(texts) >= 2:
                        texts_list.append(texts)

        except:  # noqa: E722
            pass

        return texts_list
    else:
        container = auto.WindowControl(
            searchDepth=1, ClassName="Windows.UI.Core.CoreWindow", Name="新通知"
        )
        if not container.Exists(0):
            return texts_list
        try:
            for toast, depth in auto.WalkControl(container, maxDepth=3):
                if toast.ClassName == "FlexibleToastView":
                    texts = []
                    for c in toast.GetChildren():
                        if c.ControlTypeName == "TextControl" and c.Name:
                            if len(c.Name) > 1:
                                texts.append(c.Name)
                    if len(texts) >= 2:
                        texts_list.append(texts)
        except Exception:
            pass

        return texts_list


if sys.getwindowsversion().build >= 18362:
    print(
        "由于微软安全策略限制，请手动关闭专注模式确保Toast正常弹出，按下Win+A，然后关闭专注模式即可。"
    )
else:
    import subprocess

    subprocess.run(
        'reg add "HKEY_CURRENT_USER\\Software\\Microsoft\\Windows\\CurrentVersion\\Notifications\\Settings" /v NOC_GLOBAL_SETTING_TOASTS_ENABLED /t REG_DWORD /d 1 /f',
        shell=True,
    )

while True:
    now = time.time()
    current_keys = set()

    for texts in get_toast_texts():
        # 归一化文本（去两端空格）
        norm = [" ".join(t.split()) for t in texts]
        key = hashlib.md5("|".join(norm).encode("utf-8")).hexdigest()
        current_keys.add(key)

        # 如果该 toast 还在 active_toasts 中，说明之前已经打印过且尚未消失，跳过
        if key in active_toasts:
            continue

        # 可选：短时间内重复出现也跳过（冷却）
        if key in seen and now - seen[key] < COOLDOWN:
            continue

        seen[key] = now
        active_toasts.add(key)

        temp = 0
        notify["Sender"] = texts[0]
        notify["Message"] = "\n".join(texts[1:])
        if any(p in texts[0] for p in important_persons) or any(
            k in notify["Message"] for k in important_keywords
        ):
            notify["Priority"] = 0
        else:
            notify["Priority"] = 1
        with open("notify.json", "w", encoding="utf-8") as f:
            json.dump(notify, f, ensure_ascii=False, indent=4)
        os.system("py notify.py")

    for k in list(active_toasts):
        if k not in current_keys:
            active_toasts.remove(k)

    for k, t in list(seen.items()):
        if now - t > 60:
            del seen[k]

    time.sleep(SCAN_INTERVAL)
