# S4-f: content-scoped ask(`Bash(touch *)`)は sandbox の auto-allow を**貫通してプロンプト強制**

## 目的

- docs の「content-scoped ask 規則は sandbox でもプロンプト強制」を実測する。
- S4-e(bare `Bash` ask は sandbox 実行分にスキップ)との**対の分岐**を確定する:
  auto-allow を貫通できるのは「内容を指定した ask」だけ。

## 前提(設定)

```json
{
  "sandbox": { "enabled": true },
  "permissions": { "ask": ["Bash(touch *)"] }
}
```

- docs の例示は `Bash(git push *)` だが機構は content-scoped ask 一般の話なので、P6-g で規則形の動作が
  実測済みの `Bash(touch *)` を使い、git remote の足場作りを避けた(1変数対照を優先)。

## 実行内容

1. Bash で `touch s4f-file.txt`(ask 規則の対象)
2. Bash で `echo data > inside.txt`(規則の対象外)

## 期待結果

| No | 操作 | 許諾 | 結果 | 補足 |
|---|---|:---:|:---:|---|
| 1 | Bash `touch s4f-file.txt` | ask | ✅ | **auto-allow 下でもプロンプト強制**(承認すれば完遂) |
| 2 | Bash `echo data > inside.txt` | allow | ✅ | 対象外は auto-allow のまま無プロンプト |

## なぜそうなるか

- content-scoped ask は「この内容のコマンドは確認したい」という明示の意思なので、sandbox 由来の
  auto-allow より強い(bare `Bash` ask が「sandbox 内なら確認不要」と解釈されるのと対照的 → S4-e)。
- P6-g(sandbox なしで `Bash(touch *)` ask が効く)に sandbox on を足しても ASK が残る、という
  1 変数の重ね合わせでもある。

## 運用時の留意事項

- **「広く auto-allow + 特定コマンドだけ確認」は content-scoped ask で書ける**(docs の想定形は
  `Bash(git push *)`)。sandbox 運用でも「push だけは人間が見る」のようなゲートが成立する。
- headless/CI ではこの ask は auto-deny = 対象コマンドは実行されずに止まる側へ倒れる。
- 同じ「hook で確認制に格上げ」という選択肢もある(→ P9-e)。規則で書けるなら規則が簡潔。

## 試し方(本リポジトリでの実測)

### お手軽に試す(対話)

このディレクトリで `claude` を起動し、[prompt.ja.txt](./prompt.ja.txt) を貼り付けるだけ。auto-allow 下で 1 だけ承認プロンプトが出る。

```bash
cd cases/S4-sandbox-autoallow-behavior/f-content-ask-forced && claude
```

### ハーネスで実測する(ask 系: SDK の canUseTool が決定的シグナル)

```bash
python3 harness/run.py S4-sandbox-autoallow-behavior/f-content-ask-forced
python3 harness/run.py -m sdk S4-sandbox-autoallow-behavior/f-content-ask-forced
```

## 検証記録

| 日付 | バージョン | 実測したモダリティ |
|---|---|---|
| 2026-07-05 | v2.1.201 / SDK 0.3.200 | headless(P1: DENIED=auto-deny / P2: ALLOWED)/ sdk(**P1: askFired=[Bash] で ASK** / P2: askFired 空で ALLOWED) |

## 対応する知識

- グループ [S4 README](../README.md) / S4 GAPS G5 の解消(spec §4.2 ③)
- 関連: S4-e(bare ask はスキップ=対の分岐)/ P6-g(`Bash(touch *)` ask の非 sandbox 実測)/ P9-e(hook で ask 化する別解)
