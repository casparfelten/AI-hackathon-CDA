"""Gemini client with MCP server integration."""

import asyncio
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Optional

from google import genai
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.server.stdio import stdio_server
import anyio

from .config import config
from .server import server


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
        """Connect to MCP server in-process (no subprocess)."""
        print("[MCP] Starting MCP server connection (in-process)...", flush=True)
        print("[MCP] Using in-process server connection for reliable communication", flush=True)
        
        # Use in-process server connection via memory streams
        # This avoids subprocess communication issues
        print("[MCP] Creating in-process server connection...", flush=True)
        
        # Create memory streams for in-process communication
        from anyio import create_memory_object_stream
        server_send, client_receive = create_memory_object_stream[dict](max_buffer_size=100)
        client_send, server_receive = create_memory_object_stream[dict](max_buffer_size=100)
        
        print("[MCP] ✓ Memory streams created for in-process communication", flush=True)
        
        # Start server task in background
        async def run_server():
            print("[MCP] Starting server task...", flush=True)
            try:
                async with stdio_server() as (read_stream, write_stream):
                    # Replace stdio streams with our memory streams
                    # We need to bridge the memory streams to the server
                    async def bridge_to_server():
                        async for message in server_receive:
                            await write_stream.send(message)
                    
                    async def bridge_from_server():
                        async for message in read_stream:
                            await server_send.send(message)
                    
                    # Run server with bridged streams
                    server_task = asyncio.create_task(
                        server.run(
                            server_receive,
                            server_send,
                            server.create_initialization_options()
                        )
                    )
                    bridge_tasks = [
                        asyncio.create_task(bridge_to_server()),
                        asyncio.create_task(bridge_from_server())
                    ]
                    
                    await server_task
                    for task in bridge_tasks:
                        task.cancel()
            except Exception as e:
                print(f"[MCP] Server task error: {e}", flush=True)
                import traceback
                traceback.print_exc()
        
        # Actually, let's use a simpler approach - direct server access
        # Since we're in-process, we can call the server directly
        print("[MCP] Using direct server access (in-process)...", flush=True)
        
        # Create a simple in-process session by wrapping server calls
        # We'll create a mock ClientSession that calls server directly
        class InProcessSession:
            def __init__(self):
                self._initialized = False
            
            async def initialize(self):
                print("[MCP] Initializing in-process session...", flush=True)
                # Server is already initialized, just mark as ready
                self._initialized = True
                print("[MCP] ✓ In-process session initialized", flush=True)
                return type('obj', (object,), {
                    'protocolVersion': '2024-11-05',
                    'capabilities': {},
                    'serverInfo': {'name': 'prolific-mcp', 'version': '1.0'}
                })()
            
            async def list_tools(self):
                if not self._initialized:
                    await self.initialize()
                print("[MCP] Listing tools via direct server call...", flush=True)
                # Call the registered list_tools handler
                from src.prolific_mcp.server import list_tools
                tools = await list_tools()
                print(f"[MCP] ✓ Server returned {len(tools)} tools", flush=True)
                return type('obj', (object,), {'tools': tools})()
            
            async def call_tool(self, name: str, arguments: dict):
                if not self._initialized:
                    await self.initialize()
                print(f"[MCP] Calling tool {name} via direct server call...", flush=True)
                # Call the registered call_tool handler
                from src.prolific_mcp.server import call_tool
                result = await call_tool(name, arguments)
                return type('obj', (object,), {'content': result})()
        
        self.mcp_session = InProcessSession()
        print("[MCP] ✓ In-process session created", flush=True)
        
        # Initialize the session
        print("[MCP] Initializing in-process MCP session...", flush=True)
        try:
            await self.mcp_session.initialize()
            print("[MCP] ✓ MCP session initialized successfully", flush=True)
        except Exception as e:
            print(f"[MCP] ✗ Error during MCP session initialization: {str(e)}", flush=True)
            import traceback
            traceback.print_exc()
            raise

        # List available tools
        print("[MCP] Listing available MCP tools...", flush=True)
        tools_result = await self.mcp_session.list_tools()
        print(f"[MCP] ✓ Received {len(tools_result.tools)} tools from MCP server", flush=True)
        self.mcp_tools = [self._mcp_tool_to_gemini_function(tool) for tool in tools_result.tools]
        print(f"[MCP] ✓ Converted {len(self.mcp_tools)} tools for Gemini", flush=True)
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
            print("[MCP] No tools available, returning None for tools config", flush=True)
            return None
        
        # Convert to Gemini's FunctionDeclaration format
        function_declarations = []
        for tool in self.mcp_tools:
            try:
                # Build properties dict
                properties = {}
                for k, v in tool.get("parameters", {}).get("properties", {}).items():
                    try:
                        properties[k] = self._convert_schema_property(v)
                    except Exception as prop_e:
                        print(f"[MCP] Error converting property {k} for tool {tool.get('name', 'unknown')}: {prop_e}", flush=True)
                        continue
                
                # Create Schema for the parameters object
                try:
                    # Try creating Schema with type as first positional argument
                    param_schema = genai.types.Schema(
                        genai.types.Type.OBJECT,
                        properties=properties,
                        required=tool.get("parameters", {}).get("required", []),
                    )
                except TypeError:
                    # Fallback to keyword arguments
                    try:
                        param_schema = genai.types.Schema(
                            type=genai.types.Type.OBJECT,
                            properties=properties,
                            required=tool.get("parameters", {}).get("required", []),
                        )
                    except TypeError:
                        param_schema = genai.types.Schema(
                            type_=genai.types.Type.OBJECT,
                            properties=properties,
                            required=tool.get("parameters", {}).get("required", []),
                        )
                
                func_decl = genai.types.FunctionDeclaration(
                    name=tool["name"],
                    description=tool["description"],
                    parameters=param_schema,
                )
                function_declarations.append(func_decl)
                print(f"[MCP] ✓ Successfully converted tool: {tool.get('name', 'unknown')}", flush=True)
            except Exception as e:
                print(f"[MCP] Error converting tool {tool.get('name', 'unknown')}: {e}", flush=True)
                import traceback
                traceback.print_exc()
                continue
        
        if not function_declarations:
            print("[MCP] No valid function declarations created, returning None", flush=True)
            return None
        
        # Gemini API expects a list of Tool objects
        tools_list = [genai.types.Tool(function_declarations=function_declarations)]
        print(f"[MCP] Prepared {len(function_declarations)} function declarations in 1 Tool object", flush=True)
        return tools_list

    def _generate_content_sync(self, model: str, contents: Any, tools: Any) -> Any:
        """Synchronous wrapper for generate_content (runs in executor)."""
        try:
            print(f"[Gemini] _generate_content_sync: model={model}, tools type={type(tools)}", flush=True)
            if tools is not None:
                print(f"[Gemini]   tools is list: {isinstance(tools, list)}, length: {len(tools) if isinstance(tools, list) else 'N/A'}", flush=True)
                if isinstance(tools, list) and len(tools) > 0:
                    tool = tools[0]
                    print(f"[Gemini]   Tool type: {type(tool)}", flush=True)
                    if hasattr(tool, 'function_declarations'):
                        print(f"[Gemini]   Function declarations count: {len(tool.function_declarations) if tool.function_declarations else 0}", flush=True)
            else:
                print(f"[Gemini]   tools is None (no tools will be passed)", flush=True)
            
            print(f"[Gemini] Calling generate_content API...", flush=True)
            # Only pass tools if it's not None
            # The API uses 'config' parameter with tools inside
            if tools is not None:
                # Try with config parameter
                try:
                    response = self.gemini_client.models.generate_content(
                        model=model,
                        contents=contents,
                        config=genai.types.GenerateContentConfig(tools=tools),
                    )
                except (TypeError, AttributeError):
                    # Fallback: try tools directly
                    try:
                        response = self.gemini_client.models.generate_content(
                            model=model,
                            contents=contents,
                            tools=tools,
                        )
                    except TypeError:
                        # Last resort: try as generate_content_config
                        response = self.gemini_client.models.generate_content(
                            model=model,
                            contents=contents,
                            generate_content_config=genai.types.GenerateContentConfig(tools=tools),
                        )
            else:
                response = self.gemini_client.models.generate_content(
                    model=model,
                    contents=contents,
                )
            print(f"[Gemini] ✓ generate_content API call completed", flush=True)
            return response
        except Exception as e:
            print(f"[Gemini] ✗ Error in _generate_content_sync: {str(e)}", flush=True)
            import traceback
            traceback.print_exc()
            raise

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
            
            # Debug logging for tools config
            if iteration == 1:
                print(f"[Gemini] Tools config type: {type(tools_config)}", flush=True)
                if tools_config is None:
                    print(f"[Gemini] ⚠ Tools config is None - no tools will be available", flush=True)
                elif isinstance(tools_config, list):
                    print(f"[Gemini] Tools config is a list with {len(tools_config)} items", flush=True)
                else:
                    print(f"[Gemini] Tools config is: {type(tools_config)}", flush=True)

            # Generate content with Gemini - run blocking call in executor to avoid blocking event loop
            try:
                if iteration == 1:
                    print(f"[Gemini] Iteration {iteration}: Sending initial request to model {model}...", flush=True)
                    if isinstance(current_prompt, str):
                        print(f"[Gemini]   Prompt length: {len(current_prompt)} characters", flush=True)
                    print(f"[Gemini]   Available tools: {len(self.mcp_tools) if self.mcp_tools else 0}", flush=True)
                    print(f"[Gemini]   Tools config ready: {tools_config is not None}", flush=True)
                    print(f"[Gemini]   About to enter executor for API call...", flush=True)
                else:
                    print(f"[Gemini] Iteration {iteration}: Sending follow-up request with function results...", flush=True)
                    print(f"[Gemini]   About to enter executor for API call...", flush=True)
                
                # Run the blocking generate_content call in a thread pool executor
                loop = asyncio.get_event_loop()
                request_start = time.time()
                print(f"[Gemini] Entering executor now (this may take a moment)...", flush=True)
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
                request_elapsed = time.time() - request_start
                print(f"[Gemini] ✓ Response received from model (took {request_elapsed:.2f} seconds)", flush=True)
            except asyncio.TimeoutError:
                print(f"[Gemini] API call timed out after 120 seconds", flush=True)
                return "Error: Gemini API call timed out"
            except Exception as e:
                print(f"[Gemini] Error calling API: {str(e)}", flush=True)
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
                    print(f"[Gemini] → Response contains {len(function_calls)} function call(s)", flush=True)
                    function_responses = []
                    for idx, func_call in enumerate(function_calls, 1):
                        tool_name = func_call.name
                        print(f"[Gemini]   Function call {idx}/{len(function_calls)}: {tool_name}", flush=True)
                        
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
                        
                        print(f"[MCP]   → Executing tool: {tool_name}", flush=True)
                        if arguments:
                            print(f"[MCP]     Arguments: {json.dumps(arguments, indent=2)[:200]}...", flush=True)
                        
                        # Call MCP tool
                        try:
                            mcp_start = time.time()
                            result = await self.mcp_session.call_tool(tool_name, arguments)
                            mcp_elapsed = time.time() - mcp_start
                            
                            # Format result for Gemini
                            result_text = "\n".join([content.text for content in result.content])
                            print(f"[MCP]   ✓ Tool {tool_name} executed successfully (took {mcp_elapsed:.2f} seconds)", flush=True)
                            print(f"[MCP]     Result length: {len(result_text)} characters", flush=True)
                            if len(result_text) < 500:
                                print(f"[MCP]     Result preview: {result_text[:200]}...", flush=True)
                            
                            # Create FunctionResponse - response must be a dict
                            function_responses.append(
                                genai.types.FunctionResponse(
                                    name=tool_name,
                                    response={"result": result_text}  # response must be dict
                                )
                            )
                        except Exception as e:
                            print(f"[MCP]   ✗ Error calling {tool_name}: {str(e)}", flush=True)
                            function_responses.append(
                                genai.types.FunctionResponse(
                                    name=tool_name,
                                    response={"error": str(e)}
                                )
                            )
                    
                    print(f"[Gemini] → Sending function results back to Gemini for next iteration...", flush=True)
                    
                    # Continue conversation with function results
                    # Format properly for Gemini API - use Content and Part objects
                    from google.genai.types import Content, Part
                    
                    # Model's response with function calls
                    model_parts = list(parts)  # parts are already Part objects
                    model_content = Content(role="model", parts=model_parts)
                    conversation_history.append(model_content)
                    
                    # User's function responses - wrap in Part objects
                    user_parts = []
                    for func_resp in function_responses:
                        # Create a Part with function_response
                        user_parts.append(Part(function_response=func_resp))
                    
                    user_content = Content(role="user", parts=user_parts)
                    conversation_history.append(user_content)
                    
                    # Continue conversation with function results
                    current_prompt = conversation_history
                    continue
                else:
                    # No function calls, return the response
                    response_text = "".join([
                        part.text for part in parts if hasattr(part, 'text') and part.text
                    ])
                    print(f"[Gemini] → No function calls in response - final answer ready", flush=True)
                    print(f"[Gemini]   Response length: {len(response_text)} characters", flush=True)
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
        gemini_type = type_map.get(prop_type, genai.types.Type.STRING)
        description = prop.get("description", "")
        
        # Handle array types - need to specify items
        if prop_type == "array" and "items" in prop:
            items_prop = prop["items"]
            # Recursively convert items schema
            items_schema = self._convert_schema_property(items_prop)
            # Create Schema with items
            try:
                return genai.types.Schema(
                    gemini_type,
                    description=description,
                    items=items_schema
                )
            except TypeError:
                try:
                    return genai.types.Schema(
                        type=gemini_type,
                        description=description,
                        items=items_schema
                    )
                except TypeError:
                    return genai.types.Schema(
                        type_=gemini_type,
                        description=description,
                        items=items_schema
                    )
        
        # Create Schema - try different argument patterns
        try:
            # Try positional type argument
            return genai.types.Schema(gemini_type, description=description)
        except TypeError:
            try:
                # Try type as keyword
                return genai.types.Schema(type=gemini_type, description=description)
            except TypeError:
                try:
                    # Try type_ as keyword
                    return genai.types.Schema(type_=gemini_type, description=description)
                except TypeError:
                    # Last resort: just type
                    return genai.types.Schema(gemini_type)

    async def close(self) -> None:
        """Close MCP session."""
        # In-process session doesn't need cleanup
        print("[MCP] Closing in-process session (no cleanup needed)...", flush=True)
        # Shutdown executor
        if hasattr(self, '_executor'):
            self._executor.shutdown(wait=False)

