#!/usr/bin/env python3
"""Diagnostic script to test MCP server connection and tool discovery."""

import json
import subprocess
import sys
import os

def test_mcp_server():
    """Test the MCP server connection and tool discovery."""
    print("=" * 60)
    print("MCP Server Diagnostic Test")
    print("=" * 60)
    
    # Get paths
    project_root = "/home/bitzaven/CodingProjects/AI-hackathon-CDA"
    python_path = os.path.join(project_root, "venv", "bin", "python")
    
    print(f"\n1. Checking Python path: {python_path}")
    if not os.path.exists(python_path):
        print(f"   ✗ Python not found at {python_path}")
        return False
    print(f"   ✓ Python found")
    
    print(f"\n2. Checking .env file")
    env_path = os.path.join(project_root, ".env")
    if not os.path.exists(env_path):
        print(f"   ✗ .env file not found at {env_path}")
        return False
    print(f"   ✓ .env file found")
    
    print(f"\n3. Testing module import")
    try:
        result = subprocess.run(
            [python_path, "-c", "from prolific_mcp.server import server; print('OK')"],
            cwd=project_root,
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode != 0:
            print(f"   ✗ Import failed:")
            print(f"   {result.stderr}")
            return False
        print(f"   ✓ Module imports successfully")
    except Exception as e:
        print(f"   ✗ Import error: {e}")
        return False
    
    print(f"\n4. Testing MCP protocol handshake")
    try:
        proc = subprocess.Popen(
            [python_path, "-m", "prolific_mcp.server"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=project_root
        )
        
        # Step 1: Initialize
        init_request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "diagnostic", "version": "1.0"}
            }
        }
        proc.stdin.write(json.dumps(init_request) + "\n")
        proc.stdin.flush()
        
        init_response = proc.stdout.readline()
        if not init_response:
            print(f"   ✗ No response to initialize")
            proc.terminate()
            return False
        
        init_data = json.loads(init_response)
        if "error" in init_data:
            print(f"   ✗ Initialize error: {init_data['error']}")
            proc.terminate()
            return False
        print(f"   ✓ Initialize successful")
        
        # Step 2: Send initialized notification
        initialized_notification = {
            "jsonrpc": "2.0",
            "method": "notifications/initialized"
        }
        proc.stdin.write(json.dumps(initialized_notification) + "\n")
        proc.stdin.flush()
        
        # Step 3: List tools
        tools_request = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/list",
            "params": {}
        }
        proc.stdin.write(json.dumps(tools_request) + "\n")
        proc.stdin.flush()
        
        tools_response = proc.stdout.readline()
        if not tools_response:
            print(f"   ✗ No response to tools/list")
            proc.terminate()
            return False
        
        tools_data = json.loads(tools_response)
        if "error" in tools_data:
            print(f"   ✗ Tools/list error: {tools_data['error']}")
            proc.terminate()
            return False
        
        if "result" in tools_data and "tools" in tools_data["result"]:
            tools = tools_data["result"]["tools"]
            print(f"   ✓ Found {len(tools)} tools")
            print(f"\n   Available tools:")
            for tool in tools:
                print(f"     - {tool['name']}")
        else:
            print(f"   ✗ No tools in response")
            proc.terminate()
            return False
        
        proc.terminate()
        proc.wait()
        
    except Exception as e:
        print(f"   ✗ Protocol test error: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    print(f"\n" + "=" * 60)
    print("✓ All tests passed! Server is working correctly.")
    print("=" * 60)
    print(f"\nFor your MCP client, use this configuration:")
    print(f"\n{json.dumps({")
    print(f'  "mcpServers": {{')
    print(f'    "prolific": {{')
    print(f'      "command": "{python_path}",')
    print(f'      "args": ["-m", "prolific_mcp.server"],')
    print(f'      "cwd": "{project_root}"')
    print(f'    }}')
    print(f'  }}')
    print(f'}}, indent=2)}')
    print()
    
    return True

if __name__ == "__main__":
    success = test_mcp_server()
    sys.exit(0 if success else 1)


