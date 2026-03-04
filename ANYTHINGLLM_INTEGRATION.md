# AnythingLLM Integration for Nanobot

This integration allows Nanobot to directly communicate with AnythingLLM workspaces at the Python level, eliminating the need for MCP tools and providing much more reliable communication.

## Features

- **Direct Python Integration**: No MCP layer - talks directly to AnythingLLM API
- **Automatic Agent Routing**: Messages are automatically prefixed with `@agent` 
- **Workspace Management**: List, create, and manage specialized workspaces
- **Intelligent Agent Selection**: Nanobot can route different types of tasks to specialized AnythingLLM agents
- **Reliable Communication**: Uses native HTTP calls instead of complex MCP protocol

## Configuration

Add the following to your `~/.nanobot/config.json`:

```json
{
  "tools": {
    "anythingllm": {
      "enabled": true,
      "baseUrl": "http://localhost:3001",
      "apiKey": "your-anythingllm-api-key",
      "defaultWorkspaceSlug": "nanobot",
      "workspaceManagement": true
    }
  }
}
```

### Configuration Options

- `enabled`: Enable/disable AnythingLLM integration
- `baseUrl`: AnythingLLM API base URL (default: http://localhost:3001)
- `apiKey`: Your AnythingLLM API key (get from AnythingLLM → Settings → API Keys)
- `defaultWorkspaceSlug`: Default workspace to chat with (default: "nanobot")
- `workspaceManagement`: Enable workspace creation/management tools (default: true)

### Environment Variables

You can also configure using environment variables:

```bash
export NANOBOT_TOOLS__ANYTHINGLLM__ENABLED=true
export NANOBOT_TOOLS__ANYTHINGLLM__BASE_URL=http://localhost:3001
export NANOBOT_TOOLS__ANYTHINGLLM__API_KEY=your-key-here
export NANOBOT_TOOLS__ANYTHINGLLM__DEFAULT_WORKSPACE_SLUG=nanobot
export NANOBOT_TOOLS__ANYTHINGLLM__WORKSPACE_MANAGEMENT=true
```

## Available Tools

### 1. anythingllm_chat

Send messages directly to your AnythingLLM workspace agent.

**Parameters:**
- `message` (required): The message to send to the agent
- `mode` (optional): "chat" for conversation, "query" for knowledge retrieval

**Example Usage:**
- "Please use anythingllm_chat to ask the agent about the latest project updates"
- "Send a message to AnythingLLM asking for a code review of the login function"

### 2. anythingllm_workspace_manager

Manage AnythingLLM workspaces for different specialized tasks.

**Parameters:**
- `action` (required): "list", "create", or "get_details" 
- `workspace_name`: Name for new workspace (required for create)
- `workspace_slug`: Workspace slug (required for get_details)
- `system_prompt`: Custom system prompt (optional for create)

**Example Usage:**
- "List all available AnythingLLM workspaces"
- "Create a new workspace called 'Image Analysis' for analyzing screenshots"
- "Get details about the 'code-assistant' workspace"

## How It Works

1. **Direct API Communication**: The tools use Python's `httpx` library to make HTTP requests directly to the AnythingLLM API
2. **Automatic Agent Activation**: All messages are automatically prefixed with `@agent` to activate the agent in the workspace
3. **Error Handling**: Robust error handling with timeouts and meaningful error messages
4. **Response Processing**: Automatically extracts the actual response from AnythingLLM's API response structure

## Example Workflow

1. **Initialize**: Nanobot starts up and registers AnythingLLM tools if enabled
2. **Task Recognition**: User asks something like "analyze this code for security issues"
3. **Tool Selection**: Nanobot's LLM decides to use `anythingllm_chat`
4. **Message Routing**: Tool sends "@agent analyze this code for security issues" to your workspace
5. **Response**: AnythingLLM agent responds with specialized analysis
6. **Integration**: Response is returned to Nanobot and presented to user

## Specialized Workspace Examples

You can create specialized workspaces for different domains:

```bash
# Create a code review workspace
nanobot agent -m "Create a workspace called 'Code Reviewer' with system prompt 'You are a senior software engineer who specializes in code reviews. Focus on security, performance, and maintainability.'"

# Create an image analysis workspace  
nanobot agent -m "Create a workspace called 'Image Analyzer' with system prompt 'You are an expert at analyzing images, screenshots, and visual content. Describe what you see in detail.'"
```

## Benefits Over MCP Approach

1. **Reliability**: No complex MCP protocol - simple HTTP requests
2. **Performance**: Direct communication without MCP overhead
3. **Debugging**: Easier to debug HTTP requests vs MCP protocol
4. **Maintenance**: Less complex architecture to maintain
5. **Error Handling**: Better error messages and timeout handling
6. **Development**: Easier to extend and modify

## Troubleshooting

### Tool Not Available
- Check that `enabled: true` is set in config
- Verify AnythingLLM is running and accessible
- Confirm API key is valid

### Connection Errors
- Verify `baseUrl` is correct (http://localhost:3001 for desktop app)
- Check that AnythingLLM API is enabled
- Test API key with: `curl -H "Authorization: Bearer your-key" http://localhost:3001/api/v1/system`

### Workspace Not Found
- Use `anythingllm_workspace_manager` with action "list" to see available workspaces
- Make sure `defaultWorkspaceSlug` matches an existing workspace
- Create the workspace if it doesn't exist

This integration provides a much more reliable way to connect Nanobot with AnythingLLM compared to using MCP tools, while maintaining all the functionality you need for intelligent agent routing.