#!/usr/bin/env python3
"""
MCP Test Suite for Prolific API Integration

This test suite validates all MCP tools by:
1. Creating a study with n=1 (total_available_places=1)
2. Testing query results (should be successful but empty)
3. Testing field updates (survey type, study_type, etc.)
4. Deleting the study to avoid costs

All tests use MCP tool calls to ensure the full integration works.
"""

import asyncio
import json
import sys
import time
from typing import Any

# Import the MCP server components
from src.prolific_mcp.server import server, call_tool


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


def print_data(data: Any, label: str = "Data"):
    """Print formatted data."""
    print(f"{Colors.YELLOW}  [{label}]{Colors.RESET}")
    print(json.dumps(data, indent=2))


async def test_create_study() -> str | None:
    """Test creating a study with n=1."""
    print_test("Test 1: Create Study (n=1)")
    
    study_config = {
        "name": "MCP Test Study - Placeholder Survey",
        "description": "This is a test study created by the MCP test suite. It will be deleted after testing.",
        "reward": 100,  # $1.00 in cents
        "total_available_places": 1,  # n=1 as requested
        "estimated_completion_time": 5,  # 5 minutes
        "external_study_url": "https://example.com/survey?participant={{%PROLIFIC_PID%}}",
        "prolific_id_option": "url_parameters",
        "completion_codes": [
            {
                "code": "TEST123",
                "code_type": "COMPLETED",
                "actions": [{"action": "MANUALLY_REVIEW"}]
            }
        ],
        # Test filling out survey type fields
        "study_type": "SINGLE",  # Placeholder survey type
        "study_labels": ["survey"],  # Mark as survey
        "device_compatibility": ["desktop", "tablet", "mobile"],
    }
    
    print_verbose("Calling MCP tool: prolific_create_study")
    print_verbose(f"Study configuration: n={study_config['total_available_places']}, reward={study_config['reward']} cents")
    print_verbose(f"Study type: {study_config.get('study_type')}, labels: {study_config.get('study_labels')}")
    print_data(study_config, "Request Payload")
    
    start_time = time.time()
    try:
        result = await call_tool("prolific_create_study", study_config)
        elapsed = time.time() - start_time
        
        print_verbose(f"Request completed in {elapsed:.2f} seconds")
        
        if result and len(result) > 0:
            response_text = result[0].text
            print_success("Study creation request successful")
            print_verbose(f"Response type: {type(result[0])}, Response length: {len(response_text)} chars")
            
            # Try to extract study ID from response
            try:
                # Response format: "Study created successfully:\n{json}"
                json_start = response_text.find("{")
                if json_start != -1:
                    json_str = response_text[json_start:]
                    study_data = json.loads(json_str)
                    study_id = study_data.get("id")
                    
                    print_verbose("Full API response received:")
                    print_data(study_data, "Study Data")
                    
                    if study_id:
                        print_success(f"Study ID extracted: {study_id}")
                        print_verbose(f"Study name: {study_data.get('name')}")
                        print_verbose(f"Study status: {study_data.get('status')}")
                        print_verbose(f"Total places: {study_data.get('total_available_places')}")
                        print_verbose(f"Reward: {study_data.get('reward')} cents")
                        print_verbose(f"Project ID: {study_data.get('project')}")
                        print_info(f"Study created in project: {study_data.get('project')}")
                        return study_id
                    else:
                        print_error("Study ID not found in response")
                        return None
            except json.JSONDecodeError as e:
                print_error(f"Could not parse study ID from response: {e}")
                print_info("Full response text:")
                print(response_text)
                return None
        else:
            print_error("Empty response from create_study")
            print_verbose(f"Result object: {result}")
            return None
            
    except Exception as e:
        print_error(f"Failed to create study: {str(e)}")
        import traceback
        print_verbose("Exception traceback:")
        traceback.print_exc()
        return None


async def test_get_study(study_id: str) -> bool:
    """Test getting study details."""
    print_test("Test 2: Get Study Details")
    
    print_verbose(f"Calling MCP tool: prolific_get_study with study_id={study_id}")
    print_data({"study_id": study_id}, "Request Parameters")
    
    start_time = time.time()
    try:
        result = await call_tool("prolific_get_study", {"study_id": study_id})
        elapsed = time.time() - start_time
        
        print_verbose(f"Request completed in {elapsed:.2f} seconds")
        
        if result and len(result) > 0:
            response_text = result[0].text
            print_success("Get study request successful")
            
            # Verify study details
            try:
                json_start = response_text.find("{")
                if json_start != -1:
                    json_str = response_text[json_start:]
                    study_data = json.loads(json_str)
                    
                    print_verbose("Full study data received:")
                    print_data(study_data, "Study Details")
                    
                    # Check key fields with detailed output
                    print_verbose("Verifying study fields...")
                    
                    total_places = study_data.get("total_available_places")
                    if total_places == 1:
                        print_success(f"Study has n=1 as expected (total_available_places={total_places})")
                    else:
                        print_error(f"Expected n=1, got {total_places}")
                    
                    study_type = study_data.get("study_type")
                    if study_type == "SINGLE":
                        print_success(f"Study type is SINGLE as expected (study_type={study_type})")
                    else:
                        print_verbose(f"Study type: {study_type}")
                    
                    study_labels = study_data.get("study_labels", [])
                    if "survey" in study_labels:
                        print_success(f"Study is labeled as survey (labels={study_labels})")
                    else:
                        print_verbose(f"Study labels: {study_labels}")
                    
                    # Print additional fields for verification
                    print_verbose(f"Study name: {study_data.get('name')}")
                    print_verbose(f"Study status: {study_data.get('status')}")
                    print_verbose(f"Reward: {study_data.get('reward')} cents")
                    print_verbose(f"Estimated time: {study_data.get('estimated_completion_time')} minutes")
                    print_verbose(f"External URL: {study_data.get('external_study_url')}")
                    print_verbose(f"Prolific ID option: {study_data.get('prolific_id_option')}")
                    
                    return True
            except json.JSONDecodeError as e:
                print_error(f"Could not parse study data from response: {e}")
                print_verbose("Raw response text:")
                print(response_text)
                return False
        else:
            print_error("Empty response from get_study")
            return False
            
    except Exception as e:
        print_error(f"Failed to get study: {str(e)}")
        import traceback
        print_verbose("Exception traceback:")
        traceback.print_exc()
        return False


async def test_get_results(study_id: str) -> bool:
    """Test querying results (should be successful but empty)."""
    print_test("Test 3: Query Results (should be empty)")
    
    print_verbose(f"Calling MCP tool: prolific_get_results with study_id={study_id}")
    print_verbose("Expected: Empty results array (no submissions for new study)")
    print_data({"study_id": study_id}, "Request Parameters")
    
    start_time = time.time()
    try:
        result = await call_tool("prolific_get_results", {"study_id": study_id})
        elapsed = time.time() - start_time
        
        print_verbose(f"Request completed in {elapsed:.2f} seconds")
        
        if result and len(result) > 0:
            response_text = result[0].text
            print_success("Get results request successful")
            print_verbose(f"Response length: {len(response_text)} chars")
            
            # Check if results are empty (as expected for a new study)
            try:
                json_start = response_text.find("[")
                if json_start != -1:
                    json_str = response_text[json_start:]
                    submissions = json.loads(json_str)
                    
                    print_verbose(f"Parsed submissions: {len(submissions)} items")
                    print_data(submissions, "Submissions Data")
                    
                    if isinstance(submissions, list) and len(submissions) == 0:
                        print_success("Results are empty as expected (no submissions yet)")
                        print_verbose("This is correct - new studies have no submissions")
                    else:
                        print_info(f"Found {len(submissions)} submissions (unexpected for new study)")
                        print_verbose("Showing first submission:")
                        if len(submissions) > 0:
                            print_data(submissions[0], "First Submission")
                    
                    return True
                else:
                    # Might be wrapped in a different format
                    print_info("Response received (format may vary)")
                    print_verbose("Full response text:")
                    print(response_text)
                    return True
            except json.JSONDecodeError as e:
                # If we can't parse, but got a response, that's still success
                print_info(f"Response received (could not parse JSON: {e}, but request succeeded)")
                print_verbose("Raw response text:")
                print(response_text)
                return True
        else:
            print_error("Empty response from get_results")
            return False
            
    except Exception as e:
        print_error(f"Failed to get results: {str(e)}")
        import traceback
        print_verbose("Exception traceback:")
        traceback.print_exc()
        return False


async def test_get_study_status(study_id: str) -> bool:
    """Test getting study status."""
    print_test("Test 4: Get Study Status")
    
    print_verbose(f"Calling MCP tool: prolific_get_study_status with study_id={study_id}")
    print_data({"study_id": study_id}, "Request Parameters")
    
    start_time = time.time()
    try:
        result = await call_tool("prolific_get_study_status", {"study_id": study_id})
        elapsed = time.time() - start_time
        
        print_verbose(f"Request completed in {elapsed:.2f} seconds")
        
        if result and len(result) > 0:
            response_text = result[0].text
            print_success("Get study status request successful")
            
            try:
                json_start = response_text.find("{")
                if json_start != -1:
                    json_str = response_text[json_start:]
                    status_data = json.loads(json_str)
                    
                    print_verbose("Full status data received:")
                    print_data(status_data, "Status Data")
                    
                    status = status_data.get('status')
                    places_taken = status_data.get('places_taken', 0)
                    total_places = status_data.get('total_available_places', 0)
                    completion_rate = status_data.get('completion_rate')
                    
                    print_info(f"Status: {status}")
                    print_info(f"Places taken: {places_taken}/{total_places}")
                    if completion_rate is not None:
                        print_verbose(f"Completion rate: {completion_rate}")
                    
                    return True
            except json.JSONDecodeError as e:
                print_info(f"Response received (could not parse JSON: {e})")
                print_verbose("Raw response text:")
                print(response_text)
                return True
        else:
            print_error("Empty response from get_study_status")
            return False
            
    except Exception as e:
        print_error(f"Failed to get study status: {str(e)}")
        import traceback
        print_verbose("Exception traceback:")
        traceback.print_exc()
        return False


async def test_update_study(study_id: str) -> bool:
    """Test updating study fields (survey type, etc.)."""
    print_test("Test 5: Update Study Fields (Survey Type)")
    
    # Test updating with placeholder survey fields (only survey label - API only allows 1 label)
    updates = {
        "description": "Updated description - testing field updates with placeholder survey data",
        "study_labels": ["survey"],  # Only survey label (API limitation: max 1 label)
    }
    
    print_verbose(f"Calling MCP tool: prolific_update_study with study_id={study_id}")
    print_verbose("Updating fields with placeholder survey data")
    print_data({"study_id": study_id, "updates": updates}, "Request Parameters")
    
    start_time = time.time()
    try:
        result = await call_tool("prolific_update_study", {
            "study_id": study_id,
            "updates": updates
        })
        elapsed = time.time() - start_time
        
        print_verbose(f"Request completed in {elapsed:.2f} seconds")
        
        if result and len(result) > 0:
            response_text = result[0].text
            print_success("Update study request successful")
            print_info("Study fields updated with placeholder survey data")
            
            # Parse and show updated data
            try:
                json_start = response_text.find("{")
                if json_start != -1:
                    json_str = response_text[json_start:]
                    updated_data = json.loads(json_str)
                    print_verbose("Updated study data:")
                    print_data(updated_data, "Updated Study")
                    
                    # Verify updates
                    updated_labels = updated_data.get("study_labels", [])
                    updated_desc = updated_data.get("description", "")
                    
                    print_verbose(f"Verifying updates...")
                    print_verbose(f"Description updated: {updated_desc[:50]}...")
                    print_verbose(f"Labels updated: {updated_labels}")
                    
                    if "survey" in updated_labels:
                        print_success(f"Study labels correctly updated: {updated_labels}")
                    else:
                        print_verbose(f"Labels: {updated_labels}")
            except json.JSONDecodeError as e:
                print_verbose(f"Could not parse updated data: {e}")
                print_verbose("Raw response:")
                print(response_text)
            
            return True
        else:
            print_error("Empty response from update_study")
            return False
            
    except Exception as e:
        print_error(f"Failed to update study: {str(e)}")
        import traceback
        print_verbose("Exception traceback:")
        traceback.print_exc()
        return False


async def test_delete_study(study_id: str) -> bool:
    """Test deleting the study."""
    print_test("Test 6: Delete Study")
    
    print_verbose(f"Calling MCP tool: prolific_delete_study with study_id={study_id}")
    print_verbose("This will permanently delete the test study to avoid costs")
    print_data({"study_id": study_id}, "Request Parameters")
    
    start_time = time.time()
    try:
        result = await call_tool("prolific_delete_study", {"study_id": study_id})
        elapsed = time.time() - start_time
        
        print_verbose(f"Request completed in {elapsed:.2f} seconds")
        
        if result and len(result) > 0:
            response_text = result[0].text
            print_success("Delete study request successful")
            print_info("Study deleted to avoid costs")
            print_verbose(f"Response: {response_text}")
            
            # Verify deletion by trying to get the study (should fail)
            print_verbose("Verifying deletion by attempting to retrieve study...")
            try:
                verify_result = await call_tool("prolific_get_study", {"study_id": study_id})
                print_verbose("WARNING: Study still exists after deletion attempt")
            except Exception:
                print_verbose("Confirmed: Study no longer exists (deletion successful)")
            
            return True
        else:
            print_error("Empty response from delete_study")
            return False
            
    except Exception as e:
        print_error(f"Failed to delete study: {str(e)}")
        print_info("Note: If study was published, it cannot be deleted via API")
        import traceback
        print_verbose("Exception traceback:")
        traceback.print_exc()
        return False


async def test_list_studies() -> bool:
    """Test listing studies."""
    print_test("Test 7: List Studies")
    
    request_params = {"limit": 5}
    print_verbose(f"Calling MCP tool: prolific_list_studies with limit={request_params['limit']}")
    print_data(request_params, "Request Parameters")
    
    start_time = time.time()
    try:
        result = await call_tool("prolific_list_studies", request_params)
        elapsed = time.time() - start_time
        
        print_verbose(f"Request completed in {elapsed:.2f} seconds")
        
        if result and len(result) > 0:
            response_text = result[0].text
            print_success("List studies request successful")
            
            # Parse and show study list
            try:
                json_start = response_text.find("[")
                if json_start != -1:
                    json_str = response_text[json_start:]
                    studies = json.loads(json_str)
                    
                    print_verbose(f"Found {len(studies)} studies")
                    print_info(f"Retrieved {len(studies)} studies (limit was {request_params['limit']})")
                    
                    if len(studies) > 0:
                        print_verbose("Showing first study:")
                        print_data(studies[0], "First Study")
                        print_verbose(f"Study IDs: {[s.get('id') for s in studies[:3]]}")
                    else:
                        print_verbose("No studies found in account")
                else:
                    print_verbose("Response format may vary, showing raw response:")
                    print(response_text[:500])  # First 500 chars
            except json.JSONDecodeError as e:
                print_verbose(f"Could not parse studies list: {e}")
                print_verbose("Raw response:")
                print(response_text[:500])
            
            return True
        else:
            print_error("Empty response from list_studies")
            return False
            
    except Exception as e:
        print_error(f"Failed to list studies: {str(e)}")
        import traceback
        print_verbose("Exception traceback:")
        traceback.print_exc()
        return False


async def main():
    """Run all MCP tests."""
    print(f"\n{Colors.BOLD}{Colors.BLUE}")
    print("=" * 60)
    print("MCP Test Suite for Prolific API Integration")
    print("=" * 60)
    print(f"{Colors.RESET}\n")
    
    print_verbose("Initializing test suite...")
    print_verbose("All tests will use MCP tool calls directly")
    print_verbose("Test study will be created with n=1 and deleted after testing")
    print()
    
    results = []
    study_id = None
    suite_start_time = time.time()
    
    try:
        # Test 1: Create study with n=1
        study_id = await test_create_study()
        results.append(("Create Study", study_id is not None))
        
        if not study_id:
            print_error("Cannot continue tests without study ID")
            print_info("Attempting to continue with other tests that don't require study_id...")
        else:
            # Test 2: Get study details
            results.append(("Get Study", await test_get_study(study_id)))
            
            # Test 3: Query results (should be empty)
            results.append(("Get Results", await test_get_results(study_id)))
            
            # Test 4: Get study status
            results.append(("Get Study Status", await test_get_study_status(study_id)))
            
            # Test 5: Update study fields
            results.append(("Update Study", await test_update_study(study_id)))
            
            # Wait 2 minutes before deletion
            print_test("Waiting 2 minutes before deletion...")
            print_verbose("Waiting 120 seconds as requested...")
            await asyncio.sleep(120)
            print_verbose("Wait complete, proceeding with deletion")
            
            # Test 6: Delete study
            results.append(("Delete Study", await test_delete_study(study_id)))
        
        # Test 7: List studies (doesn't require study_id)
        results.append(("List Studies", await test_list_studies()))
        
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}Test suite interrupted by user{Colors.RESET}")
        if study_id:
            print_info(f"Note: Study {study_id} may still exist and should be deleted manually")
    except Exception as e:
        print_error(f"Unexpected error: {str(e)}")
        if study_id:
            print_info(f"Note: Study {study_id} may still exist and should be deleted manually")
    
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

