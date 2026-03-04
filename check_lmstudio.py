#!/usr/bin/env python3
"""
Check LMStudio directly to see what models are loaded
"""
import asyncio
import httpx

# LMStudio typically runs on port 1234
LMSTUDIO_URL = "http://localhost:1234"

async def check_lmstudio():
    """Check LMStudio directly"""
    
    async with httpx.AsyncClient(timeout=10.0) as client:
        
        print("=== Checking LMStudio Directly ===")
        
        # Check if LMStudio is running
        try:
            response = await client.get(f"{LMSTUDIO_URL}/v1/models")
            if response.is_success:
                models = response.json()
                print("✅ LMStudio is running")
                print(f"Available models: {models}")
                
                # Check if any models are loaded
                if models.get('data'):
                    for model in models['data']:
                        print(f"  📋 Model: {model.get('id', 'Unknown')}")
                        print(f"      Created: {model.get('created', 'Unknown')}")
                else:
                    print("❌ No models loaded in LMStudio!")
                    
            else:
                print(f"❌ LMStudio responded with error: {response.status_code}")
                
        except Exception as e:
            print(f"❌ Cannot reach LMStudio: {e}")
            print("   Make sure LMStudio is running on port 1234")
            
        # Test a direct chat with LMStudio
        print(f"\n=== Testing Direct LMStudio Chat ===")
        try:
            response = await client.post(f"{LMSTUDIO_URL}/v1/chat/completions", json={
                "model": "any",  # LMStudio ignores this usually
                "messages": [
                    {"role": "user", "content": "Hello, what model are you and can you see images?"}
                ]
            })
            
            if response.is_success:
                data = response.json()
                message = data.get('choices', [{}])[0].get('message', {}).get('content', '')
                print(f"✅ LMStudio responds: {message[:200]}...")
            else:
                print(f"❌ LMStudio chat failed: {response.status_code} - {response.text}")
                
        except Exception as e:
            print(f"❌ LMStudio chat error: {e}")

async def test_lmstudio_vision():
    """Test if LMStudio can handle vision"""
    
    # Simple base64 encoded 1x1 red pixel
    tiny_red_pixel = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChAFE0gWyEwAAAABJRU5ErkJggg=="
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        
        print(f"\n=== Testing LMStudio Vision Capabilities ===")
        
        # Test OpenAI-style vision format
        try:
            response = await client.post(f"{LMSTUDIO_URL}/v1/chat/completions", json={
                "model": "any",
                "messages": [
                    {
                        "role": "user", 
                        "content": [
                            {"type": "text", "text": "What color is this image?"},
                            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{tiny_red_pixel}"}}
                        ]
                    }
                ]
            })
            
            if response.is_success:
                data = response.json()
                message = data.get('choices', [{}])[0].get('message', {}).get('content', '')
                print(f"✅ LMStudio vision test: {message[:200]}...")
                
                # Check if the response mentions red or color
                if any(word in message.lower() for word in ['red', 'color', 'pixel', 'image']):
                    print("🎯 LMStudio appears to support vision!")
                else:
                    print("⚠️  LMStudio responded but may not be processing the image")
                    
            else:
                print(f"❌ LMStudio vision test failed: {response.status_code}")
                
        except Exception as e:
            print(f"❌ LMStudio vision test error: {e}")

async def main():
    print("=== LMStudio Model Check ===")
    print("This will check what's actually running in LMStudio")
    print()
    
    await check_lmstudio()
    await test_lmstudio_vision()
    
    print(f"\n=== Summary ===")
    print("If LMStudio shows a non-vision model loaded:")
    print("1. Load your Qwen3-VL-30B-A3B model in LMStudio")  
    print("2. Make sure it's set as the default/active model")
    print("3. Configure AnythingLLM to use LMStudio with the correct model")

if __name__ == "__main__":
    asyncio.run(main())