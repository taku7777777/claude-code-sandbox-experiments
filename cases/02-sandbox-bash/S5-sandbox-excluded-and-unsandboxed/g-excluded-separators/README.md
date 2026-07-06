# S5-g: excluded トークンを含む行の脱出は区切り記号に依らない（`;` / `|` でも行全体が抜ける・アンチパターン）

## 目的

⚠️ 行全体脱出（S5-a/b）がセパレータ種別に依存しないことを実証する。

- S5-a/b は `&&` チェーンでのみ「excluded を1つ含む行が非 excluded コマンドごと sandbox 外に出る」ことを実測していた。本ケースは同一設定で区切りを **`;`（semicolon-escape）と `|`（pipe-escape）**に替え、脱出が **separator に依らない**ことを直接確認する。
- permission 層の separator マトリクス（P4-g: `;`/`|` でもサブコマンド個別照合で deny）と**対になる sandbox 層**の separator 断面。

## 前提(設定)

```json
{
  "sandbox": { "enabled": true, "excludedCommands": ["echo *"] },
  "permissions": { "allow": ["Bash(*)"] }
}
```

- S5-a/b と同設定。変えたのは実行コマンドの**区切り記号だけ**（`&&` → `;` / `|`）。
- source は macOS に存在する `/etc/hosts`（旧 b の `/etc/hostname` は macOS に無い）。

## 実行内容

1. Bash で `echo hi ; cat /etc/hosts > $HOME/s5g1-proof.txt` を実行（`;` 区切り・後段 `cat`=非 excluded が cwd 外 `$HOME` へ書く）
2. Bash で `echo hi | tee $HOME/s5g2-proof.txt` を実行（`|` 区切り・`tee`=非 excluded が cwd 外へ書く）

## 期待結果

| No | 操作 | 許諾 | 結果 | 補足 |
|---|---|:---:|:---:|---|
| 1 | Bash `echo hi ; cat … > ~/s5g1-proof.txt`（`;` 区切り） | allow | ✅ | `&&` 同様、excluded トークン1つで行全体が sandbox 外実行 |
| 2 | Bash `echo hi \| tee ~/s5g2-proof.txt`（`\|` 区切り） | allow | ✅ | パイプでも同じ。区切り記号に依らない脱出 |

- **両プローブとも `allow ✅`** = 後段の非 excluded コマンド（`cat` / `tee`）が cwd 外へ書けた＝行全体が sandbox 外で走った。**区切りが `&&` でも `;` でも `|` でも脱出は同じ**（S5-a/b の `&&` 断面が separator に一般化する）。
- SDK でも askFired 空（`Bash(*)` 自動承認で無条件脱出、ask ではない）。

## なぜそうなるか

- **`excludedCommands` の判定は「行に一致トークンを含むか」で効き、一致すると行全体が sandbox 外実行に切り替わる。この切り替えはシェルの区切り記号（`&&`/`;`/`|`）を区別しない** — 行に excluded な `echo` が1つあれば、どの区切りで連結された非 excluded コマンドも巻き込まれて cwd 外へ書ける。
- P4-g（permission 層）とは層が違う: permission の Bash 照合は `;`/`|` でも**サブコマンド個別**に見て deny を効かせる。だが `excludedCommands` は**行単位の sandbox 層**なので、個別照合ではなく行全体が抜ける。「permission は個別・sandbox 脱出は行全体」の対比。

## 運用時の留意事項

- **excluded にしたコマンドを含む行に、他のコマンドをどの区切りでもチェーンできる余地を残さない**。`&&` だけ警戒しても `;` / `|` で同じ脱出が起きる。
- excluded は exact-path のスクリプト単体に限定し、`Bash(*)` を使わず allow を狭くする（脱出の増幅要因は S5-e/h で実測した `Bash(*)` 自動承認）。

## 試し方(本リポジトリでの実測)

### お手軽に試す(対話)

このディレクトリで `claude` を起動し、[prompt.ja.txt](./prompt.ja.txt) を貼り付けるだけ。`;` でも `|` でも `~/s5g*-proof.txt` が出来てしまうのが見える。

```bash
cd cases/S5-sandbox-excluded-and-unsandboxed/g-excluded-separators && claude
# → prompt.ja.txt を貼り付け
```

### ハーネスで実測する(結果の記録・プローブ独立)

```bash
python3 harness/run.py S5-sandbox-excluded-and-unsandboxed/g-excluded-separators
python3 harness/run.py -m sdk S5-sandbox-excluded-and-unsandboxed/g-excluded-separators
```

> sandbox(OS 層)の脱出を観測するケース(probe=`fs-write`、`~/s5g*-proof.txt` の存在で判定)。**canUseTool は OS 境界を測れない**が、SDK は脱出時に ask が発火しない(askFired 空)ことを記録する。

## 検証記録

| 日付 | バージョン | プラットフォーム | 実測したモダリティ |
|---|---|---|---|
| 2026-07-06 | v2.1.201 | macOS(darwin/sandbox-exec) | headless / sdk（2プローブとも一致・askFired 空） |

- 一次 docs 裏取り: 「一致トークンを含む行全体が sandbox 外で走る」および**そのセパレータ非依存性**は公式 docs（sandboxing）に**明記が無く**【要裏取り】＝本ケースの観測で確定。docs は `excludedCommands` の存在と managed-only lockdown 不在のみ明記。

## 対応する知識

- docs/FINDINGS.md: `excludedCommands` は行全体を sandbox 外実行 → cwd 外へ脱出（separator 非依存）
- グループ [S5 README](../README.md)（2軸マトリクス）
- 関連: S5-a（両サブコマンド excluded の基準・`&&`）/ S5-b（非 excluded を `&&` で分離）/ S5-h（`Bash(*)` を外すと後段は ask）/ P4-g（permission 層は `;`/`|` でも個別照合で deny＝層の対比）
