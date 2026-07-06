# P8-d: `deny: ["Agent"]` で委譲そのものを封じる — 起動ツールがツールセットから除去される

## 目的

- a/b(継承で守られる)・c(モードは緩みうる)の手前にある**「そもそも委譲させない」直接の制御面**を実測する。sub-agents doc: "To prevent Claude from delegating to any subagent, deny the `Agent` tool itself."

## 前提(設定)

```json
{ "permissions": { "deny": ["Agent"] } }
```

## 実行内容

- general-purpose サブエージェントへの Write 委譲を指示する(起動できない場合は代替禁止)。

## 期待結果

| No | 操作 | 許諾 | 結果 | 補足 |
|---|---|:---:|:---:|---|
| 1 | Agent ツールで subagent 起動 → 内部で Write | deny | - | 起動ツール自体がツールセットから**除去**され委譲が試みられない。呼び出しが起きないので denials も出ず、判定は init tools の欠落(構造シグナル、P2-h と同機構) |

## なぜそうなるか

- ツール名だけの deny(パラメータなし)は**ツール除去**として効く(P2-h)。subagent 起動ツールも例外ではなく、`deny: ["Agent"]` でツール一覧から消える。
- **二重名に注意**: v2.1.63 で Task ツールは Agent に改名された(sub-agents doc)が、v2.1.201 の実測では init メッセージの tools 一覧は依然 `Task` 表記、モデルが発行する tool_use 名は `Agent`。**規則側は `Agent` / `Task(...)` どちらの表記でも効く**(エイリアス)。本ケースの case.json `tool` は init 表記に合わせ `Task` にしてある。

## 運用時の留意事項

- 委譲経路を丸ごと塞ぐ最も強い形。P8-c の frontmatter escalate も起動自体ができないので無効化される。
- 特定の subagent だけを封じるなら `Agent(name)` 形(P8-e)。組込 subagent(Explore 等)も `Agent(Explore)` で個別に無効化できる(docs)。
- 規則を書くときは `Agent` 表記を推奨(canonical)。旧 `Task` / `Task(...)` もエイリアスとして効き続ける(docs + 本グループ探索で `deny: ["Agent"]` が `Task` ツールを除去することを確認)。

## 試し方(本リポジトリでの実測)

お手軽に試す(対話): このディレクトリで `claude` を起動し、`prompt.ja.txt` を貼り付ける。

```bash
python3 harness/run.py P8-subagent-inheritance/d-deny-agent-tool
python3 harness/run.py -m sdk P8-subagent-inheritance/d-deny-agent-tool
```

- 類型B(engine=deny・形態非依存): SDK では initTools の `Task` 欠落で DENIED_HARD を構造検出。

## 検証記録

| 日付 | バージョン | 実測したモダリティ | 備考 |
|---|---|---|---|
| 2026-07-05 | v2.1.201 | headless, sdk | init tools 表記が `Task` のままである点はバージョン依存(将来 `Agent` へ変われば case.json の tool を更新) |

## 対応する知識

- 関連: P8-e(名指し deny)/ P2-h(ツール名 deny = ツール除去)
- 出典: sub-agents doc("deny the Agent tool itself" / v2.1.63 改名とエイリアス)
