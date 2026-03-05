#!/usr/bin/env python3.11
"""
Simplified Telegram File Receiver MCP Server
Works with AnythingLLM's MCP client expectations
"""
import asyncio
import json
import os
import subprocess
import sys
from pathlib import Path
from datetime import datetime

from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters
from telegram.request import HTTPXRequest

# Config
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
DOWNLOAD_DIR = Path.home() / "Downloads" / "Telegram_Images"
DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)

# Global state
telegram_app = None
received_files = []

class SimpleMCPServer:
    def __init__(self):
        self.capabilities = {
            "tools": {
                "start_telegram_receiver": {
                    "description": "Start the Telegram file receiver bot",
                    "inputSchema": {
                        "type": "object",
                        "properties": {},
                        "required": []
                    }
                },
                "get_receiver_status": {
                    "description": "Get status of the Telegram receiver",
                    "inputSchema": {
                        "type": "object",
                        "properties": {},
                        "required": []
                    }
                }
            },
            "resources": {
                "telegram://recent-files": {
                    "description": "List of recently received files from Telegram",
                    "mimeType": "application/json"
                }
            }
        }
    
    async def handle_request(self, request):
        """Handle MCP JSON-RPC requests"""
        try:
            method = request.get("method")
            params = request.get("params", {})
            request_id = request.get("id")
            
            if method == "initialize":
                return {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {
                        "protocolVersion": "2024-11-05",
                        "serverInfo": {"name": "telegram-file-receiver", "version": "1.0.0"},
                        "capabilities": self.capabilities
                    }
                }
            
            elif method == "tools/list":
                return {
                    "jsonrpc": "2.0", 
                    "id": request_id,
                    "result": {"tools": list(self.capabilities["tools"].values())}
                }
            
            elif method == "tools/call":
                tool_name = params.get("name")
                if tool_name == "start_telegram_receiver":
                    result = await self.start_telegram_receiver()
                elif tool_name == "get_receiver_status":
                    result = await self.get_receiver_status()
                else:
                    result = {"error": f"Unknown tool: {tool_name}"}
                
                return {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {"content": [{"type": "text", "text": json.dumps(result)}]}
                }
            
            elif method == "resources/list":
                return {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {"resources": [
                        {
                            "uri": "telegram://recent-files",
                            "name": "Recent Telegram Files", 
                            "description": "List of recently received files",
                            "mimeType": "application/json"
                        }
                    ]}
                }
            
            elif method == "resources/read":
                uri = params.get("uri")
                if uri == "telegram://recent-files":
                    content = json.dumps({
                        "recent_files": [
                            {
                                "filename": f.get("filename"),
                                "path": str(f.get("path")),
                                "timestamp": f.get("timestamp"),
                                "caption": f.get("caption", "")
                            }
                            for f in received_files[-10:]
                        ]
                    })
                    return {
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "result": {"contents": [{"uri": uri, "mimeType": "application/json", "text": content}]}
                    }
            
            # Default response for unknown methods
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {"code": -32601, "message": "Method not found"}
            }
            
        except Exception as e:
            return {
                "jsonrpc": "2.0", 
                "id": request.get("id"),
                "error": {"code": -32603, "message": f"Internal error: {str(e)}"}
            }
    
    async def start_telegram_receiver(self):
        """Start the Telegram bot"""
        global telegram_app
        
        if not TELEGRAM_TOKEN:
            return {"error": "TELEGRAM_BOT_TOKEN not set"}
        
        if telegram_app is not None:
            return {"status": "already_running", "message": "Telegram receiver already running"}
        
        try:
            req = HTTPXRequest(connection_pool_size=8, pool_timeout=5.0)
            telegram_app = Application.builder().token(TELEGRAM_TOKEN).request(req).build()
            
            telegram_app.add_handler(CommandHandler("start", self._on_start))
            telegram_app.add_handler(MessageHandler(filters.PHOTO, self._on_image))
            
            await telegram_app.initialize()
            await telegram_app.start()
            
            asyncio.create_task(self._run_polling())
            
            bot_info = await telegram_app.bot.get_me()
            return {
                "status": "started",
                "bot_username": bot_info.username,
                "message": f"@{bot_info.username} ready to receive images"
            }
            
        except Exception as e:
            return {"error": f"Failed to start: {e}"}
    
    async def get_receiver_status(self):
        """Get receiver status"""
        global telegram_app
        
        if telegram_app is None:
            return {"status": "stopped", "running": False, "files_received": len(received_files)}
        
        try:
            bot_info = await telegram_app.bot.get_me()
            return {
                "status": "running",
                "running": True,
                "bot_username": bot_info.username,
                "files_received": len(received_files),
                "download_dir": str(DOWNLOAD_DIR)
            }
        except Exception as e:
            return {"error": f"Status check failed: {e}"}
    
    async def _run_polling(self):
        """Run Telegram polling"""
        global telegram_app
        if telegram_app:
            await telegram_app.updater.start_polling(allowed_updates=["message"])
    
    async def _on_start(self, update: Update, context):
        """Handle /start"""
        if update.message and update.effective_user:
            name = update.effective_user.first_name
            await update.message.reply_text(f"Hi {name}! Send me images for AnythingLLM processing.")
    
    async def _on_image(self, update: Update, context):
        """Handle images"""
        if not update.message or not update.message.photo:
            return
        
        processing = await update.message.reply_text("📥 Processing...")
        
        try:
            # Download image
            photo_file = await update.message.photo[-1].get_file()
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"telegram_image_{timestamp}.jpg"
            local_path = DOWNLOAD_DIR / filename
            
            await photo_file.download_to_drive(local_path)
            
            # Add to files list
            received_files.append({
                "filename": filename,
                "path": local_path,
                "timestamp": datetime.now().timestamp(),
                "caption": update.message.caption or ""
            })
            
            # Open and trigger screenshot
            if sys.platform == "darwin":
                subprocess.run(["open", str(local_path)])
                await asyncio.sleep(1)
                try:
                    subprocess.run(["shortcuts", "run", "AnythingLLM Screenshot"], check=True)
                    await asyncio.sleep(3)
                    subprocess.run(["shortcuts", "run", "AnythingLLM Screenshot"], check=True)
                    await processing.edit_text(f"✅ Image processed and screenshot taken!\n📁 {filename}")
                except subprocess.CalledProcessError:
                    await processing.edit_text(f"✅ Image saved but screenshot failed\n📁 {filename}")
            
        except Exception as e:
            await processing.edit_text(f"❌ Error: {e}")

async def main():
    """Main MCP server loop"""
    print("🚀 Starting Simplified Telegram MCP Server")
    
    server = SimpleMCPServer()
    
    # Read from stdin and write to stdout (MCP protocol)
    while True:
        try:
            line = await asyncio.get_event_loop().run_in_executor(None, sys.stdin.readline)
            if not line:
                break
            
            request = json.loads(line.strip())
            response = await server.handle_request(request)
            print(json.dumps(response), flush=True)
            
        except json.JSONDecodeError:
            continue
        except Exception as e:
            error_response = {
                "jsonrpc": "2.0",
                "id": None,
                "error": {"code": -32700, "message": f"Parse error: {str(e)}"}
            }
            print(json.dumps(error_response), flush=True)

if __name__ == "__main__":
    asyncio.run(main())