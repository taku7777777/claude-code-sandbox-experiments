# P2-h: `deny: ["*"]` → 全ツールがツールセットから除去される(除去型 deny の最大形)

## 目的

- deny/ask がツール名ワイルドカード(`"*"`)を受け付け、**bare glob deny がコンテキスト除去**として
  働くことを、全ツール一括の最大形で実測する

## 前提(設定)

```json
{
  "permissions": {
    "deny": ["*"]
  }
}
```

## 実行内容

1. Write ツールで PROOF.txt の作成を指示(どのツールも使えないはずの環境で)

## 期待結果

| No | 操作 | 許諾 | 結果 | 補足 |
|---|---|:---:|:---:|---|
| 1 | Write `./PROOF.txt` | deny | - | **全ツールが除去され、呼び出し自体が起きない** |

## なぜそうなるか

- bare / glob 形の deny はマッチしたツールを**モデルのコンテキストから除去する**(P2-b の `Write(*)` と同機構)。
  `"*"` は全ツール名にマッチするので、ツールセットが空になる。
- 呼び出しが起きないため `permission_denials` は**空**。ハーネスは init メッセージの
  ツール一覧から target(Write)が欠けていることを構造的シグナルとして DENIED 判定する
  (SDK では `initTools` が空 = DENIED_HARD)。
- 実測での副観測: ツールを失ったモデルは**ツール呼び出し風の疑似テキスト**
  (`<function_calls>…` 形式の平文)を出力することがある。もちろん何も実行されない
  (副作用ゼロを確認済み)が、出力を機械処理する側は「ツールを使ったように見える平文」に注意。

## 運用時の留意事項

- 実用形は `deny: ["mcp__*"]`(MCP ツール全遮断のキルスイッチ)。本ケースはその機構実証の軽量版で、
  **MCP サーバ fixture を使った `mcp__*` の実測は未着手ギャップ**(→ GAPS.md G5)。
- allow 側は同じ書き方ができない(`mcp__<server>__` リテラルプレフィックス後のみ glob 可、docs)。
  deny/ask と allow の**構文非対称**に注意。

## 試し方(本リポジトリでの実測)

```bash
python3 harness/run.py P2-allow-deny-precedence/h-wildcard-deny-all
python3 harness/run.py -m sdk P2-allow-deny-precedence/h-wildcard-deny-all
```

## 検証記録

| 日付 | バージョン | 実測したモダリティ |
|---|---|---|
| 2026-07-05 | v2.1.201 | headless(一致・init tools 欠落で構造検出)/ sdk |

## 対応する知識

- グループ [P2 README](../README.md)
- 関連: P2-b(除去型 deny の単体形)/ P4-a・P2-f(呼び出し時 block 型との対照)
