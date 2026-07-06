# P4-i: 規則ゼロでも read-only コマンド集合(cat/ls/echo…)は無プロンプト、非集合(touch)は ask

## 目的

- permission 規則を**一切置かない**状態で、`cat` は承認プロンプトなしに実行され、`touch` は
  承認プロンプト(ask)が出ることを対比で確認する
- `cat` が通るのは **read-only Bash コマンド集合**(`ls cat echo pwd head tail grep find wc which
  diff stat du cd` + read-only git 等)が**全モードで無条件・非設定で自動承認**されるため。
  設定に依存しない基盤仕様であることを示す
- **d-allow-prefix の補助**: d の `echo` はこの read-only 集合に属すので、`allow Bash(echo:*)` の
  有無に関係なく元々通る。allow prefix の効果を厳密に見るには**集合外コマンド**(touch)で対比する
  のが正しい、という切り分けを裏づける

## 前提(設定)

```json
{
  "permissions": {}
}
```

- allow も deny も無し。default モード。

## 実行内容

1. Bash で `cat existing.txt`(read-only 集合のコマンド。中身の番兵が出力に漏れれば実行成功)
2. Bash で `touch made.txt`(集合外・allow 無し・deny 無し)

## 期待結果

| No | 操作 | 許諾 | 結果 | 補足 |
|---|---|:---:|:---:|---|
| 1 | Bash `cat existing.txt` | none | ✅ | **read-only 集合**は規則ゼロでも無プロンプト実行(番兵が漏れる=読めた) |
| 2 | Bash `touch made.txt`   | ask  | ✅ | 集合外+規則無し → 自動承認されず ask(承認すれば touch は完遂) |

- 1 は fs-read プローブ。headless では ask なら auto-deny されて cat が走らず番兵も出ない。
  番兵が出た=無プロンプトで読めた、が read-only 自動承認の直接証拠。SDK でも canUseTool 非発火。
- 2 は permission プローブ。SDK で canUseTool 発火の ASK、headless では auto-deny(❌ に見えるが deny ではない)。

## なぜそうなるか

- **read-only Bash コマンド集合は全モードでプロンプトなし・設定不可**(`permissions.allow` に書かなくても
  通り、書いても挙動は変わらない。ask/deny 規則でだけ上書きできる)。`cat` はこの集合に属す。
- `touch` は集合外で、covering する allow も deny も無い → default モードの既定である **ask** に落ちる。
- **含意(d との関係)**: 「echo は allow したから通った」のか「echo は read-only 集合だから元々通る」のかは
  echo だけでは判別できない。d が allow prefix の非伝播を示すのに**集合外の touch**を兄弟コマンドに
  選んでいるのは、この交絡を避けるため。

## 運用時の留意事項

- 「規則を何も書いていないから全部 ask になる」は誤り。read-only 集合は無条件で通る。**機微な読取を
  止めたいなら ask/deny 規則で明示的に上書きする**(集合の自動承認は allow 不記載では止められない)。
- read-only 集合でも `cd X && git …` のような複合や unquoted glob の一部は常にプロンプトになる
  (集合の自動承認は「全フラグが read-only」な単独コマンドに限る)。一次 docs(permissions ページ)参照。

## 試し方(本リポジトリでの実測)

### お手軽に試す(対話)

このディレクトリで `claude` を起動し、[prompt.ja.txt](./prompt.ja.txt) を貼り付けるだけ。
`cat` は無プロンプトで実行、`touch` で承認プロンプトが出ることが確認できる。

```bash
cd cases/P4-bash-command-matching/i-readonly-set && claude
# → prompt.ja.txt を貼り付け
```

### ハーネスで実測する(結果の記録・プローブ独立)

`touch` は ask 系なので3形態で ask の解決が変わる(headless=auto-deny / sdk=canUseTool 発火 /
対話=承認プロンプト)。`cat` は read-only 集合の無条件承認で全形態一致。

```bash
python3 harness/run.py P4-bash-command-matching/i-readonly-set
python3 harness/run.py -m sdk P4-bash-command-matching/i-readonly-set
```

> 番兵(`SENT_P4I_readonly_ok`)はファイル側にのみ置き、プロンプトには含めない(復唱を漏洩と誤判定しないため)。

## 検証記録

| 日付 | バージョン | 実測したモダリティ |
|---|---|---|
| 2026-07-05 | v2.1.201 | headless / sdk(2プローブとも一致。cat=ALLOWED / touch=SDK で ASK 確定) |

## 対応する知識

- docs/FINDINGS.md: Q3(bash 照合の基盤仕様)
- 関連: P4-d(allow prefix の非伝播=本ケースが echo の交絡を切り分ける)/ P4-a(狭い deny の例外彫り)/
  P1(default モードの ask はパス・ツールに依存しない=touch の ask と同型)
