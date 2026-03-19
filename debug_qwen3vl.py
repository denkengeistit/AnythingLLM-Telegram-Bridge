#!/usr/bin/env python3
"""
Debug specifically why Qwen3-VL isn't processing images through AnythingLLM
"""
import asyncio
import base64
import os
import tempfile
from pathlib import Path

import httpx
from PIL import Image, ImageDraw, ImageFont

ALLM_BASE_URL = os.environ.get("ANYTHINGLLM_BASE_URL", "http://localhost:3001").rstrip("/")
ALLM_API_KEY = os.environ.get("ANYTHINGLLM_API_KEY", "")
ALLM_WORKSPACE = os.environ.get("ANYTHINGLLM_WORKSPACE", "nanobot")

async def create_obvious_test_image() -> Path:
    """Create an image that should be VERY easy for vision AI to describe"""
    temp_dir = Path(tempfile.gettempdir())
    test_image_path = temp_dir / "qwen3vl_test.png"
    
    # Create a 400x300 image with VERY obvious content
    img = Image.new('RGB', (400, 300), color='white')
    draw = ImageDraw.Draw(img)
    
    # Draw very obvious shapes with bright colors
    draw.rectangle([50, 50, 150, 150], fill='red', outline='black', width=3)
    draw.rectangle([250, 50, 350, 150], fill='blue', outline='black', width=3)
    draw.rectangle([150, 200, 250, 280], fill='green', outline='black', width=3)
    
    # Add text that should be readable
    try:
        # Try to add text (may fail if no font available)
        draw.text((50, 20), "RED SQUARE", fill='red')
        draw.text((250, 20), "BLUE SQUARE", fill='blue') 
        draw.text((150, 180), "GREEN RECT", fill='green')
    except:
        # Font not available, but shapes should still be obvious
        pass
    
    img.save(test_image_path, 'PNG')
    print(f"Created obvious test image: {test_image_path}")
    return test_image_path

async def check_workspace_models():
    """Check exactly what models are configured"""
    
    async with httpx.AsyncClient(
        headers={"Authorization": f"Bearer {ALLM_API_KEY}"},
        timeout=30.0
    ) as client:
        
        print("=== Checking Workspace Model Configuration ===")
        
        try:
            response = await client.get(f"{ALLM_BASE_URL}/api/v1/workspace/{ALLM_WORKSPACE}")
            if response.is_success:
                data = response.json()
                workspace = data['workspace'][0] if isinstance(data['workspace'], list) else data['workspace']
                
                print(f"Workspace: {workspace.get('name')}")
                print(f"Chat Provider: {workspace.get('chatProvider')}")
                print(f"Chat Model: {workspace.get('chatModel')}")
                print(f"Agent Provider: {workspace.get('agentProvider')}")  
                print(f"Agent Model: {workspace.get('agentModel')}")
                print(f"Chat Mode: {workspace.get('chatMode')}")
                
                # Check model configuration (None means using system default)
                chat_model = workspace.get('chatModel')
                chat_provider = workspace.get('chatProvider')
                
                if not chat_model and not chat_provider:
                    print("ℹ️  Using system default chat model")
                    print("   This should work if system default is Qwen3-VL")
                else:
                    print(f"✓ Specific chat model configured: {chat_provider}/{chat_model}")
                    
                # Check agent model too
                agent_model = workspace.get('agentModel')
                if agent_model:
                    print(f"✓ Agent model: {agent_model}")
                    
                return True
                    
        except Exception as e:
            print(f"❌ Failed to check workspace: {e}")
            return False

async def test_vision_with_current_setup(image_path: Path):
    """Test vision with the exact setup we have"""
    
    # Read and encode image
    with open(image_path, 'rb') as f:
        image_data = f.read()
        base64_image = base64.b64encode(image_data).decode('utf-8')
    
    async with httpx.AsyncClient(
        headers={"Authorization": f"Bearer {ALLM_API_KEY}"},
        timeout=60.0
    ) as client:
        
        print(f"\n=== Testing Vision with Qwen3-VL ===")
        chat_url = f"{ALLM_BASE_URL}/api/v1/workspace/{ALLM_WORKSPACE}/chat"
        
        # Test the exact format our bridge uses
        test_payload = {
            "message": "What colors and shapes do you see in this image? Please describe each element in detail.",
            "attachments": [
                {
                    "type": "image",
                    "data": f"data:image/png;base64,{base64_image}",
                    "name": "test.png"
                }
            ]
        }
        
        print("Sending image with our bridge format...")
        try:
            response = await client.post(chat_url, json=test_payload)
            print(f"Status: {response.status_code}")
            
            if response.is_success:
                data = response.json()
                text_response = data.get('textResponse', '')
                
                print(f"Response: {text_response}")
                
                # Analyze the response
                if text_response:
                    # Check if it mentions the obvious elements from our test image
                    keywords = ['red', 'blue', 'green', 'square', 'rectangle', 'shape', 'color']
                    found_keywords = [kw for kw in keywords if kw.lower() in text_response.lower()]
                    
                    if found_keywords:
                        print(f"✅ VISION IS WORKING! Found keywords: {found_keywords}")
                        return True
                    elif "no relevant information" in text_response.lower():
                        print("❌ Getting 'no relevant information' - model not processing image")
                        return False
                    else:
                        print("⚠️  Got response but no vision keywords detected")
                        print("   This might indicate the model isn't seeing the image")
                        return False
                else:
                    print(f"❌ No text response. Full data: {data}")
                    return False
            else:
                print(f"❌ HTTP Error: {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Exception: {e}")
            return False

async def check_system_defaults():
    """Check system default model configuration"""
    
    async with httpx.AsyncClient(
        headers={"Authorization": f"Bearer {ALLM_API_KEY}"},
        timeout=30.0
    ) as client:
        
        print("\n=== Checking System Default Configuration ===")
        
        try:
            # Try to get system settings
            response = await client.get(f"{ALLM_BASE_URL}/api/v1/system/preferences")
            if response.is_success:
                data = response.json()
                print(f"System preferences found: {list(data.keys()) if isinstance(data, dict) else 'Not a dict'}")
            else:
                print(f"Could not get system preferences: {response.status_code}")
        except Exception as e:
            print(f"System preferences check failed: {e}")
            
        # Try LMStudio connection
        try:
            response = await client.get(f"{ALLM_BASE_URL}/api/v1/system/llm-providers")
            if response.is_success:
                data = response.json()
                print(f"Available LLM providers: {list(data.keys()) if isinstance(data, dict) else data}")
            else:
                print(f"Could not get LLM providers: {response.status_code}")
        except Exception as e:
            print(f"LLM providers check failed: {e}")

async def test_basic_chat_without_attachments():
    """Test if basic chat works (baseline)"""
    
    async with httpx.AsyncClient(
        headers={"Authorization": f"Bearer {ALLM_API_KEY}"},
        timeout=30.0
    ) as client:
        
        print(f"\n=== Testing Basic Chat (Baseline) ===")
        chat_url = f"{ALLM_BASE_URL}/api/v1/workspace/{ALLM_WORKSPACE}/chat"
        
        try:
            response = await client.post(chat_url, json={
                "message": "Hello! Please respond with exactly: I am working properly."
            })
            
            if response.is_success:
                data = response.json()
                text_response = data.get('textResponse', '')
                print(f"✅ Basic chat works: {text_response[:100]}...")
                return True
            else:
                print(f"❌ Basic chat failed: {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Basic chat exception: {e}")
            return False

async def main():
    print("=== Qwen3-VL Vision Debug ===")
    print(f"Base URL: {ALLM_BASE_URL}")
    print(f"Workspace: {ALLM_WORKSPACE}")
    print()
    
    if not ALLM_API_KEY:
        print("❌ ANYTHINGLLM_API_KEY not set!")
        return
    
    # Step 1: Check model configuration
    models_ok = await check_workspace_models()
    
    # Step 1b: Check system defaults
    await check_system_defaults()
    
    # Step 2: Test basic chat
    chat_ok = await test_basic_chat_without_attachments()
        
    if not chat_ok:
        print(f"\n❌ ISSUE FOUND: Basic chat not working")
        print("   Check AnythingLLM and LMStudio are running properly")
        return
    
    # Step 3: Test vision
    image_path = await create_obvious_test_image()
    
    try:
        vision_works = await test_vision_with_current_setup(image_path)
        
        if vision_works:
            print(f"\n🎉 SUCCESS: Vision is working!")
            print("   Your Telegram bridge should work for images now.")
        else:
            print(f"\n❌ ISSUE: Vision not working")
            print("   Possible causes:")
            print("   1. Chat model is not Qwen3-VL (check workspace settings)")
            print("   2. LMStudio model not loaded or not vision-capable")
            print("   3. AnythingLLM attachment format issue")
            
    finally:
        # Cleanup
        try:
            image_path.unlink()
            print(f"\n✓ Cleaned up test image")
        except Exception:
            pass

if __name__ == "__main__":
    asyncio.run(main())