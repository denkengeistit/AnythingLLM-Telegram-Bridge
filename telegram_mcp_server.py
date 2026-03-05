#!/usr/bin/env python3
"""
Telegram File Receiver MCP Server
Provides Telegram image receiving as an MCP service for AnythingLLM
"""
import asyncio
import json
import os
import subprocess
import sys
from pathlib import Path
from datetime import datetime
import logging

from telegram import BotCommand, Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)
from telegram.request import HTTPXRequest

# MCP imports (you'll need to install mcp package)
try:
    from mcp.server import Server
    from mcp.types import Resource, Tool
    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False
    print("⚠️  MCP not available - install with: pip install mcp")

# Config
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
ALLOWED_IDS = os.environ.get("ALLOWED_USER_IDS", "*")
DOWNLOAD_DIR = Path.home() / "Downloads" / "Telegram_Images"
DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)

# Global state
telegram_app = None
received_files = []

class TelegramMCPServer:
    def __init__(self):
        self.server = Server("telegram-file-receiver")
        self.setup_resources_and_tools()
    
    def setup_resources_and_tools(self):
        """Setup MCP resources and tools"""
        
        # Resource: Recent files
        @self.server.list_resources()
        async def list_resources():
            return [
                Resource(
                    uri="telegram://recent-files",
                    name="Recent Telegram Files",
                    description="List of recently received files from Telegram",
                    mimeType="application/json"
                )
            ]
        
        @self.server.read_resource()
        async def read_resource(uri: str):
            if uri == "telegram://recent-files":
                return json.dumps({
                    "recent_files": [
                        {
                            "filename": f.get("filename"),
                            "path": str(f.get("path")),
                            "timestamp": f.get("timestamp"),
                            "caption": f.get("caption", "")
                        }
                        for f in received_files[-10:]  # Last 10 files
                    ]
                })
            return ""
        
        # Tool: Start Telegram receiver
        @self.server.list_tools()
        async def list_tools():
            return [
                Tool(
                    name="start_telegram_receiver",
                    description="Start the Telegram file receiver bot",
                    inputSchema={
                        "type": "object",
                        "properties": {},
                        "required": []
                    }
                ),
                Tool(
                    name="stop_telegram_receiver", 
                    description="Stop the Telegram file receiver bot",
                    inputSchema={
                        "type": "object",
                        "properties": {},
                        "required": []
                    }
                ),
                Tool(
                    name="get_receiver_status",
                    description="Get status of the Telegram receiver",
                    inputSchema={
                        "type": "object", 
                        "properties": {},
                        "required": []
                    }
                )
            ]
        
        @self.server.call_tool()
        async def call_tool(name: str, arguments: dict):
            if name == "start_telegram_receiver":
                return await self.start_telegram_receiver()
            elif name == "stop_telegram_receiver":
                return await self.stop_telegram_receiver()
            elif name == "get_receiver_status":
                return await self.get_receiver_status()
            return {"error": f"Unknown tool: {name}"}
    
    async def start_telegram_receiver(self):
        """Start the Telegram bot"""
        global telegram_app
        
        if not TELEGRAM_TOKEN:
            return {"error": "TELEGRAM_BOT_TOKEN not set"}
        
        if telegram_app is not None:
            return {"status": "already_running", "message": "Telegram receiver is already running"}
        
        try:
            # Setup Telegram bot
            req = HTTPXRequest(connection_pool_size=8, pool_timeout=5.0)
            telegram_app = Application.builder().token(TELEGRAM_TOKEN).request(req).build()
            
            # Add handlers
            telegram_app.add_handler(CommandHandler("start", self._on_start))
            telegram_app.add_handler(CommandHandler("help", self._on_help))
            telegram_app.add_handler(MessageHandler(filters.PHOTO | filters.Document.IMAGE, self._on_image))
            
            # Start bot
            await telegram_app.initialize()
            await telegram_app.start()
            
            # Start polling in background
            asyncio.create_task(self._run_polling())
            
            bot_info = await telegram_app.bot.get_me()
            return {
                "status": "started",
                "bot_username": bot_info.username,
                "download_dir": str(DOWNLOAD_DIR),
                "message": f"Telegram receiver @{bot_info.username} started successfully"
            }
            
        except Exception as e:
            return {"error": f"Failed to start Telegram receiver: {e}"}
    
    async def stop_telegram_receiver(self):
        """Stop the Telegram bot"""
        global telegram_app
        
        if telegram_app is None:
            return {"status": "not_running", "message": "Telegram receiver is not running"}
        
        try:
            await telegram_app.updater.stop()
            await telegram_app.stop()
            await telegram_app.shutdown()
            telegram_app = None
            
            return {"status": "stopped", "message": "Telegram receiver stopped successfully"}
            
        except Exception as e:
            return {"error": f"Failed to stop Telegram receiver: {e}"}
    
    async def get_receiver_status(self):
        """Get current status"""
        global telegram_app
        
        if telegram_app is None:
            return {
                "status": "stopped",
                "running": False,
                "files_received": len(received_files),
                "download_dir": str(DOWNLOAD_DIR)
            }
        
        try:
            bot_info = await telegram_app.bot.get_me()
            return {
                "status": "running",
                "running": True,
                "bot_username": bot_info.username,
                "files_received": len(received_files),
                "download_dir": str(DOWNLOAD_DIR),
                "recent_files": len([f for f in received_files if f.get("timestamp", 0) > (datetime.now().timestamp() - 3600)])
            }
        except Exception as e:
            return {"error": f"Failed to get status: {e}"}
    
    async def _run_polling(self):
        """Run Telegram polling in background"""
        global telegram_app
        if telegram_app:
            await telegram_app.updater.start_polling(
                allowed_updates=["message"],
                drop_pending_updates=True
            )
    
    async def _on_start(self, update: Update, ctx: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        if update.message and update.effective_user:
            name = update.effective_user.first_name
            await update.message.reply_text(
                f"👋 Hi {name}! Telegram File Receiver (MCP Server)\n\n"
                f"📷 Send images → Auto-download & screenshot\n"
                f"🤖 Integrated with AnythingLLM\n"
                f"📁 Files saved to: {DOWNLOAD_DIR}"
            )
    
    async def _on_help(self, update: Update, ctx: ContextTypes.DEFAULT_TYPE):
        """Handle /help command"""
        if update.message:
            await update.message.reply_text(
                f"📁 Telegram MCP File Receiver\n\n"
                f"📷 Send images → Auto-processed\n"
                f"🤖 Connected to AnythingLLM via MCP\n"
                f"✨ Automatic screenshot integration"
            )
    
    async def _on_image(self, update: Update, ctx: ContextTypes.DEFAULT_TYPE):
        """Handle image messages"""
        if not update.message or not update.effective_user:
            return
        
        user = update.effective_user
        message = update.message
        
        if not self._is_allowed(user):
            await message.reply_text("⛔ Access denied.")
            return
        
        if message.photo:
            photo_file = await message.photo[-1].get_file()
            caption = message.caption or ""
            
            processing_msg = await message.reply_text("📥 Processing image...")
            result = await self._download_and_process_image(photo_file, caption)
            await processing_msg.edit_text(result)
    
    def _is_allowed(self, user) -> bool:
        """Check if user is allowed"""
        if ALLOWED_IDS.strip() == "*":
            return True
        allowed = {s.strip() for s in ALLOWED_IDS.split(",") if s.strip()}
        return str(user.id) in allowed or (user.username and user.username in allowed)
    
    async def _download_and_process_image(self, file, caption: str = "") -> str:
        """Download and process image with automatic screenshot"""
        try:
            # Create filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            file_extension = Path(file.file_path).suffix if file.file_path else ".png"
            safe_caption = "".join(c for c in caption[:30] if c.isalnum() or c in (' ', '-', '_')).strip()
            safe_caption = f"_{safe_caption}" if safe_caption else ""
            
            filename = f"telegram_image_{timestamp}{safe_caption}{file_extension}"
            local_path = DOWNLOAD_DIR / filename
            
            # Download file
            await file.download_to_drive(local_path)
            
            # Add to received files list
            received_files.append({
                "filename": filename,
                "path": local_path,
                "timestamp": datetime.now().timestamp(),
                "caption": caption
            })
            
            # Open image
            if sys.platform == "darwin":
                subprocess.run(["open", str(local_path)])
                
                # Trigger screenshot shortcut (with toggle reset)
                import time
                time.sleep(1)
                try:
                    subprocess.run(["shortcuts", "run", "AnythingLLM Screenshot"], check=True)
                    time.sleep(3)
                    subprocess.run(["shortcuts", "run", "AnythingLLM Screenshot"], check=True)
                    return f"✅ Image processed and screenshot taken!\n📁 {filename}\n🤖 Ready for AnythingLLM analysis"
                except subprocess.CalledProcessError:
                    return f"✅ Image saved but screenshot failed\n📁 {filename}\n💡 Manually drag into AnythingLLM"
            
            return f"✅ Image saved!\n📁 {filename}"
            
        except Exception as e:
            return f"❌ Failed to process image: {e}"

async def main():
    """Main function"""
    if not MCP_AVAILABLE:
        sys.exit("❌ MCP package required - install with: pip install mcp")
    
    print("🚀 Starting Telegram File Receiver MCP Server")
    
    # Create and run MCP server
    mcp_server = TelegramMCPServer()
    
    # Run the MCP server with stdio streams
    from mcp.server.stdio import stdio_server
    async with stdio_server(mcp_server.server) as streams:
        await streams[0].aclose()

if __name__ == "__main__":
    asyncio.run(main())