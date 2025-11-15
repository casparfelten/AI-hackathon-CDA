"""Gemini client with MCP server integration."""

import asyncio
import json
import sys
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Optional

from google import genai
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from .config import config


class GeminiMCPClient:
    """Client that integrates Gemini API with MCP server for Prolific tools."""

    def __init__(self):
        """Initialize Gemini MCP client."""
        config.validate_gemini()
        self.gemini_client = genai.Client(api_key=config.gemini_api_key)
        self.mcp_session: Optional[ClientSession] = None
        self.mcp_tools: list[dict[str, Any]] = []
        self._stdio_ctx: Optional[Any] = None
        self._tools_config_cache: Optional[Any] = None  # Cache converted tools
        self._executor = ThreadPoolExecutor(max_workers=1)  # For running blocking calls

    async def connect(self) -> None:
        """Connect to MCP server via stdio."""
        # Start MCP server as subprocess
        server_params = StdioServerParameters(
            command=sys.executable,
            args=["-m", "src.prolific_mcp.server"],
            env=None,  # Will inherit environment including PROLIFIC_API_KEY
        )

        # Connect to MCP server - stdio_client returns an async context manager
        # We need to enter it and keep it alive for the client lifetime
        self._stdio_ctx = stdio_client(server_params)
        
        # Enter the context manager - this returns the streams
        read_stream, write_stream = await self._stdio_ctx.__aenter__()
        
        # Create and initialize the MCP session
        self.mcp_session = ClientSession(read_stream, write_stream)
        await self.mcp_session.initialize()

        # List available tools
        tools_result = await self.mcp_session.list_tools()
        self.mcp_tools = [self._mcp_tool_to_gemini_function(tool) for tool in tools_result.tools]
        # Pre-convert tools to avoid doing it on every iteration
        self._tools_config_cache = self._prepare_tools_config()

    def _mcp_tool_to_gemini_function(self, mcp_tool: Any) -> dict[str, Any]:
        """Convert MCP Tool to Gemini FunctionDeclaration format."""
        return {
            "name": mcp_tool.name,
            "description": mcp_tool.description or "",
            "parameters": mcp_tool.inputSchema or {},
        }

    def _prepare_tools_config(self) -> Optional[Any]:
        """Prepare tools configuration for Gemini (cached to avoid re-converting)."""
        if not self.mcp_tools:
            return None
        
        # Convert to Gemini's FunctionDeclaration format
        function_declarations = []
        for tool in self.mcp_tools:
            function_declarations.append(
                genai.types.FunctionDeclaration(
                    name=tool["name"],
                    description=tool["description"],
                    parameters=genai.types.Schema(
                        type_=genai.types.Type.OBJECT,
                        properties={
                            k: self._convert_schema_property(v)
                            for k, v in tool.get("parameters", {}).get("properties", {}).items()
                        },
                        required=tool.get("parameters", {}).get("required", []),
                    ),
                )
            )
        return [genai.types.Tool(function_declarations=function_declarations)]

    def _generate_content_sync(self, model: str, contents: Any, tools: Any) -> Any:
        """Synchronous wrapper for generate_content (runs in executor)."""
        return self.gemini_client.models.generate_content(
            model=model,
            contents=contents,
            tools=tools,
        )

    async def chat(self, prompt: str, model: str = "gemini-2.0-flash-exp") -> str:
        """
        Send a prompt to Gemini and handle function calls via MCP.
        
        Args:
            prompt: User prompt to send to Gemini
            model: Gemini model to use
            
        Returns:
            Final response text from Gemini
        """
        if not self.mcp_session:
            await self.connect()

        conversation_history = []
        max_iterations = 10  # Prevent infinite loops
        iteration = 0

        current_prompt = prompt

        while iteration < max_iterations:
            iteration += 1

            # Use cached tools config (prepared during connect)
            tools_config = self._tools_config_cache

            # Generate content with Gemini - run blocking call in executor to avoid blocking event loop
            try:
                if iteration == 1:
                    print(f"[Gemini] Sending initial prompt to model {model}...")
                else:
                    print(f"[Gemini] Iteration {iteration}: Continuing conversation with function results...")
                
                # Run the blocking generate_content call in a thread pool executor
                loop = asyncio.get_event_loop()
                response = await asyncio.wait_for(
                    loop.run_in_executor(
                        self._executor,
                        self._generate_content_sync,
                        model,
                        current_prompt,
                        tools_config,
                    ),
                    timeout=120.0  # 2 minute timeout per API call
                )
                print(f"[Gemini] Response received from model")
            except asyncio.TimeoutError:
                print(f"[Gemini] API call timed out after 120 seconds")
                return "Error: Gemini API call timed out"
            except Exception as e:
                print(f"[Gemini] Error calling API: {str(e)}")
                return f"Error calling Gemini: {str(e)}"

            # Check if Gemini wants to call a function
            if response.candidates and response.candidates[0].content.parts:
                parts = response.candidates[0].content.parts
                
                # Check for function calls
                function_calls = []
                for part in parts:
                    if hasattr(part, 'function_call') and part.function_call:
                        function_calls.append(part.function_call)
                
                if function_calls:
                    # Execute function calls via MCP
                    print(f"[Gemini] Gemini wants to call {len(function_calls)} function(s)")
                    function_responses = []
                    for idx, func_call in enumerate(function_calls, 1):
                        tool_name = func_call.name
                        print(f"[Gemini] Function call {idx}/{len(function_calls)}: {tool_name}")
                        
                        # Parse arguments - Gemini may provide as dict or JSON string
                        if hasattr(func_call, 'args'):
                            if isinstance(func_call.args, str):
                                try:
                                    arguments = json.loads(func_call.args)
                                except json.JSONDecodeError:
                                    arguments = {}
                            else:
                                arguments = func_call.args
                        else:
                            arguments = {}
                        
                        print(f"[MCP] Calling tool: {tool_name}")
                        print(f"[MCP] Arguments: {json.dumps(arguments, indent=2) if arguments else '{}'}")
                        
                        # Call MCP tool
                        try:
                            result = await self.mcp_session.call_tool(tool_name, arguments)
                            
                            # Format result for Gemini
                            result_text = "\n".join([content.text for content in result.content])
                            print(f"[MCP] Tool {tool_name} executed successfully")
                            print(f"[MCP] Result length: {len(result_text)} characters")
                            if len(result_text) < 500:
                                print(f"[MCP] Result preview: {result_text[:200]}...")
                            
                            function_responses.append(
                                genai.types.FunctionResponse(
                                    name=tool_name,
                                    response={"result": result_text}
                                )
                            )
                        except Exception as e:
                            print(f"[MCP] Error calling {tool_name}: {str(e)}")
                            function_responses.append(
                                genai.types.FunctionResponse(
                                    name=tool_name,
                                    response={"error": str(e)}
                                )
                            )
                    
                    print(f"[Gemini] Sending function results back to Gemini...")
                    
                    # Continue conversation with function results
                    conversation_history.append({
                        "role": "model",
                        "parts": parts,
                    })
                    conversation_history.append({
                        "role": "user",
                        "parts": function_responses,
                    })
                    
                    # Continue conversation with function results
                    current_prompt = conversation_history
                    continue
                else:
                    # No function calls, return the response
                    response_text = "".join([
                        part.text for part in parts if hasattr(part, 'text') and part.text
                    ])
                    print(f"[Gemini] No more function calls needed. Final response ready.")
                    print(f"[Gemini] Response length: {len(response_text)} characters")
                    return response_text
            else:
                # No content in response
                return "No response from Gemini"

        return "Maximum iterations reached"

    def _convert_schema_property(self, prop: dict[str, Any]) -> genai.types.Schema:
        """Convert JSON schema property to Gemini Schema."""
        prop_type = prop.get("type", "string")
        type_map = {
            "string": genai.types.Type.STRING,
            "integer": genai.types.Type.INTEGER,
            "number": genai.types.Type.NUMBER,
            "boolean": genai.types.Type.BOOLEAN,
            "array": genai.types.Type.ARRAY,
            "object": genai.types.Type.OBJECT,
        }
        return genai.types.Schema(
            type_=type_map.get(prop_type, genai.types.Type.STRING),
            description=prop.get("description", ""),
        )

    async def close(self) -> None:
        """Close MCP session."""
        if hasattr(self, '_stdio_ctx') and self._stdio_ctx:
            try:
                await self._stdio_ctx.__aexit__(None, None, None)
            except Exception:
                pass
        if self.mcp_session:
            try:
                await self.mcp_session.__aexit__(None, None, None)
            except Exception:
                pass
        # Shutdown executor
        if hasattr(self, '_executor'):
            self._executor.shutdown(wait=False)

