# S6-c3: `deniedDomains` の特定ホストは**広域 allow ワイルドカードにも勝つ**(`allow ❌`)— 「広い allow の穴を deny で塞ぐ」の実証

## 目的

- docs の「deniedDomains は広い `allowedDomains` ワイルドカードが許可する場合でも特定ドメインをブロックする」を、literal 同一衝突(c)ではなく **wildcard allow × literal deny の交差**で実測する(GAPS G5 の解消)。

## 前提(設定)

```json
{
  "sandbox": { "enabled": true, "allowUnsandboxedCommands": false,
    "network": { "allowedDomains": ["*.example.com"],
                 "deniedDomains": ["www.example.com"] } },
  "permissions": { "allow": ["Bash(*)"] }
}
```

- c2(wildcard allow のみ=到達)との差分は `deniedDomains:["www.example.com"]` を足しただけ。

## 実行内容

1. Bash で `curl https://www.example.com` を実行し、成功時だけ成功マーカー(`NETMARKER.txt`)を書く

## 期待結果

| No | 操作 | 許諾 | 結果 | 補足 |
|---|---|:---:|:---:|---|
| 1 | Bash `curl https://www.example.com` | allow | ❌ | www は `*.example.com` にマッチするが deny の特定ホストが優先 |

- c2(deny なし=`allow ✅`)との1変数対照で、❌ の原因を deny に帰属できる。

## なぜそうなるか

- **deniedDomains は allowedDomains より優先され、広域ワイルドカード allow の内側でも特定ホストを塞げる**(deny-first)。permission 規則の deny 優先(P2-b)と同じ設計原理が sandbox network 層にもある。
- c(literal 同一ホスト衝突)と合わせて、「同一 literal」「wildcard×literal 交差」の両形で deny 優先が確定した。

## 運用時の留意事項

- `*.github.com` のような広域 allow を使うときは、流出先になり得るホスト(例: gist.github.com 等)を `deniedDomains` で個別に塞ぐ運用が実際に機能する。
- ただし deny はクライアント申告ホスト名で判定される(既定で TLS 非終端)。domain-fronting 耐性が要るなら `network.tlsTerminate`(実験的・v2.1.199+・user/managed/`--settings` スコープのみ)を検討(→ グループ README 要点)。

## 試し方(本リポジトリでの実測)

### お手軽に試す(対話)

このディレクトリで `claude` を起動し、[prompt.ja.txt](./prompt.ja.txt) を貼り付けるだけ。curl が遮断され `NETMARKER.txt` が出来ないのが見える。

```bash
cd cases/S6-sandbox-network/c3-wildcard-deny-precedence && claude
# → prompt.ja.txt を貼り付け
```

### ハーネスで実測する(結果の記録・プローブ独立)

```bash
python3 harness/run.py S6-sandbox-network/c3-wildcard-deny-precedence
python3 harness/run.py -m sdk S6-sandbox-network/c3-wildcard-deny-precedence
```

> probe=`network`(成功マーカー + 非 sandbox プリフライト=www.example.com)。**必ず c2(陽性対照)とセットで見る**。SDK でも `SandboxNetworkAccess` の ask は発火しない(明示 deny は即遮断=c と同型)。

## 検証記録

| 日付 | バージョン | 実測したモダリティ |
|---|---|---|
| 2026-07-05 | v2.1.201 | headless / sdk(1プローブとも一致) |

## 対応する知識

- グループ [S6 README](../README.md)
- 関連: S6-c2(陽性対照)/ S6-c(literal 同一衝突の deny 優先)/ P2-b(permission 層の deny-first)
- 一次 docs: sandboxing「Sandbox `deniedDomains`: Blocks specific domains even when a broader `allowedDomains` wildcard would otherwise permit them」(2026-07-05 確認)
