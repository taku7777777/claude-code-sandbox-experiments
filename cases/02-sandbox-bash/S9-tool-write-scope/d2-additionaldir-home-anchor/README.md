# S9-d2: 修正形 — `~/` アンカー付き `deny Edit(~/s9d-extra/scripts/**)` は additionalDirectories 実体を**ハードに守る**(残りは自動承認のまま)

## 目的

- [d](../d-additionaldir-scope/README.md) で確定した「cwd 相対 deny は additional dir にマッチしない」の**修正形**を実測する: ルート実体をアンカーで名指しすれば効くのか。
- deny の効き目が「そのルート全体」ではなく「名指しした scripts/ サブツリーだけ」であること(スコープの正確さ)も対照プローブで確認する。

## 前提(設定)

d から動かした変数は **deny 規則のアンカーだけ**(additionalDirectories は同一):

```json
{
  "permissions": {
    "additionalDirectories": ["$HOME/s9d-extra"],
    "deny": ["Edit(~/s9d-extra/scripts/**)"]
  }
}
```

- `--permission-mode acceptEdits` で起動。trust 前提と configDir 固定は d と同じ。

## 実行内容

1. Write で `~/s9d-extra/scripts/x.txt` を作成(アンカー付き deny の直撃対象。d の 2 と同じ操作)
2. Write で `~/s9d-extra/other/x.txt` を作成(同じ additional dir の deny 対象外=スコープ対照)

## 期待結果

| No | 操作 | 許諾 | 結果 | 補足 |
|---|---|:---:|:---:|---|
| 1 | Write `~/s9d-extra/scripts/x.txt` | deny | - | **`~/` アンカー形は additional dir 実体にマッチしハード deny**(d の 2 は allow ✅ だった) |
| 2 | Write `~/s9d-extra/other/x.txt` | allow | ✅ | deny は scripts/ サブツリーだけ。additional dir の残りは acceptEdits 自動承認のまま |

- d の 2(allow ✅)→ d2 の 1(deny -)で、変えたのは**規則のアンカーだけ**。「アンカーずれ」が no-op の原因だったことが 1 変数で確定する。

## なぜそうなるか

- **一次 docs(permissions、2026-07-05 確認)**: `~/` で始まる規則パスは **home 起点**で解決される。→ `Edit(~/s9d-extra/scripts/**)` は additionalDirectories の実体パスを名指しでき、無印形(cwd 起点)では届かなかった木にマッチする。
- Edit 規則は編集系ツール全体(Write 含む)に適用され(a3)、deny は全モードで効くハード deny(f)。→ 承認や acceptEdits で lift されない。
- 実測のエラーメッセージも a3 と同型(`File is in a directory that is denied by your permission settings`、permission_denials には出ない=ハード deny の観測形)。

## 運用時の留意事項

- **マルチルート workspace の deny はルートごとに 1 本ずつアンカー付きで書く**のが正解形: cwd 用の `Edit(scripts/**)` + ルートごとの `Edit(~/path/to/root/scripts/**)`(または `//` 絶対形)。
- settings を共有するチームでは `~/` 形が使える(ユーザごとに home が違っても解決される)。マシン固定の絶対パスなら `//` 形。
- ここで守れるのは**編集系ツール経路のみ**。Bash 経路は別ベクタ(→ [b](../b-scripts-denywrite-bash/README.md) の sandbox `denyWrite`。そちらの denyWrite パスも additional dir を含める必要がある点は同じ発想)。

## 試し方(本リポジトリでの実測)

### お手軽に試す(対話)

`mkdir -p ~/s9d-extra` してから acceptEdits で `claude` を起動し、[prompt.ja.txt](./prompt.ja.txt) を貼り付ける。1 だけブロックされ 2 は承認なしで書ける(d と見比べると 1 の挙動だけが反転している)。

```bash
mkdir -p ~/s9d-extra
cd cases/S9-tool-write-scope/d2-additionaldir-home-anchor && claude --permission-mode acceptEdits
# → prompt.ja.txt を貼り付け(settings の $HOME 展開について d の注記参照)
```

### ハーネスで実測する(結果の記録・プローブ独立)

> プローブ 1(ハード deny)の headless は構造的 INCONCLUSIVE(a3/d-3 と同型)。機構は -m sdk の DENIED_HARD で確定。

```bash
python3 harness/run.py S9-tool-write-scope/d2-additionaldir-home-anchor           # headless: 1=INCONCLUSIVE(構造的) / 2=ALLOWED
python3 harness/run.py -m sdk S9-tool-write-scope/d2-additionaldir-home-anchor    # sdk: 1=DENIED_HARD / 2=ALLOWED
```

## 検証記録

| 日付 | バージョン | 実測したモダリティ | 補足 |
|---|---|---|---|
| 2026-07-05〜06 | v2.1.201 | headless + sdk(2プローブ×2、全一致) | configDir trusted:true。evidenceFound=false(additionalDirectories ロード確認)。scratch 探索(t8)で `~/` アンカーのマッチを事前確認してからケース化 |

## 対応する知識

- グループ [S9 README](../README.md) / 罠側 [d](../d-additionaldir-scope/README.md)
- 関連: [a3](../a3-edit-only/README.md)(Edit 規則=編集系全体のハード deny)/ [f](../f-bypass-hard-deny/README.md)(deny は bypass でも残存)
- 一次 docs: permissions(`~/` は home 起点アンカー / Edit rules apply to all built-in tools that edit files / Deny rules apply in every mode)
- 出典ギャップ: S9 GAPS G5(修正形side)
