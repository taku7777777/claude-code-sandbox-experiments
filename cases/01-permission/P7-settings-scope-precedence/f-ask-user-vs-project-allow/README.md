# P7-f: user スコープの `ask Write(*)` は project スコープの `allow Write(*)` に勝つ（ask もスコープ横断）

## 目的

- **評価順 deny → ask → allow はスコープをまたいでも成立する**ことを、ask を主役にして確認する。
- P6-b（同一 project スコープ内で ask > allow）のスコープ横断版。deny がスコープ横断で勝つ（P7-a）のと同じく、ask も「どのスコープにあっても allow より先に評価される」かを実測する。

## 前提(設定)

project スコープ(このディレクトリの `.claude/settings.json`):

```json
{ "permissions": { "allow": ["Write(*)"] } }
```

user スコープ(`~/.claude/settings.json` 相当。ハーネスが分離 config dir に配置):

```json
{ "permissions": { "ask": ["Write(*)"] } }
```

- P7-a の deny を **ask** に置き換えた配置（allow を project、ask を user）。
- user スコープは `arrange.configDir`（分離 `CLAUDE_CONFIG_DIR`）で配置し trust 付与。SDK は `settingSources: ["user","project"]` を明示（明示しないと user の ask を読まず allow のまま素通り＝ P7-a と同根の交絡）。

## 実行内容

1. Write でケースディレクトリ直下に `PROOF.txt` を作成(project=allow / user=ask の衝突)

## 期待結果(実測一致)

| No | 操作 | 許諾 | 結果 | 補足 |
|---|---|:---:|:---:|---|
| 1 | Write `./PROOF.txt`(project=allow, user=ask) | ask | ✅ | user の ask が project の allow に勝ち承認プロンプト。承認すれば書ける |

- `ask ✅` = 承認すれば完遂。SDK では `canUseTool` が `Write` で発火し（askFired=['Write']）、onAsk=allow で承認して `PROOF.txt` が出来た＝ask が実際にゲートしている実証。headless では承認者不在で auto-deny（❌ に見えるが deny ではない）。

## なぜそうなるか

- **ask 規則もスコープに依らず allow より先に評価される**。評価順 deny → ask → allow は、スコープ横断でマージされた規則集合の上で効く。deny がスコープを飛び越えて勝つ（P7-a）のと同じ機構が、3 値の中間項 ask にも適用される。
- P6-b（同一スコープ内 ask > allow）と本ケース（スコープ横断 ask > allow）を合わせ、「ask > allow はスコープに依らない」を確定。deny 側の P2-b（同一スコープ）× P7-a（横断）と対称の構図。

## 運用時の留意事項

- **user スコープに ask を置くと、project の allow を上書きして全プロジェクトで確認プロンプトを強制できる**（個人の安全ガード）。逆に「project で allow したのに毎回確認される」ときは user/managed の ask を疑う。
- ask は「素通りしない」が「承認機会がある」——ただし **dontAsk モードでは ask が deny に化ける**（P6-e）。headless/CI では auto-deny。非対話で確実に通したいなら ask ではなく allow を、確実に止めたいなら deny を使う。

## 試し方(本リポジトリでの実測)

### お手軽に試す(対話)

⚠️ 実環境の `~/.claude/settings.json` を直接書き換えないこと。prepare が分離 config dir を提示する。ask 系なので**対話で承認プロンプトが出る**のが見どころ。

```bash
python3 harness/run.py -m interactive --step prepare P7-settings-scope-precedence/f-ask-user-vs-project-allow
# → 提示された export CLAUDE_CONFIG_DIR=... の下で claude を起動し prompt.ja.txt を貼り付け
python3 harness/run.py -m interactive --step judge P7-settings-scope-precedence/f-ask-user-vs-project-allow
```

### ハーネスで実測する(結果の記録・プローブ独立)

ask 系なので **3 形態で ask の解決が変わる**（headless=auto-deny / SDK=canUseTool 発火 / 対話=承認プロンプト）:

```bash
python3 harness/run.py P7-settings-scope-precedence/f-ask-user-vs-project-allow            # headless: auto-deny
python3 harness/run.py -m sdk P7-settings-scope-precedence/f-ask-user-vs-project-allow     # sdk: ASK（askFired=Write）
```

> headless 単独では ask と deny を区別できない（両方 DENIED）。engine=ask の確定には SDK の `canUseTool` 発火が要る（→ docs/EXECUTION-MODALITIES.md）。SDK は `settingSources: ["user","project"]` の明示が前提（case.json 参照）。

## 検証記録

| 日付 | バージョン | プラットフォーム | 実測したモダリティ |
|---|---|---|---|
| 2026-07-06 | v2.1.201 | macOS(darwin) | headless(DENIED=auto-deny) / sdk(ASK・askFired=['Write']・onAsk=allow で PROOF.txt 完遂) |
| 2026-07-06 | v2.1.201 | macOS(darwin) | **対話(cmux 駆動)**: 分離 CLAUDE_CONFIG_DIR で project allow + user ask を配置し、project allow でも user ask が勝って承認プロンプトが実出現→承認で PROOF.txt 完遂(ask ✅)。3 点セット完成 |

## 対応する知識

- 関連: P6-b（同一スコープ内 ask > allow）/ P6-e（dontAsk では ask が deny に化ける）/ P7-a（deny のスコープ横断勝ち＝本ケースの deny 版）/ P2（deny→ask→allow の両端）
