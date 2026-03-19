#!/usr/bin/env python3
"""
Test different attachment formats to find what AnythingLLM actually expects
Since the model works in desktop UI, the issue is our attachment format
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
    
    # Create a very obvious image - red circle on white background
    img = Image.new('RGB', (200, 200), color='white')
    draw = ImageDraw.Draw(img)
    draw.ellipse([50, 50, 150, 150], fill='red', outline='black', width=3)
    img.save(test_image_path, 'PNG')
    
    return test_image_path

async def test_all_possible_formats():
    """Test every possible attachment format variation"""
    
    image_path = await create_test_image()
    
    # Read and encode image
    with open(image_path, 'rb') as f:
        image_data = f.read()
        base64_image = base64.b64encode(image_data).decode('utf-8')
    
    # Try many different format variations based on common patterns
    test_formats = [
        # Format 1: Our current format
        {
            "name": "Current bridge format",
            "payload": {
                "message": "What do you see?",
                "attachments": [
                    {
                        "type": "image",
                        "data": f"data:image/png;base64,{base64_image}",
                        "name": "test.png"
                    }
                ]
            }
        },
        
        # Format 2: Without data: prefix
        {
            "name": "Raw base64 in data field",
            "payload": {
                "message": "What do you see?",
                "attachments": [
                    {
                        "type": "image", 
                        "data": base64_image,
                        "name": "test.png"
                    }
                ]
            }
        },
        
        # Format 3: With url field instead of data
        {
            "name": "Using url field",
            "payload": {
                "message": "What do you see?",
                "attachments": [
                    {
                        "type": "image",
                        "url": f"data:image/png;base64,{base64_image}",
                        "name": "test.png"
                    }
                ]
            }
        },
        
        # Format 4: Content array like OpenAI
        {
            "name": "OpenAI-style content array",
            "payload": {
                "message": [
                    {"type": "text", "text": "What do you see?"},
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{base64_image}"}}
                ]
            }
        },
        
        # Format 5: Files array
        {
            "name": "Files array",
            "payload": {
                "message": "What do you see?",
                "files": [
                    {
                        "type": "image/png",
                        "data": f"data:image/png;base64,{base64_image}",
                        "name": "test.png"
                    }
                ]
            }
        },
        
        # Format 6: Images array (simple)
        {
            "name": "Images array", 
            "payload": {
                "message": "What do you see?",
                "images": [f"data:image/png;base64,{base64_image}"]
            }
        },
        
        # Format 7: Attachment with content object
        {
            "name": "Attachment with content object",
            "payload": {
                "message": "What do you see?",
                "attachments": [
                    {
                        "type": "image",
                        "content": {
                            "type": "image/png",
                            "data": base64_image
                        },
                        "name": "test.png"
                    }
                ]
            }
        },
        
        # Format 8: Media field
        {
            "name": "Media field",
            "payload": {
                "message": "What do you see?",
                "media": [
                    {
                        "type": "image",
                        "data": f"data:image/png;base64,{base64_image}",
                        "filename": "test.png"
                    }
                ]
            }
        }
    ]
    
    async with httpx.AsyncClient(
        headers={"Authorization": f"Bearer {ALLM_API_KEY}"},
        timeout=60.0
    ) as client:
        
        print("=== Testing All Possible Attachment Formats ===")
        print("Looking for one that actually describes the red circle...")
        print()
        
        chat_url = f"{ALLM_BASE_URL}/api/v1/workspace/{ALLM_WORKSPACE}/chat"
        
        for i, test_format in enumerate(test_formats, 1):
            print(f"{i}. Testing: {test_format['name']}")
            try:
                response = await client.post(chat_url, json=test_format['payload'])
                print(f"   Status: {response.status_code}")
                
                if response.is_success:
                    data = response.json()
                    text_response = data.get('textResponse', '')
                    
                    # Check if response describes the image content
                    vision_keywords = ['red', 'circle', 'white', 'background', 'round', 'shape', 'color']
                    found_keywords = [kw for kw in vision_keywords if kw.lower() in text_response.lower()]
                    
                    if found_keywords:
                        print(f"   🎯 SUCCESS! Found vision keywords: {found_keywords}")
                        print(f"   Response: {text_response[:200]}...")
                        print(f"\n✅ WORKING FORMAT FOUND: {test_format['name']}")
                        return test_format
                    elif "no relevant information" in text_response.lower():
                        print(f"   ❌ Generic 'no relevant information' response")
                    else:
                        print(f"   ⚠️  Response: {text_response[:100]}...")
                        
                else:
                    print(f"   ❌ HTTP {response.status_code}: {response.text[:100]}...")
                    
            except Exception as e:
                print(f"   ❌ Exception: {e}")
            
            print()
    
    # Cleanup
    try:
        image_path.unlink()
    except Exception:
        pass
        
    print("❌ None of the formats worked!")
    print("This suggests AnythingLLM uses a different API format than we're testing.")
    return None

async def main():
    print("=== Finding Correct AnythingLLM Attachment Format ===")
    print("Since GLM-4.6v works in desktop UI, our format is wrong")
    print()
    
    if not ALLM_API_KEY:
        print("❌ ANYTHINGLLM_API_KEY not set!")
        return
    
    working_format = await test_all_possible_formats()
    
    if working_format:
        print(f"\n🎉 Found working format!")
        print("Now I can update the bridge code to use this format.")
    else:
        print(f"\n🤔 No standard formats worked.")
        print("We may need to inspect the actual network requests from the desktop UI")
        print("or check AnythingLLM documentation for the correct API format.")

if __name__ == "__main__":
    asyncio.run(main())