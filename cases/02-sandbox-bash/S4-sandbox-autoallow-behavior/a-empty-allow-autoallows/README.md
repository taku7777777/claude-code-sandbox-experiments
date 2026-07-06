# S4-a: sandbox on(`autoAllowBashIfSandboxed` 既定 true)→ cwd 書込は無プロンプトで自動許可

## 目的

- `autoAllowBashIfSandboxed`(**公式キー・既定 true**)により、規則を書かなくても sandboxed Bash の cwd 書込が承認プロンプトなしで通ることを確認する(d の反転側の基準)。

## 前提(設定)

```json
{ "sandbox": { "enabled": true } }
```

- sandbox を on にしただけ。d との差分は `autoAllowBashIfSandboxed` の1変数のみ(a=既定 true / d=false)。プロンプトも d と同一(`echo data > inside.txt`)。

## 実行内容

1. Bash で cwd 直下に書込(`echo data > inside.txt`)

## 期待結果

| No | 操作 | 許諾 | 結果 | 補足 |
|---|---|:---:|:---:|---|
| 1 | Bash `echo data > inside.txt`(cwd 内) | allow | ✅ | sandbox が Bash を自動許可(canUseTool 発火せず) |

- **`allow ✅`**: sandbox 境界が Bash を封じ込めるので、permission エンジンは承認を省いて自動許可する。

## なぜそうなるか

- **`autoAllowBashIfSandboxed` の既定 true が、sandbox 化された Bash を無プロンプトで自動許可する(docs: settings に「Auto-approve bash commands when sandboxed. Default: true」)。** これが worker 構成が `sandbox on + 規則なし`で回る根拠。
- この auto-allow は permission mode の `auto`(サーバ分類器・§1.4)とは**別機構**(docs: sandboxing「auto-allow は auto mode とは別で、独立して働き併用もできる」)。本グループの "auto-allow" は前者を指す。

## 運用時の留意事項

- 自動許可の対象は sandbox 化された Bash に限る。cwd 外は境界外で `allow ❌`(→ S2-a/c)、Write ツールは sandbox 対象外(→ S1)。
- auto-allow 下でも残る例外がある(明示 deny / `Bash(git push *)` 等の content-scoped ask / 危険パスの `rm`)→ S4 README。

## 試し方(本リポジトリでの実測)

### お手軽に試す(対話)

このディレクトリで `claude` を起動し、[prompt.ja.txt](./prompt.ja.txt) を貼り付けるだけ。承認プロンプトなしで `inside.txt` が出来る。

```bash
cd cases/S4-sandbox-autoallow-behavior/a-empty-allow-autoallows && claude
```

### ハーネスで実測する(結果の記録・プローブ独立)

```bash
python3 harness/run.py S4-sandbox-autoallow-behavior/a-empty-allow-autoallows
```

> probe=permission(allow)。副作用が出れば ALLOWED。allow 確定なので**全形態で同結論**(→ docs/EXECUTION-MODALITIES.md)。SDK でも canUseTool は発火せず ALLOWED。

## 検証記録

| 日付 | バージョン | 実測したモダリティ |
|---|---|---|
| 2026-07-05 | v2.1.201 | headless / sdk(1プローブ一致・askFired 空) |

## 対応する知識

- グループ [S4 README](../README.md)
- 関連: S4-d(autoAllow=false で ASK に反転)/ S2-a(同じ cwd 書込を sandbox 境界の視点で)/ S1(Write ツールは sandbox 対象外)
- 一次 docs: settings(`autoAllowBashIfSandboxed` 既定 true)/ sandboxing(auto-allow ≠ mode auto)
