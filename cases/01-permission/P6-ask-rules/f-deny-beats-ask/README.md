# P6-f: deny は ask に勝つ — 評価順 deny → ask → allow の上側の辺を実測で確定

## 目的

- 3 値評価順のうち未実測だった **deny > ask** の辺を実測で埋める(deny > allow = P2-b /
  ask > allow = P6-b は実測済み。本ケースで 3 辺すべてが実測になる)
- 副次観測: ask が同居しても deny Write(*) が**ツール除去型**で現れるか(allow 同居の P2-b は
  呼び出し時 deny だった)

## 前提(設定)

```json
{
  "permissions": {
    "deny": ["Write(*)"],
    "ask": ["Write(*)"]
  }
}
```

- b(allow + ask)の allow を deny に差し替えた 1 変数対照。モード指定なし(default)

## 実行内容

1. Write で `PROOF.txt` を作成

## 期待結果

| No | 操作 | 許諾 | 結果 | 補足 |
|---|---|:---:|:---:|---|
| 1 | Write `PROOF.txt`(deny + ask 同居) | deny | - | deny が先に当たり ask は評価されない。canUseTool 非発火 |

## なぜそうなるか

- **評価順は deny → ask → allow で、最初にマッチした規則で確定する**(公式 permissions:
  "Rules are evaluated in order: deny, then ask, then allow. The first match in that order determines
  the outcome")。deny にマッチした時点で ask は見られない。
- b(allow + ask → ask 勝ち・canUseTool 発火)との対照で、「ask は allow より強く deny より弱い」
  という 3 値の中間位置が両側から実測で確定する。
- **副次観測(実測)**: ask が同居していても `deny Write(*)` は**ツール除去型**で現れた
  (headless: denials 空・init tools から Write が欠落 → 構造検出で DENIED)。allow が同居する
  P2-b では呼び出し時 deny(denials 記録)だったので、**ツールをコンテキストに残すのは allow の
  同居であって ask の同居ではない**、という細部が新たに分かった。

## 運用時の留意事項

- 「deny した上で、通す場合は確認したい」という意図で deny と ask を並べても、**ask は死ぬ**
  (deny が常に先勝ち)。確認制にしたいなら deny を外して ask だけを置く。
- deny(ハード遮断・承認の余地なし)と ask(承認すれば通る)は排他的に設計する。
  同一 specifier への同居は誤設定のシグナル。

## 試し方(本リポジトリでの実測)

### お手軽に試す(対話)

```bash
cd cases/P6-ask-rules/f-deny-beats-ask && claude
# → prompt.ja.txt を貼り付け。プロンプトが出ずに拒否される(Write ツール自体が
#   使えないと報告される場合もある = ツール除去型)ことを確認
```

### ハーネスで実測する(結果の記録・プローブ独立)

deny 系(非 ask)なので結論は全形態で同じ。b の ASK との対照は SDK が計測器。

```bash
# ヘッドレス: DENIED(denials 空 + init tools 欠落 = ツール除去型の構造検出)
python3 harness/run.py P6-ask-rules/f-deny-beats-ask

# SDK: canUseTool 非発火 → DENIED_HARD(b は同条件で ASK・発火)
python3 harness/run.py -m sdk P6-ask-rules/f-deny-beats-ask
```

## 検証記録

| 日付 | バージョン | 実測したモダリティ |
|---|---|---|
| 2026-07-05 | v2.1.201 / SDK 0.3.200 | headless(DENIED・denials 空=ツール除去を init tools 欠落で構造検出)/ sdk(DENIED_HARD・canUseTool 非発火。1プローブ一致) |

## 対応する知識

- グループ [P6 README](../README.md) / 公式 permissions「Manage permissions」(評価順)
- 関連: P6-b(allow + ask → ask 勝ち=対照)/ P2-b(deny + allow → deny 勝ち・呼び出し時 deny)/
  P2-c/d(deny 単独=ツール除去型)
