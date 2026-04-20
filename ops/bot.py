"""
Telegram Inbox Bot - Phase 4+ (双模 + claude-agent-sdk)

默认(捕获模式):裸文字 -> inbox,保持"静默秘书"能力
/ask <q> | @<q>      一次性问,不改模式
/chat [首句]          进入对话模式,之后裸文字都是对话
/end                  退出对话模式(10 min 静默自动退)
/note <text>          强制入库,绕过 AI
/reset                清空对话记忆(不改模式)
/status               查看 bot 状态(模式 / context / inbox 计数)
/search <kw>          搜 inbox
"""

import os
import asyncio
import shutil
from datetime import datetime, timedelta
from pathlib import Path

from telegram import Update, BotCommand
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

CLAUDE_CLI = (
    os.environ.get("CLAUDE_CLI")
    or shutil.which("claude")
    or str(Path.home() / ".local" / "bin" / "claude")
)
BRAIN_LABEL = "claude-agent-sdk"

CHAT_IDLE_TIMEOUT_S = 600
CONTEXT_HARD_RESET_PCT = 90.0

TELEGRAM_PERSONA = """你现在以 Telegram 私人助理的身份和 Kevin 对话。

- 回答简洁直接,不套话
- Telegram 单条消息 4000 字符上限,回答尽量控制在 1500 字内
- 需要引用 inbox 条目时,用 Read/Glob 直接读 ~/Personal/brain/inbox/
- 不确定的就说不确定,不编造
- 你和 Kevin 的上一轮对话会被保留,可以自然延续上下文
"""

MODE_CAPTURE = "capture"
MODE_CHAT = "chat"

_client: ClaudeSDKClient | None = None
_client_lock = asyncio.Lock()
_mode = MODE_CAPTURE
_mode_last_activity: datetime | None = None


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


async def _context_percent() -> float:
    if _client is None:
        return 0.0
    try:
        usage = await _client.get_context_usage()
        return float(usage.percentage)
    except Exception:
        return 0.0


async def ask_brain(user_question: str) -> tuple[str, bool]:
    """Returns (reply, was_auto_reset)."""
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
            reply = reply or "(空回复)"

            pct = await _context_percent()
            if pct >= CONTEXT_HARD_RESET_PCT:
                await _drop_client()
                return reply, True
            return reply, False
        except Exception as e:
            await _drop_client()
            return f"⚠️ Claude SDK 失败: {type(e).__name__}: {e}", False


def _enter_chat_mode():
    global _mode, _mode_last_activity
    _mode = MODE_CHAT
    _mode_last_activity = datetime.now()


def _exit_chat_mode():
    global _mode, _mode_last_activity
    _mode = MODE_CAPTURE
    _mode_last_activity = None


def _touch_chat_activity():
    global _mode_last_activity
    if _mode == MODE_CHAT:
        _mode_last_activity = datetime.now()


def _chat_mode_timed_out() -> bool:
    if _mode != MODE_CHAT or _mode_last_activity is None:
        return False
    return (datetime.now() - _mode_last_activity) > timedelta(seconds=CHAT_IDLE_TIMEOUT_S)


def search_inbox(query: str, limit: int = 20) -> list[tuple[str, str]]:
    q = query.lower()
    hits: list[tuple[str, str]] = []
    for md in sorted(INBOX.glob("*.md"), reverse=True):
        try:
            content = md.read_text(encoding="utf-8")
        except Exception:
            continue
        if q not in content.lower():
            continue
        preview = ""
        for line in content.splitlines():
            if q in line.lower() and not line.startswith("---"):
                preview = line.strip()
                break
        hits.append((md.name, preview))
        if len(hits) >= limit:
            break
    return hits


async def build_status() -> str:
    lines = [f"🔧 mode: `{_mode}`"]
    if _mode == MODE_CHAT and _mode_last_activity:
        age = int((datetime.now() - _mode_last_activity).total_seconds())
        remain = max(0, CHAT_IDLE_TIMEOUT_S - age)
        lines.append(f"⏳ 静默 {age}s,再 {remain}s 自动退出对话")
    lines.append(f"🧠 SDK client: {'connected' if _client else 'idle'}")
    if _client is not None:
        pct = await _context_percent()
        lines.append(f"📊 context: {pct:.1f}% (≥{CONTEXT_HARD_RESET_PCT:.0f}% 自动 reset)")
    lines.append(f"📥 inbox: {len(list(INBOX.glob('*.md')))} 条 md")
    lines.append(f"📓 journal: {len(list(JOURNAL.glob('*.md')))} 天")
    return "\n".join(lines)


async def do_ask(msg, question: str):
    thinking = await msg.reply_text("🤔 思考中...")
    reply, was_reset = await ask_brain(question)
    append_to_journal(question, reply)

    suffix = "\n\n(ℹ️ context 接近满,已自动 reset)" if was_reset else ""
    full = reply + suffix
    if len(full) > 4000:
        full = full[:3900] + "\n\n...(已截断,完整见 journal)"

    try:
        await thinking.edit_text(full)
    except Exception:
        await msg.reply_text(full)


async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != MY_USER_ID:
        return

    msg = update.message
    if not msg:
        return

    if _chat_mode_timed_out():
        _exit_chat_mode()
        try:
            await msg.reply_text("⌛ 对话模式超时,已回到捕获模式。")
        except Exception:
            pass

    if msg.text is not None:
        text = msg.text.strip()

        if text == "/reset":
            async with _client_lock:
                had = _client is not None
                await _drop_client()
            await msg.reply_text("🧹 对话记忆已清空" if had else "(本来就没连,什么也没做)")
            return

        if text == "/status":
            await msg.reply_text(await build_status())
            return

        if text.startswith("/search"):
            q = text[len("/search"):].strip()
            if not q:
                await msg.reply_text("用法:`/search <keyword>`", parse_mode="Markdown")
                return
            hits = search_inbox(q)
            if not hits:
                await msg.reply_text(f"🔍 `{q}` 没命中", parse_mode="Markdown")
                return
            header = f"🔍 `{q}` 命中 {len(hits)} 条:\n\n"
            body = "\n".join(f"• {name}\n  {prev[:80]}" for name, prev in hits)
            out = header + body
            await msg.reply_text(out[:4000])
            return

        if text.startswith("/note"):
            payload = text[len("/note"):].strip()
            if not payload:
                await msg.reply_text("用法:`/note <要入库的文字>`", parse_mode="Markdown")
                return
            note = save_to_inbox(payload, "text", [])
            await msg.reply_text(f"✅ 已入库(绕过 AI)\n{note.name}")
            return

        if text == "/end":
            if _mode == MODE_CHAT:
                _exit_chat_mode()
                await msg.reply_text("👋 已退出对话模式,回到捕获。")
            else:
                await msg.reply_text("(本来就不在对话模式)")
            return

        if text.startswith("/chat"):
            first = text[len("/chat"):].strip()
            _enter_chat_mode()
            if first:
                await do_ask(msg, first)
            else:
                await msg.reply_text(
                    f"💬 进入对话模式。之后直接发消息就是聊天。\n"
                    f"  · `/end` 退出\n"
                    f"  · `/note <文字>` 强制入库\n"
                    f"  · 静默 {CHAT_IDLE_TIMEOUT_S // 60} 分钟自动退出",
                    parse_mode="Markdown",
                )
            return

        is_ask = False
        question = ""
        if text.startswith("/ask"):
            question = text[len("/ask"):].strip()
            is_ask = bool(question)
        elif text.startswith("@"):
            question = text[1:].strip()
            is_ask = bool(question)

        if is_ask:
            await do_ask(msg, question)
            return

        if _mode == MODE_CHAT:
            _touch_chat_activity()
            await do_ask(msg, text)
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


async def post_init(app: Application):
    commands = [
        BotCommand("ask", "问 Claude(一次性,不切模式)"),
        BotCommand("chat", "进入对话模式(之后免前缀)"),
        BotCommand("end", "退出对话模式"),
        BotCommand("note", "强制入库,绕过 AI"),
        BotCommand("search", "搜 inbox 关键词"),
        BotCommand("status", "查看 bot 状态"),
        BotCommand("reset", "清空对话记忆"),
    ]
    await app.bot.set_my_commands(commands)
    print(f"[Bot] 已注册 {len(commands)} 个命令到 Telegram 菜单")


async def on_shutdown(app: Application):
    await _drop_client()


def main():
    print(f"[Bot] 启动中... 模式默认: {MODE_CAPTURE},brain: {BRAIN_LABEL}")
    print(f"[Bot] inbox: {INBOX}")
    print(f"[Bot] journal: {JOURNAL}")
    print(f"[Bot] claude CLI: {CLAUDE_CLI}")
    app = (
        Application.builder()
        .token(BOT_TOKEN)
        .post_init(post_init)
        .post_shutdown(on_shutdown)
        .build()
    )
    app.add_handler(MessageHandler(filters.ALL, handle))
    app.run_polling()


if __name__ == "__main__":
    main()
