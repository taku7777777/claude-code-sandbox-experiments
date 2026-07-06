# S6-a0: `network` キー省略(真の既定)でも egress は全ブロック(`allow ❌`)= `allowedDomains:[]` と観測上等価

## 目的

- 公式 docs のいう「既定」(= `sandbox.network` キーを**書かない**構成)で egress がどうなるかを実測する。
- S6-a は `allowedDomains: []` の**明示空リスト**であり、厳密には既定構成を測っていなかった。本ケースで「省略 = 空リスト」の等価性を1変数で確認する(GAPS G3(a) の解消)。

## 前提(設定)

```json
{
  "sandbox": { "enabled": true, "allowUnsandboxedCommands": false },
  "permissions": { "allow": ["Bash(*)"] }
}
```

- a との差分は `network` キーを丸ごと省略しただけ(f/g と同じ素の sandbox 構成に、a と同じ egress プローブを当てる)。

## 実行内容

1. Bash で `curl https://example.com` を実行し、成功時だけ成功マーカー(`NETMARKER.txt`)を書く

## 期待結果

| No | 操作 | 許諾 | 結果 | 補足 |
|---|---|:---:|:---:|---|
| 1 | Bash `curl https://example.com`(network キー省略) | allow | ❌ | 既定 = 事前許可ドメインなし。OS 層 egress が遮断(a と同じ) |

- a(`allowedDomains:[]`)と結果は同一。**省略と明示空リストは観測上等価**。

## なぜそうなるか

- **公式 docs の既定は「事前許可ドメインなし。初回要求時にプロンプト、承認はセッション中持続(v2.1.191+)」**。つまり既定の実体は「恒久ブロック」ではなく「都度承認」で、承認者がいない headless では auto-deny に落ちて全ブロックに見える。
- SDK では遮断が `canUseTool` の **`SandboxNetworkAccess` 承認要求として観測できる**(本ケースで発火を実測。既定 onAsk=deny → DENIED)。事前許可済みの b や明示 deny の c ではこの承認要求は発火しない。

## 運用時の留意事項

- 「sandbox にすればネットワークは全部止まる」は headless/CI での見え方。**対話では初回プロンプトを承認すれば同一ホストへセッション中つながる**(v2.1.191+)。恒久的に止めたいホストは `deniedDomains` に明示する(→ c/c3)。
- 逆に CI で必要なドメインは `allowedDomains` に事前列挙する(プロンプトに頼れないため)。

## 試し方(本リポジトリでの実測)

### お手軽に試す(対話)

このディレクトリで `claude` を起動し、[prompt.ja.txt](./prompt.ja.txt) を貼り付けるだけ。初回 network 承認プロンプトの挙動も観察できる。

```bash
cd cases/S6-sandbox-network/a0-true-default && claude
# → prompt.ja.txt を貼り付け
```

### ハーネスで実測する(結果の記録・プローブ独立)

```bash
python3 harness/run.py S6-sandbox-network/a0-true-default
python3 harness/run.py -m sdk S6-sandbox-network/a0-true-default
```

> probe=`network`(成功マーカー + 非 sandbox プリフライト)。SDK では `SandboxNetworkAccess` の ask 発火が観測される(a/d/e と同じ)。

## 検証記録

| 日付 | バージョン | 実測したモダリティ |
|---|---|---|
| 2026-07-05 | v2.1.201 | headless / sdk(1プローブとも一致。sdk は SandboxNetworkAccess 発火を確認) |

## 対応する知識

- グループ [S6 README](../README.md)
- 関連: S6-a(明示空リスト=同結果)/ S6-b(allowedDomains で開ける)
- 一次 docs: sandboxing「Domain restrictions: no domains are pre-allowed. The first time a command needs a new domain, Claude Code prompts for approval. As of v2.1.191, choosing Yes allows the host for the rest of the current session」(2026-07-05 確認)
