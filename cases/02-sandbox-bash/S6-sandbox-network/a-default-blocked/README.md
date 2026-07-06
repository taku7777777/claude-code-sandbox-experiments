# S6-a: sandbox network は既定で全ブロック → Bash curl は permission を通っても OS 層で遮断(allow ❌)

## 目的

- `sandbox.enabled` かつ `allowedDomains:[]` のとき、egress が既定で全ブロックされることを確認する(S6 のベースライン)
- permission は通る(`Bash(*)` allow)のに OS 層で止まる= **`allow ❌`** の典型を示す

## 前提(設定)

```json
{
  "sandbox": {
    "enabled": true,
    "allowUnsandboxedCommands": false,
    "network": { "allowedDomains": [] }
  },
  "permissions": { "allow": ["Bash(*)"] }
}
```

- `allowUnsandboxedCommands:false` で非 sandbox フォールバックを封じ、**sandbox network 層だけ**を測る
- `allow Bash(*)` で permission をゲートにしない(sandboxed 実行は auto-allow)

## 実行内容

1. Bash で example.com に curl し、成功時のみ到達マーカーを作る

## 期待結果

probe=`network`(非 sandbox プリフライトで example.com 到達を確認 → 届けば判定続行、届かなければ INCONCLUSIVE。成功マーカーの有無で到達判定)

| No | 操作 | 許諾 | 結果 | 補足 |
|---|---|:---:|:---:|---|
| 1 | Bash: `curl https://example.com` | allow | ❌ | permission は通るが OS 層 egress で実行時に遮断 |

- `allow ❌` = permission エンジンは Bash を通した(auto-allow)が、sandbox(OS 層)が接続を止めた。curl は接続段階で失敗し、成功マーカーは作られない。

## なぜそうなるか

- **sandbox を有効化するとネットワークは既定で全ブロック。`allowedDomains` に何も無ければ、どのドメインにも到達できない。** これは Bash とその子プロセスに OS 層で適用される(プロセス非依存 → S6-d/e)。
- 対照: 許可ドメインを1つ入れれば到達する(S6-b が陽性対照)。

## 運用時の留意事項

- 必要なドメインは `allowedDomains` に列挙する(→ S6-b)。CI の依存取得(registry 等)はこれで最小許可する。
- 「本当にネットワークを止めたい」なら permission の文字列 deny ではなくこの sandbox network 層で張る(→ P4-c と対照)。

## 試し方(本リポジトリでの実測)

### お手軽に試す(対話)

このディレクトリで sandbox 有効の `claude` を起動し、[prompt.ja.txt](./prompt.ja.txt) の内容を貼り付けるだけ。
curl が接続段階で失敗し到達マーカーが作られないことがその場で確認できる。

```bash
cd cases/S6-sandbox-network/a-default-blocked && claude
# → prompt.ja.txt を貼り付け
```

### ハーネスで実測する(結果の記録・プローブ独立)

```bash
python3 harness/run.py S6-sandbox-network/a-default-blocked
python3 harness/run.py -m sdk S6-sandbox-network/a-default-blocked
```

> probe=`network`。**非 sandbox プリフライト**(素の curl で example.com 到達を確認)を先に行い、
> オフライン時は INCONCLUSIVE に落とす(sandbox 遮断との誤判定を防ぐ)。到達判定は成功マーカーの有無。

## 検証記録

| 日付 | バージョン | 実測したモダリティ |
|---|---|---|
| 2026-07-05 | v2.1.201 | headless / sdk |

## 対応する知識

- グループ [S6 README](../README.md)
- 関連: S6-b(allowedDomains で開ける・陽性対照)/ S6-d,e(プロセス非依存)/ S6-h(WebFetch は迂回)
