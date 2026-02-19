import hashlib
import os
import time

from src.core.settings import get_settings


class MessageProcessor:
    """消息处理器"""

    def __init__(self) -> None:
        self.settings = get_settings()
        self.seen: dict[str, float] = {}
        self.active_toasts: set[str] = set()
        self.last_file_mtime: dict[str, float] = {}

    def process_notification(self, texts: list[str]) -> dict | None:
        """
        处理通知消息
        返回通知数据字典，如果不需要显示则返回None
        """
        if not texts or not isinstance(texts, list):
            return None

        norm = [" ".join(t.split()) for t in texts if t and isinstance(t, str)]
        if not norm:
            return None

        key = hashlib.md5("|".join(norm).encode("utf-8")).hexdigest()
        now = time.time()

        # 检查是否在活跃列表中
        if key in self.active_toasts:
            return None

        # 检查冷却时间
        cooldown = self.settings.cooldown
        if key in self.seen and now - self.seen[key] < cooldown:
            return None

        self.seen[key] = now
        self.active_toasts.add(key)

        # 检查黑名单
        message_text = "\n".join(texts)
        blacklist = self.settings.blacklist
        if blacklist and isinstance(blacklist, list) and any(k in message_text for k in blacklist if k):
            return None

        # 判断消息优先级
        important = False
        calling = False
        duration = self.settings.duration_everyone

        # 检查是否是呼叫消息
        calling_keyword = self.settings.calling_keyword
        if self.settings.calling_enabled and calling_keyword and calling_keyword in message_text:
            duration = self.settings.calling_duration
            important = True
            calling = True
        else:
            # 检查是否是重要人物或关键词
            sender = texts[0] if texts else ""
            important_persons = self.settings.important_persons
            important_keywords = self.settings.important_keywords

            is_important_person = (
                important_persons and isinstance(important_persons, list)
                and any(p in sender for p in important_persons if p)
            )
            is_important_keyword = (
                important_keywords and isinstance(important_keywords, list)
                and any(k in message_text for k in important_keywords if k)
            )
            is_at_me = self.settings.someone_at_me and "有人@我" in sender

            if is_important_person or is_important_keyword or is_at_me:
                duration = self.settings.duration_important
                important = True

        # 构建通知数据
        notify_data = {
            "Sender": texts[0] if texts else "系统通知",
            "Message": "\n".join(texts[1:]) if len(texts) > 1 else "",
            "Duration": duration,
            "Priority": 0 if important else 1,
            "Calling": calling,
            "icon_file": "asset/pdf.png",
        }

        # 处理图片
        message = notify_data.get("Message", "")
        if message and "[图片]" in message and self.settings.auto_show_thumb:
            pic_path = self._find_new_thumb(timeout=self.settings.max_wait_thumb_time)
            if pic_path:
                notify_data["Pic_Path"] = pic_path

        return notify_data

    def _find_new_thumb(self, timeout: int = 5) -> str | None:
        """查找新的缩略图"""
        thumb_path = self.settings.thumb_path
        if not thumb_path or not os.path.exists(thumb_path):
            return None

        start_time = time.time()

        while time.time() - start_time < timeout:
            try:
                files = os.listdir(thumb_path)
                if not files:
                    time.sleep(0.3)
                    continue

                for f in files:
                    if not f or not isinstance(f, str):
                        continue
                    if not f.lower().endswith((".jpg", ".png", ".webp")):
                        continue

                    full = os.path.join(thumb_path, f)
                    if not os.path.exists(full):
                        continue

                    try:
                        mtime = os.path.getmtime(full)
                    except OSError:
                        continue

                    # 新文件或被修改的文件
                    if f not in self.last_file_mtime or self.last_file_mtime[f] != mtime:
                        self.last_file_mtime[f] = mtime
                        return full
            except OSError as e:
                print(f"读取缩略图目录失败: {e}")
                return None

            time.sleep(0.3)

        return None

    def cleanup_active_toast(self, key: str) -> None:
        """清理活跃通知记录"""
        if key and isinstance(key, str):
            self.active_toasts.discard(key)

    def update_active_toasts(self, current_keys: set[str] | None) -> None:
        """更新活跃通知集合"""
        if current_keys and isinstance(current_keys, set):
            self.active_toasts = {k for k in self.active_toasts if k in current_keys}
        else:
            self.active_toasts.clear()
