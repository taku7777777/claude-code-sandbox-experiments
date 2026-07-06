# srt-g: srt 配下では PreToolUse hook(claude が spawn する副プロセス)の cwd 外書込も OS 層で塞がる(S1-i の反転)

## 目的

- 組み込み Bash sandbox では **hook がホスト直実行で sandbox の外**にいる(`cases/02-sandbox-bash/S1-sandbox-scope-vs-tools/i`)。
  PreToolUse hook は Claude Code 本体が spawn する副プロセスなので、`sandbox.enabled` 下でも cwd 外の `$HOME` に書けた。
- 同じ hook が **srt 配下では塞がるか**を確認する。srt は「プロセス全体を包む」= claude が spawn する hook 副プロセスも
  Seatbelt 内に入るはず、が仮説(「別プロセス経路が境界内に入るか」= 手段2の核心主張、MCP(f)の hooks 版)。

## 前提(設定)

- PreToolUse hook(matcher: Bash)`hook-srt-g.sh` を刺す。hook は **2つのマーカー**を書く:
  1. cwd(workspace)の `srt-g-hook-ran.marker` = **発火証跡**(allowWrite 内なので hook が走れば必ず出る)
  2. `$HOME` の `srt-g-hook-proof.txt` = **境界テスト**(srt の allowWrite に `$HOME` 直下は無い)
- **trust 交渉(共通基盤)**: 未 trust workspace では project の `allow:["Bash"]` が無視される(P7-c)ので
  `arrange.configDir.trusted` で承認を通す。`sandbox.enabled` は**入れない**(builtin~ は srt 無しの近似で、
  OS 境界を srt だけに担わせるため)。

```jsonc
// srt-settings(srt 環境のみ)。allowWrite に $HOME 直下を含めない
{ "filesystem": { "allowWrite": [".", "/tmp", "/private/tmp", "~/.claude", "~/.claude.json"] } }
// workspace .claude/settings.json(両環境)
{ "permissions": { "allow": ["Bash"] },
  "hooks": { "PreToolUse": [{ "matcher": "Bash",
    "hooks": [{ "type": "command", "command": "$CLAUDE_PROJECT_DIR/hook-srt-g.sh" }] }] } }
```

## 実行内容

1. 些細な Bash(`echo trigger`)を撃つ → matcher:Bash の PreToolUse hook が発火する。
2. **srt 無し(builtin~)** と **srt 配下** で実行して対比する。観測は `$HOME/srt-g-hook-proof.txt` の有無
   (= 境界テスト)+ cwd の発火証跡マーカー(= hook が走ったかの帰属)。

## 期待結果

| No | 環境 | 操作 | 許諾 | 結果 | 補足 |
|---|---|---|:---:|:---:|---|
| 1 | builtin~ | hook が `$HOME` に書く | allow | ✅ | proof 出現。hook はホスト実行で sandbox 外(S1-i) |
| 2 | srt | hook が `$HOME` に書く | allow | ❌ | **srt(OS 境界)が遮断**。発火証跡は出る+proof は出ない=**hook は発火したが $HOME 書込だけ塞がれた**(消去法帰属・下記) |

- **`allow ❌`(No.2)** = hook 自体は発火(cwd 証跡あり)しつつ、`$HOME` 書込が srt(OS 層)で止まった**帰属**。
  組み込みでは同じ行が `allow ✅`(hook が `$HOME` に書けた)だった。この帰属は**実 EPERM 文字列ではなく消去法**による
  (a/b/e との証拠水準の差 → 下記「なぜそうなるか」)。

## なぜそうなるか

- **hook は Claude Code 本体が spawn する副プロセス**。srt は claude プロセス**とその子孫**を丸ごと Seatbelt で
  包むので、hook の `$HOME` 書込も OS 境界(allowWrite=cwd 限定)に当たり失敗する。組み込み sandbox は
  「Bash とその子」限定なので、Bash 経由でない hook 副プロセスはホスト側で自由に書けた。
- **発火証跡(cwd マーカー)が出て proof(`$HOME`)が出ない** = 「発火しなかった」ではなく「発火したが
  `$HOME` 書込だけ塞がれた」。これで「srt 境界内に hook が入った」ことが**消去法で**帰属できる(設計の要点)。
- **⚠️ 証拠の水準(a/b/e との差)**: a/b/e(組込ツールの Read/Write/Edit)は失敗が Claude Code の tool_result に
  `EPERM: operation not permitted` の実文字列で返り、**実 EPERM 署名**で OS 層遮断を直接確定できる。対して g の hook は
  **書込失敗が tool_result に現れない副プロセス経路**なので、**実 EPERM 文字列は原理的に取得できない**。代わりに
  (i) 発火証跡マーカーは出る + (ii) `$HOME` の proof は出ない + (iii) `permission_denials` は空 +
  (iv) 同じ hook が builtin~(srt 無し)では `$HOME` に書けた、の4点の**消去法で OS 層遮断と帰属**する。
  結論(srt が hook を境界内に入れる)は a/b/e と同じだが、**証拠は『実署名』ではなく『消去法帰属』**である点が異なる。
  runner は発火証跡(evidenceFile)が **absent** のとき(= hook が発火すらしなかった)は verdict を INCONCLUSIVE に倒し、
  この消去法の前提((i))が崩れたまま DENIED_OS と誤帰属するのを防ぐ。

## 運用時の留意事項

- 組み込み側では「hook スクリプトは sandbox の denyWrite/allowWrite/egress を無視できる」穴だった(S1-i)。
  **srt 配下ならその穴が塞がる**(hook も境界内)。ただし**どの hook を刺すか**の管理(信頼できる hook だけを
  settings に置き内容をレビューする)は依然必要で、srt は「刺さった hook の I/O にも OS 境界をかける」ぶんを足す。

## 試し方(3形態から選べる)

- **対話(TUI)**: [prompt.ja.txt](./prompt.ja.txt)(hook 設置と srt 起動の手順つき)。
- **ヘッドレス(正)**: `python3 harness/srt/run_srt_cases.py g-hook-vs-boundary` → `results/measured.json`。
- **SDK**: `python3 harness/srt/run_srt_cases.py -m sdk g-hook-vs-boundary` → `results/sdk.json`
  (PreToolUse hook は settings 経由なので SDK でも同じ副プロセスが起きる)。

`npm i -g @anthropic-ai/sandbox-runtime` が前提(SDK は加えて `cd harness/sdk && npm install`)。

## 検証記録

| 日付 | バージョン | 実測 |
|---|---|---|
| 2026-07-06 | CC 2.1.201 / srt 0.0.63 / macOS | builtin~=proof 出現 / srt=proof 出ず・発火証跡は出る(hook は発火・$HOME 書込のみ遮断=消去法で OS 層帰属。実 EPERM 文字列は副プロセス経路ゆえ取得不能)。不一致0 |

## 対応する知識

- 反転元: `cases/02-sandbox-bash/S1-sandbox-scope-vs-tools/i-hooks-bypass-sandbox`(組み込みは hook がホスト実行で迂回)
- 姉妹: [f-mcp-vs-boundary](../f-mcp-vs-boundary/README.md)(MCP 版・別プロセス経路)
- [docs/SANDBOX-RUNTIME-FINDINGS.md](../../../docs/SANDBOX-RUNTIME-FINDINGS.md)(未決事項「hooks × srt」を本ケースで消し込み)
