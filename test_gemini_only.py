#!/usr/bin/env python3
"""
Simple test to verify Gemini API is working (without MCP).
This just tests basic Gemini connectivity.
"""

import asyncio
import sys
import time

from google import genai
from src.prolific_mcp.config import config


async def test_gemini_only():
    """Test Gemini API directly without MCP."""
    print("=" * 60)
    print("Simple Gemini API Test (No MCP)")
    print("=" * 60)
    print()
    
    # Validate config
    try:
        config.validate_gemini()
    except Exception as e:
        print(f"✗ Configuration error: {e}")
        return False
    
    # Initialize Gemini client
    print("Initializing Gemini client...")
    client = genai.Client(api_key=config.gemini_api_key)
    print("✓ Gemini client initialized")
    
    # Test 1: Simple prompt (no tools)
    print("\n" + "=" * 60)
    print("Test 1: Simple prompt (no function calling)")
    print("=" * 60)
    simple_prompt = "Say hello in one sentence."
    print(f"Prompt: {simple_prompt}")
    print()
    
    start_time = time.time()
    try:
        print("[Test] Sending request to Gemini...")
        response = client.models.generate_content(
            model="gemini-2.0-flash-exp",
            contents=simple_prompt,
        )
        elapsed = time.time() - start_time
        print(f"[Test] ✓ Response received (took {elapsed:.2f} seconds)")
        
        if response.candidates and response.candidates[0].content.parts:
            response_text = "".join([
                part.text for part in response.candidates[0].content.parts 
                if hasattr(part, 'text') and part.text
            ])
            print(f"Response length: {len(response_text)} characters")
            print(f"Response: {response_text}")
            print("✓ Test 1 passed")
        else:
            print("✗ No response content")
            return False
            
    except Exception as e:
        print(f"✗ Test 1 failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Test 2: Another simple prompt
    print("\n" + "=" * 60)
    print("Test 2: Another simple prompt")
    print("=" * 60)
    prompt2 = "What is 2+2? Answer in one word."
    print(f"Prompt: {prompt2}")
    print()
    
    start_time = time.time()
    try:
        print("[Test] Sending request to Gemini...")
        response = client.models.generate_content(
            model="gemini-2.0-flash-exp",
            contents=prompt2,
        )
        elapsed = time.time() - start_time
        print(f"[Test] ✓ Response received (took {elapsed:.2f} seconds)")
        
        if response.candidates and response.candidates[0].content.parts:
            response_text = "".join([
                part.text for part in response.candidates[0].content.parts 
                if hasattr(part, 'text') and part.text
            ])
            print(f"Response: {response_text}")
            print("✓ Test 2 passed")
        else:
            print("✗ No response content")
            return False
            
    except Exception as e:
        print(f"✗ Test 2 failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    print("\n" + "=" * 60)
    print("All Gemini API tests passed!")
    print("=" * 60)
    return True


if __name__ == "__main__":
    try:
        success = asyncio.run(test_gemini_only())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nUnexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

