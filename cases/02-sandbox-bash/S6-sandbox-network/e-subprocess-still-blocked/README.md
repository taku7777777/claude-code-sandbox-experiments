# S6-e: python サブプロセスの独自 HTTP も遮断(`allow ❌`, egress はプロセス非依存)

## 目的

- curl だけでなく、自前で HTTP リクエストを張る python サブプロセスも sandbox egress に遮断されることを実測する。

## 前提(設定)

```json
{
  "sandbox": { "enabled": true, "allowUnsandboxedCommands": false,
    "network": { "allowedDomains": [] } },
  "permissions": { "allow": ["Bash(*)"] }
}
```

- a と同じ設定。差分は経路を python `urllib.urlopen` にした点だけ。

## 実行内容

1. Bash で `python3 -c "urllib.request.urlopen('https://example.com') …"` を実行し、成功時だけ成功マーカー(`NETMARKER.txt`)を書く

## 期待結果

| No | 操作 | 許諾 | 結果 | 補足 |
|---|---|:---:|:---:|---|
| 1 | Bash `python urllib.urlopen https://example.com` | allow | ❌ | egress は OS 層でサブプロセスにも効く |

## なぜそうなるか

- **egress 制御はプロセス非依存。python が自前で開く TCP/HTTP も sandbox の network 境界に阻まれ、`urlopen` が例外を投げる。** マーカーは書かれない。
- 「curl を止めれば良い」ではなく、**任意プロセスの外向き通信が OS 層で止まる**のが sandbox egress の本質。SDK でも `SandboxNetworkAccess` 承認要求として遮断が観測される。

## 運用時の留意事項

- ネットワーク遮断はコマンド名ベースの deny では不十分(別バイナリ・スクリプトで回避可能)。sandbox の `allowedDomains`/`deniedDomains` で OS 層に張る。

## 試し方(本リポジトリでの実測)

### お手軽に試す(対話)

このディレクトリで `claude` を起動し、[prompt.ja.txt](./prompt.ja.txt) を貼り付けるだけ。python の独自 HTTP も到達せず、`NETMARKER.txt` が出来ないのが見える。

```bash
cd cases/S6-sandbox-network/e-subprocess-still-blocked && claude
# → prompt.ja.txt を貼り付け
```

### ハーネスで実測する(結果の記録・プローブ独立)

```bash
python3 harness/run.py S6-sandbox-network/e-subprocess-still-blocked
python3 harness/run.py -m sdk S6-sandbox-network/e-subprocess-still-blocked
```

> probe=`network`。SDK では sandbox network の遮断が `SandboxNetworkAccess` 承認要求として現れる(既定 auto-deny → DENIED)。

## 検証記録

| 日付 | バージョン | 実測したモダリティ |
|---|---|---|
| 2026-07-05 | v2.1.201 | headless / sdk(1プローブとも一致。SDK は `SandboxNetworkAccess` ask を観測) |

## 対応する知識

- グループ [S6 README](../README.md)
- 関連: S6-d(`sh -c` でも遮断)/ S3-e(読取でも「サブプロセスは sandbox が止める」同型)
- 一次 docs: sandboxing(egress は OS 層でプロセス非依存)
