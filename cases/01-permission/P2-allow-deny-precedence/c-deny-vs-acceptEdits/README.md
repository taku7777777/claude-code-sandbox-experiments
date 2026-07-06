# P2-c: deny `Write(*)` + acceptEdits モード → deny はモードに勝つ。deny 対象外の Edit はモードが自動承認

## 目的

- `deny` 規則が `acceptEdits`(ファイル編集を自動承認するモード)より強いことを確認する
- 同時に、deny の対象外(Edit)ではモードの自動承認がそのまま機能することを対比で示す

## 前提(設定)

```json
{
  "permissions": { "deny": ["Write(*)"] }
}
```

- 実行フラグ: `--permission-mode acceptEdits`(deny 規則を維持したままモードだけ変える)
- 「deny 規則は全モードで適用される」(spec §1)の実測。mode × 規則の交差を埋める

## 実行内容

1. Write でケースディレクトリ直下にファイルを作成
2. Write でホームディレクトリ(cwd 外)にファイルを作成
3. Write でケース内のサブディレクトリにファイルを作成
4. Edit で既存ファイル(cwd 内)の文字列を置換

## 期待結果

| No | 操作 | 許諾 | 結果 | 補足 |
|---|---|:---:|:---:|---|
| 1 | Write `./PROOF.txt`(cwd 内) | deny | - | acceptEdits の自動承認対象のはずの場所でも deny が勝つ |
| 2 | Write `~/p2c-proof.txt`(cwd 外) | deny | - | - |
| 3 | Write `./sub/proof.txt`(サブdir) | deny | - | - |
| 4 | Edit `./note.txt`(既存ファイル) | allow | ✅ | **deny の対象外なので acceptEdits の自動承認が機能** |

- 1 と 4 の対が核心: **同じ「cwd 内のファイル編集」でも、deny にマッチする Write は拒否、
  マッチしない Edit はモードが自動承認**。deny > モード、ただしツール単位。

## なぜそうなるか

- **deny 規則はモードより先に評価され、全モードで適用される**(spec §1)。acceptEdits の自動承認は
  deny を覆せない。
- deny `Write(*)` は Write ツール限定。Edit には規則が無いので、acceptEdits のモード判定
  (プロジェクト内編集を自動承認)がそのまま働く。
- 実測では deny された Write は**ツールセットから除去**される形で現れる(呼び出し自体が起きない)。

## 運用時の留意事項

- 「モードで緩めても deny は残る」ので、**危険操作の禁止は deny 規則で書くのが堅い**(モード運用と独立に効く)。
- 逆に deny で塞いだつもりでも、**対象外のツールはモードが通す**(本ケースの Edit)。禁止したい操作は
  経路になり得るツールを列挙して deny する。

## 試し方(本リポジトリでの実測)

### お手軽に試す(対話)

このディレクトリで acceptEdits モードの `claude` を起動し、[prompt.ja.txt](./prompt.ja.txt) の内容を貼り付けるだけ。
Write は承認プロンプトすら出ずに拒否され、Edit は承認なしで即実行される対照がその場で確認できる。

```bash
cd cases/P2-allow-deny-precedence/c-deny-vs-acceptEdits && claude --permission-mode acceptEdits
# → prompt.ja.txt を貼り付け
```

### ハーネスで実測する(結果の記録・プローブ独立)

```bash
python3 harness/run.py P2-allow-deny-precedence/c-deny-vs-acceptEdits
python3 harness/run.py -m sdk P2-allow-deny-precedence/c-deny-vs-acceptEdits
```

> deny(1〜3)は全形態で同結論のハードブロック(SDK では canUseTool 発火なしの DENIED_HARD)。
> Write プローブのプロンプトは**他ツールへのフォールバックを禁止**している(モデルが Bash で代替すると
> deny の観測が汚れるため)。

## 検証記録

| 日付 | バージョン | 実測したモダリティ |
|---|---|---|
| 2026-07-05 | v2.1.201 | headless / sdk(4プローブとも一致) |

## 対応する知識

- 関連: P2-b(deny > allow)/ P2-d(deny > bypass)/ P1-b(acceptEdits 単体の挙動)
