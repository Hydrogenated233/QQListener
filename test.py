import time  # noqa: F401

import pyttsx3
import uiautomation as auto

root = auto.GetRootControl()


engine = pyttsx3.init()
voices = engine.getProperty("voices")

for i, v in enumerate(voices):
    print(i, "\n", v.id, "\n", v.name, "\n")
    engine.setProperty(
        "voice",
        r"HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Speech\Voices\Tokens\TTS_MS_JA-JP_HARUKA_11.0",
    )
    engine.setProperty("volume", 1)
    engine.say("私のオナニーお見でください")
    engine.runAndWait()

"""
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
"""
