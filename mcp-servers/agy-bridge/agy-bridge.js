import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { ListToolsRequestSchema, CallToolRequestSchema } from "@modelcontextprotocol/sdk/types.js";
import * as pty from "node-pty";

const server = new Server(
    { name: "agy-bridge", version: "1.0.0" },
    { capabilities: { tools: {} } }
);

server.setRequestHandler(ListToolsRequestSchema, async () => ({
    tools: [
        {
            name: "agy_ask",
            description: [
                "Ask Antigravity CLI (agy) to explore the codebase, answer questions, or perform analysis using Gemini.",
                "Use this tool for codebase exploration and similar.",
                "Rule of thumb: any task that is not too complex, meaning it would be handed off to a weaker subagent",
                "should be run through this tool instead to save tokens.",
            ].join(" "),
            inputSchema: {
                type: "object",
                properties: {
                    prompt: { type: "string", description: "The question or task for agy" },
                    cwd: { type: "string", description: "Working directory (defaults to current)" }
                },
                required: ["prompt"]
            }
        }
    ]
}));

function runInPty(prompt, cwd) {
    return new Promise((resolve, reject) => {
        const chunks = [];
        const term = pty.spawn("agy.exe", ["-p", prompt], {
            cwd: cwd || process.cwd(),
            cols: 220,
            rows: 50,
            useConpty: true,
        });
        term.onData(data => chunks.push(data));
        term.onExit(({ exitCode }) => {
            const raw = chunks.join("");
            // Strip ANSI/VT escape sequences and window title sequences
            const clean = raw
                .replace(/\x1b\[[0-9;?]*[a-zA-Z]/g, "")   // CSI sequences: ESC [ ... letter
                .replace(/\x1b\][^\x07]*\x07/g, "")         // OSC sequences: ESC ] ... BEL
                .replace(/\r\n/g, "\n").replace(/\r/g, "\n")
                .trim();
            if (exitCode !== 0) reject(new Error(`agy exited with code ${exitCode}\n${clean}`));
            else resolve(clean);
        });
        setTimeout(() => { term.kill(); reject(new Error("agy timed out")); }, 120000);
    });
}

server.setRequestHandler(CallToolRequestSchema, async (req) => {
    const { prompt, cwd } = req.params.arguments;
    const output = await runInPty(prompt, cwd);
    return { content: [{ type: "text", text: output }] };
});

const transport = new StdioServerTransport();
await server.connect(transport);