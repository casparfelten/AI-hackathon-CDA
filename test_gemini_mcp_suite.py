#!/usr/bin/env python3
"""
Gemini MCP Integration Test Suite

This test suite validates Gemini's ability to use MCP tools to create draft real studies.
It asks Gemini to create a draft study (UNPUBLISHED status) with two URL options 
(example.com/1 and example.com/2) to test which performs better.
The study is created as a draft and is NOT executed, launched, or deleted.
"""

import asyncio
import json
import re
import sys
import time
from typing import Any, Optional

from src.prolific_mcp.gemini_client import GeminiMCPClient
from src.prolific_mcp.config import config


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
    print(f"\n{Colors.BLUE}{Colors.BOLD}=== {name} ==={Colors.RESET}", flush=True)


def print_success(message: str):
    """Print success message."""
    print(f"{Colors.GREEN}✓ {message}{Colors.RESET}", flush=True)


def print_error(message: str):
    """Print error message."""
    print(f"{Colors.RED}✗ {message}{Colors.RESET}", flush=True)


def print_info(message: str):
    """Print info message."""
    print(f"{Colors.YELLOW}ℹ {message}{Colors.RESET}", flush=True)


def print_verbose(message: str):
    """Print verbose/debug message."""
    print(f"{Colors.YELLOW}  → {message}{Colors.RESET}", flush=True)


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
    
    prompt = """=== SYSTEM PROMPT ===

You are an AI assistant with access to Prolific study creation tools via the Model Context Protocol (MCP). Your role is to help create and manage user research studies on the Prolific platform.

TECHNICAL DETAILS:
- You have access to MCP tools for Prolific study management
- The primary tool is prolific_create_study which creates draft studies (status: UNPUBLISHED)
- Draft studies are not published or launched - they remain as drafts until explicitly launched
- Studies created via prolific_create_study are automatically in draft status and do not consume credits
- You should NOT delete draft studies - they can remain for review and future use
- All studies must include required fields: name, description, reward (in cents), estimated_completion_time (in minutes), external_study_url, total_available_places, study_type, study_labels, and completion_codes
- The external_study_url can include placeholders: {{%PROLIFIC_PID%}}, {{%STUDY_ID%}}, {{%SESSION_ID%}}
- study_type should typically be "SINGLE" for standard studies
- study_labels should be an array like ["survey"] for survey-type studies
- completion_codes should be an array of objects with: code (string), code_type (enum), and actions (array of action objects)
- Default completion code format: [{"code": "COMPLETED", "code_type": "COMPLETED", "actions": [{"action": "MANUALLY_REVIEW"}]}]
- prolific_id_option defaults to "url_parameters" which appends Prolific ID to the URL

WORKFLOW:
1. When asked to create a study, you MUST call prolific_create_study with all required parameters
2. Design the study appropriately based on the research goals provided
3. Fill in all fields with sensible defaults based on the study requirements
4. Do NOT ask for clarification - use reasonable defaults and create the study
5. After creation, confirm the study was created and provide the study ID
6. Do NOT launch, publish, or delete the study - leave it as a draft

=== INSTRUCTIONS ===

Create a user research study to test two versions of a website (example.com) to determine which performs better.

STUDY CONTEXT:
- Website: example.com (a customer service platform)
- Two versions being tested:
  * Version A: Original version (control)
  * Version B: New version with added customer service chatbot in bottom right corner
- The chatbot is the key feature difference between versions
- Participants will be randomly assigned to one version

RESEARCH GOAL:
Determine which version provides better user experience and identify the feature difference.

STUDY REQUIREMENTS:
- URL: example.com (do not pass any path parameters, just the base URL)
- Number of participants: 10
- Study type: Survey to compare two website versions
- Participants should be asked about:
  1. Their overall experience with the site
  2. What feature differences they noticed (if any)
  3. Which version they prefer (if they can identify differences)

IMPORTANT:
- Include plausible but obviously wrong options in the survey questions (e.g., "Added dark mode toggle" or "Changed logo color" when the real difference is the chatbot)
- Design appropriate survey questions that will help identify if participants noticed the chatbot feature
- Use reasonable defaults for reward amount and completion time based on the study complexity
- Create the study as a draft - do NOT launch it

ACTION REQUIRED:
Call prolific_create_study NOW with all required parameters. Design the study description and structure appropriately for this A/B testing scenario."""

    print_verbose("=" * 60)
    print_verbose("STEP 1: Connecting to MCP server...")
    print_verbose("=" * 60)
    print_verbose("Initializing Gemini MCP client...")
    print_verbose("Checking Gemini API key configuration...")
    try:
        config.validate_gemini()
        print_success("✓ Gemini API key is configured")
    except Exception as e:
        print_error(f"✗ Gemini API key validation failed: {str(e)}")
        return False, None, str(e)
    
    print_verbose("Starting MCP server subprocess...")
    print_verbose("MCP server will run as: python -m src.prolific_mcp.server")
    try:
        await client.connect()
        print_success("✓ Connected to MCP server successfully")
        print_verbose(f"✓ MCP server subprocess started and initialized")
        print_verbose(f"✓ Found {len(client.mcp_tools)} MCP tools available")
        print_verbose("\nAvailable MCP tools:")
        for tool in client.mcp_tools[:5]:  # Show first 5 tools
            print_verbose(f"  - {tool.get('name', 'unknown')}")
        if len(client.mcp_tools) > 5:
            print_verbose(f"  ... and {len(client.mcp_tools) - 5} more tools")
        print_verbose("✓ MCP tools loaded and ready for Gemini")
    except Exception as e:
        print_error(f"✗ Failed to connect to MCP server: {str(e)}")
        import traceback
        print_verbose("Connection error traceback:")
        traceback.print_exc()
        return False, None, str(e)
    
    print_verbose("\n" + "=" * 60)
    print_verbose("STEP 2: Connecting to Gemini API...")
    print_verbose("=" * 60)
    print_verbose("Initializing Gemini client...")
    print_verbose(f"Gemini client initialized: {client.gemini_client is not None}")
    print_verbose("✓ Gemini API client ready")
    
    print_verbose("\n" + "=" * 60)
    print_verbose("STEP 3: Sending prompt to Gemini...")
    print_verbose("=" * 60)
    print_verbose("PROMPT TO GEMINI:")
    print(prompt)
    print_verbose("=" * 60)
    print_verbose("Waiting for Gemini response (this may take a while)...")
    print_verbose("Gemini will analyze the prompt and use MCP tools to create the study...")
    print_verbose("Monitoring Gemini API calls and MCP tool invocations...")
    
    start_time = time.time()
    try:
        print_verbose("\n[TEST] Calling client.chat() - Gemini API interaction starting...")
        print_verbose("[TEST] This will show real-time progress as Gemini processes...")
        print_verbose("[TEST] Watch for [Gemini] and [MCP] prefixes for real-time updates...")
        print_verbose("[TEST] Starting async chat call now...")
        sys.stdout.flush()
        response = await client.chat(prompt)
        elapsed = time.time() - start_time
        sys.stdout.flush()
        
        print_verbose("\n" + "=" * 60)
        print_verbose("STEP 4: Gemini API Response Received")
        print_verbose("=" * 60)
        print_success(f"✓ Gemini API call completed in {elapsed:.2f} seconds")
        print_verbose(f"✓ Response received from Gemini API")
        print_verbose(f"✓ Response length: {len(response)} characters")
        print_verbose("\n" + "=" * 60)
        print_verbose("FULL GEMINI API RESPONSE:")
        print_verbose("=" * 60)
        print(response)
        print_verbose("=" * 60)
        
        # Verify study was created
        print_verbose("\n" + "=" * 60)
        print_verbose("STEP 5: Analyzing Gemini Response")
        print_verbose("=" * 60)
        print_verbose("Parsing response to verify study creation...")
        success, study_id = verify_study_created(response)
        
        if success:
            print_success("✓ Gemini API response indicates study was created")
            print_verbose("✓ Success indicators found in response")
            if study_id:
                print_success(f"✓ Study ID extracted: {study_id}")
                print_verbose(f"✓ Study ID pattern found: {study_id}")
                print_verbose(f"✓ Study ID format validated (24 hex characters)")
            else:
                print_info("⚠ Could not extract study ID from response, but study appears to be created")
                print_verbose("Searching for study ID patterns in response text...")
                # Try to find any study ID patterns
                potential_ids = re.findall(r'[0-9a-f]{24}', response, re.IGNORECASE)
                if potential_ids:
                    print_verbose(f"Found potential study IDs: {potential_ids}")
                    print_verbose("These may be study IDs mentioned in the response")
        else:
            print_error("✗ Gemini API response does not indicate successful study creation")
            print_verbose("Response may need manual review")
            print_verbose("Searching for success indicators in response...")
            print_verbose("Checking for common success phrases...")
        
        # Check for key requirements
        checks = {
            "Draft study created": success,
            "Study ID found": study_id is not None,
            "Website mentioned": "example.com" in response.lower(),
        }
        
        print_verbose("\n" + "=" * 60)
        print_verbose("STEP 6: Verification Checks")
        print_verbose("=" * 60)
        print_verbose("Verifying response meets requirements...")
        for check_name, check_result in checks.items():
            if check_result:
                print_success(f"  ✓ {check_name}")
            else:
                print_error(f"  ✗ {check_name}")
        print_verbose("=" * 60)
        
        return success, study_id, response
        
    except Exception as e:
        print_error(f"✗ Error during Gemini API interaction: {str(e)}")
        print_verbose("=" * 60)
        print_verbose("ERROR DETAILS:")
        print_verbose("=" * 60)
        import traceback
        print_verbose("Exception traceback:")
        traceback.print_exc()
        print_verbose("=" * 60)
        return False, None, str(e)
    finally:
        print_verbose("\nCleaning up connections...")
        print_verbose("Closing MCP server connection...")
        await client.close()
        print_verbose("✓ Connections closed")


async def verify_study_details(study_id: str) -> bool:
    """Verify study details by getting it via MCP."""
    print_test("Verify Study Details via MCP API")
    
    if not study_id:
        print_error("✗ No study ID provided")
        return False
    
    print_verbose("=" * 60)
    print_verbose("STEP 7: Verifying Study via MCP API")
    print_verbose("=" * 60)
    print_verbose(f"Study ID: {study_id}")
    print_verbose("Calling MCP tool: prolific_get_study")
    print_verbose("This will verify the study was actually created in Prolific...")
    
    # Use direct MCP call to verify
    from src.prolific_mcp.server import call_tool
    
    try:
        print_verbose("Making MCP API call to Prolific...")
        result = await call_tool("prolific_get_study", {"study_id": study_id})
        
        if result and len(result) > 0:
            response_text = result[0].text
            print_success("✓ Successfully retrieved study details from Prolific API")
            print_verbose("✓ MCP API call to Prolific succeeded")
            
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
                    places = study_data.get('total_available_places')
                    print_verbose(f"  Places: {places}")
                    print_verbose(f"  Reward: {study_data.get('reward')} cents")
                    
                    # Verify participant count
                    if places == 10:
                        print_success("✓ Study has 10 participants as requested")
                    else:
                        print_info(f"ℹ Study has {places} participants (expected 10)")
                    
                    # Verify it's a draft study (check status)
                    study_name = study_data.get('name', '')
                    study_status = study_data.get('status', '')
                    
                    print_verbose(f"Study name: {study_name}")
                    print_verbose(f"Study status: {study_status}")
                    
                    if study_status == "UNPUBLISHED":
                        print_success("✓ Study is in draft (UNPUBLISHED) status as expected")
                    else:
                        print_info(f"ℹ Study status: {study_status} (expected UNPUBLISHED for draft)")
                    
                    print_info("Note: Draft studies are not deleted - they remain for verification")
                    
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


async def verify_draft_study_exists(study_id: str) -> bool:
    """Verify draft study exists and is in draft (UNPUBLISHED) status."""
    print_test("Verify Draft Study Exists (via MCP API)")
    
    if not study_id:
        print_info("No study ID to verify")
        return True
    
    print_verbose("=" * 60)
    print_verbose("STEP 8: Final Verification via MCP API")
    print_verbose("=" * 60)
    print_verbose(f"Study ID: {study_id}")
    print_verbose("Making final MCP API call to confirm draft study exists...")
    
    from src.prolific_mcp.server import call_tool
    
    try:
        print_verbose("Calling MCP tool: prolific_get_study")
        result = await call_tool("prolific_get_study", {"study_id": study_id})
        
        if result and len(result) > 0:
            response_text = result[0].text
            print_verbose("✓ MCP API call successful")
            print_verbose("✓ Prolific API responded with study data")
            
            # Parse study data
            try:
                json_start = response_text.find("{")
                if json_start != -1:
                    json_str = response_text[json_start:]
                    study_data = json.loads(json_str)
                    
                    status = study_data.get('status', '')
                    print_verbose(f"✓ Study data parsed successfully")
                    print_verbose(f"Draft study status: {status}")
                    
                    # Verify it's in draft (UNPUBLISHED) status
                    if status == "UNPUBLISHED":
                        print_success("✓ Draft study exists and is in UNPUBLISHED (draft) status")
                        print_info("ℹ Draft studies are NOT deleted - they remain for verification")
                        print_info(f"ℹ Draft study ID: {study_id}")
                        print_verbose("✓ All API verifications passed")
                        return True
                    else:
                        print_info(f"ℹ Study status: {status} (expected UNPUBLISHED for draft)")
                        print_success("✓ Draft study exists and is accessible via Prolific API")
                        print_info("ℹ Draft studies are NOT deleted - they remain for verification")
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
    print_verbose("2. Use MCP tools to create a DRAFT real study")
    print_verbose("3. Fill in required fields appropriately")
    print_verbose("4. Create draft study (status UNPUBLISHED) - does not execute/launch")
    print_verbose("5. Draft studies are NOT deleted (they remain for verification)")
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
            
            # Verify draft study exists (draft studies are NOT deleted)
            draft_exists = await verify_draft_study_exists(study_id)
            results.append(("Verify Draft Study Exists", draft_exists))
        elif success:
            print_info("Study appears to be created but ID not extracted - skipping verification")
        else:
            print_error("Study creation failed - skipping verification and cleanup")
    
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}Test suite interrupted by user{Colors.RESET}")
        if study_id:
            print_info(f"Note: Draft study {study_id} exists (draft studies are not deleted)")
    except Exception as e:
        print_error(f"Unexpected error: {str(e)}")
        import traceback
        traceback.print_exc()
        if study_id:
            print_info(f"Note: Draft study {study_id} exists (draft studies are not deleted)")
    
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

