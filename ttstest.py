import subprocess
import time

import pygame

TEXT = "你好，这是 Edge 神经语音的测试示例。"

VOICE = "zh-CN-XiaoyiNeural"
RATE = "+0%"
PITCH = "+10Hz"
VOLUME = "+0%"

OUTPUT_FILE = "tts_output.mp3"

# 1️⃣ 调用 edge-tts 生成语音（通过命令行）
cmd = (
    f"edge-tts "
    f'--voice "{VOICE}" '
    f'--rate "{RATE}" '
    f'--pitch "{PITCH}" '
    f'--volume "{VOLUME}" '
    f'--text "{TEXT}" '
    f'--write-media "{OUTPUT_FILE}"'
)

subprocess.run(cmd, shell=True, check=True)

# 2️⃣ 用 pygame 播放
pygame.mixer.init()
pygame.mixer.music.load(OUTPUT_FILE)
pygame.mixer.music.play()

# 等待播放完成
while pygame.mixer.music.get_busy():
    time.sleep(0.1)

pygame.mixer.quit()

# 可选：播放后删除文件
# os.remove(OUTPUT_FILE)

print("播放完成 🎧")
