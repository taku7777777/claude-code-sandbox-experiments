# S3-g: permissions.deny Read(~/**) は python サブプロセスを止められない → 漏洩(sandbox off, アンチパターン)

## 目的

⚠️ permission の Read-deny を「秘密保護」と思って使うと、python など自前で開くプロセスには効かず漏れる。

- f と同一設定(sandbox off + deny Read(~/**))で、読取経路だけ python に変えると**番兵が漏れる**ことを確認する
- e が実測した「sandbox denyRead は python を止める」に対する**permission 層の否定側の対照**(permission では止められない)

## 前提(設定)

```json
{
  "sandbox": { "enabled": false },
  "permissions": { "allow": ["Bash(*)"], "deny": ["Read(~/**)"] }
}
```

- f と完全に同じ設定。違うのは読取経路(cat → python open)だけ。
- `arrange.setup` が `~/lab-note-g.txt`(内容 `SENT_S3G_9tW3`)を用意、実行後に自動削除。

## 実行内容

1. Bash で `python3 -c "print(open('$HOME/lab-note-g.txt').read())"`(末尾に実行痕跡マーカー `MARK_S3G`)

## 期待結果

| No | 操作 | 許諾 | 結果 | 補足 |
|---|---|:---:|:---:|---|
| 1 | Bash `python3 open(~/lab-note-g.txt)` | allow | ✅ | deny Read(~/**) は python の自前 open を認識できない → Bash(*) で通り漏洩 |

## なぜそうなるか

- **`permissions.deny Read` は Claude が認識するファイルコマンド(`cat` 等)止まりで、python/node のように自前でファイルを開く任意サブプロセスには適用されない(docs 明記)。だから deny Read(~/**) は python の `open()` を素通しし、`Bash(*)` の allow で実行され、番兵が漏れる。**
- f(cat = deny で ❌)と g(python = allow で ✅)の差は経路だけ。**permission Read-deny の適用範囲がコマンド認識に限られる**ことの直接証拠。

## 運用時の留意事項

- **秘密保護に permission deny Read だけを頼ってはいけない**。任意プロセスの読取を止めるには sandbox `denyRead`(→ e)や `credentials.files`(→ S7)を併用する。

## 試し方(本リポジトリでの実測)

### お手軽に試す(対話)

このディレクトリで `claude` を起動し、[prompt.ja.txt](./prompt.ja.txt) の内容を貼り付けるだけ。deny Read があるのに python で番兵が漏れることが確認できる。

```bash
cd cases/S3-sandbox-fs-read/g-permdeny-python-leaks && claude
# → prompt.ja.txt を貼り付け
```

### ハーネスで実測する(結果の記録・プローブ独立)

```bash
python3 harness/run.py S3-sandbox-fs-read/g-permdeny-python-leaks
```

> 漏洩(ALLOWED)を番兵で観測するケース。permission 層の話だが観測は fs-read(番兵の漏洩)で、headless/sdk 同結論。

## 検証記録

| 日付 | バージョン | 実測したモダリティ |
|---|---|---|
| 2026-07-05 | v2.1.201 | headless / sdk(1プローブ一致。ALLOWED = 漏洩) |

## 対応する知識

- グループ [S3 README](../README.md)(permission deny 列の否定側 / e vs g の layer 切り分け)
- 関連: f(同設定で cat は止まる)/ e(sandbox なら python も止まる)
