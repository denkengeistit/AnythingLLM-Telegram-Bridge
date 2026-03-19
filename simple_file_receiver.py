#!/usr/bin/env python3
"""
Simple Telegram File Receiver
Downloads images from Telegram and opens them locally for easy use with AnythingLLM desktop
"""
import asyncio
import os
import subprocess
import sys
from pathlib import Path
from datetime import datetime

from telegram import BotCommand, Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)
from telegram.request import HTTPXRequest

# Config
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
ALLOWED_IDS = os.environ.get("ALLOWED_USER_IDS", "*")
DOWNLOAD_DIR = Path.home() / "Downloads" / "Telegram_Images"

# Create download directory
DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)

def _is_allowed(user) -> bool:
    """Check if user is allowed"""
    if ALLOWED_IDS.strip() == "*":
        return True
    allowed = {s.strip() for s in ALLOWED_IDS.split(",") if s.strip()}
    return str(user.id) in allowed or (user.username and user.username in allowed)

async def _download_and_open_image(file, caption: str = "") -> str:
    """Download image and open it"""
    try:
        # Create filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_extension = Path(file.file_path).suffix if file.file_path else ".png"
        
        # Clean caption for filename (optional)
        safe_caption = ""
        if caption:
            safe_caption = "".join(c for c in caption[:30] if c.isalnum() or c in (' ', '-', '_')).strip()
            safe_caption = f"_{safe_caption}" if safe_caption else ""
        
        filename = f"telegram_image_{timestamp}{safe_caption}{file_extension}"
        local_path = DOWNLOAD_DIR / filename
        
        # Download the file
        await file.download_to_drive(local_path)
        
        # Open the image
        if sys.platform == "darwin":  # macOS
            subprocess.run(["open", str(local_path)])
        elif sys.platform == "win32":  # Windows
            os.startfile(str(local_path))
        else:  # Linux
            subprocess.run(["xdg-open", str(local_path)])
        
        # Wait a moment for the image to open, then trigger the shortcut
        if sys.platform == "darwin":  # macOS only
            import time
            time.sleep(1)  # Give the image time to open
            try:
                # First trigger - activate the screenshot
                subprocess.run(["shortcuts", "run", "AnythingLLM Screenshot"], check=True)
                time.sleep(3)  # Give the screenshot process time to complete
                # Second trigger - reset the toggle for next time
                subprocess.run(["shortcuts", "run", "AnythingLLM Screenshot"], check=True)
                return f"✅ Image opened and shortcut completed!\n📁 {local_path.name}\n🤖 Screenshot taken and toggle reset"
            except subprocess.CalledProcessError as e:
                return f"✅ Image opened but shortcut failed!\n📁 {local_path.name}\n❌ Shortcut error: {e}"
        
        return f"✅ Image saved and opened!\n📁 {local_path.name}\n💡 Drag it into AnythingLLM desktop for analysis"
        
    except Exception as e:
        return f"❌ Failed to download image: {e}"

async def _on_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start command"""
    if not update.message or not update.effective_user:
        return
    
    name = update.effective_user.first_name
    await update.message.reply_text(
        f"👋 Hi {name}! I'm your simple file receiver.\n\n"
        f"📷 Send me images and I'll:\n"
        f"  • Save them to: {DOWNLOAD_DIR}\n"
        f"  • Open them automatically\n"
        f"  • You can then drag them into AnythingLLM desktop\n\n"
        f"🖥️ This works perfectly with your GLM-4.6v vision model!\n\n"
        f"/help — Show this message"
    )

async def _on_help(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /help command"""
    if not update.message:
        return
    
    await update.message.reply_text(
        f"📁 Simple File Receiver\n\n"
        f"📷 Send images → I save & open them\n"
        f"💾 Download folder: {DOWNLOAD_DIR}\n"
        f"🖱️ Drag opened images into AnythingLLM desktop\n"
        f"🎯 Works with any vision model!\n\n"
        f"💡 Pro tip: Add captions to your images for better filenames"
    )

async def _on_image(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle image messages"""
    if not update.message or not update.effective_user:
        return

    user = update.effective_user
    message = update.message

    if not _is_allowed(user):
        await message.reply_text("⛔ Access denied.")
        return

    # Handle images
    if message.photo:
        # Get highest resolution photo
        photo_file = await message.photo[-1].get_file()
        caption = message.caption or ""
        
        # Show processing message
        processing_msg = await message.reply_text("📥 Downloading image...")
        
        # Download and open
        result = await _download_and_open_image(photo_file, caption)
        
        # Update the message
        await processing_msg.edit_text(result)
        
    elif message.document and message.document.mime_type and message.document.mime_type.startswith('image/'):
        # Handle image documents
        doc_file = await message.document.get_file()
        caption = message.caption or ""
        
        processing_msg = await message.reply_text("📥 Downloading image document...")
        result = await _download_and_open_image(doc_file, caption)
        await processing_msg.edit_text(result)
        
    else:
        await message.reply_text("📷 Please send an image file!")

async def _on_error(update: object, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle errors"""
    print(f"[ERROR] Telegram: {ctx.error}", file=sys.stderr)

async def main() -> None:
    """Main function"""
    if not TELEGRAM_TOKEN:
        sys.exit("❌ TELEGRAM_BOT_TOKEN not set")

    print(f"🗂️  Simple File Receiver")
    print(f"📁 Download directory: {DOWNLOAD_DIR}")
    print(f"👥 Allowed users: {ALLOWED_IDS}")
    print()

    # Setup Telegram bot
    req = HTTPXRequest(connection_pool_size=8, pool_timeout=5.0, connect_timeout=30.0, read_timeout=30.0)
    app = Application.builder().token(TELEGRAM_TOKEN).request(req).get_updates_request(req).build()
    
    # Add handlers
    app.add_error_handler(_on_error)
    app.add_handler(CommandHandler("start", _on_start))
    app.add_handler(CommandHandler("help", _on_help))
    app.add_handler(MessageHandler(filters.PHOTO | (filters.Document.IMAGE), _on_image))

    # Start bot
    await app.initialize()
    await app.start()

    bot_info = await app.bot.get_me()
    print(f"🤖 Bot @{bot_info.username} connected — ready to receive files!")

    # Set commands
    try:
        await app.bot.set_my_commands([
            BotCommand("start", "Start the file receiver"),
            BotCommand("help", "Show help"),
        ])
    except Exception as e:
        print(f"⚠️  Failed to set commands: {e}", file=sys.stderr)

    # Start polling
    await app.updater.start_polling(
        allowed_updates=["message"],
        drop_pending_updates=True,
    )

    print("✨ Send images to your bot - they'll be saved and opened automatically!")
    print("🖱️  Then just drag them into AnythingLLM desktop for vision analysis")
    print()

    # Run forever
    try:
        while True:
            await asyncio.sleep(1)
    except (KeyboardInterrupt, asyncio.CancelledError):
        pass
    finally:
        print("\n🛑 Shutting down...")
        await app.updater.stop()
        await app.stop()
        await app.shutdown()

if __name__ == "__main__":
    asyncio.run(main())