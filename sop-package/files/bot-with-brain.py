"""
Telegram Inbox Bot - Phase 4 增强版
- 默认:只存不答(inbox 捕获)
- 前缀 /ask 或 @:调 Claude API 并回复
- 对话同时留档到 journal/YYYY-MM-DD.md
"""

import os
from datetime import datetime
from pathlib import Path
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes
from dotenv import load_dotenv
from anthropic import Anthropic

load_dotenv(Path(__file__).parent / ".env")

BOT_TOKEN = os.environ["BOT_TOKEN"]
MY_USER_ID = int(os.environ["MY_USER_ID"])
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")

BRAIN_ROOT = Path.home() / "Personal" / "brain"
INBOX = BRAIN_ROOT / "inbox"
JOURNAL = BRAIN_ROOT / "journal"
CLAUDE_MD = BRAIN_ROOT / "CLAUDE.md"

INBOX.mkdir(parents=True, exist_ok=True)
JOURNAL.mkdir(parents=True, exist_ok=True)

# Claude 客户端(没配 API key 时为 None,前缀命令会提示用户)
anthropic_client = Anthropic(api_key=ANTHROPIC_API_KEY) if ANTHROPIC_API_KEY else None

# 模型配置:Opus 最聪明但贵,日常用 Sonnet 更划算
CLAUDE_MODEL = "claude-sonnet-4-5"


# ========== 工具函数 ==========

def save_to_inbox(content: str, msg_type: str, attachments: list) -> Path:
    """写入 inbox"""
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


def append_to_journal(user_msg: str, claude_reply: str):
    """对话留档"""
    today = datetime.now().strftime("%Y-%m-%d")
    journal_file = JOURNAL / f"{today}.md"
    timestamp = datetime.now().strftime("%H:%M:%S")

    entry = f"""
## {timestamp}

**Kevin:** {user_msg}

**Claude:** {claude_reply}

---
"""
    if not journal_file.exists():
        journal_file.write_text(f"# Journal {today}\n", encoding="utf-8")

    with journal_file.open("a", encoding="utf-8") as f:
        f.write(entry)


def load_context() -> str:
    """加载 CLAUDE.md + 最近 5 个 inbox 作为对话上下文"""
    context_parts = []

    # 1. CLAUDE.md
    if CLAUDE_MD.exists():
        context_parts.append(f"# 全局上下文 (CLAUDE.md)\n\n{CLAUDE_MD.read_text(encoding='utf-8')}")

    # 2. 最近 5 个 inbox 文件
    recent_notes = sorted(INBOX.glob("*.md"), reverse=True)[:5]
    if recent_notes:
        notes_text = "\n\n".join(
            f"## {note.name}\n{note.read_text(encoding='utf-8')}"
            for note in recent_notes
        )
        context_parts.append(f"# 最近的 inbox 记录\n\n{notes_text}")

    return "\n\n---\n\n".join(context_parts)


async def ask_claude(user_question: str) -> str:
    """调 Claude API 回答"""
    if not anthropic_client:
        return "⚠️ 尚未配置 ANTHROPIC_API_KEY,请在 .env 里填入你的个人 API key。"

    context = load_context()
    system_prompt = f"""你是 Kevin 的个人 AI 助手,通过 Telegram 接收他的提问。
他正在独立创业(一人公司),角色是架构师——定方向、做决策、验收。

以下是他的个人仓库上下文:

{context}

回答规则:
- 简洁直接,不要套话
- Telegram 有消息长度限制,回答尽量控制在 1500 字以内
- 如果问题涉及 inbox 里的内容,引用具体条目
- 不确定时说不确定,不编造
"""

    try:
        response = anthropic_client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=2048,
            system=system_prompt,
            messages=[{"role": "user", "content": user_question}],
        )
        return response.content[0].text
    except Exception as e:
        return f"⚠️ Claude API 调用失败: {type(e).__name__}: {e}"


# ========== 消息路由 ==========

async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != MY_USER_ID:
        return

    msg = update.message
    if not msg:
        return

    # ---------- 分支 1:文字消息 ----------
    if msg.text:
        text = msg.text.strip()

        # 检测 /ask 或 @ 前缀
        is_ask = False
        question = ""
        if text.startswith("/ask "):
            is_ask = True
            question = text[5:].strip()
        elif text.startswith("@"):
            is_ask = True
            question = text[1:].strip()

        if is_ask and question:
            # 进入对话模式
            await msg.reply_text("🤔 思考中...")
            reply = await ask_claude(question)
            append_to_journal(question, reply)

            # Telegram 单条消息 4096 字符上限,超长截断
            if len(reply) > 4000:
                reply = reply[:3900] + "\n\n...(已截断,完整版见 journal)"

            await msg.reply_text(reply)
            return

        # 否则走 inbox 捕获
        msg_type = "link" if text.startswith(("http://", "https://")) else "text"
        note = save_to_inbox(text, msg_type, [])
        await msg.reply_text(f"✅ 已入库\n{note.name}")
        return

    # ---------- 分支 2:语音 ----------
    if msg.voice:
        ts = datetime.now().strftime("%Y%m%d-%H%M%S")
        voice_file = await msg.voice.get_file()
        audio_path = INBOX / f"{ts}-voice.ogg"
        await voice_file.download_to_drive(audio_path)
        content = f"[语音消息,待转录]\n时长: {msg.voice.duration}秒\n音频: {audio_path.name}"
        note = save_to_inbox(content, "voice", [audio_path.name])
        await msg.reply_text(f"✅ 已入库\n{note.name}")
        return

    # ---------- 分支 3:图片 ----------
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

    # ---------- 分支 4:文件 ----------
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


def main():
    mode = "with Claude brain" if anthropic_client else "inbox-only (no API key)"
    print(f"[Bot] 启动中... 模式: {mode}")
    print(f"[Bot] inbox: {INBOX}")
    print(f"[Bot] journal: {JOURNAL}")
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.ALL, handle))
    app.run_polling()


if __name__ == "__main__":
    main()
