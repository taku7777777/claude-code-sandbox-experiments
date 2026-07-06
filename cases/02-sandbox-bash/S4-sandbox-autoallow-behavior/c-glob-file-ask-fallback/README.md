# S4-c: sandbox auto-allow 下でも glob→変数→ファイルの形は ASK に落ちる(ask はコマンド形状が決める)

## 目的

- sandbox の自動許可下でも、**コマンド形状**によっては承認要求(ask)に落ちることを実測する(baseline = 個別 allow なし)。
- 単純コマンド(auto-allow)と glob→変数→ファイルアクセス(ask)を並べ、ask を決めるのが allow 構成ではなく形状であることを示す(b との対比の否定側基準)。

## 前提(設定)

```json
{ "sandbox": { "enabled": true }, "permissions": { "allow": [] } }
```

- sandbox on + 個別 allow なし(baseline)。b はここに `Bash(echo:*)` を1つ足した列。

## 実行内容

1. Bash で単純コマンド(`echo hi > out.txt`)
2. Bash で glob→変数→ファイルアクセス(`for f in *.txt; do wc -l "$f"; done`)

## 期待結果

| No | 操作 | 許諾 | 結果 | 補足 |
|---|---|:---:|:---:|---|
| 1 | Bash `echo hi > out.txt`(単純) | allow | ✅ | sandbox auto-allow(canUseTool 発火せず) |
| 2 | Bash `for f in *.txt; do wc -l "$f"; done` | ask | ✅ | glob→変数→ファイルの形は自動許可されず承認フローへ |

- 同じ sandbox・同じ auto-allow でも、1は通り 2は ask。**差はコマンド形状だけ。**

## なぜそうなるか

- **sandbox auto-allow は静的に安全と判定できる Bash を無プロンプトで通すが、glob→ループ変数→ファイルアクセスのように解析しづらい形は通常の permission フローに落として ask にする。** headless の応答は制限パターン(`simple_expansion`)に言及し、SDK では `canUseTool` が Bash に発火(askFired=[Bash])。
- つまり ask を左右するのは allow 構成ではなく**コマンド形状**。b(個別 allow あり)でも同じ2結果になる。

## 運用時の留意事項

- 「sandbox 自動許可だから全 Bash が無プロンプト」ではない。動的なシェル構文は ask に落ちうる(headless/CI では auto-deny で止まる)。
- スクリプトを CI で確実に自動実行したいなら、形状を単純化するか、必要なコマンドを allow で明示する(ただし ask 頻度は形状依存で、個別 allow を足しても減らない → b)。

## 試し方(本リポジトリでの実測)

### お手軽に試す(対話)

このディレクトリで `claude` を起動し、[prompt.ja.txt](./prompt.ja.txt) を貼り付けるだけ。1 は無言実行、2 で承認プロンプトが出るのが見える。

```bash
cd cases/S4-sandbox-autoallow-behavior/c-glob-file-ask-fallback && claude
```

### ハーネスで実測する(結果の記録・プローブ独立)

プローブ2が ask 系なので3形態で解決が変わる:

```bash
python3 harness/run.py S4-sandbox-autoallow-behavior/c-glob-file-ask-fallback           # headless: 2 は auto-deny
python3 harness/run.py -m sdk S4-sandbox-autoallow-behavior/c-glob-file-ask-fallback     # SDK: 2 は ASK
```

## 検証記録

| 日付 | バージョン | 実測したモダリティ |
|---|---|---|
| 2026-07-05 | v2.1.201 | headless / sdk(2プローブとも一致) |

## 対応する知識

- グループ [S4 README](../README.md)
- 関連: S4-b(個別 allow を足しても同結果=ask 非増加)/ S4-a(単純 cwd 書込は auto-allow)
