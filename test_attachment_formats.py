#!/usr/bin/env python3
"""
Test different attachment formats to find what LMStudio/AnythingLLM expects
"""
import asyncio
import base64
import os
import tempfile
from pathlib import Path

import httpx
from PIL import Image, ImageDraw

ALLM_BASE_URL = os.environ.get("ANYTHINGLLM_BASE_URL", "http://localhost:3001").rstrip("/")
ALLM_API_KEY = os.environ.get("ANYTHINGLLM_API_KEY", "")
ALLM_WORKSPACE = os.environ.get("ANYTHINGLLM_WORKSPACE", "nanobot")

async def create_test_image() -> Path:
    """Create a simple test image"""
    temp_dir = Path(tempfile.gettempdir())
    test_image_path = temp_dir / "format_test.png"
    
    img = Image.new('RGB', (100, 100), color='red')
    draw = ImageDraw.Draw(img)
    draw.rectangle([25, 25, 75, 75], fill='blue')
    img.save(test_image_path, 'PNG')
    
    return test_image_path

async def test_attachment_formats():
    """Test various attachment formats to see what works"""
    
    image_path = await create_test_image()
    
    # Read and encode image
    with open(image_path, 'rb') as f:
        image_data = f.read()
        base64_image = base64.b64encode(image_data).decode('utf-8')
    
    # Test different formats based on common vision API patterns
    test_formats = [
        {
            "name": "OpenAI-style content array",
            "payload": {
                "message": "What colors do you see?",
                "content": [
                    {"type": "text", "text": "What colors do you see in this image?"},
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{base64_image}"}}
                ]
            }
        },
        {
            "name": "Direct content with image_url",
            "payload": {
                "message": "What colors do you see?",
                "image_url": f"data:image/png;base64,{base64_image}"
            }
        },
        {
            "name": "Images array format", 
            "payload": {
                "message": "What colors do you see in this image?",
                "images": [f"data:image/png;base64,{base64_image}"]
            }
        },
        {
            "name": "Attachments with url field",
            "payload": {
                "message": "What colors do you see?",
                "attachments": [
                    {
                        "type": "image",
                        "url": f"data:image/png;base64,{base64_image}",
                        "name": "test.png"
                    }
                ]
            }
        },
        {
            "name": "Attachments with content field",
            "payload": {
                "message": "What colors do you see?", 
                "attachments": [
                    {
                        "type": "image",
                        "content": {
                            "url": f"data:image/png;base64,{base64_image}"
                        },
                        "name": "test.png"
                    }
                ]
            }
        },
        {
            "name": "Files array with base64",
            "payload": {
                "message": "What colors do you see?",
                "files": [
                    {
                        "type": "image",
                        "data": base64_image,
                        "mime_type": "image/png",
                        "filename": "test.png"
                    }
                ]
            }
        },
        {
            "name": "Media field",
            "payload": {
                "message": "What colors do you see?",
                "media": [
                    {
                        "type": "image/png",
                        "data": f"data:image/png;base64,{base64_image}"
                    }
                ]
            }
        }
    ]
    
    async with httpx.AsyncClient(
        headers={"Authorization": f"Bearer {ALLM_API_KEY}"},
        timeout=60.0
    ) as client:
        
        print("=== Testing Attachment Formats for LMStudio Vision ===")
        chat_url = f"{ALLM_BASE_URL}/api/v1/workspace/{ALLM_WORKSPACE}/chat"
        
        for i, test_format in enumerate(test_formats, 1):
            print(f"\n{i}. Testing: {test_format['name']}")
            try:
                response = await client.post(chat_url, json=test_format['payload'])
                print(f"   Status: {response.status_code}")
                
                if response.is_success:
                    data = response.json()
                    text_response = data.get('textResponse', '')
                    
                    if text_response and "no relevant information" not in text_response.lower():
                        print(f"   ✅ SUCCESS: {text_response[:150]}...")
                        
                        # Check if response mentions colors (red/blue from our test image)
                        if any(color in text_response.lower() for color in ['red', 'blue', 'color']):
                            print(f"   🎯 VISION WORKING: Response mentions colors!")
                            return test_format  # Return the working format
                        else:
                            print(f"   ⚠️  Response received but may not be vision-aware")
                    else:
                        print(f"   ❌ Generic response: {text_response[:100]}...")
                        
                else:
                    error_text = response.text[:200] if response.text else "No error text"
                    print(f"   ❌ HTTP {response.status_code}: {error_text}")
                    
            except Exception as e:
                print(f"   ❌ Exception: {e}")
    
    # Cleanup
    try:
        image_path.unlink()
    except Exception:
        pass
        
    print(f"\n❌ None of the formats worked for vision processing")
    return None

async def test_current_workspace_setup():
    """Test the current workspace setup to see actual model configuration"""
    
    async with httpx.AsyncClient(
        headers={"Authorization": f"Bearer {ALLM_API_KEY}"},
        timeout=30.0
    ) as client:
        
        print("=== Current Workspace Setup ===")
        
        try:
            # Get workspace details
            response = await client.get(f"{ALLM_BASE_URL}/api/v1/workspace/{ALLM_WORKSPACE}")
            if response.is_success:
                data = response.json()
                workspace = data['workspace'][0] if isinstance(data['workspace'], list) else data['workspace']
                
                print(f"Chat Provider: {workspace.get('chatProvider')}")
                print(f"Chat Model: {workspace.get('chatModel')}") 
                print(f"Agent Provider: {workspace.get('agentProvider')}")
                print(f"Agent Model: {workspace.get('agentModel')}")
                
                # The issue might be that we need to set a chat model, not just agent model
                if not workspace.get('chatModel'):
                    print("⚠️  No chat model set - this might be the issue!")
                    print("   Vision might only work with chat models, not agent models")
                    
        except Exception as e:
            print(f"Failed to get workspace info: {e}")
            
        # Test if @agent prefix makes a difference with different formats
        print(f"\n=== Testing @agent vs regular chat ===")
        
        test_messages = [
            {"message": "Hello, can you see images?", "mode": "chat"},
            {"message": "@agent Hello, can you see images?"}
        ]
        
        chat_url = f"{ALLM_BASE_URL}/api/v1/workspace/{ALLM_WORKSPACE}/chat"
        
        for msg in test_messages:
            try:
                response = await client.post(chat_url, json=msg)
                if response.is_success:
                    data = response.json()
                    text_response = data.get('textResponse', '')
                    prefix = "@agent" if "@agent" in msg["message"] else "regular"
                    print(f"   {prefix}: {text_response[:100]}...")
                else:
                    print(f"   Failed: {response.status_code}")
            except Exception as e:
                print(f"   Exception: {e}")

async def main():
    print("=== LMStudio Vision Format Debugging ===")
    print(f"Testing with Qwen3-VL-30B-A3B model")
    print(f"Workspace: {ALLM_WORKSPACE}")
    print()
    
    if not ALLM_API_KEY:
        print("❌ ANYTHINGLLM_API_KEY not set!")
        return
    
    # Check current setup first
    await test_current_workspace_setup()
    
    # Test different attachment formats
    working_format = await test_attachment_formats()
    
    if working_format:
        print(f"\n🎉 Found working format: {working_format['name']}")
        print("Update your bridge code to use this format!")
    else:
        print(f"\n🤔 No attachment format worked.")
        print("Possible issues:")
        print("1. Chat model needs to be configured (not just agent model)")
        print("2. LMStudio model may not be properly loaded")
        print("3. AnythingLLM may need different configuration for LMStudio vision")

if __name__ == "__main__":
    asyncio.run(main())