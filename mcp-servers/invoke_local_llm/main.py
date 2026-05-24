"""
MCP server that gives Claude Code a tool to access a local Ollama model.
Claude Code calls this server, which spins up an agent loop to do all the
file reads/lists, then returns a single summary back to Claude.
"""

import asyncio
import os
import json
import sys
import ollama

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp import types

MODEL_TO_USE = "qwen2.5:7b"       # The model to use
KEEP_ALIVE_TIMEOUT = "30s"        # How long after the model is finished to wait before unloading it (keep at least ~20s to keep the model alive during tool calls)
LAYERS_ON_GPU = 9999              # How many layers of the LLM to run on the GPU (to run all, use a very large number like 9999)
CONTEXT_WINDOW = 32768            # Size of the LLM's context window (here: 32k tokens)

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
                "required": ["path"],
            },
        },
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
                "required": ["path"],
            },
        },
    },
]


# agent loop
async def run_agent(prompt: str, allowed_dirs: list[str]) -> str:
    system = (
        "You are a code-reading agent working on behalf of another AI. "
        "Your ONLY job is to collect raw facts from the codebase using list_dir and read_file. "
        "Do NOT reason about design, make recommendations, or explain tradeoffs — the calling agent handles that. "
        "Do NOT infer or assume anything you have not read directly from a file. "
        "If a file does not exist or is empty, say so explicitly. "
        "For every fact you report, include the exact file path and line number. "
        "Report findings as a structured list of facts. No prose summaries, no suggestions. "
        "Read every file the prompt asks for before responding — do not stop early. "
        "Once you have read all relevant files, your final message MUST be a structured summary of all facts collected. "
        "Do not make any more tool calls after the summary — just return the summary as plain text. "
        f"You may only access these directories: {', '.join(allowed_dirs)}"
    )

    messages: list[dict] = [
        {"role": "system", "content": system},
        {"role": "user", "content": prompt},
    ]

    msg: dict = {"content": "No steps were executed."}

    loop = asyncio.get_event_loop()
    step = 0

    while True:
        msgs_snapshot = list(messages)

        response = await loop.run_in_executor(
            None,
            lambda m=msgs_snapshot: ollama.chat(
                model=MODEL_TO_USE,
                messages=m,
                tools=TOOLS,
                keep_alive=KEEP_ALIVE_TIMEOUT,
                options={
                    "num_gpu": LAYERS_ON_GPU,
                    "num_ctx": CONTEXT_WINDOW,
                },
            ),
        )

        msg = response["message"]
        messages.append(msg)

        tool_calls: list[dict] = msg.get("tool_calls") or []

        print(
            f"[ollama-mcp] step={step} tool_calls={[c['function']['name'] for c in tool_calls]}",
            file=sys.stderr,
        )
        step += 1

        # model is done, return its final answer
        if not tool_calls:
            content = msg.get("content")
            if content:
                return content
            # Model stopped without a text reply, return last tool results as fallback
            tool_results = [m["content"] for m in messages if m.get("role") == "tool"]
            if tool_results:
                return "Model returned no summary. Raw tool results:\n\n" + "\n---\n".join(tool_results[-10:])
            return "No response from model."

        # execute each tool call and feed results back
        for call in tool_calls:
            fn_info = call["function"]
            fn_name = fn_info["name"]
            args = fn_info["arguments"]
            if isinstance(args, str):
                args = json.loads(args)

            # capture tool_call_id so the model can correlate results
            call_id: str = call.get("id", fn_name)

            if fn_name == "list_dir":
                result = list_dir(args.get("path", ""), allowed_dirs)
            elif fn_name == "read_file":
                result = read_file(args.get("path", ""), allowed_dirs)
            else:
                result = f"Unknown tool: {fn_name}"

            print(f"[ollama-mcp]   {fn_name}({args}) -> {len(result)} chars", file=sys.stderr)

            # FIX: include tool_call_id so models that require it work correctly
            messages.append({
                "role": "tool",
                "tool_call_id": call_id,
                "content": result,
            })


# mcp tool for claude code
@app.list_tools()
async def list_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name=CLAUDE_CODE_TOOL_NAME,
            description=(
                "Delegates a task to a local LLM running via Ollama. "
                "The local model can list directories and read files autonomously, "
                "then return a single summarised answer. Use this to reduce token usage "
                "on repetitive filesystem exploration tasks."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "prompt": {
                        "type": "string",
                        "description": "What the local model should do",
                    },
                    "allowed_dirs": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Absolute directory paths the local model may access",
                    },
                },
                "required": ["prompt", "allowed_dirs"],
            },
        )
    ]


@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:
    if name != CLAUDE_CODE_TOOL_NAME:
        return [types.TextContent(type="text", text=f"Unknown tool: {name}")]

    prompt: str = arguments["prompt"]
    allowed_dirs: list[str] = arguments["allowed_dirs"]

    result = await run_agent(prompt, allowed_dirs)
    return [types.TextContent(type="text", text=result)]


async def main() -> None:
    async with stdio_server() as (r, w):
        await app.run(r, w, app.create_initialization_options())

if __name__ == "__main__":
    asyncio.run(main())