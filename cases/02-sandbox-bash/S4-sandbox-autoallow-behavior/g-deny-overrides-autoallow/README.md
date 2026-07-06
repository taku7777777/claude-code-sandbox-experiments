# S4-g: 明示 deny 規則は sandbox の auto-allow に**勝つ** — 「sandbox にすれば何でも通る」ではない

## 目的

- docs の「明示 deny 規則は auto-allow 下でも残る」を実測する(deny × モードの P2-c/d の
  **sandbox auto-allow 版**)。

## 前提(設定)

```json
{
  "sandbox": { "enabled": true },
  "permissions": { "deny": ["Bash(echo:*)"] }
}
```

## 実行内容

1. Bash で `echo data > inside.txt`(deny 規則の対象)
2. Bash で `touch s4g-ctrl.txt`(規則の対象外)

## 期待結果

| No | 操作 | 許諾 | 結果 | 補足 |
|---|---|:---:|:---:|---|
| 1 | Bash `echo data > inside.txt` | deny | - | **auto-allow でも deny 勝ち**(承認の余地なく拒否) |
| 2 | Bash `touch s4g-ctrl.txt` | allow | ✅ | 対象外は auto-allow のまま無プロンプト |

## なぜそうなるか

- deny 規則は permission エンジンの最優先(deny→ask→allow)で、sandbox 由来の auto-allow は
  この評価を飛ばさない。auto-allow が飛ばすのは「既定 ask / bare `Bash` ask」だけ(→ S4-e)で、
  明示 deny と content-scoped ask(→ S4-f)は残る。
- SDK で canUseTool **非発火** + denials 記録 = ASK ではなく hard deny(headless の auto-deny との
  混同なし)。

## 運用時の留意事項

- sandbox 運用でも「これは絶対に実行させない」は `permissions.deny` にそのまま書ける
  (auto-allow に食われない)。防壁の優先順は deny > (content-scoped) ask > auto-allow。
- deny の specifier 形状には従来の注意がそのまま効く: プレフィックス形 `Bash(cmd:*)` は効くが、
  `Bash(command:...)` のような対象外パラメータ形は無言で無効(→ P2-g)。

## 試し方(本リポジトリでの実測)

### お手軽に試す(対話)

このディレクトリで `claude` を起動し、[prompt.ja.txt](./prompt.ja.txt) を貼り付けるだけ。1 だけ承認の余地なく拒否される。

```bash
cd cases/S4-sandbox-autoallow-behavior/g-deny-overrides-autoallow && claude
```

### ハーネスで実測する(permission≠ask の類型B: 全形態同結論)

```bash
python3 harness/run.py S4-sandbox-autoallow-behavior/g-deny-overrides-autoallow
python3 harness/run.py -m sdk S4-sandbox-autoallow-behavior/g-deny-overrides-autoallow
```

## 検証記録

| 日付 | バージョン | 実測したモダリティ |
|---|---|---|
| 2026-07-05 | v2.1.201 / SDK 0.3.200 | headless(P1: DENIED・denials=[Bash] / P2: ALLOWED)/ sdk(P1: **DENIED_HARD・canUseTool 非発火** / P2: ALLOWED) |

## 対応する知識

- グループ [S4 README](../README.md) / S4 GAPS G6 の解消(spec §4.2 ①)
- 関連: P2-c,d(deny はモードに勝つ=同型)/ S4-e,f(auto-allow が飛ばすもの・飛ばさないもの)/ P2-g(deny specifier の形状注意)
