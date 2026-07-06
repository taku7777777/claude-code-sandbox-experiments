# P5-f: `allow` 規則(実効形 `Write(*)` を含む)でも保護パスへの Write は事前承認されず ask

## 目的

- settings の `permissions.allow` は**保護パスへの write を事前承認できない**(安全チェックが
  allow 評価より前に走る)ことを実測で確定する
- c(allow なしで ask)との 1 変数対照: **allow 規則を足しても結果が変わらない**ことが本ケースの意味

## 前提(設定)

```json
{
  "permissions": {
    "allow": ["Write(*)", "Write(.claude/**)", "Edit(.claude/**)"]
  }
}
```

- `--permission-mode acceptEdits`。書込先 `.claude/PROBE.txt` は c と同一で、差分は allow 規則の有無のみ
- **`Write(*)` を含めているのが交絡対策の要**: パス限定形 `Write(.claude/**)` は保護パス以前に
  glob 不一致で無言 no-op になりうる(→ P3 グループ)。`Write(*)` は P1-g / P2-a で「書込を事前承認できる」
  ことが実測済みの形なので、これがあってなお ask なら「規則が効かなかった」ではなく
  「保護パスが allow より上流」だと確定する
- `Write(.claude/**)` / `Edit(.claude/**)` は公式 docs が「書いても無効」と名指しする例をそのまま併置

## 実行内容

1. Write で `.claude/PROBE.txt` を作成(acceptEdits + 上記 allow)

## 期待結果

| No | 操作 | 許諾 | 結果 | 補足 |
|---|---|:---:|:---:|---|
| 1 | Write `.claude/PROBE.txt`(allow `Write(*)` あり) | ask | ✅ | allow は保護パスに無効。c(allow なし)と同一結果 |

## なぜそうなるか

- **保護パスの安全チェックは settings の allow 規則の評価より前に走る**(公式 permission-modes:
  "The safety check runs before Claude Code evaluates allow rules from settings, so an entry such as
  `Edit(.claude/**)` ... does not change the per-mode outcome")。
- 「allow を書けば通るはず」は運用者が最初に試す回避策だが、それが無効というのが本グループの核心
  (保護パスは allow / acceptEdits の上流の別系統)。
- 承認できるのは対話の承認プロンプトのみ。プロンプトには「このセッション中 .claude 編集を許可」の
  選択肢が出る(= セッション内限定の承認は可能)。

## 運用時の留意事項

- 保護パスへの書込を自動化したい場合、settings の allow では実現できない。対話で
  「このセッション中許可」を選ぶか、隔離環境で bypassPermissions(→ e。アンチパターン)しかない。
- 逆に「allow を広く書いても保護パスは守られたまま」なので、`Write(*)` のような広い allow を
  置く構成でも `.git`/`.claude` 等の防護は残る(ただし bypass では残らない → e)。

## 試し方(本リポジトリでの実測)

### お手軽に試す(対話)

このディレクトリで `claude --permission-mode acceptEdits` を起動し、
[prompt.ja.txt](./prompt.ja.txt) を貼り付けるだけ。allow 規則があるのに `.claude/PROBE.txt` の書込で
承認プロンプト(ask)が出ることが確認できる。

```bash
cd cases/P5-protected-paths/f-allow-no-preapprove && claude --permission-mode acceptEdits
# → prompt.ja.txt を貼り付け
```

### ハーネスで実測する(結果の記録・プローブ独立)

ask 系なので3形態で ask の解決差を実測できる。

```bash
# ヘッドレス: ask は auto-deny → DENIED
python3 harness/run.py P5-protected-paths/f-allow-no-preapprove

# SDK(canUseTool = ask の計測器): allow 規則があっても Write の ask 発火を観測 → ASK
python3 harness/run.py -m sdk P5-protected-paths/f-allow-no-preapprove

# 対話(TUI): 承認プロンプトが出て、承認すれば書込成功 → ASK
python3 harness/run.py -m interactive --step prepare P5-protected-paths/f-allow-no-preapprove
python3 harness/run.py -m interactive --step judge P5-protected-paths/f-allow-no-preapprove \
  --answer prompted=y --answer approved=y
```

## 検証記録

| 日付 | バージョン | 実測したモダリティ |
|---|---|---|
| 2026-07-05 | v2.1.201 | headless(DENIED=auto-deny)/ sdk(ASK・canUseTool 発火。1プローブ一致) |

## 対応する知識

- docs/FINDINGS.md: Q1 / 保護パスの注(「allow があっても常に承認要求」の実測裏づけが本ケース)
- 関連: P5-c(allow なしの同一プローブ=対照)/ P5-g(dontAsk では ask ではなく即 deny)/
  P3(パス限定 Write allow の glob 非対称=本ケースの交絡対策の背景)
