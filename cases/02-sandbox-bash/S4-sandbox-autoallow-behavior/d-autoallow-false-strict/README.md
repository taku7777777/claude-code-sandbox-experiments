# S4-d: `autoAllowBashIfSandboxed:false` → 自動許可が消え、cwd 書込も通常の承認フロー(ASK)に戻る

## 目的

- `autoAllowBashIfSandboxed:false` にすると sandbox の自動許可が消え、Bash が**通常の permission フロー**に戻ることを確認する(a の反転)。
- その戻り先が **`ask`(承認要求)であって OS 層ブロックではない**ことを SDK で確定する(旧 record の "strict mode" 誤帰属を訂正)。

## 前提(設定)

```json
{ "sandbox": { "enabled": true, "autoAllowBashIfSandboxed": false } }
```

- a に `autoAllowBashIfSandboxed:false` を足しただけ(1変数差分)。プロンプトも a と同一(`echo data > inside.txt`)。

## 実行内容

1. Bash で cwd 直下に書込(`echo data > inside.txt`)

## 期待結果

| No | 操作 | 許諾 | 結果 | 補足 |
|---|---|:---:|:---:|---|
| 1 | Bash `echo data > inside.txt`(cwd 内) | ask | ✅ | 承認すれば書ける。headless は承認者不在で auto-deny |

- **`ask ✅`**: 自動許可が消えて default モードの承認フローに戻る。承認すれば cwd 書込は成功する(OS ブロックではない)。

## なぜそうなるか

- **`autoAllowBashIfSandboxed:false` は sandbox の自動許可を無効化する。Bash は通常の permission 判定に戻り、default モードでは承認要求(ask)になる。** SDK で `canUseTool` が Bash に対して発火(askFired=[Bash])= ask に戻ったことの直接証拠。headless では承認者不在で auto-deny(denials=[Bash])。
- これは OS 層のブロックではなく、`allowUnsandboxedCommands:false`(Strict sandbox mode / spec §4.2)とも**別物**。旧 `results` の "restricted in strict mode" はモデルの作文で誤り。

## 運用時の留意事項

- 「すべての Bash を明示承認させたい(厳格運用)」ときに使う。ask に戻るだけなので、対話なら承認して通せる/CI(headless)では止まる。
- CI で自動実行したいなら `false` にはせず、`allow` を明示するか acceptEdits を併用する。

## 試し方(本リポジトリでの実測)

### お手軽に試す(対話)

このディレクトリで `claude` を起動し、[prompt.ja.txt](./prompt.ja.txt) を貼り付けるだけ。a と違い承認プロンプトが出る(承認すれば書ける)ことが見える。

```bash
cd cases/S4-sandbox-autoallow-behavior/d-autoallow-false-strict && claude
```

### ハーネスで実測する(結果の記録・プローブ独立)

ask 系なので3形態で解決が変わる:

```bash
# ヘッドレス: 承認者不在で auto-deny → DENIED
python3 harness/run.py S4-sandbox-autoallow-behavior/d-autoallow-false-strict

# SDK(canUseTool = ask の計測器): Bash に ask が発火 → ASK(OS ブロックでないことの裏づけ)
python3 harness/run.py -m sdk S4-sandbox-autoallow-behavior/d-autoallow-false-strict

# 対話(TUI): 承認プロンプトが出て、承認すれば成功 → ASK
python3 harness/run.py -m interactive --step prepare S4-sandbox-autoallow-behavior/d-autoallow-false-strict
python3 harness/run.py -m interactive --step judge S4-sandbox-autoallow-behavior/d-autoallow-false-strict --answer prompted=y --answer approved=y
```

## 検証記録

| 日付 | バージョン | 実測したモダリティ |
|---|---|---|
| 2026-07-05 | v2.1.201 | headless / sdk(1プローブ一致・ASK 確定) |
| 2026-07-06 | v2.1.201 | **対話(cmux 駆動)**: `autoAllowBashIfSandboxed:false` で Bash `echo data > inside.txt` に `Do you want to proceed?` の承認プロンプトが実出現(OS ブロックではなく ask に復帰)→承認で書込完遂(ask ✅)。3 点セット完成 |

## 対応する知識

- グループ [S4 README](../README.md)
- 関連: S4-a(autoAllow=true の基準)/ S2-a(同じ cwd 書込が sandbox 自動許可で ✅)
- 一次 docs: settings(`autoAllowBashIfSandboxed`)/ sandboxing(Strict sandbox mode は別キー `allowUnsandboxedCommands`)
