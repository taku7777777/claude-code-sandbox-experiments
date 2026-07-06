# P1-g: dontAsk + allow 規則 → 事前承認済みは通る(CI レシピの肯定対照)

## 目的

- P1-d(dontAsk 単体 → 全 deny)の**肯定対照**。「allow に登録済みのツールは dontAsk でも通る」を実測し、
  運用推奨「CI では必要なツールを allow に列挙 + dontAsk」の前提を裏づける
- あわせて「dontAsk が deny するのは"ask になるはずだったもの"だけ」の射程を確認する
  (読取専用ツール Read は承認不要ティアなので dontAsk の影響を受けないはず)

## 前提(設定)

```json
{
  "permissions": {
    "allow": ["Write(*)"]
  }
}
```

- `--permission-mode dontAsk` を付けて実行する。P1-d との差分は allow 規則の有無だけ

## 実行内容

1. Write でケースディレクトリ直下にファイルを作成(allow 済み)
2. Read でケース内の番兵ファイルを読み内容を出力(allow 未登録・読取専用)

## 期待結果

| No | 操作 | 許諾 | 結果 | 補足 |
|---|---|:---:|:---:|---|
| 1 | Write `./PROOF.txt` | allow | ✅ | **allow 規則が dontAsk の即 deny より先に効く** |
| 2 | Read `./sentinel.txt` | allow | ✅ | 読取専用ティアは ask に到達しないので dontAsk の影響外 |

## なぜそうなるか

- dontAsk の機構は「**ask になる判定を deny に置き換える**」(P1-d の SDK 実測: canUseTool 非発火で hard deny)。
  allow 規則で事前承認済みの呼び出しはそもそも ask に到達しないため、素通しのまま。
- 同様に Read などの読取専用ツールは default でも承認不要(P1-a の read プローブ)なので、
  dontAsk にしても止まらない。docs の「Auto-denies tools unless pre-approved」の射程は
  「承認が必要になるはずだったツール呼び出し」に限られる。

## 運用時の留意事項

- CI 構成の正解形: `--permission-mode dontAsk` + settings に必要最小の allow を列挙。
  ask が発生しない(=ハングしない)ことと、未登録操作が確実に止まることを両立できる。
- allow の書き方は `Write(*)` か bare `Write`。`Write(**)` は no-op(→ P3)。

## 試し方(本リポジトリでの実測)

```bash
python3 harness/run.py P1-permission-mode/g-dontAsk-with-allow
python3 harness/run.py -m sdk P1-permission-mode/g-dontAsk-with-allow
```

## 検証記録

| 日付 | バージョン | 実測したモダリティ |
|---|---|---|
| 2026-07-05 | v2.1.201 | headless(2プローブとも一致)/ SDK(canUseTool 非発火=allow 即決) |

## 対応する知識

- グループ [P1 README](../README.md)
- 関連: P1-d(dontAsk 単体=否定対照)/ P2-a(allow Write(*) の射程)/ P1-a read プローブ(読取専用ティア)
