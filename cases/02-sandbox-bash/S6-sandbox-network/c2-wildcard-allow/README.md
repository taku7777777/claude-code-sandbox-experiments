# S6-c2: `allowedDomains` はワイルドカード `*.example.com` を受け付け、サブドメインへの egress が開く(`allow ✅`)= c3 の陽性対照

## 目的

- sandbox の `allowedDomains` で**ワイルドカード表記**(`*.example.com`)が機能し、サブドメイン(www.example.com)への egress が開くことを実測する。
- c3(wildcard allow + 特定ホスト deny)の**陽性対照**: これが ✅ にならないと c3 の ❌ を「deny の優先」と帰属できない。

## 前提(設定)

```json
{
  "sandbox": { "enabled": true, "allowUnsandboxedCommands": false,
    "network": { "allowedDomains": ["*.example.com"] } },
  "permissions": { "allow": ["Bash(*)"] }
}
```

- b(literal `example.com`)との違いは、allow エントリがワイルドカードで target がそのサブドメインである点。

## 実行内容

1. Bash で `curl https://www.example.com` を実行し、成功時だけ成功マーカー(`NETMARKER.txt`)を書く

## 期待結果

| No | 操作 | 許諾 | 結果 | 補足 |
|---|---|:---:|:---:|---|
| 1 | Bash `curl https://www.example.com` | allow | ✅ | `*.example.com` が www.example.com にマッチし egress が開く |

## なぜそうなるか

- **`allowedDomains` はワイルドカードをサポートする**(公式 docs にも `"allowedDomains": ["*.github.com", "registry.npmjs.org"]` の例)。`*.example.com` が www.example.com にマッチし、curl が到達して成功マーカーが出来る。

## 運用時の留意事項

- ワイルドカードは便利だが**開けすぎの典型**。`*.github.com` は gist や raw も含む。開ける範囲は必要最小にし、広域 allow の中の危険ホストは `deniedDomains` で個別に塞ぐ(→ c3 で実証)。

## 試し方(本リポジトリでの実測)

### お手軽に試す(対話)

このディレクトリで `claude` を起動し、[prompt.ja.txt](./prompt.ja.txt) を貼り付けるだけ。curl が到達して `NETMARKER.txt` が出来るのが見える。

```bash
cd cases/S6-sandbox-network/c2-wildcard-allow && claude
# → prompt.ja.txt を貼り付け
```

### ハーネスで実測する(結果の記録・プローブ独立)

```bash
python3 harness/run.py S6-sandbox-network/c2-wildcard-allow
python3 harness/run.py -m sdk S6-sandbox-network/c2-wildcard-allow
```

> probe=`network`(成功マーカー + 非 sandbox プリフライト=www.example.com)。この陽性対照がオフラインで INCONCLUSIVE になったら c3 の ❌ も信用しないこと。

## 検証記録

| 日付 | バージョン | 実測したモダリティ |
|---|---|---|
| 2026-07-05 | v2.1.201 | headless / sdk(1プローブとも一致) |

## 対応する知識

- グループ [S6 README](../README.md)
- 関連: S6-b(literal allow の陽性対照)/ S6-c3(+deny で ✅→❌)
- 一次 docs: sandboxing(allowedDomains のワイルドカード例 `*.github.com`。2026-07-05 確認)
