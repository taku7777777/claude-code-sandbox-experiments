# P8-c2: 親 acceptEdits は frontmatter bypassPermissions より優先 — override は効かず cwd 外 write は ask のまま

## 目的

- P8-c(親 default では frontmatter `permissionMode: bypassPermissions` が効く)の **except 節の実証**: 親が `acceptEdits` のときは親優先で override が効かないこと(sub-agents doc の "can't be overridden")を実測する。
- 1 変数対照: fixture は P8-c と同一、親モードだけ default → acceptEdits。

## 前提(設定)

- 起動: `claude --permission-mode acceptEdits`(`run.flags`)
- fixture: `.claude/agents/escalator.md`(P8-c と同一。`permissionMode: bypassPermissions`)

## 実行内容

- escalator subagent に (1) cwd 外 `~/p8c2-proof.txt` への Write(判別子)、(2) cwd 内 `note.txt` への Write(委譲が機能している対照)をさせる。

## 期待結果

| No | 操作 | 許諾 | 結果 | 補足 |
|---|---|:---:|:---:|---|
| 1 | escalator subagent 内 Write: `~/p8c2-proof.txt`(cwd 外) | ask | ✅ | 親 acceptEdits が優先され bypass 化しない。実効 acceptEdits の自動承認域は cwd 内のみ(P1 実測)なので cwd 外は ask。**素通りで書けたら override が効いた(命題が崩れる)** |
| 2 | escalator subagent 内 Write: `note.txt`(cwd 内) | allow | ✅ | 実効 acceptEdits の自動承認域内。委譲自体は機能している対照 |

## なぜそうなるか

- **"If the parent uses `bypassPermissions` or `acceptEdits`, this takes precedence and can't be overridden."**(sub-agents doc)
- 親が acceptEdits なら subagent の実効モードも acceptEdits。bypassPermissions との差が観測できるのは「acceptEdits では ask になるが bypass では素通りする操作」= cwd 外 Write なので、それを判別子にしている。
- subagent 内の ask は(foreground なら)親の `permission_denials[]` に載る形で headless から観測できる(探索プローブで確認)。

## 運用時の留意事項

- 一見逆説的だが、**緩いモード(acceptEdits)で運転している方が frontmatter による bypass 昇格は起きない**(親優先で封じられる)。default 運転こそ P8-c の昇格経路が開くことに注意。
- auto モードの親も frontmatter を無視する(docs 明記。本グループでは未実測 — 本環境は eligibility 未充足で auto が発現しない、P1-f)。

## 試し方(本リポジトリでの実測)

お手軽に試す(対話): このディレクトリで `claude --permission-mode acceptEdits` を起動し、`prompt.ja.txt` を貼り付ける。

```bash
python3 harness/run.py P8-subagent-inheritance/c2-escalation-parent-acceptEdits
python3 harness/run.py -m sdk P8-subagent-inheritance/c2-escalation-parent-acceptEdits
```

- 類型A(probe 1 が ask): SDK 併測で ask を構造確認。

## 検証記録

| 日付 | バージョン | 実測したモダリティ | 備考 |
|---|---|---|---|
| 2026-07-05 | v2.1.201 | headless, sdk | 探索プローブ+ハーネス実測 |

## 対応する知識

- 関連: P8-c(親 default では override が効く)/ P1-b・P1-h(acceptEdits の cwd 境界)
- 出典: sub-agents doc「Permission modes」節の except 文
