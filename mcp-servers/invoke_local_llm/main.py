"""
MCP server that gives Claude Code a tool to access a local Ollama model.
Claude Code calls this server, which spins up an agent loop to do all the
file reads/lists, then returns a single summary back to Claude.
"""

import asyncio
import os
import json
import ollama

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp import types

MODEL_TO_USE = "qwen14b-explorer"
KEEP_ALIVE_TIMEOUT = "30s"

CLAUDE_CODE_TOOL_NAME = "invoke_local_llm"

app = Server("local-ollama-llm")


# fs tools for the local model
def is_allowed(path: str, allowed_dirs: list[str]) -> bool:
    path = os.path.realpath(path)
    return any(path.startswith(os.path.realpath(d)) for d in allowed_dirs)

def list_dir(path: str, allowed_dirs: list[str]) -> str:
    if not is_allowed(path, allowed_dirs):
        return f"Access denied: {path} is not in allowed directories"
    try:
        entries = os.listdir(path)
        # annotate dirs with trailing slash
        annotated = []
        for e in sorted(entries):
            full = os.path.join(path, e)
            annotated.append(e + "/" if os.path.isdir(full) else e)
        return "\n".join(annotated)
    except Exception as ex:
        return f"Error listing {path}: {ex}"

def read_file(path: str, allowed_dirs: list[str]) -> str:
    if not is_allowed(path, allowed_dirs):
        return f"Access denied: {path} is not in allowed directories"
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
        # soft cap to avoid blowing context
        if len(content) > 40_000:
            content = content[:40_000] + "\n\n[... file truncated at 40k chars ...]"
        return content
    except Exception as ex:
        return f"Error reading {path}: {ex}"


# tool defs passed to ollama
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "list_dir",
            "description": "List contents of a directory. Directories are shown with a trailing slash.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Absolute path to directory"}
                },
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read the contents of a file.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Absolute path to file"}
                },
                "required": ["path"]
            }
        }
    }
]


# agent loop
async def run_agent(prompt: str, allowed_dirs: list[str], max_steps: int = 30) -> str:
    system = (
        "You are an assistant for another AI agent. "
        "You have access to list_dir and read_file tools. "
        "Use them to answer the user's question thoroughly. "
        "When you have enough information, stop calling tools and give a clear, concise summary. "
        f"You may only access these directories: {', '.join(allowed_dirs)}"
    )

    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": prompt}
    ]

    for step in range(max_steps):
        response = ollama.chat(
            model=MODEL_TO_USE,
            messages=messages,
            tools=TOOLS,
            keep_alive=KEEP_ALIVE_TIMEOUT
        )

        msg = response["message"]
        messages.append(msg)

        tool_calls = msg.get("tool_calls") or []

        if not tool_calls:
            # model is done, return final answer
            return msg.get("content") or "No response from model."

        # execute each tool call
        for call in tool_calls:
            fn = call["function"]["name"]
            args = call["function"]["arguments"]
            if isinstance(args, str):
                args = json.loads(args)

            if fn == "list_dir":
                result = list_dir(args.get("path", ""), allowed_dirs)
            elif fn == "read_file":
                result = read_file(args.get("path", ""), allowed_dirs)
            else:
                result = f"Unknown tool: {fn}"

            messages.append({
                "role": "tool",
                "content": result
            })

    return "Reached maximum exploration steps. Partial findings: " + (msg.get("content") or "")


# mcp tool for claude code
@app.list_tools()
async def list_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name=CLAUDE_CODE_TOOL_NAME,
            description=(
                "Delegates a task to a local LLM. "
                "The local model can list directories and read files autonomously, "
                "then return a single summarized answer. Use this to reduce token usage "
                "on repetitive filesystem exploration tasks."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "prompt": {
                        "type": "string",
                        "description": "What the local model should do"
                    },
                    "allowed_dirs": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of absolute directory paths the local model is allowed to access"
                    },
                    "max_steps": {
                        "type": "integer",
                        "description": "Max tool calls the local model can make. Default: 30.",
                        "default": 30
                    }
                },
                "required": ["prompt", "allowed_dirs"]
            }
        )
    ]

@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:
    if name != CLAUDE_CODE_TOOL_NAME:
        return [types.TextContent(type="text", text=f"Unknown tool: {name}")]

    prompt = arguments["prompt"]
    allowed_dirs = arguments["allowed_dirs"]
    max_steps = arguments.get("max_steps", 30)

    result = await run_agent(prompt, allowed_dirs, max_steps)
    return [types.TextContent(type="text", text=result)]


async def main():
    async with stdio_server() as (r, w):
        await app.run(r, w, app.create_initialization_options())

if __name__ == "__main__":
    asyncio.run(main())