# P7-e: project スコープの `deny Write(*)` は user スコープの `allow Write(*)` に勝つ（a の鏡像）

## 目的

- **deny はどちらのスコープに置いても allow に勝つ**ことの対称性を、P7-a の鏡像配置（deny を project・allow を user）で確認する。
- P7-a（deny@user × allow@project）と対にすることで、「deny-first は user スコープ特有の権能ではない」ことを両向きで固める。

## 前提(設定)

project スコープ(このディレクトリの `.claude/settings.json`):

```json
{ "permissions": { "deny": ["Write(*)"] } }
```

user スコープ(`~/.claude/settings.json` 相当。ハーネスが分離 config dir に配置):

```json
{ "permissions": { "allow": ["Write(*)"] } }
```

- P7-a と allow/deny のスコープを入れ替えただけ（deny を project、allow を user へ）。
- user スコープは `arrange.configDir`（分離 `CLAUDE_CONFIG_DIR`）で配置し、trust を付与（未 trust だと user allow が読まれる前に別問題になるため）。

## 実行内容

1. Write でケースディレクトリ直下に `PROOF.txt` を作成(project=deny / user=allow の衝突)

## 期待結果(実測一致)

| No | 操作 | 許諾 | 結果 | 補足 |
|---|---|:---:|:---:|---|
| 1 | Write `./PROOF.txt`(project=deny, user=allow) | deny | - | deny が勝つ。SDK は `DENIED_HARD`(Write がツールセットから除去) |

## なぜそうなるか

- **deny 規則はスコープに依らず allow より先に評価される**（P7-a と同じ deny-first）。a では deny を最下位 user に置いても上位 project の allow に勝った。本ケースは deny を project に置いた鏡像で、結論は同じ deny。
- ⚠️ **帰属の注意（本ケース単独では deny-first を分離できない）**: precedence は managed > CLI > local > **project > user** なので、本ケースは deny が project（user より**上位**）にある。したがって precedence でも deny-first でも同じく deny になり、この 1 ケースだけでは両者を切り分けられない。**deny-first を分離した強い実測は P7-a 側**（deny を最下位 user に置いてなお上位 project allow に勝つ = precedence では説明できず deny-first でしか説明できない）。本ケースの価値は a との**対称ペア**——「どちらのスコープの deny も allow に勝つ」を両向きで示すこと。

## 運用時の留意事項

- **project の deny は user の allow で開け直せない**（逆向きの P7-a と合わせ、deny はスコープをまたいで常勝）。「一部だけ許可したい」を deny の穴開けで実現することはできない（同一スコープ内の P2-e と同じ結論がスコープ横断でも成立）。
- deny に当たったら、まず**どのスコープの deny か**を確認する（project / local / user / managed のいずれか）。

## 試し方(本リポジトリでの実測)

### お手軽に試す(対話)

⚠️ 実環境の `~/.claude/settings.json` を直接書き換えないこと。prepare が分離 config dir を組み立てて `export CLAUDE_CONFIG_DIR=...` を提示する。

```bash
python3 harness/run.py -m interactive --step prepare P7-settings-scope-precedence/e-project-deny-vs-user-allow
# → 提示された export CLAUDE_CONFIG_DIR=... の下で claude を起動し prompt.ja.txt を貼り付け
python3 harness/run.py -m interactive --step judge P7-settings-scope-precedence/e-project-deny-vs-user-allow
```

### ハーネスで実測する(結果の記録・プローブ独立)

```bash
python3 harness/run.py P7-settings-scope-precedence/e-project-deny-vs-user-allow
python3 harness/run.py -m sdk P7-settings-scope-precedence/e-project-deny-vs-user-allow
```

> deny 規則で結論が決まるため**全形態で同結論**。⚠️ SDK は既定で project スコープしか読まないため、user allow を読ませるには `settingSources: ["user","project"]` の明示が要る（case.json 参照。明示しても deny が勝つので verdict は変わらないが、交絡を排すため P7-a と揃えた）。

## 検証記録

| 日付 | バージョン | プラットフォーム | 実測したモダリティ |
|---|---|---|---|
| 2026-07-06 | v2.1.201 | macOS(darwin) | headless(DENIED) / sdk(DENIED_HARD・askFired 空) |

## 対応する知識

- 関連: P7-a（鏡像・deny-first を分離した強い実測）/ P2-b（同一スコープ内の deny > allow）/ P2-e（deny の中に allow の穴は開けられない）/ P7-b・P7-d（precedence 本体）
