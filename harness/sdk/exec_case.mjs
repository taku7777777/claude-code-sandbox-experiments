#!/usr/bin/env node
/**
 * SDK(Claude Agent SDK)実行アダプタ — harness/run.py -m sdk から呼ばれる薄い実行器。
 *
 * ケースの解釈・前提整備・判定はすべて harness/run.py 側(モダリティ共通)が行い、
 * このスクリプトは「stdin で受けた1回分の実行指示を SDK で実行し、観測の生データを
 * stdout に JSON で返す」ことだけをする。単体では使わない。
 *
 * stdin (JSON):
 *   { cwd, prompt, model, maxTurns,
 *     options: { permissionMode?, allowDangerouslySkipPermissions?, ... },  // SDK options への追記
 *     onAsk: "deny" | "allow" }
 *
 * stdout (JSON):
 *   { askFired: [...], toolUses: [...], denials: [...],
 *     resultText, allText, numTurns }
 *
 * canUseTool は【engine が ask を返したときだけ】呼ばれる。onAsk="deny"(既定)は
 * ask の発火だけを記録して deny を返し、副作用の交絡(Write 拒否後の Bash
 * フォールバック等)を避ける。OS 層 probe で実行まで通したいケースは onAsk="allow"。
 */
import { query } from "@anthropic-ai/claude-agent-sdk";

const chunks = [];
for await (const c of process.stdin) chunks.push(c);
const payload = JSON.parse(Buffer.concat(chunks).toString("utf8"));

const asked = [];    // canUseTool が発火したツール名(= engine 判定が ask だった証跡)
const toolUses = []; // モデルが試みた tool_use
const texts = [];    // 判定用の全出力テキスト(番兵/execMarker 探索対象)
const toolErrors = []; // tool_result の is_error 本文(OS 層 EPERM 等の層判定署名。srt ランナーが使う)
let initTools = null; // セッション開始時に使用可能なツール一覧(deny 規則によるツール除去の検出用)
let result;

const q = query({
  prompt: payload.prompt,
  options: {
    cwd: payload.cwd,
    model: payload.model,
    maxTurns: payload.maxTurns ?? 3,
    settingSources: ["project"], // ケースの .claude/settings.json を読む(SDK は明示オプトイン)
    ...payload.options,
    canUseTool: async (toolName, input) => {
      asked.push(toolName);
      if (payload.onAsk === "allow") {
        return { behavior: "allow", updatedInput: input };
      }
      return { behavior: "deny", message: "probe: recording ask, denying to avoid side effects" };
    },
  },
});

// SDK 0.3.x は「maxTurns 到達」等の error result をイテレータの例外として投げる。
// ask を deny し続けるプローブでは正常系でも到達しうるので、例外は観測データと
// 一緒に報告するだけにして、収集済みデータを捨てない。
let iterError = null;
try {
  for await (const msg of q) {
    if (msg.type === "system" && msg.subtype === "init") initTools = msg.tools ?? null;
    if (msg.type === "assistant") {
      for (const b of msg.message.content) {
        if (b.type === "tool_use") toolUses.push(b.name);
        if (b.type === "text") texts.push(b.text);
      }
    }
    if (msg.type === "user") {
      for (const b of msg.message?.content ?? []) {
        if (b?.type === "tool_result" && b.is_error) toolErrors.push(JSON.stringify(b.content));
      }
    }
    if (msg.type === "result") result = msg;
  }
} catch (e) {
  iterError = String(e?.message ?? e);
}

const resultText = typeof result?.result === "string" ? result.result : null;
if (resultText) texts.push(resultText);

process.stdout.write(JSON.stringify({
  askFired: asked,
  toolUses,
  initTools,
  denials: (result?.permission_denials ?? []).map((d) => d.tool_name),
  toolErrors,
  resultText,
  allText: texts.join("\n"),
  numTurns: result?.num_turns ?? null,
  iterError,
}) + "\n");
