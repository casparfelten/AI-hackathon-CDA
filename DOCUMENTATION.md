# Prolific MCP Server - Complete Documentation

## Table of Contents

1. [Introduction](#introduction)
2. [Architecture Overview](#architecture-overview)
3. [Installation & Setup](#installation--setup)
4. [Configuration](#configuration)
5. [MCP Tools Reference](#mcp-tools-reference)
6. [API Client Reference](#api-client-reference)
7. [Integration Guide](#integration-guide)
8. [Error Handling](#error-handling)
9. [Best Practices](#best-practices)
10. [Troubleshooting](#troubleshooting)
11. [Examples & Use Cases](#examples--use-cases)

---

## Introduction

The Prolific MCP Server is a Model Context Protocol (MCP) server that acts as a translation layer between MCP-compatible AI agents (such as Gemini CLI) and Prolific's REST API. It enables autonomous management of user studies, including creation, launching, monitoring, and result collection.

### What is MCP?

Model Context Protocol (MCP) is a standardized protocol that allows AI assistants to interact with external tools and data sources. MCP servers expose capabilities as "tools" that AI agents can discover and invoke.

### Why This Server?

- **Automation**: Enables AI agents to autonomously run user studies without manual intervention
- **Translation Layer**: Simplifies Prolific API complexity into clean, AI-friendly tool interfaces
- **Standardized Interface**: Uses MCP protocol for compatibility with various AI agents
- **Error Handling**: Provides meaningful error messages and graceful failure handling

---

## Architecture Overview

### System Architecture

```
┌─────────────────┐
│   Gemini CLI    │
│  (AI Agent)     │
└────────┬────────┘
         │ MCP Protocol (stdio)
         │
┌────────▼─────────────────┐
│   MCP Server              │
│   (server.py)             │
│   - Tool Registration     │
│   - Request Routing       │
│   - Response Formatting   │
└────────┬──────────────────┘
         │
┌────────▼─────────────────┐
│   Prolific Client         │
│   (prolific_client.py)    │
│   - HTTP Requests         │
│   - Error Handling        │
│   - Response Parsing      │
└────────┬──────────────────┘
         │ HTTPS REST API
         │
┌────────▼─────────────────┐
│   Prolific API            │
│   (api.prolific.com)      │
└───────────────────────────┘
```

### Component Breakdown

#### 1. **Configuration Module** (`config.py`)
- **Purpose**: Manages environment variables and API credentials
- **Responsibilities**:
  - Load environment variables from `.env` file
  - Validate required configuration (API key)
  - Provide authentication headers
  - Handle configuration errors

#### 2. **Prolific Client** (`prolific_client.py`)
- **Purpose**: HTTP client wrapper for Prolific API
- **Responsibilities**:
  - Make authenticated HTTP requests to Prolific API
  - Handle API errors and exceptions
  - Transform API responses into Python dictionaries
  - Provide high-level methods for study operations

#### 3. **MCP Server** (`server.py`)
- **Purpose**: MCP protocol implementation
- **Responsibilities**:
  - Register MCP tools with descriptions and schemas
  - Route tool calls to appropriate client methods
  - Format responses as MCP TextContent
  - Handle tool call errors gracefully

### Data Flow

1. **AI Agent Request** → MCP tool call with parameters
2. **MCP Server** → Validates parameters, routes to client method
3. **Prolific Client** → Makes HTTP request to Prolific API
4. **Prolific API** → Processes request, returns JSON response
5. **Prolific Client** → Parses response, handles errors
6. **MCP Server** → Formats response as TextContent
7. **AI Agent** → Receives formatted result

---

## Installation & Setup

### Prerequisites

- **Python**: Version 3.8 or higher
- **Prolific Account**: Researcher account with API access
- **API Token**: Valid Prolific API token

### Step-by-Step Installation

#### 1. Clone the Repository

```bash
git clone <repository-url>
cd AI-hackathon-CDA
```

#### 2. Create Virtual Environment

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

#### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

Required packages:
- `mcp>=0.9.0`: MCP SDK for Python
- `requests>=2.31.0`: HTTP library for API calls
- `python-dotenv>=1.0.0`: Environment variable management
- `pydantic>=2.0.0`: Data validation (for future enhancements)

#### 4. Configure API Credentials

```bash
cp .env.example .env
```

Edit `.env` and add your API token:

```env
PROLIFIC_API_KEY=your_actual_api_token_here
```

#### 5. Verify Installation

```bash
python -c "from prolific_mcp.config import config; config.validate(); print('Configuration valid!')"
```

### Getting Your Prolific API Token

1. Log into [Prolific Researcher Dashboard](https://app.prolific.com)
2. Navigate to **Account Settings** → **API Tokens**
3. Click **Create API Token**
4. Provide a descriptive name (e.g., "MCP Server - Development")
5. Copy the generated token immediately (it won't be shown again)
6. Store it securely in your `.env` file

**Security Note**: Never commit your `.env` file to version control. The `.gitignore` file is configured to exclude it.

---

## Configuration

### Environment Variables

#### Required Variables

**`PROLIFIC_API_KEY`**
- **Type**: String
- **Description**: Your Prolific API authentication token
- **Format**: Alphanumeric string provided by Prolific
- **Example**: `abc123def456ghi789jkl012mno345pqr678stu901vwx234yz`
- **Location**: Set in `.env` file or system environment

#### Optional Variables

**`PROLIFIC_API_BASE_URL`**
- **Type**: String (URL)
- **Description**: Base URL for Prolific API
- **Default**: `https://api.prolific.com/api/v1`
- **When to Override**: Only if using a custom Prolific API endpoint (rare)

### Configuration Validation

The configuration is validated on server startup. If `PROLIFIC_API_KEY` is missing or invalid, the server will raise a `ValueError` with a descriptive message.

### Configuration Loading Order

1. System environment variables (highest priority)
2. `.env` file in project root
3. Default values (for optional variables)

---

## MCP Tools Reference

The server exposes 7 MCP tools. Each tool has a name, description, input schema, and returns formatted text responses.

### Tool: `prolific_create_study`

Creates a new study on Prolific with the specified configuration.

#### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `name` | string | Yes | Public name or title of the study (visible to participants) |
| `description` | string | Yes | Detailed description of the study for participants to read before starting |
| `reward` | integer | Yes | Reward amount in cents (e.g., 100 = $1.00, 150 = $1.50) |
| `total_available_places` | integer | Yes | Number of participants needed for the study |
| `estimated_completion_time` | integer | Yes | Estimated time to complete in minutes |
| `external_study_url` | string | Yes | URL where participants will complete the study (can include {{%PROLIFIC_PID%}}, {{%STUDY_ID%}}, {{%SESSION_ID%}} placeholders) |
| `prolific_id_option` | string | No (default: "url_parameters") | How to collect Prolific ID: "question" (ask in survey), "url_parameters" (recommended, pass in URL), or "not_required" |
| `completion_codes` | array | No (default: single COMPLETED code) | Array of completion code objects. Each requires: `code` (string), `code_type` (enum), `actions` (array of action objects) |
| `internal_name` | string | No | Internal name for your reference (not visible to participants) |

#### Example Request

```json
{
  "tool": "prolific_create_study",
  "arguments": {
    "name": "User Interface Preference Study",
    "description": "We are conducting research on user interface preferences. This study will take approximately 10 minutes and involves rating different UI designs.",
    "reward": 150,
    "total_available_places": 50,
    "estimated_completion_time": 10,
    "external_study_url": "https://your-study-platform.com/study/123?participant={{%PROLIFIC_PID%}}",
    "prolific_id_option": "url_parameters",
    "internal_name": "UI-Pref-Study-Q4-2024"
  }
}
```

#### Example Response

```json
{
  "type": "text",
  "text": "Study created successfully:\n{\n  \"id\": \"65a1b2c3d4e5f6g7h8i9j0k1\",\n  \"name\": \"User Interface Preference Study\",\n  \"status\": \"UNPUBLISHED\",\n  \"reward\": 150,\n  \"total_available_places\": 50,\n  \"estimated_completion_time\": 10,\n  \"external_study_url\": \"https://your-study-platform.com/study/123?participant={{%PROLIFIC_PID%}}\",\n  \"prolific_id_option\": \"url_parameters\",\n  \"completion_codes\": [...],\n  \"created_at\": \"2024-11-15T12:00:00Z\",\n  ...\n}"
}
```

#### Notes

- The study is created in `UNPUBLISHED` status and must be launched separately
- Minimum reward is typically $0.50 (50 cents)
- Study URL must be accessible to participants
- Study ID is returned in the response and needed for subsequent operations
- **Completion Codes**: If not provided, defaults to a single code "COMPLETED" with MANUALLY_REVIEW action. You can customize this by providing a `completion_codes` array with your own codes and actions
- **Prolific ID Option**: Defaults to "url_parameters" (recommended). This passes participant ID, study ID, and session ID as URL parameters that your study platform can capture

---

### Tool: `prolific_get_study`

Retrieves complete details of a specific study by its ID.

#### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `study_id` | string | Yes | Prolific study ID (returned from create_study) |

#### Example Request

```json
{
  "tool": "prolific_get_study",
  "arguments": {
    "study_id": "65a1b2c3d4e5f6g7h8i9j0k1"
  }
}
```

#### Example Response

```json
{
  "type": "text",
  "text": "Study details:\n{\n  \"id\": \"65a1b2c3d4e5f6g7h8i9j0k1\",\n  \"name\": \"User Interface Preference Study\",\n  \"description\": \"We are conducting research...\",\n  \"status\": \"ACTIVE\",\n  \"reward\": 150,\n  \"total_available_places\": 50,\n  \"places_taken\": 23,\n  \"places_remaining\": 27,\n  \"completion_rate\": 0.95,\n  \"estimated_completion_time\": 10,\n  \"external_study_url\": \"https://your-study-platform.com/study/123?participant={{%PROLIFIC_PID%}}\",\n  \"created_at\": \"2024-11-15T12:00:00Z\",\n  \"published_at\": \"2024-11-15T12:05:00Z\",\n  ...\n}"
}
```

#### Response Fields

- `id`: Unique study identifier
- `status`: Current status (`UNPUBLISHED`, `ACTIVE`, `PAUSED`, `COMPLETED`)
- `places_taken`: Number of participants who have started/completed
- `places_remaining`: Number of spots still available
- `completion_rate`: Ratio of completed to started submissions

---

### Tool: `prolific_update_study`

Updates one or more parameters of an existing study.

#### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `study_id` | string | Yes | Prolific study ID |
| `updates` | object | Yes | Dictionary of fields to update |

#### Updatable Fields

- `name`: Study name (public title)
- `description`: Study description
- `reward`: Reward amount in cents
- `total_available_places`: Number of participants
- `estimated_completion_time`: Completion time in minutes
- `external_study_url`: Study URL
- `prolific_id_option`: How to collect Prolific ID
- `completion_codes`: Array of completion code objects
- `internal_name`: Internal name

**Note**: Some fields may not be updatable after a study is published. Check Prolific API documentation for restrictions.

#### Example Request

```json
{
  "tool": "prolific_update_study",
  "arguments": {
    "study_id": "65a1b2c3d4e5f6g7h8i9j0k1",
    "updates": {
      "reward": 200,
      "total_available_places": 75,
      "name": "Updated Study Name",
      "description": "Updated description with more details"
    }
  }
}
```

#### Example Response

```json
{
  "type": "text",
  "text": "Study updated successfully:\n{\n  \"id\": \"65a1b2c3d4e5f6g7h8i9j0k1\",\n  \"reward\": 200,\n  \"total_available_places\": 75,\n  \"description\": \"Updated description with more details\",\n  ...\n}"
}
```

---

### Tool: `prolific_launch_study`

Launches a study to start participant recruitment. The study must be in `UNPUBLISHED` status.

#### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `study_id` | string | Yes | Prolific study ID |

#### Example Request

```json
{
  "tool": "prolific_launch_study",
  "arguments": {
    "study_id": "65a1b2c3d4e5f6g7h8i9j0k1"
  }
}
```

#### Example Response

```json
{
  "type": "text",
  "text": "Study launched successfully:\n{\n  \"id\": \"65a1b2c3d4e5f6g7h8i9j0k1\",\n  \"status\": \"ACTIVE\",\n  \"published_at\": \"2024-11-15T12:05:00Z\",\n  ...\n}"
}
```

#### Notes

- Study status changes from `UNPUBLISHED` to `ACTIVE`
- Participants can now see and join the study
- Once launched, some fields may become read-only
- You can pause a study using Prolific's web interface if needed

---

### Tool: `prolific_get_results`

Retrieves all submissions/results for a study. Returns data for all participants who have completed or are in progress.

#### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `study_id` | string | Yes | Prolific study ID |

#### Example Request

```json
{
  "tool": "prolific_get_results",
  "arguments": {
    "study_id": "65a1b2c3d4e5f6g7h8i9j0k1"
  }
}
```

#### Example Response

```json
{
  "type": "text",
  "text": "Study submissions:\n[\n  {\n    \"id\": \"sub_001\",\n    \"participant_id\": \"part_123\",\n    \"status\": \"APPROVED\",\n    \"started_at\": \"2024-11-15T13:00:00Z\",\n    \"completed_at\": \"2024-11-15T13:08:00Z\",\n    \"time_taken\": 480,\n    \"responses\": {...},\n    ...\n  },\n  ...\n]"
}
```

#### Response Structure

Each submission contains:
- `id`: Unique submission ID
- `participant_id`: Prolific participant identifier
- `status`: Submission status (`APPROVED`, `REJECTED`, `AWAITING_REVIEW`)
- `started_at`: When participant started the study
- `completed_at`: When participant finished (if completed)
- `time_taken`: Time taken in seconds
- `responses`: Study-specific response data (format depends on your study)

#### Notes

- Returns empty array if no submissions yet
- Includes both completed and in-progress submissions
- Response data format depends on your external study platform
- Use `prolific_get_study_status` for summary statistics

---

### Tool: `prolific_get_study_status`

Retrieves a summary of study status including completion metrics.

#### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `study_id` | string | Yes | Prolific study ID |

#### Example Request

```json
{
  "tool": "prolific_get_study_status",
  "arguments": {
    "study_id": "65a1b2c3d4e5f6g7h8i9j0k1"
  }
}
```

#### Example Response

```json
{
  "type": "text",
  "text": "Study status:\n{\n  \"id\": \"65a1b2c3d4e5f6g7h8i9j0k1\",\n  \"status\": \"ACTIVE\",\n  \"total_available_places\": 50,\n  \"places_taken\": 23,\n  \"completion_rate\": 0.95\n}"
}
```

#### Response Fields

- `id`: Study ID
- `status`: Current study status
- `total_available_places`: Total participant slots
- `places_taken`: Number of participants who have taken spots
- `completion_rate`: Ratio of completed submissions (0.0 to 1.0)

#### Use Cases

- Quick status checks without fetching full study data
- Monitoring study progress
- Determining if study is complete (places_taken == total_available_places)

---

### Tool: `prolific_list_studies`

Lists all studies in your Prolific account, optionally limited to a specific number.

#### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `limit` | integer | No | Maximum number of studies to return |

#### Example Request

```json
{
  "tool": "prolific_list_studies",
  "arguments": {
    "limit": 10
  }
}
```

#### Example Response

```json
{
  "type": "text",
  "text": "Studies:\n[\n  {\n    \"id\": \"65a1b2c3d4e5f6g7h8i9j0k1\",\n    \"title\": \"User Interface Preference Study\",\n    \"status\": \"ACTIVE\",\n    \"created_at\": \"2024-11-15T12:00:00Z\",\n    ...\n  },\n  ...\n]"
}
```

#### Notes

- Returns studies in reverse chronological order (newest first)
- Without limit, returns all studies (may be slow for accounts with many studies)
- Each study object contains summary information (use `prolific_get_study` for full details)

---

## API Client Reference

The `ProlificClient` class provides low-level access to Prolific's API. While MCP tools are the primary interface, you can also use the client directly in Python code.

### Class: `ProlificClient`

#### Initialization

```python
from prolific_mcp.prolific_client import ProlificClient

client = ProlificClient()
```

The client automatically validates configuration and sets up authentication headers.

#### Methods

##### `create_study(study_config: dict) -> dict`

Creates a new study.

**Parameters:**
- `study_config`: Dictionary with study configuration fields

**Returns:** Complete study object from Prolific API

**Raises:** `ProlificAPIError` if API call fails

##### `get_study(study_id: str) -> dict`

Retrieves study details.

**Parameters:**
- `study_id`: Prolific study ID string

**Returns:** Complete study object

**Raises:** `ProlificAPIError` if study not found or API error

##### `update_study(study_id: str, updates: dict) -> dict`

Updates study parameters.

**Parameters:**
- `study_id`: Prolific study ID
- `updates`: Dictionary of fields to update

**Returns:** Updated study object

**Raises:** `ProlificAPIError` if update fails

##### `launch_study(study_id: str) -> dict`

Launches a study (publishes it).

**Parameters:**
- `study_id`: Prolific study ID

**Returns:** Study object with updated status

**Raises:** `ProlificAPIError` if launch fails (e.g., study already published)

##### `get_submissions(study_id: str) -> list[dict]`

Gets all submissions for a study.

**Parameters:**
- `study_id`: Prolific study ID

**Returns:** List of submission objects

**Raises:** `ProlificAPIError` if API call fails

##### `get_study_status(study_id: str) -> dict`

Gets summary status of a study.

**Parameters:**
- `study_id`: Prolific study ID

**Returns:** Dictionary with status summary fields

**Raises:** `ProlificAPIError` if study not found

##### `list_studies(limit: Optional[int] = None) -> list[dict]`

Lists all studies.

**Parameters:**
- `limit`: Optional maximum number of studies to return

**Returns:** List of study objects

**Raises:** `ProlificAPIError` if API call fails

### Exception: `ProlificAPIError`

Custom exception for Prolific API errors.

**Attributes:**
- `message`: Error message string
- `status_code`: HTTP status code (if available)
- `response`: Error response from API (if available)

**Example:**

```python
from prolific_mcp.prolific_client import ProlificClient, ProlificAPIError

client = ProlificClient()

try:
    study = client.get_study("invalid_id")
except ProlificAPIError as e:
    print(f"Error: {e.message}")
    print(f"Status: {e.status_code}")
    print(f"Response: {e.response}")
```

---

## Integration Guide

### Integrating with Gemini CLI

#### 1. Install Gemini CLI

Follow Gemini CLI installation instructions for your system.

#### 2. Configure MCP Server

Add the Prolific MCP server to your Gemini CLI configuration. The exact configuration format depends on your Gemini CLI setup, but typically involves:

```json
{
  "mcpServers": {
    "prolific": {
      "command": "python",
      "args": ["-m", "prolific_mcp.server"],
      "env": {
        "PROLIFIC_API_KEY": "your_api_key_here"
      }
    }
  }
}
```

#### 3. Verify Connection

Start Gemini CLI and verify it can discover the Prolific tools:

```
> list tools
```

You should see all 7 Prolific tools listed.

#### 4. Use Tools

You can now ask Gemini CLI to manage studies:

```
> Create a study titled "User Preference Survey" with 50 participants, 
  $1.50 reward, 10 minute duration, and URL https://example.com/study
```

Gemini will automatically:
1. Call `prolific_create_study` with appropriate parameters
2. Extract the study ID from the response
3. Optionally launch the study if requested

### Integration with Other MCP Clients

The server uses stdio transport, making it compatible with any MCP client. The communication protocol is:

1. **Client** sends JSON-RPC requests via stdin
2. **Server** processes requests and sends JSON-RPC responses via stdout
3. **Error handling** via JSON-RPC error objects

### Programmatic Usage

You can also use the Prolific client directly in Python scripts:

```python
from prolific_mcp.prolific_client import ProlificClient

client = ProlificClient()

# Create a study
study = client.create_study({
    "name": "My Study",
    "description": "Study description",
    "reward": 150,
    "total_available_places": 50,
    "estimated_completion_time": 10,
    "external_study_url": "https://example.com/study?participant={{%PROLIFIC_PID%}}",
    "prolific_id_option": "url_parameters",
    "completion_codes": [
        {
            "code": "COMPLETED",
            "code_type": "COMPLETED",
            "actions": [{"action": "MANUALLY_REVIEW"}]
        }
    ]
})

study_id = study["id"]

# Launch it
client.launch_study(study_id)

# Check status later
status = client.get_study_status(study_id)
print(f"Places taken: {status['places_taken']}/{status['total_available_places']}")

# Get results when complete
submissions = client.get_submissions(study_id)
print(f"Received {len(submissions)} submissions")
```

---

## Error Handling

### Error Types

#### 1. Configuration Errors

**Error**: `ValueError: PROLIFIC_API_KEY environment variable is required`

**Cause**: API key not set in environment or `.env` file

**Solution**: 
- Ensure `.env` file exists with `PROLIFIC_API_KEY=your_token`
- Or set environment variable: `export PROLIFIC_API_KEY=your_token`

#### 2. Authentication Errors

**Error**: `Prolific API error: 401 Unauthorized`

**Cause**: Invalid or expired API token

**Solution**:
- Verify API token is correct in `.env` file
- Generate a new token from Prolific dashboard
- Ensure token hasn't been revoked

#### 3. Not Found Errors

**Error**: `Prolific API error: 404 Not Found`

**Cause**: Invalid study ID or study doesn't exist

**Solution**:
- Verify study ID is correct
- Check that study hasn't been deleted
- Use `prolific_list_studies` to find valid study IDs

#### 4. Validation Errors

**Error**: `Prolific API error: 400 Bad Request`

**Cause**: Invalid parameters in request

**Solution**:
- Check required fields are provided
- Verify data types (e.g., reward is integer, not string)
- Ensure values are within valid ranges (e.g., minimum reward)

#### 5. Rate Limiting

**Error**: `Prolific API error: 429 Too Many Requests`

**Cause**: Too many API requests in short time

**Solution**:
- Implement exponential backoff
- Reduce request frequency
- Contact Prolific support if persistent

#### 6. Network Errors

**Error**: `Request failed: Connection timeout`

**Cause**: Network connectivity issues

**Solution**:
- Check internet connection
- Verify Prolific API is accessible
- Check firewall/proxy settings

### Error Response Format

All errors are returned as MCP TextContent with descriptive messages:

```json
{
  "type": "text",
  "text": "Prolific API error: 404 Not Found (Status: 404)\nResponse: {\n  \"detail\": \"Study not found\"\n}"
}
```

### Best Practices for Error Handling

1. **Always check study IDs** before operations
2. **Validate parameters** before making API calls
3. **Handle rate limiting** with retry logic
4. **Log errors** for debugging
5. **Provide user-friendly messages** when possible

---

## Best Practices

### Study Creation

1. **Clear Titles**: Use descriptive, participant-friendly titles
2. **Accurate Descriptions**: Provide enough detail for informed consent
3. **Fair Rewards**: Set rewards appropriate for study duration
4. **Realistic Time Estimates**: Overestimate rather than underestimate
5. **Test URLs**: Ensure study URL is accessible before launching

### Study Management

1. **Create Before Launch**: Always create studies in `UNPUBLISHED` status first
2. **Review Before Launch**: Check study details before publishing
3. **Monitor Progress**: Regularly check study status
4. **Handle Completion**: Retrieve results promptly after completion
5. **Archive Studies**: Keep records of study IDs and results

### API Usage

1. **Rate Limiting**: Be mindful of API rate limits
2. **Error Handling**: Always handle exceptions
3. **Idempotency**: Design operations to be safely retryable
4. **Logging**: Log important operations for audit trails
5. **Security**: Never expose API keys in code or logs

### MCP Integration

1. **Tool Discovery**: Let AI agents discover tools automatically
2. **Clear Descriptions**: Provide detailed tool descriptions
3. **Parameter Validation**: Validate inputs before API calls
4. **Response Formatting**: Return structured, parseable responses
5. **Error Messages**: Provide actionable error messages

---

## Troubleshooting

### Server Won't Start

**Problem**: Server fails to start with configuration error

**Solutions**:
1. Check `.env` file exists and contains `PROLIFIC_API_KEY`
2. Verify Python version: `python --version` (needs 3.8+)
3. Ensure dependencies installed: `pip install -r requirements.txt`
4. Check for syntax errors: `python -m py_compile src/prolific_mcp/*.py`

### Tools Not Appearing in MCP Client

**Problem**: MCP client doesn't see Prolific tools

**Solutions**:
1. Verify server is running: `python -m prolific_mcp.server`
2. Check MCP client configuration points to correct command
3. Verify stdio communication is working
4. Check server logs for initialization errors

### API Calls Failing

**Problem**: All API calls return errors

**Solutions**:
1. Verify API key is correct and not expired
2. Check internet connectivity
3. Verify Prolific API status (check their status page)
4. Test API key directly: `curl -H "Authorization: Token YOUR_KEY" https://api.prolific.com/api/v1/studies/`

### Study Creation Fails

**Problem**: `prolific_create_study` returns validation error

**Solutions**:
1. Verify all required fields are provided
2. Check data types (reward is integer, not string)
3. Ensure reward meets minimum (typically 50 cents)
4. Verify study URL is accessible
5. Check Prolific API documentation for field requirements

### Study Won't Launch

**Problem**: `prolific_launch_study` fails

**Solutions**:
1. Verify study is in `UNPUBLISHED` status
2. Check study has all required fields set
3. Ensure study URL is accessible
4. Verify account has sufficient balance for rewards

### Results Not Available

**Problem**: `prolific_get_results` returns empty array

**Solutions**:
1. Check study status - may not have participants yet
2. Verify study is `ACTIVE` or `COMPLETED`
3. Check `prolific_get_study_status` for places_taken
4. Allow time for participants to complete studies

---

## Examples & Use Cases

### Example 1: Complete Study Workflow

**Scenario**: Create, launch, monitor, and retrieve results for a study

```python
# This would be done via MCP tools, but here's the Python equivalent:

from prolific_mcp.prolific_client import ProlificClient
import time

client = ProlificClient()

# 1. Create study
study = client.create_study({
    "name": "Website Usability Test",
    "description": "Help us improve our website by completing a 15-minute usability test",
    "reward": 200,  # $2.00
    "total_available_places": 30,
    "estimated_completion_time": 15,
    "external_study_url": "https://usability-test.example.com/study/123?participant={{%PROLIFIC_PID%}}",
    "prolific_id_option": "url_parameters",
    "completion_codes": [
        {
            "code": "COMPLETED",
            "code_type": "COMPLETED",
            "actions": [{"action": "MANUALLY_REVIEW"}]
        }
    ]
})

study_id = study["id"]
print(f"Created study: {study_id}")

# 2. Launch study
client.launch_study(study_id)
print("Study launched!")

# 3. Monitor progress
while True:
    status = client.get_study_status(study_id)
    print(f"Progress: {status['places_taken']}/{status['total_available_places']}")
    
    if status['places_taken'] >= status['total_available_places']:
        break
    
    time.sleep(300)  # Check every 5 minutes

# 4. Get results
submissions = client.get_submissions(study_id)
print(f"Received {len(submissions)} submissions")

# Process results...
for submission in submissions:
    if submission['status'] == 'APPROVED':
        # Process approved submission
        pass
```

### Example 2: Batch Study Creation

**Scenario**: Create multiple similar studies with variations

```python
from prolific_mcp.prolific_client import ProlificClient

client = ProlificClient()

base_config = {
    "description": "User preference study",
    "reward": 150,
    "total_available_places": 25,
    "estimated_completion_time": 10,
}

variations = [
    {"name": "Study A - Design A", "external_study_url": "https://example.com/study-a?participant={{%PROLIFIC_PID%}}", "prolific_id_option": "url_parameters"},
    {"name": "Study B - Design B", "external_study_url": "https://example.com/study-b?participant={{%PROLIFIC_PID%}}", "prolific_id_option": "url_parameters"},
    {"name": "Study C - Design C", "external_study_url": "https://example.com/study-c?participant={{%PROLIFIC_PID%}}", "prolific_id_option": "url_parameters"},
]

study_ids = []

for variation in variations:
    config = {**base_config, **variation}
    study = client.create_study(config)
    study_ids.append(study["id"])
    print(f"Created: {study['title']} - {study['id']}")

print(f"Created {len(study_ids)} studies")
```

### Example 3: Study Monitoring Script

**Scenario**: Monitor multiple active studies and alert when complete

```python
from prolific_mcp.prolific_client import ProlificClient
import time

client = ProlificClient()

# List of study IDs to monitor
study_ids = [
    "65a1b2c3d4e5f6g7h8i9j0k1",
    "65a1b2c3d4e5f6g7h8i9j0k2",
    "65a1b2c3d4e5f6g7h8i9j0k3",
]

def check_studies():
    for study_id in study_ids:
        try:
            status = client.get_study_status(study_id)
            places_taken = status['places_taken']
            total = status['total_available_places']
            
            if places_taken >= total:
                print(f"Study {study_id} is COMPLETE!")
                # Retrieve results
                submissions = client.get_submissions(study_id)
                print(f"  - {len(submissions)} submissions received")
            else:
                print(f"Study {study_id}: {places_taken}/{total} complete")
        except Exception as e:
            print(f"Error checking {study_id}: {e}")

# Monitor every 10 minutes
while True:
    check_studies()
    time.sleep(600)
```

### Example 4: AI Agent Autonomous Study

**Scenario**: AI agent creates and manages a study based on research question

**MCP Tool Sequence**:

1. **Create Study**:
   ```
   Tool: prolific_create_study
   Arguments: {
     "name": "Research Question: User Preferences for Dark Mode",
     "description": "We are studying user preferences for dark mode interfaces...",
     "reward": 150,
     "total_available_places": 100,
     "estimated_completion_time": 12,
     "external_study_url": "https://research-platform.com/study/dark-mode-prefs?participant={{%PROLIFIC_PID%}}",
     "prolific_id_option": "url_parameters"
   }
   ```

2. **Launch Study**:
   ```
   Tool: prolific_launch_study
   Arguments: {"study_id": "<from step 1>"}
   ```

3. **Monitor (periodic)**:
   ```
   Tool: prolific_get_study_status
   Arguments: {"study_id": "<from step 1>"}
   ```

4. **Retrieve Results** (when complete):
   ```
   Tool: prolific_get_results
   Arguments: {"study_id": "<from step 1>"}
   ```

5. **Analyze Results**: AI agent processes submission data and generates insights

### Example 5: Study Update Workflow

**Scenario**: Adjust study parameters before launch

```python
from prolific_mcp.prolific_client import ProlificClient

client = ProlificClient()

# Create initial study
study = client.create_study({
    "name": "Initial Study",
    "description": "Test description",
    "reward": 100,
    "total_available_places": 20,
    "estimated_completion_time": 5,
    "external_study_url": "https://example.com/study?participant={{%PROLIFIC_PID%}}",
    "prolific_id_option": "url_parameters",
    "completion_codes": [
        {
            "code": "COMPLETED",
            "code_type": "COMPLETED",
            "actions": [{"action": "MANUALLY_REVIEW"}]
        }
    ]
})

study_id = study["id"]

# Review and decide to increase reward and participants
client.update_study(study_id, {
    "reward": 150,  # Increased from $1.00 to $1.50
    "total_available_places": 50,  # Increased from 20 to 50
    "name": "Updated Study Name",
    "description": "Updated: More detailed description of the study"
})

# Now launch with updated parameters
client.launch_study(study_id)
```

---

## Additional Resources

### Prolific Resources

- [Prolific API Documentation](https://api-help.prolific.com)
- [Prolific Researcher Dashboard](https://app.prolific.com)
- [Prolific Support](https://participant-help.prolific.com)

### MCP Resources

- [Model Context Protocol Specification](https://modelcontextprotocol.io)
- [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk)

### Project Resources

- Repository: [GitHub URL]
- Issues: [GitHub Issues URL]
- Discussions: [GitHub Discussions URL]

---

## Changelog

### Version 0.1.0 (Initial Release)

- Initial MCP server implementation
- 7 MCP tools for study management
- Prolific API client wrapper
- Configuration management
- Error handling and validation
- Comprehensive documentation

---

## License

[Add your license information here]

---

## Contributing

[Add contribution guidelines if applicable]

---

## Support

For issues, questions, or contributions:

- **GitHub Issues**: [Issues URL]
- **Email**: [Support Email]
- **Documentation**: This file and README.md

---

*Last Updated: November 2024*

