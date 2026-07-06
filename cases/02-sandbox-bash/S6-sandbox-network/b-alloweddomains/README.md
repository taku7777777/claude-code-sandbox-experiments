# S6-b: `allowedDomains` が egress を1本開ける。Bash curl が到達(`allow ✅`)= 本グループの陽性対照

## 目的

- `allowedDomains:["example.com"]` を足すと、そのドメインへの Bash egress が通ることを実測する。
- **本グループの陽性対照**: これが到達するからこそ、a/c/d/e の `allow ❌` は「書込失敗」ではなく真のネットワーク遮断だと確定できる。

## 前提(設定)

```json
{
  "sandbox": { "enabled": true, "allowUnsandboxedCommands": false,
    "network": { "allowedDomains": ["example.com"] } },
  "permissions": { "allow": ["Bash(*)"] }
}
```

- a との差分は `allowedDomains` に `"example.com"` を1つ足しただけ。

## 実行内容

1. Bash で `curl https://example.com` を実行し、成功時だけ成功マーカー(`NETMARKER.txt`)を書く

## 期待結果

| No | 操作 | 許諾 | 結果 | 補足 |
|---|---|:---:|:---:|---|
| 1 | Bash `curl https://example.com`(target 到達) | allow | ✅ | allowedDomains の許可エントリで egress が開く |

- a(`allowedDomains:[]`=`allow ❌`)との差分は allowedDomains だけで、結果が ❌→✅ に反転する。

## なぜそうなるか

- **`allowedDomains` は egress のホワイトリスト。挙げた1ドメインへの sandboxed curl が通り、成功マーカーが出来る。** 事前許可済みなので SDK でも `SandboxNetworkAccess` 承認要求は発火しない(a/d/e とは対照)。

## 運用時の留意事項

- 出力先は cwd にする(sandbox の tmp 書込は `/tmp/claude`・`$TMPDIR`・cwd 限定。任意 `/tmp/foo` は拒否 → 偽陰性の原因)。
- 許可は最小に。ワイルドカード(`*.github.com` 等)は必要範囲だけ。

## 試し方(本リポジトリでの実測)

### お手軽に試す(対話)

このディレクトリで `claude` を起動し、[prompt.ja.txt](./prompt.ja.txt) を貼り付けるだけ。curl が到達して `NETMARKER.txt` が出来るのが見える。

```bash
cd cases/S6-sandbox-network/b-alloweddomains && claude
# → prompt.ja.txt を貼り付け
```

### ハーネスで実測する(結果の記録・プローブ独立)

```bash
python3 harness/run.py S6-sandbox-network/b-alloweddomains
python3 harness/run.py -m sdk S6-sandbox-network/b-alloweddomains
```

> sandbox(OS 層)の egress を観測するケース(probe=`network`、成功マーカー + 非 sandbox プリフライトで判定)。**この陽性対照がオフラインで INCONCLUSIVE になったらグループ全体がオフライン**のシグナル(遮断ケースの `allow ❌` を信用してはいけない)。

## 検証記録

| 日付 | バージョン | 実測したモダリティ |
|---|---|---|
| 2026-07-05 | v2.1.201 | headless / sdk(1プローブとも一致) |

## 対応する知識

- グループ [S6 README](../README.md)(b=陽性対照)
- 関連: S6-a(既定ブロック)/ S6-c(denied 優先で ✅→❌)
- 一次 docs: sandboxing(allowedDomains = egress allowlist)
