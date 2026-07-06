# P2-e: deny `Bash(*)` + allow `Bash(echo:*)` → ネストした allow では deny に穴を開けられない

## 目的

- 広い deny の内側に狭い allow を書いたとき、**allow が deny に穴を開け直せるか**を確認する
  (評価順 deny → ask → allow の「具体性は順序を変えない」の実測)
- P2-b(同一スコープ)・P4-a(deny が allow より狭い)と合わせて、スコープの包含関係3パターンを完成させる

## 前提(設定)

```json
{
  "permissions": {
    "allow": ["Bash(echo:*)"],
    "deny":  ["Bash(*)"]
  }
}
```

- Bash 規則を使う理由: プレフィックスマッチが実際に効くため(**Write 規則ではパス限定が表現できず、
  ネスト構成をそもそも作れない** → P3-d)
- allow は `echo` コマンドだけを明示的に許可し、deny は Bash 全体を塞ぐ「deny の中の allow」構成

## 実行内容

1. Bash で `echo`(allow が明示するコマンド)を実行してファイルを作成
2. Bash で `pwd`(allow に無いコマンド)を実行してファイルを作成
3. Write でケースディレクトリ直下にファイルを作成(Bash 規則の外側の対照)

## 期待結果

| No | 操作 | 許諾 | 結果 | 補足 |
|---|---|:---:|:---:|---|
| 1 | Bash `echo ok > BASHPROOF.txt` | deny | - | **明示 allow があっても deny が勝つ**(穴は開かない) |
| 2 | Bash `pwd > PWDPROOF.txt` | deny | - | - |
| 3 | Write `./PROOF.txt` | ask | ✅ | Bash の deny は Write に波及しない(規則はツール単位) |

- 1 が判別プローブ: ネスト allow が効くなら ✅ になるはずが、deny のハードブロック(SDK で
  canUseTool 発火なしの DENIED_HARD)。**deny の内側に allow で例外は作れない**。

## なぜそうなるか

- 評価順は **deny → ask → allow で最初のマッチが勝ち、規則の具体性(狭さ)は順序を変えない**。
  `Bash(*)` の deny がすべての Bash 呼び出しに先にマッチするため、`Bash(echo:*)` の allow は
  一度も参照されない。
- sandbox 層の S2-g(広い allowWrite + 内側 denyWrite → deny が勝ち再 allow 不可)と同じ構造が
  permission 層にもある。**「deny してから例外を allow で戻す」設計はどちらの層でも成立しない**。
- 逆方向(広い allow + 狭い deny)は成立する(→ P4-a: allow `Bash(*)` + deny `Bash(curl:*)` で
  curl だけ止まる)。例外を作れるのは deny 側だけ。

## 運用時の留意事項

- **許可リストは「基本 deny + 例外 allow」では書けない**。例外を作りたい方向に合わせて、
  「基本 allow(広め)+ 禁止 deny(狭め)」の形にする(→ P4-a)。
- 「Bash は原則禁止、echo だけ許したい」場合は deny `Bash(*)` をやめ、allow に `Bash(echo:*)` だけを
  書いて他を ask/deny に落とす(dontAsk 併用で完全非対話にもできる → P1-d)。

## 試し方(本リポジトリでの実測)

### お手軽に試す(対話)

このディレクトリで `claude` を起動し、[prompt.ja.txt](./prompt.ja.txt) の内容を貼り付けるだけ。
明示 allow したはずの echo までプロンプトなしで拒否され、Write だけ承認プロンプトが出ることが
その場で確認できる。

```bash
cd cases/P2-allow-deny-precedence/e-nested-allow-cannot-reopen-deny && claude
# → prompt.ja.txt を貼り付け
```

### ハーネスで実測する(結果の記録・プローブ独立)

プローブ3(Write)が ask 系。SDK では deny(発火せず)と ask(発火)が構造的に分かれる。

```bash
python3 harness/run.py P2-allow-deny-precedence/e-nested-allow-cannot-reopen-deny
python3 harness/run.py -m sdk P2-allow-deny-precedence/e-nested-allow-cannot-reopen-deny
```

> Bash プローブのプロンプトは**他ツールへのフォールバックを禁止**している(deny の観測を汚さないため)。

## 検証記録

| 日付 | バージョン | 実測したモダリティ |
|---|---|---|
| 2026-07-05 | v2.1.201 | headless / sdk(3プローブとも一致) |

## 対応する知識

- 関連: P2-b(同一スコープの deny > allow)/ P4-a(広い allow + 狭い deny は成立する=逆方向)/
  P3-d(Write ではネスト構成が表現できない)/ S2-g(sandbox 層の同型: nested deny wins)
