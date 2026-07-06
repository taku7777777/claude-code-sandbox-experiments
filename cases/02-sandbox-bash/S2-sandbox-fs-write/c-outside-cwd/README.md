# S2-c: cwd 外書込は OS 層 EPERM で止まる(`allow ❌`)。承認フォールバック(ask)ではない

## 目的

- sandbox 有効時、cwd の外への Bash 書込が境界外として止まることを確認する(a と同一設定・「境界外は拒否」の否定側対照)。
- その失敗が **`allow ❌`(OS 層 EPERM)であって `ask`(承認要求)ではない**ことを SDK で確定する(旧 INCONCLUSIVE の解消)。

## 前提(設定)

```json
{ "sandbox": { "enabled": true } }
```

- S2-a と同一設定(allowWrite なし)。c は同じ境界を「cwd 外プローブ」の視点で明示するサブケース。
- `arrange`: cwd 外の書込先を先に作り、実行後 `cleanup` で撤去。

## 実行内容

1. Bash で cwd 直下に書込(対照)
2. Bash で `~/lab-fs-write/probe.txt`(cwd 外)に書込
3. Bash で `~/lab-glob-XYZ/probe.txt`(cwd 外・別パス)に書込

## 期待結果

| No | 操作 | 許諾 | 結果 | 補足 |
|---|---|:---:|:---:|---|
| 1 | Bash `echo > inside.txt`(cwd 内) | allow | ✅ | 境界内の対照 |
| 2 | Bash `echo > ~/lab-fs-write/probe.txt`(cwd 外) | allow | ❌ | OS 層 EPERM。ask は発火しない(SDK askFired 空) |
| 3 | Bash `echo > ~/lab-glob-XYZ/probe.txt`(cwd 外) | allow | ❌ | 同上 |

- 列としては a と同一(設定が同じなので当然)。c の主眼は **❌ の内訳が `allow ❌` である**ことの確定。

## なぜそうなるか

- 書込境界は cwd + 付け替え `$TMPDIR` のみ(docs: sandboxing)。cwd 外はその外側。
- **境界外書込は permission を自動許可されたまま OS 層で EPERM する。非サンドボックス再試行の承認要求(ask)は起きない** — SDK で `canUseTool` が発火しない(askFired 空)ことを実測。よって headless の DENIED は「ask の auto-deny」ではなく OS ブロック。
- 対比: S5-c では cwd 外書込が**脱出して成功する**。あちらは `Bash(*)` allow + `allowUnsandboxedCommands` があり非サンドボックス再試行が自動承認されるため。S2-c にはその設定が無いので境界で止まる。

## 運用時の留意事項

- cwd 外書込の失敗は OS 層の遮断。対話で承認しても通らない(承認プロンプト自体が出ない)。通したいなら `allowWrite` に足す(→ S2-b)。
- 逆に言えば、sandbox は広い allow を併用しない限りプロジェクト外への書込を OS レベルで確実に止める。

## 試し方(本リポジトリでの実測)

### お手軽に試す(対話)

このディレクトリで `claude` を起動し、[prompt.ja.txt](./prompt.ja.txt) を貼り付けるだけ。2・3 が承認プロンプトなしで `operation not permitted` になる(＝ask ではなく OS ブロック)ことが見える。

```bash
cd cases/S2-sandbox-fs-write/c-outside-cwd && claude
```

### ハーネスで実測する(結果の記録・プローブ独立)

```bash
python3 harness/run.py S2-sandbox-fs-write/c-outside-cwd
python3 harness/run.py -m sdk S2-sandbox-fs-write/c-outside-cwd   # askFired 空 = OS ブロックの裏づけ
```

> probe=`fs-write`。SDK は OS 境界そのものは測れないが、境界外書込で `canUseTool` が発火しない(askFired 空)ことを記録でき、`allow ❌`(ask でない)ことの直接証拠になる。

## 検証記録

| 日付 | バージョン | 実測したモダリティ | 補足 |
|---|---|---|---|
| 2026-07-05 | v2.1.201 | headless / sdk(3プローブとも一致) | 旧 INCONCLUSIVE(自己拒否)を中立命名+3プローブで再測し `allow ❌` に確定 |

## 対応する知識

- docs/FINDINGS.md: Q2 / グループ [S2 README](../README.md)
- 関連: S2-a(実測済みの境界基準)/ S5-c(allow 併用で cwd 外へ脱出)/ S9-b(sandbox denyWrite の `allow ❌` 肯定対照)
- 一次 docs: sandboxing(既定境界 = cwd + 付け替え `$TMPDIR`)
