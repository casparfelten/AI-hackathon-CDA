# Prolific MCP Server

A Model Context Protocol (MCP) server that provides a translation layer between MCP and Prolific's API, enabling automated creation, launching, and result retrieval for user studies.

## Overview

This MCP server exposes Prolific API operations as MCP tools, allowing AI agents (like Gemini CLI) to autonomously manage user studies on Prolific. The server handles study creation, launching, monitoring, and result collection.

> 📖 **For detailed documentation**, see [DOCUMENTATION.md](DOCUMENTATION.md) - a comprehensive guide covering architecture, API reference, integration, examples, and troubleshooting.

## Features

- **Create Studies**: Programmatically create new studies with custom configurations
- **Launch Studies**: Start participant recruitment for studies
- **Monitor Studies**: Check study status and completion rates
- **Retrieve Results**: Get all submissions and data from completed studies
- **Update Studies**: Modify study parameters before or after launch
- **List Studies**: View all studies in your Prolific account
- **Test Mode**: Test studies without consuming credits using test participants

## Prerequisites

- Python 3.8 or higher
- A Prolific Researcher account with API access
- A Prolific API token

## Installation

1. Clone this repository:
```bash
git clone <repository-url>
cd AI-hackathon-CDA
```

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up your API credentials:
```bash
cp .env.example .env
# Edit .env and add your PROLIFIC_API_KEY
```

## Getting Your Prolific API Token

1. Log into your [Prolific Researcher Account](https://app.prolific.com)
2. Navigate to **Account** → **API Tokens**
3. Click **Create API Token**
4. Give it a name and generate the token
5. Copy the token to your `.env` file

## Usage

### Running the MCP Server

The server uses stdio transport for communication with MCP clients:

```bash
python -m prolific_mcp.server
```

### MCP Tools

The server exposes the following tools:

#### `prolific_create_study`
Create a new study on Prolific.

**Parameters:**
- `name` (required): Public name or title of the study (visible to participants)
- `description` (required): Study description for participants to read before starting
- `reward` (required): Reward amount in cents (e.g., 100 = $1.00)
- `total_available_places` (required): Number of participants needed
- `estimated_completion_time` (required): Estimated completion time in minutes
- `external_study_url` (required): URL to the external study (can include {{%PROLIFIC_PID%}}, {{%STUDY_ID%}}, {{%SESSION_ID%}} placeholders)
- `prolific_id_option` (optional, default: "url_parameters"): How to collect Prolific ID - "question", "url_parameters" (recommended), or "not_required"
- `completion_codes` (optional): Array of completion code objects. If not provided, defaults to a single "COMPLETED" code with MANUALLY_REVIEW action. Each code object requires: `code` (string), `code_type` (enum), and `actions` (array)
- `internal_name` (optional): Internal name for the study (not visible to participants)

#### `prolific_get_study`
Get details of a specific study.

**Parameters:**
- `study_id` (required): Prolific study ID

#### `prolific_update_study`
Update a study's parameters.

**Parameters:**
- `study_id` (required): Prolific study ID
- `updates` (required): Dictionary of fields to update

#### `prolific_launch_study`
Launch a study to start participant recruitment.

**Parameters:**
- `study_id` (required): Prolific study ID

#### `prolific_get_results`
Get all submissions/results for a study.

**Parameters:**
- `study_id` (required): Prolific study ID

#### `prolific_get_study_status`
Get the current status of a study.

**Parameters:**
- `study_id` (required): Prolific study ID

#### `prolific_list_studies`
List all studies in your account.

**Parameters:**
- `limit` (optional): Maximum number of studies to return

#### `prolific_create_test_participant`
Create a test participant account for testing studies without consuming credits.

**Parameters:**
- `email` (required): Email address for the test participant (cannot be an email already registered with Prolific)

**Notes:**
- Test participants can only take studies in workspaces where the feature is enabled
- Test participants cannot cash out any balance earned
- A randomly generated password is assigned; you may want to request a password reset
- At least one test participant must exist before launching test studies

#### `prolific_launch_test_study`
Launch a study in test mode (doesn't consume credits).

**Parameters:**
- `study_id` (required): Prolific study ID (must be in draft status)

**Notes:**
- Requires at least one test participant to exist (created via `prolific_create_test_participant`)
- Study must be in draft status
- Feature must be enabled for your workspace (contact Prolific support if unavailable)
- Returns study URL that can be used to complete the study as a test participant

## Example Workflow

1. **Create a study:**
```json
{
  "tool": "prolific_create_study",
  "arguments": {
    "name": "User Interface Preference Study",
    "description": "A study to understand user preferences for UI layouts",
    "reward": 150,
    "total_available_places": 50,
    "estimated_completion_time": 10,
    "external_study_url": "https://your-study-url.com?participant={{%PROLIFIC_PID%}}",
    "prolific_id_option": "url_parameters"
  }
}
```

2. **Launch the study:**
```json
{
  "tool": "prolific_launch_study",
  "arguments": {
    "study_id": "study_id_from_step_1"
  }
}
```

3. **Check study status:**
```json
{
  "tool": "prolific_get_study_status",
  "arguments": {
    "study_id": "study_id_from_step_1"
  }
}
```

4. **Get results:**
```json
{
  "tool": "prolific_get_results",
  "arguments": {
    "study_id": "study_id_from_step_1"
  }
}
```

## Test Mode Workflow

Test mode allows you to test your studies without consuming credits. This is the recommended way to test your integration.

1. **Create a test participant:**
```json
{
  "tool": "prolific_create_test_participant",
  "arguments": {
    "email": "test-participant@example.com"
  }
}
```

2. **Create a study (as usual):**
```json
{
  "tool": "prolific_create_study",
  "arguments": {
    "name": "Test Study",
    "description": "A test study",
    "reward": 100,
    "total_available_places": 10,
    "estimated_completion_time": 5,
    "external_study_url": "https://your-study-url.com?participant={{%PROLIFIC_PID%}}",
    "prolific_id_option": "url_parameters"
  }
}
```

3. **Launch the study in test mode:**
```json
{
  "tool": "prolific_launch_test_study",
  "arguments": {
    "study_id": "study_id_from_step_2"
  }
}
```

4. **Complete the study as a test participant** using the study URL returned from step 3

5. **Approve or reject submissions** normally using the Prolific interface

**Important Notes:**
- Test mode doesn't consume credits
- You must create at least one test participant before launching test studies
- Test participants are limited to studies in your workspace
- Test participants cannot cash out earnings

## Configuration

Configuration is managed through environment variables:

- `PROLIFIC_API_KEY`: Your Prolific API token (required)
- `PROLIFIC_API_BASE_URL`: API base URL (optional, defaults to `https://api.prolific.com/api/v1`)

## Project Structure

```
AI-hackathon-CDA/
├── src/
│   └── prolific_mcp/
│       ├── __init__.py
│       ├── server.py           # MCP server implementation
│       ├── prolific_client.py  # Prolific API client
│       └── config.py           # Configuration management
├── .env.example                # Example environment file
├── .gitignore
├── pyproject.toml             # Python project config
├── requirements.txt            # Dependencies
└── README.md
```

## Error Handling

The server handles Prolific API errors gracefully and returns meaningful error messages to the MCP client. Common errors include:

- Missing or invalid API key
- Invalid study IDs
- API rate limiting
- Network errors

## Development

To contribute or modify this project:

1. Install development dependencies:
```bash
pip install -e ".[dev]"
```

2. Run tests (when implemented):
```bash
pytest
```

3. Format code:
```bash
black src/
```

## License

[Add your license here]

## Documentation

- **[DOCUMENTATION.md](DOCUMENTATION.md)**: Complete detailed documentation covering:
  - Architecture and design
  - Complete API reference for all tools
  - Integration guides
  - Error handling
  - Best practices
  - Troubleshooting
  - Examples and use cases

## Support

For issues related to:
- **This MCP server**: Open an issue in this repository
- **Prolific API**: See [Prolific API Documentation](https://api-help.prolific.com)
- **Detailed help**: See [DOCUMENTATION.md](DOCUMENTATION.md) for comprehensive guides

