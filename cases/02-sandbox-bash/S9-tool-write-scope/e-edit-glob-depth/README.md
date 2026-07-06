# S9-e: `deny Edit(assets/*)`(単一星)は深度1も深度2も止める — 子ディレクトリごとマッチする**サブツリー保護**(深度の抜け穴なし)

## 目的

- dir 保護の効く形 `Edit(dir/...)` の **glob 深度**を確定する: docs の字面(`*`=1セグメント内 / `**`=ディレクトリ横断)どおりなら `Edit(assets/*)` は深いネスト(`assets/x/y.txt`)を素通りさせるはず。実際はどうか。
- [a3](../a3-edit-only/README.md) の `Edit(assets/**)`(横断形)側にも深度2プローブを併設し、**単一星と二重星のサブツリー効果を対で完成**させる。

## 前提(設定)

```json
{ "permissions": { "deny": ["Edit(assets/*)"] } }
```

- a3 から動かした変数は glob 形だけ(`assets/**` → `assets/*`)。`--permission-mode acceptEdits` で起動。

## 実行内容

1. Write で `assets/data.txt` を作成(深度1=単一星の字面どおりの対象)
2. Write で `assets/x/y.txt` を作成(深度2=字面上は `*` の範囲外)

## 期待結果

| No | 操作 | 許諾 | 結果 | 補足 |
|---|---|:---:|:---:|---|
| 1 | Write `assets/data.txt`(深度1) | deny | - | 単一星の直撃対象(ハード deny) |
| 2 | Write `assets/x/y.txt`(深度2) | deny | - | **字面予想に反しブロック**: `assets/*` が子ディレクトリ `assets/x` にマッチ → その中のファイルは「denied な directory の中」として拒否 |

- エラーメッセージが機構を語る: `File is in a directory that is denied by your permission settings`(ファイル自体のパターン不一致でも、**祖先ディレクトリがマッチすれば拒否**)。

## なぜそうなるか

- **一次 docs(permissions、2026-07-05 確認)**: パターンは gitignore 準拠で「`*` は1パスセグメント内 / `**` はディレクトリ横断」。ファイルパス `assets/x/y.txt` 単体には `assets/*` は不一致のはず。
- しかし実測はブロック。**マッチはファイルパスだけでなくディレクトリにも効く**: `assets/*` は子ディレクトリ `assets/x` にマッチし、拒否ディレクトリ配下のファイルはすべて拒否される(gitignore で `dir/*` が配下全体を無視するのと同じサブツリー意味論)。
- 帰結: **Edit deny の dir 保護において `dir/*` と `dir/**` はサブツリー効果が等価**(`**` 側の深度2は a3 の `write-nested-depth2` プローブで実測)。深度ベースの迂回はできない。
- なお「効く形の中の話」である点に注意: Write 規則側はそもそも glob 形を問わず no-op(a2 / P3)。深度を論じる意味があるのは Edit 規則だけ。

## 運用時の留意事項

- `Edit(<dir>/*)` と書いてしまっても実効は `Edit(<dir>/**)` と同じサブツリー保護になる(**緩い方向の事故ではない**)。とはいえ意図を明示するには `**` 形で書くのが読み手に親切。
- 逆に「dir 直下だけ deny して深部は許す」という**部分開放は glob 深度では表現できない**(単一星でもサブツリー全体が締まる)。その要件は allow/deny の組合せ設計を見直す。

## 試し方(本リポジトリでの実測)

### お手軽に試す(対話)

このディレクトリで acceptEdits で `claude` を起動し、[prompt.ja.txt](./prompt.ja.txt) を貼り付ける。深度1・深度2 の両方がブロックされることが確認できる。

```bash
cd cases/S9-tool-write-scope/e-edit-glob-depth && claude --permission-mode acceptEdits
# → prompt.ja.txt を貼り付け
```

### ハーネスで実測する(結果の記録・プローブ独立)

> 両プローブともハード deny のため headless は構造的 INCONCLUSIVE(a3 と同型)。機構は -m sdk の DENIED_HARD で確定。

```bash
python3 harness/run.py S9-tool-write-scope/e-edit-glob-depth           # headless: INCONCLUSIVE(構造的)
python3 harness/run.py -m sdk S9-tool-write-scope/e-edit-glob-depth    # sdk: 両プローブ DENIED_HARD
```

## 検証記録

| 日付 | バージョン | 実測したモダリティ | 補足 |
|---|---|---|---|
| 2026-07-05〜06 | v2.1.201 | headless + sdk(2プローブ×2、全一致) | 中立 scratch(t1/t2)で深度1・深度2ともブロックを事前確認してからケース化。`**` 側の深度2は a3 `write-nested-depth2` で同時実測(DENIED_HARD) |

## 対応する知識

- グループ [S9 README](../README.md)
- 関連: [a3](../a3-edit-only/README.md)(`Edit(assets/**)`+深度2プローブ)/ [a2](../a2-write-only/README.md)(Write 規則は glob 以前に no-op)/ P3(Write deny の glob 非対称)/ S2-e・S3-k(sandbox パス側の glob はリテラル=対照的にマッチしない)
- 一次 docs: permissions(gitignore 準拠パターン・`*`=1セグメント/`**`=横断)— 字面と実測の差(ディレクトリマッチによるサブツリー効果)は本ケースの実測が根拠
- 出典ギャップ: S9 GAPS G6
