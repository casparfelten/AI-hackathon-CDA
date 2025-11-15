"""MCP server for Prolific API integration."""

import asyncio
import json
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

from .prolific_client import ProlificClient, ProlificAPIError

# Initialize the Prolific client
client = ProlificClient()

# Create MCP server instance
server = Server("prolific-mcp")


@server.list_tools()
async def list_tools() -> list[Tool]:
    """List available MCP tools for Prolific operations."""
    return [
        Tool(
            name="prolific_create_study",
            description="Create a new study on Prolific. Requires study configuration including name, description, reward, duration, external study URL, prolific_id_option, and completion_codes.",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Public name or title of the study (visible to participants)"
                    },
                    "description": {
                        "type": "string",
                        "description": "Study description for participants to read before starting"
                    },
                    "reward": {
                        "type": "integer",
                        "description": "Reward amount in cents (e.g., 100 = $1.00)"
                    },
                    "total_available_places": {
                        "type": "integer",
                        "description": "Number of participants needed"
                    },
                    "estimated_completion_time": {
                        "type": "integer",
                        "description": "Estimated completion time in minutes"
                    },
                    "external_study_url": {
                        "type": "string",
                        "description": "URL to the external study. Can include {{%PROLIFIC_PID%}}, {{%STUDY_ID%}}, {{%SESSION_ID%}} placeholders"
                    },
                    "prolific_id_option": {
                        "type": "string",
                        "enum": ["question", "url_parameters", "not_required"],
                        "description": "How to collect Prolific ID. 'url_parameters' (recommended) passes ID in URL, 'question' asks in survey, 'not_required' skips collection",
                        "default": "url_parameters"
                    },
                    "completion_codes": {
                        "type": "array",
                        "description": "Array of completion code objects. If not provided, defaults to a single 'COMPLETED' code with MANUALLY_REVIEW action.",
                        "items": {
                            "type": "object",
                            "properties": {
                                "code": {
                                    "type": "string",
                                    "description": "The completion code participants will enter"
                                },
                                "code_type": {
                                    "type": "string",
                                    "enum": ["COMPLETED", "FAILED_ATTENTION_CHECK", "FOLLOW_UP_STUDY", "GIVE_BONUS", "INCOMPATIBLE_DEVICE", "NO_CONSENT", "OTHER", "FIXED_SCREENOUT"],
                                    "description": "Type/category of the completion code"
                                },
                                "actions": {
                                    "type": "array",
                                    "description": "Actions to take when this code is used",
                                    "items": {
                                        "type": "object",
                                        "properties": {
                                            "action": {
                                                "type": "string",
                                                "enum": ["AUTOMATICALLY_APPROVE", "MANUALLY_REVIEW", "REQUEST_RETURN", "ADD_TO_PARTICIPANT_GROUP", "REMOVE_FROM_PARTICIPANT_GROUP"],
                                                "description": "Action to perform"
                                            }
                                        }
                                    }
                                }
                            },
                            "required": ["code", "code_type", "actions"]
                        }
                    },
                    "internal_name": {
                        "type": "string",
                        "description": "Internal name for the study (optional, not visible to participants)"
                    },
                },
                "required": ["name", "description", "reward", "total_available_places", "estimated_completion_time", "external_study_url"]
            }
        ),
        Tool(
            name="prolific_get_study",
            description="Get details of a specific study by ID.",
            inputSchema={
                "type": "object",
                "properties": {
                    "study_id": {
                        "type": "string",
                        "description": "Prolific study ID"
                    }
                },
                "required": ["study_id"]
            }
        ),
        Tool(
            name="prolific_update_study",
            description="Update a study's parameters. Provide study_id and the fields to update.",
            inputSchema={
                "type": "object",
                "properties": {
                    "study_id": {
                        "type": "string",
                        "description": "Prolific study ID"
                    },
                    "updates": {
                        "type": "object",
                        "description": "Dictionary of fields to update (e.g., {'title': 'New Title', 'reward': 150})"
                    }
                },
                "required": ["study_id", "updates"]
            }
        ),
        Tool(
            name="prolific_launch_study",
            description="Launch a study to start participant recruitment.",
            inputSchema={
                "type": "object",
                "properties": {
                    "study_id": {
                        "type": "string",
                        "description": "Prolific study ID"
                    }
                },
                "required": ["study_id"]
            }
        ),
        Tool(
            name="prolific_get_results",
            description="Get all submissions/results for a completed or in-progress study.",
            inputSchema={
                "type": "object",
                "properties": {
                    "study_id": {
                        "type": "string",
                        "description": "Prolific study ID"
                    }
                },
                "required": ["study_id"]
            }
        ),
        Tool(
            name="prolific_get_study_status",
            description="Get the current status of a study including completion rate and places taken.",
            inputSchema={
                "type": "object",
                "properties": {
                    "study_id": {
                        "type": "string",
                        "description": "Prolific study ID"
                    }
                },
                "required": ["study_id"]
            }
        ),
        Tool(
            name="prolific_list_studies",
            description="List all studies. Optionally limit the number of results.",
            inputSchema={
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of studies to return (optional)"
                    }
                }
            }
        ),
        Tool(
            name="prolific_delete_study",
            description="Delete a study. Only draft studies can be deleted.",
            inputSchema={
                "type": "object",
                "properties": {
                    "study_id": {
                        "type": "string",
                        "description": "Prolific study ID"
                    }
                },
                "required": ["study_id"]
            }
        ),
        Tool(
            name="prolific_create_test_participant",
            description="Create a test participant account for testing studies without consuming credits. Test participants can only take studies in workspaces where the feature is enabled and cannot cash out earnings.",
            inputSchema={
                "type": "object",
                "properties": {
                    "email": {
                        "type": "string",
                        "format": "email",
                        "description": "Email address for the test participant (cannot be an email already registered with Prolific)"
                    }
                },
                "required": ["email"]
            }
        ),
        Tool(
            name="prolific_launch_test_study",
            description="Launch a study in test mode (doesn't consume credits). Requires at least one test participant to exist and the study must be in draft status. The feature must be enabled for your workspace.",
            inputSchema={
                "type": "object",
                "properties": {
                    "study_id": {
                        "type": "string",
                        "description": "Prolific study ID (must be in draft status)"
                    }
                },
                "required": ["study_id"]
            }
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any] | None) -> list[TextContent]:
    """Handle tool calls from the MCP client."""
    if arguments is None:
        arguments = {}

    try:
        if name == "prolific_create_study":
            # Ensure required fields have defaults if not provided
            study_config = dict(arguments)
            
            # Set default prolific_id_option if not provided
            if "prolific_id_option" not in study_config:
                study_config["prolific_id_option"] = "url_parameters"
            
            # Set default completion_codes if not provided
            if "completion_codes" not in study_config or not study_config["completion_codes"]:
                study_config["completion_codes"] = [
                    {
                        "code": "COMPLETED",
                        "code_type": "COMPLETED",
                        "actions": [{"action": "MANUALLY_REVIEW"}]
                    }
                ]
            
            result = client.create_study(study_config)
            return [TextContent(
                type="text",
                text=f"Study created successfully:\n{json.dumps(result, indent=2)}"
            )]

        elif name == "prolific_get_study":
            study_id = arguments.get("study_id")
            if not study_id:
                raise ValueError("study_id is required")
            result = client.get_study(study_id)
            return [TextContent(
                type="text",
                text=f"Study details:\n{json.dumps(result, indent=2)}"
            )]

        elif name == "prolific_update_study":
            study_id = arguments.get("study_id")
            updates = arguments.get("updates")
            if not study_id:
                raise ValueError("study_id is required")
            if not updates:
                raise ValueError("updates is required")
            result = client.update_study(study_id, updates)
            return [TextContent(
                type="text",
                text=f"Study updated successfully:\n{json.dumps(result, indent=2)}"
            )]

        elif name == "prolific_launch_study":
            study_id = arguments.get("study_id")
            if not study_id:
                raise ValueError("study_id is required")
            result = client.launch_study(study_id)
            return [TextContent(
                type="text",
                text=f"Study launched successfully:\n{json.dumps(result, indent=2)}"
            )]

        elif name == "prolific_get_results":
            study_id = arguments.get("study_id")
            if not study_id:
                raise ValueError("study_id is required")
            result = client.get_submissions(study_id)
            return [TextContent(
                type="text",
                text=f"Study submissions:\n{json.dumps(result, indent=2)}"
            )]

        elif name == "prolific_get_study_status":
            study_id = arguments.get("study_id")
            if not study_id:
                raise ValueError("study_id is required")
            result = client.get_study_status(study_id)
            return [TextContent(
                type="text",
                text=f"Study status:\n{json.dumps(result, indent=2)}"
            )]

        elif name == "prolific_list_studies":
            limit = arguments.get("limit")
            result = client.list_studies(limit=limit)
            return [TextContent(
                type="text",
                text=f"Studies:\n{json.dumps(result, indent=2)}"
            )]

        elif name == "prolific_delete_study":
            study_id = arguments.get("study_id")
            if not study_id:
                raise ValueError("study_id is required")
            client.delete_study(study_id)
            return [TextContent(
                type="text",
                text=f"Study {study_id} deleted successfully"
            )]

        elif name == "prolific_create_test_participant":
            email = arguments.get("email")
            if not email:
                raise ValueError("email is required")
            result = client.create_test_participant(email)
            return [TextContent(
                type="text",
                text=f"Test participant created successfully:\n{json.dumps(result, indent=2)}"
            )]

        elif name == "prolific_launch_test_study":
            study_id = arguments.get("study_id")
            if not study_id:
                raise ValueError("study_id is required")
            result = client.launch_test_study(study_id)
            return [TextContent(
                type="text",
                text=f"Test study launched successfully:\n{json.dumps(result, indent=2)}"
            )]

        else:
            raise ValueError(f"Unknown tool: {name}")

    except ProlificAPIError as e:
        error_msg = f"Prolific API error: {e.message}"
        if e.status_code:
            error_msg += f" (Status: {e.status_code})"
        if e.response:
            error_msg += f"\nResponse: {json.dumps(e.response, indent=2)}"
        return [TextContent(type="text", text=error_msg)]

    except Exception as e:
        return [TextContent(
            type="text",
            text=f"Error: {str(e)}"
        )]


async def main():
    """Run the MCP server using stdio transport."""
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options()
        )


if __name__ == "__main__":
    asyncio.run(main())

