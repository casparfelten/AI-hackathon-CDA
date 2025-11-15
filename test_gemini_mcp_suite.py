#!/usr/bin/env python3
"""
Gemini MCP Integration Test Suite

This test suite validates Gemini's ability to use MCP tools to create studies.
It asks Gemini to create a draft study with two URL options (example.com/1 and example.com/2)
to test which performs better.
"""

import asyncio
import json
import re
import sys
import time
from typing import Any, Optional

from src.prolific_mcp.gemini_client import GeminiMCPClient


class Colors:
    """ANSI color codes for terminal output."""
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'
    BOLD = '\033[1m'


def print_test(name: str):
    """Print test header."""
    print(f"\n{Colors.BLUE}{Colors.BOLD}=== {name} ==={Colors.RESET}")


def print_success(message: str):
    """Print success message."""
    print(f"{Colors.GREEN}✓ {message}{Colors.RESET}")


def print_error(message: str):
    """Print error message."""
    print(f"{Colors.RED}✗ {message}{Colors.RESET}")


def print_info(message: str):
    """Print info message."""
    print(f"{Colors.YELLOW}ℹ {message}{Colors.RESET}")


def print_verbose(message: str):
    """Print verbose/debug message."""
    print(f"{Colors.YELLOW}  → {message}{Colors.RESET}")


def extract_study_id(text: str) -> Optional[str]:
    """Extract study ID from Gemini response."""
    # Look for study ID pattern (24 character hex string)
    pattern = r'[0-9a-f]{24}'
    matches = re.findall(pattern, text, re.IGNORECASE)
    if matches:
        return matches[0]
    return None


def verify_study_created(response: str) -> tuple[bool, Optional[str]]:
    """Verify that Gemini created a study and extract study ID."""
    # Check for success indicators
    success_indicators = [
        "created successfully",
        "study id",
        "study_id",
        "created study",
    ]
    
    has_success = any(indicator.lower() in response.lower() for indicator in success_indicators)
    study_id = extract_study_id(response)
    
    return has_success, study_id


async def test_gemini_create_study() -> tuple[bool, Optional[str], str]:
    """Test Gemini creating a study with two URL options."""
    print_test("Test: Gemini Creates Study with Two URL Options")
    
    client = GeminiMCPClient()
    
    prompt = """Create a TEST STUDY (not a real study) to test which URL performs better. 
This is for testing purposes only and will not consume any credits.

Create a test study with two URL options: example.com/1 and example.com/2. 
Fill in all required fields appropriately including:
- A descriptive name about testing two URL options (include "TEST" in the name)
- A clear description explaining this is a test study
- Appropriate reward amount (in cents) - can be minimal since it's a test
- Estimated completion time
- Set the external_study_url appropriately (you can use example.com/1 or example.com/2)
- Use study_type SINGLE
- Add study_labels as ["survey"]
- Set total_available_places to 1 (just for testing)
- Include completion codes

IMPORTANT: This is a TEST STUDY. Test studies do not consume credits and should NOT be deleted.
1. First, create the study as a draft using prolific_create_study
2. Then, if available, use prolific_launch_test_study to launch it in test mode (this doesn't consume credits)
3. The study should be fully completed as a test (not left as draft)
4. Do NOT delete the test study - test studies can remain for future testing"""

    print_verbose("Connecting to MCP server...")
    print_verbose("Starting MCP server subprocess...")
    try:
        await client.connect()
        print_success("Connected to MCP server")
        print_verbose(f"Found {len(client.mcp_tools)} MCP tools")
        print_verbose("Available MCP tools:")
        for tool in client.mcp_tools[:5]:  # Show first 5 tools
            print_verbose(f"  - {tool.get('name', 'unknown')}")
        if len(client.mcp_tools) > 5:
            print_verbose(f"  ... and {len(client.mcp_tools) - 5} more tools")
    except Exception as e:
        print_error(f"Failed to connect to MCP server: {str(e)}")
        import traceback
        print_verbose("Connection error traceback:")
        traceback.print_exc()
        return False, None, str(e)
    
    print_verbose("\nSending prompt to Gemini...")
    print_verbose("=" * 60)
    print_verbose("PROMPT:")
    print(prompt)
    print_verbose("=" * 60)
    print_verbose("Waiting for Gemini response (this may take a while)...")
    print_verbose("Gemini will use MCP tools to create the study...")
    
    start_time = time.time()
    try:
        print_verbose("\n[Gemini is processing...]")
        response = await client.chat(prompt)
        elapsed = time.time() - start_time
        
        print_verbose(f"\nGemini response received in {elapsed:.2f} seconds")
        print_verbose("=" * 60)
        print_verbose("FULL GEMINI RESPONSE:")
        print_verbose("=" * 60)
        print(response)
        print_verbose("=" * 60)
        
        # Verify study was created
        print_verbose("\nAnalyzing Gemini response...")
        success, study_id = verify_study_created(response)
        
        if success:
            print_success("Gemini successfully created a study")
            if study_id:
                print_success(f"Study ID extracted: {study_id}")
                print_verbose(f"Study ID pattern found: {study_id}")
            else:
                print_info("Could not extract study ID from response, but study appears to be created")
                print_verbose("Attempting to find study ID in response text...")
                # Try to find any study ID patterns
                potential_ids = re.findall(r'[0-9a-f]{24}', response, re.IGNORECASE)
                if potential_ids:
                    print_verbose(f"Found potential study IDs: {potential_ids}")
        else:
            print_error("Gemini response does not indicate successful study creation")
            print_verbose("Response may need manual review")
            print_verbose("Searching for success indicators in response...")
        
        # Check for key requirements
        checks = {
            "Two URLs mentioned": any(url in response.lower() for url in ["example.com/1", "example.com/2"]),
            "Test study mentioned": "test" in response.lower(),
            "Study created": success,
        }
        
        print_verbose("\nVerification checks:")
        for check_name, check_result in checks.items():
            if check_result:
                print_success(f"  {check_name}")
            else:
                print_error(f"  {check_name}")
        
        return success, study_id, response
        
    except Exception as e:
        print_error(f"Error during Gemini chat: {str(e)}")
        import traceback
        print_verbose("Exception traceback:")
        traceback.print_exc()
        return False, None, str(e)
    finally:
        await client.close()


async def verify_study_details(study_id: str) -> bool:
    """Verify study details by getting it via MCP."""
    print_test("Verify Study Details")
    
    if not study_id:
        print_error("No study ID provided")
        return False
    
    # Use direct MCP call to verify
    from src.prolific_mcp.server import call_tool
    
    try:
        result = await call_tool("prolific_get_study", {"study_id": study_id})
        
        if result and len(result) > 0:
            response_text = result[0].text
            print_success("Successfully retrieved study details")
            
            # Parse study data
            try:
                json_start = response_text.find("{")
                if json_start != -1:
                    json_str = response_text[json_start:]
                    study_data = json.loads(json_str)
                    
                    print_verbose("Study details:")
                    print_verbose(f"  Name: {study_data.get('name')}")
                    print_verbose(f"  Status: {study_data.get('status')}")
                    print_verbose(f"  URL: {study_data.get('external_study_url')}")
                    print_verbose(f"  Places: {study_data.get('total_available_places')}")
                    print_verbose(f"  Reward: {study_data.get('reward')} cents")
                    
                    # Verify it's a test study (check name or status)
                    study_name = study_data.get('name', '').lower()
                    study_status = study_data.get('status', '')
                    
                    if 'test' in study_name:
                        print_success("Study name indicates it's a test study")
                    else:
                        print_info(f"Study name: {study_data.get('name')}")
                    
                    print_verbose(f"Study status: {study_status}")
                    print_info("Note: Test studies should not be deleted (they consume no credits)")
                    
                    return True
            except json.JSONDecodeError:
                print_error("Could not parse study data")
                return False
        else:
            print_error("Empty response from get_study")
            return False
            
    except Exception as e:
        print_error(f"Failed to get study: {str(e)}")
        return False


async def verify_test_study_complete(study_id: str) -> bool:
    """Verify test study is complete (test studies should not be deleted)."""
    print_test("Verify Test Study Complete")
    
    if not study_id:
        print_info("No study ID to verify")
        return True
    
    from src.prolific_mcp.server import call_tool
    
    try:
        result = await call_tool("prolific_get_study", {"study_id": study_id})
        
        if result and len(result) > 0:
            response_text = result[0].text
            
            # Parse study data
            try:
                json_start = response_text.find("{")
                if json_start != -1:
                    json_str = response_text[json_start:]
                    study_data = json.loads(json_str)
                    
                    status = study_data.get('status', '')
                    print_verbose(f"Test study status: {status}")
                    
                    # Test studies can be in various states - just verify it exists
                    print_success("Test study exists and is accessible")
                    print_info("Test studies are NOT deleted (they consume no credits)")
                    print_info(f"Test study ID: {study_id}")
                    return True
            except json.JSONDecodeError:
                print_error("Could not parse study data")
                return False
        else:
            print_error("Empty response from get_study")
            return False
            
    except Exception as e:
        print_error(f"Failed to get study: {str(e)}")
        return False


async def main():
    """Run Gemini MCP integration tests."""
    print(f"\n{Colors.BOLD}{Colors.BLUE}")
    print("=" * 60)
    print("Gemini MCP Integration Test Suite")
    print("=" * 60)
    print(f"{Colors.RESET}\n")
    
    print_verbose("This test suite validates Gemini's ability to:")
    print_verbose("1. Connect to MCP server")
    print_verbose("2. Use MCP tools to create a TEST STUDY")
    print_verbose("3. Fill in required fields appropriately")
    print_verbose("4. Create and complete test study (test studies consume no credits)")
    print_verbose("5. Test studies are NOT deleted (they can remain for testing)")
    print()
    
    suite_start_time = time.time()
    results = []
    study_id = None
    
    try:
        # Test: Gemini creates study
        success, extracted_study_id, response = await test_gemini_create_study()
        results.append(("Gemini Creates Study", success))
        study_id = extracted_study_id
        
        if success and study_id:
            # Verify study details
            verify_success = await verify_study_details(study_id)
            results.append(("Verify Study Details", verify_success))
            
            # Verify test study is complete (test studies are NOT deleted)
            test_complete = await verify_test_study_complete(study_id)
            results.append(("Verify Test Study Complete", test_complete))
        elif success:
            print_info("Study appears to be created but ID not extracted - skipping verification")
        else:
            print_error("Study creation failed - skipping verification and cleanup")
    
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}Test suite interrupted by user{Colors.RESET}")
        if study_id:
            print_info(f"Note: Test study {study_id} exists (test studies are not deleted)")
    except Exception as e:
        print_error(f"Unexpected error: {str(e)}")
        import traceback
        traceback.print_exc()
        if study_id:
            print_info(f"Note: Test study {study_id} exists (test studies are not deleted)")
    
    suite_elapsed = time.time() - suite_start_time
    
    # Print summary
    print(f"\n{Colors.BOLD}{Colors.BLUE}")
    print("=" * 60)
    print("Test Summary")
    print("=" * 60)
    print(f"{Colors.RESET}\n")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    print_verbose(f"Test suite execution time: {suite_elapsed:.2f} seconds")
    print_verbose(f"Tests run: {total}, Passed: {passed}, Failed: {total - passed}")
    print()
    
    for test_name, result in results:
        status = f"{Colors.GREEN}PASS{Colors.RESET}" if result else f"{Colors.RED}FAIL{Colors.RESET}"
        print(f"{status} - {test_name}")
    
    print(f"\n{Colors.BOLD}Total: {passed}/{total} tests passed{Colors.RESET}\n")
    
    if passed == total:
        print(f"{Colors.GREEN}All tests passed! ✓{Colors.RESET}\n")
        return 0
    else:
        print(f"{Colors.YELLOW}Some tests failed. Please review the output above.{Colors.RESET}\n")
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))

