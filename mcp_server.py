#!/usr/bin/env python3

import json
import sys
from typing import Any, Dict, List
import asyncio

# Import all the tool functions
from llm import (
    wikipedia_search, web_search, call_grok, call_openai, call_gemini, 
    call_claude, call_consensus_query, call_superconsensus, notify_human
)
from conversation_index import lookup_past_conversations
from file_tools import read_file, write_file, list_directory, create_directory
from system_tools import grep_files, find_files, head_file, tail_file, cat_file
from python_executor import execute_python_code, install_package

class MCPServer:
    def __init__(self):
        self.tools = {
            # LLM tools, focused on things Claude can't already do
            "wikipedia_search": {
                "function": wikipedia_search,
                "description": "Search Wikipedia for information",
                "parameters": {"query": "string"}
            },
            "web_search": {
                "function": web_search,
                "description": "Perform web search",
                "parameters": {"query": "string"}
            },
            # "call_grok": {
            #     "function": call_grok,
            #     "description": "Call Grok model",
            #     "parameters": {"prompt": "string"}
            # },
            # "call_openai": {
            #     "function": call_openai,
            #     "description": "Call OpenAI GPT-5",
            #     "parameters": {"prompt": "string"}
            # },
            # "call_gemini": {
            #     "function": call_gemini,
            #     "description": "Call Google Gemini",
            #     "parameters": {"prompt": "string"}
            # },
            # "call_claude": {
            #     "function": call_claude,
            #     "description": "Call Anthropic Claude",
            #     "parameters": {"prompt": "string"}
            # },
            "call_consensus_query": {
                "function": call_consensus_query,
                "description": "Get consensus from multiple LLMs",
                "parameters": {"prompt": "string"}
            },
            "call_superconsensus": {
                "function": call_superconsensus,
                "description": "Get superconsensus with cross-model selection",
                "parameters": {"prompt": "string"}
            },
            # "notify_human": {
            #     "function": notify_human,
            #     "description": "Play text sound notification when user input is required",
            #     "parameters": {"message": "string"}
            # },
            # "lookup_past_conversations": {
            #     "function": lookup_past_conversations,
            #     "description": "Search past conversations",
            #     "parameters": {"query": "string"}
            # },
            # # File operations
            # "read_file": {
            #     "function": read_file,
            #     "description": "Read file contents",
            #     "parameters": {"filepath": "string"}
            # },
            # "write_file": {
            #     "function": write_file,
            #     "description": "Write file contents",
            #     "parameters": {"filepath": "string", "content": "string"}
            # },
            # "list_directory": {
            #     "function": list_directory,
            #     "description": "List directory contents",
            #     "parameters": {"dirpath": "string"}
            # },
            # # System tools
            # "grep_files": {
            #     "function": grep_files,
            #     "description": "Search patterns in files",
            #     "parameters": {"pattern": "string", "directory": "string", "recursive": "boolean", "case_insensitive": "boolean"}
            # },
            # "find_files": {
            #     "function": find_files,
            #     "description": "Find files by pattern",
            #     "parameters": {"name_pattern": "string", "directory": "string", "file_type": "string"}
            # },
            # "head_file": {
            #     "function": head_file,
            #     "description": "Show first lines of file",
            #     "parameters": {"filepath": "string", "lines": "integer"}
            # },
            # "tail_file": {
            #     "function": tail_file,
            #     "description": "Show last lines of file",
            #     "parameters": {"filepath": "string", "lines": "integer"}
            # },
            # "cat_file": {
            #     "function": cat_file,
            #     "description": "Display file contents",
            #     "parameters": {"filepath": "string"}
            # },
            # # Python execution
            # "execute_python_code": {
            #     "function": execute_python_code,
            #     "description": "Execute Python code in isolated environment",
            #     "parameters": {"code": "string", "timeout": "integer"}
            # },
            # "install_package": {
            #     "function": install_package,
            #     "description": "Install Python package",
            #     "parameters": {"package": "string"}
            # }
        }

    async def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle incoming MCP requests."""
        try:
            method = request.get("method")
            params = request.get("params", {})
            request_id = request.get("id")

            if method == "initialize":
                return {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {
                        "protocolVersion": "2024-11-05",
                        "capabilities": {
                            "tools": {}
                        },
                        "serverInfo": {
                            "name": "llm-client",
                            "version": "1.0.0"
                        }
                    }
                }

            elif method == "tools/list":
                tool_list = []
                for name, info in self.tools.items():
                    tool_spec = {
                        "name": name,
                        "description": info["description"],
                        "inputSchema": {
                            "type": "object",
                            "properties": {},
                            "required": []
                        }
                    }
                    
                    # Build parameter schema
                    for param_name, param_type in info["parameters"].items():
                        tool_spec["inputSchema"]["properties"][param_name] = {"type": param_type}
                        if param_name in ["query", "prompt", "filepath", "code", "pattern"]:  # Required params
                            tool_spec["inputSchema"]["required"].append(param_name)
                        elif param_name == "message" and name == "notify_human":  # Message is optional for notify_human
                            pass  # Don't add to required
                    
                    tool_list.append(tool_spec)

                return {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {"tools": tool_list}
                }

            elif method == "tools/call":
                tool_name = params.get("name")
                arguments = params.get("arguments", {})

                if tool_name not in self.tools:
                    return {
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "error": {
                            "code": -32601,
                            "message": f"Unknown tool: {tool_name}"
                        }
                    }

                # Call the tool function
                tool_function = self.tools[tool_name]["function"]
                
                try:
                    result = tool_function(**arguments)
                    
                    return {
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "result": {
                            "content": [
                                {
                                    "type": "text",
                                    "text": str(result)
                                }
                            ]
                        }
                    }
                except Exception as e:
                    # Notify human for critical tool execution errors
                    try:
                        notify_human(f"Tool execution error for {tool_name}: {str(e)}")
                    except Exception:
                        pass  # Don't let notification errors break the MCP response
                    
                    return {
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "error": {
                            "code": -32603,
                            "message": f"Tool execution error: {str(e)}"
                        }
                    }

            else:
                return {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "error": {
                        "code": -32601,
                        "message": f"Unknown method: {method}"
                    }
                }

        except Exception as e:
            return {
                "jsonrpc": "2.0",
                "id": request.get("id"),
                "error": {
                    "code": -32603,
                    "message": f"Internal error: {str(e)}"
                }
            }

    async def run(self):
        """Run the MCP server."""
        print("🚀 Starting LLM Client MCP Server...", file=sys.stderr)
        print("📡 Available tools: LLM calls, file operations, system tools, Python execution", file=sys.stderr)
        
        while True:
            try:
                line = sys.stdin.readline()
                if not line:
                    break
                
                request = json.loads(line.strip())
                response = await self.handle_request(request)
                
                print(json.dumps(response))
                sys.stdout.flush()
                
            except json.JSONDecodeError:
                error_response = {
                    "jsonrpc": "2.0",
                    "id": None,
                    "error": {
                        "code": -32700,
                        "message": "Parse error"
                    }
                }
                print(json.dumps(error_response))
                sys.stdout.flush()
            except Exception as e:
                error_response = {
                    "jsonrpc": "2.0",
                    "id": None,
                    "error": {
                        "code": -32603,
                        "message": f"Internal error: {str(e)}"
                    }
                }
                print(json.dumps(error_response))
                sys.stdout.flush()

async def main():
    server = MCPServer()
    await server.run()

if __name__ == "__main__":
    asyncio.run(main())