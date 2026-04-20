"""
Telegram Inbox Bot - Phase 1 基础版
只做 inbox 捕获,不带 Claude 对话能力
"""

import os
from datetime import datetime
from pathlib import Path
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes
from dotenv import load_dotenv

# 从同目录的 .env 读配置
load_dotenv(Path(__file__).parent / ".env")

BOT_TOKEN = os.environ["BOT_TOKEN"]
MY_USER_ID = int(os.environ["MY_USER_ID"])

BRAIN_ROOT = Path.home() / "Personal" / "brain"
INBOX = BRAIN_ROOT / "inbox"
INBOX.mkdir(parents=True, exist_ok=True)


async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # 只接受 owner 自己的消息
    if update.effective_user.id != MY_USER_ID:
        return

    msg = update.message
    if not msg:
        return

    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    content = ""
    attachments = []
    msg_type = "text"

    if msg.text:
        content = msg.text
        # 检测是不是链接
        if msg.text.strip().startswith(("http://", "https://")):
            msg_type = "link"
    elif msg.voice:
        voice_file = await msg.voice.get_file()
        audio_path = INBOX / f"{ts}-voice.ogg"
        await voice_file.download_to_drive(audio_path)
        attachments.append(audio_path.name)
        msg_type = "voice"
        content = f"[语音消息,待转录]\n时长: {msg.voice.duration}秒\n音频: {audio_path.name}"
    elif msg.photo:
        photo_file = await msg.photo[-1].get_file()
        photo_path = INBOX / f"{ts}-photo.jpg"
        await photo_file.download_to_drive(photo_path)
        attachments.append(photo_path.name)
        msg_type = "photo"
        content = f"[图片]\n文件: {photo_path.name}"
        if msg.caption:
            content += f"\n说明: {msg.caption}"
    elif msg.document:
        doc_file = await msg.document.get_file()
        safe_name = msg.document.file_name or "file"
        doc_path = INBOX / f"{ts}-{safe_name}"
        await doc_file.download_to_drive(doc_path)
        attachments.append(doc_path.name)
        msg_type = "document"
        content = f"[文件]\n{doc_path.name}"
        if msg.caption:
            content += f"\n说明: {msg.caption}"
    else:
        return

    note = INBOX / f"{ts}.md"
    frontmatter = f"""---
source: telegram
type: {msg_type}
time: {datetime.now().isoformat()}
attachments: {attachments}
status: unprocessed
---

"""
    note.write_text(frontmatter + content + "\n", encoding="utf-8")
    await msg.reply_text(f"✅ 已入库\n{note.name}")


def main():
    print(f"[Bot] 启动中... inbox: {INBOX}")
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.ALL, handle))
    app.run_polling()


if __name__ == "__main__":
    main()
