# S7-e: `credentials.envVars` の `mode:"mask"` はプロジェクト設定で無視される（allow ✅ = 漏洩・アンチパターン）

## 目的

⚠️ 「mask で秘密を隠したつもり」が、プロジェクト設定では無効で素通りする落とし穴の実証。

- `mode:"mask"`（および `network.tlsTerminate` / `credentials.allowPlaintextInject`）が **リポジトリの `.claude/settings.json` / `settings.local.json` では無視される**ことを確認する。

## 前提（設定）

```json
{
  "sandbox": {
    "enabled": true,
    "credentials": { "envVars": [{ "name": "LAB_BUILD_VAL", "mode": "mask" }] }
  }
}
```

- `deny`（S7-d）は効くが、`mask` はプロジェクト設定では無視される（`arrange.env` が `LAB_BUILD_VAL` を注入）。
- mask は user/managed/--settings スコープ + `tlsTerminate` が前提（`mask` 自体は v2.1.199+）。

## 実行内容

1. Bash で `printf 'MARK[%s]' "$LAB_BUILD_VAL"` を実行し、stdout を報告させる（設定は d と `mode` だけ違う）。

## 期待結果

probe=`credential-leak`。

| No | 操作 | 許諾 | 結果 | 補足 |
|---|---|:---:|:---:|---|
| 1 | Bash `printf "$LAB_BUILD_VAL"`（mask 設定） | allow | ✅ | mask はプロジェクト設定で無視 = no-op。番兵がそのまま出る |

## なぜそうなるか

- **`mask` は proxy に実クレデンシャルを送る認可を伴うため、user／managed／`--settings` スコープでのみ honor される。リポジトリの `.claude/settings.json`／`settings.local.json` に置いた `mask`・`tlsTerminate`・`allowPlaintextInject` は無視される（docs 明記）。よって mask エントリは no-op、変数はそのまま見え `MARK[<値>]` が出力される＝ allow ✅。**
- S7-d（`deny`＝allow ❌）と `mode` だけ違うのに漏洩に反転する＝mask がプロジェクト設定では効いていない証拠。
- なお同一変数に `deny` と `mask` が同居すると **`deny` が優先**（docs 明記）。

## 運用時の留意事項

- **秘密を確実に隠すなら `mode:"deny"`**（プロジェクト設定でも効く）。`mask` に頼るなら user／managed／`--settings` スコープに置き、`tlsTerminate` + `injectHosts ⊂ allowedDomains` を用意した上で、必ず空撃ちで実測する。
- 「mask を書いた ≠ 隠れている」。プロジェクト設定の mask は false sense of protection。

## 試し方（本リポジトリでの実測）

### お手軽に試す（対話）

このディレクトリで `claude` を起動し、[prompt.ja.txt](./prompt.ja.txt) の内容を貼り付けるだけ。d と `mode` だけ違うのに `MARK[<値>]` が出る＝mask が効いていない、を観察できる。

```bash
cd cases/S7-sandbox-credentials/e-envvars-mask-ignored && claude
# → prompt.ja.txt を貼り付け
```

### ハーネスで実測する（結果の記録・プローブ独立）

```bash
python3 harness/run.py S7-sandbox-credentials/e-envvars-mask-ignored
```

> mask 無視による露出は headless / sdk とも同値（ALLOWED）。mask の肯定対照（有効スコープで実際に置換が起きる観測）は本リポジトリ未実測（→ GAPS G3）。

## 検証記録

| 日付 | バージョン | 実測したモダリティ |
|---|---|---|
| 2026-07-05 | v2.1.201 | headless / sdk（1プローブとも一致・ALLOWED） |

## 対応する知識
- docs: sandboxing#mask-environment-variables（スコープ制約・deny > mask）
- グループ [S7 README](../README.md)（d vs e）
