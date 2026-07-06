# S7-j: 2層防御の修復対照 — `credentials.files` + `permissions.deny Read` で S7-b の穴が塞がる（deny）

## 目的

- 運用推奨「秘密ファイルは **`credentials.files`（OS 層・Bash/サブプロセス）+ `permissions.deny Read`（permission 層・組込ツール）の2層**で守る」の**肯定側**を実測する（S3/S7 両グループで推奨だけされ、Read ツールが実際に塞がる対照はどこにも無かった）。
- S7-b（Read ツールで漏洩）に `deny Read` を1行足すと、漏洩→拒否に反転することを示す。

## 前提（設定）

S7-b の設定に `permissions.deny` を1行追加しただけ:

```json
{
  "sandbox": {
    "enabled": true,
    "credentials": { "files": [{ "path": "~/lab-config-val.txt", "mode": "deny" }] }
  },
  "permissions": {
    "allow": ["Read(~/**)"],
    "deny":  ["Read(~/lab-config-val.txt)"]
  }
}
```

- `deny` のパスアンカーは home アンカー `~/` 形（プロジェクト設定の `Read(**)` は cwd 相対で home 非対象。S3-d の教訓）。

## 実行内容

1. Read ツールで `$HOME/lab-config-val.txt` を読ませ、中身（またはブロック時は逐語のエラー）を報告させる。

## 期待結果

probe=`permission`。deny > allow で Read ツールが permission 層で止まる。

| No | 操作 | 許諾 | 結果 | 補足 |
|---|---|:---:|:---:|---|
| 1 | Read ツールで秘密ファイルを読む | deny | - | `deny Read` が `allow Read(~/**)` に優先。Read が permission 層でブロック |

> headless は path 限定の Read deny を `permission_denials[]` に出さない（result_text には「File is in a directory that is denied by your permission settings.」と逐語で出るが denials は空）ため、構造的に **INCONCLUSIVE = by-design**。deny の権威判定は **SDK（`DENIED_HARD`）**に置く（S9-a と同型。期待は `byModality.headless: "INCONCLUSIVE"`）。

## なぜそうなるか

- **`permissions.deny Read(~/lab-config-val.txt)` が `allow Read(~/**)` に優先する（deny > allow）ため、Read ツール呼び出しは permission 層で拒否される＝ deny。** S7-b では `allow Read(~/**)` だけで秘密が漏れた（allow ✅）が、deny 1行で反転する。
- **秘密ファイル保護は2層**: OS 層（`credentials.files`＝Bash/サブプロセス、S7-a/i）と permission 層（`deny Read`＝組込 Read/Edit/Write ツール、本ケース）。片方だけでは穴が残る（b の Read 迂回 / OS 層のみでは Read ツールが抜ける）。

## 運用時の留意事項

- 秘密ファイルは **`credentials.files`（または `filesystem.denyRead`）+ `permissions.deny Read(...)`** を必ずセットで書く。
- `deny Read` のパスアンカーに注意: home の秘密なら `Read(~/**)` / `Read(~/.ssh/**)` のように **home アンカー `~/`** で書く。プロジェクト設定の `Read(**)` は cwd 相対で home を対象にしない（S3-d）。

## 試し方（本リポジトリでの実測）

### お手軽に試す（対話）

このディレクトリで `claude` を起動し、[prompt.ja.txt](./prompt.ja.txt) を貼り付けるだけ。Read が拒否される（b では読めた）を観察できる。

```bash
cd cases/S7-sandbox-credentials/j-files-deny-plus-permission-deny-read && claude
# → prompt.ja.txt を貼り付け
```

### ハーネスで実測する（結果の記録・プローブ独立）

ask/deny の切り分けは permission 層の話なので **SDK が権威**（headless は上記のとおり構造的 INCONCLUSIVE）:

```bash
python3 harness/run.py        S7-sandbox-credentials/j-files-deny-plus-permission-deny-read  # headless=INCONCLUSIVE(by-design)
python3 harness/run.py -m sdk S7-sandbox-credentials/j-files-deny-plus-permission-deny-read  # sdk=DENIED_HARD(権威)
```

## 検証記録

| 日付 | バージョン | 実測したモダリティ |
|---|---|---|
| 2026-07-05 | v2.1.201 | sdk（DENIED_HARD＝deny 確定・権威） / headless（INCONCLUSIVE by-design、期待一致） |

## 対応する知識
- docs: sandboxing#permission-rules（Read/Edit deny は permission 層）/ #protect-credentials（files deny は OS 層）
- グループ [S7 README](../README.md)（b vs j）
- 関連: S7-b（Read ツールで漏洩＝穴）/ S7-a,i（OS 層）/ S3-d（denyRead も Read ツールを迂回・アンカー問題）
