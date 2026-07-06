# P2-a: allow `Write(*)` → Write は全パスで事前承認。ただし Edit には効かない(規則はツール単位)

## 目的

- 明示的な `allow` 規則が Write を事前承認し、プロンプトなしで通ることを確認する
- その allow の効き方を対比で確定させる: **パス方向には広く**(cwd 内/外・サブdir)、**ツール方向には狭い**(Edit は対象外)

## 前提(設定)

```json
{
  "permissions": { "allow": ["Write(*)"] }
}
```

- 効く形は `Write(*)`(または裸の `Write`)。**`Write(**)` はマッチせず no-op**(→ P3)
- モード指定なし(= default)。allow 規則だけで挙動を変える

## 実行内容

1. Write でケースディレクトリ直下にファイルを作成
2. Write でホームディレクトリ(cwd 外)にファイルを作成
3. Write でケース内のサブディレクトリにファイルを作成
4. Edit で既存ファイル(cwd 内)の文字列を置換

## 期待結果

| No | 操作 | 許諾 | 結果 | 補足 |
|---|---|:---:|:---:|---|
| 1 | Write `./PROOF.txt`(cwd 内) | allow | ✅ | - |
| 2 | Write `~/p2a-proof.txt`(cwd 外) | allow | ✅ | **cwd 外にも効く**(acceptEdits の cwd 境界と対照的 → P1-b) |
| 3 | Write `./sub/proof.txt`(サブdir) | allow | ✅ | - |
| 4 | Edit `./note.txt`(既存ファイル) | ask | ✅ | **allow `Write(*)` は Edit に効かない**(規則はツール単位) |

- `Write(*)` のパススコープは全域(1〜3)。しかし 4 が `ask` = **allow はツール名で切れる**。
  「書き込みを許可したつもりが Edit で止まる」の正体。

## なぜそうなるか

- `allow` 規則にマッチしたツール呼び出しは事前承認され、default モードでも ask にならない。
- **`Write(*)` の `*` はパスを問わずマッチするが、規則が承認するのは Write ツールだけ。Edit は別ツールなので default の ask に落ちる。**
- ファイル編集を丸ごと許可したいなら、ツールごとに列挙する(`Write(*)` + `Edit(*)`)か acceptEdits を使う(→ P1-b。ただし cwd 境界あり)。

## 運用時の留意事項

- allow 規則は**ツール単位で列挙**する。「書き込み許可」のつもりで `Write(*)` だけ書くと Edit / NotebookEdit 等は承認されない。
- 効く形は `Write(*)`。`Write(**)` は無言で不一致になる(→ P3-a)。allow を書いたら必ず空撃ちで確認する。

## 試し方(本リポジトリでの実測)

### お手軽に試す(対話)

このディレクトリで `claude` を起動し、[prompt.ja.txt](./prompt.ja.txt) の内容を貼り付けるだけ。
Write の3操作は承認なしで即実行され、Edit だけ承認プロンプトが出ることがその場で確認できる。

```bash
cd cases/P2-allow-deny-precedence/a-allow && claude
# → prompt.ja.txt を貼り付け
```

### ハーネスで実測する(結果の記録・プローブ独立)

プローブ4(Edit)が ask 系なので、SDK で ask の発火も切り分けられる。

> ⚠️ **workspace trust 前提**: project settings の allow は、リポジトリを trust した後にのみ適用される
> (docs 明記)。`-p`(headless)では trust ダイアログが出ないため、**clone 直後に headless で走らせると
> allow が無視され ❌ になりうる**。初回は対話モードで一度開いて trust しておくこと。

```bash
# ヘッドレス: Write は ALLOWED、Edit は ask の auto-deny で DENIED
python3 harness/run.py P2-allow-deny-precedence/a-allow

# SDK(canUseTool = ask の計測器): Edit だけ ASK、Write は発火せず ALLOWED
python3 harness/run.py -m sdk P2-allow-deny-precedence/a-allow
```

## 検証記録

| 日付 | バージョン | 実測したモダリティ |
|---|---|---|
| 2026-07-05 | v2.1.201 | headless / sdk(4プローブとも一致) |

## 対応する知識

- docs/FINDINGS.md: Q1(headless で書くには allow 明示が一手)
- 関連: P1-a(規則なしだと ask)/ P1-b(acceptEdits は cwd 境界・こちらはツール境界)/ P3-a(`Write(**)` は no-op)
