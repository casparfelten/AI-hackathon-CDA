#!/usr/bin/env python3
"""
Simple test to verify Gemini client is working.
This just tests basic connectivity and a simple prompt.
"""

import asyncio
import sys
import time

from src.prolific_mcp.gemini_client import GeminiMCPClient


async def test_gemini_basic():
    """Test basic Gemini client functionality."""
    print("=" * 60)
    print("Simple Gemini Client Test")
    print("=" * 60)
    print()
    
    client = GeminiMCPClient()
    
    # Test 1: Connection
    print("Test 1: Connecting to MCP server...")
    start_time = time.time()
    try:
        await client.connect()
        elapsed = time.time() - start_time
        print(f"✓ Connected in {elapsed:.2f} seconds")
        print(f"  Found {len(client.mcp_tools)} MCP tools")
    except Exception as e:
        print(f"✗ Connection failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Test 2: Simple prompt (no tool calls)
    print("\nTest 2: Sending simple prompt (no tool calls)...")
    simple_prompt = "Say hello and tell me what MCP tools are available. Just list the tool names."
    print(f"  Prompt: {simple_prompt[:50]}...")
    
    start_time = time.time()
    try:
        response = await client.chat(simple_prompt)
        elapsed = time.time() - start_time
        print(f"✓ Response received in {elapsed:.2f} seconds")
        print(f"  Response length: {len(response)} characters")
        print(f"  Response preview: {response[:200]}...")
    except Exception as e:
        print(f"✗ Chat failed: {e}")
        import traceback
        traceback.print_exc()
        await client.close()
        return False
    
    # Test 3: Tool listing (just ask what tools exist)
    print("\nTest 3: Asking about available tools...")
    tool_prompt = "What MCP tools do you have access to? Just list their names."
    print(f"  Prompt: {tool_prompt}")
    
    start_time = time.time()
    try:
        response = await client.chat(tool_prompt)
        elapsed = time.time() - start_time
        print(f"✓ Response received in {elapsed:.2f} seconds")
        print(f"  Response: {response[:300]}...")
    except Exception as e:
        print(f"✗ Chat failed: {e}")
        import traceback
        traceback.print_exc()
        await client.close()
        return False
    
    # Cleanup
    print("\nCleaning up...")
    await client.close()
    print("✓ Client closed")
    
    print("\n" + "=" * 60)
    print("All basic tests passed!")
    print("=" * 60)
    return True


if __name__ == "__main__":
    try:
        success = asyncio.run(test_gemini_basic())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nUnexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

