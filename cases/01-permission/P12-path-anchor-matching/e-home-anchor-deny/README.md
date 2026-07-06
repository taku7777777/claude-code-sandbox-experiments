# P12-e: `~/` home アンカー `Edit(~/dir/sub/**)` の deny は cwd 外ファイルを守る(効く形)

## 目的

- 絶対アンカーのもう一つの**効く形** `~/`(home 起点)を実測する。cwd の外にある死守パスを守る典型形。

## 前提(設定)

```json
{
  "permissions": {
    "deny": ["Edit(~/lab-p12/sub/**)"],
    "additionalDirectories": ["$HOME/lab-p12"]
  }
}
```

- 対象 `~/lab-p12/sub/` は cwd の外。編集可能にするため `additionalDirectories` に登録(未 trust だと
  無視されるため configDir.trusted=true で trust を付与=P7-c)。その上で `~/` アンカー deny を張る。
- モード: `acceptEdits`(additionalDirectories 内は自動承認されるので、deny が唯一の遮断要因)。

## 実行内容

1. Read で `$HOME/lab-p12/sub/note.txt` を読み、Edit で `hello`→`EDIT_APPLIED`

## 期待結果

| No | 操作 | 許諾 | 結果 | 補足 |
|---|---|:---:|:---:|---|
| 1 | Edit(home 配下・絶対) | deny | - | `~/` アンカーがマッチ・編集不成立(SDK=DENIED_HARD / headless=INCONCLUSIVE) |

## なぜそうなるか

- **`~/<path>` は home 起点の絶対アンカーとして認識される**(S9-d2 の additionalDirectories 修正形と同じ機構)。
  cwd の外でも、`~/` で正しくアンカーすれば絶対パス呼び出しをブロックできる。

## 運用時の留意事項

- **マルチルート/ home 配下の死守パスは `~/` アンカーで書く**。cwd 起点の相対規則は別ルートにマッチしない
  (S9-d の無言 no-op)。ルートごとに `~/`(または `//`)でアンカーした deny を併記する。
- additionalDirectories は未 trust だと丸ごと無視される(P7-c)。CI では trust の焼き込みが前提。

## 試し方(本リポジトリでの実測)

### お手軽に試す(対話)

このディレクトリで **acceptEdits で**(trust 済みの前提) claude を起動し [prompt.ja.txt](./prompt.ja.txt) を貼り付ける。

### ハーネスで実測する

```bash
python3 harness/run.py P12-path-anchor-matching/e-home-anchor-deny
python3 harness/run.py -m sdk P12-path-anchor-matching/e-home-anchor-deny
```
## 検証記録

| 日付 | バージョン | プラットフォーム | 実測したモダリティ |
|---|---|---|---|
| 2026-07-06 | v2.1.201 | macOS(darwin) | scratch → headless / sdk(DENIED_HARD / headless INCONCLUSIVE(by-design)) |

## 対応する知識

- グループ [P12 README](../README.md) / d(`//` アンカー)/ S9-d/d2(additionalDirectories の別ルート・アンカー修正)/ P7-c(trust ゲート)

