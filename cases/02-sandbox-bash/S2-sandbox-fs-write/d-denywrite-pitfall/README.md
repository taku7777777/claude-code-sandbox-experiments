# S2-d: `denyWrite:["~"]` は allowWrite 例外も cwd 暗黙許可も両方潰す(アンチパターン)

## 目的

⚠️ 危険設定の実測。運用でこの形を使ってはいけない。

- `denyWrite:["~"]` が、(1)`allowWrite` の例外パスと、(2)cwd の暗黙書込許可の**両方**を無効化することを、両プローブで実測する(S2 GAPS G8 の解消)。

## 前提(設定)

```json
{ "sandbox": { "enabled": true,
  "filesystem": { "allowWrite": ["~/lab-fs-write"], "denyWrite": ["~"] } } }
```

- b に `denyWrite:["~"]` を足した形(1変数差分)。cwd(リポジトリ)は **~ 配下**なので、`denyWrite:["~"]` は cwd も allowWrite 先も丸ごと巻き込む。

## 実行内容

1. Bash で cwd 直下に書込
2. Bash で `~/lab-fs-write/probe.txt`(allowWrite で開けたはずのパス)に書込
3. Bash で `~/lab-glob-XYZ/probe.txt`(別パス)に書込

## 期待結果

| No | 操作 | 許諾 | 結果 | 補足 |
|---|---|:---:|:---:|---|
| 1 | Bash `echo > inside.txt`(cwd 内) | allow | ❌ | **cwd の暗黙許可まで潰れる**(a/b では ✅) |
| 2 | Bash `echo > ~/lab-fs-write/probe.txt` | allow | ❌ | **allowWrite 例外も deny に負ける**(b では ✅) |
| 3 | Bash `echo > ~/lab-glob-XYZ/probe.txt` | allow | ❌ | - |

- 全プローブ `allow ❌`。とくにプローブ1(cwd 損失)とプローブ2(allowlist 損失)の**両方**を自ケース内で実測している。

## なぜそうなるか

- **sandbox FS 層では deny が allow に勝つ(docs: permissions の deny 優先と整合)。`denyWrite:["~"]` は「~ 配下すべて書込禁止」なので、~ 配下の cwd 暗黙許可も、~ 配下の `allowWrite:["~/lab-fs-write"]` 例外も、まとめて無効化する。**
- 結果、自分の作業ディレクトリにすら書けなくなる。「~ を守るつもり」が「何も書けない」に化ける典型。

## 運用時の留意事項

- **`denyWrite:["~"]` は使わない**。書込制御は `allowWrite`(ホワイトリスト)だけで行い、開けたいパスだけを足す。
- 「特定サブツリーを守りたい」なら、そのパスを allowWrite に入れないだけでよい(既定で cwd 外は書けない)。

## 試し方(本リポジトリでの実測)

### お手軽に試す(対話)

このディレクトリで `claude` を起動し、[prompt.ja.txt](./prompt.ja.txt) を貼り付けるだけ。3つとも `operation not permitted` になり、cwd にも allowWrite 先にも書けないことが見える。

```bash
cd cases/S2-sandbox-fs-write/d-denywrite-pitfall && claude
```

### ハーネスで実測する(結果の記録・プローブ独立)

```bash
python3 harness/run.py S2-sandbox-fs-write/d-denywrite-pitfall
python3 harness/run.py -m sdk S2-sandbox-fs-write/d-denywrite-pitfall
```

> probe=`fs-write`。判定は「対象パスが出来たか」。deny は OS 層で効くため canUseTool には現れない。

## 検証記録

| 日付 | バージョン | 実測したモダリティ |
|---|---|---|
| 2026-07-05 | v2.1.201 | headless / sdk(3プローブとも一致) |

## 対応する知識

- グループ [S2 README](../README.md)(a→d で 1・2 が ✅→❌ になる決定的証拠)
- 関連: S2-b(allowWrite で開ける・d の1変数前)/ S2-g(deny 勝ちの入れ子)
