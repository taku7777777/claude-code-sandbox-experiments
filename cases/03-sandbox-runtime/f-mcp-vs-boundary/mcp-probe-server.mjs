#!/usr/bin/env node
// 最小 stdio MCP サーバ(JSON-RPC 2.0, newline-delimited)。sandbox 迂回の実証用。
// 2ツール: read_path(path)=ファイル読取 / net_get(url)=外向き HTTP GET。
import fs from "node:fs";
import https from "node:https";

function send(obj) { process.stdout.write(JSON.stringify(obj) + "\n"); }

const TOOLS = [
  { name: "read_path", description: "Read a file and return its contents.",
    inputSchema: { type: "object", properties: { path: { type: "string" } }, required: ["path"] } },
  { name: "net_get", description: "HTTP GET a URL and return status.",
    inputSchema: { type: "object", properties: { url: { type: "string" } }, required: ["url"] } },
];

async function call(name, args) {
  if (name === "read_path") {
    try { return fs.readFileSync(args.path, "utf8"); }
    catch (e) { return "READ_ERROR: " + String(e.message || e); }
  }
  if (name === "net_get") {
    return await new Promise((resolve) => {
      const req = https.get(args.url, { timeout: 15000 }, (res) => {
        resolve(`NET_OK status=${res.statusCode}`);
        res.destroy();
      });
      req.on("error", (e) => resolve("NET_ERROR: " + String(e.message || e)));
      req.on("timeout", () => { req.destroy(); resolve("NET_TIMEOUT"); });
    });
  }
  return "UNKNOWN_TOOL";
}

let buf = "";
process.stdin.on("data", async (chunk) => {
  buf += chunk.toString("utf8");
  let idx;
  while ((idx = buf.indexOf("\n")) >= 0) {
    const line = buf.slice(0, idx).trim();
    buf = buf.slice(idx + 1);
    if (!line) continue;
    let msg;
    try { msg = JSON.parse(line); } catch { continue; }
    if (msg.method === "initialize") {
      send({ jsonrpc: "2.0", id: msg.id, result: {
        protocolVersion: "2024-11-05",
        capabilities: { tools: {} },
        serverInfo: { name: "sandbox-probe", version: "0.0.1" },
      }});
    } else if (msg.method === "notifications/initialized") {
      // notification, no reply
    } else if (msg.method === "tools/list") {
      send({ jsonrpc: "2.0", id: msg.id, result: { tools: TOOLS } });
    } else if (msg.method === "tools/call") {
      const text = await call(msg.params?.name, msg.params?.arguments || {});
      send({ jsonrpc: "2.0", id: msg.id, result: { content: [{ type: "text", text }] } });
    } else if (msg.id !== undefined) {
      send({ jsonrpc: "2.0", id: msg.id, error: { code: -32601, message: "method not found" } });
    }
  }
});
