# P5-g: dontAsk では保護パスへの Write は即 deny(ask を経ない)— allow `Write(*)` でも救えない

## 目的

- 保護パス write のモード別区分のうち **dontAsk = Denied**(default/acceptEdits/plan の
  Prompted と機構が異なる)を実測で確定する
- **allow 規則があっても保護パスは Denied のまま**(G3=allow 無効 × dontAsk=事前承認のみ通す、の交差点)
- 対照プローブで「同じ allow が通常パスには効く」ことを併測し、deny が保護パス由来だと切り分ける

## 前提(設定)

```json
{
  "permissions": {
    "allow": ["Write(*)"]
  }
}
```

- `--permission-mode dontAsk`。allow は実効が実証済みの形 `Write(*)`(P1-g と同じ)
- a/c との差分はモードのみ(acceptEdits → dontAsk)+ allow 規則

## 実行内容

1. Write で `.claude/PROBE.txt` を作成(保護パス)
2. Write で `sub/OK.txt` を作成(通常パス・対照)

## 期待結果

| No | 操作 | 許諾 | 結果 | 補足 |
|---|---|:---:|:---:|---|
| 1 | Write `.claude/PROBE.txt`(allow `Write(*)` あり) | deny | - | ask を経ない即 deny。canUseTool 非発火 |
| 2 | Write `sub/OK.txt`(同じ allow) | allow | ✅ | 同じ規則が通常パスには効く(deny は保護パス由来) |

- acceptEdits(a/c)の headless ❌ は「ask の auto-deny」だが、dontAsk の ❌ は**エンジンの即 deny**。
  headless では見分けがつかず、SDK の canUseTool **非発火**が区別の計測器になる。

## なぜそうなるか

- **dontAsk は「プロンプトになるはずのものを全部 deny に倒す」モード**(公式: "auto-denies every
  tool call that would otherwise prompt")。保護パス write は allow で事前承認**できない**
  (安全チェックが allow 評価より前 → P5-f)ので、必ず「プロンプト行き」に分類され、
  dontAsk ではそれが即 deny になる(公式モード表: dontAsk = **Denied**)。
- 対照(No.2)では同じ `Write(*)` が事前承認として機能し、プロンプト不要 → dontAsk でも通る。
  つまり dontAsk × 保護パスの deny は「dontAsk が全部止める」のではなく
  **「保護パスだけが allow の網から外れてプロンプト行き → 即 deny」**という機構。

## 運用時の留意事項

- CI 等で dontAsk を使う場合、保護パスへの書込は **allow をどう書いても通らない**。
  保護パス配下を生成物置き場にしない(例外は `.claude/worktrees` → i)。
- 「dontAsk + allow 列挙」は CI の推奨レシピ(→ P1-g)だが、保護パスはその allow 列挙の
  例外になることを前提に置くこと。

## 試し方(本リポジトリでの実測)

### お手軽に試す(対話)

このディレクトリで `claude --permission-mode dontAsk` を起動し、
[prompt.ja.txt](./prompt.ja.txt) を貼り付けるだけ。1(保護パス)はプロンプトなしで即拒否され、
2(通常パス)は承認なしで書けることが確認できる。

```bash
cd cases/P5-protected-paths/g-dontask-protected && claude --permission-mode dontAsk
# → prompt.ja.txt を貼り付け
```

### ハーネスで実測する(結果の記録・プローブ独立)

deny 系(非 ask)なので結論は全形態で同じだが、**「ask ではなく deny」の区別自体は SDK が計測器**
(canUseTool 非発火 = プロンプト機会なし)。

```bash
# ヘッドレス: 即 deny → DENIED(auto-deny との区別は headless 単独では不能)
python3 harness/run.py P5-protected-paths/g-dontask-protected

# SDK: canUseTool 非発火 + denial → DENIED_HARD(acceptEdits の ASK と対照)
python3 harness/run.py -m sdk P5-protected-paths/g-dontask-protected
```

## 検証記録

| 日付 | バージョン | 実測したモダリティ |
|---|---|---|
| 2026-07-05 | v2.1.201 | headless(1=DENIED / 2=ALLOWED)/ sdk(1=DENIED_HARD・canUseTool 非発火 / 2=ALLOWED。全プローブ一致) |

- 初回実測の副産物: allow を `Write(sub/**)`(パス限定形)で書いた版では対照プローブ(No.2)も
  DENIED になった — パス限定 Write allow glob は無言で不一致という P3 グループの実測と整合。
  交絡を避けるため実効形 `Write(*)` に差し替えた(case.json の hypothesis 末尾に記録)。

## 対応する知識

- グループ [P5 README](../README.md) / 公式 permission-modes「Protected paths」モード表(dontAsk = Denied)
- 関連: P5-f(allow は保護パスに無効)/ P1-d(dontAsk の基準挙動)/ P1-g(dontAsk + allow の肯定対照)/
  P3(パス限定 Write allow の glob 非対称)
