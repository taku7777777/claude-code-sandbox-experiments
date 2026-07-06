# S2-i: deny 領域内の明示 `allowWrite` は効かない — write 側に `allowRead` 相当の再許可は無い(deny 常勝)

## 目的

- g(広 allow + 内 deny → deny 勝ち)より 1 段強い主張 **「deny 領域の内側は再 allow でも開けられない」**
  を実測で決着させる(公式 docs 未記載・read 側の `allowRead` とは対称でない可能性があった)。
- g README の(当時は未検証だった)断定「再 allow を入れても効かない」を実測に昇格させる。

## 前提(設定)

```json
{
  "sandbox": {
    "enabled": true,
    "filesystem": {
      "allowWrite": ["~/lab-nest", "~/lab-nest/sub/inner"],
      "denyWrite":  ["~/lab-nest/sub"]
    }
  }
}
```

- g への 1 変数差分: `allowWrite` に **deny 領域の内側を名指しする `~/lab-nest/sub/inner`** を追加。

## 実行内容

1. Bash で `~/lab-nest/sub/inner/f.txt`(deny 領域内・再 allow 対象)に書込
2. Bash で `~/lab-nest/f.txt`(allow 領域の外周・deny 対象外)に書込

## 期待結果

| No | 操作 | 許諾 | 結果 | 補足 |
|---|---|:---:|:---:|---|
| 1 | Bash `echo > ~/lab-nest/sub/inner/f.txt` | allow | ❌ | **名指しの再 allow が無効**(EPERM)= deny 常勝 |
| 2 | Bash `echo > ~/lab-nest/f.txt` | allow | ✅ | allowWrite 自体は生きている(対照) |

## なぜそうなるか

- sandbox FS の write 側では **deny が常に勝つ**: 広い allow に対してだけでなく(g)、deny 領域の内側を
  **名指しで再 allow しても**開かない(本ケース)。
- **read 側とは非対称**: read には `allowRead` = denyRead 領域内の再許可が公式に存在し効く(S3-b)。
  write 側に同型の仕組みは無い(docs 未記載 → 本ケースで実測決着)。
- 「例外を彫れる向き」は write 側では「広 allow + 狭 deny」だけ(g)。deny の中に allow の島は作れない。

## 運用時の留意事項

- 「`~/data` は全部禁止、ただし `~/data/out` だけ書かせたい」は **denyWrite では書けない**。
  allowWrite を `~/data/out` だけに絞る(deny を使わない)設計に倒す。
- read 側(`allowRead`)の感覚で write 側を設定すると意図せず全滅する。層(read/write)で再許可の
  有無が違うことを覚えておく。

## 試し方(本リポジトリでの実測)

### お手軽に試す(対話)

このディレクトリで `claude` を起動し、[prompt.ja.txt](./prompt.ja.txt) を貼り付けるだけ。名指しの再 allow があるのに 1 が `operation not permitted` になるのが見える。

```bash
cd cases/S2-sandbox-fs-write/i-reallow-inside-deny && claude
```

### ハーネスで実測する

```bash
python3 harness/run.py S2-sandbox-fs-write/i-reallow-inside-deny
python3 harness/run.py -m sdk S2-sandbox-fs-write/i-reallow-inside-deny
```

## 検証記録

| 日付 | バージョン | 実測したモダリティ |
|---|---|---|
| 2026-07-05 | v2.1.201 / SDK 0.3.200 | headless / sdk(2プローブとも一致。EPERM 文言 evidenceFound=true) |

## 対応する知識

- docs/FINDINGS.md: Q2 / グループ [S2 README](../README.md) / S2 GAPS G2 の解消(【要裏取り】→実測決着)
- 関連: S2-g(広 allow + 内 deny = 前提ケース)/ S3-b(read 側の allowRead は再許可が**効く**=非対称の相手)/ S2-d(denyWrite の破壊力)
