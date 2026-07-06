#!/usr/bin/env node
/**
 * ask 挙動の SDK 観測（S4-b / W2）。
 * canUseTool は engine が ASK を返したときだけ発火する。sandbox auto-allow 下で
 * Bash コマンドが「無プロンプト(auto-allow)」か「ask に落ちる」かを直接測る。
 *
 *  S4-b: `allow:[]` vs `allow:[Bash(echo:*)]` で ask が増えるか（multi-repo の主張）
 *  W2  : excludedCommands + exact-allow のチェーン `./s.sh && touch X` が ask に落ちるか
 *
 * 中立な一時ディレクトリで実行（case dir の repo 名によるモデル拒否を避ける）。
 */
import { query } from "@anthropic-ai/claude-agent-sdk";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";

async function probe({ label, settings, prompt, files }) {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "ask-"));
  fs.mkdirSync(path.join(dir, ".claude"), { recursive: true });
  fs.writeFileSync(path.join(dir, ".claude", "settings.json"), JSON.stringify(settings));
  for (const [name, content] of Object.entries(files || {})) {
    fs.writeFileSync(path.join(dir, name), content, { mode: name.endsWith(".sh") ? 0o755 : 0o644 });
  }
  const asked = [];
  try {
    const q = query({
      prompt,
      options: {
        cwd: dir, model: process.env.LAB_MODEL || "claude-haiku-4-5-20251001",
        maxTurns: 3, settingSources: ["project"],
        canUseTool: async (t) => { asked.push(t); return { behavior: "deny", message: "probe" }; },
      },
    });
    for await (const _ of q) { /* drain */ }
  } catch (e) {
    console.log(`  ${label}: ERROR ${e?.message ?? e}`);
    fs.rmSync(dir, { recursive: true, force: true });
    return;
  }
  const bashAsked = asked.filter((t) => t === "Bash").length;
  console.log(`  ${label}: canUseTool fired = [${asked}]  => Bash ${bashAsked ? "ASK" : "auto-allowed (no ask)"}`);
  fs.rmSync(dir, { recursive: true, force: true });
}

const SB = { enabled: true };
const CMD_SIMPLE = "Run exactly this one bash command using the Bash tool: echo hi > out.txt — just run it.";
const CMD_GLOB = "Run exactly this one bash command using the Bash tool: for f in *.txt; do wc -l \"$f\"; done — just run it.";
const CMD_CHAIN = "Run exactly this one bash command using the Bash tool: ./s.sh && touch PWNED — just run it.";

console.log("S4-b: individual allow vs empty allow (sandbox auto-allow):");
await probe({ label: "empty-allow  / echo>out ", settings: { sandbox: SB, permissions: { allow: [] } }, prompt: CMD_SIMPLE });
await probe({ label: "indiv-allow  / echo>out ", settings: { sandbox: SB, permissions: { allow: ["Bash(echo:*)"] } }, prompt: CMD_SIMPLE });
await probe({ label: "empty-allow  / glob→file", settings: { sandbox: SB, permissions: { allow: [] } }, prompt: CMD_GLOB, files: { "a.txt": "x\n" } });
await probe({ label: "indiv-allow  / glob→file", settings: { sandbox: SB, permissions: { allow: ["Bash(echo:*)"] } }, prompt: CMD_GLOB, files: { "a.txt": "x\n" } });

console.log("\nW2: excludedCommands + exact-allow, chained with an arbitrary command:");
await probe({
  label: "excluded+exact / s.sh && touch",
  settings: { sandbox: SB, excludedCommands: ["./s.sh"], permissions: { allow: ["Bash(./s.sh)"] } },
  prompt: CMD_CHAIN, files: { "s.sh": "#!/bin/sh\necho ran\n" },
});
