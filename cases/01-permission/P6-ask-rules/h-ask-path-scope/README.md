# P6-h: ⚠️ パス限定 ask 規則 `Write(sub/**)` は**無言で不一致** — 確認ゲートのつもりが素通り(P3 系地雷の ask 版)

## 目的

- パス限定の ask 規則(相対 dir + `**` 形)が効くかを実測で確定する(探索ケース → 実測済み)。
  docs に明文はなく、deny 側では効く報告(S9-a・ただし未確定フラグ付き)、allow 側では不一致の実測
  (P5-g 初回の副産物)があり、ask 側だけ空白だった
- **結論(実測)**: 効かない。「sub/ への書込だけ確認したい」という意図の ask は**存在しない**ことになり、
  同居する広い allow に落ちて**プロンプトなしで書ける**

## 前提(設定)

```json
{
  "permissions": {
    "allow": ["Write(*)"],
    "ask": ["Write(sub/**)"]
  }
}
```

- 広い allow の同居が本ケースの計器: 素の不一致は default モードでは結局 ask に落ちるため、
  「ask 規則がマッチした ask」と見分けがつかない。allow を同居させると
  **不一致 → allow(素通り)/ マッチ → ask が allow に勝つ(b で実測済みの機構)** に分岐し、
  結果だけでマッチの有無が確定する

## 実行内容

1. Write で `sub/PROBE.txt` を作成(ask 規則の対象のつもりのパス)
2. Write で `root-OK.txt` を作成(対照: sub/ の外)

## 期待結果(実測値。**意図した挙動ではない**)

| No | 操作 | 許諾 | 結果 | 補足 |
|---|---|:---:|:---:|---|
| 1 | Write `sub/PROBE.txt`(ask `Write(sub/**)` あり) | allow | ✅ | ⚠️ ask 規則が不一致で allow に素通り。SDK: askFired=[] |
| 2 | Write `root-OK.txt`(対照) | allow | ✅ | 広い allow は正常に機能 |

- **1 と 2 が同じ結果になる = ask 規則は何もしていない**。もし効いていれば 1 だけ ask になるはず
  (g の Bash specifier 版ではそう分岐した)。

## なぜそうなるか

- 実測: headless で ALLOWED(auto-deny されるべき ask が発生していない)、SDK で
  **canUseTool 非発火のまま副作用**(askFired=[] + sub/PROBE.txt 生成)。両形態とも
  「ask 規則がマッチしなかった」ことを構造的に示す。
- Write ツールの specifier は P3 グループで実測した glob 非対称(bare `**`・完全パス・単一星 dir・絶対パスが
  無言で不一致)を持ち、**ask 側もこの非対称の適用を受ける**ことが本ケースで確定した。
  allow 側(P5-g 副産物)・ask 側(本ケース)は相対 dir + `**` でも不一致。
  ※ deny 側の同形 `deny Write(dir/**)` も S9-a の 1 変数分離で **no-op と確定**(作成 5/5。0/5 ブロックの正体は同居 `deny Edit(dir/**)`)。
  つまり **deny/ask/allow どの規則種別でも Write の path 限定は効かない**。dir をツール層で締めるのは `Edit(dir/**)`(Write も覆うハード deny)。

## 運用時の留意事項

- ⚠️ **「このディレクトリへの書込だけ確認したい」を `ask: ["Write(dir/**)"]` で書いてはいけない**。
  エラーも警告も出ずに不一致になり、同居する allow があれば素通り、なければ全 Write が ask のまま
  (= ask 規則が何の差分も生まない)。
- 確認制にしたい実務上の代替:
  - ツール単位: `ask: ["Write(*)"]`(a で実測済み。ただし全 Write が確認になる)
  - 経路を Bash に限定できるなら Bash specifier(g で実測済み)
  - 保証された path マッチが要るなら **Edit 規則に寄せる**(P3-e: Edit 規則は Write ツールにも適用。
    ask Edit(path) が同様に効くかは未実測 — 次の探索候補)
- 「規則を書いた ≠ 効いている」(FINDINGS の deny 地雷と同じ教訓)。ask も撃って確かめる。

## 試し方(本リポジトリでの実測)

### お手軽に試す(対話)

```bash
cd cases/P6-ask-rules/h-ask-path-scope && claude
# → prompt.ja.txt を貼り付け。1 も 2 もプロンプトなしで書けてしまう(= ask 不発)ことを確認
```

### ハーネスで実測する(結果の記録・プローブ独立)

```bash
# ヘッドレス: 両プローブ ALLOWED(ask が発生していない)
python3 harness/run.py P6-ask-rules/h-ask-path-scope

# SDK: askFired=[] のまま副作用 → ALLOWED(不一致の構造的証拠)
python3 harness/run.py -m sdk P6-ask-rules/h-ask-path-scope
```

## 検証記録

| 日付 | バージョン | 実測したモダリティ |
|---|---|---|
| 2026-07-05 | v2.1.201 / SDK 0.3.200 | headless(1=ALLOWED / 2=ALLOWED)/ sdk(両プローブ ALLOWED・askFired=[]。全プローブ一致) |

- 探索ケースとして expected 未設定で実測 → 実測値(allow ✅)を expected に確定(2026-07-05)。
  この expected は「観測される挙動」であって「意図した挙動」ではない(アンチパターン記録)。

## 対応する知識

- グループ [P6 README](../README.md) / docs/FINDINGS.md: glob 地雷の章(ask 側の追記)
- 関連: P3(Write specifier の glob 非対称=同根)/ P5-g 副産物(allow 側 dir/** 不一致)/
  S9-a(deny 側 dir/** も no-op=反証、dir 保護は `Edit(dir/**)`)/ P6-g(効く specifier = Bash 版の対照)
