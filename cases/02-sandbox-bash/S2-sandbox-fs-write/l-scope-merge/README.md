# S2-l: `sandbox.filesystem` はスコープ間で**配列マージ** — project の allowWrite で user の denyWrite は外せない

## 目的

- docs 明記(未実測だった)の **「sandbox.filesystem の配列はスコープ間でマージされる(置換ではない)。
  どのスコープも境界を狭められるが、他スコープの deny を外せない」**を実測する。
- セキュリティ上の要: **リポジトリ側(project)の settings では、ユーザ/管理側の deny を無効化できない**。

## 前提(設定)

- **user スコープ**(分離 `CLAUDE_CONFIG_DIR` の settings.json — ハーネスの `arrange.configDir` で配置):

```json
{ "sandbox": { "filesystem": { "denyWrite": ["~/lab-merge/sub"] } } }
```

- **project スコープ**(このディレクトリの `.claude/settings.json`):

```json
{ "sandbox": { "enabled": true, "filesystem": { "allowWrite": ["~/lab-merge"] } } }
```

## 実行内容

1. Bash で `~/lab-merge/sub/f.txt`(user の deny 対象。project の allow の内側)に書込
2. Bash で `~/lab-merge/f.txt`(deny 対象外・project の allow 内)に書込

## 期待結果

| No | 操作 | 許諾 | 結果 | 補足 |
|---|---|:---:|:---:|---|
| 1 | Bash `echo > ~/lab-merge/sub/f.txt` | allow | ❌ | **project の allow では user の deny を外せない**(EPERM) |
| 2 | Bash `echo > ~/lab-merge/f.txt` | allow | ✅ | allowWrite は和集合として有効 = マージは置換ではない |

## なぜそうなるか

- docs(sandboxing): `sandbox.filesystem` の配列は**スコープ間でマージ**される。allow は和集合(プローブ 2)、
  deny はどのスコープ由来でも常勝(プローブ 1。ケース内 deny 常勝 = S2-g/i と同じ規則がスコープ横断でも成立)。
- P7(permission 規則のスコープ precedence)と役割が対になる: permission 層は「deny はどのスコープからでも勝つ」、
  sandbox 層は「配列マージ + deny 常勝」。どちらも**下位/リポジトリ側の設定で上位の禁止を外せない**方向に倒れている。

## 運用時の留意事項

- 管理側で「ここには書かせない」を強制したいなら user(または managed)スコープの `denyWrite` に書く。
  リポジトリの `.claude/settings.json` がどう allow を広げても deny は生き残る(S7 credentials も同じ合成規則)。
- 逆に、リポジトリ側で「この deny は邪魔」と思っても project settings では外せない。外すには
  deny を書いたスコープ側を修正するしかない。

## 試し方(本リポジトリでの実測)

- user スコープの再現が必要なため、お手軽対話は**ハーネスの prepare 経由**で行う
  (分離 `CLAUDE_CONFIG_DIR` を組み立てて手順を提示してくれる):

```bash
python3 harness/run.py -m interactive --step prepare S2-sandbox-fs-write/l-scope-merge
```

- ハーネス実測:

```bash
python3 harness/run.py S2-sandbox-fs-write/l-scope-merge
python3 harness/run.py -m sdk S2-sandbox-fs-write/l-scope-merge
```

> SDK は既定で project スコープしか読まないため、case.json で `settingSources: ["user","project"]` を明示している(P7-a と同じ注意)。

## 検証記録

| 日付 | バージョン | 実測したモダリティ |
|---|---|---|
| 2026-07-05 | v2.1.201 / SDK 0.3.200 | headless / sdk(2プローブとも一致。EPERM 文言 evidenceFound=true) |

## 対応する知識

- docs/FINDINGS.md: Q2 / グループ [S2 README](../README.md) / S2 GAPS G6 の解消
- 関連: P7(permission 層のスコープ precedence・configDir の仕組み)/ S2-g,i(ケース内の deny 常勝)/ S7(credentials も同じ合成規則)
