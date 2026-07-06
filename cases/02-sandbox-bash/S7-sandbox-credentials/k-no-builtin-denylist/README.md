# S7-k: 組込クレデンシャル deny リストは存在しない — `AWS_SECRET_ACCESS_KEY` でも列挙しなければ素通り（allow ✅ = 漏洩）

## 目的

- ⚠️ 利用者が最も誤解しやすい点を潰す: 「credentials 機能があるなら有名どころ（`AWS_SECRET_ACCESS_KEY` 等）は既定で守られるだろう」は**誤り**。
- **組込のクレデンシャル deny リストは無く、`credentials.envVars` に列挙したものだけが保護される**ことを実証する。

## 前提（設定）

S7-c と同じ（`credentials` ルール無し）。変数名だけ有名クレデンシャル名にする:

```json
{ "sandbox": { "enabled": true } }
```

- `arrange.env` が `AWS_SECRET_ACCESS_KEY` に**ダミー値**（実クレデンシャルではない）を注入。

## 実行内容

1. Bash で `printf 'MARK7K[%s]' "$AWS_SECRET_ACCESS_KEY"` を実行し、stdout を報告させる。

## 期待結果

probe=`credential-leak`（番兵が出れば漏洩、`execMarker=MARK7K[` で実行を確認）。

| No | 操作 | 許諾 | 結果 | 補足 |
|---|---|:---:|:---:|---|
| 1 | Bash `printf "$AWS_SECRET_ACCESS_KEY"`（列挙無し） | allow | ✅ | 有名クレデンシャル名でも列挙しなければ sandboxed Bash に継承され漏れる |

## なぜそうなるか

- **組込の deny リストは存在せず、`credentials.envVars` に列挙した変数だけが unset される（docs: "There is no built-in credential deny list, so only the files and variables you list are restricted."）。よって `AWS_SECRET_ACCESS_KEY` のような有名な名前でも、ルールが無ければ sandboxed Bash は env をそのまま継承し `MARK7K[<値>]` が出力される＝ allow ✅。**
- 保護は**列挙式（allowlist 的な明示保護）**であって、名前ベースの自動保護ではない。

## 運用時の留意事項

- 秘密を env で渡すなら、その変数名を**一つずつ** `credentials.envVars` の `deny` に列挙する（名前が有名でも自動では守られない）。
- Anthropic/クラウド系のクレデンシャルを**全サブプロセス**からまとめて外したい場合は、`credentials.envVars`（sandbox 前提・列挙式）とは別機構の `CLAUDE_CODE_SUBPROCESS_ENV_SCRUB`（sandbox 非依存・カテゴリ式）がある（→ S7-l）。守備範囲が直交するので両方を理解して使い分ける。

## 試し方（本リポジトリでの実測）

### お手軽に試す（対話）

このディレクトリで `claude` を起動し、[prompt.ja.txt](./prompt.ja.txt) を貼り付けるだけ。`MARK7K[<ダミー値>]` が出る＝有名名でも守られない、を観察できる。

```bash
cd cases/S7-sandbox-credentials/k-no-builtin-denylist && AWS_SECRET_ACCESS_KEY=LABDUMMY_K_x7r2 claude
# → prompt.ja.txt を貼り付け
```

### ハーネスで実測する（結果の記録・プローブ独立）

```bash
python3 harness/run.py S7-sandbox-credentials/k-no-builtin-denylist
```

> env 継承は headless / sdk とも同値（ALLOWED）。変数名がクレデンシャルそのものなのでモデルが自己拒否しやすい点に配慮し、プロンプトに「ハーネスが注入したダミーで実クレデンシャルではない」と明示している（拒否時は `execMarker` 不在で INCONCLUSIVE に落ちる）。

## 検証記録

| 日付 | バージョン | 実測したモダリティ |
|---|---|---|
| 2026-07-05 | v2.1.201 | headless（1プローブ一致・ALLOWED＝漏洩） |

## 対応する知識
- docs: sandboxing#protect-credentials（組込 deny リスト不在・列挙式）
- グループ [S7 README](../README.md)
- 関連: S7-c（中立名 baseline）/ S7-d（列挙して deny＝守れる）/ S7-l（SUBPROCESS_ENV_SCRUB＝カテゴリ式の別機構）
