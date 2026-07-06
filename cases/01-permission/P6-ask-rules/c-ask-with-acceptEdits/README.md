# P6-c: ask 規則は acceptEdits に残る → 自動承認されず ask

## 目的

- `--permission-mode acceptEdits`(ファイル編集を自動承認するモード)と ask 規則が衝突したとき、**明示 ask 規則が勝つ**ことを確認する。
- 「acceptEdits なのに自動承認されない」= 明示 ask 規則は全モードで適用される、を示す。

## 前提(設定)

```json
{ "permissions": { "ask": ["Write(*)"] } }
```

- 実行フラグ: `--permission-mode acceptEdits`(case.json の `run.flags` に記載)。P6-a との差分は acceptEdits フラグの追加のみ(1変数差分)。
- probe=permission。ask 規則は `Write(*)` の1本のみ。

## 実行内容

1. Write でケースディレクトリ直下に `PROOF.txt` を作成

## 期待結果

| No | 操作 | 許諾 | 結果 | 補足 |
|---|---|:---:|:---:|---|
| 1 | Write `./PROOF.txt`(cwd 内) | ask | ✅ | acceptEdits の自動承認を上書き |

## なぜそうなるか

- **明示 ask 規則は全モードで適用される**。acceptEdits はモード由来の「自動承認」だが、規則の ask がそれより優先しプロンプトを強制する。
- モードは「規則がマッチしなかったツールの既定挙動」を決めるもので、**明示規則がマッチすればモードの自動承認は出番がない**。

## 運用時の留意事項

- 「編集は基本自動承認(acceptEdits)で回すが、特定の書込だけは必ず人に確認させたい」→ その操作に ask 規則を書けばモードに関係なく確認が入る。
- headless / CI では ask は auto-deny。acceptEdits で回している CI でも ask 規則対象は落ちる。

## 試し方(本リポジトリでの実測)

### お手軽に試す(対話)

このディレクトリで `claude --permission-mode acceptEdits` を起動し、[prompt.ja.txt](./prompt.ja.txt) の内容を貼り付けるだけ。
acceptEdits でも Write で承認プロンプト(ask)が出ることが確認できる(settings.json だけではモードが再現されないためフラグが要る)。

```bash
cd cases/P6-ask-rules/c-ask-with-acceptEdits && claude --permission-mode acceptEdits
# → prompt.ja.txt を貼り付け
```

### ハーネスで実測する(結果の記録・プローブ独立)

ask 系なので3形態で実測できる(仕組みは [docs/EXECUTION-MODALITIES.md](../../../../docs/EXECUTION-MODALITIES.md))。

```bash
# ヘッドレス(claude -p): ask は承認者不在で auto-deny → DENIED
python3 harness/run.py P6-ask-rules/c-ask-with-acceptEdits

# SDK(canUseTool = ask の計測器): acceptEdits でも Write の ask 発火 → ASK
python3 harness/run.py -m sdk P6-ask-rules/c-ask-with-acceptEdits

# 対話(TUI): 承認プロンプトが出て、承認すれば書込成功 → ASK
python3 harness/run.py -m interactive --step prepare P6-ask-rules/c-ask-with-acceptEdits
python3 harness/run.py -m interactive --step judge P6-ask-rules/c-ask-with-acceptEdits \
  --answer prompted=y --answer approved=y
```

- SDK の `askFired=['Write']` が「acceptEdits を重ねても engine=ask」の直接証拠。

## 検証記録

| 日付 | バージョン | 実測したモダリティ |
|---|---|---|
| 2026-07-05 | v2.1.201 / SDK 0.3.200 | headless / sdk(1プローブとも一致。headless=DENIED / sdk=ASK) |

## 対応する知識

- docs/FINDINGS.md: 明示 ask 規則は全モードで適用 / ask 規則の 3 値中間項
- 関連: P1-b(acceptEdits 単独の挙動)/ P6-a(ask 単独)/ P6-d(bypass でも ask は残る)
