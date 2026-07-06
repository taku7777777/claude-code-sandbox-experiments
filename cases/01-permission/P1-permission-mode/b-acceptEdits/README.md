# P1-b: acceptEdits モード → ファイル編集は自動承認。ただし cwd 外は ask のまま

## 目的

- `allow` 規則が無くても、`acceptEdits` モードならプロジェクト内のファイル編集が自動承認されることを確認する
- その自動承認が**どこまで及ぶか**(cwd 外・サブディレクトリ・Edit)を対比で確定させる

## 前提(設定)

```json
{}
```

- settings.json は空。挙動を変えているのは CLI フラグ `--permission-mode acceptEdits` のみ
- P1-a と同一プローブ・同一設定で、差分はモードだけ

## 実行内容

1. Write でケースディレクトリ直下にファイルを作成
2. Write でホームディレクトリ(cwd 外)にファイルを作成
3. Write でケース内のサブディレクトリにファイルを作成
4. Edit で既存ファイル(cwd 内)の文字列を置換

## 期待結果

| No | 操作 | 許諾 | 結果 | 補足 |
|---|---|:---:|:---:|---|
| 1 | Write `./PROOF.txt`(cwd 内) | allow | ✅ | - |
| 2 | Write `~/p1b-proof.txt`(cwd 外) | ask | ✅ | **自動承認は cwd 外に及ばない**(default と同じ ask に戻る) |
| 3 | Write `./sub/proof.txt`(サブdir) | allow | ✅ | dir 新規作成を含めて自動承認 |
| 4 | Edit `./note.txt`(既存ファイル) | allow | ✅ | - |

- 2 だけが `ask`。**acceptEdits の自動承認境界は cwd** で、外側は default モードと同じ扱いになる。

## なぜそうなるか

- `acceptEdits` は「**プロジェクト内の**ファイル編集系ツールを自動承認する」モード。規則の追加は不要。
- **P1-a と設定差分はモードだけ——default → acceptEdits の切り替えで、cwd 内の書込だけが ask → allow に反転する。**
- cwd 外への書込はモードの守備範囲外なので ask のまま(deny になるわけではない。承認すれば書ける)。

## 運用時の留意事項

- `acceptEdits` でもすべてが書けるわけではない:
  - **cwd 外への書込は ask のまま**(本ケース実測)。CI で cwd 外に書くなら allow 規則を明示する
  - `.git` などの**保護パスは対象外**で、引き続き承認が要求される(→ P5-a)
- ネストした通常のプロジェクト内パス(ディレクトリ新規作成を含む)は書ける(→ P5-b)。

## 試し方(本リポジトリでの実測)

### お手軽に試す(対話)

このディレクトリで acceptEdits モードの `claude` を起動し、[prompt.ja.txt](./prompt.ja.txt) の内容を貼り付けるだけ。
cwd 内の3操作は承認なしで即実行され、cwd 外(手順2)だけ承認プロンプトが出ることがその場で確認できる。

```bash
cd cases/P1-permission-mode/b-acceptEdits && claude --permission-mode acceptEdits
# → prompt.ja.txt を貼り付け
```

### ハーネスで実測する(結果の記録・プローブ独立)

プローブ2(cwd 外)が ask 系なので、SDK で ask の発火も切り分けられる。

```bash
# ヘッドレス: cwd 内は ALLOWED、cwd 外は ask の auto-deny で DENIED
python3 harness/run.py P1-permission-mode/b-acceptEdits

# SDK(canUseTool = ask の計測器): cwd 外だけ ASK、他は発火せず ALLOWED
python3 harness/run.py -m sdk P1-permission-mode/b-acceptEdits
```

## 検証記録

| 日付 | バージョン | 実測したモダリティ |
|---|---|---|
| 2026-07-05 | v2.1.201 | headless / sdk(4プローブとも一致) |

## 対応する知識

- docs/FINDINGS.md: Q1「deny していないのに write が拒否される」
- 関連: P1-a(default だと全プローブ ask)/ P5-a(保護パスは acceptEdits でも ask)/ P5-b(ネストは書ける)
