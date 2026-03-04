#!/usr/bin/env python3
"""
Debug VL (Vision Language) model configuration in AnythingLLM
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
    """Create a clear test image that should be easy for AI to describe"""
    temp_dir = Path(tempfile.gettempdir())
    test_image_path = temp_dir / "vl_debug_image.png"
    
    # Create a 300x200 image with clear, describable content
    img = Image.new('RGB', (300, 200), color='white')
    draw = ImageDraw.Draw(img)
    
    # Draw simple shapes with clear colors
    draw.rectangle([20, 20, 100, 80], fill='red', outline='black', width=2)
    draw.rectangle([120, 20, 200, 80], fill='blue', outline='black', width=2)  
    draw.rectangle([220, 20, 280, 80], fill='green', outline='black', width=2)
    
    # Add some text-like elements
    draw.rectangle([20, 100, 280, 120], fill='yellow', outline='black', width=1)
    draw.rectangle([20, 140, 280, 180], fill='purple', outline='black', width=1)
    
    img.save(test_image_path, 'PNG')
    print(f"Created test image: {test_image_path}")
    return test_image_path

async def check_workspace_config():
    """Check workspace configuration for vision capabilities"""
    
    async with httpx.AsyncClient(
        headers={"Authorization": f"Bearer {ALLM_API_KEY}"},
        timeout=30.0
    ) as client:
        
        print("=== Checking Workspace Configuration ===")
        
        # Get workspace details
        try:
            response = await client.get(f"{ALLM_BASE_URL}/api/v1/workspace/{ALLM_WORKSPACE}")
            if response.is_success:
                data = response.json()
                workspace = data['workspace'][0] if isinstance(data['workspace'], list) else data['workspace']
                
                print(f"✓ Workspace: {workspace.get('name', 'Unknown')}")
                print(f"  Chat Provider: {workspace.get('chatProvider', 'Not set')}")
                print(f"  Chat Model: {workspace.get('chatModel', 'Not set')}")
                print(f"  Agent Provider: {workspace.get('agentProvider', 'Not set')}")
                print(f"  Agent Model: {workspace.get('agentModel', 'Not set')}")
                print(f"  Chat Mode: {workspace.get('chatMode', 'chat')}")
                
                # Check if this looks like a vision-capable setup
                chat_model = workspace.get('chatModel', '').lower()
                agent_model = workspace.get('agentModel', '').lower()
                
                vision_indicators = ['vision', 'gpt-4', 'claude', 'gemini', 'llava', 'minicpm']
                has_vision = any(indicator in chat_model or indicator in agent_model 
                               for indicator in vision_indicators)
                
                if has_vision:
                    print("✓ Appears to have vision-capable model")
                else:
                    print("⚠️  May not have vision-capable model configured")
                    print(f"   Chat model: {chat_model}")
                    print(f"   Agent model: {agent_model}")
                
                return workspace
            else:
                print(f"❌ Failed to get workspace: {response.status_code}")
                print(f"   Error: {response.text}")
                return None
                
        except Exception as e:
            print(f"❌ Exception checking workspace: {e}")
            return None

async def test_vision_chat(image_path: Path):
    """Test vision capabilities with a direct chat request"""
    
    # Read and encode image
    with open(image_path, 'rb') as f:
        image_data = f.read()
        base64_image = base64.b64encode(image_data).decode('utf-8')
    
    # Test different message approaches
    test_cases = [
        {
            "name": "Simple vision test",
            "payload": {
                "message": "What colors and shapes do you see in this image? Please describe each element.",
                "attachments": [
                    {
                        "type": "image",
                        "data": f"data:image/png;base64,{base64_image}",
                        "name": "test_image.png"
                    }
                ]
            }
        },
        {
            "name": "Vision test without @agent",  
            "payload": {
                "message": "Describe this image in detail. What shapes and colors are visible?",
                "mode": "chat",
                "attachments": [
                    {
                        "type": "image", 
                        "data": f"data:image/png;base64,{base64_image}",
                        "name": "test_image.png"
                    }
                ]
            }
        },
        {
            "name": "Vision test with @agent prefix",
            "payload": {
                "message": "@agent Analyze this image and describe what you see. Focus on colors and shapes.",
                "attachments": [
                    {
                        "type": "image",
                        "data": f"data:image/png;base64,{base64_image}",
                        "name": "test_image.png"
                    }
                ]
            }
        }
    ]
    
    async with httpx.AsyncClient(
        headers={"Authorization": f"Bearer {ALLM_API_KEY}"},
        timeout=60.0
    ) as client:
        
        print(f"\n=== Testing Vision Chat ===")
        chat_url = f"{ALLM_BASE_URL}/api/v1/workspace/{ALLM_WORKSPACE}/chat"
        
        for test_case in test_cases:
            print(f"\n🧪 {test_case['name']}:")
            try:
                response = await client.post(chat_url, json=test_case['payload'])
                print(f"   Status: {response.status_code}")
                
                if response.is_success:
                    data = response.json()
                    text_response = data.get('textResponse', '')
                    
                    if text_response:
                        print(f"   ✅ Response: {text_response[:200]}...")
                        
                        # Check if the response suggests vision processing
                        vision_keywords = ['color', 'shape', 'rectangle', 'red', 'blue', 'green', 'image', 'see', 'visual']
                        has_vision_content = any(keyword.lower() in text_response.lower() 
                                               for keyword in vision_keywords)
                        
                        if has_vision_content:
                            print("   🎯 Response contains vision-related content!")
                        else:
                            print("   ⚠️  Response doesn't seem vision-aware")
                    else:
                        print(f"   ❌ No text response: {data}")
                else:
                    print(f"   ❌ Failed: {response.text[:200]}")
                    
            except Exception as e:
                print(f"   ❌ Exception: {e}")

async def test_text_only_chat():
    """Test basic text chat to compare with vision chat"""
    
    async with httpx.AsyncClient(
        headers={"Authorization": f"Bearer {ALLM_API_KEY}"},
        timeout=30.0
    ) as client:
        
        print(f"\n=== Testing Text-Only Chat (Baseline) ===")
        chat_url = f"{ALLM_BASE_URL}/api/v1/workspace/{ALLM_WORKSPACE}/chat"
        
        try:
            response = await client.post(chat_url, json={
                "message": "Hello! Can you see and analyze images?"
            })
            
            print(f"Status: {response.status_code}")
            if response.is_success:
                data = response.json()
                text_response = data.get('textResponse', '')
                print(f"✅ Text response: {text_response[:200]}...")
            else:
                print(f"❌ Failed: {response.text[:200]}")
                
        except Exception as e:
            print(f"❌ Exception: {e}")

async def main():
    print("=== AnythingLLM Vision Model Debug ===")
    print(f"Base URL: {ALLM_BASE_URL}")
    print(f"Workspace: {ALLM_WORKSPACE}")
    print(f"API Key: {ALLM_API_KEY[:10]}..." if ALLM_API_KEY else "API Key: NOT SET")
    print()
    
    if not ALLM_API_KEY:
        print("❌ ANYTHINGLLM_API_KEY not set!")
        return
    
    # Check workspace configuration
    workspace_config = await check_workspace_config()
    
    # Test basic text chat first
    await test_text_only_chat()
    
    # Create and test with image
    image_path = await create_test_image()
    
    try:
        await test_vision_chat(image_path)
    finally:
        # Cleanup
        try:
            image_path.unlink()
            print("\n✓ Cleaned up test image")
        except Exception:
            pass
    
    # Summary and recommendations
    print(f"\n=== Summary & Recommendations ===")
    print("If vision responses don't describe the image content:")
    print("1. Check that your AnythingLLM workspace uses a vision-capable model")
    print("2. Verify the model is properly configured and running")
    print("3. Test vision directly in AnythingLLM web UI first")
    print("4. Check AnythingLLM logs for any vision processing errors")

if __name__ == "__main__":
    asyncio.run(main())