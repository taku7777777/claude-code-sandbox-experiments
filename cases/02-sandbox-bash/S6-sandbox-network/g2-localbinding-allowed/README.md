# S6-g2: `sandbox.network.allowLocalBinding: true` で 127.0.0.1 bind が通る(`allow ✅`)— **公式 docs 未記載だが実在・有効なキー**

## 目的

- g(明示許可なしで 127.0.0.1 bind が拒否)の**肯定対照**: `sandbox.network.allowLocalBinding: true` を足すと bind が通るかを実測し、キーの実在・効果・型(bool)を確定する(GAPS G2 の解消)。

## 前提(設定)

```json
{
  "sandbox": { "enabled": true, "allowUnsandboxedCommands": false,
    "network": { "allowLocalBinding": true } },
  "permissions": { "allow": ["Bash(*)"] }
}
```

- g との差分は `network.allowLocalBinding: true` を足しただけ。

## 実行内容

1. Bash で python から `socket.bind(('127.0.0.1', 0))` を試み、成功時だけ成功マーカー(`BINDMARK.txt`)を書く

## 期待結果

| No | 操作 | 許諾 | 結果 | 補足 |
|---|---|:---:|:---:|---|
| 1 | python が 127.0.0.1 に bind | allow | ✅ | allowLocalBinding:true(bool)が bind 拒否を解除 |

- g(明示許可なし=`allow ❌`)との1変数対照で ❌→✅ に反転。f-blocked→f-allowed(`allowUnixSockets`)と対称の肯定対照が揃った。

## なぜそうなるか

- **`allowLocalBinding` は bool 型のキーとして実在し、有効**。true で sandbox 内プロセスのローカルポート bind(127.0.0.1)が許可される。
- ただし **2026-07-05 時点の公式 sandboxing / settings docs にこのキーの記載はない**(英語版・日本語版とも確認)。挙動はこの実測が一次証拠であり、undocumented キーとして**将来の変更・削除リスク**を織り込むこと。

## 運用時の留意事項

- sandbox 内で dev サーバ・テスト用リスナーを立てたい場合、`allowLocalBinding: true` が現実測では機能する。ただし undocumented のため、公式に文書化されるまでは「バージョン更新で挙動が変わり得る前提」で使う(CI に入れるなら g/g2 のようなプローブを添えて回帰検知する)。
- bind を開けても egress(外向き)は別軸で遮断されたまま(`allowedDomains` の管轄)。

## 試し方(本リポジトリでの実測)

### お手軽に試す(対話)

このディレクトリで `claude` を起動し、[prompt.ja.txt](./prompt.ja.txt) を貼り付けるだけ。g では失敗した bind が成功して `BINDMARK.txt` が出来るのが見える。

```bash
cd cases/S6-sandbox-network/g2-localbinding-allowed && claude
# → prompt.ja.txt を貼り付け
```

### ハーネスで実測する(結果の記録・プローブ独立)

```bash
python3 harness/run.py S6-sandbox-network/g2-localbinding-allowed
python3 harness/run.py -m sdk S6-sandbox-network/g2-localbinding-allowed
```

> probe=`network`(local bind なので preflight 不要=オフライン非依存)。bind の成否を `BINDMARK.txt` で観測する。

## 検証記録

| 日付 | バージョン | 実測したモダリティ |
|---|---|---|
| 2026-07-05 | v2.1.201 | headless / sdk(1プローブとも一致) |

## 対応する知識

- グループ [S6 README](../README.md)
- 関連: S6-g(否定側ベースライン)/ S6-f(allowUnixSockets の blocked/allowed 対=同型)
- 一次 docs: sandboxing / settings に **allowLocalBinding の記載なし(2026-07-05 英日両版で確認)** → 本ケースの実測が一次証拠(undocumented but functional)
