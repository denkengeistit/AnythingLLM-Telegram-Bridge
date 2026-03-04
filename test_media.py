#!/usr/bin/env python3
"""
Test script for media functionality
Tests the photo processing pipeline without requiring Telegram
"""

import asyncio
import tempfile
from pathlib import Path
from PIL import Image
import sys
import os

# Add the current directory to path to import our functions
sys.path.insert(0, os.path.dirname(__file__))

# Mock the required functions for testing
async def test_image_processing():
    """Test image processing functionality"""
    print("🧪 Testing image processing...")
    
    # Create a test image
    test_image_path = Path(tempfile.gettempdir()) / "test_image.png"
    
    # Create a simple test image
    img = Image.new('RGB', (800, 600), color='red')
    img.save(test_image_path, 'PNG')
    
    print(f"✅ Created test image: {test_image_path}")
    
    # Test our _process_image function
    try:
        from telegram_anythingllm_bridge import _process_image
        description = await _process_image(test_image_path)
        print(f"✅ Image description: {description}")
    except Exception as e:
        print(f"❌ Image processing failed: {e}")
    
    # Clean up
    test_image_path.unlink()
    print("✅ Cleaned up test image")

async def test_temp_directory():
    """Test temp directory creation"""
    print("🧪 Testing temp directory creation...")
    
    temp_dir = Path(tempfile.gettempdir()) / "anythingllm_bridge"
    temp_dir.mkdir(exist_ok=True)
    
    if temp_dir.exists():
        print(f"✅ Temp directory created: {temp_dir}")
    else:
        print(f"❌ Failed to create temp directory: {temp_dir}")

async def main():
    print("🚀 Starting media functionality tests...\n")
    
    await test_temp_directory()
    print()
    await test_image_processing()
    
    print("\n✅ All tests completed!")

if __name__ == "__main__":
    asyncio.run(main())