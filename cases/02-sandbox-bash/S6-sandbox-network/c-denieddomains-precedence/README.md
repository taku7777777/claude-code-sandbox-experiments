# S6-c: `deniedDomains` は `allowedDomains` に優先。明示許可でも到達せず(`allow ❌`)

## 目的

- 同一ホストを `allowedDomains` と `deniedDomains` の両方に入れたとき、denied が勝つ(deny-first)ことを実測する。

## 前提(設定)

```json
{
  "sandbox": { "enabled": true, "allowUnsandboxedCommands": false,
    "network": { "allowedDomains": ["example.com"], "deniedDomains": ["example.com"] } },
  "permissions": { "allow": ["Bash(*)"] }
}
```

- b との差分は `deniedDomains:["example.com"]` を1つ足しただけ。

## 実行内容

1. Bash で `curl https://example.com` を実行し、成功時だけ成功マーカー(`NETMARKER.txt`)を書く

## 期待結果

| No | 操作 | 許諾 | 結果 | 補足 |
|---|---|:---:|:---:|---|
| 1 | Bash `curl https://example.com`(target 到達) | allow | ❌ | deniedDomains が allowedDomains に優先(deny-first) |

- b(allow のみ=`allow ✅`)との差分は deniedDomains の追加だけで、✅→❌ に反転する。

## なぜそうなるか

- **example.com を明示 allow していても、同じホストが deniedDomains にあると deny が勝つ。** permission 層(deny > allow)と同じ deny-first がネットワークにも効く。
- 公式 docs も「deniedDomains は広い allowedDomains ワイルドカードにも勝つ」と明記(本ケースは literal 同一ホストの衝突を実測。広域 allow ワイルドカードへの deny 優先は [c2](../c2-wildcard-allow/README.md)/[c3](../c3-wildcard-deny-precedence/README.md) で実測済み)。

## 運用時の留意事項

- 広域 allow(`*.example.com` 等)の穴を特定ホストで塞ぐには deniedDomains を使う(denied が広域 allow に勝つ — c2/c3 で実測済み)。

## 試し方(本リポジトリでの実測)

### お手軽に試す(対話)

このディレクトリで `claude` を起動し、[prompt.ja.txt](./prompt.ja.txt) を貼り付けるだけ。allow に入っていても deny が勝ち、`NETMARKER.txt` が出来ないのが見える。

```bash
cd cases/S6-sandbox-network/c-denieddomains-precedence && claude
# → prompt.ja.txt を貼り付け
```

### ハーネスで実測する(結果の記録・プローブ独立)

```bash
python3 harness/run.py S6-sandbox-network/c-denieddomains-precedence
python3 harness/run.py -m sdk S6-sandbox-network/c-denieddomains-precedence
```

> probe=`network`。deny で拒否されるため SDK でも `SandboxNetworkAccess` 承認要求は発火しない(deny は prompt を経ず直接拒否)。

## 検証記録

| 日付 | バージョン | 実測したモダリティ |
|---|---|---|
| 2026-07-05 | v2.1.201 | headless / sdk(1プローブとも一致) |

## 対応する知識

- グループ [S6 README](../README.md)
- 関連: S6-b(allow のみ=到達)/ P2(permission の deny-first)
- 一次 docs: sandboxing(deniedDomains は広域 allow ワイルドカードにも優先)
