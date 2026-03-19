# Telegram File Receiver MCP Server Setup

This integrates the Telegram file receiver directly into AnythingLLM as an MCP (Model Context Protocol) server, so it starts automatically with AnythingLLM.

## Installation

### 1. Install MCP Package
```bash
pip install mcp
```

### 2. Configure AnythingLLM MCP Settings

Add the MCP server configuration to your AnythingLLM settings:

**Option A: Via UI**
1. Open AnythingLLM
2. Go to Settings → MCP Servers
3. Add new MCP server with these details:
   - **Name**: `telegram-file-receiver`
   - **Command**: `python3`
   - **Args**: `["/Users/andme/Sync/Projects/nanobot/AnythingLLM-Telegram-Bridge/telegram_mcp_server.py"]`
   - **Environment Variables**:
     - `TELEGRAM_BOT_TOKEN`: `8452801263:AAEbkwvbwoqaFXUkm9H0aoU-jeWFwtjSwhg`
     - `ALLOWED_USER_IDS`: `*`

**Option B: Via Config File**
Copy `mcp_config.json` to your AnythingLLM MCP configuration directory.

### 3. Restart AnythingLLM
The MCP server will now start automatically with AnythingLLM.

## Usage

### Available Tools in AnythingLLM Chat

Once configured, you can use these commands in AnythingLLM chat:

- **Start Telegram Receiver**: `@agent start telegram receiver`
- **Check Status**: `@agent get telegram receiver status` 
- **Stop Receiver**: `@agent stop telegram receiver`

### Available Resources

- **Recent Files**: Access list of recently received Telegram files
- **File Paths**: Get local paths to downloaded images

### Workflow

1. **Start the receiver** via AnythingLLM chat: `@agent start telegram receiver`
2. **Send images** to @warpagerbot on Telegram
3. **Images auto-download** and trigger screenshot
4. **AnythingLLM gets notified** of new files via MCP
5. **Seamless integration** - all from within AnythingLLM!

## Benefits vs Standalone Version

✅ **Auto-starts** with AnythingLLM - no separate process
✅ **Integrated controls** - start/stop from AnythingLLM chat  
✅ **File awareness** - AnythingLLM knows about received files
✅ **Resource access** - Can reference recent files in conversations
✅ **Unified experience** - Everything in one interface

## Troubleshooting

### MCP Server Not Starting
- Check that `pip install mcp` completed successfully
- Verify file paths in configuration are correct
- Check AnythingLLM logs for MCP connection errors

### Telegram Bot Issues  
- Verify `TELEGRAM_BOT_TOKEN` is correct
- Check permissions for AppleScript shortcuts
- Ensure AnythingLLM is running for screenshot integration

### Screenshot Automation
- Make sure "AnythingLLM Screenshot" shortcut exists
- Grant accessibility permissions when prompted
- Verify AnythingLLM desktop app is running

## Example Usage in AnythingLLM

```
You: @agent start telegram receiver