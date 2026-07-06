# P12-d: 二重スラッシュ絶対 `Edit(//abs/sub/**)` の deny は効く(c と 1 スラッシュ差)

## 目的

- 絶対アンカーの**効く形**が二重スラッシュ `//` であることを実測する(c=単一スラッシュ no-op との対照)。

## 前提(設定)

```json
{ "permissions": { "deny": ["Edit(/$CASE_DIR/sub/**)"] } }
```

- `/$CASE_DIR` は二重スラッシュ絶対(`//Users/.../sub/**`)に展開される。
- モード: `acceptEdits`。

## 実行内容

1. Read で `$CASE_DIR/sub/note.txt` を読み、Edit で `hello`→`EDIT_APPLIED`

## 期待結果

| No | 操作 | 許諾 | 結果 | 補足 |
|---|---|:---:|:---:|---|
| 1 | Edit(絶対パス) | deny | - | `//` アンカーがマッチ・編集不成立(SDK=DENIED_HARD / headless=INCONCLUSIVE) |

## なぜそうなるか

- **絶対アンカーとして認識されるのは `//<abs path>` の二重スラッシュ形**(FINDINGS の `Write(//<abs>/**)` 記述と整合)。
  c との差はスラッシュ 1 つだけで、挙動は「守れる/素通り」と真逆になる。

## 運用時の留意事項

- 絶対で書くなら `//` を徹底する。とはいえ相対(a)や `~/`(e)の方が読みやすく間違えにくいので、
  **`//` を選ぶ必然が無ければ相対か `~/` を推奨**。

## 試し方(本リポジトリでの実測)

### お手軽に試す(対話)

このディレクトリで **acceptEdits で** claude を起動し [prompt.ja.txt](./prompt.ja.txt) を貼り付ける。

### ハーネスで実測する

```bash
python3 harness/run.py P12-path-anchor-matching/d-doubleslash-abs-deny
python3 harness/run.py -m sdk P12-path-anchor-matching/d-doubleslash-abs-deny
```
## 検証記録

| 日付 | バージョン | プラットフォーム | 実測したモダリティ |
|---|---|---|---|
| 2026-07-06 | v2.1.201 | macOS(darwin) | scratch → headless / sdk(DENIED_HARD / headless INCONCLUSIVE(by-design)) |

## 対応する知識

- グループ [P12 README](../README.md) / c(単一スラッシュ=no-op)/ e(home アンカー=効く)

