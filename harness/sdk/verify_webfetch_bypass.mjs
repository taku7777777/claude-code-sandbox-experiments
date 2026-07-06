#!/usr/bin/env node
/**
 * WebFetch が sandbox network を迂回するかを、SDK の tool_result を直接検査して確定する。
 * headless だと「実際に fetch した」か「記憶から答えた」かを区別できない(モデルが言い換える)ため、
 * assistant の tool_use(WebFetch)と、その user tool_result(実内容 or ネットワークエラー)を観測する。
 *
 * 設定: sandbox allowedDomains:[]（Bash egress 全ブロック、cf S6-a=DENIED）+ allow WebFetch(domain:example.com)
 *   -> WebFetch が実内容を返せば「sandbox network を迂回」= 確定。
 */
import { query } from "@anthropic-ai/claude-agent-sdk";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";

const dir = fs.mkdtempSync(path.join(os.tmpdir(), "wf-"));
fs.mkdirSync(path.join(dir, ".claude"), { recursive: true });
fs.writeFileSync(path.join(dir, ".claude", "settings.json"), JSON.stringify({
  sandbox: { enabled: true, network: { allowedDomains: [] } },
  permissions: { allow: ["WebFetch(domain:example.com)"] },
}));

let webfetchCalled = false, resultText = "", toolResult = "";
try {
  const q = query({
    prompt: "Use the WebFetch tool to fetch https://example.com and briefly summarize what the page says.",
    options: {
      cwd: dir, model: process.env.LAB_MODEL || "claude-haiku-4-5-20251001",
      maxTurns: 3, settingSources: ["project"], permissionMode: "default",
      canUseTool: async (t, input) => ({ behavior: "allow", updatedInput: input }), // approve the ask
    },
  });
  for await (const m of q) {
    if (m.type === "assistant") for (const b of m.message.content) if (b.type === "tool_use" && b.name === "WebFetch") webfetchCalled = true;
    if (m.type === "user") for (const b of (m.message.content ?? [])) if (b.type === "tool_result") toolResult += JSON.stringify(b.content) + "\n";
    if (m.type === "result") resultText = m.result ?? "";
  }
} finally {
  fs.rmSync(dir, { recursive: true, force: true });
}

// reached = tool_result に実ページ内容がある / blocked = 実ネットワークエラー語のみ
const reached = /example domain|illustrative|for use in doc|educational materials/i.test(toolResult);
const blocked = /failed to fetch|could not fetch|unable to reach|ECONN|ETIMEDOUT|EPERM|not permitted|connection refused|network is unreachable|sandbox.{0,20}block/i.test(toolResult);
console.log("WebFetch tool called:", webfetchCalled);
console.log("tool_result excerpt:", toolResult.slice(0, 200).replace(/\s+/g, " "));
console.log("VERDICT:", webfetchCalled && reached && !blocked
  ? "ALLOWED — WebFetch reached example.com despite sandbox allowedDomains:[] (bypasses sandbox network)"
  : (blocked ? "DENIED — WebFetch was network-blocked" : "INCONCLUSIVE — inspect tool_result above"));
