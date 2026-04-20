"""
Telegram Inbox Bot - Phase 4 增强版(claude-agent-sdk 版)
- 默认:只存不答(inbox 捕获)
- 前缀 /ask 或 @:走 claude-agent-sdk 的持久 client,复用 Claude Code 订阅
- /reset:清空对话记忆,开新 session
- 对话同时留档到 journal/YYYY-MM-DD.md
"""

import os
import asyncio
from datetime import datetime
from pathlib import Path
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes
from dotenv import load_dotenv

from claude_agent_sdk import (
    ClaudeSDKClient,
    ClaudeAgentOptions,
    AssistantMessage,
    TextBlock,
    ResultMessage,
)

load_dotenv(Path(__file__).parent / ".env")

BOT_TOKEN = os.environ["BOT_TOKEN"]
MY_USER_ID = int(os.environ["MY_USER_ID"])

BRAIN_ROOT = Path.home() / "Personal" / "brain"
INBOX = BRAIN_ROOT / "inbox"
JOURNAL = BRAIN_ROOT / "journal"
CLAUDE_MD = BRAIN_ROOT / "CLAUDE.md"

INBOX.mkdir(parents=True, exist_ok=True)
JOURNAL.mkdir(parents=True, exist_ok=True)

CLAUDE_CLI = "/Users/admin/.local/bin/claude"
BRAIN_LABEL = "claude-agent-sdk"

TELEGRAM_PERSONA = """你现在以 Telegram 私人助理的身份和 Kevin 对话。

- 回答简洁直接,不套话
- Telegram 单条消息 4000 字符上限,回答尽量控制在 1500 字内
- 需要引用 inbox 条目时,用 Read/Glob 直接读 ~/Personal/brain/inbox/
- 不确定的就说不确定,不编造
- 你和 Kevin 的上一轮对话会被保留,可以自然延续上下文
"""

_client: ClaudeSDKClient | None = None
_client_lock = asyncio.Lock()


def save_to_inbox(content: str, msg_type: str, attachments: list) -> Path:
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
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
    return note


def append_to_journal(user_msg: str, reply: str):
    today = datetime.now().strftime("%Y-%m-%d")
    journal_file = JOURNAL / f"{today}.md"
    timestamp = datetime.now().strftime("%H:%M:%S")

    entry = f"""
## {timestamp}

**Kevin:** {user_msg}

**AI ({BRAIN_LABEL}):** {reply}

---
"""
    if not journal_file.exists():
        journal_file.write_text(f"# Journal {today}\n", encoding="utf-8")

    with journal_file.open("a", encoding="utf-8") as f:
        f.write(entry)


async def _ensure_client() -> ClaudeSDKClient:
    global _client
    if _client is None:
        options = ClaudeAgentOptions(
            system_prompt={
                "type": "preset",
                "preset": "claude_code",
                "append": TELEGRAM_PERSONA,
            },
            permission_mode="bypassPermissions",
            cwd=str(BRAIN_ROOT),
            cli_path=CLAUDE_CLI,
        )
        client = ClaudeSDKClient(options=options)
        await client.connect()
        _client = client
        print("[Bot] claude SDK client connected")
    return _client


async def _drop_client():
    global _client
    if _client is not None:
        try:
            await _client.disconnect()
        except Exception as e:
            print(f"[Bot] disconnect 时报错(忽略): {e}")
        _client = None


async def ask_brain(user_question: str) -> str:
    async with _client_lock:
        try:
            client = await _ensure_client()
            await client.query(user_question)

            reply_parts: list[str] = []
            async for msg in client.receive_response():
                if isinstance(msg, AssistantMessage):
                    for block in msg.content:
                        if isinstance(block, TextBlock):
                            reply_parts.append(block.text)
                elif isinstance(msg, ResultMessage):
                    break

            reply = "\n".join(p for p in reply_parts if p).strip()
            return reply or "(空回复)"
        except Exception as e:
            await _drop_client()
            return f"⚠️ Claude SDK 失败: {type(e).__name__}: {e}"


async def reset_brain() -> str:
    async with _client_lock:
        had_client = _client is not None
        await _drop_client()
    return "🧹 对话记忆已清空" if had_client else "(本来就没连,什么也没做)"


async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != MY_USER_ID:
        return

    msg = update.message
    if not msg:
        return

    if msg.text:
        text = msg.text.strip()

        if text == "/reset":
            reply = await reset_brain()
            await msg.reply_text(reply)
            return

        is_ask = False
        question = ""
        if text.startswith("/ask "):
            is_ask = True
            question = text[5:].strip()
        elif text.startswith("@"):
            is_ask = True
            question = text[1:].strip()

        if is_ask and question:
            thinking_msg = await msg.reply_text("🤔 思考中...")
            reply = await ask_brain(question)
            append_to_journal(question, reply)

            if len(reply) > 4000:
                reply = reply[:3900] + "\n\n...(已截断,完整版见 journal)"

            try:
                await thinking_msg.edit_text(reply)
            except Exception:
                await msg.reply_text(reply)
            return

        msg_type = "link" if text.startswith(("http://", "https://")) else "text"
        note = save_to_inbox(text, msg_type, [])
        await msg.reply_text(f"✅ 已入库\n{note.name}")
        return

    if msg.voice:
        ts = datetime.now().strftime("%Y%m%d-%H%M%S")
        voice_file = await msg.voice.get_file()
        audio_path = INBOX / f"{ts}-voice.ogg"
        await voice_file.download_to_drive(audio_path)
        content = f"[语音消息,待转录]\n时长: {msg.voice.duration}秒\n音频: {audio_path.name}"
        note = save_to_inbox(content, "voice", [audio_path.name])
        await msg.reply_text(f"✅ 已入库\n{note.name}")
        return

    if msg.photo:
        ts = datetime.now().strftime("%Y%m%d-%H%M%S")
        photo_file = await msg.photo[-1].get_file()
        photo_path = INBOX / f"{ts}-photo.jpg"
        await photo_file.download_to_drive(photo_path)
        content = f"[图片]\n文件: {photo_path.name}"
        if msg.caption:
            content += f"\n说明: {msg.caption}"
        note = save_to_inbox(content, "photo", [photo_path.name])
        await msg.reply_text(f"✅ 已入库\n{note.name}")
        return

    if msg.document:
        ts = datetime.now().strftime("%Y%m%d-%H%M%S")
        doc_file = await msg.document.get_file()
        safe_name = msg.document.file_name or "file"
        doc_path = INBOX / f"{ts}-{safe_name}"
        await doc_file.download_to_drive(doc_path)
        content = f"[文件]\n{doc_path.name}"
        if msg.caption:
            content += f"\n说明: {msg.caption}"
        note = save_to_inbox(content, "document", [doc_path.name])
        await msg.reply_text(f"✅ 已入库\n{note.name}")
        return


async def on_shutdown(app: Application):
    await _drop_client()


def main():
    print(f"[Bot] 启动中... 模式: {BRAIN_LABEL}")
    print(f"[Bot] inbox: {INBOX}")
    print(f"[Bot] journal: {JOURNAL}")
    print(f"[Bot] claude CLI: {CLAUDE_CLI}")
    app = (
        Application.builder()
        .token(BOT_TOKEN)
        .post_shutdown(on_shutdown)
        .build()
    )
    app.add_handler(MessageHandler(filters.ALL, handle))
    app.run_polling()


if __name__ == "__main__":
    main()
