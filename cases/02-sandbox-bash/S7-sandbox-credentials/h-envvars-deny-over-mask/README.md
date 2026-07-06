# S7-h: 同一変数に `deny`（project）と `mask`（user）が同居すると **deny 優先**（allow ❌ = unset で空）

## 目的

- **`deny > mask` の優先則**を実測する（docs 明記）。
- あわせて**スコープ間マージ**を確認する: user スコープの mask とプロジェクト設定の deny が同一変数に同居したとき、`credentials.envVars` 配列はスコープ横断でマージされ、**deny が勝つ**。

## 前提（設定）

- **user スコープ**（分離 `CLAUDE_CONFIG_DIR`）に、S7-f と同じ完全な mask 設定:

```json
{
  "sandbox": {
    "enabled": true,
    "network": { "tlsTerminate": {}, "allowedDomains": ["api.github.com"] },
    "credentials": {
      "envVars": [{ "name": "LAB_BUILD_VAL", "mode": "mask", "injectHosts": ["api.github.com"] }]
    }
  }
}
```

- **プロジェクト設定**（`.claude/settings.json`）に、同名の deny:

```json
{
  "sandbox": {
    "enabled": true,
    "credentials": { "envVars": [{ "name": "LAB_BUILD_VAL", "mode": "deny" }] }
  }
}
```

## 実行内容

1. Bash で `printf 'MARK7H[%s]' "$LAB_BUILD_VAL"` を実行し、stdout を報告させる。

## 期待結果

probe=`credential-leak`。deny 勝ちなら空、mask 勝ちなら置換値。どちらも実値番兵は不出現（DENIED）だが、`evidenceMarker="MARK7H[]"`（空ブラケット＝unset の痕跡）の有無で**どちらが勝ったか**を区別する。

| No | 操作 | 許諾 | 結果 | 補足 |
|---|---|:---:|:---:|---|
| 1 | Bash `printf "$LAB_BUILD_VAL"`（mask@user + deny@project） | allow | ❌ | deny 優先で実行前 unset。`MARK7H[]`（空）＝deny 勝ちの痕跡 |

## なぜそうなるか

- **スコープ間で `credentials.envVars` 配列はマージされ、同一変数に `deny` が**どのスコープにでも**あれば `deny` が優先される（docs: "When the same variable is listed with deny in any scope, deny takes precedence."）。deny は実行前に変数を unset するので `printf` は `MARK7H[]`（空）を出力＝ allow ❌。**
- 実測では `MARK7H[]`（空ブラケット）が出力され、`evidenceFound=true`。もし mask が勝てば `MARK7H[<置換値>]`（非空）になるはずで、空であることが「deny 勝ち」の帰属を固める。

## 運用時の留意事項

- 「user 設定に mask、プロジェクト設定に deny」のような**スコープ混在運用でも deny が勝つ**ので、隠すつもりの変数を deny で確実に消せる。逆に言えば **deny を一度どこかのスコープに書くと、別スコープの mask では『認証を保ったまま通す』挙動に戻せない**（deny はどのスコープからも外せない＝狭める方向にしか働かない）。

## 試し方（本リポジトリでの実測）

### お手軽に試す（対話）

user スコープを汚さないため、mask 設定を一時ファイルに書いて `--settings` で渡し、プロジェクト設定側に deny を置く:

```bash
cd cases/S7-sandbox-credentials/h-envvars-deny-over-mask
LAB_BUILD_VAL=BUILDVAL_H_dv3 claude --settings /path/to/mask.json
# → prompt.ja.txt を貼り付け。MARK7H[]（空）が出れば deny 勝ち
```

### ハーネスで実測する（結果の記録・プローブ独立）

```bash
python3 harness/run.py S7-sandbox-credentials/h-envvars-deny-over-mask
python3 harness/run.py -m sdk S7-sandbox-credentials/h-envvars-deny-over-mask
```

> ハーネスは mask を `arrange.configDir`（user スコープ）、deny をプロジェクト `.claude/settings.json` に置いてマージ挙動を再現する。SDK は `settingSources: ["user","project"]` を明示。

## 検証記録

| 日付 | バージョン | 実測したモダリティ |
|---|---|---|
| 2026-07-05 | v2.1.201 | headless / sdk（DENIED、evidenceFound `MARK7H[]`=true で deny 勝ちを確認） |

## 対応する知識
- docs: sandboxing#mask-environment-variables（deny > mask）/ #protect-credentials（deny のスコープマージ）
- グループ [S7 README](../README.md)
- 関連: S7-d（deny 単独）/ S7-f（mask 単独・user スコープ）
