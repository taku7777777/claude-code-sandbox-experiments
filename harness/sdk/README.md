# SDK 実行アダプタ（ask/deny 分離の計測器）

headless（`claude -p`）は `permission_denials[]` しか出さないため、
「deny 規則によるハード拒否」と「`ask` が承認者不在で auto-deny されただけ」を区別できない。
このアダプタは **Claude Agent SDK の `canUseTool`** を使って両者を経験的に切り分ける。

- 背景と全体像 → [../../docs/EXECUTION-MODALITIES.md](../../docs/EXECUTION-MODALITIES.md)
- ケース定義の書き方 → [../../docs/CASE-FORMAT.md](../../docs/CASE-FORMAT.md)

## 役割分担

ケースの解釈・前提整備・判定はすべて `harness/run.py`(モダリティ共通)が持つ。
`exec_case.mjs` は **「stdin で受けた1回分の実行指示を SDK で実行し、観測の生データを
stdout に JSON で返す」薄い実行器**で、単体では使わない。

```
harness/run.py -m sdk <case>
    │  stdin: {cwd, prompt, model, maxTurns, options, onAsk}
    ▼
harness/sdk/exec_case.mjs   ← query({...canUseTool})
    │  stdout: {askFired, toolUses, initTools, denials, resultText, allText, iterError}
    ▼
harness/run.py が judge → cases/<case>/results/sdk.json
```

## 判定ロジック

`canUseTool` は **engine が `ask` を返したときだけ**呼ばれる（`deny` はコールバック前にブロック、
`allow` はコールバックを経ず実行）。これを使って:

| 観測 | verdict |
|---|---|
| target ツールで `canUseTool` が発火 | `ASK` |
| 発火せず副作用が起きた | `ALLOWED`（規則/モードで事前承認） |
| 発火せず副作用も無くブロック / `initTools` に target 不在 | `DENIED_HARD`（deny 規則。ツール除去型を含む） |

交絡（Write 拒否後に Bash へフォールバックする等）を避けるため、`onAsk="deny"`(既定)は
**常に deny を返し**「ask が発火したか」だけを ground truth として記録する。OS 層 probe で
実行まで通したいケースは `case.json` の `modalities.sdk.onAsk = "allow"` を指定する。

## セットアップ

```bash
# Node 20+ が必要（SDK 0.3.x は Symbol.dispose を使うため 18 系では動かない）
cd harness/sdk
npm install        # @anthropic-ai/claude-agent-sdk を取得（node_modules は .gitignore 済み）
```

## 実行

```bash
# harness/run.py から SDK モダリティで回す(単体で exec_case.mjs は叩かない)
python3 harness/run.py -m sdk                              # 全ケース
python3 harness/run.py -m sdk P1-permission-mode           # グループ
python3 harness/run.py -m sdk P2-allow-deny-precedence/a-allow   # サブケース
```

- 各ケースディレクトリに `results/sdk.json` を書き出す(`harness/run.py -m headless` は
  これを join して headless の `DENIED` を `engine_decision: ASK/DENY` に内訳表示する)。
- 全体サマリは `results/summary-sdk.json`。
- モデルは `LAB_MODEL` 環境変数で上書き可（既定 `claude-haiku-4-5-20251001`）。

## flags と SDK options の変換

CLI フラグ(`case.json` の `run.flags`)は `harness/run.py` の `_FLAG_TO_OPTION` が
SDK options へ機械変換する(値は 1:1)。`bypassPermissions` を使うケースは SDK 固有の
`allowDangerouslySkipPermissions: true` が必須なので、ハーネスが自動付与する。
未対応フラグを含むケースを SDK で回すと、変換表への追加を促すエラーで停止する。

## OS 層 probe との棲み分け

network / credentials など OS 層(seatbelt)の観測は `canUseTool`(permission 層)では
測れない。SDK モダリティは **permission 判定の ask/deny 分離**に限定し、OS 層観測は
headless プローブ(`-m headless`)に任せる。

## 単発の modality プローブ(補助スクリプト)

- `verify_w1_modality.mjs` — `deny Write(assets/**)` が hard-deny か ask かを切り分ける単発
  スクリプト（中立 /tmp に settings を注入して `canUseTool` の発火を観測）。実測: **dir スコープ
  deny は ASK**（`Write(*)` の hard-deny と対照）。→ `node verify_w1_modality.mjs`
- `verify_webfetch_bypass.mjs` / `probe_ask_behavior.mjs` — それぞれ WebFetch の egress 迂回 /
  チェーン行の ask 挙動を確認する単発プローブ。
