# S2-h: permission の Edit allow 規則は sandbox 書込境界に**マージされる** — `Edit(~/dir/**)` だけで cwd 外に書ける

## 目的

- docs 明記(未実測だった)の **「sandbox.filesystem と permission 規則のパスは最終 sandbox 設定にマージされる」**を実測する。
- S2 の中心メッセージ「書込境界 = cwd + $TMPDIR + allowWrite」が**不完全**で、実際は
  **∪ permission の Edit/Write 系 allow 規則のパス**まで含むことを確定する。

## 前提(設定)

```json
{
  "sandbox": { "enabled": true },
  "permissions": { "allow": ["Edit(~/lab-permrule/**)"] }
}
```

- `sandbox.filesystem.allowWrite` は**空**。書込境界を広げうる設定は permission 側の Edit 規則だけ。

## 実行内容

1. Bash で `~/lab-permrule/probe.txt`(Edit 規則の対象パス)に書込
2. Bash で `~/lab-permrule-ctrl/probe.txt`(規則の無い隣接ディレクトリ)に書込

## 期待結果

| No | 操作 | 許諾 | 結果 | 補足 |
|---|---|:---:|:---:|---|
| 1 | Bash `echo > ~/lab-permrule/probe.txt` | allow | ✅ | **Edit 規則が OS 書込境界を開けた**(allowWrite なしで cwd 外に書けた) |
| 2 | Bash `echo > ~/lab-permrule-ctrl/probe.txt` | allow | ❌ | 規則の無い隣は通常どおり EPERM = 開けたのは規則そのもの |

## なぜそうなるか

- docs(sandboxing): "Paths from both sandbox.filesystem settings and permission rules are **merged
  together** into the final sandbox configuration" — Edit 系 allow 規則は `allowWrite` 相当として、
  Read/Edit deny 規則は deny 側として合流する(対応表あり)。
- つまり**実効の書込境界は「cwd + 付替え $TMPDIR + allowWrite ∪ Edit/Write 系 allow 規則のパス」**。
  プローブ 1(規則あり=✅)と 2(規則なし=❌)の対比が、境界を広げた原因を Edit 規則に確定させる。
- 補足: permission 層のパスマッチでは `~` 形の Write 規則が no-op だった(P3-d)が、**sandbox 境界への
  マージでは `Edit(~/dir/**)` 形が効く**。マッチング体系が層で異なる点に注意。

## 運用時の留意事項

- **`allowWrite` を絞っても permission 規則で穴が開く**。sandbox の書込境界を監査するときは
  `sandbox.filesystem` だけでなく `permissions.allow` の Edit/Write 系規則も見ること。
- **このマージは規則を置いたスコープを問わない**(→ S2-n で local を実測)。project の settings.json で
  絞っていても、開発者が `settings.local.json` に置いた allow 規則 — 承認ダイアログの
  「don't ask again」が書くのも settings.local.json — が同じように OS 層の境界を広げる。
  レビューを通らないファイルが境界を動かせる、という点が運用上の要注意ポイント。
- 逆に「Edit を許可したのに sandbox が止める」系のトラブルは起きにくい(規則が境界に合流するため)。
  意図的に OS 層で締めたい場合は denyWrite を書く(deny は常勝 → S2-i。**permission 規則由来の
  allow に対しても・local スコープからの allow に対しても勝つ** → S2-n)。

## 試し方(本リポジトリでの実測)

### お手軽に試す(対話)

このディレクトリで `claude` を起動し、[prompt.ja.txt](./prompt.ja.txt) を貼り付けるだけ。どちらも cwd 外なのに 1 だけ書けるのが見える。

```bash
cd cases/S2-sandbox-fs-write/h-permrule-merges-into-sandbox && claude
```

### ハーネスで実測する

```bash
python3 harness/run.py S2-sandbox-fs-write/h-permrule-merges-into-sandbox
python3 harness/run.py -m sdk S2-sandbox-fs-write/h-permrule-merges-into-sandbox
```

## 検証記録

| 日付 | バージョン | 実測したモダリティ |
|---|---|---|
| 2026-07-05 | v2.1.201 / SDK 0.3.200 | headless / sdk(2プローブとも一致) |

## 対応する知識

- docs/FINDINGS.md: Q2 / グループ [S2 README](../README.md) / S2 GAPS G3 の解消
- 一次 docs: sandboxing(permission 規則と sandbox 境界のマージ・対応表)
- 関連: S2-n(**local スコープの規則でも同じ穴が開く**+denyWrite での釘付け)/ S2-b(allowWrite での穴あけ)/ P3-d,e(permission 層のパスマッチ体系は別物)/ S3(read 側の deny 規則合流は未実測)
