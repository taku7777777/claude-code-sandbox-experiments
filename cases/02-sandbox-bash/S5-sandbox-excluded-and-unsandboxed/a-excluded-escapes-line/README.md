# S5-a: `excludedCommands` の一致トークンを含む行は全体が sandbox 外で走る → cwd 外へ書込脱出（アンチパターン）

## 目的

⚠️ sandbox の本物の脱出穴の実証。運用でこの同居（`excludedCommands` × `Bash(*)`）を作ってはいけない。

- `excludedCommands` に一致するコマンドを含む**行全体**が sandbox 外で実行され、チェーンした redirect が cwd 外（`$HOME`）へ書けて（脱出して）しまうことを確認する。

## 前提(設定)

```json
{
  "sandbox": { "enabled": true, "excludedCommands": ["echo *"] },
  "permissions": { "allow": ["Bash(*)"] }
}
```

- `echo` を excluded に。`Bash(*)` で Bash は permission 自動許可。
- 実行コマンドは `echo hi && echo data > $HOME/lab-a.txt`（両サブコマンドとも `echo` = excluded。非 excluded コマンドの巻き込みは S5-b で分離）。

## 実行内容

1. Bash で `echo hi && echo data > $HOME/lab-a.txt` を実行（`$HOME` は cwd 外＝通常の sandbox なら書けない）

## 期待結果

| No | 操作 | 許諾 | 結果 | 補足 |
|---|---|:---:|:---:|---|
| 1 | Bash `echo hi && echo > ~/lab-a.txt`（cwd 外へ redirect） | allow | ✅ | excluded トークンを含む行が全体 sandbox 外実行 → cwd 外へ書込脱出 |

- **`allow ✅` = permission は `Bash(*)` で自動許可され、excluded によって行全体が sandbox 外で走るため OS 境界も無く $HOME に書けてしまう。** 通常の sandbox（S2-a）なら cwd 外書込は `allow ❌`（OS 層 EPERM）になる。

## なぜそうなるか

- **`excludedCommands` は一致トークンを含む行を丸ごと sandbox 外で実行する。`echo` が excluded なので、`&&` でチェーンした `echo > $HOME/..`（通常は cwd 外で `allow ❌`＝S2-a）も sandbox 外で走り、$HOME に書けてしまう。** これが行全体脱出（承認不要・行全体巻き込み）。
- SDK でも askFired 空のまま脱出（ALLOWED）＝承認プロンプトを介さない無条件脱出であることを実測。

## 運用時の留意事項

- **`excludedCommands` と `Bash(*)` を同居させない**。worker は `excludedCommands:[]`。
- `excludedCommands` には **managed-only lockdown が無い**（一次 docs: sandboxing「Keep developers from widening the policy」で明記）。managed 設定で固定できず、project/local settings 側で開発者や侵害されたリポジトリがいつでも追記できる。だから「最小化」しか防御手段が無い。
- excluded にするなら exact-path のスクリプト1本に絞り、チェーンを ask ゲートに通す設計にする。

## 試し方(本リポジトリでの実測)

### お手軽に試す(対話)

このディレクトリで `claude` を起動し、[prompt.ja.txt](./prompt.ja.txt) を貼り付けるだけ。承認プロンプトも出ないまま `~/lab-a.txt` が出来てしまうのが見える（＝脱出）。

```bash
cd cases/S5-sandbox-excluded-and-unsandboxed/a-excluded-escapes-line && claude
# → prompt.ja.txt を貼り付け
```

### ハーネスで実測する(結果の記録・プローブ独立)

```bash
python3 harness/run.py S5-sandbox-excluded-and-unsandboxed/a-excluded-escapes-line
python3 harness/run.py -m sdk S5-sandbox-excluded-and-unsandboxed/a-excluded-escapes-line
```

> sandbox(OS 層)の脱出を観測するケース(probe=`fs-write`、`~/lab-a.txt` の存在で判定)。**canUseTool は permission 層しか見えず OS 境界そのものは測れない**が、SDK は「脱出時に ask が発火しない(askFired 空)」ことを併せて記録でき、無条件脱出であることの裏づけになる。

## 検証記録

| 日付 | バージョン | 実測したモダリティ |
|---|---|---|
| 2026-07-05 | v2.1.201 | headless / sdk(1プローブ一致) |

- 一次 docs 裏取り: 「行全体が sandbox 外で走る（チェーン巻き込み）」は公式 docs（sandboxing）に明記が無く【要裏取り】＝観測駆動。docs は `excludedCommands` の存在と「managed-only lockdown 無し」は明記。

## 対応する知識

- docs/FINDINGS.md: `excludedCommands` は行全体を sandbox 外実行 → cwd 外へ脱出
- グループ [S5 README](../README.md)（2軸マトリクス）
- 関連: S5-b（非 excluded コマンドの巻き込みを分離）/ S2-a（cwd 外は本来 `allow ❌`）/ S5-d（strict で封鎖）
