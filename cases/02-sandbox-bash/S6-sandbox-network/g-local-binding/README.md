# S6-g: sandbox は local ポートの bind も既定で遮断(`allow ❌`, 127.0.0.1 bind が PermissionError)

## 目的

- sandbox が egress(外向き)だけでなく、ローカルループバック(127.0.0.1)へのポート bind も既定で拒否することを実測する。

## 前提(設定)

```json
{
  "sandbox": { "enabled": true, "allowUnsandboxedCommands": false },
  "permissions": { "allow": ["Bash(*)"] }
}
```

- baseline(明示許可なし)で 127.0.0.1 の bind が通るかを見る。

## 実行内容

1. Bash で python から `socket.bind(('127.0.0.1', 0))` を試み、成功時だけ成功マーカー(`BINDMARK.txt`)を書く

## 期待結果

| No | 操作 | 許諾 | 結果 | 補足 |
|---|---|:---:|:---:|---|
| 1 | python が 127.0.0.1 に bind | allow | ❌ | sandbox network policy が local bind を拒否(`Operation not permitted`) |

## なぜそうなるか

- **sandbox のネットワーク制限は egress(外向き)だけでなくローカルポートの bind も既定で拒否する。** `s.bind(('127.0.0.1',0))` が `PermissionError`(実測 `result_text` は `Operation not permitted`)を投げ、成功マーカーは書かれない。

## 運用時の留意事項

- dev サーバ・ローカルプロキシ・docker デーモン等を sandbox 内で立てるには、Terminal 層(sandbox の外)で起動するか、`sandbox.network.allowLocalBinding: true` を使う。**このキーは 2026-07-05 時点の公式 docs(英日両版)に記載がないが、[g2](../g2-localbinding-allowed/README.md) の実測で実在・有効(bool)を確定済み**(undocumented のため将来の変更リスクは織り込むこと)。

## 試し方(本リポジトリでの実測)

### お手軽に試す(対話)

このディレクトリで `claude` を起動し、[prompt.ja.txt](./prompt.ja.txt) を貼り付けるだけ。127.0.0.1 への bind が `Operation not permitted` で失敗し `BINDMARK.txt` が出来ないのが見える。

```bash
cd cases/S6-sandbox-network/g-local-binding && claude
# → prompt.ja.txt を貼り付け
```

### ハーネスで実測する(結果の記録・プローブ独立)

```bash
python3 harness/run.py S6-sandbox-network/g-local-binding
python3 harness/run.py -m sdk S6-sandbox-network/g-local-binding
```

> probe=`network`(local bind なので preflight 不要=オフライン非依存)。bind の成否を `BINDMARK.txt` で観測する。

## 検証記録

| 日付 | バージョン | 実測したモダリティ |
|---|---|---|
| 2026-07-05 | v2.1.201 | headless / sdk(1プローブとも一致) |

## 対応する知識

- グループ [S6 README](../README.md)
- 関連: S6-a(egress 既定ブロック)/ S6-g2(allowLocalBinding:true の肯定対照=❌→✅)
- 一次 docs: sandboxing(local binding の可否は明記なし。allowLocalBinding は公式未記載 — 実在・効果は g2 の実測が一次証拠)
