# P4-g: deny `Bash(curl:*)` + `;` / `|` で curl を繋ぐ → どの区切りでも個別照合で deny

## 目的

- 複合コマンドの区切りは `&&` だけではない。`;`(逐次)・`|`(パイプ)でも**各サブコマンドが
  独立に照合**され、後段の curl が deny に当たってブロックされることを確認する
- b-chained は `&&` のみを実測していた。本ケースはそれを `;` と `|` に広げ、「区切り種別に依らず
  チェーンで deny をすり抜けられない」を実証する

## 前提(設定)

```json
{
  "permissions": {
    "allow": ["Bash(*)"],
    "deny":  ["Bash(curl:*)"]
  }
}
```

- b と**同一設定**。変えるのは区切り記号(`&&` → `;` / `|`)だけの1変数対照。

## 実行内容

1. Bash で `echo hi ; curl -sS … -o CURLED.txt`(`;` 逐次区切り)
2. Bash で `echo hi | curl -sS … -o CURLED.txt`(`|` パイプ区切り)

## 期待結果

| No | 操作 | 許諾 | 結果 | 補足 |
|---|---|:---:|:---:|---|
| 1 | Bash `echo hi ; curl …`  | deny | - | `;` でも curl サブコマンドが個別照合 → deny |
| 2 | Bash `echo hi \| curl …` | deny | - | `\|` でも curl サブコマンドが個別照合 → deny |

- 2プローブとも SDK で canUseTool 非発火の DENIED_HARD。

## なぜそうなるか

- **区切りは `&&` `||` `;` `|` `|&` `&` 改行**で、いずれも**各サブコマンドを独立にマッチ**する。
  先頭の `echo` が無害でも、後段の `curl` が `Bash(curl:*)` の deny に当たれば複合全体がブロックされる。
- b(`&&`)と同じ機構が全区切りに一様に効く。**チェーンは deny の抜け穴にならない**(抜けるのは
  ラッパー/サブシェルの文字列内 → P4-c)。

## 運用時の留意事項

- 「curl を後段に置けば/別の区切りで繋げば通る」は成立しない。deny 対象コマンドは、複合のどの位置・
  どの区切りにあっても個別照合で止まる。
- 逆に言えば、deny をすり抜けたいコマンドは「サブコマンドとして見えない」形(`sh -c '…'` の文字列内、
  コマンド置換 `$(…)`)に隠す必要がある。区切りで繋ぐだけでは隠せない(→ c が唯一の抜け穴の型)。

## 試し方(本リポジトリでの実測)

### お手軽に試す(対話)

このディレクトリで `claude` を起動し、[prompt.ja.txt](./prompt.ja.txt) を貼り付けるだけ。
どちらの区切りでも curl がプロンプトなしで拒否されることが確認できる。

```bash
cd cases/P4-bash-command-matching/g-separators && claude
# → prompt.ja.txt を貼り付け
```

### ハーネスで実測する(結果の記録・プローブ独立)

allow/deny 規則で結論が決まるため**全形態で同結論**。SDK では2プローブとも DENIED_HARD。

```bash
python3 harness/run.py P4-bash-command-matching/g-separators
python3 harness/run.py -m sdk P4-bash-command-matching/g-separators
```

> プローブは他ツールへのフォールバックを禁止している(deny の観測を汚さないため)。
> curl は deny で実行に至らないので、ネットワーク到達性には依存しない。

## 検証記録

| 日付 | バージョン | 実測したモダリティ |
|---|---|---|
| 2026-07-05 | v2.1.201 | headless / sdk(2プローブとも一致。DENIED_HARD=canUseTool 非発火を確認) |

## 対応する知識

- docs/FINDINGS.md: Q3「deny/allow をコマンドチェーンですり抜けられる」
- 関連: P4-b(`&&` チェーンの deny=本ケースの基点)/ P4-c(ラッパー/サブシェルはすり抜け)/
  P4-e(剥がされるラッパーは deny)/ P4-a(直接 curl の deny)
