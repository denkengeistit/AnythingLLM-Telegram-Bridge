#!/usr/bin/env python3
"""
Explore AnythingLLM API endpoints to find the correct upload path
"""
import asyncio
import os
import httpx

ALLM_BASE_URL = os.environ.get("ANYTHINGLLM_BASE_URL", "http://localhost:3001").rstrip("/")
ALLM_API_KEY = os.environ.get("ANYTHINGLLM_API_KEY", "")
ALLM_WORKSPACE = os.environ.get("ANYTHINGLLM_WORKSPACE", "nanobot")

async def test_endpoints():
    """Test various upload endpoint possibilities"""
    
    test_endpoints = [
        f"/api/v1/workspace/{ALLM_WORKSPACE}/upload",
        f"/api/v1/workspace/{ALLM_WORKSPACE}/document-upload",
        f"/api/v1/workspace/{ALLM_WORKSPACE}/documents/upload",
        f"/api/v1/document/upload",
        f"/api/v1/documents/upload",
        f"/api/v1/upload",
        f"/api/v1/system/upload",
        f"/api/document/upload",
        f"/api/documents/upload",
        f"/api/upload"
    ]
    
    async with httpx.AsyncClient(
        headers={"Authorization": f"Bearer {ALLM_API_KEY}"},
        timeout=10.0
    ) as client:
        
        print("=== Testing Upload Endpoints ===")
        for endpoint in test_endpoints:
            url = f"{ALLM_BASE_URL}{endpoint}"
            try:
                # Test with GET first to see if endpoint exists
                response = await client.get(url)
                status = response.status_code
                if status != 404:
                    print(f"✓ {endpoint} -> {status} (exists!)")
                    if status == 405:  # Method not allowed - probably needs POST
                        print(f"  → Likely needs POST method")
                else:
                    print(f"✗ {endpoint} -> 404")
            except Exception as e:
                print(f"✗ {endpoint} -> Exception: {e}")

async def test_workspace_endpoints():
    """Test workspace-specific endpoints"""
    
    async with httpx.AsyncClient(
        headers={"Authorization": f"Bearer {ALLM_API_KEY}"},
        timeout=10.0
    ) as client:
        
        print("\n=== Testing Workspace Endpoints ===")
        
        # List all workspaces to see available actions
        try:
            response = await client.get(f"{ALLM_BASE_URL}/api/v1/workspaces")
            if response.is_success:
                data = response.json()
                print(f"Available workspaces: {[w.get('name', w.get('slug', 'unknown')) for w in data.get('workspaces', [])]}")
        except Exception as e:
            print(f"Failed to list workspaces: {e}")
            
        # Check workspace-specific endpoints
        workspace_endpoints = [
            f"/api/v1/workspace/{ALLM_WORKSPACE}",
            f"/api/v1/workspace/{ALLM_WORKSPACE}/chat",
            f"/api/v1/workspace/{ALLM_WORKSPACE}/documents", 
            f"/api/v1/workspace/{ALLM_WORKSPACE}/update",
        ]
        
        for endpoint in workspace_endpoints:
            url = f"{ALLM_BASE_URL}{endpoint}"
            try:
                response = await client.get(url)
                status = response.status_code
                print(f"{endpoint} -> {status}")
                if status == 200:
                    data = response.json()
                    if isinstance(data, dict):
                        print(f"  Keys: {list(data.keys())}")
            except Exception as e:
                print(f"{endpoint} -> Exception: {e}")

async def main():
    print(f"Base URL: {ALLM_BASE_URL}")
    print(f"Workspace: {ALLM_WORKSPACE}")
    print(f"API Key: {ALLM_API_KEY[:10]}..." if ALLM_API_KEY else "API Key: NOT SET")
    print()
    
    if not ALLM_API_KEY:
        print("❌ ANYTHINGLLM_API_KEY not set!")
        return
        
    await test_endpoints()
    await test_workspace_endpoints()

if __name__ == "__main__":
    asyncio.run(main())