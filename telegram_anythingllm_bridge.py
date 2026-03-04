#!/usr/bin/env python3
"""
Telegram ↔ AnythingLLM Bridge

A thin bridge that polls Telegram for messages and forwards them directly
to an AnythingLLM workspace agent, then sends the response back.

No nanobot agent loop in the middle — just a dumb pipe with markdown conversion.

Usage:
    export TELEGRAM_BOT_TOKEN="..."
    export ANYTHINGLLM_API_KEY="..."
    export ANYTHINGLLM_BASE_URL="http://localhost:3001"   # optional
    export ANYTHINGLLM_WORKSPACE="your-workspace-slug"    # optional, default: "nanobot"
    export ALLOWED_USER_IDS="*"                           # optional, * = allow all
    export AGENT_PREFIX="true"                            # optional, enable @agent prefix
    export AGENT_FOR_TEXT="true"                          # optional, use @agent for text messages
    export AGENT_FOR_IMAGES="false"                       # optional, use @agent for image messages
    python scripts/telegram_anythingllm_bridge.py
"""

from __future__ import annotations

import asyncio
import base64
import os
import re
import sys
import tempfile
import mimetypes
from pathlib import Path

import httpx
from PIL import Image
from telegram import BotCommand, ReplyParameters, Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)
from telegram.request import HTTPXRequest

# ---------------------------------------------------------------------------
# Config from environment
# ---------------------------------------------------------------------------

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
ALLM_BASE_URL = os.environ.get("ANYTHINGLLM_BASE_URL", "http://localhost:3001").rstrip("/")
ALLM_API_KEY = os.environ.get("ANYTHINGLLM_API_KEY", "")
ALLM_WORKSPACE = os.environ.get("ANYTHINGLLM_WORKSPACE", "nanobot")
ALLOWED_IDS = os.environ.get("ALLOWED_USER_IDS", "*")  # comma-separated or "*"

# Agent mode configuration
AGENT_PREFIX = os.environ.get("AGENT_PREFIX", "true").lower() in ("1", "true", "yes")
AGENT_FOR_IMAGES = os.environ.get("AGENT_FOR_IMAGES", "false").lower() in ("1", "true", "yes")
AGENT_FOR_TEXT = os.environ.get("AGENT_FOR_TEXT", "true").lower() in ("1", "true", "yes")

# Per-chat thread tracking: chat_id -> AnythingLLM threadSlug
_chat_threads: dict[int, str | None] = {}

# Typing indicator tasks: chat_id -> Task
_typing_tasks: dict[int, asyncio.Task] = {}


# ---------------------------------------------------------------------------
# Markdown → Telegram HTML  (recycled from nanobot)
# ---------------------------------------------------------------------------

def _md_to_tg_html(text: str) -> str:
    if not text:
        return ""

    code_blocks: list[str] = []
    def _save_cb(m: re.Match) -> str:
        code_blocks.append(m.group(1))
        return f"\x00CB{len(code_blocks) - 1}\x00"
    text = re.sub(r"```[\w]*\n?([\s\S]*?)```", _save_cb, text)

    inline_codes: list[str] = []
    def _save_ic(m: re.Match) -> str:
        inline_codes.append(m.group(1))
        return f"\x00IC{len(inline_codes) - 1}\x00"
    text = re.sub(r"`([^`]+)`", _save_ic, text)

    text = re.sub(r"^#{1,6}\s+(.+)$", r"\1", text, flags=re.MULTILINE)
    text = re.sub(r"^>\s*(.*)$", r"\1", text, flags=re.MULTILINE)
    text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', text)
    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
    text = re.sub(r"__(.+?)__", r"<b>\1</b>", text)
    text = re.sub(r"(?<![a-zA-Z0-9])_([^_]+)_(?![a-zA-Z0-9])", r"<i>\1</i>", text)
    text = re.sub(r"~~(.+?)~~", r"<s>\1</s>", text)
    text = re.sub(r"^[-*]\s+", "• ", text, flags=re.MULTILINE)

    for i, code in enumerate(inline_codes):
        esc = code.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        text = text.replace(f"\x00IC{i}\x00", f"<code>{esc}</code>")
    for i, code in enumerate(code_blocks):
        esc = code.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        text = text.replace(f"\x00CB{i}\x00", f"<pre><code>{esc}</code></pre>")

    return text


def _split_message(content: str, max_len: int = 4000) -> list[str]:
    if len(content) <= max_len:
        return [content]
    chunks: list[str] = []
    while content:
        if len(content) <= max_len:
            chunks.append(content)
            break
        cut = content[:max_len]
        pos = cut.rfind("\n")
        if pos == -1:
            pos = cut.rfind(" ")
        if pos == -1:
            pos = max_len
        chunks.append(content[:pos])
        content = content[pos:].lstrip()
    return chunks


# ---------------------------------------------------------------------------
# ACL
# ---------------------------------------------------------------------------

def _is_allowed(user) -> bool:
    if ALLOWED_IDS.strip() == "*":
        return True
    allowed = {s.strip() for s in ALLOWED_IDS.split(",") if s.strip()}
    return str(user.id) in allowed or (user.username and user.username in allowed)


# ---------------------------------------------------------------------------
# Typing indicator
# ---------------------------------------------------------------------------

async def _typing_loop(bot, chat_id: int) -> None:
    try:
        while True:
            await bot.send_chat_action(chat_id=chat_id, action="typing")
            await asyncio.sleep(4)
    except asyncio.CancelledError:
        pass
    except Exception:
        pass


def _start_typing(bot, chat_id: int) -> None:
    _stop_typing(chat_id)
    _typing_tasks[chat_id] = asyncio.create_task(_typing_loop(bot, chat_id))


def _stop_typing(chat_id: int) -> None:
    task = _typing_tasks.pop(chat_id, None)
    if task and not task.done():
        task.cancel()


# ---------------------------------------------------------------------------
# Media processing helpers
# ---------------------------------------------------------------------------

async def _download_file(file, filename_prefix: str = "media") -> Path:
    """Download a Telegram file to a temporary location."""
    temp_dir = Path(tempfile.gettempdir()) / "anythingllm_bridge"
    temp_dir.mkdir(exist_ok=True)
    
    file_extension = Path(file.file_path).suffix if file.file_path else ""
    temp_file = temp_dir / f"{filename_prefix}_{file.file_unique_id}{file_extension}"
    
    await file.download_to_drive(temp_file)
    return temp_file


async def _process_image(image_path: Path) -> str:
    """Process an image and return description for AnythingLLM."""
    try:
        with Image.open(image_path) as img:
            width, height = img.size
            format_name = img.format or "Unknown"
            
        file_size = image_path.stat().st_size
        return f"[Image: {format_name} {width}x{height}, {file_size//1024}KB - uploaded to workspace]"
    except Exception as e:
        return f"[Image uploaded - processing error: {e}]"


async def _create_image_attachment(file_path: Path) -> dict:
    """Create an attachment object for AnythingLLM chat from an image file."""
    try:
        # Read and encode image as base64
        with open(file_path, 'rb') as f:
            image_data = f.read()
            base64_image = base64.b64encode(image_data).decode('utf-8')
        
        # Determine mime type
        mime_type = mimetypes.guess_type(str(file_path))[0] or 'image/png'
        
        # Create attachment in the format AnythingLLM expects
        attachment = {
            "type": "image",
            "data": f"data:{mime_type};base64,{base64_image}",
            "name": file_path.name
        }
        
        return {"attachment": attachment}
        
    except Exception as e:
        return {"error": f"Failed to create attachment: {e}"}


async def _cleanup_temp_file(file_path: Path) -> None:
    """Clean up temporary file."""
    try:
        if file_path.exists():
            file_path.unlink()
    except Exception as e:
        print(f"[WARN] Failed to cleanup {file_path}: {e}", file=sys.stderr)


# ---------------------------------------------------------------------------
# AnythingLLM API
# ---------------------------------------------------------------------------

_http = httpx.AsyncClient(
    headers={
        "Authorization": f"Bearer {ALLM_API_KEY}",
        "Content-Type": "application/json",
    },
    timeout=120.0,
)


async def _chat_anythingllm(message: str, chat_id: int, mode: str = "chat", attachments: list = None) -> str:
    """Send a message to AnythingLLM and return the text response."""
    body: dict = {"message": message, "mode": mode}

    # Add attachments if provided
    if attachments:
        body["attachments"] = attachments

    # Reuse thread if we have one for this chat
    thread_slug = _chat_threads.get(chat_id)
    if thread_slug:
        body["threadSlug"] = thread_slug

    # Smart @agent prefix logic:
    # - For images: use @agent only if AGENT_FOR_IMAGES is enabled
    # - For text: use @agent only if AGENT_FOR_TEXT is enabled
    # - Overall controlled by AGENT_PREFIX master switch
    if AGENT_PREFIX:
        if attachments and AGENT_FOR_IMAGES:
            body["message"] = f"@agent {message}"
        elif not attachments and AGENT_FOR_TEXT:
            body["message"] = f"@agent {message}"

    try:
        url = f"{ALLM_BASE_URL}/api/v1/workspace/{ALLM_WORKSPACE}/chat"
        resp = await _http.post(url, json=body)

        if not resp.is_success:
            err = resp.text[:300]
            return f"⚠️ AnythingLLM error ({resp.status_code}): {err}"

        data = resp.json()

        # Capture threadSlug for session continuity
        if "threadSlug" in data and data["threadSlug"]:
            _chat_threads[chat_id] = data["threadSlug"]

        # Extract response text
        for key in ("textResponse", "response", "content"):
            if key in data and data[key]:
                return data[key]

        return str(data)

    except httpx.TimeoutException:
        return "⚠️ AnythingLLM request timed out."
    except Exception as e:
        return f"⚠️ Failed to reach AnythingLLM: {e}"


# ---------------------------------------------------------------------------
# Telegram send helper
# ---------------------------------------------------------------------------

async def _send_reply(bot, chat_id: int, text: str, reply_to: int | None = None) -> None:
    reply_params = None
    if reply_to:
        reply_params = ReplyParameters(message_id=reply_to, allow_sending_without_reply=True)

    for chunk in _split_message(text):
        try:
            html = _md_to_tg_html(chunk)
            await bot.send_message(
                chat_id=chat_id, text=html, parse_mode="HTML",
                reply_parameters=reply_params,
            )
        except Exception:
            # Fallback to plain text
            try:
                await bot.send_message(
                    chat_id=chat_id, text=chunk,
                    reply_parameters=reply_params,
                )
            except Exception as e:
                print(f"[ERROR] send failed: {e}", file=sys.stderr)


# ---------------------------------------------------------------------------
# Handlers
# ---------------------------------------------------------------------------

async def _on_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.effective_user:
        return
    name = update.effective_user.first_name
    await update.message.reply_text(
        f"👋 Hi {name}! I'm connected to AnythingLLM workspace '{ALLM_WORKSPACE}'.\n\n"
        "💬 Send me text messages and I'll forward them to the agent.\n"
        "📷 Send photos and I'll analyze them with vision AI.\n"
        "🎵 Audio/voice: coming soon\n"
        "📄 Documents: coming soon\n\n"
        "/new — reset conversation thread\n"
        "/help — show this message"
    )


async def _on_help(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message:
        return
    await update.message.reply_text(
        f"🔗 AnythingLLM Bridge → workspace '{ALLM_WORKSPACE}'\n\n"
        "💬 Text messages - forwarded to agent\n"
        "📷 Photos - analyzed with vision AI\n" 
        "🎵 Audio/Voice - coming soon\n"
        "📄 Documents - coming soon\n\n"
        "/new — start a new conversation thread\n"
        "/help — show this message"
    )


async def _on_new(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message:
        return
    chat_id = update.message.chat_id
    _chat_threads.pop(chat_id, None)
    await update.message.reply_text("🔄 Conversation reset. Next message starts a fresh thread.")


async def _on_message(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.effective_user:
        return

    user = update.effective_user
    message = update.message
    chat_id = message.chat_id

    if not _is_allowed(user):
        await message.reply_text("⛔ Access denied. Your user ID is not in the allow list.")
        return

    # Build content
    content_parts = []
    if message.text:
        content_parts.append(message.text)
    if message.caption:
        content_parts.append(message.caption)

    # Handle media files - prepare attachments
    temp_files = []  # Track temp files for cleanup
    attachments = []  # Track attachments for chat
    
    try:
        # Handle photos
        if message.photo:
            photo_file = await message.photo[-1].get_file()  # Get highest resolution
            temp_path = await _download_file(photo_file, "photo")
            temp_files.append(temp_path)
            
            # Create attachment for AnythingLLM
            attachment_result = await _create_image_attachment(temp_path)
            if "error" in attachment_result:
                content_parts.append(f"⚠️ Photo processing failed: {attachment_result['error']}")
            else:
                attachments.append(attachment_result["attachment"])
                image_description = await _process_image(temp_path)
                content_parts.append(image_description)
        
        # Note: Audio/voice/document uploads not supported yet with chat attachments
        # Only images are supported in the current AnythingLLM chat attachment format
        if message.voice:
            content_parts.append("🎵 Voice message received (audio processing not yet implemented)")
                
        if message.audio:
            title = getattr(message.audio, 'title', 'Unknown')
            content_parts.append(f"🎵 Audio file '{title}' received (audio processing not yet implemented)")
        
        if message.document:
            content_parts.append(f"📄 Document '{message.document.file_name}' received (document processing not yet implemented)")
                
    except Exception as e:
        content_parts.append(f"⚠️ Media processing error: {e}")
        print(f"[ERROR] Media processing failed: {e}", file=sys.stderr)

    content = "\n".join(content_parts) if content_parts else ""
    if not content.strip():
        # Clean up any temp files even if no content
        for temp_file in temp_files:
            await _cleanup_temp_file(temp_file)
        return

    # Show typing while we wait for AnythingLLM
    _start_typing(ctx.bot, chat_id)

    try:
        response = await _chat_anythingllm(content, chat_id, attachments=attachments)
        _stop_typing(chat_id)
        await _send_reply(ctx.bot, chat_id, response, reply_to=message.message_id)
    except Exception as e:
        _stop_typing(chat_id)
        await _send_reply(ctx.bot, chat_id, f"⚠️ Error: {e}", reply_to=message.message_id)
    finally:
        # Clean up temporary files
        for temp_file in temp_files:
            await _cleanup_temp_file(temp_file)


async def _on_error(update: object, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    print(f"[ERROR] Telegram: {ctx.error}", file=sys.stderr)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

async def main() -> None:
    if not TELEGRAM_TOKEN:
        sys.exit("TELEGRAM_BOT_TOKEN not set")
    if not ALLM_API_KEY:
        sys.exit("ANYTHINGLLM_API_KEY not set")

    print(f"Bridge: Telegram → AnythingLLM ({ALLM_BASE_URL}/workspace/{ALLM_WORKSPACE})")
    if AGENT_PREFIX:
        agent_mode = []
        if AGENT_FOR_TEXT:
            agent_mode.append("text")
        if AGENT_FOR_IMAGES:
            agent_mode.append("images")
        print(f"Agent mode: @agent for {' + '.join(agent_mode) if agent_mode else 'nothing'}")
    else:
        print(f"Agent mode: disabled")
    print(f"Allowed users: {ALLOWED_IDS}")

    req = HTTPXRequest(connection_pool_size=16, pool_timeout=5.0, connect_timeout=30.0, read_timeout=30.0)
    app = Application.builder().token(TELEGRAM_TOKEN).request(req).get_updates_request(req).build()
    app.add_error_handler(_on_error)

    app.add_handler(CommandHandler("start", _on_start))
    app.add_handler(CommandHandler("help", _on_help))
    app.add_handler(CommandHandler("new", _on_new))
    app.add_handler(
        MessageHandler(
            (filters.TEXT | filters.PHOTO | filters.VOICE | filters.AUDIO | filters.Document.ALL)
            & ~filters.COMMAND,
            _on_message,
        )
    )

    await app.initialize()
    await app.start()

    bot_info = await app.bot.get_me()
    print(f"Bot @{bot_info.username} connected — polling...")

    try:
        await app.bot.set_my_commands([
            BotCommand("start", "Start the bot"),
            BotCommand("new", "New conversation"),
            BotCommand("help", "Show help"),
        ])
    except Exception as e:
        print(f"[WARN] Failed to register commands: {e}", file=sys.stderr)

    await app.updater.start_polling(
        allowed_updates=["message"],
        drop_pending_updates=True,
    )

    # Run forever
    try:
        while True:
            await asyncio.sleep(1)
    except (KeyboardInterrupt, asyncio.CancelledError):
        pass
    finally:
        print("\nShutting down...")
        await app.updater.stop()
        await app.stop()
        await app.shutdown()
        await _http.aclose()


if __name__ == "__main__":
    asyncio.run(main())
