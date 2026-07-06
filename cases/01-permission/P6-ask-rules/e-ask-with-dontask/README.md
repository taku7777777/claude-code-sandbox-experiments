# P6-e: dontAsk では ask 規則は**プロンプトにならず即 deny** — 「ask は全モードでプロンプト」ではない

## 目的

- 明示 ask 規則のモード掃引の残り(dontAsk)を実測で確定する。docs は「dontAsk では明示 ask 規則は
  **プロンプトにならず deny される**」と明記しており、a/c/d(default/acceptEdits/bypass = プロンプト)
  とは**解決のされ方が別物**であることを示す
- グループのこれまでの結論「ask はあらゆる圧力を跳ね返す(プロンプトが残る)」の適用範囲を正しく限定する

## 前提(設定)

```json
{
  "permissions": {
    "ask": ["Write(*)"]
  }
}
```

- a と同一の ask 規則。差分は `--permission-mode dontAsk` のみ(a → e はモードだけの1変数対照)

## 実行内容

1. Write で `PROOF.txt` を作成(dontAsk)

## 期待結果

| No | 操作 | 許諾 | 結果 | 補足 |
|---|---|:---:|:---:|---|
| 1 | Write `PROOF.txt`(ask 規則 + dontAsk) | deny | - | プロンプト機会なしの即 deny。canUseTool 非発火 |

- a/c/d の同じ規則・同じプローブは **ask**(SDK で canUseTool 発火)。e だけ **deny**(非発火)。

## なぜそうなるか

- **dontAsk は「プロンプトになるはずのものを全部 deny に倒す」モード**で、明示 ask 規則は定義上
  プロンプト行きなので deny になる(公式 permission-modes: "explicit `ask` rules **are denied rather
  than prompting**")。
- 「ask 規則は無視されて allow に落ちる」のでも「プロンプトが出る」のでもない。**素通りはしない**
  (承認なしに書けるわけではない)が、**承認の機会もない**。
- P5-g(dontAsk × 保護パス)と同じ機構: dontAsk では「ask 系」が一律 deny に解決される。

## 運用時の留意事項

- 「危険操作に ask を置いて確認制にする」設計は、**dontAsk 運用(CI 等)ではその操作が常に失敗する**
  という意味になる。確認ではなく遮断が起きる — それが意図(CI で危険操作を封じる)なら好都合、
  「CI では自動承認されるだろう」と思っていたなら誤解。
- モード別の ask 規則の解決: default/acceptEdits/plan/**bypass** = プロンプト(a/c/d)/
  **dontAsk = deny**(本ケース)/ auto = プロンプト強制(docs 明記・本環境では対象外)。

## 試し方(本リポジトリでの実測)

### お手軽に試す(対話)

```bash
cd cases/P6-ask-rules/e-ask-with-dontask && claude --permission-mode dontAsk
# → prompt.ja.txt を貼り付け。プロンプトが出ずに即拒否されることを確認
```

### ハーネスで実測する(結果の記録・プローブ独立)

deny 系(非 ask)なので結論は全形態で同じだが、**a/c/d の ASK との対照は SDK が計測器**
(canUseTool 非発火 = プロンプト機会なし)。

```bash
# ヘッドレス: 即 deny → DENIED(denials=['Write'] = 呼び出し時 deny)
python3 harness/run.py P6-ask-rules/e-ask-with-dontask

# SDK: canUseTool 非発火 + denial → DENIED_HARD(a/c/d は同条件で ASK)
python3 harness/run.py -m sdk P6-ask-rules/e-ask-with-dontask
```

## 検証記録

| 日付 | バージョン | 実測したモダリティ |
|---|---|---|
| 2026-07-05 | v2.1.201 / SDK 0.3.200 | headless(DENIED・denials=['Write'] = 呼び出し時 deny)/ sdk(DENIED_HARD・canUseTool 非発火。1プローブ一致) |

## 対応する知識

- グループ [P6 README](../README.md) / 公式 permission-modes「dontAsk」節
- 関連: P6-a/c/d(同じ規則がプロンプトになるモード群=対照)/ P5-g(dontAsk × 保護パス = 同機構)/
  P1-d・P1-g(dontAsk の基準挙動)
