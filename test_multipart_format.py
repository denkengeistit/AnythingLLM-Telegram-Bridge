#!/usr/bin/env python3
"""
Test multipart form data approach based on Context7 insights
AnythingLLM supports drag-and-drop files directly into chat
"""
import asyncio
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
    test_image_path = temp_dir / "multipart_test.png"
    
    # Create a very obvious image - blue triangle on yellow background
    img = Image.new('RGB', (200, 200), color='yellow')
    draw = ImageDraw.Draw(img)
    # Draw blue triangle
    draw.polygon([(100, 50), (50, 150), (150, 150)], fill='blue', outline='black')
    img.save(test_image_path, 'PNG')
    
    return test_image_path

async def test_multipart_approaches():
    """Test multipart form data approaches"""
    
    image_path = await create_test_image()
    
    async with httpx.AsyncClient(
        headers={"Authorization": f"Bearer {ALLM_API_KEY}"},
        timeout=60.0
    ) as client:
        
        print("=== Testing Multipart Form Data Approaches ===")
        print("Based on Context7: AnythingLLM supports drag-and-drop files into chat")
        print()
        
        chat_url = f"{ALLM_BASE_URL}/api/v1/workspace/{ALLM_WORKSPACE}/chat"
        
        # Approach 1: Just the file with message in form data
        print("1. Testing: File + message as form fields")
        try:
            with open(image_path, 'rb') as f:
                response = await client.post(
                    chat_url,
                    files={'file': ('test.png', f, 'image/png')},
                    data={'message': 'What shapes and colors do you see in this image?'}
                )
            
            print(f"   Status: {response.status_code}")
            if response.is_success:
                data = response.json()
                text_response = data.get('textResponse', '')
                
                # Check for vision keywords
                keywords = ['blue', 'yellow', 'triangle', 'shape', 'color']
                found = [k for k in keywords if k.lower() in text_response.lower()]
                
                if found:
                    print(f"   🎯 SUCCESS! Found keywords: {found}")
                    print(f"   Response: {text_response[:200]}...")
                    return "multipart-file-message"
                else:
                    print(f"   Response: {text_response[:100]}...")
            else:
                print(f"   Error: {response.text[:200]}...")
        except Exception as e:
            print(f"   Exception: {e}")
        
        print()
        
        # Approach 2: Different field names
        print("2. Testing: Different field names (attachment/image)")
        try:
            with open(image_path, 'rb') as f:
                response = await client.post(
                    chat_url,
                    files={'attachment': ('test.png', f, 'image/png')},
                    data={'message': 'Describe this image in detail.'}
                )
            
            print(f"   Status: {response.status_code}")
            if response.is_success:
                data = response.json()
                text_response = data.get('textResponse', '')
                keywords = ['blue', 'yellow', 'triangle', 'shape', 'color']
                found = [k for k in keywords if k.lower() in text_response.lower()]
                
                if found:
                    print(f"   🎯 SUCCESS! Found keywords: {found}")
                    print(f"   Response: {text_response[:200]}...")
                    return "multipart-attachment-message"
                else:
                    print(f"   Response: {text_response[:100]}...")
            else:
                print(f"   Error: {response.text[:200]}...")
        except Exception as e:
            print(f"   Exception: {e}")
        
        print()
        
        # Approach 3: Multiple files field
        print("3. Testing: Multiple files field")
        try:
            with open(image_path, 'rb') as f:
                response = await client.post(
                    chat_url,
                    files={'files': ('test.png', f, 'image/png')},
                    data={'message': 'What do you see?'}
                )
            
            print(f"   Status: {response.status_code}")
            if response.is_success:
                data = response.json()
                text_response = data.get('textResponse', '')
                keywords = ['blue', 'yellow', 'triangle', 'shape', 'color']
                found = [k for k in keywords if k.lower() in text_response.lower()]
                
                if found:
                    print(f"   🎯 SUCCESS! Found keywords: {found}")
                    print(f"   Response: {text_response[:200]}...")
                    return "multipart-files-message"
                else:
                    print(f"   Response: {text_response[:100]}...")
            else:
                print(f"   Error: {response.text[:200]}...")
        except Exception as e:
            print(f"   Exception: {e}")
        
        print()
    
    # Cleanup
    try:
        image_path.unlink()
    except Exception:
        pass
        
    return None

async def main():
    print("=== Testing Multipart Form Data for AnythingLLM ===")
    print("Based on Context7: Files are uploaded directly into chat")
    print()
    
    if not ALLM_API_KEY:
        print("❌ ANYTHINGLLM_API_KEY not set!")
        return
    
    working_approach = await test_multipart_approaches()
    
    if working_approach:
        print(f"\n🎉 FOUND WORKING APPROACH: {working_approach}")
        print("Now I can update the bridge to use multipart form data instead of JSON attachments!")
    else:
        print(f"\n❌ Multipart approaches didn't work either.")
        print("The issue might be deeper - possibly related to how AnythingLLM processes files internally.")

if __name__ == "__main__":
    asyncio.run(main())